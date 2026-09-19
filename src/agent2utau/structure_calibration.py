"""M2.5 Blocker E — machine structure precision calibration (plan2 §10.1.5).

A machine `TRUE_SPLIT_CANDIDATE`/`TRUE_MERGE_CANDIDATE` is frozen evidence,
not repair truth. Before any machine structure candidate may enter the
trusted corrected score it must survive a phrase-level A/B calibration:
the human hears SOURCE context plus a blind Baseline-vs-Candidate pair
(same phrase window, same singer/tempo/renderer/gain, identical score
outside the target) and picks one of four outcomes:

  split/baseline preferred / equivalent / none_correct
  → human_confirmed_machine_split / machine_structure_false_positive /
    no_demonstrated_benefit / unresolved (manual_followup)

Only `human_confirmed_machine_split` authorizes apply — recorded in
runs/<diag>/structure_calibration/decisions.json, bound to the exact
repair_id + patch_sha + audio_package_hash. Reuses the D render machinery
(phrase_window, blind options, shared-gain option renders, provenance)
but keeps its own store: calibration semantics ≠ phrase-review semantics.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

CALIB_SCHEMA = "m25-cal-2"
CALIB_DIRNAME = "structure_calibration"
LEGACY_DIRNAMES = ("structure_calibration_m25cal1_audit",)
LYRIC_CONTRACT = "neutral_vowel"
# §10.1.5A-G5E quality hold: full-phrase human review needs REAL lyric
# semantics — a review-only overlay from source-bound force_align
# chars; still not the M2.7 trusted lyric mapping.
LYRIC_CONTRACT_REVIEW = "real_lyric_review"
# §10.1.5A-G5G Blocker B: the lyric-mapping implementation is part of
# the render-contract IDENTITY — a semantic change to carrier/gap/
# continuation/fail-closed rules MUST stale every artifact rendered
# under the old semantics (old contract_sha256 != new → mandatory
# rebuild). Bump the relevant version whenever the mapping semantics
# change; never reuse an older version's meaning.
LYRIC_MAPPING_IMPL_VERSION = {
    "neutral_vowel": "nv1",
    # v4 (G5J): acoustic closed-loop — render-only articulation
    # anchors are re-estimated from rendered-vocal re-alignment
    # (measured onset error feeds back, k<1 + clamps + monotonic),
    # low-confidence rendered alignments fail closed, SOURCE phrase
    # windows expand to cover first/last char articulation; v3:
    # source-bound articulation splits (chars could still land early
    # vs measured acoustic onset); v2: gap fail-closed; v1: 'a'
    # v5: the loop/QC instrument switched from whisper force_align to
    # onset-strength envelope peaks — whisper-on-synthetic was found
    # to mis-assign char boundaries ~200-500ms EARLY into the previous
    # syllable's tail (whisper-on-source ≈ accurate), so a whisper-vs-
    # whisper loop drove anchors ~200ms genuinely LATE. One acoustic
    # instrument on both sides cancels detector bias by construction.
    # v6 (G5K): hard-case timing semantics — every char routes as
    # class_A (reliable landmark + carrier-feasible correction) /
    # B1_unmeasurable (no stable acoustic landmark — evidence
    # unavailable, fail-closed or second-family adjudication) /
    # B2_carrier_conflict (source onset outside the legal carrier
    # range — the review overlay may NEVER rewrite written-score
    # timing to reach it). Whisper confidence splits into
    # intelligibility (ASR diction) vs acoustic timing measurability.
    # v7 (G5L): directional carrier conflicts (early→preutterance /
    # late→post-boundary-delay|written-timing — never conflated), the
    # 120ms overhang line demoted to a triage prior, post-loop render
    # failures downgrade to explicit B1 subtypes (render_unmeasurable /
    # cross_option_unstable / detector_relock), second-family evidence
    # only adjudicates measurability (never averaged), and a B2 set
    # repeating across targets marks phrase_level_carrier_conflict.
    "real_lyric_review": "rlv7",
}
MIN_REVIEW_CHAR_PROB = 0.25   # fail-closed below this char confidence
MIN_TIMING_CHAR_PROB = 0.30   # rendered char ASR confidence below
                              # this = lyric intelligibility concern
                              # (§G5K: diction clarity, NOT acoustic
                              # timing truth — kept as separate flag)
LYRIC_PHRASE_LEAD_PAD_S = 0.15   # §G5J-A: phrase window must cover
LYRIC_PHRASE_TAIL_PAD_S = 0.15   # first/last char articulation
LOOP_K = 0.7                  # §G5J: anchor feedback gain (<1)
LOOP_CLAMP_S = 0.15           # max anchor shift per iteration
LOOP_MAX_ITERS = 4            # renders after the initial pass
LOOP_TOL_MS = 80.0            # convergence: max |shared onset error|
TIMING_GATE_MS = 120.0        # §G5J: QC gate — max |acoustic onset
                            # delta| above this fails; score_delta≈0
                            # can never mask a measured acoustic miss
ONSET_PEAK_DELTA = 0.4        # §G5J-rlv5: onset_strength peak_pick
ONSET_PEAK_WAIT = 8           # prominence / min-distance (frames)
ONSET_REF_WIN_S = 0.35        # source ref: peak must sit within this
                            # of the whisper-measured char position
ONSET_MEAS_BACK_S = 0.15      # render onset search back-window —
                            # phoneme anticipation can voice a
                            # consonant before its note start
ONSET_MEAS_FWD_S = 0.22       # forward window — vowel attack lands
                            # at/after the commanded segment start;
                            # a peak farther than this is a different
                            # event, not this char's onset
ONSET_XOPT_DISAGREE_S = 0.15  # same anchor, same instrument: two
                            # options disagreeing more than this on
                            # one char's onset means at least one
                            # peak is a mis-assignment — unmeasurable
ONSET_FLIP_S = 0.15           # measured onset jumping more than this
ONSET_FLIP_ANCH_S = 0.05      # while its anchor moved less than this
                            # is an artifact, not a real onset move
ONSET_MIN_GAP_S = 0.06        # two chars can't share one peak
ANTICIPATION_MAX_S = 0.12     # §G5L: TRIAGE PRIOR ONLY — an overhang
                            # within this names a candidate hypothesis
                            # (preutterance / post-boundary delay),
                            # beyond it suspects written timing. It is
                            # never a final adjudication authority:
                            # direction, phoneme context, neighbour
                            # timing and cross-target repetition are
                            # the real evidence.
ROUTE_CLASS_A = "class_A"
ROUTE_B1 = "B1_unmeasurable"
ROUTE_B2 = "B2_carrier_conflict"
MIN_USABLE_SEG_S = 0.12       # §G5J: an anchor update that would
                            # squeeze a char below this sung duration
                            # is bound-limited — held at the usable
                            # edge and reported, never a 30ms blip
                            # whose 'measurement' is another landmark
ARTICULATE_MIN_SEG_S = 0.03   # shortest legal render segment
CHOICES = ("split", "baseline", "equivalent", "none_correct")
OUTCOME = {"split": "human_confirmed_machine_split",
           "baseline": "machine_structure_false_positive",
           "equivalent": "no_demonstrated_benefit",
           "none_correct": "unresolved"}


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _sha(obj) -> str:
    if isinstance(obj, (dict, list)):
        obj = _canon(obj).encode("utf-8")
    return hashlib.sha256(obj).hexdigest()


def _jwrite(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)


def _now() -> float:
    return time.time()


def calib_dir(run_dir: Path) -> Path:
    return Path(run_dir) / CALIB_DIRNAME


def ensure_calib_authority(run_dir: Path):
    """Fail-closed schema gate (§10.1.5A-G1): any store whose
    plan/decisions/state files are not schema m25-cal-2 is a legacy
    review artifact — rename the whole directory to an audit name
    (never overwrite) and start a clean m25-cal-2 authority. Old
    packages/decisions keep existing only as regression evidence;
    they can never authorize repair again."""
    cdir = calib_dir(run_dir)
    if not cdir.exists():
        return
    bad = False
    for name in ("plan.json", "decisions.json", "state.json"):
        p = cdir / name
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                bad = True
                break
            if d.get("schema") != CALIB_SCHEMA:
                bad = True
                break
    if not bad:
        return
    import time as _t
    base = run_dir / LEGACY_DIRNAMES[0]
    dest = base
    if dest.exists():
        dest = run_dir / f"{LEGACY_DIRNAMES[0]}_" \
            f"{_t.strftime('%Y%m%d-%H%M%S')}"
    cdir.replace(dest)
    cdir.mkdir(parents=True, exist_ok=True)


def cal_item_id(repair_id: str) -> str:
    """Stable calibration item identity = the repair identity itself —
    same patch content → same id across re-plans."""
    return "cal-" + str(repair_id)


# ------------------------------------------------------------ plan (pure)

def plan_calibration(run, packets=None, notes=None, rph=None,
                     lyric_contract=None):
    """Pure: machine structure candidates → review-shaped cal items.

    Each item carries the exact patch the repair engine would apply,
    a blinded [baseline, candidate] option pair and a phrase window —
    same window/singer/renderer/gain for both options (§10.1.5 UX).
    Deterministic: rebuilt from the same frozen artifacts the repair
    plan binds, so repair_id/patch match plan entries exactly.
    """
    from .repair import (machine_structure_candidates,
                         _structure_repair_id, _sha as rsha)
    from .review.build import (assign_identity, blind_order,
                               context_notes, phrase_window, plan_hash,
                               render_profile, render_profile_hash)
    packets = packets if packets is not None else run["packets"]
    notes = notes if notes is not None else run["baseline_notes"]
    c0_sha = rsha(notes)
    if rph is None:
        rph = render_profile_hash(render_profile())
    items = []
    for c in machine_structure_candidates(packets):
        patch = c["patch"]
        rid = _structure_repair_id(run["run_id"], c0_sha, c, notes)
        iid = cal_item_id(rid)
        typ = patch["type"]
        if typ == "split":
            region = [patch["children"][0]["start"],
                      patch["children"][-1]["end"]]
        elif typ == "merge":
            region = [patch["merged"]["start"], patch["merged"]["end"]]
        else:  # boundary_shift — single note span after shift
            a = patch.get("after") or {}
            region = [a.get("start", patch.get("start")),
                      a.get("end", patch.get("end"))]
        item = {
            "type": typ, "parent_ids": list(patch["note_ids"]),
            "note_ids": list(patch["note_ids"]),
            "region": [float(region[0]), float(region[1])],
            "packets": [c["note_id"]],
            "boundary": patch.get("boundary"),
            "reason": f"machine_{typ}_calibration",
            "repair_id": rid, "patch": patch,
            "authority": c["authority"],
            # m25-cal-2 (§10.1.5A-G2): default is no lyric guessing —
            # deterministic a/+ vowels; the G5E review overlay uses
            # real_lyric_review with source-bound force_align chars.
            "lyric_contract": lyric_contract or LYRIC_CONTRACT,
        }
        assign_identity(item)                 # target_key + item_id
        item["item_id"] = iid                 # cal-namespaced stable id
        win = phrase_window(item["region"], run["duration"], notes,
                            run.get("lrc_lines"), run.get("silences"))
        # a note may overlap the left window edge by < NO_CUT_TOL_S —
        # context_notes keeps it (its end is inside) and its relative
        # start would go negative at render time ("precedes part
        # anchor"). Back the edge up to the earliest overlapped start;
        # nothing is ever cut, context stays identical across options.
        for _ in range(4):
            ctx = context_notes(notes, win)
            early = [n["start"] for n in ctx
                     if n["start"] < win["start"] - 1e-9]
            if not early:
                break
            win = dict(win, start=round(min(early), 3))
        if item["lyric_contract"] == LYRIC_CONTRACT_REVIEW:
            # §10.1.5A-G5J-A: the LRC boundary alone truncated lyric
            # articulation — the first source char started ~80–130ms
            # before phrase.start on every pilot item. The review
            # window must cover first_char.start - lead_pad and
            # last_char.end + tail_pad. Char evidence is selected on
            # the ORIGINAL lrc window (evidence_window) so expansion
            # can't pull a neighbouring line's char in; expansion is
            # clamped to the neighbouring note gap (never cut a note).
            item["evidence_window"] = dict(win)
            ev = review_phrase_chars(run, win)
            if ev["ok"]:
                first_s = min(c["start"] for c in ev["chars"])
                last_e = max(c["end"] for c in ev["chars"])
                lead = first_s - LYRIC_PHRASE_LEAD_PAD_S
                tail = last_e + LYRIC_PHRASE_TAIL_PAD_S
                ns = max(0.0, min(win["start"], lead))
                ne = min(run["duration"], max(win["end"], tail))
                # padding may only cross a neighbouring note when the
                # CHAR itself reaches into that note — a pad that
                # merely dips inside one would drag a carrier the
                # first/last char never uses into context (and break
                # the first-carrier binding). Clamp at the note edge:
                # it is a natural phrase boundary anyway.
                for n in notes:
                    n_s = n["start"]
                    n_e = n.get("end") or n_s + n["dur"]
                    if n_e <= min(first_s, win["start"] + 1e-9):
                        ns = max(ns, n_e)
                    if n_s >= max(last_e, win["end"] - 1e-9):
                        ne = min(ne, n_s)
                ns, ne = round(ns, 3), round(ne, 3)
                if ns < win["start"] - 1e-9 or \
                        ne > win["end"] + 1e-9:
                    win = dict(win, start=ns, end=ne,
                               boundary_source="lrc+lyric_pad")
                    # the pad may land INSIDE a neighbouring note —
                    # extend to its full span on either side so no
                    # note (and no lyric articulation it carries) is
                    # ever cut by the review window
                    for _ in range(6):
                        ctx = context_notes(notes, win)
                        early = [n["start"] for n in ctx
                                 if n["start"] < win["start"] - 1e-9]
                        late = [n["end"] for n in ctx
                                if n["end"] > win["end"] + 1e-9]
                        if not early and not late:
                            break
                        win = dict(
                            win,
                            start=round(min(early), 3) if early
                            else win["start"],
                            end=round(min(max(late),
                                          run["duration"]), 3)
                            if late else win["end"])
        item["phrase"] = win
        item["phrase_key"] = f"{win['start']:.2f}-{win['end']:.2f}"
        ctx = context_notes(notes, win)
        opts = blind_order([
            {"candidate_id": "baseline",
             "score_patch": {"type": "identity"},
             "provenance": {"kind": "candidate0"}},
            {"candidate_id": f"machine_{typ}",
             "score_patch": patch,
             "provenance": {"kind": "machine_structure_candidate",
                            "repair_id": rid,
                            "authority": c["authority"]}},
        ], iid)
        item["options"] = opts
        item["context"] = ctx
        item["context_note_ids"] = [n["id"] for n in ctx]
        item["baseline_option"] = next(
            o["option_id"] for o in opts
            if o["candidate_id"] == "baseline")
        item["generation"] = 1
        item["plan_hash"] = plan_hash(
            iid, run["song_sha256"], run["run_id"], c0_sha, win,
            item["context_note_ids"], opts, rph,
            target_key_=item["target_key"])
        items.append(item)
    return items


# ------------------------------------------------------------- render IO

def render_contract_sha(run, rph_hash: str,
                        lyric_contract: str = None) -> str:
    """Identity of the review-render contract (§10.1.5A-G2/G5G-B):
    schema + lyric contract + lyric-mapping impl version + render
    profile. A material renderer OR lyric-mapping change → a different
    contract → previous artifacts/QC verdicts no longer apply."""
    contract = lyric_contract or LYRIC_CONTRACT
    return _sha({"schema": CALIB_SCHEMA,
                 "lyric_contract": contract,
                 "lyric_mapping_impl":
                     LYRIC_MAPPING_IMPL_VERSION[contract],
                 "render_profile_hash": rph_hash})


def item_contract_stale(man: dict, run, rph_hash: str) -> bool:
    """True when the item's recorded contract_sha256 no longer matches
    the contract the CURRENT code computes for its lyric_contract —
    e.g. a real_lyric_review package rendered under rlv1 ('a' allowed)
    is stale under rlv2 (gap fail-closed) even if its bytes exist."""
    contract = man.get("calibration", {}).get("lyric_contract")
    recorded = man.get("calibration", {}).get("contract_sha256")
    if not contract or not recorded:
        return True
    return recorded != render_contract_sha(run, rph_hash, contract)


def review_phrase_chars(run, win):
    """§10.1.5A-G5E evidence gate for the real-lyric review overlay:
    force_align chars bound to the source recording inside the phrase
    window. Returns {ok, chars, reason, min_probability, n_chars} —
    callers must fail-closed on ok=False (no guessing, no package)."""
    chars = [c for c in (run.get("chars") or [])
             if c["start"] < win["end"] and c["end"] > win["start"]]
    probs = [float(c.get("probability") or 0.0) for c in chars]
    if not chars:
        return {"ok": False, "chars": None, "reason": "no_chars",
                "min_probability": None, "n_chars": 0}
    mp = min(probs)
    if mp < MIN_REVIEW_CHAR_PROB:
        return {"ok": False, "chars": None,
                "reason": "low_confidence",
                "min_probability": round(mp, 3), "n_chars": len(chars)}
    return {"ok": True, "chars": chars, "reason": None,
            "min_probability": round(mp, 3), "n_chars": len(chars)}


# ------------------------------------------------------------- QC verdict

def _load_run(run_dir):
    from .review.render import load_run
    return load_run(run_dir)


def _verify_package(man, item_dir):
    from .review.render import verify_package
    return verify_package(man, item_dir)


def pilot_authority(run_dir: Path, sample_ids=None,
                    expected_lyric_contract="real_lyric_review") -> dict:
    """§10.1.5A-G5H: the human-review authority contract derives from
    the EXACT sample set — never from plan.json's store-level default
    contract. Every sample must exist under the current schema, share
    ONE contract_sha256 + lyric_contract + impl, be non-stale under the
    current implementation, have signal_qc.auto_review_ready, and pass
    verify_package. Non-raising report — callers decide whether a
    violation refuses a PASS (write_verdict) or just blocks readiness
    (review_ready / state)."""
    run_dir = Path(run_dir)
    cdir = calib_dir(run_dir)
    plan_p = cdir / "plan.json"
    plan = json.loads(plan_p.read_text(encoding="utf-8")) \
        if plan_p.exists() else {"items": []}
    by_iid = {it["cal_item_id"]: it for it in plan.get("items", [])
              if it.get("cal_item_id")}
    by_note = {it["note_id"]: it for it in plan.get("items", [])
               if it.get("note_id")}
    violations = []
    if sample_ids is None:
        sample_ids = [by_note[n]["cal_item_id"] for n in PILOT_NOTE_IDS
                      if n in by_note]
    resolved, note_ids = [], []
    for tok in sample_ids:
        it = by_iid.get(tok) or by_note.get(tok)
        if it is None:
            violations.append(f"unknown sample {tok}")
            continue
        resolved.append(it["cal_item_id"])
        note_ids.append(it["note_id"])
    if not resolved:
        violations.append("no resolvable samples")
    contracts, lyr_contracts, impls = set(), set(), set()
    aphs = {}
    run, rph = None, None
    for iid in resolved:
        mp = _find_manifest(run_dir, iid)
        if mp is None:
            violations.append(f"{iid}: manifest missing")
            continue
        man = json.loads(mp.read_text(encoding="utf-8"))
        if man.get("schema") != CALIB_SCHEMA:
            violations.append(f"{iid}: schema {man.get('schema')}")
            continue
        cal = man.get("calibration") or {}
        contracts.add(cal.get("contract_sha256"))
        lyr_contracts.add(cal.get("lyric_contract"))
        impls.add(cal.get("lyric_mapping_impl"))
        if cal.get("lyric_contract") != expected_lyric_contract:
            violations.append(
                f"{iid}: lyric_contract={cal.get('lyric_contract')}"
                f" != {expected_lyric_contract}")
        if cal.get("lyric_mapping_impl") != \
                LYRIC_MAPPING_IMPL_VERSION.get(expected_lyric_contract):
            violations.append(
                f"{iid}: lyric_mapping_impl="
                f"{cal.get('lyric_mapping_impl')}")
        if run is None:
            try:
                run = _load_run(run_dir)
                rph = _rph_hash()
            except Exception as e:
                run, rph = False, str(e)
        if run is False:
            violations.append(
                f"{iid}: staleness unevaluable ({rph})")
        elif item_contract_stale(man, run, rph):
            violations.append(f"{iid}: stale contract")
        sq_p = mp.parent / "signal_qc.json"
        sq = json.loads(sq_p.read_text(encoding="utf-8")) \
            if sq_p.exists() else {}
        if not sq.get("auto_review_ready"):
            violations.append(f"{iid}: auto_review_ready not true")
        try:
            ok, why = _verify_package(man, mp.parent)
        except Exception as e:
            ok, why = False, str(e)
        if not ok:
            violations.append(f"{iid}: verify_package {why}")
        aphs[iid] = man.get("audio_package_hash")
    if len(contracts) > 1:
        violations.append("mixed sample contract_sha256")
    if len(lyr_contracts) > 1 or len(impls) > 1:
        violations.append("mixed sample lyric contract/impl")
    one = lambda s: next(iter(s)) if len(s) == 1 else None
    return {"ok": not violations, "violations": violations,
            "sample_ids": resolved, "note_ids": note_ids,
            "contract_sha256": one(contracts),
            "lyric_contract": one(lyr_contracts),
            "lyric_mapping_impl": one(impls),
            "audio_package_hashes": aphs}


def _pilot_payload_sha(run_dir: Path):
    p = calib_dir(run_dir) / "pilot_review.json"
    return _file_sha_local(p) if p.exists() else None


def _verdict_path(run_dir: Path) -> Path:
    return calib_dir(run_dir) / "qc" / "verdict.json"


def load_verdict(run_dir: Path):
    p = _verdict_path(run_dir)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return d if d.get("schema") == CALIB_SCHEMA else None


def review_ready(run_dir: Path) -> bool:
    """§10.1.5A-G9 + G5H: review-readiness defaults false and is set
    only by an explicit pre-human QC PASS whose bound pilot identity —
    exact sample set, shared contract, pilot payload hash, per-sample
    audio_package_hash — still verifies AND whose required artifacts
    (including the qc files themselves) are committed to Git. Any
    roster/contract/package/payload change stales the verdict."""
    v = load_verdict(run_dir)
    if not (v and v.get("verdict") == "PASS"
            # recorded under the Git-evidence regime — a verdict
            # written before this rule existed never counts
            and (v.get("git_evidence_at_record") or {}).get("complete")):
        return False
    pilot = v.get("pilot") or {}
    if not pilot.get("sample_ids"):
        # pre-G5H verdicts bound the store-level default contract —
        # they carry no per-sample authority and can never count
        return False
    if _pilot_payload_sha(run_dir) != pilot.get("pilot_payload_sha256"):
        return False
    cur = pilot_authority(run_dir, pilot["sample_ids"])
    if not cur["ok"]:
        return False
    if (cur["contract_sha256"] != pilot.get("contract_sha256")
            or cur["audio_package_hashes"]
            != pilot.get("audio_package_hashes")):
        return False
    # §10.1.5A-G5G Blocker C: a lying plan (stale fields vs manifests)
    # can never be review-ready regardless of the verdict
    if not plan_invariants(run_dir)["ok"]:
        return False
    ev = git_evidence(run_dir, item_ids=pilot["sample_ids"],
                      include_qc=True)
    return bool(ev["complete"])


def write_verdict(run_dir: Path, verdict: str, contract_sha: str = None,
                  auditor: str = "", notes: str = "",
                  sample_ids=None,
                  require_git_evidence: bool = True) -> dict:
    """Record the pre-human QC verdict (append-only audit trail).
    §10.1.5A-G5H: a PASS must name its exact sample set — the bound
    contract is DERIVED from the sample manifests (shared
    contract_sha256 + lyric_contract + impl, non-stale, auto-ready,
    verify_package PASS), never from the plan-level default. The
    verdict also binds the current pilot_review.json hash and every
    sample's audio_package_hash so any later change stales it. A PASS
    is refused unless the sample packages + plan/state it covers are
    already committed to Git — the verdict then only takes effect
    (review_ready) after the qc files themselves are committed too."""
    run_dir = Path(run_dir)
    is_pass = verdict.upper() == "PASS"
    pilot = None
    if is_pass:
        if not sample_ids:
            raise RuntimeError(
                "QC PASS refused (§10.1.5A-G5H): --samples required — "
                "a verdict binds the exact review sample set, never "
                "the plan-level default contract")
        auth = pilot_authority(run_dir, sample_ids)
        if not auth["ok"]:
            raise RuntimeError(
                "QC PASS refused (§10.1.5A-G5H sample gate): "
                f"{auth['violations'][:5]}")
        if contract_sha and contract_sha != auth["contract_sha256"]:
            raise RuntimeError(
                "QC PASS refused (§10.1.5A-G5H): explicit contract "
                f"{contract_sha[:16]} disagrees with the sample-set "
                f"contract {auth['contract_sha256'][:16]}")
        contract_sha = auth["contract_sha256"]
        payload_sha = _pilot_payload_sha(run_dir)
        if payload_sha is None:
            raise RuntimeError(
                "QC PASS refused (§10.1.5A-G5H): pilot_review.json "
                "missing — the verdict must bind an exact payload")
        pilot = {"sample_ids": auth["sample_ids"],
                 "note_ids": auth["note_ids"],
                 "contract_sha256": auth["contract_sha256"],
                 "lyric_contract": auth["lyric_contract"],
                 "lyric_mapping_impl": auth["lyric_mapping_impl"],
                 "pilot_payload_sha256": payload_sha,
                 "audio_package_hashes": auth["audio_package_hashes"]}
    rec = {"schema": CALIB_SCHEMA,
           "verdict": "PASS" if is_pass else "FAIL",
           "contract_sha256": contract_sha,
           "auditor": auditor, "notes": notes,
           "sample_ids": list(sample_ids or []),
           "recorded_at": _now()}
    if pilot is not None:
        rec["pilot"] = pilot
    if rec["verdict"] == "PASS" and require_git_evidence:
        inv = plan_invariants(run_dir)
        if not inv["ok"]:
            raise RuntimeError(
                "QC PASS refused (§10.1.5A-G5G plan-invariant rule): "
                f"plan.json disagrees with authoritative artifacts — "
                f"{inv['violations'][:3]}")
        ev = git_evidence(run_dir, item_ids=pilot["sample_ids"],
                          include_qc=False)
        if not ev["complete"]:
            raise RuntimeError(
                "QC PASS refused (§10.1.5A Git-evidence rule): "
                f"{len(ev['missing'])}/{ev['checked']} required "
                "artifacts are not committed to Git — e.g. "
                f"{ev['missing'][:4]}")
        rec["git_evidence_at_record"] = {
            "complete": True, "checked": ev["checked"]}
    _jwrite(_verdict_path(run_dir), rec)
    log = _verdict_path(run_dir).parent / "audit.jsonl"
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


# ------------------------------------------------------------- semantic diff

def semantic_diff(item, c0_notes_by_id=None) -> dict:
    """§10.1.5A-G3/G4: machine-checkable proof that the Baseline option
    is Candidate-0 verbatim outside the target and the Candidate option
    differs ONLY by the declared patch. Rendered notes compare at
    score level (float tone); ustx integerization is uniform across
    options and recorded explicitly."""
    from .review.build import apply_patch
    from .review.render import option_notes, neutral_vowels
    ctx = item["context"]
    patch = item["patch"]
    target_ids = set(patch["note_ids"])
    base = apply_patch(ctx, {"type": "identity"})
    cand = apply_patch(ctx, patch)

    def produced(n):
        return n.get("split_child") is not None or n["id"] == "__merged__"

    def fields(n):
        return {"id": n["id"], "start": round(n["start"], 6),
                "end": round(n["end"], 6), "dur": round(n["dur"], 6),
                "tone": round(n["tone"], 6),
                "voiced": bool(n.get("voiced", True))}

    b_out = [n for n in base if n["id"] not in target_ids]
    c_out = [n for n in cand
             if n["id"] not in target_ids and not produced(n)]
    score_diff = []
    if [n["id"] for n in b_out] != [n["id"] for n in c_out]:
        score_diff.append({"kind": "note_set_changed_outside_target"})
    else:
        for bn, cn in zip(b_out, c_out):
            if fields(bn) != fields(cn):
                score_diff.append({"kind": "note_changed_outside_target",
                                   "id": bn["id"],
                                   "baseline": fields(bn),
                                   "candidate": fields(cn)})
    b_lyr = neutral_vowels(b_out)
    c_lyr = neutral_vowels(
        [n for n in cand
         if n["id"] not in target_ids and not produced(n)])
    lyric_diff = ([{"kind": "lyric_diff_outside_target"}]
                  if b_lyr != c_lyr else [])
    dev = max((abs(n["tone"] - round(n["tone"])) * 100.0
               for n in base + cand), default=0.0)
    c0_diff = []
    if c0_notes_by_id:
        for n in base:
            src = c0_notes_by_id.get(n["id"])
            if src is not None and (abs(src["start"] - n["start"]) > 1e-6
                                    or abs(src["dur"] - n["dur"]) > 1e-6
                                    or abs(src["tone"] - n["tone"]) > 1e-6):
                c0_diff.append({"id": n["id"], "context": fields(n),
                                "c0": src})
    return {
        "schema": CALIB_SCHEMA, "cal_item_id": item["item_id"],
        "repair_id": item["repair_id"],
        "lyric_contract": item.get("lyric_contract") or LYRIC_CONTRACT,
        "target": {"note_ids": sorted(target_ids),
                   "operation": patch["type"],
                   "patch_sha256": _sha(patch)},
        "outside_target": {
            "score_diff": score_diff, "lyric_diff": lyric_diff,
            "pitch_semantics": ("uniform: integer tone, no PITD "
                                "(diagnostic contract, identical "
                                "across options)")},
        "within_target": {
            "before": [fields(n) for n in base
                       if n["id"] in target_ids],
            "after": [fields(n) for n in cand if produced(n)
                      or n["id"] in target_ids]},
        "baseline_vs_c0": ("context slice identical" if not c0_diff
                           else c0_diff),
        "tone_integerization": {
            "max_deviation_cents": round(dev, 3),
            "note": ("uniform across options; canonical GAME ustx "
                     "also stores integer tones")},
        "canonical_audio_reference": None,
    }


# ------------------------------------------- target focus + signal QC (G5A/B)

SOURCE_FOCUS_PAD_S = 0.6
TARGET_FOCUS_PAD_S = 0.5
TARGET_CORE_PAD_S = 0.15         # G5D: narrowest blind listening surface
QC_DRIFT_RATIO_FLAG = 0.5        # out-of-target A/B diff rms / baseline rms
QC_LOUDNESS_RANGE = (0.7, 1.4)   # candidate/baseline full-phrase rms
QC_LISTEN_OUTSIDE_FLAG = 0.08    # listen surface outside-splice diff must
                                 # stay ~0 (bit-identical by construction;
                                 # only fade zones may differ slightly)
QC_LISTEN_DELTA_DB_FLAG = 3.5    # constructed pair loudness delta bound
GIT_REQUIRED_ITEM_FILES = (
    "manifest.json", "OPTION_0.wav", "OPTION_1.wav",
    "OPTION_0_LISTEN.wav", "OPTION_1_LISTEN.wav",
    "OPTION_0.ustx", "OPTION_1.ustx",
    "BASELINE.ustx", "CANDIDATE.ustx",
    "SOURCE_FOCUS_original_mix.wav", "SOURCE_FOCUS_separated_vocal.wav",
    "semantic_diff.json",
    "BASELINE_TARGET.wav", "CANDIDATE_TARGET.wav",
    "BASELINE_CORE.wav", "CANDIDATE_CORE.wav",
    "SOURCE_CORE_original_mix.wav", "SOURCE_CORE_separated_vocal.wav",
    "signal_qc.json",
)


def _crop_rendered(src_wav: Path, dst: Path, t0: float, t1: float) -> dict:
    """§10.1.5A-G5A: crop [t0,t1] seconds from the ALREADY-RENDERED
    full-phrase wav — never re-render a short window for focus audio."""
    import soundfile as sf
    info = sf.info(str(src_wav))
    i0 = max(0, min(info.frames, int(round(t0 * info.samplerate))))
    i1 = max(i0, min(info.frames, int(round(t1 * info.samplerate))))
    with sf.SoundFile(str(src_wav)) as f:
        f.seek(i0)
        data = f.read(i1 - i0, always_2d=True)
    sf.write(str(dst), data, info.samplerate)
    return {"frames": i1 - i0, "sample_rate": info.samplerate}


def _extract_f0(wav_path: Path) -> dict:
    """Lazy torchfcpe extraction — the monkeypatch seam for tests."""
    from .analysis.f0 import extract_f0
    return extract_f0(wav_path)


def _f0_segment_summary(f0: dict, t0: float, t1: float) -> dict:
    """§10.1.5A-G5C: median/IQR MIDI of voiced frames strictly inside
    [t0,t1) — one REAL child span, never a focus-window half. Context
    outside the span cannot contaminate the median; too few voiced
    frames → nulls (unavailable), never a fabricated MIDI."""
    import numpy as np
    from .analysis.f0 import hz_to_midi
    times = np.asarray(f0["times"], dtype=float)
    hz = np.asarray(f0["f0_hz"], dtype=float)
    voiced = np.asarray(f0["voiced"], dtype=bool)
    m = (times >= t0) & (times < t1)
    n_tot = int(m.sum())
    v = m & voiced
    n_v = int(v.sum())
    out = {"span_rel": [round(t0, 4), round(t1, 4)],
           "n_frames": n_tot, "voiced_frames": n_v,
           "voiced_fraction": round(n_v / max(1, n_tot), 4),
           "midi_median": None, "midi_iqr": None,
           "midi_min": None, "midi_max": None,
           "dominant_fraction": None,
           "evidence": "unavailable",
           "provenance": f0.get("backend")}
    if n_v >= 3:
        midi = hz_to_midi(hz[v])
        med = float(np.median(midi))
        q25, q75 = np.percentile(midi, [25, 75])
        dom = float((np.abs(midi - med) <= 1.0).mean())
        out.update({"midi_median": round(med, 3),
                    "midi_iqr": round(float(q75 - q25), 3),
                    "midi_min": round(float(midi.min()), 3),
                    "midi_max": round(float(midi.max()), 3),
                    "dominant_fraction": round(dom, 3),
                    "evidence": ("ambiguous" if (q75 - q25) > 3.0
                                 or dom < 0.6 else "ok")})
    return out


def _child_spans(patch: dict) -> list:
    """Operation-aware child spans (absolute seconds) straight from the
    declared patch — split children, merged span, or shifted span."""
    if patch["type"] == "split":
        return [(float(c["start"]), float(c["end"]))
                for c in patch["children"]]
    if patch["type"] == "merge":
        m = patch["merged"]
        return [(float(m["start"]), float(m["end"]))]
    a = patch.get("after") or {}
    return [(float(a.get("start", patch.get("start"))),
             float(a.get("end", patch.get("end"))))]


def child_f0_qc(man: dict, idir: Path) -> dict:
    """Per-child F0 summaries + source-distance metrics (G5C).

    Each declared child span is measured independently on the SOURCE
    vocal (ground truth) and on both option renders; the option's
    per-child error vs the source median and a robust structure error
    quantify whether the candidate actually tracks the source better
    than the baseline — evidence for review-readiness, never truth."""
    cal = man["calibration"]
    opts = {o["option_id"]: o for o in man["options"]}
    patch = opts[cal["candidate_role"]]["score_patch"]
    spans = _child_spans(patch)
    region = [float(x) for x in man["target_group"]["region"]]
    t0 = max(0.0, region[0] - TARGET_FOCUS_PAD_S)
    fs = max(0.0, region[0] - SOURCE_FOCUS_PAD_S)
    f0_b = f0_c = f0_s = None
    errs = {}
    for key, wav in (("baseline", idir / "BASELINE_TARGET.wav"),
                     ("candidate", idir / "CANDIDATE_TARGET.wav")):
        try:
            f = _extract_f0(wav)
        except Exception as e:
            errs[key] = str(e)
        else:
            if key == "baseline":
                f0_b = f
            else:
                f0_c = f
    foc = idir / "SOURCE_FOCUS_separated_vocal.wav"
    if foc.exists():
        try:
            f0_s = _extract_f0(foc)
        except Exception as e:
            errs["source"] = str(e)
    else:
        errs["source"] = "missing SOURCE_FOCUS_separated_vocal.wav"
    children = []
    for k, (s, e) in enumerate(spans):
        ch = {"child": k, "span_abs": [round(s, 4), round(e, 4)],
              "duration": round(e - s, 4)}
        ch["source"] = (_f0_segment_summary(f0_s, s - fs, e - fs)
                        if f0_s is not None
                        else {"evidence": "unavailable",
                              "error": errs.get("source",
                                                "no source f0")})
        ch["baseline"] = (_f0_segment_summary(f0_b, s - t0, e - t0)
                          if f0_b is not None
                          else {"evidence": "unavailable",
                                "error": errs.get("baseline",
                                                  "no baseline f0")})
        ch["candidate"] = (_f0_segment_summary(f0_c, s - t0, e - t0)
                           if f0_c is not None
                           else {"evidence": "unavailable",
                                 "error": errs.get("candidate",
                                                   "no candidate f0")})
        sm = ch["source"].get("midi_median")
        for nm in ("baseline", "candidate"):
            m = ch[nm].get("midi_median")
            ch[f"{nm}_error_semitones"] = (
                round(m - sm, 3)
                if sm is not None and m is not None else None)
        children.append(ch)
    b_err = [abs(ch["baseline_error_semitones"]) for ch in children
             if ch["baseline_error_semitones"] is not None]
    c_err = [abs(ch["candidate_error_semitones"]) for ch in children
             if ch["candidate_error_semitones"] is not None]
    # worst-child error — with two children a median degenerates to the
    # mean and would halve a single badly-off child
    bse = round(max(b_err), 3) if b_err else None
    cse = round(max(c_err), 3) if c_err else None
    unavail = sum(1 for ch in children for nm in
                  ("source", "baseline", "candidate")
                  if ch[nm].get("midi_median") is None)
    ambiguous = [f"{nm}_child_{ch['child']}"
                 for ch in children for nm in
                 ("source", "baseline", "candidate")
                 if ch[nm].get("evidence") == "ambiguous"]
    return {
        "children": children,
        "baseline_child_error_semitones":
            [ch["baseline_error_semitones"] for ch in children],
        "candidate_child_error_semitones":
            [ch["candidate_error_semitones"] for ch in children],
        "baseline_structure_error": bse,
        "candidate_structure_error": cse,
        "candidate_improvement_vs_baseline":
            (round(bse - cse, 3)
             if bse is not None and cse is not None else None),
        "unavailable_child_slots": unavail,
        "ambiguous_children": ambiguous,
        "note": ("review-readiness evidence only — never an automatic "
                 "score truth; unavailable/ambiguous stays neutral"),
    }


def _segment_ab_ratio(b, c, i0: int, i1: int):
    """rms(b−c)/rms(b) over a sample range — the phrase-drift metric the
    pre-human Git audit used (~0.68×baseline RMS on phrase-wide diffs)."""
    import numpy as np
    sb, sc = b[i0:i1], c[i0:i1]
    if sb.size == 0:
        return None
    rb = float(np.sqrt(np.mean(sb ** 2)))
    if rb < 1e-6:
        return None
    return round(float(np.sqrt(np.mean((sb - sc) ** 2))) / rb, 4)


LISTEN_TARGET_DBFS = -16.0   # phone-friendly review level (rms)
SPLICE_PAD_S = 0.35          # candidate segment keeps ~0.35s of its own
                           # context on each side (covers coarticulation)
SPLICE_SEARCH_S = 0.06       # ±60ms search for the lowest-energy cut
SPLICE_XFADE_S = 0.04        # 40ms crossfade at each splice edge


def _best_lag(xa, xb, max_lag):
    """Normalized best-lag cross-correlation of same-length windows:
    returns (lag_samples, correlation_at_lag)."""
    import numpy as np
    c = np.correlate(xa - xa.mean(), xb - xb.mean(), mode="full")
    lo = len(xa) - 1 - max_lag
    hi = len(xa) - 1 + max_lag
    seg = c[lo:hi + 1]
    lag = int(np.argmax(seg)) + lo - (len(xa) - 1)
    den = float(np.linalg.norm(xa) * np.linalg.norm(xb)) or 1e-9
    return lag, float(c[len(xa) - 1 + lag] / den)


def _low_energy_cut(ref, sr, t_abs, search=SPLICE_SEARCH_S,
                    win=0.02) -> int:
    """Lowest-energy win-second center within t_abs ± search seconds —
    splice edges land in pauses/unvoiced spans, not on onsets."""
    import numpy as np
    i0 = max(0, int((t_abs - search) * sr))
    i1 = min(len(ref), int((t_abs + search) * sr))
    w = max(1, int(win * sr))
    if i1 - i0 <= w:
        return max(0, min(len(ref), int(t_abs * sr)))
    best, bi = None, i0 + w // 2
    step = max(1, int(0.005 * sr))
    for s in range(i0, i1 - w, step):
        e = float((ref[s:s + w] ** 2).mean())
        if best is None or e < best:
            best, bi = e, s + w // 2
    return bi


def _spliced_listen(base, cand, sr, region_rel) -> dict:
    """§10.1.5A-G5F Blocker 3 — shared-context listening surface.

    The renderer is DETERMINISTIC (same-ustx re-render diff < 0.001),
    so every canonical A/B difference is causal: DiffSinger's duration
    model attends the whole phoneme sequence, and the declared patch's
    extra/removed phoneme propagates a ~1-2ms timing shift plus small
    acoustic smear into context notes. A human cannot A/B sample-wise
    — but the drift pollutes the sample-level diff metric and, worse,
    could let a listener attribute a non-target difference.

    The review surface therefore shares ONE context render: the
    baseline option plays straight through; the candidate LISTEN copy
    is baseline context outside [e0, e1] and the CANDIDATE's own
    rendered audio inside — spliced at low-energy points with edge-lag
    alignment + 40ms crossfades. Outside the splice edges A and B are
    bit-identical, so non-target drift is zero BY CONSTRUCTION; inside
    them the candidate's real timing/structure is the evidence.
    Canonical OPTION wavs are never touched — they remain the
    hash-bound decision authority and their honest full-render drift
    is recorded in signal_qc as renderer/global-context effect."""
    import numpy as np
    e0_rel = max(0.0, region_rel[0] - SPLICE_PAD_S)
    e1_rel = min(len(base) / sr, region_rel[1] + SPLICE_PAD_S)
    c0 = _low_energy_cut(base[:, 0], sr, e0_rel)
    c1 = _low_energy_cut(base[:, 0], sr, e1_rel)
    # align the candidate segment to the baseline at each edge —
    # measure the local constant shift so fade zones line up exactly.
    max_lag = int(0.01 * sr)
    lags = {}
    for name, cut in (("left", c0), ("right", c1)):
        w = int(0.06 * sr)
        xa = base[max(0, cut - w):cut + w, 0]
        xb = cand[max(0, cut - w):cut + w, 0]
        lag, conf = _best_lag(xa, xb, max_lag)
        lags[name] = {"samples": lag, "ms": round(lag / sr * 1000, 2),
                      "confidence": round(conf, 3),
                      "applied": lag if conf >= 0.5 else 0}
    l0 = lags["left"]["applied"]
    l1 = lags["right"]["applied"]
    n = min(len(base), len(cand))
    xf = int(SPLICE_XFADE_S * sr)
    s0 = max(xf, min(n - xf, c0 + l0))
    s1 = max(s0 + 2 * xf, min(n - xf, c1 + l1))
    if s1 + xf > n or s0 - xf < 0:            # degenerate tiny clip —
        s0, s1 = xf, max(xf, n - xf)        # splice at the edges only
    # each fade spans the ±xf window around an edge → 2*xf samples
    t = np.linspace(0.0, 1.0, 2 * xf, dtype=np.float32)

    def xfade(x, y):
        return x * (1.0 - t)[:, None] + y * t[:, None]

    out = np.vstack([
        base[:s0 - xf],
        xfade(base[s0 - xf:s0 + xf], cand[s0 - xf:s0 + xf]),
        cand[s0 + xf:s1 - xf],
        xfade(cand[s1 - xf:s1 + xf], base[s1 - xf:s1 + xf]),
        base[s1 + xf:]])
    return {"data": out,
            "construction": "shared_context_splice",
            "context_donor": "baseline",
            "splice_edges_rel": [round(c0 / sr, 4), round(c1 / sr, 4)],
            "fade_zone_rel": [round((s0 - xf) / sr, 4),
                              round((s1 + xf) / sr, 4)],
            "edge_lag": lags}


def _listen_copies(idir: Path, owav: dict, man: dict,
                   region_rel) -> dict:
    """§10.1.5A-G5E/G5F: build the human listening surface.

    The baseline-side LISTEN copy is its canonical wav; the
    candidate-side copy is the shared-context splice (baseline context
    outside the splice edges, candidate's own render inside) — so the
    pair differs ONLY inside the declared target span. ONE pair-shared
    gain is then measured on the constructed pair and applied to both:
    no independent normalization, canonical OPTION wavs untouched."""
    import math
    import numpy as np
    import soundfile as sf
    cal = man["calibration"]
    base_id, cand_id = cal["baseline_option"], cal["candidate_role"]
    ids = sorted(owav)
    data = {o: sf.read(str(idir / owav[o]), dtype="float32",
                     always_2d=True) for o in ids}
    sr = int(data[ids[0]][1])
    n = min(len(data[o][0]) for o in ids)
    sp = _spliced_listen(data[base_id][0][:n], data[cand_id][0][:n],
                         sr, region_rel)
    constructed = {}
    for o in ids:
        if o == cand_id:
            constructed[o] = sp["data"]
        else:
            constructed[o] = data[o][0][:n]
    rms = {o: float(np.sqrt((d ** 2).mean())) or 1e-9
           for o, d in constructed.items()}
    pk = {o: float(np.abs(d).max()) or 1e-9
          for o, d in constructed.items()}
    pair_rms = math.sqrt(sum(v * v for v in rms.values())
                         / len(rms)) or 1e-9
    want = 10 ** (LISTEN_TARGET_DBFS / 20.0) / pair_rms
    gain = min(want, *(0.98 / pk[o] for o in ids))
    gdb = round(20 * math.log10(max(gain, 1e-9)), 2)
    peaks, files = {}, []
    for o in ids:
        d = constructed[o]
        dst = idir / f"{o}_LISTEN.wav"
        sf.write(str(dst), d * gain, sr, subtype="PCM_16")
        peaks[o] = round(pk[o] * gain, 4)
        files.append(dst.name)
    rdb = {o: round(20 * math.log10(rms[o]), 2) for o in ids}
    return {"target_dbfs": LISTEN_TARGET_DBFS,
            "pair_rms_db": round(20 * math.log10(pair_rms), 2),
            "shared_gain_db": gdb,
            "clipped": gain < want - 1e-9,
            "option_rms_db": rdb,
            "ab_loudness_delta_db":
                round(abs(rdb[ids[0]] - rdb[ids[1]]), 2)
                if len(ids) == 2 else None,
            "listen_peak": peaks, "files": files,
            "construction": sp["construction"],
            "context_donor": sp["context_donor"],
            "splice_edges_rel": sp["splice_edges_rel"],
            "fade_zone_rel": sp["fade_zone_rel"],
            "edge_lag": sp["edge_lag"],
            "outside_surface": "bit-identical outside the fade zone"}


def _phrase_listen_copies(cdir: Path) -> dict:
    """Gain-match SOURCE_PHRASE_* clips to the same listening target —
    presentation copies only; canonical phrase bytes stay bound.
    Idempotent: existing copies are skipped (source bytes unchanged)."""
    import math
    import numpy as np
    import soundfile as sf
    res = {}
    pdir = Path(cdir) / "phrases"
    if not pdir.exists():
        return res
    for ph in sorted(pdir.iterdir()):
        if not ph.is_dir():
            continue
        for src in sorted(ph.glob("SOURCE_PHRASE_*.wav")):
            if src.name.endswith("_LISTEN.wav"):
                continue
            dst = src.with_name(src.stem + "_LISTEN.wav")
            if dst.exists():
                continue
            d, sr = sf.read(str(src), dtype="float32", always_2d=True)
            rms = float(np.sqrt((d ** 2).mean())) or 1e-9
            pk = float(np.abs(d).max()) or 1e-9
            want = 10 ** (LISTEN_TARGET_DBFS / 20.0) / rms
            gain = min(want, 0.98 / pk)
            sf.write(str(dst), d * gain, sr, subtype="PCM_16")
            res[f"{ph.name}/{dst.name}"] = {
                "source_listening_gain_db":
                    round(20 * math.log10(max(gain, 1e-9)), 2),
                "clipped": gain < want - 1e-9}
    return res


def _anchor_bounds(it: dict, chars: list) -> tuple | None:
    """§10.1.5A-G5J: legal anchor range per char — the intersection
    over ALL options of its carrier-note span
    [carrier.start, carrier.end - ARTICULATE_MIN_SEG_S]. A char may
    only onset inside its own carrier's span (earlier would voice it
    at the previous note's pitch); the shared range keeps A/B
    outside-target anchors identical (J7). None when any option can't
    bind the evidence."""
    from .review.build import apply_patch
    from .review.render import _char_anchor_binding
    lo = [None] * len(chars)
    hi = [None] * len(chars)
    for o in it["options"]:
        notes = apply_patch(it["context"], o["score_patch"])
        bind = _char_anchor_binding(notes, chars)
        if bind is None:
            return None
        for k, (pos, ch, i) in enumerate(bind):
            n = notes[i]
            l, h = n["start"], n["end"] - ARTICULATE_MIN_SEG_S
            lo[k] = l if lo[k] is None else max(lo[k], l)
            hi[k] = h if hi[k] is None else min(hi[k], h)
    return lo, hi


def _onset_peaks(path) -> np.ndarray:
    """§G5J-rlv5: onset-strength envelope peak times (seconds) — ONE
    acoustic instrument used on BOTH the source vocal and every
    rendered option, so detector bias cancels in the delta instead of
    being chased by the loop. (Whisper force_align stays in the QC
    table as diagnostic evidence — it proved to report rendered char
    boundaries ~200-500ms early, inside the previous syllable.)"""
    import librosa
    y, sr = librosa.load(str(path), sr=22050, mono=True)
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=256)
    pk = librosa.util.peak_pick(env, pre_max=5, post_max=5, pre_avg=5,
                                post_avg=5, delta=ONSET_PEAK_DELTA,
                                wait=ONSET_PEAK_WAIT)
    return pk * 256.0 / sr


def _source_ref_onsets(chars: list, src_wav, ph0: float):
    """Per-char acoustic onset reference on the SOURCE separated
    vocal: the onset-strength peak nearest the whisper-measured char
    position (whisper positions select the landmark; the acoustic
    peak refines it), monotonic and never shared between chars.
    Returns (refs, kinds): refs are phrase-relative seconds or None
    (None = no acoustic evidence at all — the wav couldn't be read),
    kinds 'onset_peak' | 'whisper_fallback' | 'none'."""
    import numpy as np
    refs, kinds = [], []
    try:
        peaks = _onset_peaks(src_wav)
    except Exception:
        peaks = None
    if peaks is None:
        return None, ["none"] * len(chars)
    prev = -1e9
    for c in chars:
        rel = float(c["start"]) - ph0
        pk = None
        cand = peaks[(peaks > prev + ONSET_MIN_GAP_S)
                     & (np.abs(peaks - rel) <= ONSET_REF_WIN_S)]
        if cand.size:
            pk = float(cand[np.argmin(np.abs(cand - rel))])
        if pk is not None:
            refs.append(pk)
            kinds.append("onset_peak")
            prev = pk
        else:
            refs.append(rel)
            kinds.append("whisper_fallback")
    return refs, kinds


def _option_char_starts(ustx_path):
    """Wav-relative commanded onset positions (seconds) of every
    lyric-carrying note in a rendered OPTION_*.ustx — the exact
    segment starts the synth was told to voice (post-snap), one per
    char. None when the file can't be read or has no carriers."""
    import yaml
    try:
        doc = yaml.safe_load(Path(ustx_path).read_text(
            encoding="utf-8"))
        tick_s = 60000.0 / (120.0 * 480.0) / 1000.0
        carriers = [n for n in doc["voice_parts"][0]["notes"]
                    if n["lyric"] != "+"]
        return [n["position"] * tick_s for n in carriers] or None
    except Exception:
        return None


def _render_onsets(wav, centers: list):
    """Per-char rendered acoustic onset: the onset-strength peak
    nearest the char's COMMANDED segment start (wav-relative,
    ustx-derived), monotonic. Searching near the commanded start —
    not the source ref — keeps a truly displaced onset measurable;
    the window is asymmetric because DiffSinger phoneme anticipation
    can voice a consonant ~0.2s before its note while the vowel
    attack lands at/after it."""
    import numpy as np
    try:
        peaks = _onset_peaks(wav)
    except Exception:
        return [None] * len(centers)
    out, prev = [], -1e9
    for k, a in enumerate(centers):
        rel = float(a)
        fwd = ONSET_MEAS_FWD_S
        if k + 1 < len(centers):
            fwd = min(fwd, float(centers[k + 1]) - rel
                      - ONSET_MIN_GAP_S)
        cand = peaks[(peaks > prev + ONSET_MIN_GAP_S)
                     & (peaks >= rel - ONSET_MEAS_BACK_S)
                     & (peaks <= rel + fwd)]
        if cand.size:
            pk = float(cand[np.argmin(np.abs(cand - rel))])
            out.append(pk)
            prev = pk
        else:
            out.append(None)
    return out


def _classify_routes(chars: list, refs, ref_kinds, lo, hi,
                     off: float = 0.0) -> list:
    """§10.1.5A-G5K per-char hard-case routing — decided BEFORE the
    loop iterates, from evidence that cannot change under iteration:
      class_A              reliable acoustic landmark AND the desired
                           correction is carrier-feasible
      B1_unmeasurable      no reliable source landmark — timing
                           evidence unavailable (≠ wrong, ≠ right)
      B2_carrier_conflict  source onset outside the legal carrier
                           anchor range — the review overlay may
                           never rewrite written-score timing to
                           reach it
    `hi` entries are the raw legal limits; feasibility uses the
    usable-move bound (a char also needs MIN_USABLE_SEG_S of sung
    span). `refs` are recorded verbatim; `off` shifts them into the
    bounds' domain for the comparison (phrase-relative refs vs
    absolute carrier times). Returns a list of route dicts."""
    hi_move = [hi[k] + ARTICULATE_MIN_SEG_S - MIN_USABLE_SEG_S
               for k in range(len(chars))]
    routes = []
    for k, c in enumerate(chars):
        ref = None if refs is None else refs[k]
        ra = None if ref is None else ref + off
        r = {"char": c["char"],
             "source_ref_onset": None if ref is None
             else round(ref, 4),
             "source_ref_kind": None if ref_kinds is None
             else ref_kinds[k],
             # carrier bounds recorded in the SAME domain as the ref
             # (off subtracted) so reviewers compare like with like
             "carrier_lo": round(lo[k] - off, 4),
             "carrier_hi": round(hi_move[k] - off, 4),
             "desired_anchor": None if ref is None
             else round(ref, 4),
             "bound_conflict": False,
             "unmeasurable_reason": None,
             "route_detail": None,
             # §G5L: directional + post-loop adjudication fields
             "route_subtype": None,
             "direction": None,
             "overhang_ms": None,
             "primary_measurement": "onset_strength_peak_v1",
             "secondary_measurement": None,
             "render_measurement_status": None,
             "final_class": None,
             "phrase_level_conflict_id": None}
        if (ra is None or ref_kinds is None
                or ref_kinds[k] != "onset_peak"):
            r["route"] = ROUTE_B1
            r["route_subtype"] = "source_unmeasurable"
            r["unmeasurable_reason"] = "no_source_landmark"
        elif (ra < lo[k] - 1e-9
              or ra > hi_move[k] + 1e-9):
            r["route"] = ROUTE_B2
            r["bound_conflict"] = True
            below = ra < lo[k]
            # §G5L Blocker 1: direction is persisted explicitly —
            # early and late carrier conflicts are opposite physics
            # and can never share one 'anticipation' label.
            r["direction"] = "early" if below else "late"
            gap = (lo[k] - ra) if below else (ra - hi_move[k])
            r["overhang_ms"] = round(gap * 1000.0, 1)
            r["unmeasurable_reason"] = (
                "source_ref_below_carrier_lo" if below
                else "source_ref_above_carrier_hi")
            # §G5L Blocker 2: the 120ms line is a TRIAGE PRIOR only —
            # it names a candidate hypothesis, never a final verdict.
            # Only an EARLY conflict may be a preutterance candidate;
            # a late conflict can never be anticipation — it is a
            # post-boundary delay or a written-timing suspicion.
            if below:
                r["route_detail"] = (
                    "preutterance_candidate"
                    if gap <= ANTICIPATION_MAX_S
                    else "written_timing_suspect")
            else:
                r["route_detail"] = (
                    "post_boundary_delay_candidate"
                    if gap <= ANTICIPATION_MAX_S
                    else "written_timing_suspect")
        else:
            r["route"] = ROUTE_CLASS_A
        r["final_class"] = r["route_subtype"] or r["route"]
        routes.append(r)
    return routes


def _energy_edge_onsets(wav: Path, centers) -> list:
    """§G5K-B1 second independent landmark family — adjudication
    evidence ONLY (never merged into the primary measurement's
    weight). Energy-envelope derivative: a consonant burst produces
    a steep RMS-dB rise independent of spectral-flux peak shape.
    Returns wav-relative seconds or None per char."""
    import numpy as np
    try:
        import librosa
        y, sr = librosa.load(str(wav), sr=None, mono=True)
        rms = librosa.feature.rms(
            y=y, frame_length=1024, hop_length=256)[0]
        t = librosa.frames_to_time(np.arange(rms.size),
                                 sr=sr, hop_length=256)
        db = librosa.amplitude_to_db(np.maximum(rms, 1e-10),
                                   ref=np.max)
        slope = np.diff(db)
        out = []
        for k, c in enumerate(centers):
            fwd = 0.25
            if k + 1 < len(centers):
                fwd = min(fwd, float(centers[k + 1]) - float(c)
                          - ONSET_MIN_GAP_S)
            w = (t[1:] >= float(c) - 0.15) & (t[1:] <= float(c) + fwd)
            cand = np.where(w)[0]
            if not cand.size:
                out.append(None)
                continue
            i = cand[np.argmax(slope[cand])]
            # edge must be a real rise, not noise-floor jitter
            if slope[i] < 2.0:
                out.append(None)
            else:
                out.append(float(t[i + 1]))
        return out
    except Exception:
        return [None] * len(list(centers))


def _closed_loop_anchors(cfg, idir: Path, it: dict, chars: list,
                         src_wav=None, progress=None) -> dict:
    """§10.1.5A-G5J acoustic lyric-timing closed loop (rlv5).

    render → measure each option's per-char acoustic onsets with the
    SAME onset-strength instrument as the source reference → per-char
    onset error = rendered peak − source ref peak → shift every
    char's render-only anchor opposite the error (k<1, per-iteration
    clamp, strictly monotonic, carrier-span bounds shared across
    A/B) → rerender → repeat until the max absolute shared error
    converges or the iteration budget ends.

    Anchors never leave the render layer — the written score is
    untouched. Anything unmeasurable (missing wav, no source ref, no
    renderable peak) or blocked (clamp/monotonic can't move an
    anchor further) records the residual and reports converged=False
    — never a fake 'closer' timing."""
    from .review.render import render_item
    ph0 = float(it["phrase"]["start"])
    bounds = _anchor_bounds(it, chars)
    meta = {"k": LOOP_K, "clamp_s": LOOP_CLAMP_S, "tol_ms": LOOP_TOL_MS,
            "instrument": "onset_strength_peak_v1"}
    if bounds is None:
        return {"converged": False, "reason": "unbindable_chars",
                "iterations": [], "anchors": None, "rres": None,
                "bound_limited": [], "unmeasurable_chars": [],
                "char_routes": None, "hard_cases": [],
                "bounds": None, **meta}
    lo, hi = bounds
    if any(lo[k] > hi[k] for k in range(len(chars))):
        return {"converged": False, "reason": "unbindable_chars",
                "iterations": [], "anchors": None, "rres": None,
                "bound_limited": [], "unmeasurable_chars": [],
                "char_routes": None, "hard_cases": [],
                "bounds": {"lo": lo, "hi": hi}, **meta}
    refs, ref_kinds = _source_ref_onsets(chars, src_wav, ph0)
    if refs is None:
        return {"converged": False, "reason": "unmeasurable",
                "iterations": [], "anchors": None, "rres": None,
                "bound_limited": [], "unmeasurable_chars":
                list(range(len(chars))),
                "ref_kinds": ref_kinds,
                "char_routes": _classify_routes(
                    chars, refs, ref_kinds, lo, hi, off=ph0),
                "hard_cases": list(range(len(chars))),
                "bounds": {"lo": lo, "hi": hi}, **meta}
    # §G5K: classify every char BEFORE iterating — B1 has no reliable
    # landmark (timing evidence unavailable), B2's source onset sits
    # outside the legal carrier range (the review overlay may never
    # rewrite written-score timing to reach it). Hard-case anchors are
    # held at their nearest legal position, never updated, and do not
    # count toward convergence — they are routed, not repaired.
    # refs are phrase-relative; bounds are absolute — off bridges them.
    routes = _classify_routes(chars, refs, ref_kinds, lo, hi, off=ph0)
    hard = [k for k in range(len(chars))
            if routes[k]["route"] != ROUTE_CLASS_A]
    hi_move = [hi[k] + ARTICULATE_MIN_SEG_S - MIN_USABLE_SEG_S
               for k in range(len(chars))]
    anchors = [min(max(refs[k] + ph0, lo[k]), hi_move[k])
               for k in range(len(chars))]
    if any(anchors[k + 1] - anchors[k] < ARTICULATE_MIN_SEG_S
           for k in range(len(anchors) - 1)):
        return {"converged": False, "reason": "unbindable_chars",
                "iterations": [], "anchors": None, "rres": None,
                "bound_limited": [], "unmeasurable_chars": [],
                "bounds": {"lo": lo, "hi": hi}, **meta}
    history, rres, converged, stop = [], None, False, "max_iters"
    limited, unmeasurable = [], []
    for it_i in range(LOOP_MAX_ITERS + 1):
        rres = render_item(cfg, idir, it, chars, anchors=anchors)
        errs, onsets, measurable, conf = {}, {}, True, {}
        for o in it["options"]:
            oid = o["option_id"]
            wav = idir / f"{oid}.wav"
            if not wav.exists():
                errs[oid] = None
                onsets[oid] = None
                conf[oid] = None
                measurable = False
                continue
            starts = _option_char_starts(idir / f"{oid}.ustx")
            if starts is None or len(starts) != len(chars):
                errs[oid] = None
                onsets[oid] = None
                conf[oid] = None
                measurable = False
                continue
            pks = _render_onsets(wav, starts)
            onsets[oid] = pks
            conf[oid] = [1.0 if p is not None else 0.0 for p in pks]
            errs[oid] = [
                round(pks[k] - refs[k], 4)
                if pks[k] is not None and refs[k] is not None else None
                for k in range(len(chars))]
        # §G5J-B: a char with no trusted measurement in ANY option
        # (no detected onset peak / no source ref) is unmeasurable —
        # it can't drive an anchor update (noise is not evidence);
        # its anchor holds at the last position and is reported.
        # Trusted measurements only feed the shared error — noise
        # never contaminates evidence.
        shared = None
        fail_reasons = {}
        if measurable:
            shared = []
            for k in range(len(chars)):
                tr = [errs[oid][k] for oid in errs
                      if errs[oid] is not None
                      and errs[oid][k] is not None
                      and conf[oid][k] >= MIN_TIMING_CHAR_PROB]
                # §G5J-rlv5 stability gate 1: both options render the
                # SAME anchor, so their measured onsets for one char
                # must agree — a disagreement means at least one peak
                # is a mis-assignment; the char is unmeasurable, not
                # "averaged" (averaging two wrong landmarks is still
                # wrong evidence).
                if len(tr) >= 2 and max(tr) - min(tr) \
                        > ONSET_XOPT_DISAGREE_S:
                    tr = []
                    # §G5L: the downgrade path needs to know WHY
                    fail_reasons[k] = "cross_option_unstable"
                elif not tr:
                    fail_reasons[k] = "render_unmeasurable"
                shared.append(
                    round(sum(tr) / len(tr), 4) if tr else None)
        # §G5J-rlv5 stability gate 2: an onset legitimately tracks its
        # commanded anchor — if the measured error jumps >FLIP_S while
        # the anchor moved <FLIP_ANCH_S, the detector re-locked onto a
        # different landmark; the char is unmeasurable this round, not
        # a real swing to chase.
        shared_raw = list(shared) if shared else None
        if shared and history:
            prev_err = history[-1].get("shared_err_raw")
            prev_anch = history[-1]["anchors"]
            for k in range(len(chars)):
                if routes[k]["route"] != ROUTE_CLASS_A:
                    continue                # held — not update evidence
                if shared[k] is None or prev_err is None \
                        or prev_err[k] is None:
                    continue
                if abs(shared[k] - prev_err[k]) > ONSET_FLIP_S \
                        and abs(anchors[k] - prev_anch[k]) \
                        < ONSET_FLIP_ANCH_S:
                    shared[k] = None
                    fail_reasons[k] = "detector_relock"
        # §G5K: convergence judges ONLY class_A chars — a held
        # hard-case anchor is neither converging evidence nor a
        # converging blocker; its route is reported separately.
        unmeasurable = []
        if measurable:
            unmeasurable = [k for k in range(len(chars))
                            if routes[k]["route"] == ROUTE_CLASS_A
                            and shared[k] is None]
        trusted = [shared[k] for k in range(len(chars))
                   if routes[k]["route"] == ROUTE_CLASS_A
                   and shared[k] is not None]
        max_abs = max((abs(e) for e in trusted), default=None)
        history.append({
            "iteration": it_i,
            "anchors": [round(a, 4) for a in anchors],
            "onsets": {oid: ([round(p, 4) if p is not None else None
                              for p in pv] if pv else None)
                       for oid, pv in onsets.items()},
            "errors_ms": {oid: ([round(e * 1000.0, 1)
                                 if e is not None else None
                                 for e in ev] if ev else None)
                          for oid, ev in errs.items()},
            "shared_err_raw": shared_raw,
            "shared_err_ms": ([round(e * 1000.0, 1)
                               if e is not None else None
                               for e in shared]
                              if shared else None),
            "unmeasurable_chars": unmeasurable,
            "unmeasurable_reasons": dict(fail_reasons),
            "max_abs_err_ms": round(max_abs * 1000.0, 1)
            if max_abs is not None else None})
        if not measurable:
            stop = "unmeasurable"
            break
        if trusted and max_abs * 1000.0 <= LOOP_TOL_MS \
                and not unmeasurable:
            converged, stop = True, "converged"
            break
        if not any(routes[k]["route"] == ROUTE_CLASS_A
                   for k in range(len(chars))):
            stop = "hard_cases_only"        # nothing legal to update
            break
        if it_i == LOOP_MAX_ITERS:
            break
        # §G5J: hi_move keeps ≥MIN_USABLE_SEG_S of sung duration inside
        # the carrier — an update past it is bound-limited, not applied
        new, limited = [], []
        for k, a in enumerate(anchors):
            if routes[k]["route"] != ROUTE_CLASS_A:
                new.append(a)               # §G5K: held hard case
                continue
            if k in unmeasurable or shared[k] is None:
                new.append(a)               # hold — no evidence
                continue
            want = a - LOOP_K * shared[k]
            na = min(max(want, a - LOOP_CLAMP_S), a + LOOP_CLAMP_S)
            # bound-limited: the carrier span itself blocks the
            # correction — recorded, not silently squeezed
            if na < lo[k] - 1e-9 or na > hi_move[k] + 1e-9:
                limited.append(k)
            na = min(max(na, lo[k]), hi_move[k])
            new.append(na)
        # monotonic: every anchor needs MIN_SEG room before the next —
        # forward pass enforces new[k] >= new[k-1]+MIN_SEG, backward
        # pass enforces new[k] <= new[k+1]-MIN_SEG; if either side has
        # no room left inside [lo,hi] the update crosses a neighbour —
        # fail closed rather than ship a reordered articulation (J6).
        for k in range(1, len(new)):
            new[k] = max(new[k], new[k - 1] + ARTICULATE_MIN_SEG_S)
        for k in range(len(new) - 2, -1, -1):
            new[k] = min(new[k], new[k + 1] - ARTICULATE_MIN_SEG_S)
        if any(new[k] < lo[k] - 1e-9 or new[k] > hi_move[k] + 1e-9
               for k in range(len(new))) or \
           any(new[k + 1] - new[k] < ARTICULATE_MIN_SEG_S - 1e-9
               for k in range(len(new) - 1)):
            stop = "anchors_crossed"
            break
        if not any(abs(new[k] - anchors[k]) > 1e-6
                   for k in range(len(new))):
            stop = "bound_limited" if limited else "anchors_clamped"
            break
        anchors = new
        if progress:
            progress(f"    closed-loop iter {it_i}: "
                     f"max|err|={max_abs * 1000.0:.0f}ms → re-render")
    if not converged and stop in ("max_iters", "anchors_clamped"):
        if unmeasurable:
            stop = "unmeasurable_chars"
        elif limited:
            stop = "bound_limited"
        elif hard:
            stop = "hard_cases"
    # §G5K: fill the persisted route table — reviewer must see
    # 'measured nowhere' vs 'could never reach' as different stories
    last = history[-1] if history else {}
    last_on = last.get("onsets") or {}
    last_er = last.get("errors_ms") or {}
    last_un = set(last.get("unmeasurable_chars") or [])
    last_why = last.get("unmeasurable_reasons") or {}
    for k, r in enumerate(routes):
        r["final_anchor"] = (round(anchors[k] - ph0, 4)
                             if anchors else None)
        r["render_onset"] = {oid: (pv[k] if pv else None)
                             for oid, pv in last_on.items()}
        r["acoustic_error_ms"] = {oid: (ev[k] if ev else None)
                                  for oid, ev in last_er.items()}
        # §G5L Blocker 3: a class_A char that PERSISTENTLY fails render
        # measurement is formally downgraded to a B1 subtype — timing
        # evidence unavailable is never 'timing correct'.
        r["render_measurement_status"] = (
            "measured" if k not in last_un else
            last_why.get(k, "render_unmeasurable"))
        if (r["route"] == ROUTE_CLASS_A and k in last_un
                and not converged):
            sub = {"render_unmeasurable": "B1_render_unmeasurable",
                   "cross_option_unstable": "B1_cross_option_unstable",
                   "detector_relock": "B1_detector_relock"}[
                       last_why.get(k, "render_unmeasurable")]
            r["route_subtype"] = sub
            r["final_class"] = sub
            r["route"] = ROUTE_B1
            r["measurement_stability"] = "unstable_measurement"
        elif r["route"] == ROUTE_B1:
            r["measurement_stability"] = "unmeasurable_source"
            r["final_class"] = r["route_subtype"] or \
                "B1_source_unmeasurable"
        elif r["route"] == ROUTE_B2:
            r["measurement_stability"] = "held"
            # a B2 char whose render measurement is ALSO unstable has
            # ambiguous evidence — direction stays recorded but the
            # detail is demoted to measurement_ambiguous
            if k in last_un:
                r["route_detail"] = "measurement_ambiguous"
            r["final_class"] = ROUTE_B2
        else:
            r["measurement_stability"] = "stable"
            r["final_class"] = ROUTE_CLASS_A
    return {"converged": converged, "reason": stop,
            "iterations": history, "anchors": anchors, "rres": rres,
            "k": LOOP_K, "clamp_s": LOOP_CLAMP_S,
            "tol_ms": LOOP_TOL_MS,
            "instrument": "onset_strength_peak_v1",
            "ref_onsets": [round(r, 4) if r is not None else None
                           for r in refs],
            "ref_kinds": ref_kinds,
            "char_routes": routes,
            "hard_cases": hard,
            "bound_limited": sorted(set(limited)),
            "unmeasurable_chars": unmeasurable,
            "bounds": {"lo": lo, "hi": hi}}


def _lyric_timing_qc(man: dict, idir: Path) -> dict:
    """§10.1.5A-G5I: same-aligner per-char lyric-timing comparison —
    the SOURCE-bound char table (persisted in the manifest) is the
    reference; each rendered option is re-aligned with the SAME
    force_align model + SAME text, so systematic aligner lag cancels
    in the delta. Times are phrase-relative seconds. A char sequence
    that can't be reproduced (missing/reordered/mismatched chars or
    an aligner failure) is a fail-closed flag — deltas themselves are
    measured and persisted (thresholds come from real pilot data, not
    guesswork)."""
    cal = man.get("calibration") or {}
    ev = cal.get("lyric_evidence") or {}
    src = ev.get("chars")
    if cal.get("lyric_contract") != "real_lyric_review" or not src:
        return None
    # §G5J: an rlv5+ package must carry a CONVERGED closed loop —
    # non-convergence means the acoustic timing gate can't claim PASS
    art = ev.get("articulation") or {}
    loop = art.get("closed_loop")
    flags0 = []
    if loop is not None and not loop.get("converged"):
        flags0.append(f"lyric_timing_not_converged:"
                      f"{loop.get('reason')}")
    # §G5K: hard-case routes are item-level truth, independent of any
    # option's render — B1 = timing evidence unavailable (≠ wrong),
    # B2 = the source onset sits outside the legal carrier range and
    # the review overlay may never rewrite written-score timing to
    # reach it. Both block PASS; the char is routed, not 'fixed'.
    char_routes = (loop or {}).get("char_routes") or []
    b1 = [r["char"] for r in char_routes
          if r.get("route") == ROUTE_B1]
    b2 = [r for r in char_routes if r.get("route") == ROUTE_B2]
    if b1:
        flags0.append(
            f"lyric_timing_evidence_unmeasurable:{''.join(b1)}")
    if b2:
        flags0.append(
            "lyric_timing_carrier_conflict:"
            f"{''.join(r['char'] for r in b2)}")
    # §G5L: a B2 set repeating across review targets on this phrase is
    # a systematic written-vs-articulation incompatibility — routed to
    # written-timing/structure adjudication, not re-looped per item.
    plc = [r["char"] for r in char_routes
           if r.get("phrase_level_conflict_id")]
    if plc:
        flags0.append(
            "lyric_timing_phrase_level_conflict:"
            f"{''.join(plc)}")
    from .analysis.lyrics import force_align, DEFAULT_MODEL
    import numpy as np
    ph_start = float(man["phrase"]["start"])
    dur = float(man["phrase"]["end"]) - ph_start
    text = "".join(c["char"] for c in src)
    out = {"aligner": "whisper-attention-dtw", "model": DEFAULT_MODEL,
           "text": text,
           "source_chars": [{"char": c["char"],
                             "start": round(c["start"] - ph_start, 4),
                             "end": round(c["end"] - ph_start, 4),
                             "probability": c.get("probability")}
                            for c in src],
           "options": {}, "per_char": [], "stats": {},
           "flags": list(flags0)}
    base_seq = [c["char"] for c in src]
    aligned = {}
    for o in man["options"]:
        oid = o["option_id"]
        try:
            cs = force_align(idir / o["wav"], text, 0.0,
                             min(29.0, dur + 0.05), model=DEFAULT_MODEL)
            aligned[oid] = cs
            out["options"][oid] = {"chars": cs}
        except Exception as e:
            aligned[oid] = None
            out["options"][oid] = {"error": str(e)[:160]}
            out["flags"].append(f"lyric_timing_unmeasurable:{oid}")
    # §G5J: two flag classes — GATE flags (unmeasurable / char
    # mismatch / score mismatch) make the delta table meaningless and
    # suppress it; REPORTING flags (not_converged, low_confidence) are
    # recorded alongside the table — evidence is never hidden, the
    # item just can't PASS while any flag stands.
    gate = [f for f in out["flags"]
            if f.startswith(("lyric_timing_unmeasurable",
                             "lyric_timing_mismatch"))]
    for oid, cs in aligned.items():
        if cs is None:
            continue
        if [c["char"] for c in cs] != base_seq:
            out["flags"].append(f"lyric_timing_mismatch:{oid}")
            gate.append(f"lyric_timing_mismatch:{oid}")
            continue
        # §G5K: ASR/force-align confidence on the RENDER measures
        # lyric intelligibility (can a recogniser hear the diction),
        # NOT acoustic timing truth — a low value blocks review because
        # diction may be unclear, but it is never evidence that the
        # onset is wrong. Kept as a separate flag family by design.
        low = [c["char"] for c in cs
               if float(c.get("probability") or 0.0)
               < MIN_TIMING_CHAR_PROB]
        if low:
            out["flags"].append(
                f"lyric_intelligibility_low:{oid}:"
                f"{''.join(low)}")
    # §G5J-rlv5 acoustic onset evidence — onset-strength peaks, ONE
    # instrument on both source and rendered audio so detector bias
    # cancels (whisper above stays diagnostic: it reported rendered
    # boundaries ~200-500ms early into the previous syllable's tail,
    # which made a whisper-vs-whisper loop push anchors genuinely
    # late — the acoustic gate below is the PASS criterion).
    refs, ref_kinds, ac_unstable = None, [], set()
    sec_meas = {}
    if loop and loop.get("ref_onsets"):
        refs = loop["ref_onsets"]
        ref_kinds = loop.get("ref_kinds") or []
    else:
        _sw = ((man.get("source_reference") or {})
               .get("separated_vocal") or {}).get("path")
        if _sw:
            try:
                refs, ref_kinds = _source_ref_onsets(
                    src, (idir / _sw).resolve(), ph_start)
            except Exception:
                refs = None
    ac_on = {}
    if refs is not None:
        for o in man["options"]:
            oid = o["option_id"]
            starts = _option_char_starts(idir / f"{oid}.ustx")
            if starts is None or len(starts) != len(src):
                ac_on[oid] = None
                continue
            ac_on[oid] = _render_onsets(idir / o["wav"], starts)
        out["acoustic"] = {
            "instrument": "onset_strength_peak_v1",
            "src_ref_onsets": [round(r, 4) if r is not None else None
                               for r in refs],
            "src_ref_kinds": ref_kinds,
            "render_onsets": {
                oid: ([round(p, 4) if p is not None else None
                       for p in pv] if pv is not None else None)
                for oid, pv in ac_on.items()},
        }
        for oid in ac_on:
            if ac_on[oid] is None:
                out["flags"].append(
                    f"lyric_timing_acoustic_unmeasurable:{oid}")
                continue
            missing = [src[k]["char"] for k in range(len(src))
                       if refs[k] is not None
                       and ac_on[oid][k] is None]
            if missing:
                out["flags"].append(
                    f"lyric_timing_acoustic_unmeasurable:{oid}:"
                    f"{''.join(missing)}")
        # §G5J-rlv5 reliability: both options share every anchor, so a
        # char whose two measured onsets disagree by more than
        # ONSET_XOPT_DISAGREE_S has at least one mis-assigned peak —
        # the delta gate must not fire on such evidence (a REAL
        # displacement shows in both options alike; a cross-assigned
        # landmark usually hits only one).
        ac_unstable = set()
        opts_ok = [oid for oid in ac_on if ac_on[oid] is not None]
        if len(opts_ok) >= 2:
            for k in range(len(src)):
                pv = [ac_on[oid][k] for oid in opts_ok
                      if ac_on[oid][k] is not None]
                if len(pv) >= 2 and max(pv) - min(pv) \
                        > ONSET_XOPT_DISAGREE_S:
                    ac_unstable.add(k)
            if ac_unstable:
                out["flags"].append(
                    "lyric_timing_acoustic_unstable:"
                    f"{''.join(src[k]['char'] for k in sorted(ac_unstable))}")
        out["acoustic"]["unstable_chars"] = sorted(ac_unstable)
        # §G5K: persist the route table so a reviewer sees 'measured
        # nowhere' vs 'could never legally reach' as different stories
        if char_routes:
            out["acoustic"]["char_routes"] = char_routes
        # §G5K-B1: second independent landmark family (energy-edge
        # derivative) as adjudication evidence ONLY for B1 chars —
        # same family on both sides, never merged into the primary
        # instrument's weight. If it finds a consistent edge the
        # char is adjudicable; if not, B1 stands confirmed.
        if b1:
            o_wavs = {o["option_id"]: o["wav"] for o in man["options"]}
            src_wav = ((man.get("source_reference") or {})
                       .get("separated_vocal") or {}).get("path")
            sf2 = {"instrument": "energy_edge_v1", "chars": {}}
            for k, r in enumerate(char_routes):
                if r.get("route") != ROUTE_B1:
                    continue
                entry = {}
                se = None
                if src_wav and (idir / src_wav).exists():
                    se = _energy_edge_onsets(
                        (idir / src_wav).resolve(),
                        [float(src[k]["start"]) - ph_start])[0]
                    entry["src_edge"] = se
                edges = []
                for oid in opts_ok:
                    starts = _option_char_starts(idir / f"{oid}.ustx")
                    if starts and len(starts) == len(src):
                        e = _energy_edge_onsets(
                            idir / o_wavs[oid], [starts[k]])[0]
                        entry[f"{oid}_edge"] = e
                        if e is not None:
                            edges.append(e)
                # §G5L: the second family only adjudicates whether B1
                # MAY become measurable — an independent consistent
                # edge earns 'measurable_with_secondary_evidence'
                # (re-entry eligible); disagreement stays fail-closed.
                # It is NEVER averaged into the primary measurement.
                if se is not None and edges:
                    d = [abs(e - se) for e in edges]
                    entry["verdict"] = (
                        "measurable_with_secondary_evidence"
                        if min(d) <= ONSET_XOPT_DISAGREE_S
                        else "disagreed")
                else:
                    entry["verdict"] = "unavailable"
                sec_meas[k] = entry["verdict"]
                sf2["chars"][src[k]["char"]] = entry
            out["acoustic"]["second_family"] = sf2
    if not gate:
        # score-bound ground truth: the render voices each char exactly
        # at its carrier note position in OPTION_x.ustx (fixed
        # 120bpm/480tpq, part_start=0, no preutterance), so
        # (measured - score_onset) is the aligner's own domain bias on
        # rendered audio — kept separate from src-vs-score construction
        # deviation so a reviewer can tell "render is early" apart from
        # "the aligner reports synthetic vocals early".
        import yaml
        tick_s = 60000.0 / (120.0 * 480.0) / 1000.0
        score_onsets = {}
        for o in man["options"]:
            oid = o["option_id"]
            try:
                doc = yaml.safe_load((idir / f"{oid}.ustx")
                                     .read_text(encoding="utf-8"))
                carriers = [n for n in doc["voice_parts"][0]["notes"]
                            if n["lyric"] != "+"]
                if [c["char"] for c in src] != \
                        [n["lyric"] for n in carriers]:
                    out["flags"].append(
                        f"lyric_timing_score_mismatch:{oid}")
                    gate.append(
                        f"lyric_timing_score_mismatch:{oid}")
                    continue
                score_onsets[oid] = [n["position"] * tick_s
                                     for n in carriers]
            except Exception as e:
                out["flags"].append(
                    f"lyric_timing_score_unavailable:"
                    f"{oid}:{str(e)[:80]}")
                gate.append(
                    f"lyric_timing_score_unavailable:{oid}")
    if not gate:
        on = {oid: [] for oid in aligned}
        off = {oid: [] for oid in aligned}
        aln_off = {oid: [] for oid in aligned}
        for k, sc_ in enumerate(out["source_chars"]):
            row = {"char": sc_["char"], "src_start": sc_["start"],
                   "src_end": sc_["end"]}
            # §G5K: every char carries its route — 'unmeasurable'
            # and 'could never reach' are different stories
            if k < len(char_routes):
                rt = char_routes[k]
                row["route"] = rt.get("route")
                row["route_subtype"] = rt.get("route_subtype")
                row["direction"] = rt.get("direction")
                row["overhang_ms"] = rt.get("overhang_ms")
                row["bound_conflict"] = rt.get("bound_conflict")
                row["carrier_lo"] = rt.get("carrier_lo")
                row["carrier_hi"] = rt.get("carrier_hi")
                row["desired_anchor"] = rt.get("desired_anchor")
                row["final_anchor"] = rt.get("final_anchor")
                row["measurement_stability"] = rt.get(
                    "measurement_stability")
                row["route_detail"] = rt.get("route_detail")
                row["render_measurement_status"] = rt.get(
                    "render_measurement_status")
                row["final_class"] = rt.get("final_class")
                row["phrase_level_conflict_id"] = rt.get(
                    "phrase_level_conflict_id")
                row["secondary_measurement"] = sec_meas.get(k)
            if refs is not None:
                row["src_acoustic_onset"] = (
                    round(refs[k], 4) if refs[k] is not None else None)
                row["src_ref_kind"] = (
                    ref_kinds[k] if k < len(ref_kinds) else None)
            for oid, cs in aligned.items():
                cc = cs[k]
                so = score_onsets[oid][k]
                row[f"{oid}_start"] = round(cc["start"], 4)
                row[f"{oid}_end"] = round(cc["end"], 4)
                row[f"{oid}_score_onset"] = round(so, 4)
                do = (cc["start"] - sc_["start"]) * 1000.0
                df = (cc["end"] - sc_["end"]) * 1000.0
                row[f"{oid}_onset_delta_ms"] = round(do, 1)
                row[f"{oid}_offset_delta_ms"] = round(df, 1)
                row[f"{oid}_score_delta_ms"] = round(
                    (so - sc_["start"]) * 1000.0, 1)
                ao = (cc["start"] - so) * 1000.0
                row[f"{oid}_aligner_offset_ms"] = round(ao, 1)
                if refs is not None and ac_on.get(oid):
                    pk = ac_on[oid][k]
                    row[f"{oid}_acoustic_onset"] = (
                        round(pk, 4) if pk is not None else None)
                    row[f"{oid}_acoustic_delta_ms"] = (
                        round((pk - refs[k]) * 1000.0, 1)
                        if pk is not None and refs[k] is not None
                        else None)
                on[oid].append(abs(do))
                off[oid].append(abs(df))
                aln_off[oid].append(ao)
            out["per_char"].append(row)
        probs = {oid: [float(c.get("probability") or 0.0)
                       for c in aligned[oid]] for oid in aligned}
        for oid in aligned:
            a, b = np.asarray(on[oid]), np.asarray(off[oid])
            out["stats"][oid] = {
                "median_abs_onset_delta_ms":
                    round(float(np.median(a)), 1),
                "p90_abs_onset_delta_ms":
                    round(float(np.percentile(a, 90)), 1),
                "max_abs_onset_delta_ms": round(float(a.max()), 1),
                "median_abs_offset_delta_ms":
                    round(float(np.median(b)), 1),
                "n_chars_over_100ms": int((a > 100).sum()),
                "n_chars_over_200ms": int((a > 200).sum()),
                "median_aligner_offset_ms":
                    round(float(np.median(aln_off[oid])), 1),
                # §G5K: ASR confidence = lyric intelligibility
                # (diction clarity), NOT acoustic timing confidence
                "min_intelligibility_probability":
                    round(min(probs[oid]), 3)}
            ta = a[np.asarray(probs[oid]) >= MIN_TIMING_CHAR_PROB]
            out["stats"][oid]["trusted_max_abs_onset_delta_ms"] = \
                round(float(ta.max()), 1) if ta.size else None
            # §10.1.5A-G5J-rlv5: the REAL acoustic gate — onset-strength
            # peaks measured with ONE instrument on both sides, so
            # detector bias cancels (whisper-vs-whisper deltas above
            # stay diagnostic only — on synthetic audio that aligner
            # reported boundaries ~200-500ms early and would false-
            # gate every item). Gate reads only chars with a real
            # onset-peak source ref AND a detected render peak; a
            # missing peak is already flagged unmeasurable above.
            if refs is not None and ac_on.get(oid):
                # §G5K: the delta gate judges class_A chars only —
                # a held B2 anchor's 'error' is a carrier conflict
                # already flagged by its route, not a timing miss to
                # re-measure, and B1 has no landmark to delta against.
                ad = [abs((ac_on[oid][k] - refs[k]) * 1000.0)
                      for k in range(len(src))
                      if refs[k] is not None
                      and k < len(ref_kinds)
                      and ref_kinds[k] == "onset_peak"
                      and k not in ac_unstable
                      and (k >= len(char_routes)
                           or char_routes[k].get("route")
                           == ROUTE_CLASS_A)
                      and ac_on[oid][k] is not None]
                out["stats"][oid]["median_abs_acoustic_delta_ms"] = (
                    round(float(np.median(ad)), 1) if ad else None)
                out["stats"][oid]["max_abs_acoustic_delta_ms"] = (
                    round(float(max(ad)), 1) if ad else None)
                if ad and max(ad) > TIMING_GATE_MS:
                    out["flags"].append(
                        f"lyric_timing_acoustic_delta:{oid}:"
                        f"{max(ad):.0f}ms")
        loop = ((man.get("calibration") or {}).get("lyric_evidence")
                or {}).get("articulation", {}).get("closed_loop")
        if loop:
            out["convergence_iterations"] = len(
                loop.get("iterations") or []) - 1
            out["converged"] = bool(loop.get("converged"))
    return out


def signal_qc(man: dict, idir: Path) -> dict:
    """§10.1.5A-G5B: machine-readable signal audit of one rendered item.

    Crops BASELINE/CANDIDATE_TARGET.wav (G5A) and _CORE.wav (G5D) from
    the real renders, measures full-phrase level/timing drift +
    pre/target/post A/B diff ratios, computes operation-aware per-child
    F0 QC vs the source vocal (G5C), and auto-flags conditions that
    disqualify human review (phrase-wide bleed, loudness drift,
    unavailable/ambiguous child evidence)."""
    import numpy as np
    import soundfile as sf
    from .review.render import _file_sha
    idir = Path(idir)
    cal = man["calibration"]
    base_id, cand_id = cal["baseline_option"], cal["candidate_role"]
    owav = {o["option_id"]: o["wav"] for o in man["options"]}
    region = [float(x) for x in man["target_group"]["region"]]
    ph_start = float(man["phrase"]["start"])
    t0 = max(0.0, region[0] - TARGET_FOCUS_PAD_S)
    t1 = region[1] + TARGET_FOCUS_PAD_S
    focus = {}
    for oid, name in ((base_id, "BASELINE_TARGET.wav"),
                      (cand_id, "CANDIDATE_TARGET.wav")):
        focus[name] = _crop_rendered(idir / owav[oid], idir / name,
                                     t0 - ph_start, t1 - ph_start)
    b, sr = sf.read(str(idir / owav[base_id]), dtype="float32",
                    always_2d=True)
    c, _ = sf.read(str(idir / owav[cand_id]), dtype="float32",
                   always_2d=True)
    n = min(len(b), len(c))
    b, c = b[:n], c[:n]
    reg0 = max(0, min(n, int((region[0] - ph_start) * sr)))
    reg1 = max(reg0, min(n, int((region[1] - ph_start) * sr)))

    def rms(x):
        return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0

    def peak(x):
        return float(np.abs(x).max()) if x.size else 0.0

    def sil(x):
        return round(float((np.abs(x) < 0.0032).mean()), 4)

    rb, rc = rms(b), rms(c)
    loud = rc / rb if rb > 1e-6 else None
    pre = _segment_ab_ratio(b, c, 0, reg0)
    tgt = _segment_ab_ratio(b, c, reg0, reg1)
    post = _segment_ab_ratio(b, c, reg1, n)
    # §10.1.5A-G5F Blocker 3: quantify the renderer global-context
    # effect honestly — per-window best-lag shows the duration model's
    # constant timing shift on context notes; aligned residual shows
    # the real acoustic smear. Recorded as data, never hidden.
    shift_win = int(0.2 * sr)
    max_lag = int(0.02 * sr)
    shift_prof = {"pre": [], "post": []}
    aligned_res = {"pre": [], "post": []}
    for s in range(0, n - shift_win + 1, shift_win // 2):
        t_mid = ph_start + (s + shift_win // 2) / sr
        zone = ("pre" if t_mid < region[0] else
                "post" if t_mid > region[1] else None)
        if zone is None:
            continue
        xa = b[s:s + shift_win, 0]
        xb = c[s:s + shift_win, 0]
        if rms(xa) < 0.008:
            continue
        lag, conf = _best_lag(xa, xb, max_lag)
        shift_prof[zone].append(round(lag / sr * 1000, 2))
        aligned_res[zone].append(
            round(float(np.sqrt(max(0.0, 2.0 * (1.0 - conf)))), 3))

    def _med(xs):
        return round(float(np.median(xs)), 3) if xs else None

    renderer_ctx = {
        "effect": ("deterministic renderer; declared patch's phoneme "
                   "delta propagates a constant timing shift + small "
                   "acoustic smear into context notes (DiffSinger "
                   "duration model attends the full phoneme sequence)"),
        "canonical_pre_ab_diff_rms_ratio": pre,
        "canonical_post_ab_diff_rms_ratio": post,
        "canonical_target_ab_diff_rms_ratio": tgt,
        "timing_shift_ms_median": {z: _med(v)
                                   for z, v in shift_prof.items()},
        "aligned_residual_median": {z: _med(v)
                                    for z, v in aligned_res.items()},
        # audit-visible, non-blocking: the canonical bleed stays on the
        # record; the review gate measures the listen surface instead
        "flags": ([f"pre_target_ab_drift:{round(pre, 3)}"]
                  if pre is not None and pre > QC_DRIFT_RATIO_FLAG else []) +
                 ([f"post_target_ab_drift:{round(post, 3)}"]
                  if post is not None and post > QC_DRIFT_RATIO_FLAG else []),
    }
    flags = []
    # canonical loudness imbalance is a real render defect (the listen
    # surface compensates it via shared gain, but the defect is still
    # recorded and still flags the package for audit)
    if loud is not None and not QC_LOUDNESS_RANGE[0] <= loud \
            <= QC_LOUDNESS_RANGE[1]:
        flags.append(f"option_loudness_drift:{round(loud, 3)}")
    # §10.1.5A-G5D: narrower CORE crops (region ±0.15s) from the same
    # renders — 100–300ms child transitions are not drowned by context.
    core_t0 = max(0.0, region[0] - TARGET_CORE_PAD_S)
    core_t1 = region[1] + TARGET_CORE_PAD_S
    for oid, name in ((base_id, "BASELINE_CORE.wav"),
                      (cand_id, "CANDIDATE_CORE.wav")):
        _crop_rendered(idir / owav[oid], idir / name,
                       core_t0 - ph_start, core_t1 - ph_start)
    foc = idir / "SOURCE_FOCUS_separated_vocal.wav"
    if foc.exists():
        fs0 = max(0.0, region[0] - SOURCE_FOCUS_PAD_S)
        _crop_rendered(foc, idir / "SOURCE_CORE_separated_vocal.wav",
                       core_t0 - fs0, core_t1 - fs0)
    foc_m = idir / "SOURCE_FOCUS_original_mix.wav"
    if foc_m.exists():
        _crop_rendered(foc_m, idir / "SOURCE_CORE_original_mix.wav",
                       core_t0 - fs0, core_t1 - fs0)
    # §10.1.5A-G5E/G5F listening surface: baseline-side LISTEN copy is
    # canonical; candidate-side is the shared-context splice — A/B are
    # bit-identical outside the splice edges. The review-safety gate
    # measures THIS surface (what the user actually hears).
    listen = _listen_copies(
        idir, owav, man, [region[0] - ph_start, region[1] - ph_start])
    la, _ = sf.read(str(idir / f"{base_id}_LISTEN.wav"),
                    dtype="float32", always_2d=True)
    lb, _ = sf.read(str(idir / f"{cand_id}_LISTEN.wav"),
                    dtype="float32", always_2d=True)
    nl = min(len(la), len(lb))
    e0 = max(0, min(nl, int(listen["fade_zone_rel"][0] * sr)))
    e1 = max(e0, min(nl, int(listen["fade_zone_rel"][1] * sr)))
    listen_pre = _segment_ab_ratio(la[:nl], lb[:nl], 0, e0)
    listen_post = _segment_ab_ratio(la[:nl], lb[:nl], e1, nl)
    listen_outside = max(listen_pre or 0.0, listen_post or 0.0)
    if listen_outside > QC_LISTEN_OUTSIDE_FLAG:
        flags.append(f"listen_outside_drift:{round(listen_outside, 4)}")
    ldelta = listen.get("ab_loudness_delta_db")
    if ldelta is not None and abs(ldelta) > QC_LISTEN_DELTA_DB_FLAG:
        flags.append(f"listen_loudness_delta:{ldelta}")
    # §10.1.5A-G5C: operation-aware per-child F0 + source-distance
    f0_qc = child_f0_qc(man, idir)
    if f0_qc["unavailable_child_slots"]:
        flags.append(
            f"f0_unavailable_slots:{f0_qc['unavailable_child_slots']}")
    flags += [f"octave_ambiguous:{a}" for a in
              f0_qc["ambiguous_children"]]
    if f0_qc["baseline_structure_error"] is None \
            or f0_qc["candidate_structure_error"] is None:
        flags.append("f0_structure_evidence_insufficient")
    # §10.1.5A-G5I: lyric timing — a rendered option that can't
    # reproduce the source char sequence (mismatch / aligner failure)
    # is fail-closed; numeric onset/offset deltas are persisted for
    # the acceptance decision, not hidden behind a flag.
    lt = _lyric_timing_qc(man, idir)
    if lt is not None:
        flags += lt["flags"]
    return {
        "schema": CALIB_SCHEMA,
        "cal_item_id": man["review_item_id"],
        "repair_id": cal["repair_id"],
        "sample_rate": sr, "duration": round(n / sr, 4),
        "baseline_rms": round(rb, 6), "candidate_rms": round(rc, 6),
        "baseline_peak": round(peak(b), 6),
        "candidate_peak": round(peak(c), 6),
        "silence_fraction": {"baseline": sil(b), "candidate": sil(c)},
        "declared_region": region,
        "target_window": {"absolute": [round(t0, 4), round(t1, 4)],
                          "phrase_relative":
                              [round(t0 - ph_start, 4),
                               round(t1 - ph_start, 4)],
                          "pad_s": TARGET_FOCUS_PAD_S},
        "pre_target_ab_diff_rms_ratio": pre,
        "target_ab_diff_rms_ratio": tgt,
        "post_target_ab_diff_rms_ratio": post,
        "option_loudness_ratio": round(loud, 4) if loud else None,
        "renderer_global_context": renderer_ctx,
        "listen_surface": {
            "construction": listen["construction"],
            "splice_edges_rel": listen["splice_edges_rel"],
            "fade_zone_rel": listen["fade_zone_rel"],
            "edge_lag": listen["edge_lag"],
            "pre_outside_ab_diff_rms_ratio": listen_pre,
            "post_outside_ab_diff_rms_ratio": listen_post,
            "outside_max_ratio": round(listen_outside, 4)},
        "core_window": {"absolute": [round(core_t0, 4), round(core_t1, 4)],
                        "pad_s": TARGET_CORE_PAD_S},
        "listen": listen,
        "f0_qc": f0_qc,
        "lyric_timing": lt,
        "target_focus_sha256": _sha({
            "baseline": _file_sha(idir / "BASELINE_TARGET.wav"),
            "candidate": _file_sha(idir / "CANDIDATE_TARGET.wav")}),
        "target_core_sha256": _sha({
            "baseline": _file_sha(idir / "BASELINE_CORE.wav"),
            "candidate": _file_sha(idir / "CANDIDATE_CORE.wav")}),
        "target_focus_is_primary": True,
        "auto_flags": flags,
        "auto_review_ready": not flags,
    }


def augment_item(idir: Path) -> dict:
    """(Re)generate the G5A target-focus crops + G5B signal_qc.json for
    one already-rendered item. Reads OPTION wavs only — never re-renders,
    never touches manifest/aph (the decision authority)."""
    idir = Path(idir)
    man = json.loads((idir / "manifest.json").read_text(encoding="utf-8"))
    qc = signal_qc(man, idir)
    _jwrite(idir / "signal_qc.json", qc)
    return qc


def augment_calibration(run_dir: Path, only=None, progress=print) -> dict:
    """G5A/G5B pass over an existing store (or a fresh build): every
    rendered item gets target-focus crops + signal_qc.json."""
    run_dir = Path(run_dir)
    ensure_calib_authority(run_dir)
    plan_p = calib_dir(run_dir) / "plan.json"
    if not plan_p.exists():
        raise RuntimeError("no calibration plan — build packages first")
    plan = json.loads(plan_p.read_text(encoding="utf-8"))
    keep = set(only or [])
    out = {}
    for it in plan["items"]:
        iid = it["cal_item_id"]
        if keep and iid not in keep and it["repair_id"] not in keep \
                and it["note_id"] not in keep:
            continue
        idir = calib_dir(run_dir) / "items" / iid
        if not (idir / "manifest.json").exists():
            continue
        qc = augment_item(idir)
        out[iid] = qc["auto_flags"]
        progress(f"  {iid}: auto_flags={qc['auto_flags'] or 'none'}")
    # §10.1.5A-G5E: phrase-source listening copies at the same target
    # level — generated for every declared phrase, not just augmented
    # items, so git_evidence covers the whole review surface.
    listen = _phrase_listen_copies(calib_dir(run_dir))
    return {"augmented": sorted(out), "flags": out,
            "phrase_listen": listen}


# --------------------------------------------- Git evidence rule (§10.1.5A)

def _git_tracked_set(run_dir: Path):
    """Files committed to Git under the calibration store, calib-dir-
    relative posix paths; None when unavailable/not a worktree."""
    import subprocess
    cdir = calib_dir(run_dir).resolve()
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             cwd=cdir, capture_output=True, text=True,
                             timeout=15)
        if top.returncode != 0:
            return None
        root = Path(top.stdout.strip()).resolve()
        prefix = cdir.relative_to(root).as_posix() + "/"
        out = subprocess.run(["git", "ls-files", "-z", "--", prefix],
                             cwd=root, capture_output=True, timeout=60)
        if out.returncode != 0:
            return None
        raw = out.stdout.decode("utf-8", "replace").split("\0")
        return {p[len(prefix):] for p in raw
                if p.startswith(prefix)}
    except Exception:
        return None


def _git_dirty_set(run_dir: Path):
    """Calib-dir-relative posix paths whose worktree bytes differ from
    HEAD (modified / staged / untracked) — a tracked-but-dirty file is
    NOT committed evidence. None when unavailable/not a worktree."""
    import subprocess
    cdir = calib_dir(run_dir).resolve()
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             cwd=cdir, capture_output=True, text=True,
                             timeout=15)
        if top.returncode != 0:
            return None
        root = Path(top.stdout.strip()).resolve()
        prefix = cdir.relative_to(root).as_posix() + "/"
        out = subprocess.run(
            ["git", "status", "--porcelain", "-z", "--", prefix],
            cwd=root, capture_output=True, timeout=60)
        if out.returncode != 0:
            return None
        dirty = set()
        for ent in out.stdout.decode("utf-8", "replace").split("\0"):
            if len(ent) > 3:
                p = ent[3:]
                if p.startswith(prefix):
                    dirty.add(p[len(prefix):])
        return dirty
    except Exception:
        return None


def git_evidence(run_dir: Path, item_ids=None,
                 include_qc: bool = True) -> dict:
    """§10.1.5A hard rule — 'local file exists' / 'agent says generated'
    never counts; only files actually committed to Git are acceptance
    evidence. A tracked file with uncommitted changes is NOT evidence
    either — the committed bytes must match the worktree."""
    cdir = calib_dir(run_dir)
    if item_ids is None:
        items_dir = cdir / "items"
        item_ids = sorted(d.name for d in items_dir.iterdir()
                          if d.is_dir()) if items_dir.exists() else []
    expected = ["plan.json", "state.json", "pilot_review.json"]
    if include_qc:
        expected += ["qc/verdict.json", "qc/audit.jsonl"]
    # §G5M: once generated, the eligibility inventory IS roster-
    # selection evidence — it must be committed like every other
    # authority artifact
    if (cdir / "eligibility_inventory.json").exists():
        expected.append("eligibility_inventory.json")
    # §10.1.5A-G5E: the full natural-phrase SOURCE clip is the PRIMARY
    # human-review material — it must be Git-evidence too, keyed by each
    # item's declared phrase_key (deduped: items can share a phrase)
    plan_p = cdir / "plan.json"
    phrase_keys = set()
    if plan_p.exists():
        plan = json.loads(plan_p.read_text(encoding="utf-8"))
        phrase_keys = {it["phrase_key"] for it in plan.get("items", [])
                       if it.get("phrase_key")}
    for pk in sorted(phrase_keys):
        expected += [f"phrases/{pk}/SOURCE_PHRASE_original_mix.wav",
                     f"phrases/{pk}/SOURCE_PHRASE_separated_vocal.wav",
                     f"phrases/{pk}/SOURCE_PHRASE_original_mix_LISTEN.wav",
                     f"phrases/{pk}/"
                     "SOURCE_PHRASE_separated_vocal_LISTEN.wav"]
    for iid in item_ids:
        expected += [f"items/{iid}/{f}" for f in GIT_REQUIRED_ITEM_FILES]
    tracked = _git_tracked_set(run_dir)
    if tracked is None:
        return {"complete": False, "git": "unavailable_or_not_a_worktree",
                "missing": expected, "checked": len(expected),
                "item_ids": list(item_ids)}
    dirty = _git_dirty_set(run_dir) or set()
    missing = [e for e in expected if e not in tracked]
    uncommitted = [e for e in expected
                   if e in tracked and e in dirty]
    return {"complete": not missing and not uncommitted, "git": "ok",
            "missing": missing, "uncommitted": uncommitted,
            "checked": len(expected),
            "item_ids": list(item_ids)}


# ------------------------------------------------- plan authority (G5G-C)

def _rph_hash():
    from .review.build import render_profile, render_profile_hash
    return render_profile_hash(render_profile(
        template_sha=_file_sha_local(
            Path(__file__).resolve().parents[2]
            / "configs" / "ustx_template.yaml")))


def _file_sha_local(p):
    from .review.render import _file_sha
    return _file_sha(p)


def plan_invariants(run_dir: Path) -> dict:
    """§10.1.5A-G5G Blocker C: plan.json is a DERIVED snapshot — every
    entry must equal the item's authoritative manifest + signal_qc, and
    the item's recorded contract must equal what CURRENT code computes
    (a lyric-impl bump makes old packages stale). Any mismatch means
    the plan lies about the store → review_ready / pilot / QC PASS all
    blocked. Returns {ok, violations}."""
    cdir = calib_dir(run_dir)
    plan_p = cdir / "plan.json"
    violations = []
    items_dir = cdir / "items"
    has_items = items_dir.exists() and any(
        d.is_dir() for d in items_dir.iterdir())
    if not plan_p.exists():
        # vacuous only when there is nothing to lie about — a store
        # with item dirs but no plan is exactly the lie this gate exists
        # to catch
        return {"ok": not has_items,
                "violations": [] if not has_items
                else ["plan.json missing over a non-empty item store"]}
    plan = json.loads(plan_p.read_text(encoding="utf-8"))
    try:
        from .review.render import load_run
        run = load_run(run_dir)
        rph = _rph_hash()
    except Exception:
        run, rph = None, None
    seen = set()
    for it in plan.get("items", []):
        iid = it["cal_item_id"]
        seen.add(iid)
        mp = cdir / "items" / iid / "manifest.json"
        if not mp.exists():
            violations.append(f"{iid}: manifest missing")
            continue
        man = json.loads(mp.read_text(encoding="utf-8"))
        cal = man.get("calibration", {})
        checks = (
            ("audio_package_hash", it.get("audio_package_hash"),
             man.get("audio_package_hash")),
            ("lyric_contract", it.get("lyric_contract"),
             cal.get("lyric_contract")),
            ("contract_sha256", it.get("contract_sha256"),
             cal.get("contract_sha256")),
            ("package_state", it.get("package_state"),
             man.get("package_state")),
        )
        for field, plan_v, man_v in checks:
            if plan_v != man_v:
                violations.append(
                    f"{iid}: plan.{field}={plan_v!r} != "
                    f"manifest.{field}={man_v!r}")
        qc_p = cdir / "items" / iid / "signal_qc.json"
        qc = json.loads(qc_p.read_text(encoding="utf-8")) \
            if qc_p.exists() else {}
        if it.get("signal_qc_flags") != qc.get("auto_flags"):
            violations.append(
                f"{iid}: plan.signal_qc_flags="
                f"{it.get('signal_qc_flags')!r} != "
                f"signal_qc.auto_flags={qc.get('auto_flags')!r}")
        if run is not None and rph and item_contract_stale(man, run, rph):
            violations.append(
                f"{iid}: stale contract (impl "
                f"{cal.get('lyric_mapping_impl')!r} != current "
                f"{LYRIC_MAPPING_IMPL_VERSION.get(cal.get('lyric_contract'))!r})")
    if items_dir.exists():
        for d in sorted(items_dir.iterdir()):
            if d.is_dir() and d.name not in seen:
                violations.append(
                    f"{d.name}: item dir not covered by plan.json")
    return {"ok": not violations, "violations": violations}


def rebuild_plan(run_dir: Path) -> dict:
    """§10.1.5A-G5G Blocker C: rebuild plan.json FROM the authoritative
    item manifests + signal_qc files — no partial merge, no carried
    stale fields. Preserves plan-level metadata; every item field is
    re-read from its manifest."""
    from .review.render import load_run
    cdir = calib_dir(run_dir)
    prev_p = cdir / "plan.json"
    prev = json.loads(prev_p.read_text(encoding="utf-8")) \
        if prev_p.exists() else {}
    try:
        run = load_run(run_dir)
    except Exception:
        run = None
    items = []
    for d in sorted((cdir / "items").iterdir()):
        if not d.is_dir():
            continue
        mp = d / "manifest.json"
        if not mp.exists():
            continue
        man = json.loads(mp.read_text(encoding="utf-8"))
        if man.get("schema") != CALIB_SCHEMA:
            continue
        cal = man.get("calibration", {})
        qc_p = d / "signal_qc.json"
        qc = json.loads(qc_p.read_text(encoding="utf-8")) \
            if qc_p.exists() else {}
        old = {i["cal_item_id"]: i for i in prev.get("items", [])}
        prior = old.get(d.name, {})
        items.append({
            "cal_item_id": d.name,
            "repair_id": cal.get("repair_id") or prior.get("repair_id"),
            "note_id": prior.get("note_id") or man.get("note_id"),
            "type": prior.get("type") or man.get("type"),
            "phrase": man.get("phrase") or prior.get("phrase"),
            "phrase_key": prior.get("phrase_key") or
                man.get("phrase_key"),
            "plan_hash": prior.get("plan_hash"),
            "audio_package_hash": man.get("audio_package_hash"),
            "package_state": man.get("package_state"),
            "lyric_contract": cal.get("lyric_contract"),
            "contract_sha256": cal.get("contract_sha256"),
            "signal_qc_flags": qc.get("auto_flags"),
            "semantic_diff_sha256": cal.get("semantic_diff_sha256"),
            "manifest": str(mp),
        })
    items.sort(key=lambda x: (x.get("phrase") or {}).get("start", 0))
    plan_doc = dict(prev)
    plan_doc.update({"schema": CALIB_SCHEMA, "created_at": _now(),
                     "diagnostic_run_id":
                         (run or {}).get("run_id")
                         or prev.get("diagnostic_run_id"),
                     "candidate0_sha256":
                         (run or {}).get("candidate0_sha256")
                         or prev.get("candidate0_sha256"),
                     "items": items})
    _jwrite(prev_p, plan_doc)
    return plan_doc


# §10.1.5A-G5E/G5F/G5G: representative items for the remote pilot.
# After the rlv2 fail-closed gap rule the honest pilot is FOUR items —
# every other evidence-passing item (0012/0044/0246/0248) carries an
# unmapped note after a real gap, where '+' is unrenderable (probe-
# verified) and any hanzi would be a guess, so they all fail closed.
# The 13 remaining items have no aligned char evidence at all.
# These four pass the evidence gate AND map cleanly AND carry no
# signal_qc flags: 0061 (37.8s), 0188 (90.4s), 0192 (90.4s — same
# phrase, different target note), 0379 (178.0s).
PILOT_NOTE_IDS = ("note_0061", "note_0188", "note_0192", "note_0379")

# Chat reply → official decide() choice. A/B keep the blind map;
# 无法判断 collapses to none_correct — both mean `unresolved`, never
# repair authority.
PILOT_REPLY_MAP = {"A": "OPTION_0", "B": "OPTION_1",
                   "都差不多": "equivalent",
                   "都不对": "none_correct",
                   "无法判断": "none_correct"}


def _git_remote_repo(run_dir: Path) -> dict:
    """owner/repo + current HEAD sha from the local clone — the raw-url
    base for downloadable review audio is derived, never hardcoded."""
    import subprocess
    def _g(*a):
        r = subprocess.run(["git", *a], cwd=str(run_dir),
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    url = _g("remote", "get-url", "origin") or ""
    sha = _g("rev-parse", "HEAD")
    slug = None
    if url.endswith(".git"):
        url = url[:-4]
    m = url.rstrip("/").rsplit("/", 2)
    if len(m) == 3:
        slug = f"{m[1]}/{m[2]}"
    return {"slug": slug, "sha": sha, "remote": url or None}


def build_pilot_review(run_dir: Path, note_ids=None,
                       write: bool = True) -> dict:
    """§10.1.5A-G5E remote-review payload: for each pilot item the blind
    A/B full-phrase wavs + the shared SOURCE_PHRASE clips, each with its
    Git path, canonical sha256 and downloadable raw URL at the current
    HEAD. ChatGPT/maintainer turns this into download links; the user's
    reply still has to go through decide() to become authority."""
    from .review.render import _file_sha
    run_dir = Path(run_dir)
    cdir = calib_dir(run_dir)
    # §10.1.5A-G5G Blocker C/D: never emit a pilot payload over a lying
    # plan — the reviewer would download bytes the plan misdescribes
    inv = plan_invariants(run_dir)
    if not inv["ok"]:
        raise RuntimeError(
            "pilot payload blocked (§10.1.5A-G5G plan-invariant rule): "
            f"{inv['violations'][:3]}")
    plan = json.loads((cdir / "plan.json").read_text(encoding="utf-8"))
    by_note = {it["note_id"]: it for it in plan.get("items", [])}
    remote = _git_remote_repo(run_dir)
    repo_root = Path(run_dir).parent.parent
    # §G5M-M10: once an eligibility inventory exists, the review
    # surface binds ONLY its honest roster — a disqualified or
    # historical item can never ride the payload into review, and an
    # empty roster means there is nothing to emit.
    inv_p = cdir / "eligibility_inventory.json"
    if inv_p.exists():
        inv_doc = json.loads(inv_p.read_text(encoding="utf-8"))
        allowed = set(inv_doc.get("roster_candidates") or [])
        if note_ids is None:
            note_ids = tuple(sorted(allowed))
        else:
            bad = [n for n in note_ids if n not in allowed]
            if bad:
                raise RuntimeError(
                    "pilot payload blocked (§G5M honest-roster "
                    f"rule): {bad} are not eligible under the "
                    "current inventory — the review surface binds "
                    "the honest roster only")
        if not note_ids:
            raise RuntimeError(
                "pilot payload blocked (§G5M honest-roster rule): "
                "the eligibility inventory selected ZERO honest "
                "items — no review surface is emitted while "
                "review_ready=false")
    note_ids = tuple(note_ids) if note_ids else PILOT_NOTE_IDS

    def entry(rel: str, label: str, display: str = None):
        p = repo_root / rel
        e = {"label": label, "git_path": rel,
             # canonical path may embed the role (BASELINE_CORE.wav) —
             # the display layer must use this neutral name as link text
             "display_name": display or Path(rel).name}
        if p.exists():
            e["sha256"] = _file_sha(p)
            e["bytes"] = p.stat().st_size
        else:
            e["sha256"] = None
            e["missing"] = True
        if remote["slug"] and remote["sha"]:
            e["raw_url"] = ("https://raw.githubusercontent.com/"
                            f"{remote['slug']}/{remote['sha']}/{rel}")
        return e

    prefix = f"runs/{run_dir.name}/structure_calibration"
    groups = []
    for i, nid in enumerate(note_ids, 1):
        it = by_note.get(nid)
        if it is None:
            groups.append({"group": i, "note_id": nid,
                           "error": "no calibration item"})
            continue
        iid, pk = it["cal_item_id"], it["phrase_key"]
        dur = round(it["phrase"]["end"] - it["phrase"]["start"], 3)
        # primary = gain-matched LISTEN copies (what the reviewer
        # actually hears); canonical = the authority-bound bytes the
        # decision/aph still references.
        files = {
            "SOURCE": entry(f"{prefix}/phrases/{pk}/"
                            "SOURCE_PHRASE_original_mix_LISTEN.wav",
                            "原唱", "SOURCE.wav"),
            "SOURCE_VOCAL": entry(
                f"{prefix}/phrases/{pk}/"
                "SOURCE_PHRASE_separated_vocal_LISTEN.wav",
                "原唱分离人声", "SOURCE_VOCAL.wav"),
            "A": entry(f"{prefix}/items/{iid}/OPTION_0_LISTEN.wav",
                       "A", "A.wav"),
            "B": entry(f"{prefix}/items/{iid}/OPTION_1_LISTEN.wav",
                       "B", "B.wav"),
        }
        canon = {
            "SOURCE": f"{prefix}/phrases/{pk}/"
                      "SOURCE_PHRASE_original_mix.wav",
            "SOURCE_VOCAL": f"{prefix}/phrases/{pk}/"
                            "SOURCE_PHRASE_separated_vocal.wav",
            "A": f"{prefix}/items/{iid}/OPTION_0.wav",
            "B": f"{prefix}/items/{iid}/OPTION_1.wav",
        }
        for k, rel in canon.items():
            p = repo_root / rel
            files[k]["canonical"] = {
                "git_path": rel,
                "sha256": _file_sha(p) if p.exists() else None}
        aux = {"SOURCE_CORE": entry(
                   f"{prefix}/items/{iid}/"
                   "SOURCE_CORE_original_mix.wav", "原唱·定位",
                   "SOURCE_CORE.wav")}
        # role-mapped file names must not leak: publish aux crops only
        # under blind labels — resolve OPTION_i -> {BASELINE,CANDIDATE}
        man = json.loads((cdir / "items" / iid
                          / "manifest.json").read_text(encoding="utf-8"))
        cal = man.get("calibration") or {}
        opt_map = {o["option_id"]: (
            "BASELINE" if o["option_id"] == cal.get("baseline_option")
            else "CANDIDATE") for o in man.get("options", [])}
        for lbl, oid in (("A", "OPTION_0"), ("B", "OPTION_1")):
            role = opt_map.get(oid)
            if role:
                aux[f"{lbl}_CORE"] = entry(
                    f"{prefix}/items/{iid}/{role}_CORE.wav",
                    f"{lbl}·定位", f"{lbl}_CORE.wav")
                aux[f"{lbl}_FOCUS"] = entry(
                    f"{prefix}/items/{iid}/{role}_TARGET.wav",
                    f"{lbl}·聚焦", f"{lbl}_FOCUS.wav")
        groups.append({
            "group": i, "note_id": nid, "cal_item_id": iid,
            "repair_id": it["repair_id"], "type": it["type"],
            "phrase": it["phrase"], "phrase_key": pk,
            "phrase_duration_s": dur,
            "audio_package_hash": it.get("audio_package_hash"),
            "files": files, "auxiliary": aux,
        })
    payload = {
        "schema": CALIB_SCHEMA, "kind": "pilot_review",
        "generated_at": _now(), "run_id": run_dir.name,
        "git": remote,
        "primary_review_unit": "full_natural_phrase",
        "blind_map": {"A": "OPTION_0", "B": "OPTION_1"},
        "reply_map": dict(PILOT_REPLY_MAP),
        "decision_command": ("agent2utau structure-calib-decide "
                             f"{run_dir.name} <cal_item_id> <choice>"),
        "groups": groups,
    }
    if write:
        _jwrite(cdir / "pilot_review.json", payload)
    return payload


def _phrase_level_conflicts(cdir: Path) -> dict:
    """§G5L: an overlapping B2 char set repeating across review targets
    on the SAME phrase is a phrase-level carrier conflict — systematic
    written-vs-articulation incompatibility, not a per-item render
    accident. For every affected manifest the closed_loop records
      phrase_level_carrier_conflict = true
      phrase_level_conflict_id      = phrase_key
      shared_b2_chars               = [...]
    and each affected char's route gains phrase_level_conflict_id and
    is upgraded to route_detail=structure_timing_suspect (repeated
    across independent targets is structural evidence, stronger than
    any single-target triage detail).
    Returns {cal_item_id: [shared chars]}."""
    items_d = cdir / "items"
    if not items_d.exists():
        return {}
    by_phrase = {}
    for d in sorted(items_d.iterdir()):
        mp = d / "manifest.json"
        if not mp.exists():
            continue
        man = json.loads(mp.read_text(encoding="utf-8"))
        ph = man.get("phrase") or {}
        if ph.get("start") is None or ph.get("end") is None:
            continue
        pkey = f"{float(ph['start']):.2f}-{float(ph['end']):.2f}"
        cl = (((man.get("calibration") or {})
               .get("lyric_evidence") or {})
              .get("articulation") or {}).get("closed_loop") or {}
        routes = cl.get("char_routes") or []
        b2 = {r["char"] for r in routes if r.get("route") == ROUTE_B2}
        by_phrase.setdefault(pkey, []).append(
            (d.name, mp, man, routes, b2))
    marked = {}
    for pkey, entries in by_phrase.items():
        if len(entries) < 2:
            continue
        shared = set.intersection(*[e[4] for e in entries])
        if not shared:
            continue
        for iid, mp, man, routes, b2 in entries:
            chars_here = shared & b2
            if not chars_here:
                continue
            cl = man["calibration"]["lyric_evidence"]["articulation"][
                "closed_loop"]
            cl["phrase_level_carrier_conflict"] = True
            cl["phrase_level_conflict_id"] = pkey
            cl["shared_b2_chars"] = sorted(chars_here)
            for r in routes:
                if r.get("char") in chars_here:
                    r["phrase_level_conflict_id"] = pkey
                    r["route_detail"] = "structure_timing_suspect"
            _jwrite(mp, man)
            marked[iid] = sorted(chars_here)
    return marked


# ------------------------------------------------- §G5M eligibility inventory

# Disqualifier → diagnosis lane (§G5M: hard cases are ROUTED to the
# matching diagnosis, never silently dropped or tuned into eligibility).
_DIAGNOSIS_LANES = {
    "lyric_evidence": "lyric_intelligibility_diagnosis",
    "unbindable_chars": "structure_diagnosis",
    "source_unmeasurable": "measurement_diagnosis",
    "unresolved_B1": "measurement_diagnosis",
    "unresolved_B2": "written_timing_diagnosis",
    "phrase_level_carrier_conflict": "structure_diagnosis",
}


def _eligibility_routes_summary(routes):
    """Slim per-char route table for the inventory — the audit needs
    the same fields a manifest persists, not a second schema."""
    if routes is None:
        return None
    return [{"char": r["char"], "route": r["route"],
             "direction": r.get("direction"),
             "route_detail": r.get("route_detail"),
             "route_subtype": r.get("route_subtype"),
             "overhang_ms": r.get("overhang_ms"),
             "unmeasurable_reason": r.get("unmeasurable_reason"),
             "source_ref_onset": r.get("source_ref_onset"),
             "carrier_lo": r.get("carrier_lo"),
             "carrier_hi": r.get("carrier_hi")}
            for r in routes]


def eligibility_inventory(run_dir: Path, write: bool = True,
                          progress=print) -> dict:
    """§G5M honest-roster gate — scan EVERY machine split candidate
    under the CURRENT real_lyric_review contract and record why it can
    or cannot enter the human pilot.

    The decisive evidence is render-free: the pre-loop route
    classification depends only on source landmarks and written
    carrier bounds, neither of which a render can change. A B1/B2 or
    lyric-evidence failure disqualifies without a single wav being
    re-rendered; render-side checks (post-loop downgrades, signal_qc
    flags, verify_package) are additionally recorded when a current-
    contract package already exists, and remain mandatory gates for
    any item that is rebuilt.

    Persisted as eligibility_inventory.json — auditable
    roster-selection evidence. Items failing a hard gate are routed to
    a diagnosis lane, never silently dropped."""
    from .review.render import load_run, _clip, verify_package
    run_dir = Path(run_dir)
    cdir = calib_dir(run_dir)
    run = load_run(run_dir)
    rph = _rph_hash()
    contract_sha = render_contract_sha(
        run, rph, LYRIC_CONTRACT_REVIEW)
    items = plan_calibration(
        run, rph=rph, lyric_contract=LYRIC_CONTRACT_REVIEW)
    entries, pending = [], []
    for it in items:
        pk, iid = it["phrase_key"], it["item_id"]
        ent = {"note_id": it["packets"][0], "cal_item_id": iid,
               "repair_id": it["repair_id"], "type": it["type"],
               "phrase_key": pk,
               "phrase": {"start": it["phrase"]["start"],
                          "end": it["phrase"]["end"]}}
        # --- existing package state (informational; staleness is
        # fixed by rebuild, never by eligibility fiat) ---
        idir = cdir / "items" / iid
        mp = idir / "manifest.json"
        man = json.loads(mp.read_text(encoding="utf-8")) \
            if mp.exists() else None
        cal = (man or {}).get("calibration") or {}
        qc_p = idir / "signal_qc.json"
        qc = json.loads(qc_p.read_text(encoding="utf-8")) \
            if qc_p.exists() else {}
        ent["package_state"] = (man or {}).get("package_state")
        ent["lyric_contract"] = cal.get("lyric_contract")
        ent["lyric_mapping_impl"] = cal.get("lyric_mapping_impl")
        ent["contract_sha256"] = cal.get("contract_sha256")
        ent["contract_status"] = (
            "missing" if man is None else
            "current" if cal.get("contract_sha256") == contract_sha
            else "stale")
        if man is not None:
            try:
                ok, why = verify_package(man, idir)
            except Exception as e:
                ok, why = False, str(e)
            ent["verify_package"] = "PASS" if ok else f"FAIL:{why}"
        else:
            ent["verify_package"] = None
        ent["signal_qc_auto_review_ready"] = qc.get("auto_review_ready")
        ent["signal_qc_flags"] = qc.get("auto_flags") or []
        ent["audio_package_hash"] = (man or {}).get("audio_package_hash")
        # --- post-loop evidence already on disk (rlv7 packages) ---
        cl = (((cal.get("lyric_evidence") or {})
               .get("articulation") or {}).get("closed_loop") or {})
        ent["closed_loop_stop_reason"] = cl.get("reason")
        ent["closed_loop_converged"] = cl.get("converged")
        post = cl.get("char_routes") or []
        ent["post_loop_final_class"] = {
            r["char"]: r.get("final_class") for r in post} or None
        ent["second_family_verdicts"] = {
            r["char"]: r.get("secondary_measurement")
            for r in post if r.get("secondary_measurement")} or None
        # --- lyric evidence under the CURRENT contract ---
        ev = review_phrase_chars(
            run, it.get("evidence_window") or it["phrase"])
        ent["lyric_evidence"] = {
            "ok": ev["ok"], "reason": ev["reason"],
            "min_probability": ev["min_probability"],
            "n_chars": ev["n_chars"]}
        dq, routes = [], None
        if not ev["ok"]:
            dq.append(f"lyric_evidence:{ev['reason']}")
        else:
            chars = ev["chars"]
            bounds = _anchor_bounds(it, chars)
            if bounds is None:
                dq.append("unbindable_chars")
            else:
                lo, hi = bounds
                sw = (cdir / "phrases" / pk
                      / "SOURCE_PHRASE_separated_vocal.wav")
                if not sw.exists():
                    # the review window is lyric-padded — its phrase
                    # clip may not exist yet; the measurement still
                    # needs the real source span
                    sw.parent.mkdir(parents=True, exist_ok=True)
                    _clip(run["vocals_wav"], sw,
                          it["phrase"]["start"], it["phrase"]["end"])
                ph0 = float(it["phrase"]["start"])
                refs, kinds = _source_ref_onsets(chars, sw, ph0)
                routes = _classify_routes(
                    chars, refs, kinds, lo, hi, off=ph0)
                n_onset = sum(1 for k in kinds
                              if k == "onset_peak")
                ent["source_measurement"] = {
                    "wav": str(sw.relative_to(cdir)),
                    "n_chars": len(chars),
                    "n_onset_landmarks": n_onset,
                    "available": refs is not None}
                if refs is None:
                    dq.append("source_unmeasurable")
                b1 = [r for r in routes
                      if r["route"] == ROUTE_B1]
                b2 = [r for r in routes
                      if r["route"] == ROUTE_B2]
                ent["route_summary"] = {
                    "class_A": sum(1 for r in routes
                                   if r["route"] == ROUTE_CLASS_A),
                    "B1_unmeasurable": len(b1),
                    "B2_carrier_conflict": len(b2)}
                if b1:
                    dq.append("unresolved_B1:"
                              + "".join(r["char"] for r in b1))
                if b2:
                    dq.append("unresolved_B2:"
                              + "".join(r["char"] for r in b2))
        ent["char_routes"] = _eligibility_routes_summary(routes)
        ent["disqualifiers"] = dq
        ent["phrase_level_carrier_conflict"] = False
        ent["shared_b2_chars"] = []
        entries.append(ent)
        pending.append((ent, routes))
    # --- phrase-level: a B2 set repeating across review targets on
    # the same phrase is systematic, never an ordinary pilot item ---
    by_pk = {}
    for ent, routes in pending:
        if routes:
            b2 = {r["char"] for r in routes
                  if r["route"] == ROUTE_B2}
            by_pk.setdefault(ent["phrase_key"], []).append((ent, b2))
    for pk, grp in by_pk.items():
        if len(grp) < 2:
            continue
        shared = set.intersection(*[b2 for _, b2 in grp])
        if not shared:
            continue
        for ent, b2 in grp:
            mine = shared & b2
            if not mine:
                continue
            ent["phrase_level_carrier_conflict"] = True
            ent["shared_b2_chars"] = sorted(mine)
            ent["disqualifiers"].append(
                "phrase_level_carrier_conflict:"
                + "".join(sorted(mine)))
    # --- verdicts + diagnosis lanes ---
    for ent in entries:
        ent["eligible"] = not ent["disqualifiers"]
        lanes = {_DIAGNOSIS_LANES[d.split(":")[0]]
                 for d in ent["disqualifiers"]
                 if d.split(":")[0] in _DIAGNOSIS_LANES}
        # written-timing suspects and structure-level conflicts are
        # both written-score diagnoses at the route_detail level
        if ent["phrase_level_carrier_conflict"]:
            lanes.add("structure_diagnosis")
        ent["diagnosis_routes"] = sorted(lanes)
        ent["rebuild_required"] = (
            ent["eligible"] and ent["contract_status"] != "current")
    roster = [e["note_id"] for e in entries if e["eligible"]]
    doc = {"schema": CALIB_SCHEMA,
           "kind": "eligibility_inventory",
           "generated_at": _now(), "run_id": run_dir.name,
           "lyric_contract": LYRIC_CONTRACT_REVIEW,
           "lyric_mapping_impl":
               LYRIC_MAPPING_IMPL_VERSION[LYRIC_CONTRACT_REVIEW],
           "contract_sha256": contract_sha,
           "items": entries,
           "summary": {
               "n_items": len(entries),
               "n_eligible": len(roster),
               "n_lyric_evidence_fail": sum(
                   1 for e in entries
                   if any(d.startswith("lyric_evidence:")
                          for d in e["disqualifiers"])),
               "n_unresolved_B1": sum(
                   1 for e in entries
                   if any(d.startswith("unresolved_B1:")
                          for d in e["disqualifiers"])),
               "n_unresolved_B2": sum(
                   1 for e in entries
                   if any(d.startswith("unresolved_B2:")
                          for d in e["disqualifiers"])),
               "n_phrase_level": sum(
                   1 for e in entries
                   if e["phrase_level_carrier_conflict"]),
               "n_rebuild_required": sum(
                   1 for e in entries if e["rebuild_required"])},
           "roster_candidates": roster,
           "roster_size_ok": len(roster) >= 3}
    if write:
        _jwrite(cdir / "eligibility_inventory.json", doc)
    if progress:
        s = doc["summary"]
        progress(f"eligibility inventory: {s['n_eligible']}/"
                 f"{s['n_items']} eligible "
                 f"(B1:{s['n_unresolved_B1']} B2:{s['n_unresolved_B2']} "
                 f"phrase-level:{s['n_phrase_level']} "
                 f"lyric-evidence:{s['n_lyric_evidence_fail']})")
        if not doc["roster_size_ok"]:
            progress("  insufficient honest items — review_ready "
                     "stays false; disqualified items are routed to "
                     "diagnosis lanes, not tuned into eligibility")
    return doc


def build_calibration(run_dir: Path, cfg=None, render=True, only=None,
                      progress=print, lyric_contract=None) -> dict:
    """Build (and render) phrase A/B packages for machine structure
    candidates. m25-cal-2 (§10.1.5A): a FULL batch (no `only`) requires
    a pre-human QC PASS verdict for the current render contract —
    samples (only=...) are the pre-QC path."""
    from .review.render import (load_run, render_item, item_manifest,
                                _clip, render_provenance, _file_sha)
    from .review.build import (render_profile, render_profile_hash)
    run_dir = Path(run_dir)
    ensure_calib_authority(run_dir)
    run = load_run(run_dir)
    profile = render_profile(
        template_sha=_file_sha(
            Path(__file__).resolve().parents[2]
            / "configs" / "ustx_template.yaml"))
    rph = {"profile": profile, "hash": render_profile_hash(profile)}
    eff_contract = lyric_contract or LYRIC_CONTRACT
    contract_sha = render_contract_sha(run, rph["hash"], eff_contract)
    if not only:
        v = load_verdict(run_dir)
        bound = (v.get("pilot") or {}).get("contract_sha256") if v \
            else None
        if not review_ready(run_dir) or bound != contract_sha:
            raise RuntimeError(
                "full calibration batch blocked (§10.1.5A-G10/G5H): "
                "no committed pre-human QC PASS binding this batch "
                f"contract {contract_sha[:16]} (verdict binds "
                f"{str(bound)[:16]}) — build samples with --items "
                "first, audit them, then structure-calib-qc --pass "
                "--samples ...")
    items = plan_calibration(run, rph=rph["hash"],
                             lyric_contract=eff_contract)
    if only:
        keep = set(only)
        items = [i for i in items if i["item_id"] in keep
                 or i["repair_id"] in keep or i["packets"][0] in keep]
    cdir = calib_dir(run_dir)
    c0_by_id = {f"note_{i:04d}": n
                for i, n in enumerate(run["baseline_notes"])}
    prov = render_provenance(cfg) if render else None
    planned, src_rendered, lyr_evidence = [], {}, {}
    for it in items:
        pkey, ph = it["phrase_key"], it["phrase"]
        pdir = cdir / "phrases" / pkey
        refs = None
        if render:
            if pkey not in src_rendered:
                refs = {
                    "original_mix": _clip(
                        run["original_wav"],
                        pdir / "SOURCE_PHRASE_original_mix.wav",
                        ph["start"], ph["end"]),
                    "separated_vocal": _clip(
                        run["vocals_wav"],
                        pdir / "SOURCE_PHRASE_separated_vocal.wav",
                        ph["start"], ph["end"])}
                for r in refs.values():
                    r["path"] = f"../../phrases/{pkey}/{r['path']}"
                src_rendered[pkey] = refs
                progress(f"  source phrase {pkey} "
                         f"({ph['end'] - ph['start']:.2f}s, "
                         f"{ph['boundary_source']})")
            else:
                refs = src_rendered[pkey]
        idir = cdir / "items" / it["item_id"]
        # §10.1.5A-G5E quality hold: the lyric contract is per-ITEM —
        # a partial re-render may upgrade a subset to real_lyric_review
        # while the rest of the store stays on the neutral contract.
        item_contract = it.get("lyric_contract") or eff_contract
        item_contract_sha = render_contract_sha(run, rph["hash"],
                                                item_contract)
        rres = None
        if render:
            chars = run["chars"]
            if item_contract == LYRIC_CONTRACT_REVIEW:
                if pkey not in lyr_evidence:
                    # §G5J-A: evidence is selected on the ORIGINAL lrc
                    # window — the phrase window itself may have been
                    # expanded to cover char articulation, and the
                    # expanded span must not pull neighbouring chars in.
                    lyr_evidence[pkey] = review_phrase_chars(
                        run, it.get("evidence_window") or ph)
                ev = lyr_evidence[pkey]
                if not ev["ok"]:
                    raise RuntimeError(
                        f"real_lyric_review {it['item_id']}: insufficient "
                        f"aligned char evidence ({ev['reason']}, "
                        f"min_p={ev['min_probability']}, "
                        f"n={ev['n_chars']}) — fail-closed, no review "
                        "package")
                chars = ev["chars"]
            progress(f"  rendering {it['item_id']} "
                     f"({it['type']}, {len(it['options'])} options)")
            if item_contract == LYRIC_CONTRACT_REVIEW:
                # §10.1.5A-G5J: acoustic closed-loop — render, measure
                # each option's onsets with the SAME onset-strength
                # instrument as the source reference, shift render-
                # only anchors opposite the error, rerender to converge.
                _sw = refs.get("separated_vocal", {}).get("path")
                loop = _closed_loop_anchors(
                    cfg, idir, it, chars,
                    src_wav=((idir / _sw).resolve() if _sw else None),
                    progress=progress)
                it["_loop"] = loop
                rres = loop["rres"]
                if not loop["converged"]:
                    progress(f"    closed-loop NOT converged "
                             f"({loop['reason']}) — recorded, "
                             "flagged in QC")
            else:
                rres = render_item(cfg, idir, it, chars)
            # §10.1.5A-G4: focus clips of the contested region from the
            # SOURCE audio — the original melody is the ground truth.
            reg = it["region"]
            _clip(run["original_wav"],
                  idir / "SOURCE_FOCUS_original_mix.wav",
                  max(0.0, reg[0] - SOURCE_FOCUS_PAD_S),
                  reg[1] + SOURCE_FOCUS_PAD_S)
            _clip(run["vocals_wav"],
                  idir / "SOURCE_FOCUS_separated_vocal.wav",
                  max(0.0, reg[0] - SOURCE_FOCUS_PAD_S),
                  reg[1] + SOURCE_FOCUS_PAD_S)
        man = item_manifest(run, it, "structure-calibration", rph,
                            refs, rres, provenance=prov)
        # calibration-specific manifest fields (append, never reshape)
        man["schema"] = CALIB_SCHEMA
        man["calibration"] = {
            "repair_id": it["repair_id"],
            "patch_sha256": _sha(it["patch"]),
            "candidate_role": next(
                o["option_id"] for o in it["options"]
                if o["candidate_id"] != "baseline"),
            "baseline_option": it["baseline_option"],
            "lyric_contract": item_contract,
            "lyric_mapping_impl":
                LYRIC_MAPPING_IMPL_VERSION[item_contract],
            "contract_sha256": item_contract_sha,
            "choices": list(CHOICES),
        }
        diff = semantic_diff(it, c0_by_id)
        _jwrite(idir / "semantic_diff.json", diff)
        man["calibration"]["semantic_diff_sha256"] = _sha(diff)
        if item_contract == LYRIC_CONTRACT_REVIEW:
            ev = lyr_evidence.get(it["phrase_key"])
            # §10.1.5A-G5I: persist the FULL source char-timing table
            # (the audit needs per-char onsets, not just counts) plus
            # the articulation-split summary the render-only overlay
            # produced — Candidate 0 stays untouched, these splits are
            # review-render only.
            art = None
            if ev and ev.get("chars"):
                from .review.build import apply_patch
                from .review.render import review_lyrics_articulated
                segs = review_lyrics_articulated(
                    apply_patch(it["context"],
                                {"type": "identity"}), ev["chars"],
                    anchors=(it.get("_loop") or {}).get("anchors"))
                loop = it.get("_loop")
                if segs is not None:
                    art = {"impl": "rlv7",
                           "n_segments": len(segs),
                           "n_articulation_splits": sum(
                               1 for sg in segs
                               if sg["articulation_split"]),
                           "n_chars": len(ev["chars"])}
                if loop is not None:
                    art = dict(art or {})
                    art.update({
                        "closed_loop": {
                            "converged": loop["converged"],
                            "reason": loop["reason"],
                            "k": loop["k"], "clamp_s": loop["clamp_s"],
                            "tol_ms": loop["tol_ms"],
                            "instrument": loop.get("instrument"),
                            "ref_onsets": loop.get("ref_onsets"),
                            "ref_kinds": loop.get("ref_kinds"),
                            "anchors": loop["anchors"],
                            "bounds": loop["bounds"],
                            "bound_limited":
                                loop.get("bound_limited") or [],
                            "unmeasurable_chars":
                                loop.get("unmeasurable_chars") or [],
                            "char_routes":
                                loop.get("char_routes"),
                            "hard_cases":
                                loop.get("hard_cases") or [],
                            "iterations": loop["iterations"]}})
            man["calibration"]["lyric_evidence"] = {
                "method": "force_align_source_bound",
                "n_chars": ev["n_chars"],
                "min_probability": ev["min_probability"],
                "chars": [{"char": c["char"], "start": c["start"],
                           "end": c["end"],
                           "probability": c.get("probability")}
                          for c in ev["chars"]],
                "articulation": art,
            } if ev else None
        # unblinded copies for pre-human QC — OPTION_* files remain the
        # decision authority; these are review aids only.
        if render and idir.exists():
            base_opt = man["baseline_option"]
            cand_opt = man["calibration"]["candidate_role"]
            for opt, name in ((base_opt, "BASELINE.ustx"),
                              (cand_opt, "CANDIDATE.ustx")):
                src_ustx = idir / f"{opt}.ustx"
                if src_ustx.exists():
                    (idir / name).write_bytes(src_ustx.read_bytes())
        mpath = idir / "manifest.json"
        _jwrite(mpath, man)
        qc_flags = None
        if render and man["package_state"] == "valid":
            qc_flags = augment_item(idir)["auto_flags"]
        planned.append({"cal_item_id": it["item_id"],
                        "repair_id": it["repair_id"],
                        "note_id": it["packets"][0],
                        "type": it["type"], "phrase": it["phrase"],
                        "phrase_key": pkey,
                        "plan_hash": it["plan_hash"],
                        "audio_package_hash": man["audio_package_hash"],
                        "package_state": man["package_state"],
                        "lyric_contract": item_contract,
                        "contract_sha256": item_contract_sha,
                        "signal_qc_flags": qc_flags,
                        "semantic_diff_sha256": _sha(diff),
                        "manifest": str(mpath)})
    # §G5L: phrase-level carrier conflict — a B2 char set repeating
    # across review targets on the same phrase is systematic written-
    # vs-articulation incompatibility, not a per-item render accident.
    # Mark manifests, then refresh QC so the flag is visible in
    # auto_flags too (the audio package hash never covers these files).
    marked = _phrase_level_conflicts(cdir)
    if marked:
        progress(f"  phrase-level carrier conflict: "
                 f"{len(marked)} item(s) share B2 chars across targets")
        for iid in marked:
            mp = cdir / "items" / iid / "manifest.json"
            man2 = json.loads(mp.read_text(encoding="utf-8"))
            qc2 = signal_qc(man2, mp.parent)
            _jwrite(mp.parent / "signal_qc.json", qc2)
            for pit in planned:
                if pit["cal_item_id"] == iid:
                    pit["signal_qc_flags"] = qc2["auto_flags"]
    if only:
        # partial (re)build — merge into the existing plan so the other
        # items' entries survive; per-item lyric_contract/contract_sha
        # keep the store honest under mixed contracts.
        prev_p = cdir / "plan.json"
        prev = (json.loads(prev_p.read_text(encoding="utf-8"))
                if prev_p.exists() else {})
        merged = {i["cal_item_id"]: i for i in prev.get("items", [])}
        merged.update({i["cal_item_id"]: i for i in planned})
        plan_doc = dict(prev)
        plan_doc.update({"schema": CALIB_SCHEMA, "created_at": _now(),
                         "diagnostic_run_id": run["run_id"],
                         "candidate0_sha256": run["candidate0_sha256"],
                         "items": [merged[k] for k in sorted(
                             merged, key=lambda x: merged[x]
                             .get("phrase", {}).get("start", 0))]})
        _jwrite(cdir / "plan.json", plan_doc)
    else:
        _jwrite(cdir / "plan.json",
                {"schema": CALIB_SCHEMA, "created_at": _now(),
                 "diagnostic_run_id": run["run_id"],
                 "candidate0_sha256": run["candidate0_sha256"],
                 "lyric_contract": eff_contract,
                 "contract_sha256": contract_sha,
                 "items": planned})
    progress(f"calibration: {len(planned)} items → {cdir}")
    return {"items": planned, "contract_sha256": contract_sha}


# ------------------------------------------------------------- decisions

def _decisions_path(run_dir: Path) -> Path:
    return calib_dir(run_dir) / "decisions.json"


def load_decisions(run_dir: Path) -> dict:
    ensure_calib_authority(Path(run_dir))
    p = _decisions_path(run_dir)
    if not p.exists():
        return {"schema": CALIB_SCHEMA, "revisions": []}
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("schema") != CALIB_SCHEMA:
        raise RuntimeError(
            f"unsupported calibration decisions schema: {d.get('schema')}")
    return d


def current_decision(run_dir: Path, repair_id: str):
    """Latest non-superseded decision for one repair_id."""
    revs = [r for r in load_decisions(run_dir)["revisions"]
            if r.get("repair_id") == repair_id
            and not r.get("superseded_by")]
    return revs[-1] if revs else None


def _find_manifest(run_dir: Path, cal_item_id: str):
    p = calib_dir(run_dir) / "items" / cal_item_id / "manifest.json"
    return p if p.exists() else None


def decide(run_dir: Path, cal_item_id: str, choice: str):
    """Append a calibration decision. `choice` is the blinded OPTION_i
    (or equivalent/none_correct); the manifest maps it to the
    baseline/candidate role so the recorded semantics are always
    role-based — the reviewer never needs to know which is which.
    """
    from .review.render import verify_package
    run_dir = Path(run_dir)
    ensure_calib_authority(run_dir)
    mpath = _find_manifest(run_dir, cal_item_id)
    if mpath is None:
        raise RuntimeError(f"no calibration package for {cal_item_id}")
    man = json.loads(mpath.read_text(encoding="utf-8"))
    if man.get("schema") != CALIB_SCHEMA:
        raise RuntimeError(
            f"legacy package schema {man.get('schema')} is not "
            f"decidable under {CALIB_SCHEMA} — m25-cal-1 packages are "
            "audit-only")
    ok, why = verify_package(man, mpath.parent)
    if not ok:
        raise RuntimeError(f"package not decidable: {why}")
    cal = man["calibration"]
    opts = {o["option_id"]: o for o in man["options"]}
    if choice in opts:
        role = ("baseline" if opts[choice]["candidate_id"] == "baseline"
                else "split")
        decided_option = choice
    elif choice in ("equivalent", "none_correct"):
        role = choice
        decided_option = None
    else:
        raise RuntimeError(f"bad choice {choice} — one of "
                           f"{sorted(opts) + ['equivalent', 'none_correct']}")
    prior = current_decision(run_dir, cal["repair_id"])
    rev = {
        "revision_id": "calrev-" + _sha({
            "repair_id": cal["repair_id"], "role": role,
            "aph": man["audio_package_hash"], "at": _now()})[:16],
        "cal_item_id": cal_item_id,
        "repair_id": cal["repair_id"],
        "note_id": man["target_group"]["packets"][0],
        "patch_sha256": cal["patch_sha256"],
        "audio_package_hash": man["audio_package_hash"],
        "choice": role,
        "decided_option": decided_option,
        "option_role": (opts.get(decided_option) or {})
                       .get("candidate_id"),
        "outcome": OUTCOME[role],
        "decided_at": _now(),
        "superseded_by": None,
    }
    d = load_decisions(run_dir)
    if prior is not None:
        prior["superseded_by"] = rev["revision_id"]
    d["revisions"].append(rev)
    _jwrite(_decisions_path(run_dir), d)
    rebuild_calibration_state(run_dir)
    return rev


def calibration_authorized(run_dir: Path, repair_id: str, patch):
    """The M2.5 machine-authority gate (§10.1.5/§10.1.7-C): a machine
    structure candidate applies ONLY while a fresh
    human_confirmed_machine_split decision binds this exact repair_id +
    patch content AND its recorded package still verifies byte-for-byte.
    Any other outcome — false_positive / no_benefit / unresolved /
    superseded / missing — is no authority (candidate, never repair)."""
    rev = current_decision(run_dir, repair_id)
    if rev is None or rev.get("outcome") != \
            "human_confirmed_machine_split":
        return None
    if rev.get("patch_sha256") != _sha(patch):
        return None
    from .review.render import verify_package
    mpath = _find_manifest(run_dir, rev["cal_item_id"])
    if mpath is None:
        return None
    man = json.loads(mpath.read_text(encoding="utf-8"))
    if man.get("schema") != CALIB_SCHEMA:
        return None                        # legacy package — audit-only
    if man.get("audio_package_hash") != rev["audio_package_hash"]:
        return None
    ok, _ = verify_package(man, mpath.parent)
    return rev if ok else None


def rebuild_calibration_state(run_dir: Path, write: bool = True) -> dict:
    """Derived summary — always recomputable from decisions + plan.

    §10.1.5A-G5J-C: `write=False` computes the same state in memory
    without touching state.json — read paths (e.g. calib-web GETs)
    must not dirty a tracked file, or the byte-level git_evidence
    rule self-pollutes review_ready on every page load."""
    ensure_calib_authority(Path(run_dir))
    d = load_decisions(run_dir)
    plan_p = calib_dir(run_dir) / "plan.json"
    plan = json.loads(plan_p.read_text(encoding="utf-8")) \
        if plan_p.exists() else {"items": []}
    counts = {v: 0 for v in OUTCOME.values()}
    reviewed, pending = [], []
    for it in plan["items"]:
        rev = current_decision(run_dir, it["repair_id"])
        if rev is None:
            pending.append(it["cal_item_id"])
        else:
            reviewed.append({"cal_item_id": it["cal_item_id"],
                             "repair_id": it["repair_id"],
                             "outcome": rev["outcome"],
                             "revision_id": rev["revision_id"]})
            counts[rev["outcome"]] += 1
    confirmed = counts["human_confirmed_machine_split"]
    ev = git_evidence(run_dir)
    inv = plan_invariants(run_dir)
    # §10.1.5A-G5H: two different contracts must not be conflated —
    # store_contract_sha256 describes the plan's DEFAULT contract while
    # pilot_contract_sha256 is the human-review authority derived from
    # the exact current pilot sample set.
    # §G5M: when an eligibility inventory exists the pilot roster is
    # ITS selection — history no longer picks the samples; an empty
    # honest roster evaluates as not-ok, never as the old four.
    elig_p = calib_dir(run_dir) / "eligibility_inventory.json"
    elig = {"inventory_present": elig_p.exists()}
    roster_ids = None
    if elig_p.exists():
        # an inventory that can't be read still revokes the historical
        # default roster — fail closed to an empty sample set
        roster_ids = []
        try:
            edoc = json.loads(elig_p.read_text(encoding="utf-8"))
            by_note = {it.get("note_id"): it.get("cal_item_id")
                       for it in plan["items"]}
            roster_ids = [by_note[n]
                          for n in edoc.get("roster_candidates") or []
                          if n in by_note]
            elig.update({
                "n_eligible": (edoc.get("summary") or {})
                .get("n_eligible"),
                "roster_candidates":
                    edoc.get("roster_candidates") or [],
                "roster_size_ok": edoc.get("roster_size_ok")})
        except Exception:
            roster_ids = None
    pilot = pilot_authority(
        run_dir, sample_ids=roster_ids
        if elig_p.exists() else None)
    state = {
        "schema": CALIB_SCHEMA, "rebuilt_at": _now(),
        "eligibility": elig,
        "total_machine_split_candidates": len(plan["items"]),
        "reviewed_count": len(reviewed),
        "split_preferred_count": confirmed,
        "baseline_preferred_count":
            counts["machine_structure_false_positive"],
        "equivalent_count": counts["no_demonstrated_benefit"],
        "none_correct_count": counts["unresolved"],
        "measured_song_level_precision":
            (confirmed / len(reviewed)) if reviewed else None,
        "pending": pending, "reviewed": reviewed,
        "store_contract_sha256": plan.get("contract_sha256"),
        "pilot_contract_sha256": pilot["contract_sha256"],
        "pilot_authority": {"ok": pilot["ok"],
                            "sample_ids": pilot["sample_ids"],
                            "violations": pilot["violations"][:10]},
        "git_evidence": {k: ev[k] for k in
                         ("complete", "git", "checked")} | \
                        {"missing_count": len(ev["missing"])},
        "plan_invariants": {"ok": inv["ok"],
                            "violations": inv["violations"][:20]},
        "review_ready": review_ready(run_dir),
    }
    if write:
        _jwrite(calib_dir(run_dir) / "state.json", state)
    return state
