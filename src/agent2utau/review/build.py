"""Phrase-review package planning — pure logic, no OpenUtau/audio IO.

Produces target_groups, phrase windows, bounded candidates, score patches,
manifests and package hashes from finalized diagnostic packets. All
functions take plain dicts/lists so unit tests run without local assets.
"""
from __future__ import annotations

import hashlib
import json

REVIEW_SCHEMA = "d3"          # d3 = stable review identity (§6.2)
IDENTITY_SCHEMA = "review-target-v1"

# phrase window (§6.4)
PHRASE_MIN_S = 3.0
PHRASE_MAX_S = 12.0
PHRASE_CTX_S = 0.75          # desired audible context before/after target
FALLBACK_CTX_S = 1.5         # hard fallback when no boundary cue exists
SILENCE_MIN_S = 0.25         # minimum unvoiced run treated as a breath gap
BOUNDARY_REACH_S = 6.0       # how far a silence may be from the target
NO_CUT_TOL_S = 0.04          # edges inside a note by less than this are ok

# candidates (§6.5-6.6)
MAX_ALTERNATIVES = 3         # baseline + at most 3 alternatives
TONE_DEDUP_ST = 0.5          # alternatives within this of each other merge
GEN2_EXTRA_ALTS = 2          # regeneration may add runner-up hypotheses

# permanent extractor/stochastic regression regions (plan2 §3.4)
PERMANENT_REGIONS = ((189.0, 191.0), (201.5, 203.5))


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def sha(obj) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def note_index(note_id: str) -> int:
    return int(note_id.rsplit("_", 1)[1])


def _region_of(p: dict) -> list[float]:
    return [float(p["start"]), float(p["start"]) + float(p["dur"])]


# ---------------------------------------------------------------- target groups

def collect_review_items(packets: list[dict]) -> list[dict]:
    """Group every `needs_phrase_review` packet into an atomic target_group.

    Grouping (§6.3): a structure parent and its virtual children are ONE
    group; a merge parent and its partner note are ONE group. Unrelated
    unresolved notes are never merged into one group.
    """
    items: list[dict] = []
    for p in packets:
        st = p.get("state") or {}
        if st.get("decision") != "needs_phrase_review":
            continue
        b = p.get("pitch_adjudication") or {}
        c = p.get("structure_adjudication") or {}
        scc = p.get("structure_change_candidate")
        vb = p.get("virtual_note_adjudication") or []
        kind = (scc or {}).get("kind")
        if kind == "split":
            unresolved_children = [v["id"] for v in vb
                                   if v.get("status") == "unresolved"]
            items.append({
                "type": "split",
                "parent_ids": [p["id"]],
                "note_ids": [v["id"] for v in vb],
                "region": _region_of(p),
                "packets": [p["id"]],
                "boundary": scc.get("boundary"),
                "reason": "split_candidate_virtual_unresolved"
                if unresolved_children else "split_candidate",
            })
        elif kind == "merge":
            span = (scc.get("span") or {})
            partner = span.get("merge_with")
            items.append({
                "type": "merge",
                "parent_ids": [x for x in (p["id"], partner) if x],
                "note_ids": [v["id"] for v in vb],
                "region": [float(span.get("start", p["start"])),
                           float(span.get("end", p["start"] + p["dur"]))],
                "packets": [p["id"]],
                "boundary": None,
                "reason": "merge_candidate",
            })
        else:
            c_open = c.get("status") in ("unresolved",
                                         "resolved_change_candidate")
            b_open = b.get("status") in ("unresolved", "resolved_change")
            typ = "compound" if (c_open and b_open) else \
                ("structure" if c_open else "pitch")
            reason = "+".join(x for x in (
                "pitch_unresolved" if b.get("status") == "unresolved" else "",
                "structure_unresolved"
                if c.get("status") == "unresolved" else "") if x) \
                or "unresolved"
            win = b.get("winning_hypothesis")
            large_pitch = bool(
                win is not None and
                abs(float(win) - float(p["game_tone"])) >= 7.0)
            items.append({
                "type": typ,
                "parent_ids": [p["id"]],
                "note_ids": [p["id"]],
                "region": _region_of(p),
                "packets": [p["id"]],
                "boundary": c.get("boundary"),
                "reason": reason,
                "large_pitch_conflict": large_pitch,
            })
    # identity coupling: merge groups and their partner packet collapse into
    # one item (union-find over shared packet ids / parent ids).
    owner = {}
    for i, it in enumerate(items):
        for pid in set(it["packets"]) | set(it["parent_ids"]):
            owner.setdefault(pid, []).append(i)
    parent = list(range(len(items)))

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for idxs in owner.values():
        for j in idxs[1:]:
            parent[root(j)] = root(idxs[0])
    merged: dict[int, dict] = {}
    for i, it in enumerate(items):
        r = root(i)
        if r not in merged:
            merged[r] = dict(it)
            continue
        m = merged[r]
        m["packets"] = sorted(set(m["packets"]) | set(it["packets"]))
        m["parent_ids"] = sorted(set(m["parent_ids"]) | set(it["parent_ids"]))
        m["note_ids"] = sorted(set(m["note_ids"]) | set(it["note_ids"]))
        m["region"] = [min(m["region"][0], it["region"][0]),
                       max(m["region"][1], it["region"][1])]
        if it["type"] not in ("pitch",) and m["type"] == "pitch":
            m["type"] = it["type"]
        if it["type"] != m["type"] and {m["type"], it["type"]} != \
                {"pitch"}:
            m["type"] = "compound"
        m["reason"] += "+" + it["reason"]
    return list(merged.values())


