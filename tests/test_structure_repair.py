"""M2.5 structure repair — split/merge/boundary_shift (plan2 §10.1).

Human path consumes the M2.4-preserved blocked_structure authority
(repair_authorized_decision snapshot, no re-review). Machine path only
materializes frozen resolved_change_candidate packets that pass the
operation-specific precision gate AND a phrase-level A/B calibration
decision (§10.1.5 Blocker E) — a frozen C classification alone can
never enter the trusted written score.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from agent2utau.repair import (BLOCKED_CONFLICT, CALIB_PENDING, PATCH_OK,
                               REJECTED, apply_structure_ops,
                               apply_structure_plan, build_structure_plan,
                               machine_structure_candidates,
                               validate_structure_patch)
from agent2utau.structure_calibration import (cal_item_id, decide,
                                              calibration_authorized,
                                              rebuild_calibration_state)
from agent2utau.review import build as rb

from test_repair import _human_decision, _mk_run, _pkt, _NOTES


def _split_scc(t0, t1, b):
    return {"kind": "split", "boundary": b,
            "notes": [{"start": t0, "end": b},
                      {"start": b, "end": t1}]}


def _vb(pid, tones, presence=None):
    return [{"id": f"{pid}__v{i}", "status": "resolved_keep",
             "winning_hypothesis": t,
             "correspondence":
                 {"child_presence_rate": (presence or [0.0] * 9)[i]}}
            for i, t in enumerate(tones)]


def _machine_split_pkt(pid="note_0002", boundary=11.2, tones=(60.0, 64.0),
                       cls="TRUE_SPLIT_CANDIDATE", dual=True, nonf0=0.5,
                       gsplit=0.0, vb_status="resolved_keep", sep=False):
    """Frozen finalized machine split packet on _NOTES[2]
    (start 11.0, dur 0.4 -> span [11.0,11.4])."""
    p = _pkt(pid, decision="resolved_change_candidate", tone=58.15,
             sep=sep, c_status="resolved_change_candidate")
    p["structure_adjudication"] = {
        "status": "resolved_change_candidate", "classification": cls,
        "extractor_evidence": {"dual_delta_agreement": dual},
        "boundary_evidence": {"non_f0_support": nonf0},
        "game_structure": {"split_ratio": gsplit}}
    p["structure_change_candidate"] = _split_scc(11.0, 11.4, boundary)
    p["virtual_note_adjudication"] = [
        {"id": f"{pid}__v{i}", "status": vb_status,
         "winning_hypothesis": t,
         "correspondence": {"child_presence_rate": 0.0}}
        for i, t in enumerate(tones)]
    return p


def _machine_merge_pkt(pid="note_0001"):
    """Frozen finalized merge of _NOTES[1](10.5-11.0)+_NOTES[2](11.0-11.4)."""
    p = _pkt(pid, decision="resolved_change_candidate", tone=62.0,
             c_status="resolved_change_candidate")
    p["structure_adjudication"] = {
        "status": "resolved_change_candidate",
        "classification": "TRUE_MERGE_CANDIDATE"}
    p["structure_change_candidate"] = {
        "kind": "merge",
        "span": {"start": 10.5, "end": 11.4, "merge_with": "note_0002"}}
    p["virtual_note_adjudication"] = [
        {"id": f"{pid}__v0", "status": "resolved_change",
         "winning_hypothesis": 61.0,
         "correspondence": {"child_presence_rate": 0.6}}]
    return p


def _split_patch(nid="note_0002", b=11.2, tones=(60.0, 64.0)):
    return {"type": "split", "note_ids": [nid], "boundary": b,
            "children": [{"start": 11.0, "end": b, "tone": tones[0]},
                         {"start": b, "end": 11.4, "tone": tones[1]}]}


def _cal_confirm(run, entry, choice="split"):
    """Fabricate a real verified calibration package + decision.

    Writes OPTION wavs + source clips as real bytes, a schema-bound
    manifest whose audio_package_hash recomputes, then runs the real
    decide() gate (verify_package included)."""
    rid = entry["repair_id"]
    cid = cal_item_id(rid)
    idir = run / "structure_calibration" / "items" / cid
    idir.mkdir(parents=True, exist_ok=True)
    wavs, opts = {}, []
    for i, cand in enumerate(("baseline", "machine_split")):
        b = b"wav" + rid.encode() + bytes([i])
        (idir / f"OPTION_{i}.wav").write_bytes(b)
        h = hashlib.sha256(b).hexdigest()
        wavs[f"OPTION_{i}"] = {"wav_sha256": h}
        opts.append({"option_id": f"OPTION_{i}", "candidate_id": cand,
                     "score_patch": {"type": "identity"}
                     if cand == "baseline" else entry["patch"],
                     "provenance": {"kind": "t"},
                     "wav": f"OPTION_{i}.wav", "wav_sha256": h,
                     "sample_rate": 44100, "frames": 8})
    (idir / "s.wav").write_bytes(b"mix")
    (idir / "v.wav").write_bytes(b"voc")
    srcs = {"original_mix": {"path": "s.wav",
                             "sha256": hashlib.sha256(b"mix").hexdigest()},
            "separated_vocal": {"path": "v.wav",
                                "sha256": hashlib.sha256(b"voc").hexdigest()}}
    man = {"schema": "m25-cal-2", "review_item_id": cid,
           "target_key": "tk-" + rid,
           "target_group": {"packets": [entry["note_id"]],
                            "type": entry["patch"]["type"]},
           "plan_hash": "ph-" + rid, "options": opts,
           "source_reference": srcs,
           "render_provenance": {"impl": "t"},
           "baseline_option": "OPTION_0",
           "phrase": {"start": 0.0, "end": 1.0},
           "context": {"phrase_key": "0.00-1.00"},
           "calibration": {
               "repair_id": rid,
               "patch_sha256": rb.sha(entry["patch"]),
               "candidate_role": "OPTION_1",
               "baseline_option": "OPTION_0",
               "choices": ["split", "baseline", "equivalent",
                           "none_correct"]},
           "review": {"generation": 1}}
    man["audio_package_hash"] = rb.audio_package_hash(
        man["plan_hash"], srcs, wavs, man["render_provenance"])
    (idir / "manifest.json").write_text(json.dumps(man),
                                        encoding="utf-8")
    opt = "OPTION_1" if choice == "split" else \
        ("OPTION_0" if choice == "baseline" else choice)
    return decide(run, cid, opt)


# ---------------------------------------------------- §10.1.2 patch legality

def test_split_patch_validation():
    ok, why = validate_structure_patch(_split_patch(), _NOTES)
    assert ok
    for bad, want in [
            (_split_patch(b=11.02), "boundary_outside_span"),
            (_split_patch(b=11.39), "boundary_outside_span"),
            (_split_patch(b=10.5), "boundary_outside_span"),
            ({"type": "split", "note_ids": ["note_0002"],
              "boundary": 11.2,
              "children": [{"start": 11.0, "end": 11.2, "tone": 60.0}]},
             "bad_split_shape"),
            ({"type": "split", "note_ids": ["note_0002"],
              "boundary": 11.2,
              "children": [{"start": 11.0, "end": 11.25, "tone": 60.0},
                           {"start": 11.25, "end": 11.4, "tone": 64.0}]},
             "children_not_tiling_parent"),
            ({"type": "split", "note_ids": ["note_0002"],
              "boundary": 11.2,
              "children": [{"start": 11.0, "end": 11.2, "tone": 200.0},
                           {"start": 11.2, "end": 11.4, "tone": 64.0}]},
             "tone_invalid"),
            (_split_patch(nid="note_9999"), "note_not_in_candidate0")]:
        ok, why = validate_structure_patch(bad, _NOTES)
        assert not ok and why == want, (bad, why)


def test_merge_patch_validation():
    good = {"type": "merge", "note_ids": ["note_0001", "note_0002"],
            "merged": {"start": 10.5, "end": 11.4, "tone": 61.0}}
    ok, _ = validate_structure_patch(good, _NOTES)
    assert ok
    for bad, want in [
            ({"type": "merge", "note_ids": ["note_0001", "note_0003"],
              "merged": {"start": 10.5, "end": 12.5, "tone": 61.0}},
             "merge_not_adjacent"),
            ({"type": "merge", "note_ids": ["note_0001", "note_0002"],
              "merged": {"start": 10.5, "end": 11.5, "tone": 61.0}},
             "merged_span_mismatch"),
            ({"type": "merge", "note_ids": ["note_0001"],
              "merged": {"start": 10.5, "end": 11.4, "tone": 61.0}},
             "merge_needs_two_notes")]:
        ok, why = validate_structure_patch(bad, _NOTES)
        assert not ok and why == want, (bad, why)


def _gap_notes(gap):
    """note_0000 [10.0,10.5], note_0001 [10.5+gap, 11.0+gap]."""
    return [{"start": 10.0, "dur": 0.5, "tone": 60.0, "voiced": True},
            {"start": 10.5 + gap, "dur": 0.5, "tone": 62.0,
             "voiced": True},
            {"start": 11.5 + gap, "dur": 0.5, "tone": 65.0,
             "voiced": True}]


def test_merge_temporal_adjacency():
    """§10.1.6 Blocker F — index-adjacent != time-contiguous:
    F1 exact shared boundary -> allow
    F2 small gap within MERGE_ADJ_TOL_S -> allow
    F3 gap > tolerance -> merge_temporal_gap
    F4 material overlap -> merge_temporal_overlap
    F5 merged span may never bridge a rejected gap
    """
    def merge_patch(gap):
        ns = _gap_notes(gap)
        return {"type": "merge", "note_ids": ["note_0000", "note_0001"],
                "merged": {"start": 10.0, "end": 11.0 + gap,
                           "tone": 61.0}}

    ok, _ = validate_structure_patch(merge_patch(0.0), _gap_notes(0.0))
    assert ok                                             # F1
    ok, _ = validate_structure_patch(merge_patch(0.04), _gap_notes(0.04))
    assert ok                                             # F2 (<0.06)
    for gap in (0.07, 0.5, 1.0):                          # F3
        ok, why = validate_structure_patch(merge_patch(gap),
                                         _gap_notes(gap))
        assert not ok and why == "merge_temporal_gap", (gap, why)
    # F4: overlap — note_0001 starts before note_0000 ends
    ns = [{"start": 10.0, "dur": 0.6, "tone": 60.0, "voiced": True},
          {"start": 10.5, "dur": 0.5, "tone": 62.0, "voiced": True},
          {"start": 11.5, "dur": 0.5, "tone": 65.0, "voiced": True}]
    bad = {"type": "merge", "note_ids": ["note_0000", "note_0001"],
           "merged": {"start": 10.0, "end": 11.0, "tone": 61.0}}
    ok, why = validate_structure_patch(bad, ns)
    assert not ok and why == "merge_temporal_overlap"
    # F5: a 3-note merge bridging a >tol gap rejects at the gap pair
    ns = _gap_notes(0.2)
    bad = {"type": "merge",
           "note_ids": ["note_0000", "note_0001", "note_0002"],
           "merged": {"start": 10.0, "end": 11.7, "tone": 61.0}}
    ok, why = validate_structure_patch(bad, ns)
    assert not ok and why == "merge_temporal_gap"


def test_boundary_shift_validation():
    good = {"type": "boundary_shift", "note_ids": ["note_0002"],
            "start": 11.0, "end": 11.35}
    ok, _ = validate_structure_patch(good, _NOTES)
    assert ok
    for bad, want in [
            ({"type": "boundary_shift", "note_ids": ["note_0002"],
              "start": 10.9, "end": 11.4}, "overlaps_previous"),
            ({"type": "boundary_shift", "note_ids": ["note_0002"],
              "start": 11.0, "end": 12.05}, "overlaps_next"),
            ({"type": "boundary_shift", "note_ids": ["note_0002"],
              "start": 11.0, "end": 11.4}, "no_op"),
            ({"type": "boundary_shift", "note_ids": ["note_0002"],
              "start": 11.0, "end": 11.01},
             "negative_or_tiny_duration")]:
        ok, why = validate_structure_patch(bad, _NOTES)
        assert not ok and why == want, (bad, why)


# ------------------------------------------------- §10.1.2 machine gate

def test_machine_split_enters_through_gate():
    cands = machine_structure_candidates([_machine_split_pkt()])
    assert len(cands) == 1
    c = cands[0]
    assert c["source_type"] == "machine_structure"
    assert c["patch"]["type"] == "split"
    assert [ch["tone"] for ch in c["patch"]["children"]] == [60.0, 64.0]
    a = c["authority"]
    assert a["classification"] == "TRUE_SPLIT_CANDIDATE"
    assert a["virtual_b_statuses"] == ["resolved_keep", "resolved_keep"]


@pytest.mark.parametrize("mut", [
    lambda p: p["state"].update(decision="needs_phrase_review"),
    lambda p: p["structure_adjudication"].update(
        classification="UNRESOLVED_STRUCTURE"),
    lambda p: p["structure_adjudication"]
        ["extractor_evidence"].update(dual_delta_agreement=False),
    lambda p: p["structure_adjudication"]
        ["boundary_evidence"].update(non_f0_support=0.0),
    lambda p: p["virtual_note_adjudication"][0]
        .update(status="unresolved"),
    lambda p: p.pop("virtual_note_adjudication"),
    lambda p: p["virtual_note_adjudication"][0]
        .update(winning_hypothesis=float("nan")),
    lambda p: p["separation"].update(separation_sensitive=True),
    lambda p: p["structure_change_candidate"]
        .update(notes=[{"start": 11.0, "end": 11.02},
                       {"start": 11.02, "end": 11.4}]),
])
def test_machine_split_gate_fail_closed(mut):
    """No boundary confidence / unresolved virtual-B / tiny child /
    separation sensitivity -> no machine structure repair."""
    p = _machine_split_pkt()
    mut(p)
    assert machine_structure_candidates([p]) == []


def test_machine_merge_enters_through_gate():
    cands = machine_structure_candidates([_machine_merge_pkt()])
    assert len(cands) == 1
    assert cands[0]["patch"] == {
        "type": "merge", "note_ids": ["note_0001", "note_0002"],
        "merged": {"start": 10.5, "end": 11.4, "tone": 61.0}}


# ------------------------------------------------------------- apply ops

def test_apply_split_expands_children():
    e = {"affected": [2], "patch": _split_patch()}
    out = apply_structure_ops(_NOTES, [e])
    assert len(out) == len(_NOTES) + 1
    assert out[2]["start"] == 11.0 and out[2]["tone"] == 60.0
    assert out[2]["dur"] == pytest.approx(0.2)
    assert out[3]["start"] == 11.2 and out[3]["tone"] == 64.0
    assert out[3]["dur"] == pytest.approx(0.2)
    assert out[4] == _NOTES[3]                    # non-target intact
    assert _NOTES[2]["tone"] == 58.15             # source untouched


def test_apply_merge_collapses():
    e = {"affected": [1, 2],
         "patch": {"type": "merge",
                   "note_ids": ["note_0001", "note_0002"],
                   "merged": {"start": 10.5, "end": 11.4, "tone": 61.0}}}
    out = apply_structure_ops(_NOTES, [e])
    assert len(out) == len(_NOTES) - 1
    assert out[1]["start"] == 10.5 and out[1]["tone"] == 61.0
    assert out[1]["dur"] == pytest.approx(0.9)
    assert out[2] == _NOTES[3]


def test_apply_boundary_shift():
    e = {"affected": [2],
         "patch": {"type": "boundary_shift", "note_ids": ["note_0002"],
                   "start": 10.95, "end": 11.35}}
    out = apply_structure_ops(_NOTES, [e])
    assert len(out) == len(_NOTES)
    assert out[2]["start"] == 10.95
    assert out[2]["dur"] == pytest.approx(0.4)
    assert out[2]["tone"] == 58.15                # tone untouched


# --------------------------------------------------- §10.1.3 plan/apply

def test_machine_candidate_is_pending_until_calibrated(tmp_path):
    """§10.1.5: a frozen TRUE_SPLIT_CANDIDATE alone can never apply —
    it stays an auditable calibration_pending candidate until a
    human_confirmed_machine_split decision binds repair_id+patch."""
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    plan = build_structure_plan(run)
    e = plan["repairs"][0]
    assert e["status"] == CALIB_PENDING
    assert e["blocked_reason"] == "awaiting_phrase_calibration"
    res = apply_structure_plan(run, plan)
    assert res["score"]["notes"] == _NOTES        # never applied
    blk = res["manifest"]["blocked"][0]
    assert blk["status"] == CALIB_PENDING


def test_structure_plan_apply_machine_split(tmp_path):
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    plan = build_structure_plan(run)
    e = plan["repairs"][0]
    assert e["status"] == CALIB_PENDING
    _cal_confirm(run, e)                          # A/B confirms split
    plan = build_structure_plan(run)
    e = plan["repairs"][0]
    assert e["status"] == PATCH_OK
    assert e["repair_id"].startswith("srp-")
    assert e["authority"]["calibration"]["outcome"] == \
        "human_confirmed_machine_split"
    res = apply_structure_plan(run, plan)
    sc = res["score"]
    assert len(sc["notes"]) == len(_NOTES) + 1
    assert sc["notes"][2]["tone"] == 60.0
    assert sc["notes"][3]["tone"] == 64.0
    c0 = json.loads((run / "diagnostic" / "baseline_game.json")
                    .read_text())["notes"]
    assert len(c0) == len(_NOTES)                 # C0 immutable
    m = res["manifest"]["repairs"][0]
    assert m["operation"] == "split"
    assert m["authority"]["packet_id"] == "note_0002"
    assert m["authority"]["calibration"]["revision_id"]


@pytest.mark.parametrize("choice", ["baseline", "equivalent",
                                    "none_correct"])
def test_unconfirmed_outcomes_never_authorize(tmp_path, choice):
    """baseline/equivalent/none_correct -> no repair authority;
    the candidate stays pending and never enters the score."""
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    e = build_structure_plan(run)["repairs"][0]
    _cal_confirm(run, e, choice=choice)
    plan = build_structure_plan(run)
    assert plan["repairs"][0]["status"] == CALIB_PENDING
    res = apply_structure_plan(run, plan)
    assert res["score"]["notes"] == _NOTES


def test_superseded_confirmation_restales(tmp_path):
    """A newer decision superseding the confirmation removes the
    authority — the next plan is pending and any already-built plan
    goes stale at apply."""
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    e = build_structure_plan(run)["repairs"][0]
    _cal_confirm(run, e, choice="split")
    plan = build_structure_plan(run)
    assert plan["repairs"][0]["status"] == PATCH_OK
    _cal_confirm(run, e, choice="baseline")       # re-review: false pos
    assert build_structure_plan(
        run)["repairs"][0]["status"] == CALIB_PENDING
    with pytest.raises(RuntimeError, match="calibration_revoked"):
        apply_structure_plan(run, plan)


def test_calibration_summary(tmp_path):
    run = _mk_run(tmp_path, [_machine_split_pkt(),
                             _machine_split_pkt(pid="note_0003",
                                                boundary=12.2)])
    pk = json.loads((run / "diagnostic" / "residual_triage.json")
                    .read_text())
    pk[1]["structure_change_candidate"] = \
        {"kind": "split", "boundary": 12.2,
         "notes": [{"start": 12.0, "end": 12.2},
                   {"start": 12.2, "end": 12.5}]}
    (run / "diagnostic" / "residual_triage.json").write_text(
        json.dumps(pk), encoding="utf-8")
    entries = build_structure_plan(run)["repairs"]
    _cal_confirm(run, entries[0], "split")
    _cal_confirm(run, entries[1], "equivalent")
    # state is derived from plan.json items — register them
    from agent2utau.structure_calibration import calib_dir, _jwrite
    _jwrite(calib_dir(run) / "plan.json",
            {"schema": "m25-cal-2", "created_at": 0,
             "diagnostic_run_id": "diag-x",
             "candidate0_sha256": "x",
             "items": [{"cal_item_id": cal_item_id(e["repair_id"]),
                        "repair_id": e["repair_id"],
                        "note_id": e["note_id"],
                        "type": "split", "phrase": {}, "phrase_key": "",
                        "plan_hash": "", "audio_package_hash": "",
                        "package_state": "", "manifest": ""}
                       for e in entries]})
    st = rebuild_calibration_state(run)
    assert st["total_machine_split_candidates"] == 2
    assert st["reviewed_count"] == 2
    assert st["split_preferred_count"] == 1
    assert st["equivalent_count"] == 1
    assert st["measured_song_level_precision"] == 0.5


def test_human_structure_authority_applies(tmp_path):
    """§10.1.1: the M2.4 blocked_structure selection applies through
    the structure engine — same snapshot, no re-review."""
    run = _mk_run(tmp_path)
    rev, man = _human_decision(run, _split_patch())
    plan = build_structure_plan(run)
    e = next(e for e in plan["repairs"]
             if e["source_type"] == "human_selected")
    assert e["status"] == PATCH_OK
    assert e["authority"]["revision_id"] == rev["revision_id"]
    res = apply_structure_plan(run, plan)
    assert len(res["score"]["notes"]) == len(_NOTES) + 1
    m = res["manifest"]["repairs"][0]
    assert m["authority"]["audio_package_hash"] == \
        man["audio_package_hash"]


def test_conflict_and_dedupe(tmp_path):
    """Same note, different structure patches -> blocked_conflict;
    identical patches dedupe with provenance kept."""
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    _human_decision(run, _split_patch(tones=(61.0, 65.0)))
    e0 = build_structure_plan(run)["repairs"][0]
    _cal_confirm(run, next(e for e in [e0]
                      if e["source_type"] == "machine_structure"))
    plan = build_structure_plan(run)
    assert all(e["status"] == BLOCKED_CONFLICT
               for e in plan["repairs"])
    res = apply_structure_plan(run, plan)
    assert res["score"]["notes"] == _NOTES        # nothing applied

    run2 = _mk_run(tmp_path / "b", [_machine_split_pkt()])
    _human_decision(run2, _split_patch())          # identical patch
    e1 = next(e for e in build_structure_plan(run2)["repairs"]
              if e["source_type"] == "machine_structure")
    _cal_confirm(run2, e1)
    plan2 = build_structure_plan(run2)
    st = [e["status"] for e in plan2["repairs"]]
    assert st.count("eligible") == 1 and "deduped" in st


def test_rollback_subset_zero(tmp_path):
    pk = [_machine_split_pkt(pid="note_0000", boundary=10.2,
                             tones=(60.0, 64.0)),
          _machine_split_pkt()]
    # fix child spans for note_0000 (10.0-10.4)
    pk[0]["structure_change_candidate"] = _split_scc(10.0, 10.4, 10.2)
    run = _mk_run(tmp_path, pk)
    plan = build_structure_plan(run)
    for e in plan["repairs"]:
        _cal_confirm(run, e)
    plan = build_structure_plan(run)
    ids = [e["repair_id"] for e in plan["repairs"]]
    r1 = apply_structure_plan(run, plan)
    assert len(r1["score"]["notes"]) == len(_NOTES) + 2
    r2 = apply_structure_plan(run, plan, exclude=[ids[0]])
    assert len(r2["score"]["notes"]) == len(_NOTES) + 1
    assert r2["score"]["notes"][0]["tone"] == 60.0   # C0 note intact
    r3 = apply_structure_plan(run, plan, only=[])
    assert r3["score"]["notes"] == _NOTES


def test_tampered_plan_hash_refused(tmp_path):
    """§10.1.4 P2: a tampered repair patch with the old plan_hash must
    fail — hash is recomputed at apply."""
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    plan = build_structure_plan(run)
    import copy
    bad = copy.deepcopy(plan)
    bad["repairs"][0]["patch"]["children"][0]["tone"] = 99.0
    with pytest.raises(RuntimeError, match="plan_hash_mismatch"):
        apply_structure_plan(run, bad)
    bad2 = copy.deepcopy(plan)
    bad2["bindings"]["residual_triage_sha256"] = "x"
    with pytest.raises(RuntimeError, match="stale"):
        apply_structure_plan(run, bad2)


def test_legacy_schema_refused(tmp_path):
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    plan = build_structure_plan(run)
    bad = dict(plan); bad["schema"] = "m24-2"
    with pytest.raises(RuntimeError, match="unsupported_plan_schema"):
        apply_structure_plan(run, bad)


def test_no_machine_candidates_no_repairs(tmp_path):
    """Real-run shape: needs_phrase_review / keep packets contribute
    nothing; 0 repairs is legal."""
    run = _mk_run(tmp_path, [_pkt("note_0393",
                                  decision="needs_phrase_review"),
                             _pkt("note_0414",
                                  decision="needs_phrase_review")])
    plan = build_structure_plan(run)
    assert plan["repairs"] == []
    res = apply_structure_plan(run, plan)
    assert res["score"]["notes"] == _NOTES


# ------------------------------------------- §10.1.5A review readiness (G)

def _fake_run_dict():
    """Minimal run dict for plan_calibration/semantic_diff — no disk."""
    pkts = [_machine_split_pkt()]
    return {"run_id": "diag-x", "song_sha256": "song",
            "packets": pkts,
            "packets_by_id": {p["id"]: p for p in pkts},
            "baseline_notes": _NOTES,
            "candidate0_sha256": "c0-sha",
            "duration": 20.0, "lrc_lines": [], "silences": []}


def test_g1_legacy_cal1_store_is_archived_and_dead(tmp_path):
    """G1: an m25-cal-1 store is renamed to audit-only on first access;
    its packages/decisions can never authorize or be decided again."""
    from agent2utau.structure_calibration import (
        calib_dir, ensure_calib_authority)
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    cdir = calib_dir(run)
    (cdir / "items" / "x").mkdir(parents=True)
    (cdir / "plan.json").write_text(
        json.dumps({"schema": "m25-cal-1", "items": []}))
    ensure_calib_authority(run)
    assert (run / "structure_calibration_m25cal1_audit" /
            "plan.json").exists()
    assert cdir.exists() and not (cdir / "plan.json").exists()
    ensure_calib_authority(run)          # idempotent — nothing happens
    assert cdir.exists()


def test_g1_legacy_package_refused_by_decide_and_authorize(tmp_path):
    """G1: a package with schema m25-cal-1 is not decidable; a confirmed
    decision whose manifest was re-tagged m25-cal-1 loses authority."""
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    e = build_structure_plan(run)["repairs"][0]
    rev = _cal_confirm(run, e, "split")
    assert calibration_authorized(run, e["repair_id"], e["patch"])
    mpath = (run / "structure_calibration" / "items"
             / rev["cal_item_id"] / "manifest.json")
    man = json.loads(mpath.read_text(encoding="utf-8"))
    man["schema"] = "m25-cal-1"
    mpath.write_text(json.dumps(man), encoding="utf-8")
    assert calibration_authorized(run, e["repair_id"], e["patch"]) \
        is None
    with pytest.raises(RuntimeError, match="audit-only"):
        decide(run, rev["cal_item_id"], "OPTION_1")


def test_g2_g3_semantic_diff_outside_target_empty(tmp_path):
    """G2/G3: Baseline is C0 verbatim outside the target; the Candidate
    differs only by the declared patch."""
    from agent2utau.structure_calibration import (plan_calibration,
                                                semantic_diff)
    run = _fake_run_dict()
    items = plan_calibration(run)
    assert len(items) == 1
    d = semantic_diff(items[0])
    assert d["schema"] == "m25-cal-2"
    assert d["outside_target"]["score_diff"] == []
    assert d["outside_target"]["lyric_diff"] == []
    assert d["target"]["operation"] == "split"
    assert len(d["within_target"]["before"]) == 1
    assert len(d["within_target"]["after"]) == 2   # the two children
    # the diff must DETECT a renderer that bleeds outside the declared
    # target — simulate a buggy apply_patch that retunes a neighbour.
    import agent2utau.review.build as rbuild
    real = rbuild.apply_patch

    def bleeding(context, patch):
        out = real(context, patch)
        if patch.get("type") == "split":
            for n in out:
                if n["id"] == "note_0003":
                    n["tone"] += 1.0
        return out
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(rbuild, "apply_patch", bleeding)
    try:
        d2 = semantic_diff(items[0])
        kinds = [x["kind"] for x in d2["outside_target"]["score_diff"]]
        assert "note_changed_outside_target" in kinds
    finally:
        monkeypatch.undo()


def test_g4_g7_neutral_vowel_deterministic(tmp_path):
    """G4/G7: a/+ semantics are mechanical — touch→'+', gap→'a' — and
    never consult the lyric table, so melisma/re-articulation and
    repeated-char cases cannot be corrupted by lyric guessing."""
    from agent2utau.review.render import neutral_vowels, option_notes
    notes = [{"id": "n0", "start": 0.0, "end": 0.5, "dur": 0.5,
              "tone": 60.0},
             {"id": "n1", "start": 0.5, "end": 1.0, "dur": 0.5,
              "tone": 62.0},
             {"id": "n2", "start": 1.4, "end": 2.0, "dur": 0.6,
              "tone": 64.0}]
    assert neutral_vowels(notes) == ["a", "+", "a"]
    item = {"lyric_contract": "neutral_vowel",
            "phrase": {"start": 0.0},
            "context": notes,
            "options": []}
    opt = {"option_id": "OPTION_0", "candidate_id": "baseline",
           "score_patch": {"type": "identity"}}
    out = option_notes(item, opt, chars=[{"char": "真", "start": 0.0,
                                          "end": 2.0}])
    assert [n["lyric"] for n in out] == ["a", "+", "a"]


def test_g5_diagnostic_pitch_contract_uniform(tmp_path):
    """G5: no PITD/pitch-curve fields appear on either option — the
    diagnostic contract is uniform integer tone + no PITD."""
    from agent2utau.structure_calibration import (plan_calibration,
                                                semantic_diff)
    from agent2utau.review.render import option_notes
    items = plan_calibration(_fake_run_dict())
    it = items[0]
    for opt in it["options"]:
        out = option_notes(it, opt, chars=[])
        assert all(set(n) <= {"lyric", "start", "end", "dur", "tone"}
                   for n in out)
    d = semantic_diff(it)
    assert "no PITD" in d["outside_target"]["pitch_semantics"]
    assert "max_deviation_cents" in d["tone_integerization"]


def test_g6_no_silent_real_lyric_fallback(tmp_path):
    """G6: with lyric_contract=neutral_vowel the renderer must not fall
    back to guessed real lyrics even when aligned chars exist."""
    from agent2utau.structure_calibration import plan_calibration
    from agent2utau.review.render import option_notes
    items = plan_calibration(_fake_run_dict())
    it = items[0]
    assert it["lyric_contract"] == "neutral_vowel"
    chars = [{"char": "字", "start": 9.0, "end": 15.0}]
    for opt in it["options"]:
        out = option_notes(it, opt, chars=chars)
        assert set(n["lyric"] for n in out) <= {"a", "+"}


def _tracked_all(item_ids=(), phrase_keys=()):
    """Everything the Git-evidence rule could require — simulates a
    fully-committed store for _git_tracked_set monkeypatches."""
    from agent2utau.structure_calibration import GIT_REQUIRED_ITEM_FILES
    s = {"plan.json", "state.json", "pilot_review.json",
         "qc/verdict.json", "qc/audit.jsonl"}
    for pk in phrase_keys:
        s |= {f"phrases/{pk}/SOURCE_PHRASE_original_mix.wav",
              f"phrases/{pk}/SOURCE_PHRASE_separated_vocal.wav",
              f"phrases/{pk}/SOURCE_PHRASE_original_mix_LISTEN.wav",
              f"phrases/{pk}/"
              "SOURCE_PHRASE_separated_vocal_LISTEN.wav"}
    for iid in item_ids:
        s |= {f"items/{iid}/{f}" for f in GIT_REQUIRED_ITEM_FILES}
    return s


def _g5h_store(tmp_path, monkeypatch, n=2, auto_ready=True,
               contract="real_lyric_review",
               stale_iids=(), not_ready_iids=(), bad_verify_iids=()):
    """§G5H fixture: a store whose plan-level default contract is
    neutral_vowel nv1 while the SAMPLES are real_lyric_review rlv2 —
    the exact deadlock G5H fixes. Returns (run_dir, items, contract).
    """
    import agent2utau.structure_calibration as sc
    monkeypatch.setattr(sc, "_load_run", lambda d: {})
    monkeypatch.setattr(
        sc, "_verify_package",
        lambda man, d: (d.name not in bad_verify_iids, "ok"))
    cdir = tmp_path / "structure_calibration"
    (cdir / "items").mkdir(parents=True, exist_ok=True)
    sha = sc.render_contract_sha({}, sc._rph_hash(), contract)
    items = []
    for i in range(n):
        nid = sc.PILOT_NOTE_IDS[i] if i < len(sc.PILOT_NOTE_IDS) \
            else f"note_{i:04d}"
        iid, pk = f"cal-s{i}", f"{i}.00-{i+5}.00"
        (cdir / "items" / iid).mkdir(exist_ok=True)
        rec_sha = "stale-old-sha" if iid in stale_iids else sha
        man = {"schema": sc.CALIB_SCHEMA,
               "package_state": "valid",
               "audio_package_hash": f"aph-{iid}",
               "calibration": {
                   "repair_id": f"srp-s{i}",
                   "lyric_contract": contract,
                   "lyric_mapping_impl":
                       sc.LYRIC_MAPPING_IMPL_VERSION[contract],
                   "contract_sha256": rec_sha}}
        (cdir / "items" / iid / "manifest.json").write_text(
            json.dumps(man), encoding="utf-8")
        (cdir / "items" / iid / "signal_qc.json").write_text(
            json.dumps({"auto_flags": [],
                        "auto_review_ready":
                            iid not in not_ready_iids and auto_ready}),
            encoding="utf-8")
        items.append({"cal_item_id": iid, "repair_id": f"srp-s{i}",
                      "note_id": nid, "type": "split",
                      "phrase": {"start": float(i), "end": float(i + 5)},
                      "phrase_key": pk,
                      "audio_package_hash": f"aph-{iid}",
                      "package_state": "valid",
                      "lyric_contract": contract,
                      "contract_sha256": rec_sha,
                      "signal_qc_flags": []})
    (cdir / "plan.json").write_text(json.dumps(
        {"schema": sc.CALIB_SCHEMA, "lyric_contract": "neutral_vowel",
         "contract_sha256": "store-default-nv1", "items": items}),
        encoding="utf-8")
    (cdir / "pilot_review.json").write_text(json.dumps(
        {"schema": sc.CALIB_SCHEMA, "kind": "pilot_review",
         "groups": [{"note_id": it["note_id"],
                     "cal_item_id": it["cal_item_id"]}
                    for it in items]}), encoding="utf-8")
    return tmp_path, items, sha


def _g5h_tracked(items):
    return _tracked_all(
        [i["cal_item_id"] for i in items],
        [i["phrase_key"] for i in items])


def test_g9_review_ready_defaults_false(tmp_path, monkeypatch):
    """G9/G5H: review-ready is false until an explicit verdict; a PASS
    must name its exact sample set — it can never fall back to the
    plan-level default contract."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch)
    iid = items[0]["cal_item_id"]
    assert not sc.review_ready(run)
    sc.write_verdict(run, "FAIL", auditor="t")
    assert not sc.review_ready(run)
    with pytest.raises(RuntimeError, match="samples required"):
        sc.write_verdict(run, "PASS", auditor="t")
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    rec = sc.write_verdict(run, "PASS", auditor="t",
                           sample_ids=[iid, items[1]["cal_item_id"]])
    assert rec["contract_sha256"] == sha        # derived from samples
    assert rec["pilot"]["contract_sha256"] == sha
    assert rec["pilot"]["pilot_payload_sha256"]
    assert sc.review_ready(run)


