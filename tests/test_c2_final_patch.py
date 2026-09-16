"""C2 final correctness patch regressions (plan2 §8.1-8.5, §9 matrix)."""
import numpy as np
import pytest

from agent2utau.diagnostic.adjudicate import adjudicate
from agent2utau.diagnostic.structure_adj import (
    adjudicate_structure, apply_structure, _one_note_support)
from agent2utau.diagnostic.triage import safe_retune_gate

from test_structure_adj import _pkt, _times_energy, PL1, PL2


def _audio(sr=44100, f=440.0, dur=1.0):
    t = np.arange(int(sr * dur)) / sr
    return (0.1 * np.sin(2 * np.pi * f * t)).astype(np.float32), sr


def _vpkt(seed=64.0, run_tones=None, unavailable=False):
    """Virtual-note style packet: acoustic seed + optional real GAME
    run tones."""
    p = {"id": "v", "start": 10.0, "dur": 0.4, "game_tone": seed,
         "candidate_written_pitch": seed, "candidate_seed": True,
         "flags": [], "rmvpe": {"center_midi": seed, "iqr_cents": 10,
                                "voiced_coverage": 1.0},
         "fcpe": {"center_midi": seed, "iqr_cents": 12,
                  "voiced_coverage": 1.0},
         "plateaus": PL1, "fcpe_plateaus": PL1}
    if run_tones is not None:
        p["consensus"] = {"run_tones": run_tones, "n_runs": len(run_tones),
                          "structure_varies": False}
    if unavailable:
        p["game_evidence_unavailable"] = True
    return p


# ---- §8.1: virtual pitch seed != GAME evidence ---------------------------

def test_virtual_seed_without_game_members_is_neutral():
    """A: RMVPE-derived seed + no real GAME member notes -> game group
    neutral, RMVPE counted once."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=69.0, unavailable=True)
    adj = adjudicate(p, wav, sr, None, [])
    win = adj["hypotheses"][0]
    assert win["group_scores"]["game"] == 0.0
    assert "game" not in adj["supporting_independence_groups"]
    assert "game" not in adj["opposing_independence_groups"]
    assert win["supporting"].get("game") is None
    assert win["opposing"].get("game") is None


def test_virtual_with_real_game_members_uses_real_tones():
    """B: real per-run member notes -> game group from real tones."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=69.0, run_tones=[69.0, 69.1, 68.9, 69.0])
    adj = adjudicate(p, wav, sr, None, [])
    win = adj["hypotheses"][0]
    assert win["group_scores"]["game"] == 1.0
    p2 = _vpkt(seed=69.0, run_tones=[69.0, 57.0, 69.0])
    adj2 = adjudicate(p2, wav, sr, None, [])
    g = [h for h in adj2["hypotheses"] if h["hypothesis"] == 69.0][0]
    assert abs(g["group_scores"]["game"] - 0.667) < 0.01


def test_seed_presence_does_not_create_game_evidence():
    """C: adding/removing the acoustic seed must not change whether
    GAME evidence exists."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=69.0, unavailable=True)
    a1 = adjudicate(p, wav, sr, None, [])["hypotheses"][0]
    p["candidate_written_pitch"] = 70.0      # different seed
    a2 = adjudicate(p, wav, sr, None, [])["hypotheses"][0]
    assert (a1["group_scores"]["game"] == a2["group_scores"]["game"]
            == 0.0)


# ---- §8.2: final_structure_clear before SAFE gate (production order) -----

def test_gate_reads_final_status_on_first_call():
    """Production-order regression: C resolved_keep has not run
    apply_structure yet, but the gate must already see finalized
    semantics — no second call needed."""
    p = _pkt(varies=True)
    p["consensus"].update({"presence_rate": 1.0, "tone_agreement": 1.0,
                           "stability": "GAME_STABLE"})
    p["dual_f0"] = {"extractors_agree": True, "both_oppose_game": True,
                    "game_vs_rmvpe_cents": 400, "game_vs_fcpe_cents": 410}
    p["rmvpe"] = {"iqr_cents": 20, "center_midi": 64.0}
    p["fcpe"] = {"iqr_cents": 20, "center_midi": 64.0}
    pl = [{"start": 10.0, "end": 10.4, "dur": 0.4, "center_midi": 64.0,
           "iqr_cents": 20}]
    # production order: gate FIRST (with C status), flag not yet set
    assert "final_structure_clear" not in p
    g = safe_retune_gate(p, pl, pl, [], target_midi=64.0,
                         final_structure_status="resolved_keep")
    assert g["gates"]["no_structure_ambiguity"] is True
    # and an unresolved C still blocks
    g2 = safe_retune_gate(p, pl, pl, [], target_midi=64.0,
                          final_structure_status="unresolved")
    assert g2["gates"]["no_structure_ambiguity"] is False


# ---- §8.3: RMVPE voiced-drop is not an independent boundary family -------

def test_voiced_drop_alone_cannot_split():
    """GAME stable 1-note + dual delta agree + RMVPE voiced drop +
    NO energy/onset boundary -> not TRUE_SPLIT."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[1, 1, 1, 1, 1])
    times, energy = _times_energy(10.0, 10.4)          # flat energy
    voiced = np.ones(len(times))                       # rmvpe mask dips:
    voiced[(times >= 10.16) & (times <= 10.24)] = 0    # at boundary
    adj = adjudicate_structure(p, times, energy,
                               ["dual_f0_multi_plateau"], voiced=voiced)
    assert adj["classification"] != "TRUE_SPLIT_CANDIDATE"
    # but the drop still boosts the RMVPE family (audit trail)
    assert adj["boundary_evidence"]["voiced_drop"] > 0


# ---- §8.5: missing extractor evidence is neutral -------------------------

def test_missing_extractor_is_neutral_for_h0():
    p = _pkt(pl_r=[], pl_f=[], counts=[1] * 5)
    times, energy = _times_energy(10.0, 10.4)
    adj = adjudicate_structure(p, times, energy, [])
    # artifact override -> unresolved, but H0 score must show no fake
    # extractor support: only game + acoustic + duration terms
    assert adj["all_scores"]["H0"] == pytest.approx(1 + 0 + 0 + 1 + 0.5)


def test_one_note_support_values():
    assert _one_note_support([]) == 0.0                  # missing
    assert _one_note_support(PL1) > 0.5                  # stable single
    small = [{"start": 10.0, "end": 10.2, "dur": 0.2, "center_midi": 60,
              "iqr_cents": 10},
             {"start": 10.2, "end": 10.4, "dur": 0.2, "center_midi": 60.2,
              "iqr_cents": 10}]
    assert _one_note_support(small) > 0.5                # tiny delta
    assert _one_note_support(PL2) == 0.0                 # 4st delta


# ---- §8.4: separation sensitivity on virtual notes -----------------------

def test_virtual_separation_field_carried_into_b():
    """A virtual packet's separation field must reach frozen B —
    sensitive + opposition -> unresolved (penalty applied)."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=69.0, unavailable=True)
    p["rmvpe"]["center_midi"] = 57.0        # extractor opposition
    p["separation"] = {"separation_sensitive": True,
                       "inherited_from_parent": True}
    adj = adjudicate(p, wav, sr, None, [])
    assert adj["separation_sensitive"] is True