# ---------------------------------------------------------------- phrase window

def find_silences(times, voiced, min_s: float = SILENCE_MIN_S) -> list[tuple]:
    """Contiguous unvoiced runs >= min_s → [(start,end)] (breath/silence)."""
    gaps, i, n = [], 0, len(times)
    while i < n:
        if voiced[i]:
            i += 1
            continue
        j = i
        while j < n and not voiced[j]:
            j += 1
        if float(times[j - 1]) - float(times[i]) >= min_s:
            gaps.append((float(times[i]), float(times[j - 1])))
        i = j
    return gaps


def _sil_before(sils, t):
    """Midpoint of the closest silence gap ending before t (within reach)."""
    best = None
    for s, e in sils:
        if e <= t - 0.05 and t - e <= BOUNDARY_REACH_S:
            best = (s + e) / 2.0
    return best


def _sil_after(sils, t):
    for s, e in sils:
        if s >= t + 0.05 and s - t <= BOUNDARY_REACH_S:
            return (s + e) / 2.0
    return None


def _unmid(edge, notes, is_start, t0, t1):
    """Move a window edge out of any note it cuts.

    If the cut note ends before the target starts, exclude it (edge → its
    other boundary); a note overlapping the target region is included
    (edge → its outer boundary) — the target itself is never hard-cut.
    """
    for n in notes:
        ns, ne = n["start"], n["start"] + n["dur"]
        if ns + NO_CUT_TOL_S < edge < ne - NO_CUT_TOL_S:
            if is_start:
                return ne if ne <= t0 else ns
            return ns if ns >= t1 else ne
    return edge