def test_g10_full_batch_blocked_until_qc_pass(tmp_path, monkeypatch):
    """G10/G5H: build_calibration with no `only` filter is a full
    batch — blocked until a committed QC PASS binds THIS batch's
    contract. A verdict over a different contract (e.g. the rlv2
    pilot) can never authorize a neutral-vowel batch."""
    import agent2utau.review.render as rr
    import agent2utau.structure_calibration as sc
    monkeypatch.setattr(rr, "load_run", lambda p: _fake_run_dict())
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    with pytest.raises(RuntimeError, match="QC PASS"):
        sc.build_calibration(run, render=False)
    # a sample/subset build is the allowed pre-QC path — built here
    # under the review contract so the verdict can bind it
    res = sc.build_calibration(run, render=False, only=["note_0002"],
                               lyric_contract="real_lyric_review")
    iid = res["items"][0]["cal_item_id"]
    cdir = run / "structure_calibration"
    (cdir / "items" / iid / "signal_qc.json").write_text(
        json.dumps({"auto_flags": [], "auto_review_ready": True}))
    plan = json.loads((cdir / "plan.json").read_text(encoding="utf-8"))
    plan["items"][0]["signal_qc_flags"] = []
    plan["items"][0]["package_state"] = \
        json.loads((cdir / "items" / iid / "manifest.json")
                   .read_text(encoding="utf-8")).get("package_state")
    (cdir / "plan.json").write_text(json.dumps(plan))
    (cdir / "pilot_review.json").write_text(json.dumps(
        {"schema": sc.CALIB_SCHEMA, "kind": "pilot_review",
         "groups": [{"note_id": "note_0002", "cal_item_id": iid}]}))
    monkeypatch.setattr(sc, "_load_run", lambda d: {})
    monkeypatch.setattr(sc, "_verify_package",
                        lambda m, d: (True, "ok"))
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _tracked_all(
                            [iid], [res["items"][0]["phrase_key"]]))
    sc.write_verdict(run, "PASS", auditor="t", sample_ids=[iid])
    res2 = sc.build_calibration(run, render=False,
                                lyric_contract="real_lyric_review")
    assert len(res2["items"]) == 1
    it_dir = cdir / "items" / res2["items"][0]["cal_item_id"]
    assert (it_dir / "semantic_diff.json").exists()      # G8 artifact
    plan = json.loads((cdir / "plan.json").read_text(encoding="utf-8"))
    assert plan["schema"] == "m25-cal-2"


# --------------------------------- §10.1.5A Git evidence + G5A/G5B artifacts

def test_git_evidence_pass_refused_without_commits(tmp_path, monkeypatch):
    """Git-evidence rule: a PASS verdict is refused while required
    artifacts are uncommitted — local existence never counts."""
    import agent2utau.structure_calibration as sc
    run, items, _ = _g5h_store(tmp_path, monkeypatch)
    ids = [i["cal_item_id"] for i in items]
    monkeypatch.setattr(sc, "_git_tracked_set", lambda d: None)
    with pytest.raises(RuntimeError, match="not committed to Git"):
        sc.write_verdict(run, "PASS", auditor="t", sample_ids=ids)
    monkeypatch.setattr(sc, "_git_tracked_set", lambda d: {"plan.json"})
    with pytest.raises(RuntimeError, match="not committed to Git"):
        sc.write_verdict(run, "PASS", auditor="t", sample_ids=ids)
    rec = sc.write_verdict(run, "FAIL", "c", auditor="t")
    assert rec["verdict"] == "FAIL"


def test_git_evidence_review_ready_needs_qc_committed(tmp_path,
                                                      monkeypatch):
    """A recorded PASS only takes effect after the qc files themselves
    are committed — the verdict must exist in Git, not just on disk."""
    import agent2utau.structure_calibration as sc
    run, items, _ = _g5h_store(tmp_path, monkeypatch)
    base = _g5h_tracked(items) - {"qc/verdict.json", "qc/audit.jsonl"}
    monkeypatch.setattr(sc, "_git_tracked_set", lambda d: set(base))
    sc.write_verdict(run, "PASS", auditor="t",
                     sample_ids=[i["cal_item_id"] for i in items])
    assert not sc.review_ready(run)      # qc files not committed yet
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    assert sc.review_ready(run)


def test_git_evidence_legacy_verdict_never_ready(tmp_path, monkeypatch):
    """Verdicts recorded before the Git-evidence regime (no
    git_evidence_at_record) OR before G5H (no pilot binding) can never
    flip review_ready — even when every artifact is committed."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch)
    cdir = run / "structure_calibration" / "qc"
    cdir.mkdir(parents=True)
    (cdir / "audit.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    # pre-Git-evidence verdict
    (cdir / "verdict.json").write_text(json.dumps({
        "schema": sc.CALIB_SCHEMA, "verdict": "PASS",
        "contract_sha256": sha, "auditor": "devin",
        "sample_ids": [i["cal_item_id"] for i in items]}),
        encoding="utf-8")
    assert not sc.review_ready(run)
    # pre-G5H verdict: git evidence recorded but bound the store-level
    # default contract — no per-sample pilot authority
    (cdir / "verdict.json").write_text(json.dumps({
        "schema": sc.CALIB_SCHEMA, "verdict": "PASS",
        "contract_sha256": sha, "auditor": "devin",
        "git_evidence_at_record": {"complete": True, "checked": 99},
        "sample_ids": [i["cal_item_id"] for i in items]}),
        encoding="utf-8")
    assert not sc.review_ready(run)


def _fake_rendered_item(tmp_path, name="cal-x", region=(2.0, 2.5),
                        phrase_start=0.0, dur=6.0, sr=8000,
                        cand_gain=1.0, boundary=None):
    """Write a minimal rendered item dir: option wavs + source focus +
    manifest with a declared split patch (asymmetric by default)."""
    import numpy as np
    import soundfile as sf
    idir = tmp_path / "items" / name
    idir.mkdir(parents=True)
    t = np.arange(int(sr * dur)) / sr
    base = 0.1 * np.sin(2 * np.pi * 200 * t)
    cand = base * cand_gain
    sf.write(str(idir / "OPTION_0.wav"), base, sr)
    sf.write(str(idir / "OPTION_1.wav"), cand, sr)
    for nm in ("SOURCE_FOCUS_original_mix.wav",
               "SOURCE_FOCUS_separated_vocal.wav"):
        sf.write(str(idir / nm), base, sr)
    b = boundary if boundary is not None else (region[0] + 0.2)
    patch = {"type": "split", "note_ids": ["n1"], "boundary": b,
             "children": [{"start": region[0], "end": b, "tone": 62.0},
                          {"start": b, "end": region[1], "tone": 64.0}]}
    man = {"review_item_id": name,
           "calibration": {"repair_id": "srp-x",
                           "baseline_option": "OPTION_0",
                           "candidate_role": "OPTION_1"},
           "options": [{"option_id": "OPTION_0", "wav": "OPTION_0.wav",
                        "score_patch": {"type": "identity"}},
                       {"option_id": "OPTION_1", "wav": "OPTION_1.wav",
                        "score_patch": patch}],
           "target_group": {"region": list(region)},
           "phrase": {"start": phrase_start,
                      "end": phrase_start + dur}}
    (idir / "manifest.json").write_text(json.dumps(man))
    return idir, man


def _fake_f0_series(segments, dur, hop=0.01):
    """Fake extract_f0 dict: voiced midi segments on a hop grid,
    times are clip-relative seconds."""
    import numpy as np
    n = int(dur / hop)
    times = np.arange(n) * hop
    hz = np.zeros(n)
    voiced = np.zeros(n, dtype=bool)
    for s, e, m in segments:
        msk = (times >= s) & (times < e)
        voiced |= msk
        hz[msk] = 440.0 * 2 ** ((m - 69.0) / 12.0)
    return {"times": times, "f0_hz": hz, "voiced": voiced,
            "backend": "test:fake", "n_frames": n}


def test_target_focus_crops_and_signal_qc(tmp_path, monkeypatch):
    """G5A/G5B: BASELINE/CANDIDATE_TARGET.wav are crops of the real
    rendered wavs at region±0.5s; signal_qc.json records drift metrics."""
    import soundfile as sf
    import agent2utau.structure_calibration as sc
    flat = _fake_f0_series([(0.0, 6.0, 64.0)], dur=6.0)
    monkeypatch.setattr(sc, "_extract_f0", lambda p: flat)
    idir, man = _fake_rendered_item(tmp_path, region=(2.0, 2.5),
                                    phrase_start=1.0)
    qc = sc.augment_item(idir)
    info = sf.info(str(idir / "BASELINE_TARGET.wav"))
    # window = 1.5..3.0 absolute → phrase-relative 0.5..2.0 → 1.5s
    assert info.frames == int(1.5 * 8000)
    assert (idir / "CANDIDATE_TARGET.wav").exists()
    assert (idir / "BASELINE_CORE.wav").exists()
    assert (idir / "SOURCE_CORE_separated_vocal.wav").exists()
    assert (idir / "signal_qc.json").exists()
    assert qc["target_window"]["absolute"] == [1.5, 3.0]
    assert qc["option_loudness_ratio"] == pytest.approx(1.0, abs=0.01)
    assert qc["auto_review_ready"] is True       # identical renders
    assert qc["f0_qc"]["candidate_structure_error"] == 0.0
    # loudness drift is flagged when options diverge in level
    import soundfile as sf2
    import numpy as np
    t = np.arange(8000 * 6) / 8000
    sf2.write(str(idir / "OPTION_1.wav"),
              0.19 * np.sin(2 * np.pi * 200 * t), 8000)
    qc2 = sc.signal_qc(man, idir)
    assert qc2["option_loudness_ratio"] == pytest.approx(1.9, abs=0.01)
    assert any("option_loudness_drift" in f for f in qc2["auto_flags"])


def test_signal_qc_flags_phrase_wide_drift(tmp_path, monkeypatch):
    """G5F: canonical out-of-target divergence stays ON THE RECORD in
    renderer_global_context (audit), while the shared-context splice
    keeps the LISTEN surface clean — the review gate measures the
    surface, not the canonical bleed."""
    import numpy as np
    import soundfile as sf
    import agent2utau.structure_calibration as sc
    monkeypatch.setattr(
        sc, "_extract_f0",
        lambda p: _fake_f0_series([(0.0, 6.0, 64.0)], dur=6.0))
    idir, man = _fake_rendered_item(tmp_path, region=(2.0, 3.0))
    # overwrite OPTION_1: identical inside target, divergent after 4s
    sr, t = 8000, np.arange(8000 * 6) / 8000
    c = 0.1 * np.sin(2 * np.pi * 200 * t)
    c[int(4 * sr):] = 0.18 * np.sin(2 * np.pi * 260 * t[int(4 * sr):])
    sf.write(str(idir / "OPTION_1.wav"), c, sr)
    qc = sc.signal_qc(man, idir)
    # canonical divergence still recorded verbatim (never hidden)
    assert qc["post_target_ab_diff_rms_ratio"] > 0.5
    ctx = qc["renderer_global_context"]
    assert ctx["canonical_post_ab_diff_rms_ratio"] > 0.5
    assert any("post_target_ab_drift" in f for f in ctx["flags"])
    # …but the splice replaces the candidate's divergent tail with the
    # shared baseline context → the surface the reviewer hears is clean
    assert qc["listen_surface"]["construction"] == \
        "shared_context_splice"
    assert qc["listen_surface"]["post_outside_ab_diff_rms_ratio"] < 0.05
    assert qc["auto_review_ready"] is True
    assert qc["target_focus_is_primary"] is True


def test_target_wav_blind_role_mapping(tmp_path):
    """Web TARGET/CORE_i endpoints stay blind: OPTION_i resolves
    through the manifest to its role's wav — A/B labels never leak."""
    from agent2utau.calib_web import _role_wav
    idir, man = _fake_rendered_item(tmp_path / "structure_calibration",
                                    name="cal-map")
    # candidate_role is OPTION_1 in the fixture; flip to check mapping
    man["calibration"]["baseline_option"] = "OPTION_1"
    man["calibration"]["candidate_role"] = "OPTION_0"
    (idir / "manifest.json").write_text(json.dumps(man))
    (idir / "BASELINE_TARGET.wav").write_bytes(b"b")
    (idir / "CANDIDATE_TARGET.wav").write_bytes(b"c")
    (idir / "BASELINE_CORE.wav").write_bytes(b"cb")
    (idir / "CANDIDATE_CORE.wav").write_bytes(b"cc")
    run = tmp_path
    assert _role_wav(run, "cal-map", 1, "TARGET").name \
        == "BASELINE_TARGET.wav"
    assert _role_wav(run, "cal-map", 0, "TARGET").name \
        == "CANDIDATE_TARGET.wav"
    assert _role_wav(run, "cal-map", 1, "CORE").name \
        == "BASELINE_CORE.wav"
    assert _role_wav(run, "cal-map", 0, "CORE").name \
        == "CANDIDATE_CORE.wav"
    assert _role_wav(run, "cal-map", 2, "TARGET") is None
    assert _role_wav(run, "cal-missing", 0, "TARGET") is None


