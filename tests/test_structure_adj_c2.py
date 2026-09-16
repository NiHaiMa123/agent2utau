"""M2.3.2C2 calibration regressions (plan2 §9 matrix)."""
import numpy as np

from agent2utau.diagnostic.structure_adj import (
    discover_structure, adjudicate_structure, apply_structure,
    _split_support, _extractor_evidence, _boundary_energy)
from agent2utau.diagnostic.triage import safe_retune_gate

from test_structure_adj import _pkt, _times_energy, PL1, PL2


# ---- 9.2 split correctness ---------------------------------------------

def test_two_plateaus_alone_not_full_support():
    """§9.2.9: two plateaus with a tiny delta -> graded, not full."""
    small = [{"start": 10.0, "end": 10.18, "dur": 0.18,
              "center_midi": 60.0, "iqr_cents": 20},
             {"start": 10.20, "end": 10.40, "dur": 0.20,
              "center_midi": 60.3, "iqr_cents": 20}]
    ev = _extractor_evidence(small)
    assert ev is not None
    assert _split_support(ev) == 0.0          # 0.3st < MIN delta
    big = [dict(small[0]), {**small[1], "center_midi": 64.0}]
    assert _split_support(_extractor_evidence(big)) > 0.5


def test_small_delta_not_true_split():
    """§9.2.12: 0.3st wobble with changepoint agreement -> no split."""
    small_r = [{"start": 10.0, "end": 10.18, "dur": 0.18,
                "center_midi": 60.0, "iqr_cents": 15},
               {"start": 10.20, "end": 10.40, "dur": 0.20,
                "center_midi": 60.3, "iqr_cents": 15}]
    small_f = [dict(small_r[0]), {**small_r[1], "center_midi": 60.4}]
    p = _pkt(pl_r=small_r, pl_f=small_f, counts=[1, 2, 1, 2, 1],
             varies=True)
    times, energy = _times_energy(10.0, 10.4, dip_at=10.20)
    adj = adjudicate_structure(p, times, energy, ["dual_f0_multi_plateau"])
    assert adj["classification"] != "TRUE_SPLIT_CANDIDATE"


def test_f0_only_changepoint_cannot_auto_split():
    """§9.2.15: dual-F0 agreement but NO non-F0 boundary evidence and
    weak GAME split support -> not a high-confidence split."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[1, 1, 1, 1, 1])   # GAME stable 1
    times, energy = _times_energy(10.0, 10.4)             # flat energy
    adj = adjudicate_structure(p, times, energy,
                               ["dual_f0_multi_plateau"])
    # H1 may outscore but the §8.4 gate must block TRUE_SPLIT
    assert adj["classification"] != "TRUE_SPLIT_CANDIDATE"


def test_strong_game_split_plus_f0_agree_is_split():
    """§9.2.13: stable two-note synthetic (GAME splits 60%, dual delta
    agree, boundary dip) -> TRUE_SPLIT_CANDIDATE."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[2, 2, 1, 2, 2], varies=True)
    times, energy = _times_energy(10.0, 10.4, dip_at=10.20)
    adj = adjudicate_structure(p, times, energy,
                               ["dual_f0_multi_plateau",
                                "cross_extractor_changepoint"])
    assert adj["classification"] == "TRUE_SPLIT_CANDIDATE"
    assert adj["status"] == "resolved_change_candidate"


def test_portamento_wins_without_boundary_evidence():
    """§9.2.14: dual-F0 changepoint but no non-F0 boundary family and
    GAME keeps one note -> portamento/ornament, not split."""
    # GAME says one note in all runs; delta present; flat energy
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[1, 1, 1, 1, 1])
    times, energy = _times_energy(10.0, 10.4)
    adj = adjudicate_structure(p, times, energy, [])
    assert adj["classification"] in ("ONE_NOTE_WITH_PORTAMENTO",
                                     "GRACE_OR_ORNAMENT",
                                     "UNRESOLVED_STRUCTURE")
    assert adj["classification"] != "TRUE_SPLIT_CANDIDATE"


