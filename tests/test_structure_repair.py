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


def test_j8_rlv3_artifacts_stale_under_rlv6():
    """J8: the rlv3→rlv6 impl bump stales every previous package/
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
    assert sc.LYRIC_MAPPING_IMPL_VERSION["real_lyric_review"] == "rlv6"


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
    assert r["route_detail"] == "anticipation_candidate"
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



def _qc_route_man(route0, route1=None):
    """_timing_man + injected rlv6 closed_loop carrying char_routes."""
    import agent2utau.structure_calibration as sc
    man = _timing_man()
    r1 = route1 or {"char": "演", "route": sc.ROUTE_CLASS_A,
                    "bound_conflict": False,
                    "unmeasurable_reason": None,
                    "route_detail": None,
                    "carrier_lo": 0.5, "carrier_hi": 0.97,
                    "desired_anchor": 0.6, "final_anchor": 0.6,
                    "measurement_stability": "stable"}
    man["calibration"]["lyric_evidence"]["articulation"] = {
        "impl": "rlv6",
        "closed_loop": {
            "converged": False, "reason": "hard_cases_only",
            "char_routes": [route0, r1]}}
    return man


def _qc_idir(idir):
    """wavs + matching-carrier ustx pair for _lyric_timing_qc."""
    (idir / "o0.wav").write_bytes(b"x")
    (idir / "o1.wav").write_bytes(b"x")
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