def test_git_evidence_reports_missing(tmp_path, monkeypatch):
    """git_evidence lists every required-but-uncommitted artifact —
    the maintainer can see exactly what Git is missing."""
    import agent2utau.structure_calibration as sc
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    items = run / "structure_calibration" / "items"
    (items / "cal-a").mkdir(parents=True)
    (items / "cal-b").mkdir(parents=True)
    monkeypatch.setattr(
        sc, "_git_tracked_set",
        lambda d: {"plan.json", "items/cal-a/manifest.json"})
    ev = sc.git_evidence(run)
    assert ev["complete"] is False
    assert "state.json" in ev["missing"]
    assert "pilot_review.json" in ev["missing"]
    assert "qc/verdict.json" in ev["missing"]
    assert "items/cal-a/signal_qc.json" in ev["missing"]
    assert "items/cal-a/BASELINE_TARGET.wav" in ev["missing"]
    assert all(e.startswith("items/cal-b/") for e in ev["missing"]
               if e.startswith("items/cal-b/"))
    assert ev["checked"] == 3 + 2 + 2 * len(sc.GIT_REQUIRED_ITEM_FILES)


# --------------------------------- §10.1.5A-G5C child-level F0 QC (Blocker H)

def _f0_dispatch(table):
    """filename -> fake f0 series dispatcher for _extract_f0."""
    def disp(p):
        name = str(p).replace("\\", "/").rsplit("/", 1)[-1]
        for key, f0 in table.items():
            if key in name:
                return f0
        raise AssertionError(f"no fake f0 for {name}")
    return disp


def test_h1_child_spans_follow_patch_boundary(tmp_path, monkeypatch):
    """H1: asymmetric children — windows come from the declared patch
    boundary, never a 50/50 focus split; ±0.5s context pitch cannot
    contaminate child medians (H2)."""
    import agent2utau.structure_calibration as sc
    idir, man = _fake_rendered_item(tmp_path, region=(2.0, 3.0),
                                    boundary=2.2)   # child0 0.2s / child1 0.8s
    # TARGET clip covers abs [1.5,3.5] (2s): children rel [0.5,0.7]/[0.7,1.5]
    tgt = _fake_f0_series([(0.0, 0.5, 70.0), (0.5, 0.7, 62.0),
                           (0.7, 1.5, 64.0), (1.5, 2.0, 70.0)], dur=2.0)
    # SOURCE focus covers abs [1.4,3.6] (2.2s): children rel [0.6,0.8]/[0.8,1.6]
    src = _fake_f0_series([(0.0, 0.6, 70.0), (0.6, 0.8, 62.0),
                           (0.8, 1.6, 64.0), (1.6, 2.2, 70.0)], dur=2.2)
    monkeypatch.setattr(sc, "_extract_f0", _f0_dispatch({
        "BASELINE_TARGET": tgt, "CANDIDATE_TARGET": tgt,
        "SOURCE_FOCUS": src}))
    qc = sc.child_f0_qc(man, idir)
    c0, c1 = qc["children"]
    assert c0["span_abs"] == [2.0, 2.2]          # boundary, not midpoint
    assert c1["span_abs"] == [2.2, 3.0]
    assert c0["duration"] == pytest.approx(0.2, abs=1e-3)
    # context at 70 surrounds both children — medians must stay clean
    assert c0["candidate"]["midi_median"] == pytest.approx(62.0, abs=0.05)
    assert c1["candidate"]["midi_median"] == pytest.approx(64.0, abs=0.05)
    assert c0["source"]["midi_median"] == pytest.approx(62.0, abs=0.05)
    assert c1["source"]["midi_median"] == pytest.approx(64.0, abs=0.05)


def _note0012_like(tmp_path, monkeypatch):
    """note_0012/0061/0123 direction fixture (H3–H5): source 62→64,
    baseline flat 64, candidate 62→64 — candidate must measure closer
    to source than baseline."""
    import agent2utau.structure_calibration as sc
    idir, man = _fake_rendered_item(tmp_path, region=(2.0, 3.0),
                                    boundary=2.4)
    src = _fake_f0_series([(0.6, 1.0, 62.0), (1.0, 1.6, 64.0)], dur=2.2)
    base = _fake_f0_series([(0.0, 2.0, 64.0)], dur=2.0)
    cand = _fake_f0_series([(0.5, 0.9, 62.0), (0.9, 1.5, 64.0)], dur=2.0)
    monkeypatch.setattr(sc, "_extract_f0", _f0_dispatch({
        "BASELINE_TARGET": base, "CANDIDATE_TARGET": cand,
        "SOURCE_FOCUS": src}))
    return sc.child_f0_qc(man, idir)


def test_h3_candidate_closer_to_source_than_baseline(tmp_path,
                                                     monkeypatch):
    """H3–H5 (note_0012/0061/0123 direction): candidate child errors vs
    source ≈0 while baseline child0 is ~2 semitones off — improvement
    positive; the old focus-window summary could never see this."""
    qc = _note0012_like(tmp_path, monkeypatch)
    assert qc["baseline_child_error_semitones"][0] == pytest.approx(
        2.0, abs=0.05)
    assert qc["baseline_child_error_semitones"][1] == pytest.approx(
        0.0, abs=0.05)
    assert qc["candidate_child_error_semitones"] == pytest.approx(
        [0.0, 0.0], abs=0.05)
    assert qc["baseline_structure_error"] > 1.0
    assert qc["candidate_structure_error"] == pytest.approx(0.0,
                                                          abs=0.05)
    assert qc["candidate_improvement_vs_baseline"] > 1.0
    assert qc["unavailable_child_slots"] == 0
    assert qc["ambiguous_children"] == []


def test_h6_insufficient_voiced_child_is_unavailable(tmp_path,
                                                     monkeypatch):
    """H6: a child with <3 voiced frames is unavailable/neutral — its
    error slots stay None; never a fabricated 0 or default MIDI."""
    import agent2utau.structure_calibration as sc
    idir, man = _fake_rendered_item(tmp_path, region=(2.0, 3.0),
                                    boundary=2.2)
    # source: child0 span (rel [0.6,0.8]) entirely unvoiced; child1 = 64
    src = _fake_f0_series([(0.8, 1.6, 64.0)], dur=2.2)
    both = _fake_f0_series([(0.5, 0.7, 62.0), (0.7, 1.5, 64.0)],
                           dur=2.0)
    monkeypatch.setattr(sc, "_extract_f0", _f0_dispatch({
        "BASELINE_TARGET": both, "CANDIDATE_TARGET": both,
        "SOURCE_FOCUS": src}))
    qc = sc.child_f0_qc(man, idir)
    c0, c1 = qc["children"]
    assert c0["source"]["evidence"] == "unavailable"
    assert c0["source"]["midi_median"] is None
    assert c0["baseline_error_semitones"] is None
    assert c0["candidate_error_semitones"] is None
    assert qc["baseline_child_error_semitones"] == [None, 0.0]
    assert qc["unavailable_child_slots"] >= 1
    # structure error aggregates over AVAILABLE children only
    assert qc["candidate_structure_error"] == pytest.approx(0.0,
                                                          abs=0.05)


def test_h7_octave_ambiguous_child_flagged(tmp_path, monkeypatch):
    """H7: octave-folded child evidence is flagged ambiguous — no
    forced candidate/baseline winner."""
    import agent2utau.structure_calibration as sc
    idir, man = _fake_rendered_item(tmp_path, region=(2.0, 3.0),
                                    boundary=2.4)
    src = _fake_f0_series([(0.6, 1.0, 62.0), (1.0, 1.6, 64.0)], dur=2.2)
    base = _fake_f0_series([(0.0, 2.0, 64.0)], dur=2.0)
    # candidate child1 (rel [0.9,1.5]) folds between 64 and 76
    cand = _fake_f0_series(
        [(0.5, 0.9, 62.0), (0.9, 1.1, 64.0), (1.1, 1.3, 76.0),
         (1.3, 1.5, 64.0)], dur=2.0)
    monkeypatch.setattr(sc, "_extract_f0", _f0_dispatch({
        "BASELINE_TARGET": base, "CANDIDATE_TARGET": cand,
        "SOURCE_FOCUS": src}))
    qc = sc.child_f0_qc(man, idir)
    c1 = qc["children"][1]
    assert c1["candidate"]["evidence"] == "ambiguous"
    assert "candidate_child_1" in qc["ambiguous_children"]


# --------------------------------- §10.1.5A-G5E remote pilot review

def _pilot_store(tmp_path, note_id="note_0061", phrase_key="37.78-44.08"):
    """Minimal m25-cal-2 store with one rendered item + phrase clips —
    enough for build_pilot_review. Run sits under runs/<id> so the
    git_path derivation mirrors the production repo layout."""
    import numpy as np
    import soundfile as sf
    run = tmp_path / "runs" / "diag-x"
    cdir = run / "structure_calibration"
    idir, man = _fake_rendered_item(cdir, name="cal-p1",
                                    region=(20.0, 20.5))
    for nm in ("BASELINE_CORE.wav", "CANDIDATE_CORE.wav",
               "BASELINE_TARGET.wav", "CANDIDATE_TARGET.wav",
               "OPTION_0_LISTEN.wav", "OPTION_1_LISTEN.wav"):
        sf.write(str(idir / nm), np.zeros(800), 8000)
    pdir = cdir / "phrases" / phrase_key
    pdir.mkdir(parents=True)
    for nm in ("SOURCE_PHRASE_original_mix.wav",
               "SOURCE_PHRASE_separated_vocal.wav",
               "SOURCE_PHRASE_original_mix_LISTEN.wav",
               "SOURCE_PHRASE_separated_vocal_LISTEN.wav"):
        sf.write(str(pdir / nm), np.zeros(8000), 8000)
    # G5G-C: plan must mirror the authoritative manifest + signal_qc —
    # enrich the fixture manifest with the fields invariants compare
    man["schema"] = "m25-cal-2"
    man["audio_package_hash"] = "aph-p1"
    man["package_state"] = "valid"
    man["calibration"]["lyric_contract"] = "real_lyric_review"
    man["calibration"]["lyric_mapping_impl"] = "rlv2"
    man["calibration"]["contract_sha256"] = "cs-p1"
    (idir / "manifest.json").write_text(json.dumps(man))
    (idir / "signal_qc.json").write_text(json.dumps(
        {"schema": "m25-cal-2", "auto_flags": [],
         "auto_review_ready": True}))
    plan = {"schema": "m25-cal-2", "items": [{
        "cal_item_id": "cal-p1", "repair_id": "srp-p1",
        "note_id": note_id, "type": "split",
        "phrase": {"start": 37.78, "end": 44.08},
        "phrase_key": phrase_key,
        "audio_package_hash": "aph-p1",
        "package_state": "valid",
        "lyric_contract": "real_lyric_review",
        "contract_sha256": "cs-p1",
        "signal_qc_flags": []}]}
    (cdir / "plan.json").write_text(json.dumps(plan))
    return run


def test_pilot_review_payload_blind_and_bound(tmp_path, monkeypatch):
    """G5E: the remote pilot payload ships blind A/B full-phrase files
    with canonical sha256 + neutral display names — role-mapped aux
    paths never leak baseline/candidate into labels."""
    import agent2utau.structure_calibration as sc
    run = _pilot_store(tmp_path)
    monkeypatch.setattr(sc, "_git_remote_repo",
                        lambda d: {"slug": "o/r", "sha": "abc123",
                                   "remote": "https://github.com/o/r"})
    payload = sc.build_pilot_review(run)
    assert payload["schema"] == "m25-cal-2"
    assert payload["blind_map"] == {"A": "OPTION_0", "B": "OPTION_1"}
    assert payload["reply_map"]["都差不多"] == "equivalent"
    g = next(x for x in payload["groups"]
             if x.get("note_id") == "note_0061")
    assert g["cal_item_id"] == "cal-p1"
    assert g["phrase_duration_s"] == pytest.approx(6.30, abs=0.01)
    f = g["files"]
    # primary review audio = gain-matched LISTEN copies; canonical
    # authority bytes stay referenced for traceability
    assert f["A"]["git_path"].endswith("items/cal-p1/OPTION_0_LISTEN.wav")
    assert f["A"]["canonical"]["git_path"].endswith(
        "items/cal-p1/OPTION_0.wav")
    assert f["A"]["canonical"]["sha256"]
    assert f["A"]["display_name"] == "A.wav"
    assert f["B"]["display_name"] == "B.wav"
    assert f["SOURCE"]["display_name"] == "SOURCE.wav"
    assert f["SOURCE"]["git_path"].endswith(
        "phrases/37.78-44.08/SOURCE_PHRASE_original_mix_LISTEN.wav")
    assert f["SOURCE"]["canonical"]["git_path"].endswith(
        "SOURCE_PHRASE_original_mix.wav")
    for e in f.values():
        assert e["sha256"] and not e.get("missing")
        assert e["raw_url"].startswith(
            "https://raw.githubusercontent.com/o/r/abc123/")
    # aux A/B resolved through the manifest role map, labelled blind —
    # OPTION_0 is baseline here so A_CORE points at BASELINE_CORE.wav
    aux = g["auxiliary"]
    assert aux["A_CORE"]["git_path"].endswith("BASELINE_CORE.wav")
    assert aux["A_CORE"]["display_name"] == "A_CORE.wav"
    assert aux["B_CORE"]["git_path"].endswith("CANDIDATE_CORE.wav")
    assert "baseline" not in aux["A_CORE"]["label"].lower()
    # persisted for Git commit
    assert (run / "structure_calibration"
            / "pilot_review.json").exists()


def test_pilot_review_missing_note_reported(tmp_path):
    """A pilot note without a calibration item is reported, not
    silently dropped — the reviewer sees the hole."""
    import agent2utau.structure_calibration as sc
    run = _pilot_store(tmp_path)
    payload = sc.build_pilot_review(run, note_ids=["note_0061",
                                                   "note_9999"])
    errs = [g for g in payload["groups"] if "error" in g]
    assert len(errs) == 1 and errs[0]["note_id"] == "note_9999"


def test_git_evidence_includes_phrase_source(tmp_path, monkeypatch):
    """SOURCE_PHRASE clips are primary review material — git_evidence
    requires them per declared phrase_key (deduped across items)."""
    import agent2utau.structure_calibration as sc
    run = _pilot_store(tmp_path)
    cdir = run / "structure_calibration"
    plan = json.loads((cdir / "plan.json").read_text(encoding="utf-8"))
    plan["items"].append(dict(plan["items"][0],
                              cal_item_id="cal-p2",
                              note_id="note_0192"))
    (cdir / "plan.json").write_text(json.dumps(plan))
    monkeypatch.setattr(sc, "_git_tracked_set", lambda d: set())
    ev = sc.git_evidence(run)
    ph = [m for m in ev["missing"] if m.startswith("phrases/")]
    # two items share one phrase -> exactly four phrase files (canonical
    # + LISTEN copies), deduped — not eight
    assert sorted(ph) == [
        "phrases/37.78-44.08/SOURCE_PHRASE_original_mix.wav",
        "phrases/37.78-44.08/SOURCE_PHRASE_original_mix_LISTEN.wav",
        "phrases/37.78-44.08/SOURCE_PHRASE_separated_vocal.wav",
        "phrases/37.78-44.08/SOURCE_PHRASE_separated_vocal_LISTEN.wav"]
    assert "pilot_review.json" in ev["missing"]


# ----------------- §10.1.5A-G5E quality hold: real lyrics + loudness

def test_review_lyrics_carriers_and_melisma():
    """Real-lyric overlay: each hanzi only on its syllable's FIRST note;
    touching continuations '+'; notes after a real gap take 'a'."""
    from agent2utau.review.render import review_lyrics
    notes = [{"start": s, "end": e}
             for s, e in ((0.0, 0.4), (0.4, 0.8), (0.9, 1.3),
                          (1.3, 1.7), (1.7, 2.1), (2.4, 2.8))]
    chars = [{"char": "春", "start": 0.1, "end": 0.6},
             {"char": "秋", "start": 0.95, "end": 1.5},
             {"char": "冬", "start": 2.5, "end": 2.9}]
    out = review_lyrics(notes, chars)
    # 春 lands on note0 (contains 0.1); note1 is its melisma '+'
    # 秋 lands on note2 (starts inside the 0.8-0.9 gap -> next note);
    # note3/4 continue '+'; 冬 lands on note5
    assert out == ["春", "+", "秋", "+", "+", "冬"]


def test_review_lyrics_leading_note_fail_closed():
    """G5F: a note before the first carrier has no syllable to
    continue — fail-closed, never an audible placeholder 'a'."""
    from agent2utau.review.render import review_lyrics
    notes = [{"start": s, "end": e}
             for s, e in ((0.0, 0.3), (0.6, 0.9), (0.9, 1.2))]
    chars = [{"char": "年", "start": 0.7, "end": 1.1}]
    # note0 (0-0.3) precedes 年's carrier (note1) -> no syllable to
    # extend -> None
    assert review_lyrics(notes, chars) is None


def test_review_lyrics_never_audible_a():
    """G5F: 'a' can never appear in real-lyric review output — an
    unmapped note after a real gap can't honestly be '+' either
    (probe-verified: OpenUtau rejects a gap-separated '+' phoneme), so
    the whole mapping fails closed instead of guessing."""
    from agent2utau.review.render import review_lyrics
    notes = [{"start": s, "end": e}
             for s, e in ((0.0, 0.4), (0.9, 1.3), (1.7, 2.1))]
    chars = [{"char": "春", "start": 0.1, "end": 0.3},
             {"char": "秋", "start": 1.8, "end": 2.0}]
    # note1 (0.9-1.3) sits between carriers across real gaps -> the
    # only honest outcomes are '+' (illegal here) or a guessed hanzi
    # (forbidden) -> None
    assert review_lyrics(notes, chars) is None


def test_review_lyrics_fail_closed_on_exhausted_notes():
    """Char evidence that outlives the note list returns None — the
    caller must fail-closed, never pad with guesses."""
    from agent2utau.review.render import review_lyrics
    notes = [{"start": 0.0, "end": 0.4}]
    chars = [{"char": "一", "start": 0.1, "end": 0.3},
             {"char": "二", "start": 0.9, "end": 1.1}]
    assert review_lyrics(notes, chars) is None


def test_real_lyric_review_option_ab_identical_outside_target():
    """The real-lyric overlay keeps A/B lyric sequences identical
    outside the target operation: a split parent's char lands on
    child[0] and its later children are '+' only."""
    from agent2utau.review.render import option_notes
    ctx = [{"id": f"note_{i:04d}", "index": i,
            "start": s, "end": e, "tone": 62.0}
           for i, (s, e) in enumerate(
               ((0.0, 0.4), (0.4, 0.8), (0.9, 1.3), (1.3, 1.7),
                (1.7, 2.1)))]
    patch = {"type": "split", "note_ids": ["note_0002"],
             "boundary": 1.1,
             "children": [{"start": 0.9, "end": 1.1, "tone": 62.0},
                          {"start": 1.1, "end": 1.3, "tone": 64.0}]}
    item = {"lyric_contract": "real_lyric_review",
            "phrase": {"start": 0.0, "end": 2.1}, "context": ctx}
    chars = [{"char": "春", "start": 0.05, "end": 0.6},
             {"char": "秋", "start": 0.95, "end": 1.4},
             {"char": "冬", "start": 1.8, "end": 2.05}]
    base = option_notes(item, {"score_patch": {"type": "identity"}},
                        chars)
    cand = option_notes(item, {"score_patch": patch}, chars)
    bl = [n["lyric"] for n in base]
    cl = [n["lyric"] for n in cand]
    # 冬's onset is 100ms inside the last note — rlv3 articulation
    # splits it there: the front keeps '+' and 冬 voices at its
    # source onset instead of the note start (G5I)
    assert bl == ["春", "+", "秋", "+", "+", "冬"]
    # candidate replaces note2 with two children: 秋 on child0, '+' on
    # child1 and on the following context note — outside-target lyrics
    # stay identical to the baseline sequence
    assert cl == ["春", "+", "秋", "+", "+", "+", "冬"]
    # context lyrics identical; the target expands 秋 -> [秋, +]
    assert cl[:2] == bl[:2] and cl[4:] == bl[3:]
    assert cl[2:4] == ["秋", "+"]


def test_review_phrase_chars_evidence_gate():
    """review_phrase_chars fail-closed: no chars -> no_chars; any char
    below MIN_REVIEW_CHAR_PROB -> low_confidence."""
    import agent2utau.structure_calibration as sc
    run = {"chars": [{"char": "a", "start": 1.0, "end": 1.4,
                      "probability": 0.6},
                     {"char": "b", "start": 1.5, "end": 1.9,
                      "probability": 0.1}]}
    ev = sc.review_phrase_chars(run, {"start": 0.5, "end": 2.5})
    assert ev["ok"] is False and ev["reason"] == "low_confidence"
    assert ev["min_probability"] == 0.1
    ev = sc.review_phrase_chars({"chars": []},
                                {"start": 0.0, "end": 1.0})
    assert ev["ok"] is False and ev["reason"] == "no_chars"
    run["chars"][1]["probability"] = 0.9
    ev = sc.review_phrase_chars(run, {"start": 0.5, "end": 2.5})
    assert ev["ok"] and len(ev["chars"]) == 2


def test_listen_copies_pair_shared_gain(tmp_path):
    """G5F listening surface: baseline-side LISTEN is canonical; the
    candidate side is the shared-context splice — bit-identical to A
    outside the fade zone, the candidate's own render inside; ONE
    pair-shared gain on top; canonical wavs untouched."""
    import numpy as np
    import soundfile as sf
    import agent2utau.structure_calibration as sc
    idir = tmp_path / "cal-x"
    idir.mkdir()
    sr = 8000
    t = np.arange(4 * sr) / sr
    a = 0.02 * np.sin(2 * np.pi * 200 * t)      # quiet baseline
    b = 0.04 * np.sin(2 * np.pi * 200 * t)      # 2x louder candidate
    sf.write(str(idir / "OPTION_0.wav"), a, sr, subtype="FLOAT")
    sf.write(str(idir / "OPTION_1.wav"), b, sr, subtype="FLOAT")
    canon0 = (idir / "OPTION_0.wav").read_bytes()
    man = {"calibration": {"baseline_option": "OPTION_0",
                           "candidate_role": "OPTION_1"}}
    out = sc._listen_copies(
        idir, {"OPTION_0": "OPTION_0.wav", "OPTION_1": "OPTION_1.wav"},
        man, [1.5, 2.5])
    assert out["construction"] == "shared_context_splice"
    assert out["shared_gain_db"] > 0
    la, _ = sf.read(str(idir / "OPTION_0_LISTEN.wav"))
    lb, _ = sf.read(str(idir / "OPTION_1_LISTEN.wav"))
    g = 10 ** (out["shared_gain_db"] / 20)
    # A side = canonical baseline * shared gain (quantize-tolerant)
    assert np.allclose(la, a * g, atol=1e-3)
    fz = out["fade_zone_rel"]
    f0, f1 = int(fz[0] * sr), int(fz[1] * sr)
    # outside the fade zone B is bit-identical to A (shared context)
    assert np.allclose(lb[:f0], la[:f0], atol=2e-3)
    assert np.allclose(lb[f1:], la[f1:], atol=2e-3)
    # inside the candidate segment is the candidate's own render —
    # compare energy (edge-lag alignment shifts phase by ~ms, which is
    # fine for listening but breaks sample-exact equality)
    s0 = int(out["splice_edges_rel"][0] * sr)
    s1 = int(out["splice_edges_rel"][1] * sr)
    m = int(0.1 * sr)
    mid = lb[s0 + m:s1 - m]
    ref = b[s0 + m:s1 - m] * g
    mid_rms = float(np.sqrt((mid ** 2).mean()))
    ref_rms = float(np.sqrt((ref ** 2).mean()))
    assert mid_rms == pytest.approx(ref_rms, rel=0.1)
    assert np.abs(mid).max() == pytest.approx(
        np.abs(ref).max(), rel=0.1)
    assert out["listen_peak"]["OPTION_1"] <= 0.98 + 1e-4
    # canonical bytes untouched
    assert (idir / "OPTION_0.wav").read_bytes() == canon0


# --------------------------------- §10.1.5A-G5G close-out regressions

def test_contract_sha_binds_lyric_impl_version(tmp_path):
    """G5G-B: the render-contract identity includes the lyric-mapping
    impl version — a semantic bump produces a different contract sha,
    so artifacts rendered under the old impl can never pass as current."""
    import agent2utau.structure_calibration as sc
    run = {"chars": []}
    rph = "rph-test"
    review_sha = sc.render_contract_sha(run, rph, "real_lyric_review")
    neutral_sha = sc.render_contract_sha(run, rph, "neutral_vowel")
    assert review_sha != neutral_sha
    # simulate the rlv1 semantics era by patching the version table
    import agent2utau.structure_calibration as scmod
    old = scmod.LYRIC_MAPPING_IMPL_VERSION["real_lyric_review"]
    try:
        scmod.LYRIC_MAPPING_IMPL_VERSION["real_lyric_review"] = "rlv1"
        v1_sha = sc.render_contract_sha(run, rph, "real_lyric_review")
    finally:
        scmod.LYRIC_MAPPING_IMPL_VERSION["real_lyric_review"] = old
    assert v1_sha != review_sha      # impl bump changes identity