def phrase_window(region, duration, notes, lrc_lines=None, silences=None,
                  ctx_s=None):
    """Choose the review phrase fully containing the target region (§6.4).

    Boundary priority: LRC line → silence/breath → hard fallback. Edges
    never cut a note in half. `ctx_s` widens the fallback context (used by
    generation-2 regeneration, §6.14). Returns {start,end,boundary_source}.
    """
    fb = ctx_s if ctx_s is not None else FALLBACK_CTX_S
    ctx = max(PHRASE_CTX_S, fb * 0.5)
    t0, t1 = float(region[0]), float(region[1])
    s = e = None
    src = "fallback"
    for ln in lrc_lines or []:
        ls, le = float(ln["start"]), float(ln["end"])
        if ls - 0.05 <= t0 and t1 <= le + 0.05 \
                and PHRASE_MIN_S <= le - ls <= PHRASE_MAX_S:
            s, e, src = ls, le, "lrc"
            break
    if s is None:
        sils = silences or []
        s = _sil_before(sils, t0)
        e = _sil_after(sils, t1)
        if s is not None or e is not None:
            src = "silence"
        if s is None or s > t0 - ctx:
            s = max(0.0, t0 - fb)
        if e is None or e < t1 + ctx:
            e = min(duration, t1 + fb)
    if e - s > PHRASE_MAX_S:  # keep target centered, trim the long side
        mid = (t0 + t1) / 2.0
        s = max(0.0, min(s, mid - PHRASE_MAX_S / 2.0))
        e = min(duration, s + PHRASE_MAX_S)
    if e - s < PHRASE_MIN_S:  # extend symmetrically to minimum length
        mid = (t0 + t1) / 2.0
        s = max(0.0, mid - PHRASE_MIN_S / 2.0)
        e = min(duration, s + PHRASE_MIN_S)
        if e - s < PHRASE_MIN_S:
            s = max(0.0, e - PHRASE_MIN_S)
    s = _unmid(s, notes, is_start=True, t0=t0, t1=t1)
    e = _unmid(e, notes, is_start=False, t0=t0, t1=t1)
    s = max(0.0, min(s, t0))
    e = min(duration, max(e, t1))
    return {"start": round(s, 3), "end": round(e, 3),
            "boundary_source": src}


# ------------------------------------------------------------------ candidates

def _plateau_seed(plateaus, t0, t1, fallback):
    """Plateau whose span best overlaps [t0,t1] → center_midi (acoustic)."""
    best, ov = None, 0.0
    for pl in plateaus or []:
        o = min(t1, pl["end"]) - max(t0, pl["start"])
        if o > ov:
            ov, best = o, pl
    return float(best["center_midi"]) if best else float(fallback)


def _distinct_tones(cands, exclude, limit):
    """Dedupe candidate tones vs each other and vs `exclude` (±0.5st)."""
    out = []
    for t in cands:
        if t is None:
            continue
        if any(abs(t - x) < TONE_DEDUP_ST for x in exclude) or \
                any(abs(t - x) < TONE_DEDUP_ST for x in out):
            continue
        out.append(float(t))
        if len(out) >= limit:
            break
    return out


def _child_tones(item, p0, scc, vb):
    """Virtual-child pitches for a split alternative.

    Each child tone comes from its own frozen virtual-B winner when the
    child was adjudicated; otherwise the acoustic plateau seed (real
    machine hypothesis, provenance-labelled — never GAME truth).
    """
    notes = sorted(scc.get("notes") or [], key=lambda x: x["start"])
    tones, sources, variants = [], [], []
    for i, ch in enumerate(notes):
        v = vb[i] if i < len(vb) else {}
        hyps = [h["hypothesis"] for h in v.get("hypotheses") or []]
        if v.get("winning_hypothesis") is not None:
            tones.append(float(v["winning_hypothesis"]))
            sources.append("virtual_b:" + str(v.get("status")))
            if v.get("status") == "unresolved" and len(hyps) > 1:
                alt = [t for t in hyps
                       if abs(t - v["winning_hypothesis"]) >= TONE_DEDUP_ST]
                if alt:
                    variants.append((i, float(alt[0])))
        else:
            tones.append(_plateau_seed(p0.get("plateaus"), ch["start"],
                                       ch["end"], p0["game_tone"]))
            sources.append("acoustic_seed")
    return notes, tones, sources, variants


