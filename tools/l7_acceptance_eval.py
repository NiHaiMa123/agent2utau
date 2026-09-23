"""L7 machine-acceptance evaluator (plan.md §10.3).

This is the ONLY authority allowed to emit HUMAN_LISTENING_READY.  It
evaluates every required term from committed artifacts — never from
prose, summaries, or in-memory state:

    tests, real_render, topology_gate, event_lane_gate,
    absolute_event_shape_gate, render_voicing_gate, cross_extractor_gate,
    provenance_gate, artifact_consistency_gate, blocking_issue_count,
    unknown_required_gate_count, HUMAN_LISTENING_READY

Every verdict is one of PASS / FAIL / UNKNOWN / NOT_RUN (§10.1) with an
evidence reference.  PASS is the only non-blocking state; UNKNOWN and
NOT_RUN block exactly like FAIL.  "No detected failure" is never
evidence of success: a term is PASS only when positive evidence exists.

Per-phrase verdicts are derived from
    runs/expr-20260921/phrases3/<phrase>/run_manifest.json
    runs/expr-20260921/phrases3/<phrase>/qa/*.json
    runs/expr-20260921/phrases3/<phrase>/events/*.json
plus on-disk hash verification of the bound USTX/WAV.

`tests` is a global term: the evaluator runs the committed pytest suite
itself (`--run-tests`, default on) so the verdict is bound to a fresh
execution, not a remembered claim.

Usage:
    .venv/Scripts/python.exe tools/l7_acceptance_eval.py [--no-tests]
        [--out runs/expr-20260921/acceptance_eval.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l7_phrase_gate as drv                      # noqa: E402

from agent2utau.openutau.ustx import (             # noqa: E402
    load_ustx, semantic_notes_sha256, sha256)

PASS, FAIL, UNKNOWN, NOT_RUN = "PASS", "FAIL", "UNKNOWN", "NOT_RUN"
TERMS = ["tests", "real_render", "topology_gate", "event_lane_gate",
         "absolute_event_shape_gate", "render_voicing_gate",
         "cross_extractor_gate", "provenance_gate",
         "artifact_consistency_gate"]

TOPOLOGY_KEYS = {"matched_turns", "missing_turns", "extra_turns",
                 "sequence_edit_distance"}
LANE_KEY_RE = re.compile(r"^(portamento|vibrato|onset|ornament)\.")


def _term(verdict, evidence, detail=None):
    out = {"verdict": verdict, "evidence": evidence}
    if detail is not None:
        out["detail"] = detail
    return out


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _unresolved_fail_evidence(phrase_name):
    """Split probe-report events into unresolved vs adjudicated.

    A candidate cannot receive positive absolute/cross-extractor shape
    acceptance against an unverified SOURCE target.  The probe report is
    the committed failure-class authority until a later evidence
    adjudication/regenerated probe resolves it:

    - verdict FAIL_EVIDENCE -> unresolved: gates become UNKNOWN
    - verdict EVIDENCE_ADJUDICATED_ARTIFACT -> the detected SOURCE event
      is positively adjudicated an extraction artifact by an independent
      extractor family; its blocking rows measure deviation from a
      non-existent target and are excluded from `known_blocking`, but
      they stay visible in `adjudicated_artifact_events`.
    - a report without worktree_clean_at_generation=true is stale
      evidence: every event in it counts as unresolved.
    """
    p = drv.RUN_DIR / "probe_portamento" / f"{phrase_name}_probe_report.json"
    rep = _load_json(p)
    if rep is None:
        return [], [], str(p), False
    clean = rep.get("worktree_clean_at_generation") is True
    unresolved = sorted({
        int(r["from_note"]) for r in rep.get("events", [])
        if r.get("from_note") is not None
        and (r.get("verdict") == "FAIL_EVIDENCE" or not clean)})
    adjudicated = sorted({
        int(r["from_note"]) for r in rep.get("events", [])
        if r.get("verdict") == "EVIDENCE_ADJUDICATED_ARTIFACT"
        and r.get("from_note") is not None
        and clean})
    return unresolved, adjudicated, str(p), clean


def _wav_stats(path):
    try:
        with wave.open(str(path)) as w:
            n, sr = w.getnframes(), w.getframerate()
            sw = w.getsampwidth()
            frames = w.readframes(n)
        if sw == 2:
            a = np.frombuffer(frames, dtype=np.int16).astype(float) / 32768.0
        elif sw == 4:
            a = np.frombuffer(frames, dtype=np.int32).astype(float) \
                / 2147483648.0
        else:
            a = np.frombuffer(frames, dtype=np.uint8).astype(float)
            a = (a - 128.0) / 128.0
        return {"duration_s": round(n / sr, 3), "sr": sr,
                "rms_dbfs": round(float(20 * np.log10(
                    max(np.sqrt(np.mean(a * a)), 1e-12))), 1)}
    except Exception as e:
        return {"error": str(e)}


def eval_phrase(pdir: Path) -> dict:
    name = pdir.name
    ev_base = str(pdir)
    out = {"phrase": name, "dir": str(pdir), "terms": {},
           "blocking_issue_count": None,
           "unknown_required_gate_count": None}

    man = _load_json(pdir / "run_manifest.json")
    if man is None:
        for t in TERMS:
            out["terms"][t] = _term(
                NOT_RUN, f"{ev_base}/run_manifest.json",
                "manifest missing or unreadable")
        out["HUMAN_LISTENING_READY"] = _term(
            FAIL, f"{ev_base}/run_manifest.json",
            "no committed manifest -> every required gate is NOT_RUN")
        out["unknown_required_gate_count"] = len(TERMS) - 1
        return out

    # ---- real_render -------------------------------------------------
    wav_p = Path(man.get("render_wav_path", ""))
    ustx_p = Path(man.get("ustx_path", ""))
    rr_ev = f"{ev_base}/run_manifest.json#render_wav_sha256"
    if not wav_p.is_file():
        out["terms"]["real_render"] = _term(
            FAIL, rr_ev, "render wav missing on disk")
    else:
        actual = sha256(wav_p)
        if actual != man.get("render_wav_sha256"):
            out["terms"]["real_render"] = _term(
                FAIL, rr_ev,
                f"wav sha256 mismatch {actual[:12]}!="
                f"{str(man.get('render_wav_sha256'))[:12]}")
        else:
            st = _wav_stats(wav_p)
            if st.get("duration_s", 0) > 0.5 and \
                    st.get("rms_dbfs", -120) > -60:
                out["terms"]["real_render"] = _term(
                    PASS, f"{wav_p} sha256={actual[:16]} "
                          f"dur={st['duration_s']}s rms={st['rms_dbfs']}dB")
            else:
                out["terms"]["real_render"] = _term(
                    FAIL, rr_ev, f"wav degenerate: {st}")

    # ---- topology_gate + event_lane_gate ------------------------------
    # The production gate verdict for the ACCEPTED candidate, read from
    # the committed manifest stage list (relative non-regression vs v1
    # already enforced there; the absolute event-shape term is separate).
    final = man.get("shape_gate", {}).get("final_candidate")
    stages = man.get("shape_gate", {}).get("stages") or []
    m = re.search(r"v\d+$", str(final or ""))
    tag = m.group(0) if m else ("v1" if final == "C3" else None)
    acc = next((s for s in stages if s["candidate"] == tag), None)
    sg_ev = f"{ev_base}/run_manifest.json#shape_gate"
    if acc is None:
        out["terms"]["topology_gate"] = _term(
            NOT_RUN, sg_ev, "accepted stage not recorded")
        out["terms"]["event_lane_gate"] = _term(
            NOT_RUN, sg_ev, "accepted stage not recorded")
    else:
        viol = acc.get("violations") or []
        topo_v = [v for v in viol if v in TOPOLOGY_KEYS]
        lane_v = [v for v in viol if LANE_KEY_RE.match(v)]
        out["terms"]["topology_gate"] = _term(
            FAIL if topo_v else PASS, sg_ev,
            {"stage": acc["candidate"], "violations": topo_v,
             "topology": acc.get("topology")})
        out["terms"]["event_lane_gate"] = _term(
            FAIL if lane_v else PASS, sg_ev,
            {"stage": acc["candidate"], "violations": lane_v})

    # ---- absolute_event_shape_gate (primary fcpe family) --------------
    es = _load_json(pdir / "qa" / "event_shape_metrics.json")
    es_ev = f"{ev_base}/qa/event_shape_metrics.json"
    evidence_unknown, adjudicated, evidence_ev, evidence_clean = \
        _unresolved_fail_evidence(name)
    if es is None:
        out["terms"]["absolute_event_shape_gate"] = _term(
            NOT_RUN, es_ev, "artifact missing")
        n_block_a = None
        known_blocking = None
    else:
        n_block_a = int(es.get("n_blocking") or 0)
        blocking = [r for r in es.get("events", []) if r.get("blocking")]
        exempt = set(evidence_unknown) | set(adjudicated)
        known_blocking = [r for r in blocking
                          if int(r.get("from_note", -1)) not in exempt]
        if known_blocking:
            abs_verdict = FAIL
        elif evidence_unknown:
            abs_verdict = UNKNOWN
        else:
            abs_verdict = PASS
        out["terms"]["absolute_event_shape_gate"] = _term(
            abs_verdict,
            f"{es_ev}; {evidence_ev}"
            if (evidence_unknown or adjudicated) else es_ev,
            {"n_blocking": n_block_a,
             "blocking": [{"from_note": r["from_note"],
                           "class": r["class"]} for r in blocking],
             "unverified_source_events": evidence_unknown,
             "adjudicated_artifact_events": adjudicated,
             "evidence_report_clean": evidence_clean})

    # ---- render_voicing_gate ------------------------------------------
    if es is None:
        out["terms"]["render_voicing_gate"] = _term(
            NOT_RUN, es_ev, "artifact missing")
    else:
        vloss = [r for r in es.get("events", [])
                 if r.get("class") == "render_voicing_loss"]
        out["terms"]["render_voicing_gate"] = _term(
            FAIL if vloss else PASS, es_ev,
            {"render_voicing_loss_events":
             [r["from_note"] for r in vloss]})

    # ---- cross_extractor_gate (rmvpe family re-measurement) -----------
    es_b = _load_json(pdir / "qa" / "event_shape_metrics_rmvpe.json")
    esb_ev = f"{ev_base}/qa/event_shape_metrics_rmvpe.json"
    if es_b is None:
        out["terms"]["cross_extractor_gate"] = _term(
            NOT_RUN, esb_ev,
            "independent extractor-family shape verdict missing")
        n_block_b = None
        known_b = None
    else:
        n_block_b = int(es_b.get("n_blocking") or 0)
        # Cross-family disagreement that already caused FAIL_EVIDENCE is
        # uncertainty, not a positive cross-extractor PASS.  A later
        # evidence adjudication/probe must resolve the SOURCE target.
        block_b = [r for r in es_b.get("events", []) if r.get("blocking")]
        known_b = [r for r in block_b
                   if int(r.get("from_note", -1))
                   not in set(evidence_unknown) | set(adjudicated)]
        cross_verdict = (FAIL if known_b else
                         UNKNOWN if evidence_unknown else PASS)
        out["terms"]["cross_extractor_gate"] = _term(
            cross_verdict,
            f"{esb_ev}; {evidence_ev}"
            if (evidence_unknown or adjudicated) else esb_ev,
            {"n_blocking_rmvpe": n_block_b,
             "unverified_source_events": evidence_unknown,
             "adjudicated_artifact_events": adjudicated})

    # Blocking issues = blocking rows not explained by an adjudicated
    # extraction artifact.  Unresolved-evidence events block via
    # unknown_required_gate_count instead.
    if known_blocking is None and known_b is None:
        out["blocking_issue_count"] = None
    else:
        out["blocking_issue_count"] = len(known_blocking or []) \
            + len(known_b or [])

    # ---- provenance_gate ----------------------------------------------
    prov_ev = f"{ev_base}/run_manifest.json"
    probs = []
    if man.get("worktree_clean_at_generation") is not True:
        probs.append("worktree_clean_at_generation missing/false")
    for k in ("generator_code_head", "qa_code_head"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(man.get(k) or "")):
            probs.append(f"{k} missing/not a commit")
    if not re.fullmatch(r"[0-9a-f]{64}",
                        str(man.get("base_file_sha256") or "")):
        probs.append("base_file_sha256 missing")
    if not re.fullmatch(r"[0-9a-f]{64}",
                        str(man.get("base_semantic_sha256") or "")):
        probs.append("base_semantic_sha256 missing")
    else:
        try:
            actual_sem = semantic_notes_sha256(load_ustx(drv.BASE_USTX))
            if actual_sem != man["base_semantic_sha256"]:
                probs.append("semantic hash mismatch vs base score")
        except Exception as e:
            probs.append(f"semantic recompute failed: {e}")
    if drv.BASE_USTX.is_file() and \
            re.fullmatch(r"[0-9a-f]{64}",
                         str(man.get("base_file_sha256") or "")):
        if sha256(drv.BASE_USTX) != man["base_file_sha256"]:
            probs.append("base file hash mismatch")
    out["terms"]["provenance_gate"] = _term(
        FAIL if probs else PASS, prov_ev, probs or "ok")

    # ---- artifact_consistency_gate ------------------------------------
    probs = []
    for k in man.get("qa_files", []):
        p = pdir / "qa" / k
        if _load_json(p) is None:
            probs.append(f"qa/{k} missing/invalid")
    for k in man.get("event_files", []):
        p = pdir / "events" / k
        if _load_json(p) is None:
            probs.append(f"events/{k} missing/invalid")
    if ustx_p.is_file():
        if sha256(ustx_p) != man.get("candidate_ustx_sha256"):
            probs.append("candidate ustx sha256 mismatch")
    else:
        probs.append("candidate ustx missing")
    out["terms"]["artifact_consistency_gate"] = _term(
        FAIL if probs else PASS, prov_ev, probs or "ok")

    # ---- tests: verdict injected by caller (global term) --------------
    out["terms"]["tests"] = _term(NOT_RUN, "pytest",
                                  "global suite verdict pending")

    # ---- roll up -------------------------------------------------------
    unk = sum(1 for t in TERMS
              if out["terms"][t]["verdict"] in (UNKNOWN, NOT_RUN))
    out["unknown_required_gate_count"] = unk
    allpass = all(out["terms"][t]["verdict"] == PASS for t in TERMS)
    ready = allpass and unk == 0 and (out["blocking_issue_count"] or 0) == 0
    out["HUMAN_LISTENING_READY"] = _term(
        PASS if ready else FAIL, prov_ev,
        {"all_terms_pass": allpass,
         "blocking_issue_count": out["blocking_issue_count"],
         "unknown_required_gate_count": unk})
    return out


def run_tests() -> dict:
    """Global `tests` term: execute the committed suite now."""
    try:
        p = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-x", "-q"],
            capture_output=True, text=True, timeout=900)
    except Exception as e:
        return _term(NOT_RUN, "pytest tests/ -x -q", str(e))
    tail = (p.stdout.strip().splitlines() or ["<no output>"])[-1]
    ev = f"pytest tests/ -x -q -> exit {p.returncode}; {tail}"
    if p.returncode == 0:
        return _term(PASS, ev)
    return _term(FAIL, ev)


def main():
    evaluator_head = drv._require_clean_worktree("l7_acceptance_eval")
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--out", default=str(drv.RUN_DIR / "acceptance_eval.json"))
    args = ap.parse_args()

    tests_term = _term(NOT_RUN, "pytest", "skipped via --no-tests") \
        if args.no_tests else run_tests()

    phrases = {}
    for name in drv.PHRASES:
        rep = eval_phrase(drv.PHRASE_DIR / name)
        rep["terms"]["tests"] = dict(tests_term)
        unk = sum(1 for t in TERMS
                  if rep["terms"][t]["verdict"] in (UNKNOWN, NOT_RUN))
        rep["unknown_required_gate_count"] = unk
        ready = all(rep["terms"][t]["verdict"] == PASS for t in TERMS) \
            and unk == 0 and (rep["blocking_issue_count"] or 0) == 0
        rep["HUMAN_LISTENING_READY"] = _term(
            PASS if ready else FAIL,
            str(drv.PHRASE_DIR / name / "run_manifest.json"),
            {"all_terms_pass":
             all(rep["terms"][t]["verdict"] == PASS for t in TERMS),
             "blocking_issue_count": rep["blocking_issue_count"],
             "unknown_required_gate_count": unk})
        phrases[name] = rep
        line = " ".join(f"{t}={rep['terms'][t]['verdict']}" for t in TERMS)
        print(f"{name}: {line}")
        print(f"   blocking={rep['blocking_issue_count']} "
              f"unknown={rep['unknown_required_gate_count']} "
              f"READY={rep['HUMAN_LISTENING_READY']['verdict']}",
              flush=True)

    # ---- global roll-up ------------------------------------------------
    glob_terms = {"tests": tests_term}
    for t in TERMS[1:]:
        vs = {n: phrases[n]["terms"][t]["verdict"] for n in phrases}
        if all(v == PASS for v in vs.values()):
            glob_terms[t] = _term(PASS, "all phrases", vs)
        elif any(v == FAIL for v in vs.values()):
            glob_terms[t] = _term(FAIL, "phrases", vs)
        else:
            glob_terms[t] = _term(
                UNKNOWN if any(v == UNKNOWN for v in vs.values())
                else NOT_RUN, "phrases", vs)
    glob_block = sum(phrases[n]["blocking_issue_count"] or 0
                     for n in phrases)
    glob_unk = sum(1 for t in TERMS
                   if glob_terms[t]["verdict"] in (UNKNOWN, NOT_RUN))
    g_ready = all(glob_terms[t]["verdict"] == PASS for t in TERMS) \
        and glob_unk == 0 and glob_block == 0
    report = {
        "evaluator": "tools/l7_acceptance_eval.py",
        "evaluator_head": evaluator_head,
        "worktree_clean_at_evaluation": True,
        "run_dir": str(drv.RUN_DIR),
        "terms": TERMS,
        "phrases": phrases,
        "global": {
            "terms": glob_terms,
            "blocking_issue_count": glob_block,
            "unknown_required_gate_count": glob_unk,
            "HUMAN_LISTENING_READY": _term(
                PASS if g_ready else FAIL, "global roll-up",
                {"blocking_issue_count": glob_block,
                 "unknown_required_gate_count": glob_unk})}}
    drv._dump(report, Path(args.out))
    g = report["global"]
    print("GLOBAL: " + " ".join(
        f"{t}={g['terms'][t]['verdict']}" for t in TERMS))
    print(f"  blocking_issue_count={g['blocking_issue_count']} "
          f"unknown_required_gate_count={g['unknown_required_gate_count']}")
    print(f"  HUMAN_LISTENING_READY={g['HUMAN_LISTENING_READY']['verdict']}")
    print(f"  report: {args.out}")
    return 0 if g["HUMAN_LISTENING_READY"]["verdict"] == PASS else 1


if __name__ == "__main__":
    sys.exit(main())
