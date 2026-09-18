"""M2.4 SAFE Repair Engine — plan/apply split, copy-on-write on Candidate 0.

v1 scope (plan2 §6.1): single existing-note written-pitch retune ONLY.
Split/merge/insert/delete/boundary/lyric/PITD patches are never applied —
a valid human structure selection is preserved but `blocked_structure`.

Two legal inputs (§6.2):
  A. machine-safe — frozen upstream `state.decision == "repair_candidate"`
     packets only; M2.4 verifies the frozen authorization, never
     re-computes B scores/margins/thresholds.
  B. human-selected — `review.render.repair_authorized_decision()`; the
     already-reviewed `selected_score_patch` snapshot is consumed
     verbatim (no OPTION re-interpretation, no B/C re-derivation).

Candidate 0 is immutable: planning never mutates it and apply writes
only `runs/<diag>/repair/` artifacts.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

REPAIR_SCHEMA = "m24-2"
REPAIR_DIRNAME = "repair"
TONE_EPS_ST = 0.05        # ~5 cents: below this a "retune" is a no-op
MIDI_MIN, MIDI_MAX = 0.0, 127.0

PATCH_OK = "eligible"
BLOCKED_STRUCTURE = "blocked_structure"
BLOCKED_CONFLICT = "blocked_conflict"
REJECTED = "rejected"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _sha(obj) -> str:
    if isinstance(obj, (dict, list)):
        obj = _canon(obj).encode("utf-8")
    return hashlib.sha256(obj).hexdigest()


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)


def _note_index(note_id: str) -> int:
    return int(note_id.rsplit("_", 1)[1])


def _span_of(note) -> list[float]:
    return [float(note["start"]), float(note["start"]) + float(note["dur"])]


def canonical_plan_hash(plan) -> str:
    """§10.1.4 (P2): tamper-evident plan identity — recomputable from the
    plan's binding fields. Excludes created_at; covers schema, run,
    Candidate-0 bindings, authority bindings and every repair's
    identity/patch/status semantics. apply MUST recompute and compare:
    a stored hash that does not match is tamper or drift -> refuse."""
    return _sha({
        "schema": plan.get("schema"),
        "run_id": plan.get("diagnostic_run_id"),
        "candidate0_sha256": plan.get("candidate0_sha256"),
        "bindings": plan.get("bindings"),
        "repairs": [{k: e.get(k) for k in
                     ("repair_id", "note_id", "source_type", "affected",
                      "patch", "authority", "before", "after",
                      "status", "blocked_reason", "provenance_refs")}
                    for e in plan.get("repairs") or []]})


# ------------------------------------------------------------- patch shape

def validate_retune_patch(patch, notes) -> tuple[bool, str]:
    """v1 patch-shape gate (§6.3/§7.1). Returns (ok, reason).

    Legal: retune of exactly one existing Candidate-0 note — same note
    identity/span, finite in-range tone materially different from the
    baseline tone. Anything structure-shaped -> blocked_structure.
    """
    typ = (patch or {}).get("type")
    if typ in ("split", "merge", "insert", "delete", "boundary_shift",
               "move", "lyric", "pitd"):
        return False, BLOCKED_STRUCTURE
    if typ != "retune":
        return False, f"out_of_scope:{typ}"
    ids = patch.get("note_ids") or []
    if len(ids) != 1:
        return False, "not_single_note"
    try:
        idx = _note_index(ids[0])
    except (ValueError, AttributeError):
        return False, "bad_note_id"
    if not (0 <= idx < len(notes)):
        return False, "note_not_in_candidate0"
    to = patch.get("to")
    if not isinstance(to, (int, float)) or not math.isfinite(to) or \
            not (MIDI_MIN <= float(to) <= MIDI_MAX):
        return False, "tone_invalid"
    if abs(float(to) - float(notes[idx]["tone"])) < TONE_EPS_ST:
        return False, "tone_unchanged"
    frm = patch.get("from")
    if frm is not None and abs(float(frm) - float(notes[idx]["tone"])) \
            >= TONE_EPS_ST:
        return False, "patch_from_mismatch"
    return True, "ok"


# --------------------------------------------------------- machine adapter

def machine_candidates(packets) -> list[dict]:
    """Frozen-upstream adapter (§6.2-A): verify the finalized
    `repair_candidate` authorization, never re-adjudicate.

    Each entry: {source_type, note_id, patch, gate refs}. Packets whose
    frozen artifacts don't satisfy every gate are skipped — their blocker
    was already decided upstream.
    """
    out = []
    for p in packets:
        st = p.get("state") or {}
        if st.get("decision") != "repair_candidate":
            continue
        b = p.get("pitch_adjudication") or {}
        c = p.get("structure_adjudication") or {}
        gate = p.get("repair_gate") or {}
        tone = b.get("winning_hypothesis")
        ok = (
            st.get("separation_state") != "sensitive"
            and not (p.get("separation") or {}).get("separation_sensitive")
            and gate.get("eligible") is True
            and b.get("status") == "resolved_change"
            and not b.get("provisional")
            and not b.get("invalidated_by_structure")
            and b.get("status") != "invalidated"
            and p.get("structure_change_candidate") is None
            and (c.get("status") in ("resolved_keep", "not_needed")
                 or p.get("final_structure_clear"))
            and isinstance(tone, (int, float)) and math.isfinite(tone)
        )
        if not ok:
            continue
        out.append({
            "source_type": "machine_safe",
            "note_id": p["id"],
            "patch": {"type": "retune", "note_ids": [p["id"]],
                      "from": float(p["game_tone"]), "to": float(tone)},
            "authority": {
                "packet_id": p["id"],
                "b_status": b.get("status"),
                "winning_hypothesis": tone,
                "repair_gate": gate,
                "c_status": c.get("status"),
                "final_structure_clear":
                    bool(p.get("final_structure_clear")),
            },
        })
    return out


def human_candidates(run_dir: Path) -> list[dict]:
    """D-authority adapter (§6.2-B): every registered review item through
    the single repair gate. Non-candidate decisions contribute nothing —
    a valid structure selection yields a blocked_structure entry so the
    authority is preserved, not dropped (§6.3)."""
    from .review.decisions import load_packages
    from .review.render import repair_authorized_decision
    out = []
    for iid in sorted(load_packages(run_dir)):
        rev = repair_authorized_decision(run_dir, iid)
        if rev is None:
            continue
        patch = rev.get("selected_score_patch") or {}
        entry = {
            "source_type": "human_selected",
            "note_id": (patch.get("note_ids") or [None])[0],
            "patch": patch,
            "authority": {
                "review_item_id": iid,
                "target_key": rev.get("target_key"),
                "revision_id": rev["revision_id"],
                "audio_package_hash": rev["audio_package_hash"],
                "selected_option_id": rev.get("selected_option_id"),
                "selected_provenance": rev.get("selected_provenance"),
                "selected_wav_sha256": rev.get("selected_wav_sha256"),
            },
        }
        out.append(entry)
    return out


# ------------------------------------------------------------------- plan

def _repair_id(run_id, c0_sha, cand, note) -> str:
    """Stable identity (§6.5): same evidence → same repair_id. No
    timestamps — content only."""
    a = cand["authority"]
    return "rp-" + _sha({
        "schema": REPAIR_SCHEMA,
        "run_id": run_id, "candidate0_sha256": c0_sha,
        "source_type": cand["source_type"],
        "authority_id": a.get("revision_id") or a.get("packet_id"),
        "note_id": cand["note_id"],
        "before": {"start": note["start"], "end": _span_of(note)[1],
                   "tone": note["tone"]},
        "after_tone": cand["patch"].get("to"),
    })[:24]


def build_plan(run_dir: Path, *, run_id=None, packets=None, notes=None,
               triage_sha=None, song_sha256=None, write=True) -> dict:
    """Read-only planning (§6.4): collect both paths, shape-validate,
    dedupe/conflict-detect, bind upstream artifacts. Candidate 0 is
    never touched. Returns the plan dict (also written to
    runs/<diag>/repair/repair_plan.json when `write`)."""
    run_dir = Path(run_dir)
    run_id = run_id or run_dir.name
    c0_path = run_dir / "diagnostic" / "baseline_game.json"
    if packets is None or notes is None:
        diag = run_dir / "diagnostic"
        packets = json.loads((diag / "residual_triage.json")
                             .read_text(encoding="utf-8"))
        notes = json.loads(c0_path.read_text(encoding="utf-8"))["notes"]
        triage_sha = _file_sha(diag / "residual_triage.json")
        if song_sha256 is None:
            rep = json.loads((run_dir / "report.json")
                             .read_text(encoding="utf-8"))
            song_sha256 = rep["cache"]["source_sha256"]
    # §6.3/§6.4-D (pre-M2.5): the plan binds BOTH the semantic notes
    # hash and the exact baseline_game.json artifact bytes — without
    # the exact artifact there is nothing to bind and NO plan may be
    # produced (fail-closed, never a sha=None plan).
    if not c0_path.exists():
        raise FileNotFoundError(
            f"{c0_path} missing — cannot bind the exact Candidate-0 "
            "artifact; refusing to build a repair plan")
    c0_sha = _sha(notes)
    c0_file_sha = _file_sha(c0_path)

    cands = machine_candidates(packets) + human_candidates(run_dir)
    entries, per_note = [], {}
    for c in cands:
        nid = c["note_id"]
        note = None
        if nid is not None:
            try:
                note = notes[_note_index(nid)]
            except (ValueError, IndexError):
                note = None
        ok, why = (False, "note_not_in_candidate0") if note is None \
            else validate_retune_patch(c["patch"], notes)
        e = {
            "repair_id": _repair_id(run_id, c0_sha, c, note)
            if note is not None else None,
            "note_id": nid, "source_type": c["source_type"],
            "patch": c["patch"], "authority": c["authority"],
            "before": {"start": note["start"], "end": _span_of(note)[1],
                       "tone": note["tone"]} if note else None,
            "after": {"start": note["start"], "end": _span_of(note)[1],
                      "tone": c["patch"].get("to")} if note else None,
            "status": PATCH_OK if ok else
            (BLOCKED_STRUCTURE if why == BLOCKED_STRUCTURE else REJECTED),
            "blocked_reason": None if ok else why,
        }
        entries.append(e)
        if nid is not None:
            per_note.setdefault(nid, []).append(e)

    # §6.6 conflict policy — no silent precedence. Same note + same after
    # tone dedupes (provenance kept); different after tone blocks ALL.
    for nid, group in per_note.items():
        elig = [e for e in group if e["status"] == PATCH_OK]
        if len(elig) <= 1:
            continue
        tones = {round(float(e["patch"]["to"]), 4) for e in elig}
        if len(tones) == 1:
            keep = elig[0]
            keep["provenance_refs"] = [e["authority"] for e in elig[1:]]
            for e in elig[1:]:
                e["status"] = "deduped"
                e["blocked_reason"] = f"duplicate_of:{keep['repair_id']}"
        else:
            for e in elig:
                e["status"] = BLOCKED_CONFLICT
                e["blocked_reason"] = "same_note_conflicting_after_tone"

    plan = {
        "schema": REPAIR_SCHEMA,
        "created_at": _now(),
        "diagnostic_run_id": run_id,
        "candidate0_sha256": c0_sha,
        "candidate0_notes_sha256": c0_sha,
        "candidate0_file_sha256": c0_file_sha,
        "song_sha256": song_sha256,
        "bindings": {
            "residual_triage_sha256": triage_sha,
            "candidate0_notes_sha256": c0_sha,
            "candidate0_file_sha256": c0_file_sha,
            "review_authority": {"schema": "d3",
                                 "identity_schema": "review-target-v1"},
            "human_revisions": {e["authority"]["review_item_id"]: {
                "revision_id": e["authority"]["revision_id"],
                "audio_package_hash": e["authority"]["audio_package_hash"],
            } for e in entries if e["source_type"] == "human_selected"},
        },
        "repairs": entries,
        "summary": {},
    }
    for e in entries:
        plan["summary"][e["status"]] = plan["summary"].get(e["status"], 0) + 1
    plan["plan_hash"] = canonical_plan_hash(plan)
    if write:
        _atomic_write(run_dir / REPAIR_DIRNAME / "repair_plan.json", plan)
    return plan


# ------------------------------------------------------------------ apply

def _eligible_entries(plan, only=None, exclude=None):
    elig = [e for e in plan["repairs"] if e["status"] == PATCH_OK]
    if only is not None:
        keep = set(only)
        elig = [e for e in elig if e["repair_id"] in keep]
    if exclude:
        drop = set(exclude)
        elig = [e for e in elig if e["repair_id"] not in drop]
    return elig


def apply_repairs(notes, entries) -> list:
    """Deterministic copy-on-write apply (§6.8): returns a NEW note list;
    `notes` is never mutated. Subset/zero repair ids rebuild correctly."""
    out = [dict(n) for n in notes]
    for e in entries:
        idx = _note_index(e["note_id"])
        out[idx] = dict(out[idx], tone=float(e["patch"]["to"]))
    return out


def corrected_score(notes, applied_ids, c0_sha,
                    c0_file_sha=None) -> dict:
    return {"schema": REPAIR_SCHEMA,
            "base_candidate0_sha256": c0_sha,
            "base_candidate0_notes_sha256": c0_sha,
            "base_candidate0_file_sha256": c0_file_sha,
            "notes": notes,
            "applied_repairs": list(applied_ids),
            "corrected_score_sha256": _sha({"notes": notes,
                                            "applied": list(applied_ids)})}


def verify_freshness(run_dir: Path, plan, *, schema=REPAIR_SCHEMA,
                     machine_adapter=None) -> list[str]:
    """§6.9/§6.10 — every binding must still hold at apply time."""
    from .review.render import repair_authorized_decision
    run_dir = Path(run_dir)
    if machine_adapter is None:
        machine_adapter = machine_candidates
    stale = []
    # §6.4-D (pre-M2.5): fail-closed schema + dual-binding gate. A
    # legacy m24-1 plan (or any plan missing either Candidate-0 hash)
    # can never authorize apply — it must be regenerated, never
    # silently migrated by backfilling current hashes.
    if plan.get("schema") != schema:
        stale.append(f"unsupported_plan_schema:{plan.get('schema')}")
    if not plan.get("candidate0_notes_sha256"):
        stale.append("missing_candidate0_notes_sha256")
    if not plan.get("candidate0_file_sha256"):
        stale.append("missing_candidate0_file_sha256")
    # §10.1.4 (P2): tamper-evidence — the stored plan_hash must recompute
    # over the plan's own binding fields; a tampered operation, tone,
    # authority or binding cannot keep the old hash.
    if plan.get("plan_hash") != canonical_plan_hash(plan):
        stale.append("plan_hash_mismatch")
    diag = run_dir / "diagnostic"
    c0_path = diag / "baseline_game.json"
    if stale or not c0_path.exists():
        if not c0_path.exists():
            stale.append("candidate0_file_missing")
        return stale
    notes = json.loads(c0_path.read_text(encoding="utf-8"))["notes"]
    if _sha(notes) != plan["candidate0_notes_sha256"]:
        stale.append("candidate0_notes_changed")
    if _file_sha(c0_path) != plan["candidate0_file_sha256"]:
        stale.append("candidate0_file_changed")
    if plan["bindings"].get("residual_triage_sha256") and \
            _file_sha(diag / "residual_triage.json") != \
            plan["bindings"]["residual_triage_sha256"]:
        stale.append("residual_triage_changed")
    # machine path: re-run the adapter; every applied machine repair_id
    # must still be authorized by the SAME frozen upstream artifact
    now = {}
    for e in machine_adapter(packets=json.loads(
            (diag / "residual_triage.json").read_text(encoding="utf-8"))):
        now.setdefault(e["note_id"], []).append(e)
    for e in plan["repairs"]:
        if e["status"] != PATCH_OK:
            continue
        if e["source_type"].startswith("machine"):
            cur = now.get(e["note_id"]) or []
            if not any(c["patch"] == e["patch"] for c in cur):
                stale.append(f"machine_auth_changed:{e['note_id']}")
        else:
            rev = repair_authorized_decision(
                run_dir, e["authority"]["review_item_id"])
            if rev is None:
                stale.append(f"human_auth_lost:{e['authority']['review_item_id']}")
            elif rev["revision_id"] != e["authority"]["revision_id"] or \
                    rev["audio_package_hash"] != \
                    e["authority"]["audio_package_hash"] or \
                    rev.get("selected_score_patch") != e["patch"]:
                stale.append(f"human_rev_superseded:{e['authority']['review_item_id']}")
    return stale


def apply_plan(run_dir: Path, plan=None, only=None, exclude=None) -> dict:
    """Consume a verified repair_plan (§6.4/§6.9). Refuses stale plans,
    writes corrected_score.json + repair_manifest.json, and re-verifies
    integrity. Candidate 0 on disk is never written."""
    run_dir = Path(run_dir)
    if plan is None:
        plan = json.loads((run_dir / REPAIR_DIRNAME / "repair_plan.json")
                          .read_text(encoding="utf-8"))
    stale = verify_freshness(run_dir, plan)
    if stale:
        raise RuntimeError(f"repair plan stale — regenerate: {stale}")
    diag = run_dir / "diagnostic"
    c0_path = diag / "baseline_game.json"
    c0_bytes_sha = _file_sha(c0_path)
    notes = json.loads(c0_path.read_text(encoding="utf-8"))["notes"]

    elig = _eligible_entries(plan, only=only, exclude=exclude)
    new_notes = apply_repairs(notes, elig)
    applied = [e["repair_id"] for e in elig]
    score = corrected_score(new_notes, applied,
                            plan["candidate0_notes_sha256"],
                            c0_file_sha=plan["candidate0_file_sha256"])

    # ---- post-apply integrity verification (§6.9): no re-adjudication
    checks = {
        "note_count_same": len(new_notes) == len(notes),
        "order_same": all(new_notes[i]["start"] == notes[i]["start"] and
                          new_notes[i]["dur"] == notes[i]["dur"]
                          for i in range(len(notes))),
        "only_target_tone_changed": True,
        "candidate0_file_unchanged": _file_sha(c0_path) == c0_bytes_sha,
    }
    touched = {_note_index(e["note_id"]) for e in elig}
    for i, (a, b) in enumerate(zip(notes, new_notes)):
        if i in touched:
            if {k: v for k, v in a.items() if k != "tone"} != \
                    {k: v for k, v in b.items() if k != "tone"}:
                checks["only_target_tone_changed"] = False
        elif a != b:
            checks["only_target_tone_changed"] = False
    if not all(checks.values()):
        raise RuntimeError(f"post-apply integrity failed: {checks}")

    rdir = run_dir / REPAIR_DIRNAME
    manifest = {
        "schema": REPAIR_SCHEMA, "created_at": _now(),
        "diagnostic_run_id": plan["diagnostic_run_id"],
        "plan_hash": plan["plan_hash"],
        "candidate0_sha256": plan["candidate0_sha256"],
        "candidate0_notes_sha256": plan.get("candidate0_notes_sha256"),
        "candidate0_file_sha256": plan.get("candidate0_file_sha256"),
        "corrected_score_sha256": score["corrected_score_sha256"],
        "applied_repairs": applied,
        "repairs": [{
            "repair_id": e["repair_id"],
            "repair_schema_version": REPAIR_SCHEMA,
            "note_id": e["note_id"], "region": e["before"],
            "before": e["before"], "after": e["after"],
            "source_type": e["source_type"],
            "authority": e["authority"],
            "provenance_refs": e.get("provenance_refs"),
            "gates_passed": ["upstream_frozen", "patch_shape",
                             "plan_freshness", "integrity"],
            "blocked_reason": e.get("blocked_reason"),
            "rollback": "rebuild from Candidate 0 + repair ids; "
                        "never derives from corrected score",
        } for e in elig],
        "integrity_checks": checks,
        "blocked": [{
            "repair_id": e["repair_id"],
            "note_id": e["note_id"],
            "source_type": e["source_type"],
            "patch_type": (e.get("patch") or {}).get("type"),
            "status": e["status"],
            "blocked_reason": e["blocked_reason"],
            "authority": e["authority"],
        } for e in plan["repairs"]
            if e["status"] not in (PATCH_OK, "deduped")],
    }
    manifest["manifest_sha256"] = _sha({k: v for k, v in manifest.items()
                                        if k not in ("manifest_sha256",
                                                     "created_at")})
    _atomic_write(rdir / "corrected_score.json", score)
    _atomic_write(rdir / "repair_manifest.json", manifest)
    return {"plan": plan, "score": score, "manifest": manifest}


# =====================================================================
# M2.5 — structure repair (plan2 §10.1): split / merge / boundary_shift
# =====================================================================

STRUCTURE_SCHEMA = "m25-1"
STRUCTURE_DIRNAME = "structure_repair"
MIN_NOTE_DUR_S = 0.05            # minimum legal child/note duration
SPAN_TOL_S = 1e-3
STRUCTURE_TYPES = ("split", "merge", "boundary_shift")


def _note_end(n) -> float:
    return float(n["start"]) + float(n["dur"])


def _affected_indices(patch, notes) -> list[int]:
    """Sorted C0 indices a structure patch touches (conflict domain)."""
    idxs = []
    for nid in patch.get("note_ids") or []:
        try:
            i = _note_index(nid)
            if 0 <= i < len(notes):
                idxs.append(i)
        except (ValueError, AttributeError):
            pass
    return sorted(set(idxs))


def _finite_tone(t) -> bool:
    return isinstance(t, (int, float)) and math.isfinite(t) \
        and MIDI_MIN <= float(t) <= MIDI_MAX


def validate_structure_patch(patch, notes) -> tuple[bool, str]:
    """§10.1.2 operation legality — verify, never re-derive. Returns
    (ok, reason). Shape/span/identity checks only; authority freshness
    is a separate gate."""
    typ = (patch or {}).get("type")
    ids = (patch or {}).get("note_ids") or []
    if typ == "split":
        if len(ids) != 1:
            return False, "not_single_note"
        idxs = _affected_indices(patch, notes)
        if len(idxs) != 1:
            return False, "note_not_in_candidate0"
        n = notes[idxs[0]]
        t0, t1 = float(n["start"]), _note_end(n)
        b = patch.get("boundary")
        ch = sorted(patch.get("children") or [],
                    key=lambda c: c["start"])
        if not isinstance(b, (int, float)) or len(ch) != 2:
            return False, "bad_split_shape"
        if not (t0 + MIN_NOTE_DUR_S <= float(b) <= t1 - MIN_NOTE_DUR_S):
            return False, "boundary_outside_span"
        # children must tile the parent span exactly at the boundary
        if abs(float(ch[0]["start"]) - t0) > SPAN_TOL_S or \
                abs(float(ch[0]["end"]) - float(b)) > SPAN_TOL_S or \
                abs(float(ch[1]["start"]) - float(b)) > SPAN_TOL_S or \
                abs(float(ch[1]["end"]) - t1) > SPAN_TOL_S:
            return False, "children_not_tiling_parent"
        for c in ch:
            if float(c["end"]) - float(c["start"]) < MIN_NOTE_DUR_S:
                return False, "child_too_short"
            if not _finite_tone(c.get("tone")):
                return False, "tone_invalid"
        return True, "ok"
    if typ == "merge":
        if len(ids) < 2:
            return False, "merge_needs_two_notes"
        idxs = _affected_indices(patch, notes)
        if len(idxs) != len(ids):
            return False, "note_not_in_candidate0"
        if idxs != list(range(idxs[0], idxs[0] + len(idxs))):
            return False, "merge_not_adjacent"
        m = patch.get("merged") or {}
        t0 = float(notes[idxs[0]]["start"])
        t1 = _note_end(notes[idxs[-1]])
        if abs(float(m.get("start", -1)) - t0) > SPAN_TOL_S or \
                abs(float(m.get("end", -1)) - t1) > SPAN_TOL_S:
            return False, "merged_span_mismatch"
        if not _finite_tone(m.get("tone")):
            return False, "tone_invalid"
        return True, "ok"
    if typ == "boundary_shift":
        if len(ids) != 1:
            return False, "not_single_note"
        idxs = _affected_indices(patch, notes)
        if len(idxs) != 1:
            return False, "note_not_in_candidate0"
        i = idxs[0]
        n = notes[i]
        after = patch.get("after") or {}
        ns = after.get("start", patch.get("start"))
        ne = after.get("end", patch.get("end"))
        if not isinstance(ns, (int, float)) or \
                not isinstance(ne, (int, float)):
            return False, "bad_shift_shape"
        ns, ne = float(ns), float(ne)
        if ne - ns < MIN_NOTE_DUR_S:
            return False, "negative_or_tiny_duration"
        if i > 0 and ns < _note_end(notes[i - 1]) - SPAN_TOL_S:
            return False, "overlaps_previous"
        if i < len(notes) - 1 and \
                ne > float(notes[i + 1]["start"]) + SPAN_TOL_S:
            return False, "overlaps_next"
        if abs(ns - float(n["start"])) < SPAN_TOL_S and \
                abs(ne - _note_end(n)) < SPAN_TOL_S:
            return False, "no_op"
        return True, "ok"
    return False, f"out_of_scope:{typ}"


def machine_structure_candidates(packets) -> list[dict]:
    """§10.1.2 machine path — only frozen `resolved_change_candidate`
    packets that pass the operation-specific precision gate. M2.5
    verifies frozen evidence fields; it never re-runs B/C or re-derives
    boundaries from raw audio."""
    from .diagnostic.structure_adj import (GAME_SPLIT_STRONG,
        MIN_SPLIT_DUR_S, NONF0_BOUNDARY_THR)
    out = []
    for p in packets:
        st = p.get("state") or {}
        if st.get("decision") != "resolved_change_candidate":
            continue
        c = p.get("structure_adjudication") or {}
        scc = p.get("structure_change_candidate") or {}
        vb = p.get("virtual_note_adjudication") or []
        sep = bool((p.get("separation") or {})
                   .get("separation_sensitive")) \
            or st.get("separation_state") == "sensitive"
        # identity-safe child mapping: every virtual child resolved by
        # frozen B with a finite winner — never an acoustic-seed guess
        vb_ok = bool(vb) and all(
            (v.get("status") or "").startswith("resolved")
            and _finite_tone(v.get("winning_hypothesis"))
            for v in vb)
        if sep or not vb_ok or \
                c.get("status") != "resolved_change_candidate":
            continue
        kind = scc.get("kind")
        patch, gate_detail = None, {}
        if kind == "split":
            ee = c.get("extractor_evidence") or {}
            be = c.get("boundary_evidence") or {}
            gs = c.get("game_structure") or {}
            dual = bool(ee.get("dual_delta_agreement"))
            nonf0 = float(be.get("non_f0_support") or 0.0)
            gsplit = float(gs.get("split_ratio") or 0.0)
            # boundary confidence = the frozen split gate itself
            boundary_conf = (
                (gsplit >= GAME_SPLIT_STRONG
                 and (dual or nonf0 > NONF0_BOUNDARY_THR))
                or (dual and nonf0 > NONF0_BOUNDARY_THR))
            chs = sorted(scc.get("notes") or [], key=lambda x: x["start"])
            dur_ok = bool(chs) and all(
                float(ch["end"]) - float(ch["start"]) >= MIN_SPLIT_DUR_S
                for ch in chs)
            gate_detail = {"dual_delta_agreement": dual,
                           "non_f0_support": nonf0,
                           "game_split_ratio": gsplit}
            if not (boundary_conf and dur_ok and len(chs) == len(vb)
                    and c.get("classification") == "TRUE_SPLIT_CANDIDATE"):
                continue
            children = [{"start": float(ch["start"]),
                         "end": float(ch["end"]),
                         "tone": float(v["winning_hypothesis"])}
                        for ch, v in zip(chs, vb)]
            patch = {"type": "split", "note_ids": [p["id"]],
                     "boundary": float(scc["boundary"]),
                     "children": children}
        elif kind == "merge":
            span = scc.get("span") or {}
            if not (c.get("classification") == "TRUE_MERGE_CANDIDATE"
                    and len(vb) == 1 and span.get("merge_with")):
                continue
            patch = {"type": "merge",
                     "note_ids": [p["id"], span["merge_with"]],
                     "merged": {"start": float(span["start"]),
                                "end": float(span["end"]),
                                "tone": float(
                                    vb[0]["winning_hypothesis"])}}
        else:
            continue
        out.append({
            "source_type": "machine_structure",
            "note_id": p["id"], "patch": patch,
            "authority": {
                "packet_id": p["id"],
                "c_status": c.get("status"),
                "classification": c.get("classification"),
                "virtual_b_statuses": [v.get("status") for v in vb],
                "child_presence": [
                    (v.get("correspondence") or {})
                    .get("child_presence_rate") for v in vb],
                **gate_detail}})
    return out


def structure_human_candidates(run_dir: Path) -> list[dict]:
    """§10.1.1: the M2.4-preserved human structure authority — same
    repair_authorized_decision() snapshot, filtered to structure ops.
    The user already heard the exact package; no re-review needed, but
    shape/legality/freshness are still verified."""
    return [c for c in human_candidates(run_dir)
            if (c["patch"] or {}).get("type") in STRUCTURE_TYPES]


def _structure_before_after(patch, notes):
    idxs = _affected_indices(patch, notes)
    before = [{"start": float(notes[i]["start"]),
               "end": _note_end(notes[i]),
               "tone": float(notes[i]["tone"])} for i in idxs]
    typ = patch["type"]
    if typ == "split":
        after = [{"start": c["start"], "end": c["end"],
                  "tone": c["tone"]}
                 for c in sorted(patch["children"],
                                 key=lambda c: c["start"])]
    elif typ == "merge":
        m = patch["merged"]
        after = [{"start": m["start"], "end": m["end"],
                  "tone": m["tone"]}]
    else:
        a = patch.get("after") or {}
        after = [{"start": a.get("start", patch.get("start")),
                  "end": a.get("end", patch.get("end")),
                  "tone": before[0]["tone"]}]
    return before, after


def _structure_repair_id(run_id, c0_sha, cand, notes) -> str:
    return "srp-" + _sha({
        "schema": STRUCTURE_SCHEMA,
        "run_id": run_id, "candidate0_sha256": c0_sha,
        "source_type": cand["source_type"],
        "authority_id": (cand["authority"].get("revision_id")
                         or cand["authority"].get("packet_id")),
        "note_id": cand["note_id"],
        "affected": _affected_indices(cand["patch"], notes),
        "patch_sha": _sha(cand["patch"])[:16]})[:24]


def build_structure_plan(run_dir: Path, *, run_id=None, packets=None,
                         notes=None, triage_sha=None, song_sha256=None,
                         write=True) -> dict:
    """§10.1.3 read-only structure planning. Same fail-closed bindings
    as M2.4 (schema + dual C0 hash + triage hash + human revisions)."""
    run_dir = Path(run_dir)
    run_id = run_id or run_dir.name
    c0_path = run_dir / "diagnostic" / "baseline_game.json"
    if packets is None or notes is None:
        diag = run_dir / "diagnostic"
        packets = json.loads((diag / "residual_triage.json")
                             .read_text(encoding="utf-8"))
        notes = json.loads(c0_path.read_text(encoding="utf-8"))["notes"]
        triage_sha = _file_sha(diag / "residual_triage.json")
        if song_sha256 is None:
            rep = json.loads((run_dir / "report.json")
                             .read_text(encoding="utf-8"))
            song_sha256 = rep["cache"]["source_sha256"]
    if not c0_path.exists():
        raise FileNotFoundError(
            f"{c0_path} missing — cannot bind the exact Candidate-0 "
            "artifact; refusing to build a structure plan")
    c0_sha = _sha(notes)
    c0_file_sha = _file_sha(c0_path)

    cands = (machine_structure_candidates(packets)
             + structure_human_candidates(run_dir))
    entries, per_key = [], {}
    for c in cands:
        idxs = _affected_indices(c["patch"], notes)
        ok, why = validate_structure_patch(c["patch"], notes) \
            if idxs else (False, "note_not_in_candidate0")
        before, after = (_structure_before_after(c["patch"], notes)
                         if ok else (None, None))
        e = {"repair_id": _structure_repair_id(run_id, c0_sha, c, notes),
             "note_id": c["note_id"], "source_type": c["source_type"],
             "affected": idxs, "patch": c["patch"],
             "authority": c["authority"],
             "before": before, "after": after,
             "status": PATCH_OK if ok else REJECTED,
             "blocked_reason": None if ok else why}
        entries.append(e)
        per_key.setdefault(tuple(idxs), []).append(e)

    # conflict policy: identical patches on the same note set dedupe;
    # different patches on the same note set block — no precedence.
    for key, group in per_key.items():
        elig = [e for e in group if e["status"] == PATCH_OK]
        if len(elig) <= 1:
            continue
        sigs = {_sha(e["patch"]) for e in elig}
        if len(sigs) == 1:
            keep = elig[0]
            keep["provenance_refs"] = [e["authority"] for e in elig[1:]]
            for e in elig[1:]:
                e["status"] = "deduped"
                e["blocked_reason"] = \
                    f"duplicate_of:{keep['repair_id']}"
        else:
            for e in elig:
                e["status"] = BLOCKED_CONFLICT
                e["blocked_reason"] = "conflicting_structure_patches"
    # cross-entry overlap: an eligible op must not share notes with a
    # different eligible op on another note set
    seen = {}
    for e in [e for e in entries if e["status"] == PATCH_OK]:
        for i in e["affected"]:
            other = seen.get(i)
            if other is not None and \
                    other["repair_id"] != e["repair_id"]:
                for x in (e, other):
                    x["status"] = BLOCKED_CONFLICT
                    x["blocked_reason"] = "overlapping_affected_notes"
            else:
                seen[i] = e

    plan = {
        "schema": STRUCTURE_SCHEMA,
        "created_at": _now(),
        "diagnostic_run_id": run_id,
        "candidate0_sha256": c0_sha,
        "candidate0_notes_sha256": c0_sha,
        "candidate0_file_sha256": c0_file_sha,
        "song_sha256": song_sha256,
        "bindings": {
            "residual_triage_sha256": triage_sha,
            "candidate0_notes_sha256": c0_sha,
            "candidate0_file_sha256": c0_file_sha,
            "review_authority": {"schema": "d3",
                                 "identity_schema":
                                 "review-target-v1"},
            "human_revisions": {e["authority"]["review_item_id"]: {
                "revision_id": e["authority"]["revision_id"],
                "audio_package_hash":
                e["authority"]["audio_package_hash"],
            } for e in entries if e["source_type"] == "human_selected"},
        },
        "repairs": entries,
        "summary": {},
    }
    for e in entries:
        plan["summary"][e["status"]] = \
            plan["summary"].get(e["status"], 0) + 1
    plan["plan_hash"] = canonical_plan_hash(plan)
    if write:
        _atomic_write(run_dir / STRUCTURE_DIRNAME
                      / "structure_plan.json", plan)
    return plan


def apply_structure_ops(notes, entries) -> list:
    """Deterministic copy-on-write structure apply: split expands to
    children, merge collapses adjacent notes, boundary_shift re-spans.
    `notes` is never mutated."""
    ops = {e["affected"][0]: e for e in entries}
    out = []
    i = 0
    while i < len(notes):
        e = ops.get(i)
        if e is None:
            out.append(dict(notes[i]))
            i += 1
            continue
        p, n = e["patch"], notes[i]
        typ = p["type"]
        if typ == "split":
            for c in sorted(p["children"], key=lambda c: c["start"]):
                out.append({"start": float(c["start"]),
                            "dur": float(c["end"]) - float(c["start"]),
                            "tone": float(c["tone"]),
                            "voiced": n.get("voiced", True)})
            i += 1
        elif typ == "merge":
            m = p["merged"]
            out.append({"start": float(m["start"]),
                        "dur": float(m["end"]) - float(m["start"]),
                        "tone": float(m["tone"]),
                        "voiced": n.get("voiced", True)})
            i += len(p["note_ids"])
        elif typ == "boundary_shift":
            a = p.get("after") or {}
            ns = float(a.get("start", p.get("start")))
            ne = float(a.get("end", p.get("end")))
            out.append(dict(n, start=ns, dur=ne - ns))
            i += 1
        else:
            i += 1
    return out


def apply_structure_plan(run_dir: Path, plan=None, only=None,
                         exclude=None) -> dict:
    """§10.1.3 apply — same freshness/integrity contract as M2.4."""
    run_dir = Path(run_dir)
    if plan is None:
        plan = json.loads((run_dir / STRUCTURE_DIRNAME
                           / "structure_plan.json")
                          .read_text(encoding="utf-8"))
    stale = verify_freshness(
        run_dir, plan, schema=STRUCTURE_SCHEMA,
        machine_adapter=machine_structure_candidates)
    if stale:
        raise RuntimeError(
            f"structure plan stale — regenerate: {stale}")
    diag = run_dir / "diagnostic"
    c0_path = diag / "baseline_game.json"
    c0_bytes_sha = _file_sha(c0_path)
    notes = json.loads(c0_path.read_text(encoding="utf-8"))["notes"]

    elig = _eligible_entries(plan, only=only, exclude=exclude)
    new_notes = apply_structure_ops(notes, elig)
    applied = [e["repair_id"] for e in elig]
    score = corrected_score(new_notes, applied,
                            plan["candidate0_notes_sha256"],
                            c0_file_sha=plan["candidate0_file_sha256"])

    # post-apply integrity: monotonic non-overlapping spans, positive
    # durations, every untouched C0 note present verbatim, C0 file
    # untouched
    touched = set()
    for e in elig:
        touched.update(e["affected"])
    checks = {
        "monotonic_spans": all(
            new_notes[i]["start"] + new_notes[i]["dur"]
            <= new_notes[i + 1]["start"] + SPAN_TOL_S
            for i in range(len(new_notes) - 1)),
        "positive_durations": all(n["dur"] > 0 for n in new_notes),
        "non_target_unchanged": all(
            orig in new_notes for i, orig in enumerate(notes)
            if i not in touched),
        "candidate0_file_unchanged":
            _file_sha(c0_path) == c0_bytes_sha,
    }
    if not all(checks.values()):
        raise RuntimeError(f"post-apply integrity failed: {checks}")

    rdir = run_dir / STRUCTURE_DIRNAME
    manifest = {
        "schema": STRUCTURE_SCHEMA, "created_at": _now(),
        "diagnostic_run_id": plan["diagnostic_run_id"],
        "plan_hash": plan["plan_hash"],
        "candidate0_sha256": plan["candidate0_sha256"],
        "candidate0_notes_sha256": plan["candidate0_notes_sha256"],
        "candidate0_file_sha256": plan["candidate0_file_sha256"],
        "corrected_score_sha256": score["corrected_score_sha256"],
        "applied_repairs": applied,
        "repairs": [{
            "repair_id": e["repair_id"],
            "repair_schema_version": STRUCTURE_SCHEMA,
            "note_id": e["note_id"], "affected": e["affected"],
            "operation": e["patch"]["type"],
            "before": e["before"], "after": e["after"],
            "source_type": e["source_type"],
            "authority": e["authority"],
            "provenance_refs": e.get("provenance_refs"),
            "gates_passed": ["upstream_frozen", "operation_legality",
                             "plan_freshness", "integrity"],
            "blocked_reason": e.get("blocked_reason"),
            "rollback": "rebuild from Candidate 0 + repair ids; "
                        "never derives from corrected score",
        } for e in elig],
        "integrity_checks": checks,
        "blocked": [{
            "repair_id": e["repair_id"], "note_id": e["note_id"],
            "source_type": e["source_type"],
            "patch_type": (e.get("patch") or {}).get("type"),
            "status": e["status"],
            "blocked_reason": e["blocked_reason"],
            "authority": e["authority"],
        } for e in plan["repairs"]
            if e["status"] not in (PATCH_OK, "deduped")],
    }
    manifest["manifest_sha256"] = _sha(
        {k: v for k, v in manifest.items()
         if k not in ("manifest_sha256", "created_at")})
    _atomic_write(rdir / "structure_corrected_score.json", score)
    _atomic_write(rdir / "structure_manifest.json", manifest)
    return {"plan": plan, "score": score, "manifest": manifest}
