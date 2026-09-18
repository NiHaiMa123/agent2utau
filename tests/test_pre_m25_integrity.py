"""Pre-M2.5 Freeze Integrity regressions (plan2 §6.1-6.3, §6.5 matrix).

A: provisional B must not launder identity-unsafe aggregate run_tones
   into a finalized result.
B: C missing boundary/GAME-structure evidence is neutral, never
   complement support.
C: M2.4 plan binds BOTH semantic notes hash and exact file bytes.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from agent2utau.diagnostic.adjudicate import adjudicate
from agent2utau.diagnostic.structure_adj import (
    _boundary_energy, adjudicate_structure, apply_structure)
from agent2utau.repair import apply_plan, build_plan

from test_c2_final_patch import _audio, _vpkt
from test_repair import _mk_run, _machine_pkt, _NOTES
from test_structure_adj import _pkt, _times_energy, PL1, PL2


# ---------------------------------------------------------------- Blocker A

def test_a1_aggregate_run_tones_neutral_on_structure_ambiguous():
    """A1: structure_varies + aggregate run_tones=[60,64,...] -> the
    aggregate must NOT fabricate GAME support for either tone; the
    medoid's own written note keeps its H0 anchor only."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=60.0)
    p["rmvpe"] = {"center_midi": 64.0, "iqr_cents": 10,
                  "voiced_coverage": 1.0}          # seeds the h64 hyp
    p["consensus"] = {"run_tones": [60.0, 64.0, 60.0, 64.0, 60.0],
                      "n_runs": 5, "structure_varies": True}
    adj = adjudicate(p, wav, sr, None, [])
    assert adj["game_evidence"] == "aggregate_neutralized_structure_ambiguous"
    h60 = [h for h in adj["hypotheses"] if h["hypothesis"] == 60.0][0]
    h64 = [h for h in adj["hypotheses"] if h["hypothesis"] == 64.0][0]
    # medoid written note still anchors H0; aggregate gives h64 NOTHING
    assert h60["group_scores"]["game"] == 1.0
    assert h64["group_scores"]["game"] == 0.0
    assert "game" not in adj["opposing_independence_groups"]


def test_a2_provisional_b_finalizes_on_identity_safe_evidence():
    """A2: provisional B + C resolved_keep -> finalized winner/margin
    comes from identity-safe evidence only (aggregate neutralized)."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=60.0)
    p["rmvpe"] = {"center_midi": 64.0, "iqr_cents": 10,
                  "voiced_coverage": 1.0}          # seeds the h64 hyp
    p["consensus"] = {"run_tones": [64.0, 64.0, 64.0, 64.0],
                      "n_runs": 4, "structure_varies": True}
    p["state"] = {"routing_needs": {"structure_adjudication": True,
                                    "pitch_adjudication": True,
                                    "phrase_review": False},
                  "decision": "needs_structure_adjudication"}
    adj = adjudicate(p, wav, sr, None, [])
    adj["provisional"] = True
    p["pitch_adjudication"] = adj
    # the aggregate would have voted 4/4 for 64 — neutralized, so the
    # winner cannot be the aggregate's answer
    h64 = [h for h in adj["hypotheses"] if h["hypothesis"] == 64.0][0]
    assert h64["group_scores"]["game"] == 0.0
    c = adjudicate_structure(p, *_times_energy(10.0, 10.4), [],
                             voiced=None)
    assert c["status"] == "resolved_keep"
    apply_structure(p, c)
    b = p["pitch_adjudication"]
    assert b["provisional"] is False
    assert b["finalized_by"] == "structure_resolved_keep"
    assert b["game_evidence"] == \
        "aggregate_neutralized_structure_ambiguous"


def test_a3_structure_change_still_invalidates_provisional_b():
    """A3: resolved_change_candidate keeps invalidating old B —
    virtual path unaffected."""
    p = _pkt(varies=True)
    p["pitch_adjudication"] = {"status": "resolved_change",
                               "provisional": True,
                               "winning_hypothesis": 64.0}
    c = {"status": "resolved_change_candidate",
         "hypothesis_detail": {"kind": "split", "boundary": 10.2,
                               "notes": [{"start": 10.0, "end": 10.2},
                                         {"start": 10.2, "end": 10.4}]},
         "classification": "TRUE_SPLIT_CANDIDATE"}
    apply_structure(p, c, virtual_b=[{"id": "v0", "status":
                                      "resolved_keep"}])
    b = p["pitch_adjudication"]
    assert b["status"] == "invalidated"
    assert b["invalidated_by_structure"] is True
    assert b["old_winning_hypothesis"] == 64.0


def test_a4_structure_stable_run_tones_unchanged():
    """A4: ordinary C0 (structure_varies=False) keeps continuous
    GAME run-tone semantics — no neutralization."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=60.0, run_tones=[60.0, 64.0, 60.0, 64.0])
    adj = adjudicate(p, wav, sr, None, [])
    assert adj["game_evidence"] == "run_tones"
    h64 = [h for h in adj["hypotheses"] if h["hypothesis"] == 64.0][0]
    assert h64["group_scores"]["game"] == pytest.approx(0.5)


