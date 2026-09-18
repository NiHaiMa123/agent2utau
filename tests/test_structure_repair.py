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


def _tracked_all(item_ids=()):
    """Everything the Git-evidence rule could require — simulates a
    fully-committed store for _git_tracked_set monkeypatches."""
    from agent2utau.structure_calibration import GIT_REQUIRED_ITEM_FILES
    s = {"plan.json", "state.json",
         "qc/verdict.json", "qc/audit.jsonl"}
    for iid in item_ids:
        s |= {f"items/{iid}/{f}" for f in GIT_REQUIRED_ITEM_FILES}
    return s


def test_g9_review_ready_defaults_false(tmp_path, monkeypatch):
    """G9: review-ready is false until an explicit verdict — render
    success alone never sets it; a mismatched contract hash fails too."""
    import agent2utau.structure_calibration as sc
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    assert not sc.review_ready(run, "contract-x")
    sc.write_verdict(run, "FAIL", "contract-x", auditor="t")
    assert not sc.review_ready(run, "contract-x")
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _tracked_all())
    sc.write_verdict(run, "PASS", "contract-x", auditor="t")
    assert sc.review_ready(run, "contract-x")
    assert not sc.review_ready(run, "other-contract")


def test_g10_full_batch_blocked_until_qc_pass(tmp_path, monkeypatch):
    """G10: build_calibration with no `only` filter is a full batch —
    blocked until the contract's QC verdict is PASS (and committed)."""
    import agent2utau.review.render as rr
    import agent2utau.structure_calibration as sc
    monkeypatch.setattr(rr, "load_run", lambda p: _fake_run_dict())
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    with pytest.raises(RuntimeError, match="QC PASS"):
        sc.build_calibration(run, render=False)
    # a sample/subset build is the allowed pre-QC path
    res = sc.build_calibration(run, render=False, only=["note_0002"])
    contract = res["contract_sha256"]
    iid = res["items"][0]["cal_item_id"]
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: _tracked_all([iid]))
    sc.write_verdict(run, "PASS", contract, auditor="t",
                     sample_ids=[iid])
    res2 = sc.build_calibration(run, render=False)
    assert len(res2["items"]) == 1
    it_dir = run / "structure_calibration" / "items" \
        / res2["items"][0]["cal_item_id"]
    assert (it_dir / "semantic_diff.json").exists()      # G8 artifact
    plan = json.loads((run / "structure_calibration"
                       / "plan.json").read_text(encoding="utf-8"))
    assert plan["lyric_contract"] == "neutral_vowel"
    assert plan["schema"] == "m25-cal-2"


# --------------------------------- §10.1.5A Git evidence + G5A/G5B artifacts

def test_git_evidence_pass_refused_without_commits(tmp_path, monkeypatch):
    """Git-evidence rule: a PASS verdict is refused while required
    artifacts are uncommitted — local existence never counts."""
    import agent2utau.structure_calibration as sc
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    monkeypatch.setattr(sc, "_git_tracked_set", lambda d: None)
    with pytest.raises(RuntimeError, match="not committed to Git"):
        sc.write_verdict(run, "PASS", "c", auditor="t",
                         sample_ids=["i1"])
    monkeypatch.setattr(sc, "_git_tracked_set", lambda d: {"plan.json"})
    with pytest.raises(RuntimeError, match="not committed to Git"):
        sc.write_verdict(run, "PASS", "c", auditor="t",
                         sample_ids=["i1"])
    rec = sc.write_verdict(run, "FAIL", "c", auditor="t")
    assert rec["verdict"] == "FAIL"


def test_git_evidence_review_ready_needs_qc_committed(tmp_path,
                                                      monkeypatch):
    """A recorded PASS only takes effect after the qc files themselves
    are committed — the verdict must exist in Git, not just on disk."""
    import agent2utau.structure_calibration as sc
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    iid = "cal-x"
    base = {"plan.json", "state.json"} | {
        f"items/{iid}/{f}" for f in sc.GIT_REQUIRED_ITEM_FILES}
    monkeypatch.setattr(sc, "_git_tracked_set", lambda d: set(base))
    sc.write_verdict(run, "PASS", "c", auditor="t", sample_ids=[iid])
    assert not sc.review_ready(run, "c")     # qc files not committed yet
    monkeypatch.setattr(sc, "_git_tracked_set",
                        lambda d: base | {"qc/verdict.json",
                                          "qc/audit.jsonl"})
    assert sc.review_ready(run, "c")


