"""M2.3.2C structure adjudication tests (plan2 §10 matrix)."""
import numpy as np

from agent2utau.diagnostic.structure_adj import (
    discover_structure, adjudicate_structure, apply_structure)


def _pkt(start=10.0, dur=0.4, tone=60.0, pl_r=None, pl_f=None,
         counts=None, varies=False):
    return {"id": "note_0000", "start": start, "dur": dur,
            "game_tone": tone, "plateaus": pl_r or [],
            "fcpe_plateaus": pl_f or [],
            "consensus": {"structure_varies": varies,
                          "run_note_counts": counts or [1] * 5},
            "state": {"routing_needs": {"structure_adjudication": True,
                                       "pitch_adjudication": False,
                                       "phrase_review": False},
                      "decision": "needs_structure_adjudication"}}


def _times_energy(t0, t1, dip_at=None, fps=100.0):
    n = int((t1 - t0) * fps)
    times = t0 + np.arange(n) / fps
    energy = np.full(n, 0.5)
    if dip_at is not None:
        m = np.abs(times - dip_at) < 0.05
        energy[m] = 0.05
    return times, energy


PL2 = [{"start": 10.0, "end": 10.18, "dur": 0.18, "center_midi": 60.0},
       {"start": 10.20, "end": 10.40, "dur": 0.20, "center_midi": 64.0}]
PL1 = [{"start": 10.0, "end": 10.40, "dur": 0.40, "center_midi": 60.0}]


# ---- 10.2: independent discovery --------------------------------------

