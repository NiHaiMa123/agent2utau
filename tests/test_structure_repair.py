"""M2.5 structure repair — split/merge/boundary_shift (plan2 §10.1).

Human path consumes the M2.4-preserved blocked_structure authority
(repair_authorized_decision snapshot, no re-review). Machine path only
materializes frozen resolved_change_candidate packets that pass the
operation-specific precision gate — verified, never re-derived.
"""
from __future__ import annotations

import json

import pytest

from agent2utau.repair import (BLOCKED_CONFLICT, PATCH_OK, REJECTED,
                               apply_structure_ops, apply_structure_plan,
                               build_structure_plan,
                               machine_structure_candidates,
                               validate_structure_patch)

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

def test_structure_plan_apply_machine_split(tmp_path):
    run = _mk_run(tmp_path, [_machine_split_pkt()])
    plan = build_structure_plan(run)
    e = plan["repairs"][0]
    assert e["status"] == PATCH_OK
    assert e["repair_id"].startswith("srp-")
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
    plan = build_structure_plan(run)
    assert all(e["status"] == BLOCKED_CONFLICT
               for e in plan["repairs"])
    res = apply_structure_plan(run, plan)
    assert res["score"]["notes"] == _NOTES        # nothing applied

    run2 = _mk_run(tmp_path / "b", [_machine_split_pkt()])
    _human_decision(run2, _split_patch())          # identical patch
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