def test_item_contract_stale_detects_old_impl(tmp_path, monkeypatch):
    """G5G-B regression: an artifact whose manifest records a contract
    sha computed under an older lyric impl is stale — it must not pass
    as current-contract valid."""
    import agent2utau.structure_calibration as sc
    run = {"chars": []}
    man = {"calibration": {"lyric_contract": "real_lyric_review",
                           "contract_sha256": "old-impl-sha"}}
    assert sc.item_contract_stale(man, run, "rph") is True
    man["calibration"]["contract_sha256"] = sc.render_contract_sha(
        run, "rph", "real_lyric_review")
    assert sc.item_contract_stale(man, run, "rph") is False


def test_plan_invariants_catches_lying_plan(tmp_path):
    """G5G-C: a plan entry disagreeing with the authoritative manifest
    or signal_qc is reported — review_ready/pilot/QC must all block."""
    import agent2utau.structure_calibration as sc
    run = _pilot_store(tmp_path)
    cdir = run / "structure_calibration"
    inv = sc.plan_invariants(run)
    assert inv["ok"] is True and inv["violations"] == []
    # corrupt one field in the plan → violation names the field+item
    plan = json.loads((cdir / "plan.json").read_text(encoding="utf-8"))
    plan["items"][0]["signal_qc_flags"] = ["stale_flag:1"]
    plan["items"][0]["lyric_contract"] = "neutral_vowel"
    (cdir / "plan.json").write_text(json.dumps(plan))
    inv = sc.plan_invariants(run)
    assert inv["ok"] is False
    assert any("signal_qc_flags" in v for v in inv["violations"])
    assert any("lyric_contract" in v for v in inv["violations"])
    # a lying plan also blocks pilot payload generation
    with pytest.raises(RuntimeError, match="plan-invariant"):
        sc.build_pilot_review(run)


def test_rebuild_plan_mirrors_manifests(tmp_path):
    """G5G-C: rebuild_plan re-reads every field from the authoritative
    manifest + signal_qc — no stale value survives the rebuild."""
    import agent2utau.structure_calibration as sc
    run = _pilot_store(tmp_path)
    cdir = run / "structure_calibration"
    plan = json.loads((cdir / "plan.json").read_text(encoding="utf-8"))
    plan["items"][0]["signal_qc_flags"] = ["stale_flag:1"]
    plan["items"][0]["audio_package_hash"] = "old-hash"
    (cdir / "plan.json").write_text(json.dumps(plan))
    assert not sc.plan_invariants(run)["ok"]
    doc = sc.rebuild_plan(run)
    it = doc["items"][0]
    assert it["audio_package_hash"] == "aph-p1"
    assert it["signal_qc_flags"] == []
    assert it["lyric_contract"] == "real_lyric_review"
    assert sc.plan_invariants(run)["ok"] is True


def test_pilot_blocked_when_plan_missing_over_store(tmp_path):
    """A non-empty item store with no plan.json is a violation — the
    empty-store case stays vacuous."""
    import agent2utau.structure_calibration as sc
    run = _pilot_store(tmp_path)
    (run / "structure_calibration" / "plan.json").unlink()
    inv = sc.plan_invariants(run)
    assert inv["ok"] is False
    assert any("plan.json missing" in v for v in inv["violations"])


# ------------------------------------------- §10.1.5A-G5H QC authority binding

def test_g5h_verdict_binds_sample_contract_not_plan(tmp_path,
                                                    monkeypatch):
    """H1+H2: plan top-level = neutral nv1 while the samples are
    real-lyric rlv2 — the PASS binds the SHARED SAMPLE contract,
    never the plan default."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch)
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    rec = sc.write_verdict(
        run, "PASS", auditor="t",
        sample_ids=[i["cal_item_id"] for i in items])
    assert rec["contract_sha256"] == sha
    assert rec["contract_sha256"] != "store-default-nv1"
    assert rec["pilot"]["sample_ids"] == [i["cal_item_id"]
                                        for i in items]
    assert rec["pilot"]["audio_package_hashes"] == {
        i["cal_item_id"]: f"aph-{i['cal_item_id']}" for i in items}
    # note_ids resolve to cal_item_ids too
    rec2 = sc.write_verdict(
        run, "PASS", auditor="t",
        sample_ids=[i["note_id"] for i in items])
    assert rec2["pilot"]["sample_ids"] == rec["pilot"]["sample_ids"]


def test_g5h_pass_refused_on_mixed_stale_or_unready(tmp_path,
                                                    monkeypatch):
    """H3+H4+H5: mixed contracts, a stale sample, or an unready sample
    each hard-refuse the PASS."""
    import agent2utau.structure_calibration as sc
    ids = lambda items: [i["cal_item_id"] for i in items]
    # H3 — mixed sample contracts (one item rendered under a
    # different contract sha)
    run, items, _ = _g5h_store(tmp_path, monkeypatch)
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    man_p = run / "structure_calibration" / "items" \
        / "cal-s1" / "manifest.json"
    man = json.loads(man_p.read_text(encoding="utf-8"))
    man["calibration"]["contract_sha256"] = "other-contract"
    man_p.write_text(json.dumps(man), encoding="utf-8")
    # keep the plan mirror consistent so ONLY the mix is the problem
    plan_p = run / "structure_calibration" / "plan.json"
    plan = json.loads(plan_p.read_text(encoding="utf-8"))
    plan["items"][1]["contract_sha256"] = "other-contract"
    plan_p.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(RuntimeError, match="mixed sample"):
        sc.write_verdict(run, "PASS", auditor="t", sample_ids=ids(items))
    # H4 — one sample stale under the current impl
    run, items, _ = _g5h_store(tmp_path, monkeypatch,
                               stale_iids=("cal-s1",))
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    with pytest.raises(RuntimeError, match="stale contract"):
        sc.write_verdict(run, "PASS", auditor="t", sample_ids=ids(items))
    # H5 — one sample auto_review_ready=false
    run, items, _ = _g5h_store(tmp_path, monkeypatch,
                               not_ready_iids=("cal-s0",))
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    with pytest.raises(RuntimeError, match="auto_review_ready"):
        sc.write_verdict(run, "PASS", auditor="t", sample_ids=ids(items))
    # verify_package failure also refuses
    run, items, _ = _g5h_store(tmp_path, monkeypatch,
                               bad_verify_iids=("cal-s0",))
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    with pytest.raises(RuntimeError, match="verify_package"):
        sc.write_verdict(run, "PASS", auditor="t", sample_ids=ids(items))


def _pass_over(run, items):
    import agent2utau.structure_calibration as sc
    return sc.write_verdict(
        run, "PASS", auditor="t",
        sample_ids=[i["cal_item_id"] for i in items])


def test_g5h_verdict_stales_on_any_pilot_change(tmp_path, monkeypatch):
    """H6+H7+H8: after a committed PASS, ANY change to the bound pilot
    identity — roster/payload, one audio_package_hash, or a sample's
    own contract — stales the verdict (review_ready=false)."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch)
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    _pass_over(run, items)
    assert sc.review_ready(run)
    cdir = run / "structure_calibration"
    pr = cdir / "pilot_review.json"
    orig = pr.read_text(encoding="utf-8")
    # H6 — pilot roster changes inside the payload
    pay = json.loads(orig)
    pay["groups"].append({"note_id": "note_9999",
                          "cal_item_id": "cal-new"})
    pr.write_text(json.dumps(pay), encoding="utf-8")
    assert not sc.review_ready(run)
    pr.write_text(orig, encoding="utf-8")
    assert sc.review_ready(run)
    # H7 — one audio_package_hash changes
    man_p = cdir / "items" / "cal-s0" / "manifest.json"
    man = json.loads(man_p.read_text(encoding="utf-8"))
    man["audio_package_hash"] = "aph-tampered"
    man_p.write_text(json.dumps(man), encoding="utf-8")
    assert not sc.review_ready(run)


def test_g5h_old_neutral_verdict_no_authority(tmp_path, monkeypatch):
    """H9: the old c54f07 neutral-vowel PASS over the old 5-sample
    roster cannot authorize the current rlv2 pilot."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch)
    cdir = run / "structure_calibration" / "qc"
    cdir.mkdir(parents=True)
    (cdir / "audit.jsonl").write_text("{}\n", encoding="utf-8")
    (cdir / "verdict.json").write_text(json.dumps({
        "schema": sc.CALIB_SCHEMA, "verdict": "PASS",
        "contract_sha256": "c54f07d6-nv1", "auditor": "devin",
        "git_evidence_at_record": {"complete": True, "checked": 400},
        "sample_ids": ["cal-srp-c491a6b75c7d94cb28fd7a1e",
                       "cal-srp-cb76bf56bb24b5c3d8849bc0",
                       "cal-srp-d2be57c8bd5099d60a05227",
                       "cal-srp-9ff662d834e7cbadd1aa9434",
                       "cal-srp-8f73580bd3c768145f417f0d"]}),
        encoding="utf-8")
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    assert not sc.review_ready(run)


def test_g5h_current_exact_pilot_ready(tmp_path, monkeypatch):
    """H10: exact current sample set + current-contract PASS +
    committed qc files → review_ready=true."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch, n=4)
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    _pass_over(run, items)
    assert sc.review_ready(run)
    st = sc.rebuild_calibration_state(run)
    assert st["review_ready"] is True
    assert st["store_contract_sha256"] == "store-default-nv1"
    assert st["pilot_contract_sha256"] == sha


def test_g5h_dirty_bytes_are_not_committed(tmp_path, monkeypatch):
    """G5H follow-through: a tracked file with UNCOMMITTED changes is
    not committed evidence — a freshly written (dirty) verdict must
    not flip review_ready until its bytes are actually committed."""
    import agent2utau.structure_calibration as sc
    run, items, _ = _g5h_store(tmp_path, monkeypatch)
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    _pass_over(run, items)
    assert sc.review_ready(run)
    # simulate: verdict.json tracked but modified vs HEAD
    monkeypatch.setattr(sc, "_git_dirty_set",
                        lambda d: {"qc/verdict.json"})
    assert not sc.review_ready(run)
    ev = sc.git_evidence(run, item_ids=[items[0]["cal_item_id"]])
    assert ev["uncommitted"] == ["qc/verdict.json"]
    assert not ev["complete"]


# --------------------------------------- §10.1.5A-G5I Lyric Timing Gate

def _art(notes, chars):
    from agent2utau.review.render import review_lyrics_articulated
    return review_lyrics_articulated(notes, chars)


def test_g5i_interior_onset_splits_same_pitch():
    """I1: a char onset inside a note produces a render-only
    same-pitch split — the char voices at its onset, never dragged
    back to note.start."""
    notes = [{"id": "n0", "start": 0.0, "end": 0.5, "tone": 62.0},
             {"id": "n1", "start": 0.5, "end": 1.0, "tone": 64.0}]
    chars = [{"char": "我", "start": 0.02, "end": 0.4},
             {"char": "演", "start": 0.8, "end": 0.95}]
    segs = _art(notes, chars)
    assert [(s["lyric"], round(s["start"], 2), round(s["end"], 2))
            for s in segs] == [
        ("我", 0.0, 0.5), ("+", 0.5, 0.8), ("演", 0.8, 1.0)]
    assert segs[1]["tone"] == segs[2]["tone"] == 64.0   # same pitch
    assert segs[1]["articulation_split"] and \
        segs[2]["articulation_split"]


def test_g5i_two_chars_one_written_note():
    """I2: two chars inside one constant-pitch written note → render
    splits same pitch for articulation; the written score input is
    untouched (the function never mutates `notes`)."""
    notes = [{"id": "n0", "start": 0.0, "end": 1.0, "tone": 62.0}]
    chars = [{"char": "我", "start": 0.02, "end": 0.3},
             {"char": "演", "start": 0.31, "end": 0.7}]
    segs = _art(notes, chars)
    assert [s["lyric"] for s in segs] == ["我", "演"]
    assert [(s["start"], s["end"]) for s in segs] == \
        [(0.0, 0.31), (0.31, 1.0)]
    assert all(s["tone"] == 62.0 for s in segs)   # same written pitch
    assert notes[0]["end"] == 1.0        # input unchanged


def test_g5i_boundary_onset_no_split():
    """I3: a char onset already near a note boundary snaps to it —
    no unnecessary split."""
    notes = [{"id": "n0", "start": 0.0, "end": 0.5, "tone": 62.0},
             {"id": "n1", "start": 0.5, "end": 1.0, "tone": 64.0}]
    chars = [{"char": "我", "start": 0.03, "end": 0.4},
             {"char": "演", "start": 0.55, "end": 0.9}]
    segs = _art(notes, chars)
    assert len(segs) == 2
    assert [s["lyric"] for s in segs] == ["我", "演"]
    assert not any(s["articulation_split"] for s in segs)


def test_g5i_ab_identical_anchors_outside_target():
    """I4: A/B lyric timing anchors outside the target are identical
    — both options derive from the SAME source char evidence."""
    from agent2utau.review.render import option_notes
    ctx = [{"id": f"note_{i:04d}", "index": i, "start": s, "end": e,
            "tone": 62.0}
           for i, (s, e) in enumerate(
               ((0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0)))]
    patch = {"type": "split", "note_ids": ["note_0002"], "boundary": 1.25,
             "children": [{"start": 1.0, "end": 1.25, "tone": 62.0},
                          {"start": 1.25, "end": 1.5, "tone": 64.0}]}
    item = {"lyric_contract": "real_lyric_review",
            "phrase": {"start": 0.0, "end": 2.0}, "context": ctx}
    chars = [{"char": "我", "start": 0.03, "end": 0.4},
             {"char": "演", "start": 1.05, "end": 1.4},
             {"char": "剧", "start": 1.8, "end": 1.95}]
    a = option_notes(item, {"score_patch": {"type": "identity"}}, chars)
    b = option_notes(item, {"score_patch": patch}, chars)
    # outside the 1.0–1.5 target the render segments are identical —
    # same written notes + same source onsets → same splits
    a_out = [(n["lyric"], round(n["start"], 3), round(n["end"], 3))
             for n in a if n["end"] <= 1.0 or n["start"] >= 1.5]
    b_out = [(n["lyric"], round(n["start"], 3), round(n["end"], 3))
             for n in b if n["end"] <= 1.0 or n["start"] >= 1.5]
    assert a_out == b_out
    # 剧's interior onset splits identically in both options
    assert any(abs(n["start"] - 1.8) < 1e-9 and n["lyric"] == "剧"
               for n in a)


def test_g5i_target_split_keeps_source_anchors():
    """I5: when the declared split changes target note structure, the
    lyric timing still binds the same source char onsets."""
    from agent2utau.review.render import option_notes
    ctx = [{"id": "note_0000", "index": 0, "start": 0.0, "end": 1.0,
            "tone": 62.0}]
    patch = {"type": "split", "note_ids": ["note_0000"], "boundary": 0.6,
             "children": [{"start": 0.0, "end": 0.6, "tone": 62.0},
                          {"start": 0.6, "end": 1.0, "tone": 64.0}]}
    item = {"lyric_contract": "real_lyric_review",
            "phrase": {"start": 0.0, "end": 1.0}, "context": ctx}
    chars = [{"char": "我", "start": 0.02, "end": 0.4},
             {"char": "演", "start": 0.7, "end": 0.9}]
    a = option_notes(item, {"score_patch": {"type": "identity"}}, chars)
    b = option_notes(item, {"score_patch": patch}, chars)
    # 演 onsets at 0.7 in BOTH renders — the candidate's extra written
    # boundary doesn't move the lyric anchor
    assert any(n["lyric"] == "演" and abs(n["start"] - 0.7) < 1e-9
               for n in a)
    assert any(n["lyric"] == "演" and abs(n["start"] - 0.7) < 1e-9
               for n in b)


def _timing_man(chars=None, n_options=2):
    import agent2utau.structure_calibration as sc
    chars = chars or [{"char": "我", "start": 0.1, "end": 0.5},
                      {"char": "演", "start": 0.6, "end": 1.0}]
    return {"schema": sc.CALIB_SCHEMA, "review_item_id": "cal-x",
            "phrase": {"start": 0.0, "end": 2.0},
            "source_reference": {
                "separated_vocal": {"path": "src.wav"}},
            "calibration": {"repair_id": "srp-x",
                            "lyric_contract": "real_lyric_review",
                            "lyric_evidence": {"chars": chars}},
            "options": [{"option_id": f"OPTION_{i}",
                         "wav": f"o{i}.wav"}
                        for i in range(n_options)]}


def test_g5i_timing_mismatch_fails_closed(tmp_path, monkeypatch):
    """I6: a rendered option whose aligned char sequence can't be
    reproduced gets a fail-closed lyric_timing flag — never a silent
    pass."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _timing_man()
    idir = tmp_path / "cal-x"
    idir.mkdir()
    (idir / "o0.wav").write_bytes(b"x")
    (idir / "o1.wav").write_bytes(b"x")
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "错", "start": 0.1, "end": 0.5,
             "probability": 0.9}])
    lt = sc._lyric_timing_qc(man, idir)
    assert any("lyric_timing_mismatch" in f for f in lt["flags"])
    assert lt["per_char"] == []              # no table over a lie
    # aligner failure → unmeasurable, also fail-closed
    monkeypatch.setattr(
        al, "force_align",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    lt2 = sc._lyric_timing_qc(man, idir)
    assert any("lyric_timing_unmeasurable" in f
               for f in lt2["flags"])


def test_g5i_timing_delta_table_and_stats(tmp_path, monkeypatch):
    """I9/I10: matching sequences produce the per-char delta table +
    summary stats — the artifacts the acceptance gate consumes."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _timing_man()
    idir = tmp_path / "cal-x"
    idir.mkdir()
    (idir / "o0.wav").write_bytes(b"x")
    (idir / "o1.wav").write_bytes(b"x")
    # score-bound truth: carriers voice at tick 96 (0.1s) / 576 (0.6s);
    # the '+' row must be skipped by the carrier filter
    ustx = ("voice_parts:\n  - notes:\n"
            "    - position: 0\n      duration: 90\n      lyric: '+'\n"
            "    - position: 96\n      duration: 100\n      lyric: '我'\n"
            "    - position: 576\n      duration: 200\n"
            "      lyric: '演'\n")
    (idir / "OPTION_0.ustx").write_text(ustx, encoding="utf-8")
    (idir / "OPTION_1.ustx").write_text(ustx, encoding="utf-8")
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.15, "end": 0.5,
             "probability": 0.9},
            {"char": "演", "start": 0.68, "end": 1.0,
             "probability": 0.8}])
    lt = sc._lyric_timing_qc(man, idir)
    assert lt["flags"] == []
    assert len(lt["per_char"]) == 2
    row = lt["per_char"][1]
    assert row["OPTION_0_onset_delta_ms"] == 80.0
    assert row["OPTION_0_offset_delta_ms"] == 0.0
    # score-bound columns: score_onset=0.6, src=0.6 → construction 0;
    # measured 0.68 vs score 0.6 → +80ms is the aligner's own bias
    assert row["OPTION_0_score_onset"] == 0.6
    assert row["OPTION_0_score_delta_ms"] == 0.0
    assert row["OPTION_0_aligner_offset_ms"] == 80.0
    st = lt["stats"]["OPTION_0"]
    assert st["median_abs_onset_delta_ms"] == 65.0
    assert st["max_abs_onset_delta_ms"] == 80.0
    assert st["n_chars_over_200ms"] == 0
    assert st["median_aligner_offset_ms"] == 65.0
    assert st["min_intelligibility_probability"] == 0.8
    assert lt["aligner"] == "whisper-attention-dtw"