def test_discovery_dual_f0_two_plateau_without_structure_varies():
    """§10.2.5/6: GAME-stable one-note + dual-F0 two-plateau -> in C."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[1, 1, 1, 1, 1], varies=False)
    times, energy = _times_energy(10.0, 10.4)
    d = discover_structure([p], times, energy)
    assert p["id"] in d
    assert "dual_f0_multi_plateau" in d[p["id"]]
    assert "cross_extractor_changepoint" in d[p["id"]]


def test_discovery_plain_stable_note_not_flagged():
    """§10.2.7: ordinary stable notes should not be over-flagged."""
    p = _pkt(pl_r=PL1, pl_f=PL1)
    times, energy = _times_energy(10.0, 10.4)
    assert discover_structure([p], times, energy) == {}


def test_discovery_long_merged_note():
    p = _pkt(dur=1.3, pl_r=PL1 * 2)
    times, energy = _times_energy(10.0, 11.3)
    d = discover_structure([p], times, energy)
    assert "long_note_multi_plateau" in d[p["id"]]


# ---- 10.1/10.4: adjudication outcomes ---------------------------------

def test_true_split_candidate_dual_plateau_plus_dip():
    """Dual-plateau agreement + energy dip + GAME variance -> split."""
    p = _pkt(pl_r=PL2, pl_f=PL2, counts=[1, 2, 1, 2, 1], varies=True)
    times, energy = _times_energy(10.0, 10.4, dip_at=10.20)
    adj = adjudicate_structure(p, times, energy,
                               ["dual_f0_multi_plateau"])
    assert adj["status"] == "resolved_change_candidate"
    assert adj["classification"] == "TRUE_SPLIT_CANDIDATE"
    assert adj["boundary"] == 10.20


def test_reverse_stochastic_split_acoustic_one_note():
    """§10.3.8: GAME sometimes splits but acoustics say one note."""
    p = _pkt(pl_r=PL1, pl_f=PL1, counts=[1, 2, 1, 1, 1], varies=True)
    times, energy = _times_energy(10.0, 10.4)
    adj = adjudicate_structure(p, times, energy, [])
    assert adj["status"] == "resolved_keep"
    assert adj["classification"] in ("RESOLVED_KEEP",
                                     "ONE_NOTE_WITH_PORTAMENTO")


def test_true_merge_candidate_short_note_continuity():
    """Very short note whose plateau continues into the neighbour."""
    nb = {"id": "note_0001", "start": 10.05, "dur": 0.35,
          "plateaus": [{"start": 10.05, "end": 10.40, "dur": 0.35,
                        "center_midi": 60.2}],
          "fcpe_plateaus": [{"start": 10.05, "end": 10.40, "dur": 0.35,
                             "center_midi": 60.1}]}
    p = _pkt(dur=0.05,
             pl_r=[{"start": 10.0, "end": 10.05, "dur": 0.05,
                    "center_midi": 60.1}],
             pl_f=[{"start": 10.0, "end": 10.05, "dur": 0.05,
                    "center_midi": 60.0}],
             counts=[1, 1, 1, 1, 1])
    times, energy = _times_energy(10.0, 10.4)
    adj = adjudicate_structure(p, times, energy, ["very_short_note"],
                               neighbors=[nb])
    assert adj["status"] == "resolved_change_candidate"
    assert adj["classification"] == "TRUE_MERGE_CANDIDATE"
    assert adj["hypothesis_detail"]["span"]["merge_with"] == "note_0001"


def test_artifact_when_no_plateau_evidence():
    p = _pkt(pl_r=[], pl_f=[], counts=[1, 2, 1, 1, 1], varies=True)
    times, energy = _times_energy(10.0, 10.4)
    adj = adjudicate_structure(p, times, energy, [])
    assert adj["status"] == "unresolved"
    assert adj["classification"] == "ALIGNMENT_ARTIFACT"


# ---- 10.4: C <-> frozen-B lifecycle ------------------------------------

def test_apply_resolved_keep_finalizes_provisional_b():
    """§8.1: C resolved_keep must finalize the provisional B result."""
    p = _pkt()
    p["state"]["routing_needs"]["pitch_adjudication"] = True
    p["pitch_adjudication"] = {"status": "resolved_keep",
                               "provisional": True,
                               "winning_hypothesis": 64.0}
    apply_structure(p, {"status": "resolved_keep",
                        "hypothesis_detail": None})
    assert p["pitch_adjudication"]["provisional"] is False
    assert p["pitch_adjudication"]["finalized_by"] == \
        "structure_resolved_keep"
    needs = p["state"]["routing_needs"]
    assert needs["structure_adjudication"] is False
    assert needs["pitch_adjudication"] is False
    assert p["state"]["decision"] == "auto_resolved"


def test_apply_resolved_keep_unresolved_b_goes_to_review():
    """A provisional UNRESOLVED B finalized by C resolved_keep must land
    in phrase_review — a contested pitch may not silently keep_baseline."""
    p = _pkt()
    p["state"]["routing_needs"]["pitch_adjudication"] = True
    p["pitch_adjudication"] = {"status": "unresolved",
                               "provisional": True}
    apply_structure(p, {"status": "resolved_keep",
                        "hypothesis_detail": None})
    assert p["state"]["routing_needs"]["phrase_review"] is True
    assert p["state"]["decision"] == "needs_phrase_review"


def test_apply_resolved_keep_finalizes_change_through_gate():
    """resolved_change provisional B + confirmed structure + eligible
    frozen gate -> repair_candidate (the only repair path)."""
    p = _pkt()
    p["state"]["routing_needs"]["pitch_adjudication"] = True
    p["pitch_adjudication"] = {"status": "resolved_change",
                               "provisional": True,
                               "winning_hypothesis": 64.0}
    apply_structure(p, {"status": "resolved_keep",
                        "hypothesis_detail": None},
                    b_gate={"eligible": True})
    assert p["state"]["decision"] == "repair_candidate"
    assert p["repair_gate"]["eligible"] is True


def test_apply_resolved_keep_change_without_gate_demoted():
    """resolved_change finalized but gate fails -> unresolved + review,
    never a silent repair."""
    p = _pkt()
    p["state"]["routing_needs"]["pitch_adjudication"] = True
    p["pitch_adjudication"] = {"status": "resolved_change",
                               "provisional": True}
    apply_structure(p, {"status": "resolved_keep",
                        "hypothesis_detail": None},
                    b_gate={"eligible": False, "failed": ["x"]})
    assert p["pitch_adjudication"]["status"] == "unresolved"
    assert "finalized_change_needs_gate" in \
        p["pitch_adjudication"]["reason"]
    assert p["state"]["decision"] == "needs_phrase_review"


def test_apply_change_candidate_invalidates_old_b():
    """§8.2: structure change invalidates the old B result entirely."""
    p = _pkt()
    p["pitch_adjudication"] = {"status": "resolved_change",
                               "provisional": True,
                               "winning_hypothesis": 64.0}
    apply_structure(p, {"status": "resolved_change_candidate",
                        "hypothesis_detail": {"kind": "split",
                                              "boundary": 10.2}})
    assert p["pitch_adjudication"]["status"] == "invalidated"
    assert p["pitch_adjudication"]["invalidated_by_structure"] is True
    assert p["pitch_adjudication"]["old_winning_hypothesis"] == 64.0
    assert "winning_hypothesis" not in p["pitch_adjudication"]
    assert p["state"]["decision"] == "needs_phrase_review"


def test_apply_unresolved_clears_pending_no_loop():
    """§8.3: unresolved must not leave structure pending (no C loop)."""
    p = _pkt()
    p["pitch_adjudication"] = {"status": "resolved_change",
                               "provisional": True}
    apply_structure(p, {"status": "unresolved",
                        "hypothesis_detail": None})
    needs = p["state"]["routing_needs"]
    assert needs["structure_adjudication"] is False
    assert p["pitch_adjudication"]["provisional"] is False
    assert p["pitch_adjudication"]["blocked_by_unresolved_structure"]
    assert p["state"]["decision"] == "needs_phrase_review"