def test_a5_virtual_correspondence_is_identity_safe():
    """A5: virtual_correspondence packets stay on the identity-aware
    denominator path — no neutralization."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=60.0, run_tones=[60.0])
    p["consensus"]["virtual_correspondence"] = {"n_total_runs": 5}
    p["consensus"]["structure_varies"] = True    # irrelevant with vcorr
    adj = adjudicate(p, wav, sr, None, [])
    assert adj["game_evidence"] == "identity_aware_correspondence"
    h60 = [h for h in adj["hypotheses"] if h["hypothesis"] == 60.0][0]
    assert h60["group_scores"]["game"] == pytest.approx(0.2)


# ---------------------------------------------------------------- Blocker B

def test_b1_insufficient_boundary_samples_unavailable():
    """B1: too few samples around the boundary -> available=False."""
    times = np.array([10.0])
    energy = np.array([0.5])
    be = _boundary_energy(times, energy, 10.2, 10.0, 10.4)
    assert be["available"] is False
    assert be["boundary_support"] == 0.0
    assert be["continuity_support"] == 0.0


def test_b2_unavailable_boundary_never_supports_either_side():
    """B2: a boundary candidate exists but the observation is
    unavailable -> acoustic_boundary group contributes 0 to H0 AND H1."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[1, 2, 1, 2, 1], varies=True)
    # energy window ends BEFORE the boundary context -> insufficient
    times = np.linspace(10.0, 10.12, 12)
    energy = np.full(12, 0.5)
    adj = adjudicate_structure(p, times, energy,
                               ["dual_f0_multi_plateau"])
    assert adj["boundary_evidence"]["available"] is False
    assert adj["boundary_evidence"]["non_f0_support"] == 0.0
    assert adj["all_scores"]["H0"] == pytest.approx(
        adj["game_structure"]["one_note_ratio"] + 0 + 0 + 0 + 0.5)


def test_b3_missing_run_note_counts_neutral_game_structure():
    """B3: no run_note_counts -> game_one=0, game_split=0 (was 1.0)."""
    p = _pkt(pl_r=PL1, pl_f=PL1)
    p["consensus"]["run_note_counts"] = []
    times, energy = _times_energy(10.0, 10.4)
    adj = adjudicate_structure(p, times, energy, [])
    gs = adj["game_structure"]
    assert gs["available"] is False
    assert gs["one_note_ratio"] == 0.0 and gs["split_ratio"] == 0.0


def test_b4_all_missing_evidence_cannot_resolve_keep():
    """B4: missing boundary + missing GAME structure + missing
    extractor -> unresolved; absence alone never unlocks keep."""
    p = _pkt(pl_r=[], pl_f=[], varies=True)
    p["consensus"]["run_note_counts"] = []
    times, energy = _times_energy(10.0, 10.4)
    adj = adjudicate_structure(p, times, energy, [])
    assert adj["status"] == "unresolved"
    # apply_structure must not set final_structure_clear
    p2 = dict(p)
    apply_structure(p2, adj)
    assert not p2.get("final_structure_clear")