def test_g5i_timing_score_mismatch_fails_closed(tmp_path, monkeypatch):
    """I11: a rendered ustx whose carrier sequence doesn't match the
    bound char evidence is fail-closed — the score-onset column can
    never be silently derived from a different score."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _timing_man()
    idir = tmp_path / "cal-x"
    idir.mkdir()
    (idir / "o0.wav").write_bytes(b"x")
    (idir / "o1.wav").write_bytes(b"x")
    bad = ("voice_parts:\n  - notes:\n"
           "    - position: 96\n      duration: 100\n      lyric: '我'\n"
           "    - position: 576\n      duration: 200\n      lyric: '别'\n")
    good = ("voice_parts:\n  - notes:\n"
            "    - position: 96\n      duration: 100\n      lyric: '我'\n"
            "    - position: 576\n      duration: 200\n"
            "      lyric: '演'\n")
    (idir / "OPTION_0.ustx").write_text(bad, encoding="utf-8")
    (idir / "OPTION_1.ustx").write_text(good, encoding="utf-8")
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.15, "end": 0.5,
             "probability": 0.9},
            {"char": "演", "start": 0.85, "end": 1.0,
             "probability": 0.8}])
    lt = sc._lyric_timing_qc(man, idir)
    assert any("lyric_timing_score_mismatch:OPTION_0" in f
               for f in lt["flags"])
    assert lt["per_char"] == []


def test_g5i_impl_bump_stales_old_packages():
    """I8: the lyric-mapping impl is part of the render contract —
    an rlv2 manifest is stale under rlv3 (verdict/package/authority
    all go stale with it)."""
    import agent2utau.structure_calibration as sc
    rlv2_sha = sc._sha({"schema": sc.CALIB_SCHEMA,
                        "lyric_contract": "real_lyric_review",
                        "lyric_mapping_impl": "rlv2",
                        "render_profile_hash": "rph"})
    man = {"schema": sc.CALIB_SCHEMA,
           "calibration": {"lyric_contract": "real_lyric_review",
                           "lyric_mapping_impl": "rlv2",
                           "contract_sha256": rlv2_sha}}
    # recorded contract was valid under rlv2 but stale under rlv3
    assert sc.item_contract_stale(man, {}, "rph") is True
    cur = sc.render_contract_sha({}, "rph", "real_lyric_review")
    assert rlv2_sha != cur


# --------------------- §10.1.5A-G5J acoustic closed-loop (J) ----------------

def _loop_item(notes=None):
    """Minimal item for _closed_loop_anchors/_anchor_bounds — two
    identical options, contiguous carrier notes."""
    notes = notes or [{"id": "note_0001", "index": 1, "start": 0.0,
                       "end": 0.5, "dur": 0.5, "tone": 60.0},
                      {"id": "note_0002", "index": 2, "start": 0.5,
                       "end": 1.0, "dur": 0.5, "tone": 62.0}]
    return {"phrase": {"start": 0.0, "end": 2.0},
            "context": notes,
            "options": [{"option_id": f"OPTION_{i}",
                         "score_patch": {"type": "identity"}}
                        for i in range(2)]}


def _fake_render_factory():
    """render_item stub — writes option wavs + ustx carriers the
    loop re-aligns (carrier positions = commanded anchors, like a
    real render's lyric notes)."""
    def fake(cfg, idir, it, chars, timeout_min=10, anchors=None):
        from pathlib import Path
        Path(idir).mkdir(parents=True, exist_ok=True)
        ph0 = it["phrase"]["start"]
        pos = anchors or [c["start"] for c in chars]
        for o in it["options"]:
            oid = o["option_id"]
            (Path(idir) / f"{oid}.wav").write_bytes(b"x")
            notes = "\n".join(
                f"    - lyric: {c['char']}\n"
                f"      position: {int(round((p - ph0) * 960))}"
                for c, p in zip(chars, pos))
            (Path(idir) / f"{oid}.ustx").write_text(
                "voice_parts:\n  - notes:\n" + notes + "\n",
                encoding="utf-8")
        return {"ok": True, "anchors": anchors}
    return fake


def _fa_seq(chars, shifts):
    """force_align stub — per-call onset shift schedule (2 calls per
    iteration: OPTION_0 then OPTION_1)."""
    calls = {"n": 0}

    def fa(wav, text, t0, t1, model=None):
        calls["n"] += 1
        s = shifts[min(calls["n"] - 1, len(shifts) - 1)]
        return [{"char": c["char"], "start": c["start"] + s,
                 "end": c["end"] + s, "probability": 0.9}
                for c in chars]
    fa.calls = calls
    return fa


def _sro(chars, ph0=0.0):
    """_source_ref_onsets stub — whisper positions as 'onset_peak'
    refs (phrase-relative)."""
    def sro(cs, wav, p0):
        return ([c["start"] - p0 for c in cs],
                ["onset_peak"] * len(cs))
    return sro


def _ro_seq(chars, shifts, ph0=0.0):
    """_render_onsets stub — per-call onset schedule, peaks at
    ref+shift (2 calls per iteration: OPTION_0 then OPTION_1)."""
    calls = {"n": 0}

    def ro(wav, centers):
        calls["n"] += 1
        s = shifts[min(calls["n"] - 1, len(shifts) - 1)]
        return [c + s for c in centers]
    ro.calls = calls
    return ro


def _ro_fixed(peaks):
    """_render_onsets stub — fixed per-char peak list every call."""
    def ro(wav, centers):
        return list(peaks)
    return ro


def test_j1_phrase_window_covers_first_last_char():
    """J1: a source char starting before the LRC phrase boundary must
    not be truncated — the review window expands (clamped by the
    neighbouring note gap) while char evidence stays bound to the
    ORIGINAL lrc window."""
    import agent2utau.structure_calibration as sc
    run = _fake_run_dict()
    run["lrc_lines"] = [{"start": 9.5, "end": 14.5}]
    run["chars"] = [{"char": "前", "start": 9.42, "end": 9.7,
                     "probability": 0.9},
                    {"char": "字", "start": 10.0, "end": 10.4,
                     "probability": 0.9},
                    {"char": "尾", "start": 14.3, "end": 14.44,
                     "probability": 0.9}]
    items = sc.plan_calibration(run, lyric_contract="real_lyric_review")
    it = items[0]
    assert it["phrase"]["boundary_source"] == "lrc+lyric_pad"
    # first char 9.42 - lead pad 0.15 → 9.27 (< lrc 9.5)
    assert it["phrase"]["start"] == 9.27
    # tail 14.44 + 0.15 = 14.59, clamped by next note start — none →
    # min(duration 20, 14.59) but lrc end 14.5 < tail → expanded too
    assert it["phrase"]["end"] == 14.59
    # evidence selection stays on the ORIGINAL lrc window
    assert it["evidence_window"]["start"] == 9.5
    assert it["evidence_window"]["end"] == 14.5


def test_j2_acoustic_miss_fails_despite_clean_score(tmp_path,
                                                    monkeypatch):
    """J2: USTX score onset matches the source (score_delta≈0) but the
    measured acoustic onset is -300ms — the acoustic gate fires;
    construction integrity can never mask a measured timing miss."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _timing_man()
    idir = tmp_path / "cal-x"
    idir.mkdir()
    (idir / "o0.wav").write_bytes(b"x")
    (idir / "o1.wav").write_bytes(b"x")
    ustx = ("voice_parts:\n  - notes:\n"
            "    - position: 96\n      duration: 100\n      lyric: '我'\n"
            "    - position: 576\n      duration: 200\n"
            "      lyric: '演'\n")
    (idir / "OPTION_0.ustx").write_text(ustx, encoding="utf-8")
    (idir / "OPTION_1.ustx").write_text(ustx, encoding="utf-8")
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.0, "end": 0.3,
             "probability": 0.9},     # src 0.1 → measured -100ms
            {"char": "演", "start": 0.3, "end": 0.6,
             "probability": 0.9}])    # src 0.6 → measured -300ms
    chars = man["calibration"]["lyric_evidence"]["chars"]
    monkeypatch.setattr(sc, "_source_ref_onsets", _sro(chars))
    # rlv5 acoustic instrument: render peaks -100/-300ms vs refs —
    # the REAL acoustic gate (whisper deltas above stay diagnostic)
    monkeypatch.setattr(sc, "_render_onsets", _ro_fixed([0.0, 0.3]))
    lt = sc._lyric_timing_qc(man, idir)
    row = lt["per_char"][1]
    assert row["OPTION_0_score_delta_ms"] == 0.0   # score is clean…
    assert row["OPTION_0_onset_delta_ms"] == -300.0
    assert row["OPTION_0_acoustic_delta_ms"] == -300.0
    assert any(f.startswith("lyric_timing_acoustic_delta:OPTION_0")
               for f in lt["flags"])               # …and still fails


def test_j3_low_confidence_char_blocks_pass(tmp_path, monkeypatch):
    """J3: a rendered char aligned below MIN_TIMING_CHAR_PROB is
    untrusted timing evidence — flag stands, no PASS."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _timing_man()
    idir = tmp_path / "cal-x"
    idir.mkdir()
    (idir / "o0.wav").write_bytes(b"x")
    (idir / "o1.wav").write_bytes(b"x")
    ustx = ("voice_parts:\n  - notes:\n"
            "    - position: 96\n      duration: 100\n      lyric: '我'\n"
            "    - position: 576\n      duration: 200\n"
            "      lyric: '演'\n")
    (idir / "OPTION_0.ustx").write_text(ustx, encoding="utf-8")
    (idir / "OPTION_1.ustx").write_text(ustx, encoding="utf-8")
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.1, "end": 0.5,
             "probability": 0.9},
            {"char": "演", "start": 0.6, "end": 1.0,
             "probability": 0.05}])   # untrusted timing
    lt = sc._lyric_timing_qc(man, idir)
    # §G5K: ASR confidence flags lyric INTELLIGIBILITY (diction
    # clarity) — a separate concept from acoustic timing truth
    assert any("lyric_intelligibility_low:OPTION_0:演" in f
               for f in lt["flags"])
    assert lt["stats"]["OPTION_0"][
        "min_intelligibility_probability"] == 0.05


def test_j4_anchor_moves_opposite_error_sign(tmp_path, monkeypatch):
    """J4: measured late (+200ms) → anchors move EARLIER by k·err,
    one damped step per iteration."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    import agent2utau.review.render as rr
    chars = [{"char": "甲", "start": 0.2, "end": 0.45},
             {"char": "乙", "start": 0.6, "end": 0.95}]
    it = _loop_item()
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets", _sro(chars))
    # rlv5: the measured onset tracks the COMMANDED anchor plus the
    # scheduled instrument offset (how a real render behaves — the
    # onset follows where the note was told to start)
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_seq(chars, [0.3, 0.3, 0.1, 0.1, 0.0, 0.0]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    assert loop["converged"] is True
    a0 = loop["iterations"][0]["anchors"]
    a1 = loop["iterations"][1]["anchors"]
    # err +0.3 (rendered late) → anchors move EARLIER — opposite the
    # error sign; the 0.15/iter clamp caps 甲 at a0-0.15=0.05 and
    # 乙 floors at its carrier start 0.5 — neither can onset before
    # the note it must voice inside
    assert a1[0] == pytest.approx(0.05, abs=1e-3)
    assert a1[0] < a0[0] and a1[1] < a0[1]
    assert a1[1] == pytest.approx(0.5, abs=1e-3)
    assert loop["iterations"][0]["max_abs_err_ms"] == 300.0


def test_j5_iterations_converge_score_untouched(tmp_path, monkeypatch):
    """J5: multi-iteration convergence never touches Candidate 0 —
    the written score (context notes) is byte-identical after the
    loop; only render-only anchors moved."""
    import copy
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    import agent2utau.review.render as rr
    chars = [{"char": "甲", "start": 0.2, "end": 0.45},
             {"char": "乙", "start": 0.6, "end": 0.95}]
    it = _loop_item()
    ctx0 = copy.deepcopy(it["context"])
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets", _sro(chars))
    monkeypatch.setattr(
        sc, "_render_onsets",
        _ro_seq(chars, [0.25, 0.25, 0.1, 0.1, 0.0, 0.0]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    assert loop["converged"] is True
    assert len(loop["iterations"]) >= 2   # re-render really happened
    assert it["context"] == ctx0          # written score untouched
    assert all(sg.get("index") == n.get("index")
             for sg, n in zip(it["context"], ctx0))


def test_j6_anchor_crossing_fails_closed(tmp_path, monkeypatch):
    """J6: an update that would push an anchor past the next char (or
    out of its carrier span) stops the loop — never a reordered
    articulation."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    import agent2utau.review.render as rr
    notes = [{"id": "note_0001", "index": 1, "start": 0.0,
              "end": 1.0, "dur": 1.0, "tone": 60.0}]
    chars = [{"char": "甲", "start": 0.90, "end": 0.93},
             {"char": "乙", "start": 0.95, "end": 0.99}]
    it = _loop_item(notes)
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets", _sro(chars))
    # 甲 measured 500ms EARLY forever → anchor wants to move later
    # than 乙's — impossible inside [0, 0.97] with MIN_SEG room.
    # §G5K: both refs (0.90/0.95) sit beyond the usable carrier bound
    # (0.88) → routed B2 and HELD — the held positions collide at
    # bind time, so the item fails closed even earlier (unbindable).
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_fixed([0.40, 0.95]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    assert loop["converged"] is False
    assert loop["reason"] in ("anchors_crossed", "anchors_clamped",
                              "bound_limited", "unbindable_chars")


def test_j7_outside_target_anchors_identical():
    """J7: chars binding outside the target region get identical
    anchors/bounds in baseline and candidate — the shared-range
    intersection is a no-op outside the patched span."""
    import agent2utau.structure_calibration as sc
    from agent2utau.review.build import apply_patch
    from agent2utau.review.render import _char_anchor_binding
    notes = [{"id": "note_0001", "index": 1, "start": 0.0,
              "end": 0.5, "dur": 0.5, "tone": 60.0},
             {"id": "note_0002", "index": 2, "start": 0.5,
              "end": 1.0, "dur": 0.5, "tone": 62.0},
             {"id": "note_0003", "index": 3, "start": 1.0,
              "end": 1.4, "dur": 0.4, "tone": 64.0}]
    chars = [{"char": "外", "start": 0.2, "end": 0.4},   # before target
             {"char": "侧", "start": 1.1, "end": 1.3}]   # after target
    it = _loop_item(notes)
    it["options"][1]["score_patch"] = {
        "type": "split", "note_ids": ["note_0002"], "boundary": 0.7,
        "children": [{"start": 0.5, "end": 0.7, "tone": 62.0},
                     {"start": 0.7, "end": 1.0, "tone": 65.0}]}
    b0 = _char_anchor_binding(
        apply_patch(notes, {"type": "identity"}), chars)
    b1 = _char_anchor_binding(
        apply_patch(notes, it["options"][1]["score_patch"]), chars)
    assert [x[0] for x in b0] == [x[0] for x in b1]   # same positions
    lo, hi = sc._anchor_bounds(it, chars)
    assert lo == [0.0, 1.0]
    assert hi == [pytest.approx(0.5 - 0.03), pytest.approx(1.4 - 0.03)]


def test_j8_rlv3_artifacts_stale_under_rlv7():
    """J8: the rlv3→rlv7 impl bump stales every previous package/
    payload/verdict — old-contract evidence can't pass the new
    acoustic-timing authority."""
    import agent2utau.structure_calibration as sc
    rlv3_sha = sc._sha({"schema": sc.CALIB_SCHEMA,
                        "lyric_contract": "real_lyric_review",
                        "lyric_mapping_impl": "rlv3",
                        "render_profile_hash": "rph"})
    man = {"schema": sc.CALIB_SCHEMA,
           "calibration": {"lyric_contract": "real_lyric_review",
                           "lyric_mapping_impl": "rlv3",
                           "contract_sha256": rlv3_sha}}
    assert sc.item_contract_stale(man, {}, "rph") is True
    assert sc.LYRIC_MAPPING_IMPL_VERSION["real_lyric_review"] == "rlv11"


def test_j9_state_read_does_not_dirty(tmp_path, monkeypatch):
    """J9: a read-path rebuild (calib-web GET) must not write
    state.json — a page load can never dirty Git-authoritative
    bytes."""
    import agent2utau.structure_calibration as sc
    import agent2utau.calib_web as cw
    run = _mk_run(tmp_path, [])
    cdir = run / "structure_calibration"
    cdir.mkdir(exist_ok=True)
    (cdir / "plan.json").write_text(
        json.dumps({"schema": sc.CALIB_SCHEMA, "items": []}))
    state_p = cdir / "state.json"
    sentinel = json.dumps({"schema": sc.CALIB_SCHEMA,
                           "sentinel": True})
    state_p.write_text(sentinel, encoding="utf-8")
    sc.rebuild_calibration_state(run, write=False)
    assert state_p.read_text() == sentinel            # untouched
    # the web read path really passes write=False
    calls = []
    monkeypatch.setattr(cw, "rebuild_calibration_state",
                        lambda d, write=True: calls.append(write) or {})
    cw._items_payload(run)
    assert calls == [False]
    sc.rebuild_calibration_state(run, write=True)
    assert json.loads(state_p.read_text())["schema"] == sc.CALIB_SCHEMA


def test_j10_no_acoustic_pass_no_review_ready(tmp_path, monkeypatch):
    """J10: a package whose signal_qc carries a lyric-timing flag is
    not auto_review_ready → pilot authority fails → a PASS verdict is
    refused; acoustic PASS + package/QC PASS are jointly required."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch)
    iid = items[0]["cal_item_id"]
    qcp = run / "structure_calibration" / "items" / iid \
        / "signal_qc.json"
    qcp.write_text(json.dumps({
        "auto_flags": ["lyric_timing_acoustic_delta:OPTION_0:-210ms"],
        "auto_review_ready": False}))
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _g5h_tracked(items))
    with pytest.raises(RuntimeError):
        sc.write_verdict(run, "PASS", auditor="t",
                         sample_ids=[i["cal_item_id"] for i in items])
    assert not sc.review_ready(run)


# ------------- §10.1.5A-G5K hard-case timing semantics (K) -------------

def _sro_vals(refs, kinds):
    """_source_ref_onsets stub — explicit refs + kinds lists."""
    def sro(cs, wav, p0):
        return (list(refs), list(kinds))
    return sro


def test_k1_class_a_converges_inside_carrier(tmp_path, monkeypatch):
    """K1: reliable landmark + correction inside the carrier →
    class_A; the loop may converge and the route table says so."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    chars = [{"char": "甲", "start": 0.2, "end": 0.4},
             {"char": "乙", "start": 0.6, "end": 0.8}]
    it = _loop_item()
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets", _sro(chars))
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_fixed([0.23, 0.63]))   # +30ms, inside tol
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    assert loop["converged"] is True
    assert [r["route"] for r in loop["char_routes"]] == [
        sc.ROUTE_CLASS_A, sc.ROUTE_CLASS_A]
    assert loop["hard_cases"] == []
    assert all(r["bound_conflict"] is False
               for r in loop["char_routes"])


def test_k2_no_landmark_routes_b1_and_holds(tmp_path, monkeypatch):
    """K2: no stable source landmark → B1_unmeasurable — timing
    evidence unavailable (not 'wrong'); its anchor is HELD, never
    driven by noise, and doesn't block class-A convergence."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    chars = [{"char": "甲", "start": 0.2, "end": 0.4},
             {"char": "乙", "start": 0.6, "end": 0.8}]
    it = _loop_item()
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets",
                        _sro_vals([0.2, 0.6],
                                  ["whisper_fallback", "onset_peak"]))
    # char0 measured 700ms LATE (would push its anchor if it could);
    # char1 converges after damped steps — shifts are per-CALL (two
    # calls per iteration, both options must agree)
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_seq(chars, [0.2, 0.2, 0.0, 0.0, 0.0, 0.0]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    rts = loop["char_routes"]
    assert rts[0]["route"] == sc.ROUTE_B1
    assert rts[0]["unmeasurable_reason"] == "no_source_landmark"
    assert rts[1]["route"] == sc.ROUTE_CLASS_A
    assert loop["hard_cases"] == [0]
    # held: char0's anchor identical across EVERY iteration
    a0 = loop["iterations"][0]["anchors"][0]
    assert all(i_["anchors"][0] == a0 for i_ in loop["iterations"])
    # class-A converged; B1 is reported by route, not faked
    assert loop["converged"] is True


def test_k3_source_onset_below_carrier_bound(tmp_path, monkeypatch):
    """K3: source onset earlier than the legal carrier lower bound →
    B2_carrier_conflict; the overlay can never rewrite written timing
    to reach it — the anchor holds AT the bound."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    notes = [{"id": "note_0001", "index": 1, "start": 0.5, "end": 1.0,
              "dur": 0.5, "tone": 60.0}]
    chars = [{"char": "甲", "start": 0.42, "end": 0.48}]
    it = _loop_item(notes)
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    # ref 60ms below carrier start → anticipation-scale conflict
    monkeypatch.setattr(sc, "_source_ref_onsets",
                        _sro_vals([0.44], ["onset_peak"]))
    monkeypatch.setattr(sc, "_render_onsets", _ro_fixed([0.5]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    r = loop["char_routes"][0]
    assert r["route"] == sc.ROUTE_B2
    assert r["bound_conflict"] is True
    assert r["unmeasurable_reason"] == "source_ref_below_carrier_lo"
    assert r["route_detail"] == "preutterance_candidate"
    assert loop["anchors"][0] == pytest.approx(0.5)   # held at lo
    assert loop["converged"] is False
    assert loop["reason"] == "hard_cases_only"


def test_k4_source_onset_above_carrier_bound(tmp_path, monkeypatch):
    """K4: source onset later than the usable carrier bound → B2
    above; a large gap routes to written-timing suspicion, not
    anticipation — and the anchor can never reach it."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    notes = [{"id": "note_0001", "index": 1, "start": 0.0, "end": 0.5,
              "dur": 0.5, "tone": 60.0}]
    chars = [{"char": "甲", "start": 0.45, "end": 0.49}]
    it = _loop_item(notes)
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    # usable bound hi_move = 0.5-0.12 = 0.38; ref at 0.55 → gap 0.17
    monkeypatch.setattr(sc, "_source_ref_onsets",
                        _sro_vals([0.55], ["onset_peak"]))
    monkeypatch.setattr(sc, "_render_onsets", _ro_fixed([0.38]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    r = loop["char_routes"][0]
    assert r["route"] == sc.ROUTE_B2
    assert r["unmeasurable_reason"] == "source_ref_above_carrier_hi"
    assert r["route_detail"] == "written_timing_suspect"
    assert loop["anchors"][0] == pytest.approx(0.38, abs=1e-3)
    assert loop["converged"] is False


def test_k5_relaxing_params_cannot_convert_b2(tmp_path, monkeypatch):
    """K5: cranking LOOP_K / LOOP_CLAMP_S can never turn a carrier
    conflict into a PASS — a B2 char never enters the update path."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    notes = [{"id": "note_0001", "index": 1, "start": 0.0, "end": 0.5,
              "dur": 0.5, "tone": 60.0}]
    chars = [{"char": "甲", "start": 0.45, "end": 0.49}]
    it = _loop_item(notes)
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "LOOP_K", 50.0)
    monkeypatch.setattr(sc, "LOOP_CLAMP_S", 50.0)
    monkeypatch.setattr(sc, "_source_ref_onsets",
                        _sro_vals([0.55], ["onset_peak"]))
    monkeypatch.setattr(sc, "_render_onsets", _ro_fixed([0.38]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    assert loop["char_routes"][0]["route"] == sc.ROUTE_B2
    assert loop["converged"] is False
    assert all(i_["anchors"][0] == pytest.approx(0.38, abs=1e-3)
               for i_ in loop["iterations"])


def test_k6_overlay_never_touches_candidate0_score(tmp_path,
                                                   monkeypatch):
    """K6: anchors are render-only — the context notes (Candidate 0's
    written score) are byte-identical before and after the loop."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    import copy
    chars = [{"char": "甲", "start": 0.2, "end": 0.4},
             {"char": "乙", "start": 0.6, "end": 0.8}]
    it = _loop_item()
    before = copy.deepcopy(it["context"])
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets", _sro(chars))
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_seq(chars, [0.3, 0.0, 0.0, 0.0]))
    sc._closed_loop_anchors({}, tmp_path / "i", it, chars, src_wav="x")
    assert it["context"] == before
    assert all("anchor" not in n for n in it["context"])



def _qc_route_man(route0, route1=None, ref_onsets=None):
    """_timing_man + injected rlv7 closed_loop carrying char_routes."""
    import agent2utau.structure_calibration as sc
    man = _timing_man()
    r1 = route1 or {"char": "演", "route": sc.ROUTE_CLASS_A,
                    "bound_conflict": False,
                    "unmeasurable_reason": None,
                    "route_detail": None,
                    "carrier_lo": 0.5, "carrier_hi": 0.97,
                    "desired_anchor": 0.6, "final_anchor": 0.6,
                    "measurement_stability": "stable"}
    cl = {"converged": False, "reason": "hard_cases_only",
          "char_routes": [route0, r1]}
    if ref_onsets:
        cl["ref_onsets"] = ref_onsets
        cl["ref_kinds"] = ["onset_peak"] * len(ref_onsets)
    man["calibration"]["lyric_evidence"]["articulation"] = {
        "impl": "rlv10", "closed_loop": cl}
    return man


def _qc_idir(idir):
    """wavs + matching-carrier ustx pair for _lyric_timing_qc."""
    (idir / "o0.wav").write_bytes(b"x")
    (idir / "o1.wav").write_bytes(b"x")
    (idir / "src.wav").write_bytes(b"x")
    ustx = ("voice_parts:\n  - notes:\n"
            "    - position: 96\n      duration: 100\n      lyric: '我'\n"
            "    - position: 576\n      duration: 200\n"
            "      lyric: '演'\n")
    (idir / "OPTION_0.ustx").write_text(ustx, encoding="utf-8")
    (idir / "OPTION_1.ustx").write_text(ustx, encoding="utf-8")


def test_k7_b2_routes_to_written_timing_diagnosis(tmp_path,
                                                  monkeypatch):
    """K7: a B2 char surfaces in QC as carrier conflict + route
    detail — routed to written-timing adjudication, never masked by
    the review overlay."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _qc_route_man(
        {"char": "我", "route": sc.ROUTE_B2,
         "bound_conflict": True,
         "unmeasurable_reason": "source_ref_below_carrier_lo",
         "route_detail": "written_timing_suspect",
         "carrier_lo": 0.5, "carrier_hi": 0.88,
         "desired_anchor": 0.3, "final_anchor": 0.5,
         "measurement_stability": "held"})
    idir = tmp_path / "cal-x"
    idir.mkdir()
    _qc_idir(idir)
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.1, "end": 0.5,
             "probability": 0.9},
            {"char": "演", "start": 0.6, "end": 1.0,
             "probability": 0.9}])
    lt = sc._lyric_timing_qc(man, idir)
    assert any("lyric_timing_carrier_conflict:我" in f
               for f in lt["flags"])
    assert any("lyric_timing_not_converged:hard_cases_only" in f
               for f in lt["flags"])
    row0 = lt["per_char"][0]
    assert row0["route"] == sc.ROUTE_B2
    assert row0["bound_conflict"] is True
    assert row0["route_detail"] == "written_timing_suspect"
    assert row0["final_anchor"] == 0.5
    assert lt["per_char"][1]["route"] == sc.ROUTE_CLASS_A


def test_k8_low_whisper_flags_intelligibility_not_timing(
        tmp_path, monkeypatch):
    """K8: low ASR probability on the render flags lyric
    intelligibility (diction clarity) — it can never masquerade as
    acoustic-timing truth."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _timing_man()
    idir = tmp_path / "cal-x"
    idir.mkdir()
    _qc_idir(idir)
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.1, "end": 0.5,
             "probability": 0.9},
            {"char": "演", "start": 0.6, "end": 1.0,
             "probability": 0.05}])
    lt = sc._lyric_timing_qc(man, idir)
    assert any(f.startswith("lyric_intelligibility_low:OPTION_0")
               for f in lt["flags"])
    assert not any("low_confidence" in f for f in lt["flags"])
    # the same char can never produce an acoustic-TIMING flag from
    # ASR confidence alone
    assert not any("acoustic_delta" in f and "演" in f
                   for f in lt["flags"])
    st = lt["stats"]["OPTION_0"]
    assert st["min_intelligibility_probability"] == 0.05
    assert "min_alignment_probability" not in st


def test_k9_unmeasurable_landmark_is_not_unintelligible(
        tmp_path, monkeypatch):
    """K9: an unmeasurable acoustic landmark (B1) means timing
    evidence unavailable — with clean ASR confidence NO
    intelligibility flag fires; the two concepts stay separate."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _qc_route_man(
        {"char": "我", "route": sc.ROUTE_B1,
         "bound_conflict": False,
         "unmeasurable_reason": "no_source_landmark",
         "route_detail": None,
         "carrier_lo": 0.0, "carrier_hi": 0.38,
         "desired_anchor": 0.1, "final_anchor": 0.1,
         "measurement_stability": "unmeasurable_source"})
    idir = tmp_path / "cal-x"
    idir.mkdir()
    _qc_idir(idir)
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.1, "end": 0.5,
             "probability": 0.95},
            {"char": "演", "start": 0.6, "end": 1.0,
             "probability": 0.9}])
    lt = sc._lyric_timing_qc(man, idir)
    assert any("lyric_timing_evidence_unmeasurable:我" in f
               for f in lt["flags"])
    assert not any(f.startswith("lyric_intelligibility_low")
                   for f in lt["flags"])
    assert lt["per_char"][0]["route"] == sc.ROUTE_B1
    assert lt["per_char"][0]["measurement_stability"] == \
        "unmeasurable_source"


