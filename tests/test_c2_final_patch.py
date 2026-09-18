"""C2 final correctness patch regressions (plan2 §8.1-8.5, §9 matrix)."""
import numpy as np
import pytest

from agent2utau.diagnostic.adjudicate import adjudicate
from agent2utau.diagnostic.structure_adj import (
    adjudicate_structure, apply_structure, _one_note_support,
    virtual_game_correspondence)
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
    # extractor support — and no fake acoustic support either: with no
    # boundary observation the acoustic_boundary group is neutral 0
    # (pre-M2.5: 1-nonf0 on missing evidence was a bug).
    assert adj["all_scores"]["H0"] == pytest.approx(1 + 0 + 0 + 0 + 0.5)
    assert adj["boundary_evidence"]["available"] is False


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


# ---- §9.3: identity-aware virtual GAME correspondence ------------------
#
# Parent [10.0,10.4] split at 10.2 -> child A [10.0,10.2] / B [10.2,10.4].
# Runs keep {str(i): [[start,end,tone], ...]} REAL per-run GAME notes.

def _b_game(p, hyp):
    wav, sr = _audio(f=440)
    adj = adjudicate(p, wav, sr, None, [])
    return [h for h in adj["hypotheses"]
            if abs(h["hypothesis"] - hyp) <= 0.5][0], adj


def test_38_parent_spanning_note_cannot_vote_for_children():
    """§9.5.38: 4 runs keep one long note across the candidate split
    boundary + 1 run truly splits -> the long notes are anti-split
    STRUCTURE evidence, never child pitch votes; GAME support keeps
    the 5-run denominator instead of renormalizing to 1/1."""
    runs = {"0": [[10.0, 10.4, 60.0]],
            "1": [[10.0, 10.4, 60.0]],
            "2": [[10.0, 10.4, 60.0]],
            "3": [[10.0, 10.4, 64.0]],
            "4": [[10.0, 10.2, 60.0], [10.2, 10.4, 64.0]]}
    cA = virtual_game_correspondence("split", 10.0, 10.2, runs, 5,
                                     boundary=10.2, seed=60.0)
    cB = virtual_game_correspondence("split", 10.2, 10.4, runs, 5,
                                     boundary=10.2, seed=64.0)
    for c, tone in ((cA, 60.0), (cB, 64.0)):
        cls = [v["class"] for v in c["per_run"].values()]
        assert cls.count("child_identity_match") == 1
        assert cls.count("parent_spanning_note") == 4
        assert c["n_total_runs"] == 5 and c["n_present"] == 1
        assert c["child_presence_rate"] == 0.2
        assert c["conditional_tone_support"] == 1.0
        assert c["effective_game_support"] == 0.2
        assert c["present_tones"] == [tone]
        # matched member identity is recorded for audit
        assert c["per_run"]["4"]["member_ref"] == "run4[0]" or \
            c["per_run"]["4"]["member_ref"] == "run4[1]"
    # frozen B consumes the denominator-preserving support
    p = _vpkt(seed=60.0, run_tones=cA["present_tones"])
    p["consensus"]["virtual_correspondence"] = cA
    h, _adj = _b_game(p, 60.0)
    assert h["group_scores"]["game"] == pytest.approx(0.2)
    assert h["game_support_ratio"] == pytest.approx(0.2)


def test_39_all_runs_split_support_reflects_tone_agreement():
    """§9.5.39: 5/5 runs truly split; child tone 4/5一致 ->
    presence=5/5, GAME pitch support = 4/5 (not 1.0, not 4/4)."""
    runs = {str(i): [[10.0, 10.2, 60.0], [10.2, 10.4, 64.0]]
            for i in range(4)}
    runs["4"] = [[10.0, 10.2, 60.0], [10.2, 10.4, 62.0]]
    cB = virtual_game_correspondence("split", 10.2, 10.4, runs, 5,
                                     boundary=10.2, seed=64.0)
    assert cB["n_present"] == 5 and cB["child_presence_rate"] == 1.0
    assert cB["conditional_tone_support"] == 0.8
    assert cB["effective_game_support"] == 0.8
    p = _vpkt(seed=64.0, run_tones=cB["present_tones"])
    p["consensus"]["virtual_correspondence"] = cB
    h, _adj = _b_game(p, 64.0)
    assert h["group_scores"]["game"] == pytest.approx(0.8)
    # the dissenting present run is real pitch opposition (1/5)
    assert h["game_opposition"] == pytest.approx(0.2)