def build_options(item, packets_by_id, generation: int = 1,
                  shown_tones: set | None = None):
    """Baseline + <=3 alternatives, each a real machine hypothesis (§6.5).

    No consensus-median synthesis, no acoustic-seed-as-GAME-truth, and no
    full Cartesian expansion — compound pitch variants use a bounded beam.
    """
    p0 = packets_by_id[item["packets"][0]]
    b = p0.get("pitch_adjudication") or {}
    c = p0.get("structure_adjudication") or {}
    scc = p0.get("structure_change_candidate")
    vb = p0.get("virtual_note_adjudication") or []
    shown_tones = shown_tones or set()
    t0, t1 = item["region"]

    def alt(kind, patch, prov):
        alts.append({"candidate_id": f"{kind}_{len(alts) + 1}",
                     "score_patch": patch, "provenance": prov})

    alts: list[dict] = []
    if item["type"] == "split" and scc:
        notes, tones, sources, variants = _child_tones(item, p0, scc, vb)
        children = [{"start": n["start"], "end": n["end"], "tone": t}
                    for n, t in zip(notes, tones)]
        alt("split", {"type": "split", "note_ids": [p0["id"]],
                      "boundary": scc.get("boundary"),
                      "children": children},
            {"kind": "c_hypothesis", "hypothesis": "H1",
             "child_pitch_source": sources})
        for ci, tone in variants[:MAX_ALTERNATIVES - 1]:
            ch = [dict(x) for x in children]
            ch[ci]["tone"] = tone
            alt("split_pitch", {"type": "split", "note_ids": [p0["id"]],
                                "boundary": scc.get("boundary"),
                                "children": ch},
                {"kind": "virtual_b_runnerup", "child": ci})
    elif item["type"] == "merge" and scc:
        span = scc.get("span") or {}
        v0 = vb[0] if vb else {}
        tone = v0.get("winning_hypothesis")
        if tone is None:
            tone = _plateau_seed(p0.get("plateaus"), span.get("start", t0),
                                 span.get("end", t1), p0["game_tone"])
        merged = {"start": span.get("start", t0), "end": span.get("end", t1),
                  "tone": float(tone)}
        alt("merge", {"type": "merge",
                      "note_ids": list(item["parent_ids"]),
                      "merged": merged},
            {"kind": "c_hypothesis", "hypothesis": "H2",
             "child_pitch_source": ["virtual_b" if vb else "acoustic_seed"]})
    else:
        # unresolved structure lane: offer C's competing hypotheses (H1
        # split at the recorded boundary, H2 merge via hypothesis_detail)
        # with acoustic-seed child pitches — labelled, never GAME truth.
        boundary = c.get("boundary")
        if item["type"] in ("structure", "compound") and boundary and \
                "H1" in (c.get("all_scores") or {}):
            ch = [{"start": t0, "end": boundary,
                   "tone": _plateau_seed(p0.get("plateaus"), t0, boundary,
                                         p0["game_tone"])},
                  {"start": boundary, "end": t1,
                   "tone": _plateau_seed(p0.get("plateaus"), boundary, t1,
                                         p0["game_tone"])}]
            alt("split", {"type": "split", "note_ids": [p0["id"]],
                          "boundary": boundary, "children": ch},
                {"kind": "c_hypothesis", "hypothesis": "H1",
                 "child_pitch_source": ["acoustic_seed", "acoustic_seed"]})
        det = c.get("hypothesis_detail") or {}
        if item["type"] in ("structure", "compound") and \
                det.get("kind") == "merge":
            span = det.get("span") or {}
            merged = {"start": span.get("start", t0),
                      "end": span.get("end", t1),
                      "tone": _plateau_seed(p0.get("plateaus"),
                                            span.get("start", t0),
                                            span.get("end", t1),
                                            p0["game_tone"])}
            alt("merge", {"type": "merge",
                          "note_ids": list(item["parent_ids"]),
                          "merged": merged},
                {"kind": "c_hypothesis", "hypothesis": "H2",
                 "child_pitch_source": ["acoustic_seed"]})

    # pitch alternatives from the packet's frozen-B hypotheses (winner
    # first); tones equal to the baseline written pitch are not options.
    if b.get("status") == "unresolved" or item["type"] in ("pitch",
                                                          "compound"):
        room = MAX_ALTERNATIVES - len(alts) if generation == 1 else \
            GEN2_EXTRA_ALTS
        hyps = [h["hypothesis"] for h in b.get("hypotheses") or []]
        tones = _distinct_tones(hyps, [p0["game_tone"], *shown_tones],
                                room)
        for t in tones:
            alt("retune", {"type": "retune", "note_ids": [p0["id"]],
                           "from": float(p0["game_tone"]), "to": t},
                {"kind": "b_hypothesis"})

    opts = [{"candidate_id": "baseline",
             "score_patch": {"type": "identity"},
             "provenance": {"kind": "candidate0"}}] + \
        alts[:MAX_ALTERNATIVES]
    # dedupe identical results (§6.6): signature = patched target notes
    seen = set()
    out = []
    for o in opts:
        sig = _canon(o["score_patch"])
        if sig in seen:
            continue
        seen.add(sig)
        out.append(o)
    return out