def test_k10_sample_replacement_rebinds_authority(tmp_path,
                                                 monkeypatch):
    """K10: replacing a B1/B2 sample is legal — pilot authority
    re-derives from the NEW exact set; a verdict bound to the old
    roster can never cover the new one."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch, n=3)
    a = sc.pilot_authority(
        run, [items[0]["cal_item_id"], items[1]["cal_item_id"]])
    assert a["ok"]
    b = sc.pilot_authority(
        run, [items[0]["cal_item_id"], items[2]["cal_item_id"]])
    assert b["ok"]
    # replacement keeps ONE shared contract — an honest sample swap,
    # but the bound set is roster-exact and therefore different
    assert b["contract_sha256"] == a["contract_sha256"]
    assert b["sample_ids"] != a["sample_ids"]
    assert items[2]["cal_item_id"] not in a["sample_ids"]
    assert items[1]["cal_item_id"] not in b["sample_ids"]


# ------------- §10.1.5A-G5L directional + post-loop (L) -------------

def _ro_per_opt(vals0, vals1):
    """_render_onsets stub — vals0 on OPTION_0 calls, vals1 on
    OPTION_1 calls (alternating call order)."""
    calls = {"n": 0}

    def ro(wav, centers):
        calls["n"] += 1
        return list(vals0) if calls["n"] % 2 == 1 else list(vals1)
    return ro


def test_l1_early_conflict_may_be_preutterance(tmp_path, monkeypatch):
    """L1: source_ref < carrier_lo by 80ms → B2 EARLY conflict —
    preutterance_candidate is a legal hypothesis."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    notes = [{"id": "note_0001", "index": 1, "start": 0.5, "end": 1.0,
              "dur": 0.5, "tone": 60.0}]
    chars = [{"char": "甲", "start": 0.45, "end": 0.49}]
    it = _loop_item(notes)
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets",
                        _sro_vals([0.42], ["onset_peak"]))
    monkeypatch.setattr(sc, "_render_onsets", _ro_fixed([0.5]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    r = loop["char_routes"][0]
    assert r["route"] == sc.ROUTE_B2
    assert r["direction"] == "early"
    assert r["overhang_ms"] == pytest.approx(80.0, abs=0.5)
    assert r["route_detail"] == "preutterance_candidate"


def test_l2_late_conflict_is_never_anticipation(tmp_path, monkeypatch):
    """L2: source_ref > carrier_hi by 80ms → B2 LATE conflict — can
    NEVER be anticipation/preutterance (opposite physics)."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    notes = [{"id": "note_0001", "index": 1, "start": 0.0, "end": 0.5,
              "dur": 0.5, "tone": 60.0}]
    chars = [{"char": "甲", "start": 0.45, "end": 0.49}]
    it = _loop_item(notes)
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    # hi_move = 0.38; ref 0.46 → 80ms late
    monkeypatch.setattr(sc, "_source_ref_onsets",
                        _sro_vals([0.46], ["onset_peak"]))
    monkeypatch.setattr(sc, "_render_onsets", _ro_fixed([0.38]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    r = loop["char_routes"][0]
    assert r["route"] == sc.ROUTE_B2
    assert r["direction"] == "late"
    assert r["overhang_ms"] == pytest.approx(80.0, abs=0.5)
    assert "preutterance" not in r["route_detail"]
    assert "anticipation" not in r["route_detail"]
    assert r["route_detail"] == "post_boundary_delay_candidate"


def test_l3_threshold_is_triage_not_truth(tmp_path, monkeypatch):
    """L3: 115ms vs 129ms overhangs sit on opposite sides of the
    120ms line but BOTH stay B2 — the threshold names candidates,
    it never proves semantic truth. Direction + overhang persist."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    notes = [{"id": "note_0001", "index": 1, "start": 0.0, "end": 0.5,
              "dur": 0.5, "tone": 60.0},
             {"id": "note_0002", "index": 2, "start": 0.6, "end": 1.1,
              "dur": 0.5, "tone": 62.0}]
    chars = [{"char": "甲", "start": 0.40, "end": 0.44},
             {"char": "乙", "start": 1.05, "end": 1.09}]
    it = _loop_item(notes)
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    # hi_move = 0.38 / 0.98 → overhangs 115ms and 129ms late
    monkeypatch.setattr(sc, "_source_ref_onsets",
                        _sro_vals([0.495, 1.109],
                                  ["onset_peak", "onset_peak"]))
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_fixed([0.38, 0.98]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    r0, r1 = loop["char_routes"]
    assert r0["route"] == r1["route"] == sc.ROUTE_B2
    assert r0["direction"] == r1["direction"] == "late"
    # 14ms apart — the triage labels differ but neither is 'truth'
    assert r0["overhang_ms"] == pytest.approx(115.0, abs=0.5)
    assert r1["overhang_ms"] == pytest.approx(129.0, abs=0.5)
    assert r0["route_detail"].endswith("_candidate") or \
        r0["route_detail"].endswith("_suspect")
    assert r1["route_detail"].endswith("_candidate") or \
        r1["route_detail"].endswith("_suspect")


def test_l4_repeated_b2_marks_phrase_level(tmp_path):
    """L4: an identical B2 char set repeating across two review
    targets on the same phrase → phrase_level_carrier_conflict +
    structure_timing_suspect (repeated = structural evidence)."""
    import agent2utau.structure_calibration as sc
    cdir = tmp_path / "structure_calibration"
    items_d = cdir / "items"
    for iid in ("cal-a", "cal-b"):
        d = items_d / iid
        d.mkdir(parents=True)
        man = {"schema": sc.CALIB_SCHEMA,
               "phrase": {"start": 90.03, "end": 96.96},
               "calibration": {"lyric_evidence": {"articulation": {
                   "closed_loop": {"char_routes": [
                       {"char": c, "route": sc.ROUTE_B2,
                        "route_detail": "preutterance_candidate"}
                       for c in "可人陪这本"]}}}}}
        (d / "manifest.json").write_text(json.dumps(man),
                                         encoding="utf-8")
    marked = sc._phrase_level_conflicts(cdir)
    assert set(marked) == {"cal-a", "cal-b"}
    man = json.loads((items_d / "cal-a" / "manifest.json")
                     .read_text(encoding="utf-8"))
    cl = man["calibration"]["lyric_evidence"]["articulation"][
        "closed_loop"]
    assert cl["phrase_level_carrier_conflict"] is True
    assert cl["phrase_level_conflict_id"] == "90.03-96.96"
    assert cl["shared_b2_chars"] == sorted("可人陪这本")
    assert all(r["route_detail"] == "structure_timing_suspect"
               for r in cl["char_routes"])
    assert all(r["phrase_level_conflict_id"] == "90.03-96.96"
               for r in cl["char_routes"])
    # a lone target never marks phrase-level conflict
    cdir2 = tmp_path / "c2" / "structure_calibration" / "items"
    d = cdir2 / "cal-c"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(man),
                                    encoding="utf-8")
    assert sc._phrase_level_conflicts(
        cdir2.parent) == {}


def test_l5_class_a_render_missing_downgrades_b1(tmp_path,
                                                monkeypatch):
    """L5: initial class_A but render onset persistently missing →
    post-loop B1_render_unmeasurable (evidence unavailable, never
    'timing correct')."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    chars = [{"char": "甲", "start": 0.2, "end": 0.4},
             {"char": "乙", "start": 0.6, "end": 0.8}]
    it = _loop_item()
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets", _sro(chars))
    # char0's onset is NEVER detectable on either option
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_fixed([None, 0.6]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    r = loop["char_routes"][0]
    assert r["route"] == sc.ROUTE_B1
    assert r["route_subtype"] == "B1_render_unmeasurable"
    assert r["final_class"] == "B1_render_unmeasurable"
    assert r["render_measurement_status"] == "render_unmeasurable"
    assert loop["char_routes"][1]["route"] == sc.ROUTE_CLASS_A
    assert loop["converged"] is False


def test_l6_cross_option_unstable_downgrades_b1(tmp_path,
                                                monkeypatch):
    """L6: initial class_A but the two options persistently disagree
    on its onset → post-loop B1_cross_option_unstable."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    chars = [{"char": "甲", "start": 0.2, "end": 0.4},
             {"char": "乙", "start": 0.6, "end": 0.8}]
    it = _loop_item()
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets", _sro(chars))
    # OPTION_0 hears char0 at 0.55, OPTION_1 at -0.15 → 700ms apart
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_per_opt([0.55, 0.6], [-0.15, 0.6]))
    loop = sc._closed_loop_anchors({}, tmp_path / "i", it, chars,
                                   src_wav="x")
    r = loop["char_routes"][0]
    assert r["route"] == sc.ROUTE_B1
    assert r["route_subtype"] == "B1_cross_option_unstable"
    assert r["render_measurement_status"] == "cross_option_unstable"
    assert loop["converged"] is False


def test_l7_second_family_confirms_b1(tmp_path, monkeypatch):
    """L7: an independent energy edge consistent with the source
    landmark earns 'measurable_with_secondary_evidence' — re-entry
    eligibility is recorded, never averaged into the primary."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _qc_route_man(
        {"char": "我", "route": sc.ROUTE_B1,
         "route_subtype": "source_unmeasurable",
         "bound_conflict": False,
         "unmeasurable_reason": "no_source_landmark",
         "route_detail": None,
         "carrier_lo": 0.0, "carrier_hi": 0.38,
         "desired_anchor": 0.1, "final_anchor": 0.1,
         "measurement_stability": "unmeasurable_source"},
        ref_onsets=[0.1, 0.6])
    idir = tmp_path / "cal-x"
    idir.mkdir()
    _qc_idir(idir)
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.1, "end": 0.5,
             "probability": 0.9},
            {"char": "演", "start": 0.6, "end": 1.0,
             "probability": 0.9}])
    # src edge 0.12, option edges 0.15/0.16 → consistent (<150ms)
    edges = iter([0.12, 0.15, 0.16])
    monkeypatch.setattr(sc, "_energy_edge_onsets",
                        lambda w, c: [next(edges)])
    lt = sc._lyric_timing_qc(man, idir)
    sf = lt["acoustic"]["second_family"]["chars"]["我"]
    assert sf["verdict"] == "measurable_with_secondary_evidence"
    assert lt["per_char"][0]["secondary_measurement"] == \
        "measurable_with_secondary_evidence"


def test_l8_second_family_disagreement_stays_closed(tmp_path,
                                                    monkeypatch):
    """L8: second-family edges inconsistent with the source landmark
    → 'disagreed' — B1 stays fail-closed, never promoted."""
    import agent2utau.structure_calibration as sc
    import agent2utau.analysis.lyrics as al
    man = _qc_route_man(
        {"char": "我", "route": sc.ROUTE_B1,
         "route_subtype": "source_unmeasurable",
         "bound_conflict": False,
         "unmeasurable_reason": "no_source_landmark",
         "route_detail": None,
         "carrier_lo": 0.0, "carrier_hi": 0.38,
         "desired_anchor": 0.1, "final_anchor": 0.1,
         "measurement_stability": "unmeasurable_source"},
        ref_onsets=[0.1, 0.6])
    idir = tmp_path / "cal-x"
    idir.mkdir()
    _qc_idir(idir)
    monkeypatch.setattr(
        al, "force_align",
        lambda w, t, t0, t1, model=None: [
            {"char": "我", "start": 0.1, "end": 0.5,
             "probability": 0.9},
            {"char": "演", "start": 0.6, "end": 1.0,
             "probability": 0.9}])
    # src edge 0.12, option edges 0.5/0.6 → 380ms+ apart → disagreed
    edges = iter([0.12, 0.5, 0.6])
    monkeypatch.setattr(sc, "_energy_edge_onsets",
                        lambda w, c: [next(edges)])
    lt = sc._lyric_timing_qc(man, idir)
    sf = lt["acoustic"]["second_family"]["chars"]["我"]
    assert sf["verdict"] == "disagreed"
    assert lt["per_char"][0]["secondary_measurement"] == "disagreed"


def test_l9_no_route_may_alter_candidate0_timing(tmp_path,
                                                 monkeypatch):
    """L9: neither class_A updates nor B1/B2 holds nor post-loop
    downgrades may alter Candidate 0 written timing — context stays
    byte-identical."""
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    import copy
    notes = [{"id": "note_0001", "index": 1, "start": 0.0, "end": 0.5,
              "dur": 0.5, "tone": 60.0},
             {"id": "note_0002", "index": 2, "start": 0.5, "end": 1.0,
              "dur": 0.5, "tone": 62.0}]
    chars = [{"char": "甲", "start": 0.45, "end": 0.49},   # → B2 late
             {"char": "乙", "start": 0.6, "end": 0.8}]     # → class_A
    it = _loop_item(notes)
    before = copy.deepcopy(it["context"])
    monkeypatch.setattr(rr, "render_item", _fake_render_factory())
    monkeypatch.setattr(sc, "_source_ref_onsets",
                        _sro_vals([0.55, 0.6],
                                  ["onset_peak", "onset_peak"]))
    monkeypatch.setattr(sc, "_render_onsets",
                        _ro_fixed([0.38, 0.63]))
    sc._closed_loop_anchors({}, tmp_path / "i", it, chars, src_wav="x")
    assert it["context"] == before
    # written note start/end fields untouched — not even a key added
    assert [n["start"] for n in it["context"]] == \
        [n["start"] for n in before]
    assert [n["end"] for n in it["context"]] == \
        [n["end"] for n in before]


def test_l10_unresolved_cases_excluded_from_roster(tmp_path,
                                                  monkeypatch):
    """L10: a flagged item is not auto_review_ready → pilot authority
    refuses it — the honest roster keeps only reviewable samples."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch, n=2,
                                 not_ready_iids={"cal-s1"})
    a = sc.pilot_authority(
        run, [i["cal_item_id"] for i in items])
    assert not a["ok"]
    assert any("auto_review_ready" in v for v in a["violations"])
    # the honest roster = only the ready sample
    b = sc.pilot_authority(run, [items[0]["cal_item_id"]])
    assert b["ok"]
    assert b["sample_ids"] == [items[0]["cal_item_id"]]


# --------------------- §10.1.5A-G5M honest roster (M) ----------------

def _inv_store(tmp_path, monkeypatch, specs):
    """§G5M fixture: a calibration store + injectable scan evidence.
    specs: [{note_id, item_id, phrase_key, ev, bounds, refs, man, qc}]
      ev     → review_phrase_chars result dict
      bounds → (lo, hi) or None for _anchor_bounds
      refs   → (refs, kinds) for _source_ref_onsets
      man/qc → existing manifest/signal_qc dicts or None
    _classify_routes stays REAL — eligibility must derive from the
    same routing semantics the loop uses."""
    from pathlib import Path
    import agent2utau.structure_calibration as sc
    import agent2utau.review.render as rr
    cdir = tmp_path / "structure_calibration"
    (cdir / "items").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        rr, "load_run",
        lambda d: {"run_id": tmp_path.name, "vocals_wav": "v.wav",
                   "duration": 300.0})
    monkeypatch.setattr(rr, "verify_package",
                        lambda man, d: (True, "ok"))
    items, ev_by_start, bounds_by_iid, refs_by_pk = [], {}, {}, {}
    for i, s in enumerate(specs):
        iid = s["item_id"]
        ew = {"start": float(i), "end": float(i) + 1.0}
        items.append({
            "item_id": iid, "repair_id": f"srp-{iid}",
            "packets": [s["note_id"]], "type": "split",
            "phrase_key": s["phrase_key"],
            "phrase": dict(s.get("phrase")
                           or {"start": 0.0, "end": 5.0}),
            "context": s.get("context") or [],
            "evidence_window": ew})
        ev_by_start[ew["start"]] = s["ev"]
        bounds_by_iid[iid] = s["bounds"]
        refs_by_pk[s["phrase_key"]] = s["refs"]
        idir = cdir / "items" / iid
        idir.mkdir(exist_ok=True)
        if s.get("man") is not None:
            (idir / "manifest.json").write_text(
                json.dumps(s["man"]), encoding="utf-8")
        if s.get("qc") is not None:
            (idir / "signal_qc.json").write_text(
                json.dumps(s["qc"]), encoding="utf-8")
        pdir = cdir / "phrases" / s["phrase_key"]
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "SOURCE_PHRASE_separated_vocal.wav").write_bytes(b"x")
    monkeypatch.setattr(
        sc, "plan_calibration",
        lambda run, rph=None, lyric_contract=None: items)
    monkeypatch.setattr(
        sc, "review_phrase_chars",
        lambda run, win: ev_by_start.get(
            win["start"], {"ok": False, "chars": None,
                           "reason": "no_chars",
                           "min_probability": None, "n_chars": 0}))
    monkeypatch.setattr(
        sc, "_anchor_bounds",
        lambda it, chars: bounds_by_iid[it["item_id"]])
    monkeypatch.setattr(
        sc, "_source_ref_onsets",
        lambda chars, sw, ph0: refs_by_pk[Path(sw).parent.name])
    # §G5N.3: family-B is a real model — stub it per spec so tests
    # stay hermetic; s["fam_b"] may be a dict or a callable
    # (wav, chars) → align doc; default = unavailable (fail-closed)
    import agent2utau.identity_align as ia
    fam_by_pk = {s["phrase_key"]: s.get("fam_b") for s in specs}
    def _fa_stub(wav, chs):
        spec = fam_by_pk.get(Path(wav).parent.name)
        doc = spec(wav, chs) if callable(spec) else spec
        if doc is not None:
            return doc
        return {"available": False, "reason": "test_stub",
                "tokens": []}
    monkeypatch.setattr(ia, "forced_align", _fa_stub)
    return tmp_path


def _ev_ok(chars):
    return {"ok": True, "chars": chars, "reason": None,
            "min_probability": 0.9, "n_chars": len(chars)}


def _ev_fail(reason="low_confidence", n=3):
    return {"ok": False, "chars": None, "reason": reason,
            "min_probability": 0.3, "n_chars": n}


def test_m1_unresolved_b1_cannot_enter_roster(tmp_path, monkeypatch):
    """M1: no source landmark → every char B1 → the item is routed to
    measurement diagnosis, never into the pilot roster."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": c, "start": i * 0.4, "end": i * 0.4 + 0.3}
             for i, c in enumerate("甲乙丙")]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-b1", phrase_key="0.00-5.00",
        ev=_ev_ok(chars), bounds=([0.0, 0.4, 0.8], [0.3, 0.7, 1.1]),
        refs=(None, ["none"] * 3), man=None, qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["eligible"] is False
    assert any(d.startswith("source_unmeasurable")
               or d.startswith("unresolved_B1")
               for d in e["disqualifiers"])
    assert "measurement_diagnosis" in e["diagnosis_routes"]
    assert doc["roster_candidates"] == []


def test_m2_phrase_level_b2_cannot_enter_roster(tmp_path, monkeypatch):
    """M2: a shared B2 set repeating across targets on one phrase is a
    systematic conflict — both items route to structure diagnosis."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": c, "start": i * 0.4, "end": i * 0.4 + 0.3}
             for i, c in enumerate("甲乙丙")]
    spec = dict(ev=_ev_ok(chars),
                bounds=([0.0, 0.4, 0.8], [0.3, 0.7, 1.1]),
                # char 丙's ref lands above its carrier hi → B2 late
                refs=([0.1, 0.5, 1.5], ["onset_peak"] * 3))
    _inv_store(tmp_path, monkeypatch, [
        dict(note_id="note_0001", item_id="cal-p1",
             phrase_key="0.00-5.00", man=None, qc=None, **spec),
        dict(note_id="note_0002", item_id="cal-p2",
             phrase_key="0.00-5.00", man=None, qc=None, **spec)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    assert doc["summary"]["n_phrase_level"] == 2
    for e in doc["items"]:
        assert e["eligible"] is False
        assert e["phrase_level_carrier_conflict"] is True
        assert "丙" in e["shared_b2_chars"]
        assert "structure_diagnosis" in e["diagnosis_routes"]
    assert doc["roster_candidates"] == []


def test_m3_late_conflict_never_regains_via_anticipation(
        tmp_path, monkeypatch):
    """M3: a late-side conflict may not be relabeled anticipation to
    regain eligibility — the disqualifier and the direction persist."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-late",
        phrase_key="0.00-5.00", ev=_ev_ok(chars),
        bounds=([0.0], [0.3]),
        refs=([0.8], ["onset_peak"]), man=None, qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["eligible"] is False
    r = e["char_routes"][0]
    assert r["route"] == sc.ROUTE_B2
    assert r["direction"] == "late"
    assert r["route_detail"] in ("post_boundary_delay_candidate",
                                 "written_timing_suspect")


def test_m4_threshold_relax_cannot_make_b2_eligible(
        tmp_path, monkeypatch):
    """M4: the overhang line is a triage prior — widening it renames a
    detail, it never turns a carrier conflict into eligibility."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-th",
        phrase_key="0.00-5.00", ev=_ev_ok(chars),
        bounds=([0.0], [0.3]),
        refs=([0.9], ["onset_peak"]), man=None, qc=None)])
    monkeypatch.setattr(sc, "ANTICIPATION_MAX_S", 10.0)
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["eligible"] is False
    assert e["char_routes"][0]["route"] == sc.ROUTE_B2
    assert doc["roster_candidates"] == []




def test_m5_only_current_contract_may_be_selected(
        tmp_path, monkeypatch):
    """M5: a route-clean but stale/missing package is eligible only
    WITH rebuild_required — current-contract status is explicit."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    spec = dict(ev=_ev_ok(chars), bounds=([0.0], [0.5]),
                refs=([0.1], ["onset_peak"]))
    _inv_store(tmp_path, monkeypatch, [
        dict(note_id="note_0001", item_id="cal-stale",
             phrase_key="0.00-5.00",
             man={"schema": sc.CALIB_SCHEMA,
                  "package_state": "valid",
                  "audio_package_hash": "aph-old",
                  "calibration": {
                      "lyric_contract": "real_lyric_review",
                      "lyric_mapping_impl": "rlv6",
                      "contract_sha256": "old-stale"}},
             qc={"auto_flags": [], "auto_review_ready": True},
             **spec),
        dict(note_id="note_0002", item_id="cal-none",
             phrase_key="1.00-6.00", man=None, qc=None, **spec)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e0, e1 = doc["items"]
    assert e0["eligible"] is True and e0["rebuild_required"] is True
    assert e0["contract_status"] == "stale"
    assert e1["eligible"] is True and e1["rebuild_required"] is True
    assert e1["contract_status"] == "missing"


def test_m6_roster_derived_from_evidence_not_history(
        tmp_path, monkeypatch):
    """M6: the roster is recomputed from current evidence — flip one
    item's route evidence and it leaves roster_candidates."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    specs = [dict(note_id="note_0001", item_id="cal-a",
                  phrase_key="0.00-5.00", ev=_ev_ok(chars),
                  bounds=([0.0], [0.5]), refs=([0.1], ["onset_peak"]),
                  man=None, qc=None),
             dict(note_id="note_0002", item_id="cal-b",
                  phrase_key="1.00-6.00", ev=_ev_ok(chars),
                  bounds=([0.0], [0.5]), refs=([0.9], ["onset_peak"]),
                  man=None, qc=None)]
    _inv_store(tmp_path, monkeypatch, specs)
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    # §G5N.1: render-free clean items are rebuild candidates — the
    # roster itself requires current-contract post-loop evidence
    assert doc["roster_candidates"] == []
    assert doc["roster_pending_render"] == ["note_0001"]
    specs[1]["refs"] = ([0.1], ["onset_peak"])
    _inv_store(tmp_path, monkeypatch, specs)
    doc2 = sc.eligibility_inventory(tmp_path, progress=None)
    assert doc2["roster_candidates"] == []
    assert set(doc2["roster_pending_render"]) == {"note_0001",
                                                "note_0002"}