def test_dual_delta_fields_present():
    """§9.2.10/11: direction/magnitude/boundary-time agreement computed."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[2] * 5, varies=True)
    times, energy = _times_energy(10.0, 10.4, dip_at=10.2)
    adj = adjudicate_structure(p, times, energy, [])
    d = adj["extractor_evidence"]["dual_delta"]
    assert d["direction_agreement"] is True
    assert d["magnitude_difference_st"] == 0.0
    assert d["boundary_time_delta_ms"] == 0.0
    assert adj["extractor_evidence"]["dual_delta_agreement"] is True


# ---- 9.3 boundary evidence ----------------------------------------------

def test_boundary_energy_is_local():
    """§9.3.16/17: a dip far from the candidate boundary is not
    evidence; a dip AT the boundary is."""
    times, energy = _times_energy(10.0, 10.4, dip_at=10.02)  # far
    far = _boundary_energy(times, energy, 10.20, 10.0, 10.4)
    times, energy = _times_energy(10.0, 10.4, dip_at=10.20)  # at b
    near = _boundary_energy(times, energy, 10.20, 10.0, 10.4)
    assert near["support"] > far["support"]
    assert near["support"] > 0.5


def test_discovery_energy_reason_needs_candidate_boundary():
    """§8.5: no candidate boundary -> energy dip alone is not a reason."""
    p = _pkt(pl_r=PL1, pl_f=PL1)
    times, energy = _times_energy(10.0, 10.4, dip_at=10.2)
    d = discover_structure([p], times, energy)
    assert p["id"] not in d


# ---- 9.4 merge ------------------------------------------------------------

def test_merge_support_from_member_spans():
    """§9.4.21: a run's real GAME note crossing the shared boundary =
    merge support; member_spans drive it, not run_note_counts."""
    p = _pkt(dur=0.05,
             pl_r=[{"start": 10.0, "end": 10.05, "dur": 0.05,
                    "center_midi": 60.1}],
             pl_f=[{"start": 10.0, "end": 10.05, "dur": 0.05,
                    "center_midi": 60.0}])
    p["consensus"]["member_spans"] = {
        "0": [[10.0, 10.4]], "1": [[10.0, 10.4]],
        "2": [[10.0, 10.05], [10.05, 10.4]],
        "3": [[10.0, 10.4]], "4": [[10.0, 10.05], [10.05, 10.4]]}
    p["consensus"]["n_runs"] = 5
    nb = {"id": "note_0001", "start": 10.05, "dur": 0.35,
          "plateaus": [{"start": 10.05, "end": 10.40, "dur": 0.35,
                        "center_midi": 60.2}],
          "fcpe_plateaus": [{"start": 10.05, "end": 10.40, "dur": 0.35,
                             "center_midi": 60.1}]}
    times, energy = _times_energy(10.0, 10.4)
    adj = adjudicate_structure(p, times, energy, ["very_short_note"],
                               neighbors=[nb])
    assert adj["classification"] == "TRUE_MERGE_CANDIDATE"
    # 3/5 runs had one note crossing the 10.05 boundary
    assert adj["all_scores"]["H2"] > 0


def test_count_zero_is_not_merge_support():
    """§9.4.20/23: run_note_counts==0 (gap/absence) must not count as
    GAME merge support."""
    p = _pkt(dur=0.05,
             pl_r=[{"start": 10.0, "end": 10.05, "dur": 0.05,
                    "center_midi": 60.1}],
             pl_f=[{"start": 10.0, "end": 10.05, "dur": 0.05,
                    "center_midi": 60.0}],
             counts=[0, 0, 1, 1, 1])      # zeros = absence, NOT merge
    p["consensus"]["member_spans"] = {"2": [[10.0, 10.05]],
                                      "3": [[10.0, 10.05]],
                                      "4": [[10.0, 10.05]]}
    p["consensus"]["n_runs"] = 5
    from agent2utau.diagnostic.structure_adj import _game_merge_support
    nb = {"id": "n", "start": 10.05, "dur": 0.3, "plateaus": []}
    assert _game_merge_support(p, [nb]) == 0.0


# ---- 9.5 final gate semantics --------------------------------------------

def test_final_structure_clear_unblocks_gate():
    """§9.5.24: C resolved_keep sets final_structure_clear; the safe
    gate must not be permanently blocked by raw structure_varies."""
    p = _pkt(varies=True)
    p["consensus"]["presence_rate"] = 1.0
    p["consensus"]["tone_agreement"] = 1.0
    p["consensus"]["stability"] = "GAME_STABLE"
    p["dual_f0"] = {"extractors_agree": True, "both_oppose_game": True,
                    "game_vs_rmvpe_cents": 400, "game_vs_fcpe_cents": 410}
    p["rmvpe"] = {"iqr_cents": 20, "center_midi": 64.0}
    p["fcpe"] = {"iqr_cents": 20, "center_midi": 64.0}
    pl = [{"start": 10.0, "end": 10.4, "dur": 0.4, "center_midi": 64.0,
           "iqr_cents": 20}]
    g1 = safe_retune_gate(p, pl, pl, [], target_midi=64.0)
    assert g1["gates"]["no_structure_ambiguity"] is False
    apply_structure(p, {"status": "resolved_keep",
                        "hypothesis_detail": None})
    g2 = safe_retune_gate(p, pl, pl, [], target_midi=64.0)
    assert p["final_structure_clear"] is True
    assert g2["gates"]["no_structure_ambiguity"] is True
    assert p["consensus"]["structure_varies"] is True   # audit kept


# ---- 9.1 lifecycle: virtual-note B results drive routing ------------------

def test_change_candidate_virtual_b_resolved_no_review():
    """§9.1.6: all virtual-note B resolved -> no phrase_review."""
    p = _pkt()
    p["pitch_adjudication"] = {"status": "resolved_change",
                               "provisional": True,
                               "winning_hypothesis": 64.0}
    apply_structure(
        p, {"status": "resolved_change_candidate",
            "hypothesis_detail": {"kind": "split", "boundary": 10.2}},
        virtual_b=[{"status": "resolved_keep"},
                   {"status": "resolved_keep"}])
    assert p["state"]["decision"] == "resolved_change_candidate"
    assert p["state"]["routing_needs"]["phrase_review"] is False
    assert p["pitch_adjudication"]["status"] == "invalidated"


def test_change_candidate_virtual_b_unresolved_goes_review():
    """§9.1.6: any unresolved virtual B -> phrase_review."""
    p = _pkt()
    p["pitch_adjudication"] = {"status": "resolved_keep",
                               "provisional": True}
    apply_structure(
        p, {"status": "resolved_change_candidate",
            "hypothesis_detail": {"kind": "split", "boundary": 10.2}},
        virtual_b=[{"status": "resolved_keep"},
                   {"status": "unresolved"}])
    assert p["state"]["decision"] == "needs_phrase_review"
