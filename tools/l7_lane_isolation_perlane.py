"""L7 Round-B2 per-lane portamento ownership isolation (plan.md §12).

The global full_note/event A/B is too coarse: it toggles every applied
lane at once and cannot attribute either the RMVPE note9 distortion or
the discrete-lane absorption to a specific ownership tail.  This tool
renders one single-lane toggle per applied portamento lane plus one
final hybrid vector, and reports per-event (not per-count) lane state.

Vectors over the applied target-note lanes (P2: {2,5,7}):

    FFF  all full_note (baseline)
    EFF  only target 2 -> event
    FEF  only target 5 -> event
    FFE  only target 7 -> event
    H    hybrid built from the per-lane attributions

Causal attribution: a discrete-lane difference between a single-toggle
render and FFF is caused by that lane by construction (one variable
changed); the incremental `full_note - event` ownership tail overlap is
recorded as supporting spatial evidence, never as sole proof.

Artifacts: runs/expr-20260921/lane_ab/<phrase>_perlane/...

Usage (clean worktree required):
    .venv/Scripts/python.exe tools/l7_lane_isolation_perlane.py P2_slides
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l7_phrase_gate as drv                      # noqa: E402
import l7_lane_isolation_ab as ab                 # noqa: E402

from agent2utau.expression import contour_qa as cq  # noqa: E402
from agent2utau.expression.contour import build_contour_signal  # noqa: E402
from agent2utau.expression.events import (                    # noqa: E402
    event_to_json, match_pitch_events, match_vibrato_events)
from agent2utau.expression.pitch_residual import (  # noqa: E402
    compile_C3, compile_portamento_lane, compute_dense,
    flatten_pitd_spans)
from agent2utau.openutau.ustx import (             # noqa: E402
    load_ustx, save_ustx, semantic_notes_sha256, sha256)
from agent2utau.resources.config import load_config  # noqa: E402

NON_PORTA = ab.NON_PORTA_DISCRETE_TYPES


def _non_porta_lane_detail(source_events, render_events, notes, nuc):
    """Per-event non-portamento lane state (identities, not counts)."""
    src = [e for e in source_events if e.type in NON_PORTA]
    ren = [e for e in render_events if e.type in NON_PORTA]
    m = match_pitch_events(src, ren, notes, nucleus_times=nuc)
    rows = []
    for i, se in enumerate(src):
        st = "source_only"
        for row in m["matched"]:
            if row["source"] is se:
                st = "matched"
                break
        else:
            for row in m["ambiguous"]:
                if row["source"] is se:
                    st = "ambiguous"
                    break
        rows.append({"src_index": i, "state": st,
                     **{k: event_to_json(se)[k] for k in
                        ("type", "note_indices", "start_s", "end_s")}})
    render_only = [{k: event_to_json(e)[k] for k in
                    ("type", "note_indices", "start_s", "end_s")}
                   for e in m["neutral_only"]]
    summ = ab._non_porta_lane_summary(source_events, render_events,
                                      notes, nuc)
    return {**summ, "events": rows, "render_only_events": render_only}


def _qa_battery(src_sig, src_sig_b, neu_sig, neu_sig_b, src_events,
                src_events_b, rec, spans, notes, nuc, core_bounds):
    qa_mask = src_sig.voiced & (src_sig.note_idx >= 0)
    out_mask = ab._out_of_lane_mask(src_sig, spans)
    return {
        "portamento": cq.portamento_metrics(src_events, rec["events"]),
        "vibrato": cq.vibrato_metrics(src_events, rec["events"]),
        "non_portamento_event_lanes": {
            "fcpe": _non_porta_lane_detail(src_events, rec["events"],
                                           notes, nuc),
            "rmvpe": _non_porta_lane_detail(src_events_b,
                                            rec["events_b"], notes, nuc),
        },
        "topology": cq.turning_point_metrics(
            src_sig.cents, rec["sig"].cents, qa_mask),
        "event_shape": cq.event_shape_gate(
            src_events, rec["events"], neu_sig, src_sig, rec["sig"],
            source_core_bounds=core_bounds),
        "event_shape_rmvpe": cq.event_shape_gate(
            src_events_b, rec["events_b"], neu_sig_b, src_sig_b,
            rec["sig_b"], source_core_bounds=core_bounds),
        "in_lane_position": cq.contour_position_metrics(
            src_sig.cents, rec["sig"].cents, qa_mask & ~out_mask),
        "out_of_lane_position": cq.contour_position_metrics(
            src_sig.cents, rec["sig"].cents, out_mask),
        "out_of_lane_topology": cq.turning_point_metrics(
            src_sig.cents, rec["sig"].cents, out_mask),
    }


def _event_key(row):
    return (row["type"], tuple(row["note_indices"]),
            round(row["start_s"], 2))


def _lane_diff(base_rows, cand_rows):
    """State changes of SOURCE discrete events between two renders."""
    b = {_event_key(r): r for r in base_rows}
    c = {_event_key(r): r for r in cand_rows}
    out = []
    for k in sorted(set(b) | set(c)):
        rb, rc = b.get(k), c.get(k)
        sb = rb["state"] if rb else "absent"
        sc = rc["state"] if rc else "absent"
        if sb != sc:
            out.append({"event": k, "baseline_state": sb,
                        "toggle_state": sc,
                        "span_s": [rc["start_s"] if rc else rb["start_s"],
                                   rc["end_s"] if rc else rb["end_s"]]})
    return out


def _overlap(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def run_phrase(phrase, cfg, base_doc, caches, head):
    w0, w1 = drv.PHRASES[phrase]
    t0, t1 = w0 - drv.PAD_S, w1 + drv.PAD_S
    pdir = ab.AB_DIR / f"{phrase}_perlane"
    pdir.mkdir(parents=True, exist_ok=True)
    print(f"== {phrase} per-lane window [{w0},{w1}]", flush=True)
    core_bounds, edge_evidence = drv.load_source_core_bounds(phrase)

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

    # ---- discover applied lanes + incremental tails -------------------
    _, _, prov_f = compile_portamento_lane(
        src_sig, src_sig_b, notes, src_events, vib_marks=vib_marks,
        ownership="full_note")
    _, _, prov_e = compile_portamento_lane(
        src_sig, src_sig_b, notes, src_events, vib_marks=vib_marks,
        ownership="event")
    lanes = sorted(i for i, p in prov_f.items() if p.get("applied"))
    tails = {}
    for i in lanes:
        f_end = prov_f[i]["carrier_span_s"][1]
        e_end = prov_e[i]["carrier_span_s"][1]
        tails[i] = [round(e_end, 3), round(f_end, 3)]
    print(f"   applied lanes={lanes} tails={tails}", flush=True)

    vectors = {"F" * len(lanes): {}}
    for pos, i in enumerate(lanes):
        label = list("F" * len(lanes))
        label[pos] = "E"
        vectors["".join(label)] = {i: "event"}

    # ---- render + QA each vector --------------------------------------
    results = {}
    for label, vec in vectors.items():
        marks, spans, prov = compile_portamento_lane(
            src_sig, src_sig_b, notes, src_events, vib_marks=vib_marks,
            ownership=vec if vec else "full_note")
        curve = flatten_pitd_spans(pitd_v1, spans, part_pos)
        ustx = pdir / f"{phrase}_{label}.ustx"
        save_ustx(drv.build_phrase_doc(base_doc, base_part, notes,
                                       part_pos, curve, vib_marks,
                                       f"{phrase}_pl",
                                       porta_marks=marks), ustx)
        rec = ab._load_render(
            drv.render(cfg, ustx, pdir / f"{phrase}_{label}"),
            notes, t0, t1, nuc)
        qa = _qa_battery(src_sig, src_sig_b, neu_sig, neu_sig_b,
                         src_events, src_events_b, rec, spans,
                         notes, nuc, core_bounds)
        drv._dump(qa, pdir / f"qa_{label}.json")
        results[label] = {
            "label": label,
            "ownership_vector": {i: ("event" if vec.get(i) == "event"
                                     else "full_note") for i in lanes},
            "ustx": ustx.name, "ustx_sha256": sha256(ustx),
            "wav": rec["wav"].name, "wav_sha256": sha256(rec["wav"]),
            "lane_provenance": prov, "owned_spans_s": spans,
            "blocking_events_fcpe": [
                {"from_note": r["from_note"], "class": r["class"]}
                for r in qa["event_shape"]["events"] if r.get("blocking")],
            "blocking_events_rmvpe": [
                {"from_note": r["from_note"], "class": r["class"]}
                for r in qa["event_shape_rmvpe"]["events"]
                if r.get("blocking")],
            "vibrato_missing": ab._vibrato_missing_count(qa["vibrato"]),
            "qa": qa}
        print(f"   {label}: fcpe={len(results[label]['blocking_events_fcpe'])}"
              f" rmvpe={len(results[label]['blocking_events_rmvpe'])}"
              f" vib_missing={results[label]['vibrato_missing']}",
              flush=True)

    base_label = "F" * len(lanes)
    base = results[base_label]

    # ---- causal attribution -------------------------------------------
    attribution = {}
    for i in lanes:
        pos = lanes.index(i)
        label = list("F" * len(lanes))
        label[pos] = "E"
        label = "".join(label)
        cand = results[label]
        diffs = {}
        for fam in ("fcpe", "rmvpe"):
            b_rows = base["qa"]["non_portamento_event_lanes"][fam]["events"]
            c_rows = cand["qa"]["non_portamento_event_lanes"][fam]["events"]
            for d in _lane_diff(b_rows, c_rows):
                d["family"] = fam
                d["tail_overlap_s"] = round(_overlap(d["span_s"],
                                                     tails[i]), 3)
                diffs.setdefault("discrete_state_changes", []).append(d)
            b_ex = {_event_key(r) for r in
                    base["qa"]["non_portamento_event_lanes"][fam]
                    ["render_only_events"]}
            c_ex = {_event_key(r) for r in
                    cand["qa"]["non_portamento_event_lanes"][fam]
                    ["render_only_events"]}
            for k in sorted(c_ex - b_ex):
                diffs.setdefault("new_render_only", []).append(
                    {"family": fam, "event": k})
        diffs["new_blockers_fcpe"] = [
            r for r in cand["blocking_events_fcpe"]
            if r not in base["blocking_events_fcpe"]]
        diffs["new_blockers_rmvpe"] = [
            r for r in cand["blocking_events_rmvpe"]
            if r not in base["blocking_events_rmvpe"]]
        diffs["vibrato_missing_delta"] = (
            cand["vibrato_missing"] - base["vibrato_missing"])
        attribution[str(i)] = {"toggle_label": label,
                               "incremental_tail_s": tails[i],
                               **diffs}
        print(f"   lane {i} ({label}): {json_brief(diffs)}", flush=True)

    # ---- hybrid selection ----------------------------------------------
    hybrid = {}
    for i in lanes:
        at = attribution[str(i)]
        introduces_blocker = (at["new_blockers_fcpe"]
                              or at["new_blockers_rmvpe"]
                              or at["vibrato_missing_delta"] > 0)
        discrete_worse = False
        for fam in ("fcpe", "rmvpe"):
            for d in at.get("discrete_state_changes", []):
                if d["family"] == fam and _worse_state(
                        d["baseline_state"], d["toggle_state"]):
                    discrete_worse = True
            if at.get("new_render_only"):
                if any(r["family"] == fam
                       for r in at["new_render_only"]):
                    discrete_worse = True
        hybrid[i] = "full_note" if (introduces_blocker or discrete_worse) \
            else "event"

    # ---- render + validate the hybrid ----------------------------------
    marks, spans, prov = compile_portamento_lane(
        src_sig, src_sig_b, notes, src_events, vib_marks=vib_marks,
        ownership=hybrid)
    curve = flatten_pitd_spans(pitd_v1, spans, part_pos)
    ustx = pdir / f"{phrase}_hybrid.ustx"
    save_ustx(drv.build_phrase_doc(base_doc, base_part, notes,
                                   part_pos, curve, vib_marks,
                                   f"{phrase}_pl", porta_marks=marks),
              ustx)
    rec = ab._load_render(
        drv.render(cfg, ustx, pdir / f"{phrase}_hybrid"),
        notes, t0, t1, nuc)
    qa = _qa_battery(src_sig, src_sig_b, neu_sig, neu_sig_b,
                     src_events, src_events_b, rec, spans,
                     notes, nuc, core_bounds)
    drv._dump(qa, pdir / "qa_hybrid.json")
    hyb_np = qa["non_portamento_event_lanes"]
    base_np = base["qa"]["non_portamento_event_lanes"]
    out_med = qa["out_of_lane_position"].get("med_c")
    base_med = base["qa"]["out_of_lane_position"].get("med_c")
    hybrid_ok = (
        not [r for r in qa["event_shape"]["events"] if r.get("blocking")]
        and not [r for r in qa["event_shape_rmvpe"]["events"]
                 if r.get("blocking")]
        and ab._lane_nonworse(hyb_np["fcpe"], base_np["fcpe"])
        and ab._lane_nonworse(hyb_np["rmvpe"], base_np["rmvpe"])
        and ab._vibrato_missing_count(qa["vibrato"])
            <= base["vibrato_missing"]
        and (out_med is None or base_med is None
             or out_med <= base_med + 5.0))
    hybrid_rec = {
        "ownership_vector": hybrid,
        "ustx": ustx.name, "ustx_sha256": sha256(ustx),
        "wav": rec["wav"].name, "wav_sha256": sha256(rec["wav"]),
        "lane_provenance": prov, "owned_spans_s": spans,
        "blocking_events_fcpe": [
            {"from_note": r["from_note"], "class": r["class"]}
            for r in qa["event_shape"]["events"] if r.get("blocking")],
        "blocking_events_rmvpe": [
            {"from_note": r["from_note"], "class": r["class"]}
            for r in qa["event_shape_rmvpe"]["events"]
            if r.get("blocking")],
        "vibrato_missing": ab._vibrato_missing_count(qa["vibrato"]),
        "out_of_lane_med_c": out_med,
        "accepted": bool(hybrid_ok),
        "qa": qa}

    if all(v == "full_note" for v in hybrid.values()):
        preferred = "full_note"
        reason = ("no single-lane toggle preserved all gates; the "
                  "all-full baseline is retained (aggregate lane "
                  "differences are not attributable to any one lane)")
    elif hybrid_ok:
        preferred = f"hybrid({hybrid})"
        reason = ("hybrid preserves every required gate while "
                  "narrowing ownership on the attributed lanes")
    else:
        preferred = "BLOCKED_PER_LANE"
        reason = ("the composed hybrid fails at least one required "
                  "gate; no representation degrees of freedom may be "
                  "added in this round")

    rep = {"phrase": phrase, "generator_code_head": head,
           "qa_code_head": drv._git_head(),
           "worktree_clean_at_generation": True,
           "base_file_sha256": sha256(drv.BASE_USTX),
           "base_semantic_sha256": semantic_notes_sha256(base_doc),
           "source_edge_evidence": edge_evidence,
           "applied_lanes": lanes, "incremental_tails_s": tails,
           "vectors": results, "attribution": attribution,
           "hybrid": hybrid_rec,
           "verdict": {"preferred": preferred, "reason": reason,
                       "rule": ("per-lane toggle attribution; hybrid "
                                "accepted only with 0 blockers on both "
                                "families, non-worse discrete lanes, "
                                "non-worse vibrato, out-of-lane within "
                                "+5c vs the all-full baseline")}}
    drv._dump(rep, pdir / "perlane_report.json")
    print(f"   preferred={preferred}", flush=True)
    return rep


def _worse_state(before, after):
    order = {"matched": 0, "ambiguous": 1, "source_only": 2,
             "absent": 3}
    return order.get(after, 3) > order.get(before, 3)


def json_brief(d):
    parts = []
    for k in ("discrete_state_changes", "new_render_only"):
        if d.get(k):
            parts.append(f"{k}={len(d[k])}")
    if d.get("new_blockers_rmvpe"):
        parts.append(f"rmvpe_blockers={d['new_blockers_rmvpe']}")
    if d.get("new_blockers_fcpe"):
        parts.append(f"fcpe_blockers={d['new_blockers_fcpe']}")
    if d.get("vibrato_missing_delta"):
        parts.append(f"vib_delta={d['vibrato_missing_delta']}")
    return ", ".join(parts) if parts else "no diffs"


def main():
    head = drv._require_clean_worktree("l7_lane_isolation_perlane")
    cfg = load_config()
    which = sys.argv[1:] or ["P2_slides"]
    base_doc = load_ustx(drv.BASE_USTX)
    caches = {"src_fcpe": drv._npz_f0(drv.SRC_FCPE),
              "src_rmvpe": drv._npz_f0(drv.SRC_RMVPE),
              "neu_fcpe": drv._npz_f0(drv.NEU_FCPE),
              "neu_rmvpe": drv._npz_f0(drv.NEU_RMVPE)}
    for phrase in which:
        run_phrase(phrase, cfg, base_doc, caches, head)


if __name__ == "__main__":
    main()