def test_m7_exact_roster_passes_pilot_authority(tmp_path, monkeypatch):
    """M7: a clean sample set + current contract + exact-sample QC
    binding → pilot_authority.ok=true."""
    import agent2utau.structure_calibration as sc
    run, items, sha = _g5h_store(tmp_path, monkeypatch, n=2)
    a = sc.pilot_authority(run, [i["cal_item_id"] for i in items])
    assert a["ok"]
    assert a["contract_sha256"] == sha
    assert a["lyric_mapping_impl"] == \
        sc.LYRIC_MAPPING_IMPL_VERSION["real_lyric_review"]


def test_m8_state_reads_never_dirty_evidence(tmp_path, monkeypatch):
    """M8: review_ready/git_evidence/verdict reads are pure — they may
    never create or mutate the Git-authoritative artifacts."""
    import agent2utau.structure_calibration as sc
    run, items, _ = _g5h_store(tmp_path, monkeypatch, n=1)
    cdir = tmp_path / "structure_calibration"
    before = {p.relative_to(cdir): p.read_bytes()
              for p in cdir.rglob("*") if p.is_file()}
    monkeypatch.setattr(sc, "_git_tracked_set", lambda d: set())
    monkeypatch.setattr(sc, "_git_dirty_set", lambda d: set())
    sc.review_ready(run)
    sc.git_evidence(run)
    sc.load_verdict(run)
    sc.plan_invariants(run)
    after = {p.relative_to(cdir): p.read_bytes()
             for p in cdir.rglob("*") if p.is_file()}
    assert before == after


def test_m9_inventory_binds_current_contract_identity(
        tmp_path, monkeypatch):
    """M9: the inventory binds the current contract identity — the
    FINAL acceptance SHA must carry this exact contract/impl."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-a",
        phrase_key="0.00-5.00", ev=_ev_ok(chars),
        bounds=([0.0], [0.5]), refs=([0.1], ["onset_peak"]),
        man=None, qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    assert doc["lyric_contract"] == "real_lyric_review"
    assert doc["lyric_mapping_impl"] == \
        sc.LYRIC_MAPPING_IMPL_VERSION["real_lyric_review"]
    assert doc["contract_sha256"] == sc.render_contract_sha(
        {"run_id": tmp_path.name}, sc._rph_hash(),
        "real_lyric_review")


def test_m10_no_pass_verdict_without_authority(tmp_path, monkeypatch):
    """M10: while the roster fails authority a PASS verdict is
    refused and review_ready stays false — no user surface."""
    import agent2utau.structure_calibration as sc
    run, items, _ = _g5h_store(
        tmp_path, monkeypatch, n=2, not_ready_iids={"cal-s1"})
    with pytest.raises(RuntimeError):
        sc.write_verdict(
            run, "PASS",
            sample_ids=[i["cal_item_id"] for i in items])
    assert sc.review_ready(run) is False


def test_m10b_inventory_gates_pilot_payload(tmp_path, monkeypatch):
    """M10: with an inventory on disk the pilot payload binds ONLY its
    honest roster — ineligible notes are refused, an empty roster
    emits no surface at all."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    _inv_store(tmp_path, monkeypatch, [
        dict(note_id="note_0001", item_id="cal-ok",
             phrase_key="0.00-5.00", ev=_ev_ok(chars),
             bounds=([0.0], [0.5]), refs=([0.1], ["onset_peak"]),
             man={"schema": sc.CALIB_SCHEMA,
                  "review_item_id": "cal-ok",
                  "package_state": "valid",
                  "audio_package_hash": "aph-ok",
                  "options": [{"option_id": "OPTION_0"},
                              {"option_id": "OPTION_1"}],
                  "calibration": {
                      "baseline_option": "OPTION_0",
                      "lyric_contract": "real_lyric_review",
                      "lyric_mapping_impl":
                          sc.LYRIC_MAPPING_IMPL_VERSION[
                              "real_lyric_review"],
                      "contract_sha256": sc.render_contract_sha(
                          {"run_id": tmp_path.name}, sc._rph_hash(),
                          "real_lyric_review"),
                      "lyric_evidence": {"articulation": {
                          "closed_loop": {"char_routes": [
                              {"char": "甲",
                               "final_class": sc.ROUTE_CLASS_A}]}}}}},
             qc=None),
        dict(note_id="note_0002", item_id="cal-bad",
             phrase_key="1.00-6.00", ev=_ev_ok(chars),
             bounds=([0.0], [0.3]), refs=([0.9], ["onset_peak"]),
             man=None, qc=None)])
    cdir = tmp_path / "structure_calibration"
    (cdir / "plan.json").write_text(json.dumps({
        "schema": sc.CALIB_SCHEMA, "items": [
            {"note_id": "note_0001", "cal_item_id": "cal-ok",
             "repair_id": "srp-ok", "type": "split",
             "phrase_key": "0.00-5.00",
             "phrase": {"start": 0.0, "end": 5.0}},
            {"note_id": "note_0002", "cal_item_id": "cal-bad",
             "repair_id": "srp-bad", "type": "split",
             "phrase_key": "1.00-6.00",
             "phrase": {"start": 0.0, "end": 5.0}}]}),
        encoding="utf-8")
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    assert doc["roster_candidates"] == ["note_0001"]
    monkeypatch.setattr(sc, "plan_invariants",
                        lambda d: {"ok": True, "violations": []})
    monkeypatch.setattr(sc, "_git_remote_repo",
                        lambda d: {"slug": None, "sha": None,
                                   "remote": None})
    # an ineligible note can never ride the payload
    with pytest.raises(RuntimeError):
        sc.build_pilot_review(tmp_path, note_ids=["note_0002"],
                              write=False)
    # the honest roster alone may bind
    payload = sc.build_pilot_review(tmp_path, write=False)
    assert [g["note_id"] for g in payload["groups"]] == ["note_0001"]


def test_m10c_empty_roster_emits_no_surface(tmp_path, monkeypatch):
    """M10: zero eligible items → no pilot payload, period."""
    import agent2utau.structure_calibration as sc
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-x",
        phrase_key="0.00-5.00", ev=_ev_fail(),
        bounds=None, refs=(None, []), man=None, qc=None)])
    cdir = tmp_path / "structure_calibration"
    (cdir / "plan.json").write_text(json.dumps({
        "schema": sc.CALIB_SCHEMA, "items": [
            {"note_id": "note_0001", "cal_item_id": "cal-x",
             "repair_id": "srp-x", "type": "split",
             "phrase_key": "0.00-5.00",
             "phrase": {"start": 0.0, "end": 5.0}}]}),
        encoding="utf-8")
    sc.eligibility_inventory(tmp_path, progress=None)
    monkeypatch.setattr(sc, "plan_invariants",
                        lambda d: {"ok": True, "violations": []})
    with pytest.raises(RuntimeError):
        sc.build_pilot_review(tmp_path, write=False)


# ------------------------------------------------- §G5N semantic adjudication


def _b2r(char, direction, oh_ms, ref):
    """Minimal B2 route dict for _b2_semantic unit tests."""
    import agent2utau.structure_calibration as sc
    return {"char": char, "route": sc.ROUTE_B2,
            "direction": direction, "overhang_ms": oh_ms,
            "source_ref_onset": ref}


def test_n1_benign_preutterance_needs_confirmed_obstruent():
    """§G5N.1: early obstruent + second family AND frication in the
    pre-carrier span + consistent neighbour → benign_preutterance.
    Waveform-onset agreement alone is never enough."""
    import agent2utau.structure_calibration as sc
    r = _b2r("等", "early", 37.0, 0.41)
    sem = sc._b2_semantic(
        r, "等", "early", 0.037, 0.40, 0.45, 0.90, 0.0, 0.4,
        span_ev={"insufficient": False, "frication_like": True},
        prev_class_a=True, next_class_a=True)
    assert sem["b2_semantic"] == "benign_preutterance"
    ev = sem["b2_evidence"]
    assert ev["initial_class"] == "obstruent"
    assert ev["second_family"] == "confirms"
    assert ev["shared_bound_conflict"] is True
    # same call without span evidence → confirmed displacement but
    # unproven semantics → ambiguous, not benign
    sem2 = sc._b2_semantic(r, "等", "early", 0.037, 0.40, 0.45, 0.90,
                           0.0, 0.4)
    assert sem2["b2_semantic"] == "measurement_ambiguous"


def test_n2_benign_post_boundary_delay_confirmed():
    """late + edge confirms + real pre-onset gap + consistent
    neighbour → benign_post_boundary_delay."""
    import agent2utau.structure_calibration as sc
    r = _b2r("遮", "late", 66.0, 1.016)
    sem = sc._b2_semantic(
        r, "遮", "late", 0.066, 1.00, 0.60, 0.95, 0.0, 0.4,
        span_ev={"insufficient": False, "pre_onset_gap": True,
                 "voiced_continuation": False},
        prev_class_a=True, next_class_a=True)
    assert sem["b2_semantic"] == "benign_post_boundary_delay"
    assert sem["b2_evidence"]["second_family"] == "confirms"


def test_n3_second_family_contradiction_is_ambiguous():
    """edge stays inside the legal range while the primary landmark
    crossed it → the conflict can't be trusted → ambiguous."""
    import agent2utau.structure_calibration as sc
    r = _b2r("等", "early", 37.0, 0.41)
    sem = sc._b2_semantic(r, "等", "early", 0.037, 0.50, 0.45, 0.90,
                          0.0, 0.4)
    assert sem["b2_semantic"] == "measurement_ambiguous"
    assert sem["b2_evidence"]["second_family"] == "contradicts"


def test_n4_confirmed_large_overhang_is_written_timing_error():
    """a 300ms+ early onset CONFIRMED by the second family → written
    timing error routed upstream, never benign."""
    import agent2utau.structure_calibration as sc
    r = _b2r("圆", "early", 319.0, 0.25)
    sem = sc._b2_semantic(r, "圆", "early", 0.319, 0.20, 0.57, 0.95,
                          None, 0.4)
    assert sem["b2_semantic"] == "written_timing_error"


def test_n5_no_second_family_is_unresolved():
    """without independent evidence a small overhang stays
    unresolved — 'the number is small' is not evidence."""
    import agent2utau.structure_calibration as sc
    r = _b2r("等", "early", 37.0, 0.41)
    sem = sc._b2_semantic(r, "等", "early", 0.037, None, 0.45, 0.90,
                          0.0, 0.4)
    assert sem["b2_semantic"] == "unresolved"
    assert sem["b2_evidence"]["second_family"] == "unavailable"


def test_n6_unknown_phoneme_never_benign():
    """a char outside the audited initial table fails closed in BOTH
    directions — no guessed phoneme may support a benign verdict."""
    import agent2utau.structure_calibration as sc
    r = _b2r("好", "early", 30.0, 0.42)
    sem = sc._b2_semantic(r, "好", "early", 0.030, 0.41, 0.45, 0.90,
                          0.0, 0.4)
    assert sem["b2_semantic"] == "unresolved"
    assert sem["b2_evidence"]["initial_class"] == "unknown"
    r2 = _b2r("好", "late", 60.0, 1.0)
    sem2 = sc._b2_semantic(r2, "好", "late", 0.06, 1.0, 0.6, 0.95,
                           0.0, 0.4)
    assert sem2["b2_semantic"] == "unresolved"


def test_n7_glide_cannot_preutter():
    """a glide-initial char has no consonant to preutter — early +
    confirmed is still not benign (boundary/elision suspicion)."""
    import agent2utau.structure_calibration as sc
    r = _b2r("夜", "early", 37.0, 0.41)
    sem = sc._b2_semantic(r, "夜", "early", 0.037, 0.40, 0.45, 0.90,
                          0.0, 0.4)
    assert sem["b2_semantic"] in ("unresolved",
                                  "written_timing_error",
                                  "measurement_ambiguous")
    assert sem["b2_semantic"] != "benign_preutterance"


def _fam_b_ok(monkeypatch, chars, offset=0.0):
    """family-B mock: aligns every known token at the family-A
    position (+offset) — what a good forced alignment looks like."""
    import agent2utau.identity_align as ia
    def _fa(wav, chs):
        return {"aligner_family": ia.ALIGNER_FAMILY,
                "aligner_version": ia.ALIGNER_VERSION,
                "available": True, "reason": None,
                "tokens": [
                    {"token_index": i, "char": c["char"],
                     "pinyin": "x", "phoneme_sequence": None,
                     "start": c["start"] + offset,
                     "end": c["end"] + offset,
                     "confidence": -0.5,
                     "boundary_uncertainty_s": 0.02,
                     "status": "aligned"}
                    for i, c in enumerate(chs)]}
    monkeypatch.setattr(ia, "forced_align", _fa)


def test_n8_lyric_outlier_timing_supported_by_family_b(monkeypatch):
    """§G5N.3: a low-prob char's TIMING is corroborated ONLY via
    family-B alignment_supported — onset-peak is timing corroboration
    only and phoneme-class consistency is a diagnostic. The lexical
    identity was never in question: known lyrics already fix it."""
    import agent2utau.structure_calibration as sc
    import agent2utau.identity_align as ia
    chars = [{"char": "甲", "start": 0.0, "end": 0.3,
              "probability": 0.9},
             {"char": "等", "start": 0.4, "end": 0.7,
              "probability": 0.01},
             {"char": "丙", "start": 0.8, "end": 1.1,
              "probability": 0.9}]
    run = {"chars": chars}
    it = {"phrase": {"start": 0.0, "end": 2.0},
          "evidence_window": {"start": 0.0, "end": 1.2}}
    ev = {"ok": False, "reason": "low_confidence", "chars": None}
    monkeypatch.setattr(
        sc, "_source_ref_onsets",
        lambda c, sw, ph0: ([0.0, 0.41, 0.8], ["onset_peak"] * 3))
    monkeypatch.setattr(
        sc, "_onset_span_evidence",
        lambda sw, a, b: {"insufficient": False,
                          "frication_like": True,
                          "periodicity": 0.2})
    # family-B aligns the same known token with valid order/timing
    _fam_b_ok(monkeypatch, chars)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    # lexical identity was NEVER doubted — the gate is about timing
    assert adj["lexical_text_status"] == "authoritative_known"
    assert adj["timing_supported"] is True
    assert adj["alignment_status"] == "supported"
    assert adj["diagnosis"] == "timing_supported"
    ent = adj["low_prob_chars"][0]
    assert ent["timing_corroborated"] is True
    assert ent["family_b_verdict"] == "alignment_supported"
    # phoneme-class consistency is recorded as diagnostic only
    assert ent["phoneme_class_consistent"] is True
    # family-B unavailable → alignment_unresolved → fail closed even
    # with perfect phoneme-class consistency
    monkeypatch.setattr(
        ia, "forced_align",
        lambda wav, chs: {"aligner_family": ia.ALIGNER_FAMILY,
                          "aligner_version": ia.ALIGNER_VERSION,
                          "available": False,
                          "reason": "source_wav_missing",
                          "tokens": []})
    adj2 = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj2["timing_supported"] is False
    assert adj2["alignment_status"] == "unresolved"
    assert adj2["diagnosis"] == "alignment_unresolved"
    # a landmark far from the claimed position does NOT confirm
    _fam_b_ok(monkeypatch, chars)
    monkeypatch.setattr(
        sc, "_source_ref_onsets",
        lambda c, sw, ph0: ([0.0, 0.60, 0.8], ["onset_peak"] * 3))
    adj3 = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj3["timing_supported"] is False
    # a contradicting third-family landmark demotes to ambiguous —
    # a real timing-evidence conflict, never a silent pass
    assert adj3["alignment_status"] == "ambiguous"
    assert adj3["diagnosis"] == "measurement_ambiguous"


def test_n9_no_chars_instrumental_is_a5_not_a1():
    """a window inside an instrumental span (nearest lyric chars far
    away) is honestly no_lyrics coverage — not a coverage bug."""
    import agent2utau.structure_calibration as sc
    run = {"chars": [{"char": "甲", "start": 0.0, "end": 0.3},
                     {"char": "乙", "start": 30.0, "end": 30.3}]}
    it = {"phrase": {"start": 5.0, "end": 7.0},
          "evidence_window": {"start": 5.0, "end": 7.0}}
    ev = {"ok": False, "reason": "no_chars", "chars": None}
    adj = sc._adjudicate_lyric_evidence(run, it, ev, [], None, 5.0)
    assert adj["lexical_text_status"] == "no_lyrics"
    assert adj["diagnosis"] == "A5_instrumental_no_lyrics"
    assert adj["timing_supported"] is False


def test_n10_phrase_level_is_target_independent(tmp_path, monkeypatch):
    """the same B2 set on two targets of ONE phrase is ONE
    target-independent finding routed to adjudication — never
    double-confirmed evidence of a written-score error."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "夜", "start": 0.0, "end": 0.3}]
    spec = dict(phrase_key="0.00-5.00", ev=_ev_ok(chars),
                bounds=([0.40], [0.75]),
                refs=([0.30], ["onset_peak"]))
    _inv_store(tmp_path, monkeypatch, [
        dict(note_id="note_0001", item_id="cal-a", **spec),
        dict(note_id="note_0002", item_id="cal-b", **spec)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    for e in doc["items"]:
        assert e["phrase_level_target_independent_conflict"] is True
        assert e["eligible"] is False
        assert any(d.startswith("phrase_level_carrier_conflict")
                   for d in e["disqualifiers"])


def test_n10b_benign_b2_leaves_blocker_route(tmp_path, monkeypatch):
    """a benign-resolved B2 stops disqualifying — but ONLY via the
    independent-evidence path, and the item still can't be roster-
    final without current-contract post-loop evidence (§G5N.1)."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "等", "start": 0.0, "end": 0.3},
             {"char": "甲", "start": 0.4, "end": 0.7}]
    ctx = [{"id": "n1", "start": 0.40, "end": 0.75, "dur": 0.35},
           {"id": "n2", "start": 0.80, "end": 1.15, "dur": 0.35}]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-ben",
        phrase_key="0.00-5.00", ev=_ev_ok(chars),
        context=ctx,
        bounds=([0.40, 0.80], [0.75, 1.15]),
        refs=([0.37, 0.85], ["onset_peak"] * 2),
        man=None, qc=None)])
    monkeypatch.setattr(sc, "_energy_edge_onsets",
                        lambda sw, centers: [0.38, None])
    monkeypatch.setattr(
        sc, "_onset_span_evidence",
        lambda sw, a, b: {"insufficient": False,
                          "frication_like": True, "periodicity": 0.2,
                          "pre_onset_gap": False,
                          "voiced_continuation": False})
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    r = e["char_routes"][0]
    assert r["route"] == sc.ROUTE_B2
    assert r["b2_semantic"] == "benign_preutterance"
    assert e["eligible"] is True
    assert e["disqualifiers"] == []
    # render-free clean ≠ final eligibility — it is a rebuild
    # candidate until a current-contract closed loop verifies it
    assert e["post_loop_gate"] == "needs_render"
    assert e["final_eligible"] is False
    assert doc["roster_candidates"] == []
    assert doc["roster_pending_render"] == ["note_0001"]


def test_n11_onset_peak_is_timing_corroboration_only(monkeypatch):
    """N11: onset-peak confirms timing but cannot carry the gate —
    without family-B the low-prob boundary stays unresolved."""
    import agent2utau.structure_calibration as sc
    import agent2utau.identity_align as ia
    chars = [{"char": "甲", "start": 0.0, "end": 0.3,
              "probability": 0.9},
             {"char": "等", "start": 0.4, "end": 0.7,
              "probability": 0.01}]
    run = {"chars": chars}
    it = {"phrase": {"start": 0.0, "end": 2.0},
          "evidence_window": {"start": 0.0, "end": 1.0}}
    ev = {"ok": False, "reason": "low_confidence", "chars": None}
    monkeypatch.setattr(
        sc, "_source_ref_onsets",
        lambda c, sw, ph0: ([0.0, 0.41], ["onset_peak"] * 2))
    monkeypatch.setattr(sc, "_onset_span_evidence",
                        lambda sw, a, b: {"insufficient": True})
    monkeypatch.setattr(
        ia, "forced_align",
        lambda wav, chs: {"available": False,
                          "reason": "source_wav_missing",
                          "tokens": []})
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj["timing_supported"] is False
    assert adj["alignment_status"] == "unresolved"
    assert adj["diagnosis"] == "alignment_unresolved"
    assert adj["low_prob_chars"][0]["timing_corroborated"] is True


def test_n12_family_b_agreement_supports_timing(monkeypatch):
    """N12: family-B boundary agreement supports the low-prob char's
    timing WITHOUT touching the 0.25 threshold — a timing pass,
    never a lexical-identity recovery."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3,
              "probability": 0.9},
             {"char": "等", "start": 0.4, "end": 0.7,
              "probability": 0.01}]
    run = {"chars": chars}
    it = {"phrase": {"start": 0.0, "end": 2.0},
          "evidence_window": {"start": 0.0, "end": 1.0}}
    ev = {"ok": False, "reason": "low_confidence", "chars": None}
    monkeypatch.setattr(
        sc, "_source_ref_onsets",
        lambda c, sw, ph0: ([0.0, 0.41], ["onset_peak"] * 2))
    monkeypatch.setattr(
        sc, "_onset_span_evidence",
        lambda sw, a, b: {"insufficient": False,
                          "frication_like": True,
                          "periodicity": 0.2})
    _fam_b_ok(monkeypatch, chars)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj["timing_supported"] is True
    assert adj["lexical_text_status"] == "authoritative_known"
    assert adj["diagnosis"] == "timing_supported"
    assert sc.MIN_REVIEW_CHAR_PROB == 0.25


def test_n13_late_waveform_agreement_is_not_benign():
    """N13: late + same-family detector confirms = displacement real,
    semantics unproven — never benign on waveform agreement alone."""
    import agent2utau.structure_calibration as sc
    r = _b2r("遮", "late", 66.0, 1.016)
    sem = sc._b2_semantic(r, "遮", "late", 0.066, 1.00, 0.60, 0.95,
                          0.0, 0.4)
    assert sem["b2_semantic"] == "measurement_ambiguous"
    # loud periodic continuation up to the onset → NOT a delay
    sem2 = sc._b2_semantic(
        r, "遮", "late", 0.066, 1.00, 0.60, 0.95, 0.0, 0.4,
        span_ev={"insufficient": False, "pre_onset_gap": False,
                 "voiced_continuation": True},
        next_class_a=True)
    assert sem2["b2_semantic"] == "measurement_ambiguous"


def test_n14_benign_late_needs_phoneme_and_neighbor():
    """N14: benign late needs gap evidence + neighbour consistency —
    a displaced next neighbour means a systematic shift, not a local
    delay."""
    import agent2utau.structure_calibration as sc
    r = _b2r("遮", "late", 66.0, 1.016)
    ev = {"insufficient": False, "pre_onset_gap": True,
          "voiced_continuation": False}
    ok = sc._b2_semantic(r, "遮", "late", 0.066, 1.00, 0.60, 0.95,
                         0.0, 0.4, span_ev=ev, next_class_a=True)
    assert ok["b2_semantic"] == "benign_post_boundary_delay"
    bad = sc._b2_semantic(r, "遮", "late", 0.066, 1.00, 0.60, 0.95,
                          0.0, 0.4, span_ev=ev, next_class_a=False)
    assert bad["b2_semantic"] == "measurement_ambiguous"


def _man_with_post_loop(final_class):
    """manifest carrying a closed_loop char_route with final_class."""
    import agent2utau.structure_calibration as sc
    return {"schema": sc.CALIB_SCHEMA,
            "calibration": {
                "lyric_contract": "real_lyric_review",
                "lyric_mapping_impl": sc.LYRIC_MAPPING_IMPL_VERSION[
                    "real_lyric_review"],
                "lyric_evidence": {"articulation": {"closed_loop": {
                    "char_routes": [{"char": "甲",
                                     "final_class": final_class}]}}}},
            "audio_package_hash": "x"}


def test_n15_post_loop_b1_unstable_blocks(tmp_path, monkeypatch):
    """N15: post-loop B1_cross_option_unstable is a hard roster
    blocker even when every pre-loop conflict is clean."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-b1p",
        phrase_key="0.00-5.00", ev=_ev_ok(chars),
        context=[{"id": "n1", "start": 0.0, "end": 0.3, "dur": 0.3}],
        bounds=([0.0], [0.3]), refs=([0.1], ["onset_peak"]),
        man=_man_with_post_loop("B1_cross_option_unstable"),
        qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["post_loop_gate"] == "b1_block"
    assert any(d.startswith("unresolved_post_loop_B1")
               for d in e["disqualifiers"])
    assert e["eligible"] is False
    assert doc["roster_candidates"] == []