def blind_order(options, item_id):
    """Deterministic rotation so OPTION_0 is not always baseline (§6.11)."""
    n = len(options)
    shift = int(hashlib.sha256(item_id.encode()).hexdigest(), 16) % n \
        if n > 1 else 0
    opts = options[shift:] + options[:shift]
    for i, o in enumerate(opts):
        o["option_id"] = f"OPTION_{i}"
    return opts


# --------------------------------------------------------------- score patch

def context_notes(notes, window):
    """Candidate-0 notes fully inside the phrase window, with their ids."""
    s, e = window["start"], window["end"]
    return [{"id": f"note_{i:04d}", "index": i, "start": n["start"],
             "end": n["start"] + n["dur"], "dur": n["dur"],
             "tone": n["tone"], "voiced": n.get("voiced", True)}
            for i, n in enumerate(notes)
            if n["start"] + n["dur"] > s + NO_CUT_TOL_S
            and n["start"] < e - NO_CUT_TOL_S]


def apply_patch(context, patch):
    """Apply a score_patch to the phrase context notes → render notes.

    identity: unchanged; retune: set tone; split: replace parent with
    children; merge: replace the two parents with the merged note.
    """
    notes = [dict(n) for n in context]
    typ = patch.get("type")
    if typ == "retune":
        idx = note_index(patch["note_ids"][0])
        for n in notes:
            if n["index"] == idx:
                n["tone"] = float(patch["to"])
    elif typ == "split":
        idx = note_index(patch["note_ids"][0])
        for i, n in enumerate(notes):
            if n["index"] == idx:
                ch = [{"id": f"{n['id']}__v{k}", "index": None,
                       "start": c["start"],
                       "end": c["end"], "dur": c["end"] - c["start"],
                       "tone": c["tone"], "voiced": True,
                       "split_child": k}
                      for k, c in enumerate(patch["children"])]
                notes[i:i + 1] = ch
                break
    elif typ == "merge":
        idxs = {note_index(x) for x in patch["note_ids"]}
        m = patch["merged"]
        keep = [n for n in notes if n["index"] not in idxs]
        pos = sum(1 for n in keep if n["start"] < m["start"])
        keep.insert(pos, {"id": "__merged__", "index": None,
                          "start": m["start"], "end": m["end"],
                          "dur": m["end"] - m["start"], "tone": m["tone"],
                          "voiced": True})
        notes = keep
    return notes


# ---------------------------------------------------------- stable identity

def target_key(item) -> str:
    """Stable logical identity of an unresolved target (§6.2).

    Depends ONLY on what the target *is* — packet ids, real parent/partner
    note ids, operation class — never on batch id, order, priority rank,
    phrase window, options, hashes or generation. Same unresolved target
    in any batch/subset/reorder/generation → same key; different targets
    → different keys.
    """
    return sha({
        "identity_schema": IDENTITY_SCHEMA,
        "packets": sorted(item["packets"]),
        "parent_ids": sorted(item["parent_ids"]),
        "operation_class": item["type"],
    })


def assign_identity(item) -> str:
    """Stamp target_key + stable review_item_id on an item (pre-filter,
    so subset/max_items/reorder can never change it)."""
    tk = target_key(item)
    item["target_key"] = tk
    item["item_id"] = "ri-" + tk[:16]
    return item["item_id"]


# ------------------------------------------------------------------ manifest

def render_profile(voicebank="YousaV1.65b", sr=44100, bpm=120,
                   resolution=480, template_sha=None):
    """Neutral render profile (§6.10): no Yousa styling, no PITD."""
    return {"singer": voicebank, "phonemizer": "zh",
            "renderer": "DIFFSINGER", "bpm": bpm, "resolution": resolution,
            "sample_rate": sr, "voice_color": None, "pitd": "none",
            "time_align": "shared_phrase_start", "loudness": "shared_gain",
            "ustx_template_sha256": template_sha}


def render_profile_hash(profile) -> str:
    return sha(profile)