def _fake_rendered_item(tmp_path, name="cal-x", region=(2.0, 2.5),
                        phrase_start=0.0, dur=6.0, sr=8000,
                        cand_gain=1.0):
    """Write a minimal rendered item dir: two option wavs + manifest."""
    import numpy as np
    import soundfile as sf
    idir = tmp_path / "items" / name
    idir.mkdir(parents=True)
    t = np.arange(int(sr * dur)) / sr
    base = 0.1 * np.sin(2 * np.pi * 200 * t)
    cand = base * cand_gain
    sf.write(str(idir / "OPTION_0.wav"), base, sr)
    sf.write(str(idir / "OPTION_1.wav"), cand, sr)
    man = {"review_item_id": name,
           "calibration": {"repair_id": "srp-x",
                           "baseline_option": "OPTION_0",
                           "candidate_role": "OPTION_1"},
           "options": [{"option_id": "OPTION_0", "wav": "OPTION_0.wav"},
                       {"option_id": "OPTION_1", "wav": "OPTION_1.wav"}],
           "target_group": {"region": list(region)},
           "phrase": {"start": phrase_start,
                      "end": phrase_start + dur}}
    (idir / "manifest.json").write_text(json.dumps(man))
    return idir, man


def test_target_focus_crops_and_signal_qc(tmp_path, monkeypatch):
    """G5A/G5B: BASELINE/CANDIDATE_TARGET.wav are crops of the real
    rendered wavs at region±0.5s; signal_qc.json records drift metrics."""
    import soundfile as sf
    import agent2utau.structure_calibration as sc
    monkeypatch.setattr(sc, "_f0_summary",
                        lambda p, t0=0.0, t1=None: {"midi_median": 64.0})
    idir, man = _fake_rendered_item(tmp_path, region=(2.0, 2.5),
                                    phrase_start=1.0)
    qc = sc.augment_item(idir)
    info = sf.info(str(idir / "BASELINE_TARGET.wav"))
    # window = 1.5..3.0 absolute → phrase-relative 0.5..2.0 → 1.5s
    assert info.frames == int(1.5 * 8000)
    assert (idir / "CANDIDATE_TARGET.wav").exists()
    assert (idir / "signal_qc.json").exists()
    assert qc["target_window"]["absolute"] == [1.5, 3.0]
    assert qc["option_loudness_ratio"] == pytest.approx(1.0, abs=0.01)
    assert qc["auto_review_ready"] is True       # identical renders
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
    """G5B: out-of-target A/B acoustic divergence (DiffSinger context
    bleed) is quantified and flagged — full-phrase A/B alone can never
    be the primary review surface."""
    import numpy as np
    import soundfile as sf
    import agent2utau.structure_calibration as sc
    monkeypatch.setattr(sc, "_f0_summary",
                        lambda p, t0=0.0, t1=None: {"midi_median": 64.0})
    idir, man = _fake_rendered_item(tmp_path, region=(2.0, 3.0))
    # overwrite OPTION_1: identical inside target, divergent after 4s
    sr, t = 8000, np.arange(8000 * 6) / 8000
    c = 0.1 * np.sin(2 * np.pi * 200 * t)
    c[int(4 * sr):] = 0.18 * np.sin(2 * np.pi * 260 * t[int(4 * sr):])
    sf.write(str(idir / "OPTION_1.wav"), c, sr)
    qc = sc.signal_qc(man, idir)
    assert qc["pre_target_ab_diff_rms_ratio"] == pytest.approx(
        0.0, abs=1e-3)
    assert qc["target_ab_diff_rms_ratio"] == pytest.approx(
        0.0, abs=1e-3)
    assert qc["post_target_ab_diff_rms_ratio"] > 0.5
    assert any("post_target_ab_drift" in f for f in qc["auto_flags"])
    assert qc["auto_review_ready"] is False
    assert qc["target_focus_is_primary"] is True


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
    assert "qc/verdict.json" in ev["missing"]
    assert "items/cal-a/signal_qc.json" in ev["missing"]
    assert "items/cal-a/BASELINE_TARGET.wav" in ev["missing"]
    assert all(e.startswith("items/cal-b/") for e in ev["missing"]
               if e.startswith("items/cal-b/"))
    assert ev["checked"] == 2 + 2 + 2 * len(sc.GIT_REQUIRED_ITEM_FILES)