def test_n16_post_loop_b1_relock_blocks(tmp_path, monkeypatch):
    """N16: B1_detector_relock hard-blocks identically."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-b1r",
        phrase_key="0.00-5.00", ev=_ev_ok(chars),
        context=[{"id": "n1", "start": 0.0, "end": 0.3, "dur": 0.3}],
        bounds=([0.0], [0.3]), refs=([0.1], ["onset_peak"]),
        man=_man_with_post_loop("B1_detector_relock"), qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["post_loop_gate"] == "b1_block"
    assert e["eligible"] is False


def test_n17_verified_post_loop_allows_final(tmp_path, monkeypatch):
    """N17: a clean pre-loop item WITH current-contract post-loop
    evidence (all class_A) may be roster-final."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    man = _man_with_post_loop(sc.ROUTE_CLASS_A)
    man["calibration"]["contract_sha256"] = sc.render_contract_sha(
        {"run_id": tmp_path.name}, sc._rph_hash(),
        "real_lyric_review")
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-ver",
        phrase_key="0.00-5.00", ev=_ev_ok(chars),
        context=[{"id": "n1", "start": 0.0, "end": 0.3, "dur": 0.3}],
        bounds=([0.0], [0.3]), refs=([0.1], ["onset_peak"]),
        man=man, qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["post_loop_gate"] == "verified"
    assert e["final_eligible"] is True
    assert doc["roster_candidates"] == ["note_0001"]


def test_n18_phrase_level_benign_is_audit_only(tmp_path, monkeypatch):
    """N18: shared B2s ALL resolved benign → the target-independent
    flag remains for audit but adds NO disqualifier."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "等", "start": 0.0, "end": 0.3}]
    ctx = [{"id": "n1", "start": 0.40, "end": 0.75, "dur": 0.35}]
    spec = dict(phrase_key="0.00-5.00", ev=_ev_ok(chars),
                context=ctx, bounds=([0.40], [0.75]),
                refs=([0.37], ["onset_peak"]))
    _inv_store(tmp_path, monkeypatch, [
        dict(note_id="note_0001", item_id="cal-a", **spec),
        dict(note_id="note_0002", item_id="cal-b", **spec)])
    monkeypatch.setattr(sc, "_energy_edge_onsets",
                        lambda sw, centers: [0.38])
    monkeypatch.setattr(
        sc, "_onset_span_evidence",
        lambda sw, a, b: {"insufficient": False,
                          "frication_like": True, "periodicity": 0.2})
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    for e in doc["items"]:
        assert e["phrase_level_target_independent_conflict"] is True
        assert not any(
            d.startswith("phrase_level_carrier_conflict")
            for d in e["disqualifiers"])
        assert e["eligible"] is True


def test_n19_phrase_level_unresolved_still_blocks(
        tmp_path, monkeypatch):
    """N19: any non-benign shared B2 keeps the phrase-level blocker."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "夜", "start": 0.0, "end": 0.3}]
    spec = dict(phrase_key="0.00-5.00", ev=_ev_ok(chars),
                context=[{"id": "n1", "start": 0.40, "end": 0.75,
                          "dur": 0.35}],
                bounds=([0.40], [0.75]),
                refs=([0.30], ["onset_peak"]))
    _inv_store(tmp_path, monkeypatch, [
        dict(note_id="note_0001", item_id="cal-a", **spec),
        dict(note_id="note_0002", item_id="cal-b", **spec)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    for e in doc["items"]:
        assert e["phrase_level_target_independent_conflict"] is True
        assert any(d.startswith("phrase_level_carrier_conflict")
                   for d in e["disqualifiers"])
        assert e["eligible"] is False


def test_n20_subresolution_is_neutral(tmp_path, monkeypatch):
    """N20: a below-resolution displacement cannot establish a
    material conflict — measurement_below_resolution is neutral,
    never a hard blocker by itself."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "等", "start": 0.0, "end": 0.3}]
    ctx = [{"id": "n1", "start": 0.40, "end": 0.75, "dur": 0.35}]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-sub",
        phrase_key="0.00-5.00", ev=_ev_ok(chars), context=ctx,
        bounds=([0.40], [0.75]),
        refs=([0.392], ["onset_peak"]),  # 8ms early < resolution
        man=None, qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    r = e["char_routes"][0]
    assert r["route"] == sc.ROUTE_B2
    assert r["b2_semantic"] == "measurement_below_resolution"
    assert e["eligible"] is True
    assert e["disqualifiers"] == []


def test_n21_inventory_carries_post_loop_gates(tmp_path, monkeypatch):
    """N21: every inventory item records its post-loop gate state —
    verified / b1_block / needs_render — for the after-commit state
    rebuild to audit."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-g",
        phrase_key="0.00-5.00", ev=_ev_ok(chars),
        bounds=([0.0], [0.3]), refs=([0.1], ["onset_peak"]),
        man=None, qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["post_loop_gate"] in ("verified", "b1_block",
                                   "needs_render")
    assert "roster_pending_render" in doc
    assert "final_eligible" in e


def _n_fixture(monkeypatch):
    """shared low-conf lyric fixture for the N22+ matrix."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3,
              "probability": 0.9},
             {"char": "等", "start": 0.4, "end": 0.7,
              "probability": 0.01},
             {"char": "丙", "start": 0.8, "end": 1.1,
              "probability": 0.9}]
    run = {"chars": chars}
    it = {"phrase": {"start": 0.0, "end": 2.0},
          "evidence_window": {"start": 0.0, "end": 1.2}}
    ev = {"ok": False, "reason": "low_confidence", "chars": None}
    monkeypatch.setattr(
        sc, "_source_ref_onsets",
        lambda c, sw, ph0: ([0.0, 0.41, 0.8], ["onset_peak"] * 3))
    monkeypatch.setattr(
        sc, "_onset_span_evidence",
        lambda sw, a, b: {"insufficient": False,
                          "frication_like": True,
                          "periodicity": 0.2})
    return sc, chars, run, it, ev


def test_n22_waveform_only_never_supports(monkeypatch):
    """N22: timing corroboration + phoneme-class consistency WITHOUT
    family-B → alignment stays unresolved (supported=false)."""
    import agent2utau.identity_align as ia
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    monkeypatch.setattr(
        ia, "forced_align",
        lambda wav, chs: {"available": False,
                          "reason": "source_wav_missing",
                          "tokens": []})
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    ent = adj["low_prob_chars"][0]
    assert ent["timing_corroborated"] is True
    assert ent["phoneme_class_consistent"] is True
    assert ent["family_b_verdict"] == "alignment_unresolved"
    assert adj["timing_supported"] is False
    assert adj["alignment_status"] == "unresolved"


def test_n23_family_b_same_token_supports(monkeypatch):
    """N23: family-B aligning the same known token with valid
    confidence/order → alignment_supported → timing gate may pass."""
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    _fam_b_ok(monkeypatch, chars)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj["low_prob_chars"][0]["family_b_verdict"] == \
        "alignment_supported"
    assert adj["timing_supported"] is True
    assert adj["diagnosis"] == "timing_supported"


def test_n24_family_b_order_conflict_fails_closed(monkeypatch):
    """N24: family-B non-monotonic placement →
    alignment_order_conflict → fail-closed."""
    import agent2utau.identity_align as ia
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    def _fa(wav, chs):
        # swap the order: token 1 (等) placed BEFORE token 0
        toks = [{"token_index": i, "char": c["char"],
                 "pinyin": "x", "phoneme_sequence": None,
                 "start": c["start"], "end": c["end"],
                 "confidence": -0.5,
                 "boundary_uncertainty_s": 0.02,
                 "status": "aligned"}
                for i, c in enumerate(chs)]
        toks[1]["start"] = -0.5
        toks[1]["end"] = -0.2
        return {"aligner_family": ia.ALIGNER_FAMILY,
                "aligner_version": ia.ALIGNER_VERSION,
                "available": True, "reason": None, "tokens": toks}
    monkeypatch.setattr(ia, "forced_align", _fa)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj["low_prob_chars"][0]["family_b_verdict"] == \
        "alignment_order_conflict"
    assert adj["timing_supported"] is False
    assert adj["alignment_status"] == "order_conflict"
    assert adj["diagnosis"] == "alignment_order_conflict"


def test_n25_family_b_unavailable_fails_closed(monkeypatch):
    """N25: family-B unavailable or low-confidence →
    alignment_unresolved → fail-closed."""
    import agent2utau.identity_align as ia
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    # low-confidence token (status=skipped)
    def _fa(wav, chs):
        toks = [{"token_index": i, "char": c["char"],
                 "pinyin": "x", "phoneme_sequence": None,
                 "start": c["start"], "end": c["end"],
                 "confidence": -9.0,
                 "boundary_uncertainty_s": 0.02,
                 "status": "skipped"}
                for i, c in enumerate(chs)]
        return {"aligner_family": ia.ALIGNER_FAMILY,
                "aligner_version": ia.ALIGNER_VERSION,
                "available": True, "reason": None, "tokens": toks}
    monkeypatch.setattr(ia, "forced_align", _fa)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj["low_prob_chars"][0]["family_b_verdict"] == \
        "alignment_unresolved"
    assert adj["timing_supported"] is False
    assert adj["alignment_status"] == "unresolved"


def test_n26_known_text_alone_is_not_evidence(monkeypatch):
    """N26: the known lyric sequence is the lexical AUTHORITY and
    the alignment constraint — its mere presence is not acoustic
    evidence; without family-B output timing stays unresolved."""
    import agent2utau.identity_align as ia
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    monkeypatch.setattr(
        ia, "forced_align",
        lambda wav, chs: {"available": False,
                          "reason": "source_wav_missing",
                          "tokens": []})
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    # known text fixed identity already — but the TIMING gate still
    # needs an acoustic family; unavailable → unresolved
    assert adj["lexical_text_status"] == "authoritative_known"
    assert adj["family_b"]["available"] is False
    assert all(e["family_b_verdict"] == "alignment_unresolved"
               for e in adj["low_prob_chars"])
    assert adj["timing_supported"] is False


def test_n27_timing_disagreement_is_ambiguous(monkeypatch):
    """N27: family-B same token but A/B boundary disagreement beyond
    the evidence-derived tolerance → measurement_ambiguous — the
    lexical token itself stays known."""
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    _fam_b_ok(monkeypatch, chars, offset=0.5)  # +500ms shift
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    ent = adj["low_prob_chars"][0]
    assert ent["family_b_verdict"] == "measurement_ambiguous"
    assert adj["timing_supported"] is False
    assert adj["alignment_status"] == "ambiguous"
    assert adj["diagnosis"] == "measurement_ambiguous"
    assert adj["lexical_text_status"] == "authoritative_known"


def test_n28_no_tolerance_relaxation(monkeypatch):
    """N28: the timing verdict may not be bought by widening the
    tolerance — the cap is a safety bound, not a pass target."""
    import agent2utau.identity_align as ia
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    _fam_b_ok(monkeypatch, chars, offset=0.5)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    ent = adj["low_prob_chars"][0]
    assert ent["tolerance_s"] <= ia.ALIGN_TIMING_CAP_S + 1e-9
    assert ent["family_b_verdict"] == "measurement_ambiguous"


def test_n29_supported_persists_provenance(monkeypatch):
    """N29: a timing-supported token carries
    family/provenance/hash/boundary evidence — auditable end to end."""
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    _fam_b_ok(monkeypatch, chars)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj["timing_supported"] is True
    fb = adj["family_b"]
    assert fb["aligner_family"] == "mms_fa_ctc_uroman"
    assert fb["aligner_version"] is not None
    tok = fb["tokens"][1]
    assert tok["char"] == "等"
    assert tok["start"] is not None and tok["end"] is not None
    assert tok["confidence"] is not None
    ent = adj["low_prob_chars"][0]
    assert ent["famB_start"] is not None
    assert ent["dev_start_s"] is not None


def test_n30_aligner_change_bumps_evidence_contract():
    """N30: material aligner/model/lexicon/config change bumps
    ALIGNER_VERSION — dependent evidence contracts must go stale."""
    import agent2utau.identity_align as ia
    import agent2utau.structure_calibration as sc
    assert ia.ALIGNER_VERSION == "ifa2"
    assert ia.ALIGNER_FAMILY == "mms_fa_ctc_uroman"
    assert sc.LYRIC_MAPPING_IMPL_VERSION["real_lyric_review"] ==         "rlv11"


def test_n31_family_b_may_strengthen_b2_never_identity():
    """N31: family-B boundaries MAY feed B2 semantics, but a forced
    alignment under known tokens can never be independent lexical
    recognition — the two lanes stay separate."""
    import agent2utau.identity_align as ia
    import agent2utau.structure_calibration as sc
    assert callable(sc._onset_span_evidence)
    assert ia.ALIGNER_FAMILY not in ("onset_strength_peak_v1",
                                     "energy_edge_v1")
    v = ia.alignment_adjudicate(
        {"available": True,
         "tokens": [{"token_index": 0, "char": "等",
                     "start": 0.4, "end": 0.7,
                     "confidence": -0.5, "status": "aligned"}]},
        [{"char": "等", "start": 0.4, "end": 0.7}])
    # timing agreement — NOT identity_verified; that name is retired
    assert v["verdicts"][0]["verdict"] == "alignment_supported"


def test_n32_low_prob_never_fails_lexical_identity(monkeypatch):
    """N32: known lyric + low Whisper probability →
    lexical_text_status=authoritative_known — a low probability can
    never fail lexical identity by itself (§G5N.3)."""
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    _fam_b_ok(monkeypatch, chars)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj["lexical_text_status"] == "authoritative_known"
    assert adj["low_prob_chars"][0]["probability"] == 0.01
    # identity stays known even when timing evidence is still weak
    assert adj["timing_supported"] is True


def test_n33_forced_alignment_is_not_identity_authority(monkeypatch):
    """N33: MMS same-token target may yield alignment_supported but
    MUST NOT produce an independent lexical-identity verdict — the
    token was injected as the target."""
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    _fam_b_ok(monkeypatch, chars)
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    allv = [v["verdict"] for v in adj["family_b"]["verdicts"]]
    assert "identity_verified" not in allv
    assert set(allv) <= {"alignment_supported",
                         "alignment_unresolved",
                         "alignment_order_conflict",
                         "measurement_ambiguous"}
    # the adjudication doc carries no identity authority field
    assert "identity_verified" not in adj
    assert "identity_conflict" not in adj


def test_n34_boundary_agreement_passes_timing_gate(
        tmp_path, monkeypatch):
    """N34: Whisper/MMS agreement within tolerance → timing gate
    passes → the item proceeds to route classification."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3,
              "probability": 0.9},
             {"char": "等", "start": 0.4, "end": 0.7,
              "probability": 0.01},
             {"char": "丙", "start": 0.8, "end": 1.1,
              "probability": 0.9}]
    ctx = [{"id": "n1", "start": 0.0, "end": 0.35, "dur": 0.35},
           {"id": "n2", "start": 0.40, "end": 0.75, "dur": 0.35},
           {"id": "n3", "start": 0.80, "end": 1.15, "dur": 0.35}]
    ev = {"ok": False, "reason": "low_confidence",
          "min_probability": 0.01, "n_chars": 3}
    run_chars = list(chars)
    import agent2utau.review.render as rr
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-ts",
        phrase_key="0.00-5.00", ev=ev, context=ctx,
        bounds=([0.0, 0.40, 0.80], [0.35, 0.75, 1.15]),
        refs=([0.02, 0.42, 0.82], ["onset_peak"] * 3),
        man=None, qc=None)])
    # run["chars"] must exist for the adjudication's window scan
    for m in (rr,):
        orig = rr.load_run
        monkeypatch.setattr(
            m, "load_run",
            lambda d, _o=orig: dict(_o(d), chars=run_chars))
    _fam_b_ok(monkeypatch, chars)
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["lyric_evidence"]["alignment_status"] == "supported"
    assert e["lyric_evidence"]["lexical_text_status"] == \
        "authoritative_known"
    assert e["lyric_evidence"]["adjudicated"] is True
    assert not any(d.split(":")[0].startswith("alignment")
                   or d.startswith("lyric_coverage")
                   for d in e["disqualifiers"])


def test_n35_timing_disagreement_keeps_known_token(
        tmp_path, monkeypatch):
    """N35: Whisper/MMS disagreement beyond tolerance →
    measurement_ambiguous disqualifier — but the lexical token
    itself remains authoritative_known."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3,
              "probability": 0.9},
             {"char": "等", "start": 0.4, "end": 0.7,
              "probability": 0.01},
             {"char": "丙", "start": 0.8, "end": 1.1,
              "probability": 0.9}]
    ev = {"ok": False, "reason": "low_confidence",
          "min_probability": 0.01, "n_chars": 3}
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-amb",
        phrase_key="0.00-5.00", ev=ev,
        bounds=None, refs=(None, ["none"] * 3),
        man=None, qc=None)])
    import agent2utau.review.render as rr
    orig = rr.load_run
    monkeypatch.setattr(
        rr, "load_run", lambda d: dict(orig(d), chars=list(chars)))
    _fam_b_ok(monkeypatch, chars, offset=0.6)  # 600ms disagreement
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["lyric_evidence"]["lexical_text_status"] == \
        "authoritative_known"
    assert e["lyric_evidence"]["alignment_status"] == "ambiguous"
    assert any(d.startswith("alignment_ambiguous")
               for d in e["disqualifiers"])
    assert "measurement_diagnosis" in e["diagnosis_routes"]
    assert e["eligible"] is False


def test_n36_mms_unavailable_no_timing_authority(monkeypatch):
    """N36: MMS unavailable / low CTC confidence →
    alignment_unresolved — no timing authority is invented."""
    import agent2utau.identity_align as ia
    sc, chars, run, it, ev = _n_fixture(monkeypatch)
    monkeypatch.setattr(
        ia, "forced_align",
        lambda wav, chs: {"available": False,
                          "reason": "aligner_unavailable:RuntimeError",
                          "tokens": []})
    adj = sc._adjudicate_lyric_evidence(
        run, it, ev, chars, "fake.wav", 0.0)
    assert adj["alignment_status"] == "unresolved"
    assert adj["diagnosis"] == "alignment_unresolved"
    assert adj["timing_supported"] is False


def test_n37_coverage_mismatch_fail_closed(tmp_path, monkeypatch):
    """N37: lyric chars bound just outside the evidence window →
    lexical_text_status=coverage_mismatch → fail-closed; the known
    token sequence is never forced into a wrong phrase."""
    import agent2utau.structure_calibration as sc
    # nearest chars are 0.5s outside the window (< INSTRUMENTAL_GAP)
    chars = [{"char": "甲", "start": 0.0, "end": 0.3}]
    it = {"phrase": {"start": 1.0, "end": 2.0},
          "evidence_window": {"start": 1.0, "end": 2.0}}
    ev = {"ok": False, "reason": "no_chars", "chars": None}
    adj = sc._adjudicate_lyric_evidence(
        {"chars": chars}, it, ev, [], None, 1.0)
    assert adj["lexical_text_status"] == "coverage_mismatch"
    assert adj["diagnosis"] == "A1_coverage_suspect"
    assert adj["timing_supported"] is False
    # through the inventory it must disqualify into the coverage lane
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-cov",
        phrase_key="0.00-5.00",
        ev={"ok": False, "reason": "no_chars", "chars": None,
            "min_probability": None, "n_chars": 0},
        bounds=None, refs=(None, ["none"]), man=None, qc=None)])
    import agent2utau.review.render as rr
    orig = rr.load_run
    monkeypatch.setattr(
        rr, "load_run", lambda d: dict(orig(d), chars=chars))
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["lyric_evidence"]["lexical_text_status"] == \
        "coverage_mismatch"
    assert any(d.startswith("lyric_coverage:")
               for d in e["disqualifiers"])
    assert "coverage_diagnosis" in e["diagnosis_routes"]


def test_n38_instrumental_never_gets_forced_tokens(
        tmp_path, monkeypatch):
    """N38: instrumental/no-lyrics span → lexical_text_status=
    no_lyrics — no forced lyric alignment may be emitted."""
    import agent2utau.structure_calibration as sc
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-ins",
        phrase_key="0.00-5.00",
        ev={"ok": False, "reason": "no_chars", "chars": None,
            "min_probability": None, "n_chars": 0},
        bounds=None, refs=(None, ["none"]), man=None, qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    assert e["lyric_evidence"]["lexical_text_status"] == "no_lyrics"
    assert any(d == "lyric_coverage:no_lyrics"
               for d in e["disqualifiers"])
    assert e["eligible"] is False
    assert (e.get("lyric_adjudication") or {}).get("family_b") \
        is None  # never aligned — nothing to align


def test_n39_rlv10_identity_fields_are_historical_only():
    """N39: a rlv10 artifact's identity_verified is readable for
    audit but can never authorize the current roster — the current
    contract version makes it stale."""
    import agent2utau.structure_calibration as sc
    man = {"schema": sc.CALIB_SCHEMA,
           "calibration": {
               "lyric_contract": "real_lyric_review",
               "lyric_mapping_impl": "rlv10",
               "contract_sha256": "old",
               "lyric_evidence": {"adjudication": {
                   "family_b_verdict": "identity_verified"}}}}
    # historical field is READABLE…
    assert man["calibration"]["lyric_evidence"]["adjudication"][
        "family_b_verdict"] == "identity_verified"
    # …but the artifact is stale under the current rlv11 contract —
    # it can never bind a current roster/review/repair
    assert sc.item_contract_stale(man, {}, "rph") is True


def test_n40_material_change_bumps_timing_contract():
    """N40: a material aligner/model/lexicon/config change bumps the
    TIMING evidence contract — ifa2 renamed the verdict set."""
    import agent2utau.identity_align as ia
    assert ia.ALIGNER_VERSION == "ifa2"
    assert ia.ALIGNER_FAMILY == "mms_fa_ctc_uroman"
    v = ia.alignment_adjudicate({"available": False}, [])
    assert v["verdicts"] == []
    assert v["available"] is False


def test_n41_b1_readjudicated_by_mms_span(tmp_path, monkeypatch):
    """N41: B1 no_source_landmark with a usable MMS span →
    measurability re-adjudicated — B1 must not persist solely
    because the onset detector missed a landmark."""
    import agent2utau.structure_calibration as sc
    chars = [{"char": "甲", "start": 0.0, "end": 0.3},
             {"char": "数", "start": 0.4, "end": 0.7}]
    ctx = [{"id": "n1", "start": 0.0, "end": 0.35, "dur": 0.35},
           {"id": "n2", "start": 0.40, "end": 0.75, "dur": 0.35}]
    # char 2 has NO onset landmark (whisper_fallback → would-be B1);
    # family-B places its token INSIDE the carrier → measurable.
    fam = {"available": True, "reason": None,
           "tokens": [
               {"token_index": 0, "char": "甲", "start": 0.02,
                "end": 0.33, "confidence": -0.4,
                "status": "aligned"},
               {"token_index": 1, "char": "数", "start": 0.45,
                "end": 0.72, "confidence": -0.4,
                "status": "aligned"}]}
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0001", item_id="cal-b1m",
        phrase_key="0.00-5.00", ev=_ev_ok(chars), context=ctx,
        bounds=([0.0, 0.40], [0.35, 0.75]),
        refs=([0.02, 0.42], ["onset_peak", "whisper_fallback"]),
        fam_b=fam, man=None, qc=None)])
    doc = sc.eligibility_inventory(tmp_path, progress=None)
    e = doc["items"][0]
    r1, r2 = e["char_routes"]
    assert r1["route"] == sc.ROUTE_CLASS_A
    # the missed onset landmark was re-adjudicated by the MMS span —
    # no B1 may remain for it
    assert r2["route"] == sc.ROUTE_CLASS_A
    assert r2["b1_readjudicated"] is True
    assert r2["source_ref_kind"] == "mms_fa_token"
    assert r2["primary_measurement"] == "mms_fa_ctc_uroman"
    assert not any(d.startswith("unresolved_B1")
                   for d in e["disqualifiers"])
    assert doc["summary"]["n_b1_readjudicated"] == 1
    # and without family-B the same evidence still fails closed
    _inv_store(tmp_path, monkeypatch, [dict(
        note_id="note_0002", item_id="cal-b1n",
        phrase_key="0.00-5.00", ev=_ev_ok(chars), context=ctx,
        bounds=([0.0, 0.40], [0.35, 0.75]),
        refs=([0.02, 0.42], ["onset_peak", "whisper_fallback"]),
        man=None, qc=None)])
    doc2 = sc.eligibility_inventory(tmp_path, progress=None)
    e2 = doc2["items"][0]
    assert e2["char_routes"][1]["route"] == sc.ROUTE_B1
    assert any(d.startswith("unresolved_B1")
               for d in e2["disqualifiers"])