def test_b5_observed_continuity_is_explicit_evidence():
    """B5: a real flat observation supports H0 through
    continuity_support, not complement-of-missing."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[1, 1, 1, 1, 1], varies=True)
    times, energy = _times_energy(10.0, 10.4)      # flat 0.5 energy
    adj = adjudicate_structure(p, times, energy, [])
    be = adj["boundary_evidence"]
    assert be["available"] is True
    assert be["continuity_support"] > 0.5          # explicit evidence
    # H1's split_gate still needs a real dip — flat energy fails it
    if adj["winning_hypothesis"] == "H1":
        assert adj["status"] != "resolved_change_candidate" or \
            be["non_f0_support"] > 0.3


def test_b6_dip_still_supports_boundary():
    """B6: a real observed dip still feeds boundary_support."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[1, 2, 1, 2, 1], varies=True)
    times, energy = _times_energy(10.0, 10.4, dip_at=10.20)
    adj = adjudicate_structure(p, times, energy,
                               ["dual_f0_multi_plateau"])
    be = adj["boundary_evidence"]
    assert be["available"] is True
    assert be["non_f0_support"] > 0
    assert adj["status"] == "resolved_change_candidate"


# ---------------------------------------------------------------- Blocker C

def test_c1_notes_change_stales_both(tmp_path):
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    assert plan["candidate0_notes_sha256"]
    assert plan["candidate0_file_sha256"]
    c0 = run / "diagnostic" / "baseline_game.json"
    d = json.loads(c0.read_text())
    d["notes"][0]["tone"] = 99.0
    c0.write_text(json.dumps(d))
    with pytest.raises(RuntimeError, match="stale"):
        apply_plan(run, plan)


def test_c2_metadata_only_change_stales_plan(tmp_path):
    """C2: notes identical but run_index/provenance changed ->
    file-hash stale -> refuse apply."""
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    c0 = run / "diagnostic" / "baseline_game.json"
    d = json.loads(c0.read_text())
    d["run_index"] = 99
    c0.write_text(json.dumps(d))
    with pytest.raises(RuntimeError, match="stale"):
        apply_plan(run, plan)


def test_c3_byte_only_change_stales_plan(tmp_path):
    """C3: same JSON, different bytes -> stale."""
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    c0 = run / "diagnostic" / "baseline_game.json"
    c0.write_text(c0.read_text() + "\n")
    with pytest.raises(RuntimeError, match="stale"):
        apply_plan(run, plan)


def test_c4_apply_never_writes_candidate0(tmp_path):
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    import hashlib
    pre = hashlib.sha256(
        (run / "diagnostic" / "baseline_game.json").read_bytes()) \
        .hexdigest()
    apply_plan(run, plan)
    post = hashlib.sha256(
        (run / "diagnostic" / "baseline_game.json").read_bytes()) \
        .hexdigest()
    assert pre == post == plan["candidate0_file_sha256"]


def test_c5_artifacts_record_both_hashes(tmp_path):
    run = _mk_run(tmp_path, [_machine_pkt()])
    plan = build_plan(run)
    res = apply_plan(run, plan)
    sc = res["score"]
    assert sc["base_candidate0_notes_sha256"] == \
        plan["candidate0_notes_sha256"]
    assert sc["base_candidate0_file_sha256"] == \
        plan["candidate0_file_sha256"]
    m = res["manifest"]
    assert m["candidate0_notes_sha256"] == plan["candidate0_notes_sha256"]
    assert m["candidate0_file_sha256"] == plan["candidate0_file_sha256"]
    p2 = build_plan(run)
    assert p2["plan_hash"] == plan["plan_hash"]      # deterministic