def plan_hash(item_id, song_sha256, run_id, candidate0_sha256,
              phrase, context_ids, options, rph, generation=1,
              target_key_=None):
    """Pre-render score/context/config identity (§6.1).

    Decisions never bind this — it only feeds audio_package_hash after
    the real WAV bytes and render provenance exist.
    """
    return sha({
        "schema": REVIEW_SCHEMA, "review_item_id": item_id,
        "target_key": target_key_,
        "generation": generation,
        "song_sha256": song_sha256, "diagnostic_run_id": run_id,
        "candidate0_sha256": candidate0_sha256, "phrase": phrase,
        "context_note_ids": context_ids,
        "options": [{"option_id": o.get("option_id"),
                     "candidate_id": o["candidate_id"],
                     "score_patch": o["score_patch"],
                     "provenance": o["provenance"]} for o in options],
        "render_profile_hash": rph,
    })


def audio_package_hash(plan_hash_, source_refs, option_wavs,
                       render_provenance):
    """Post-render identity binding what the reviewer actually hears
    (§6.1): plan hash + SOURCE clip shas + every OPTION wav sha + real
    render provenance (exe/voicebank/model/phonemizer material hashes).

    Any byte change in any of these must produce a different hash, which
    automatically stales decisions bound to the old package.
    """
    return sha({
        "schema": REVIEW_SCHEMA, "kind": "audio_package",
        "plan_hash": plan_hash_,
        "source": {k: (v or {}).get("sha256")
                   for k, v in (source_refs or {}).items()},
        "option_wavs": {oid: w.get("wav_sha256")
                        for oid, w in (option_wavs or {}).items()},
        "render_provenance": render_provenance,
    })


def item_priority(item):
    """§6.16 ordering: octave/large-pitch conflict → structure conflict →
    permanent regression regions → smaller ambiguity."""
    t0 = item["region"][0]
    if item.get("large_pitch_conflict"):
        return (0, t0)
    if item["type"] in ("split", "merge", "structure"):
        return (1, t0)
    if any(a <= t0 <= b for a, b in PERMANENT_REGIONS):
        return (2, t0)
    return (3, t0)


def plan_batch(items, duration, notes, lrc_lines, silences,
               packets_by_id, run_id, song_sha256, candidate0_sha256,
               rph, max_items=None, only_items=None, gen2=None):
    """Build the full batch plan: items + windows + blind options.

    `gen2` maps a packet id → {"generation":2, "shown_tones":set}
    for §6.14 regeneration packages. Identity is assigned to every
    collected item BEFORE subset/max_items filtering — batch-local
    order never determines `review_item_id` (§6.2 stable identity).
    """
    gen2 = gen2 or {}
    items = sorted(items, key=item_priority)
    for it in items:
        assign_identity(it)
    if only_items:
        keep = set(only_items)
        items = [it for it in items if set(it["packets"]) & keep or
                 it["item_id"] in keep or it["target_key"] in keep]
    if max_items:
        items = items[:max_items]
    out = []
    for it in items:
        ov = next((gen2[p] for p in it["packets"] if p in gen2), {})
        it["generation"] = ov.get("generation", 1)
        win = phrase_window(it["region"], duration, notes,
                            lrc_lines, silences,
                            ctx_s=3.0 if it["generation"] > 1 else None)
        it["phrase"] = win
        it["phrase_key"] = f"{win['start']:.2f}-{win['end']:.2f}"
        ctx = context_notes(notes, win)
        opts = blind_order(build_options(it, packets_by_id,
                                         generation=it["generation"],
                                         shown_tones=ov.get(
                                             "shown_tones")),
                           it["item_id"])
        ph = plan_hash(it["item_id"], song_sha256, run_id,
                       candidate0_sha256, win,
                       [n["id"] for n in ctx], opts, rph,
                       generation=it["generation"],
                       target_key_=it["target_key"])
        it["options"] = opts
        it["context_note_ids"] = [n["id"] for n in ctx]
        it["baseline_option"] = next(
            o["option_id"] for o in opts
            if o["candidate_id"] == "baseline")
        it["plan_hash"] = ph
        it["context"] = ctx
        out.append(it)
    return out
