"""L7 portamento lane-isolation A/B (plan.md §12 reviewer item 3).

`compile_portamento_lane` historically owned the span from the slide's
departure all the way to the TARGET NOTE END.  That may absorb stable
intonation / onset / ornament content into the portamento carrier.  This
tool renders both ownership modes of the same phrase candidate and
compares:

  A  full_note : pitch.data anchors through target-note end (current)
  B  event     : pitch.data anchors stop at event end + settle tail;
                 PITD resumes ownership beyond it

For each mode: real OpenUtau render -> the SAME QA battery as the phrase
driver (topology / portamento / vibrato / absolute event-shape on both
extractor families) plus an OUT-OF-LANE position comparison (all SOURCE
voiced frames outside every owned span).

Verdict: `event` is preferred when its in-event shape is non-worse and
its out-of-lane error is non-worse; otherwise `full_note` stands.  The
chosen mode is recorded so `l7_phrase_gate --porta-ownership` runs the
accepted one.

Artifacts: runs/expr-20260921/lane_ab/<phrase>/...

Usage (clean worktree required):
    .venv/Scripts/python.exe tools/l7_lane_isolation_ab.py [P2_slides ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l7_phrase_gate as drv                      # noqa: E402

from agent2utau.expression import contour_qa as cq  # noqa: E402
from agent2utau.expression.contour import build_contour_signal  # noqa: E402
from agent2utau.expression.events import (                    # noqa: E402
    match_pitch_events, match_vibrato_events)
from agent2utau.analysis.f0 import extract_f0     # noqa: E402
from agent2utau.analysis.rmvpe import infer_rmvpe  # noqa: E402
from agent2utau.expression.pitch_residual import (  # noqa: E402
    compile_C3, compile_portamento_lane, compute_dense,
    flatten_pitd_spans)
from agent2utau.openutau.ustx import (             # noqa: E402
    load_ustx, save_ustx, semantic_notes_sha256, sha256)
from agent2utau.resources.config import load_config  # noqa: E402

AB_DIR = drv.RUN_DIR / "lane_ab"
MODES = ("full_note", "event")


def _load_render(wav, notes, t0, t1, nuc):
    f = extract_f0(wav)
    r = infer_rmvpe(wav)
    sig = build_contour_signal(f, r, notes, t0_s=t0, t1_s=t1,
                               extractor="fcpe", source="render")
    sig_b = build_contour_signal(r, f, notes, t0_s=t0, t1_s=t1,
                                 extractor="rmvpe", source="render")
    return {"wav": Path(wav), "sig": sig, "sig_b": sig_b,
            "events": drv.detect_all(sig, notes, nuc),
            "events_b": drv.detect_all(sig_b, notes, nuc)}


def _out_of_lane_mask(sig, spans):
    m = sig.voiced & (sig.note_idx >= 0)
    for a, b in spans:
        m &= ~((sig.times >= a - 0.01) & (sig.times <= b + 0.01))
    return m


NON_PORTA_DISCRETE_TYPES = {
    "scoop", "undershoot", "overshoot", "ornament"
}


def _non_porta_lane_summary(source_events, render_events, notes, nuc):
    """Explicit onset/ornament preservation check.

    Stable intonation is covered by out-of-lane position/topology and
    vibrato has its dedicated metrics.  This summary covers the discrete
    non-portamento lanes most likely to be swallowed by full-note
    pitch.data ownership.
    """
    src = [e for e in source_events if e.type in NON_PORTA_DISCRETE_TYPES]
    ren = [e for e in render_events if e.type in NON_PORTA_DISCRETE_TYPES]
    m = match_pitch_events(src, ren, notes, nucleus_times=nuc)

    def _count(events):
        out = {t: 0 for t in sorted(NON_PORTA_DISCRETE_TYPES)}
        for e in events:
            if e.type in out:
                out[e.type] += 1
        return out

    matched = {t: 0 for t in sorted(NON_PORTA_DISCRETE_TYPES)}
    for row in m["matched"]:
        t = row["source"].type
        if t in matched:
            matched[t] += 1

    ambiguous_src = [row["source"] for row in m["ambiguous"]]
    return {
        "matched_by_type": matched,
        "source_only_by_type": _count(m["source_only"]),
        "ambiguous_by_type": _count(ambiguous_src),
        "render_only_by_type": _count(m["neutral_only"]),
        "source_unresolved_total": (
            len(m["source_only"]) + len(m["ambiguous"])),
        "render_only_total": len(m["neutral_only"]),
    }


def _lane_nonworse(candidate, reference):
    """Candidate must add neither unresolved SOURCE events nor extras."""
    return (
        candidate["source_unresolved_total"]
        <= reference["source_unresolved_total"]
        and candidate["render_only_total"]
        <= reference["render_only_total"]
    )


def run_phrase(phrase, cfg, base_doc, caches, head):
    w0, w1 = drv.PHRASES[phrase]
    t0, t1 = w0 - drv.PAD_S, w1 + drv.PAD_S
    pdir = AB_DIR / phrase
    pdir.mkdir(parents=True, exist_ok=True)
    print(f"== {phrase} window [{w0},{w1}]", flush=True)
    source_core_bounds, source_edge_evidence = \
        drv.load_source_core_bounds(phrase)

    base_part, notes = drv.phrase_notes(base_doc, w0, w1)
    part_pos = notes[0]["_abs_tick"] - 480
    nuc = drv.nucleus_times(notes)

    src_sig = build_contour_signal(caches["src_fcpe"], caches["src_rmvpe"],
                                   notes, t0_s=t0, t1_s=t1,
                                   extractor="fcpe", source="source")
    src_sig_b = build_contour_signal(caches["src_rmvpe"],
                                     caches["src_fcpe"], notes,
                                     t0_s=t0, t1_s=t1,
                                     extractor="rmvpe", source="source")
    neu_sig = build_contour_signal(caches["neu_fcpe"], caches["neu_rmvpe"],
                                   notes, t0_s=t0, t1_s=t1,
                                   extractor="fcpe", source="neutral")
    neu_sig_b = build_contour_signal(caches["neu_rmvpe"],
                                     caches["neu_fcpe"], notes,
                                     t0_s=t0, t1_s=t1,
                                     extractor="rmvpe", source="neutral")
    dense = compute_dense(caches["src_fcpe"], caches["neu_fcpe"],
                          caches["src_rmvpe"], caches["neu_rmvpe"],
                          notes, t0, t1)
    np.savez(pdir / "dense.npz", **dense)

    src_events = drv.detect_all(src_sig, notes, nuc)
    neu_events = drv.detect_all(neu_sig, notes, nuc)
    src_events_b = drv.detect_all(src_sig_b, notes, nuc)
    neu_events_b = drv.detect_all(neu_sig_b, notes, nuc)
    vib_match = match_vibrato_events(src_events, neu_events, notes)
    pitd_v1, vib_marks, vib_prov = compile_C3(
        dense, src_sig, neu_sig, notes, part_pos, vib_match,
        max_err_c=10.0,
        base_vibrato={i: n["_note"].get("vibrato")
                      for i, n in enumerate(notes)})

    qa_mask = src_sig.voiced & (src_sig.note_idx >= 0)
    qa_mask_b = src_sig_b.voiced & (src_sig_b.note_idx >= 0)
    results = {}
    for mode in MODES:
        marks, spans, prov = compile_portamento_lane(
            src_sig, src_sig_b, notes, src_events, vib_marks=vib_marks,
            ownership=mode)
        curve = flatten_pitd_spans(pitd_v1, spans, part_pos)
        ustx = pdir / f"{phrase}_{mode}.ustx"
        save_ustx(drv.build_phrase_doc(base_doc, base_part, notes,
                                       part_pos, curve, vib_marks,
                                       f"{phrase}_ab",
                                       porta_marks=marks),
                  ustx)
        rec = _load_render(drv.render(cfg, ustx, pdir / f"{phrase}_{mode}"),
                           notes, t0, t1, nuc)
        out_mask = _out_of_lane_mask(src_sig, spans)
        out_mask_b = _out_of_lane_mask(src_sig_b, spans)
        qa = {
            "portamento": cq.portamento_metrics(src_events, rec["events"]),
            "vibrato": cq.vibrato_metrics(src_events, rec["events"]),
            "non_portamento_event_lanes": {
                "fcpe": _non_porta_lane_summary(
                    src_events, rec["events"], notes, nuc),
                "rmvpe": _non_porta_lane_summary(
                    src_events_b, rec["events_b"], notes, nuc),
            },
            "topology": cq.turning_point_metrics(
                src_sig.cents, rec["sig"].cents, qa_mask),
            "event_shape": cq.event_shape_gate(
                src_events, rec["events"], neu_sig, src_sig, rec["sig"],
                source_core_bounds=source_core_bounds),
            "event_shape_rmvpe": cq.event_shape_gate(
                src_events_b, rec["events_b"], neu_sig_b, src_sig_b,
                rec["sig_b"], source_core_bounds=source_core_bounds),
            "in_lane_position": cq.contour_position_metrics(
                src_sig.cents, rec["sig"].cents, qa_mask & ~out_mask),
            "out_of_lane_position": cq.contour_position_metrics(
                src_sig.cents, rec["sig"].cents, out_mask),
            "out_of_lane_topology": cq.turning_point_metrics(
                src_sig.cents, rec["sig"].cents, out_mask),
        }
        drv._dump(qa, pdir / f"qa_{mode}.json")
        results[mode] = {
            "ustx": ustx.name, "ustx_sha256": sha256(ustx),
            "wav": rec["wav"].name, "wav_sha256": sha256(rec["wav"]),
            "lane_provenance": prov, "owned_spans_s": spans,
            "n_blocking_fcpe": qa["event_shape"]["n_blocking"],
            "n_blocking_rmvpe": qa["event_shape_rmvpe"]["n_blocking"],
            "blocking_events_fcpe": [
                {"from_note": r["from_note"], "class": r["class"]}
                for r in qa["event_shape"]["events"] if r.get("blocking")],
            "blocking_events_rmvpe": [
                {"from_note": r["from_note"], "class": r["class"]}
                for r in qa["event_shape_rmvpe"]["events"]
                if r.get("blocking")],
            "qa": qa}
        print(f"   {mode}: blocking fcpe={qa['event_shape']['n_blocking']}"
              f" rmvpe={qa['event_shape_rmvpe']['n_blocking']}",
              flush=True)

    # ---- verdict ------------------------------------------------------
    a, b = results["full_note"], results["event"]
    def _med_err(q):
        return q["out_of_lane_position"].get("med_c")
    verdict = {
        "in_event_blocking_delta":
            b["n_blocking_fcpe"] - a["n_blocking_fcpe"],
        "out_of_lane_med_abs_err_c":
            {"full_note": _med_err(a["qa"]), "event": _med_err(b["qa"])},
        "preferred": None}
    a_np = a["qa"]["non_portamento_event_lanes"]
    b_np = b["qa"]["non_portamento_event_lanes"]
    event_nonporta_ok = (
        _lane_nonworse(b_np["fcpe"], a_np["fcpe"])
        and _lane_nonworse(b_np["rmvpe"], a_np["rmvpe"]))
    full_nonporta_ok = (
        _lane_nonworse(a_np["fcpe"], b_np["fcpe"])
        and _lane_nonworse(a_np["rmvpe"], b_np["rmvpe"]))

    narrow_ok = (b["n_blocking_fcpe"] <= a["n_blocking_fcpe"]
                 and b["n_blocking_rmvpe"] <= a["n_blocking_rmvpe"]
                 and event_nonporta_ok
                 and (_med_err(b["qa"]) is None or _med_err(a["qa"]) is None
                      or _med_err(b["qa"]) <= _med_err(a["qa"]) + 5.0))

    if narrow_ok:
        preferred = "event"
    elif full_nonporta_ok:
        preferred = "full_note"
    else:
        # Neither ownership dominates: one protects portamento/position
        # while the other protects a discrete onset/ornament lane.
        # Do not hide the trade-off behind a single scalar preference.
        preferred = "BLOCKED"

    verdict["preferred"] = preferred
    verdict["non_portamento_event_lanes"] = {
        "full_note": a_np,
        "event": b_np,
        "event_nonworse": event_nonporta_ok,
        "full_note_nonworse": full_nonporta_ok,
    }
    verdict["rule"] = (
        "prefer event-bounded ownership only when absolute event-shape "
        "blocking is non-worse on both extractor families, discrete "
        "non-portamento event lanes are non-worse, and out-of-lane median "
        "|err| is non-worse (+5c tolerance); otherwise retain full_note "
        "only if its discrete non-portamento lanes are also non-worse; "
        "if neither mode dominates, verdict=BLOCKED")

    rep = {"phrase": phrase, "generator_code_head": head,
           "qa_code_head": drv._git_head(),
           "worktree_clean_at_generation": True,
           "base_file_sha256": sha256(drv.BASE_USTX),
           "base_semantic_sha256": semantic_notes_sha256(base_doc),
           "source_edge_evidence": source_edge_evidence,
           "modes": results, "verdict": verdict}
    drv._dump(rep, pdir / "lane_ab_report.json")
    print(f"   preferred={verdict['preferred']}", flush=True)
    return rep


def main():
    head = drv._require_clean_worktree("l7_lane_isolation_ab")
    cfg = load_config()
    which = sys.argv[1:] or list(drv.PHRASES)
    base_doc = load_ustx(drv.BASE_USTX)
    caches = {"src_fcpe": drv._npz_f0(drv.SRC_FCPE),
              "src_rmvpe": drv._npz_f0(drv.SRC_RMVPE),
              "neu_fcpe": drv._npz_f0(drv.NEU_FCPE),
              "neu_rmvpe": drv._npz_f0(drv.NEU_RMVPE)}
    AB_DIR.mkdir(parents=True, exist_ok=True)
    prefs = {}
    for phrase in which:
        rep = run_phrase(phrase, cfg, base_doc, caches, head)
        prefs[phrase] = rep["verdict"]["preferred"]
    drv._dump({"preferred_by_phrase": prefs,
               "generator_code_head": head},
              AB_DIR / "summary.json")
    print("preferred:", prefs)


if __name__ == "__main__":
    main()