def test_40_partial_presence_never_renormalized():
    """§9.5.40: only 2/5 runs produce the child identity, 2/2 agree ->
    conditional=1.0, presence=0.4, effective=0.4 — never 1.0. Absent
    runs are pitch-neutral, not opposition."""
    runs = {"0": [[10.0, 10.4, 61.0]],
            "1": [[10.0, 10.4, 61.0]],
            "2": [[10.0, 10.4, 61.0]],
            "3": [[10.0, 10.2, 60.0], [10.2, 10.4, 64.0]],
            "4": [[10.0, 10.2, 60.0], [10.2, 10.4, 64.0]]}
    cB = virtual_game_correspondence("split", 10.2, 10.4, runs, 5,
                                     boundary=10.2, seed=64.0)
    assert cB["n_present"] == 2
    assert cB["child_presence_rate"] == 0.4
    assert cB["conditional_tone_support"] == 1.0
    assert cB["effective_game_support"] == 0.4
    p = _vpkt(seed=64.0, run_tones=cB["present_tones"])
    p["consensus"]["virtual_correspondence"] = cB
    h, _adj = _b_game(p, 64.0)
    assert h["group_scores"]["game"] == pytest.approx(0.4)
    assert h["game_opposition"] == pytest.approx(0.0)


def test_41_merge_long_member_is_merged_identity():
    """§9.5.41: merge candidate — a real GAME note spanning the removed
    internal boundary IS the merged virtual identity (the opposite
    semantics from split) and must not be excluded by split rules."""
    # A[10.0,10.05] + B[10.05,10.4] -> virtual [10.0,10.4], removed
    # boundary = 10.05
    runs = {"0": [[10.0, 10.4, 60.0]],                  # merged
            "1": [[9.98, 10.42, 60.1]],                # merged (edge tol)
            "2": [[10.0, 10.05, 60.0], [10.05, 10.4, 60.0]],
            "3": [[10.0, 10.4, 60.2]],
            "4": [[10.3, 10.5, 60.0]]}                 # no correspondence
    c = virtual_game_correspondence("merge", 10.0, 10.4, runs, 5,
                                    boundary=10.05, seed=60.0)
    per = c["per_run"]
    assert per["0"]["class"] == "child_identity_match"
    assert per["1"]["class"] == "child_identity_match"
    assert per["3"]["class"] == "child_identity_match"
    assert per["2"]["class"] == "parent_spanning_note"
    assert per["2"]["detail"] == "internal_boundary_kept"
    assert per["4"]["class"] in ("ambiguous", "absent")
    assert c["n_present"] == 3 and c["child_presence_rate"] == 0.6


def test_42_ordinary_candidate0_game_semantics_unchanged():
    """§9.5.42: a non-virtual packet keeps frozen-B GAME semantics —
    mean over run_tones, opposition = 1 - support."""
    wav, sr = _audio(f=440)
    p = _vpkt(seed=69.0, run_tones=[69.0, 69.0, 69.0, 64.0])
    # no virtual_correspondence -> ordinary Candidate 0 path
    adj = adjudicate(p, wav, sr, None, [])
    h69 = [h for h in adj["hypotheses"]
           if h["hypothesis"] == 69.0][0]
    h64 = [h for h in adj["hypotheses"]
           if h["hypothesis"] == 64.0][0]
    assert h69["group_scores"]["game"] == pytest.approx(0.75)
    assert h64["group_scores"]["game"] == pytest.approx(0.25)
    assert h69["game_opposition"] is None      # legacy derivation


def test_split_compatible_internal_boundary_counts():
    """A run that split at its own edge compatible with the candidate
    boundary (within tolerance) DID produce the child identity — its
    tone is a real vote, not anti-split evidence."""
    runs = {"0": [[10.0, 10.26, 60.0], [10.26, 10.4, 64.0]],
            "1": [[10.0, 10.4, 60.0]]}
    cA = virtual_game_correspondence("split", 10.0, 10.2, runs, 2,
                                     boundary=10.2, seed=60.0)
    assert cA["per_run"]["0"]["class"] == "child_identity_match"
    assert cA["per_run"]["0"]["detail"] == "internal_boundary_compatible"
    assert cA["per_run"]["1"]["class"] == "parent_spanning_note"
    cB = virtual_game_correspondence("split", 10.2, 10.4, runs, 2,
                                     boundary=10.2, seed=64.0)
    assert cB["per_run"]["0"]["class"] == "child_identity_match"
    assert cB["present_tones"] == [64.0]
