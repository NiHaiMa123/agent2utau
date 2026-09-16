"""M2.3.2B regressions: hypothesis-based pitch/octave adjudication."""
import numpy as np

from agent2utau.diagnostic.adjudicate import (adjudicate,
                                            apply_adjudication,
                                            hypotheses)
from agent2utau.diagnostic.triage import orthogonal_states

SR = 8000


def _seg(midi, dur=0.5, sr=SR, noise=0.02):
    """Synthesize a harmonic tone at `midi` for waveform evidence."""
    f0 = 440.0 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(sr * dur)) / sr
    rng = np.random.default_rng(0)
    s = sum(np.sin(2 * np.pi * k * f0 * t) / k for k in range(1, 7))
    return (s * 0.4 + rng.normal(0, noise, len(t))).astype(np.float64)


def _wav_for(midi, t0=0.0, dur=0.5, sr=SR):
    wav = np.zeros(int(sr * (t0 + dur + 0.1)))
    seg = _seg(midi, dur, sr)
    wav[int(t0 * sr):int(t0 * sr) + len(seg)] = seg
    return wav


def _pkt(game_tone=69.96, start=0.0, dur=0.5, run_tones=None,
         rmvpe=69.96, fcpe=58.03, dual_delta=-1193.0, **kw):
    p = {"id": "n0", "start": start, "dur": dur, "game_tone": game_tone,
         "flags": [], "plateaus": [{"center_midi": rmvpe}] if rmvpe else [],
         "rmvpe": ({"center_midi": rmvpe, "iqr_cents": 10,
                   "voiced_coverage": 1.0} if rmvpe is not None else {}),
         "fcpe": ({"center_midi": fcpe, "iqr_cents": 10,
                  "voiced_coverage": 1.0} if fcpe is not None else {}),
         "dual_f0": {"rmvpe_vs_fcpe_cents": dual_delta,
                     "extractors_agree": False, "both_oppose_game": False},
         "consensus": {"stability": "GAME_STABLE", "tone_agreement": 1.0,
                       "presence_rate": 1.0, "structure_varies": False,
                       "run_tones": run_tones or [game_tone] * 5,
                       "run_note_counts": [1] * 5}}
    p.update(kw)
    return p


def test_b1_extractor_conflict_resolved_by_waveform_not_majority():
    # 189s-like: RMVPE says 70, FCPE says 58 (one octave apart). A clean
    # tone at 58 => periodicity+harmonic converge on the LOWER octave —
    # extractor majority (game+rmvpe on 70) must not dominate.
    wav = _wav_for(58.0)
    p = _pkt()
    adj = adjudicate(p, wav, SR, None, [])
    assert adj["extractor_conflict"] is True
    assert abs(adj["winning_hypothesis"] - 58.0) < 1.0
    assert "periodicity" in adj["evidence_families"]
    assert adj["status"] == "resolved_change"


def test_b1b_extractor_conflict_noise_cannot_be_majority_fixed():
    # Same conflict but the waveform carries no pitch evidence (noise) —
    # periodicity counter-evidence => unresolved, never majority vote.
    rng = np.random.default_rng(1)
    wav = rng.normal(0, 0.3, int(SR * 0.6))
    p = _pkt()
    adj = adjudicate(p, wav, SR, None, [])
    assert adj["status"] == "unresolved"


def test_b2_game_distribution_consumed_continuously():
    # 202s-like: GAME answered 65.3 in 2/5 runs, 72.4 in 3/5.
    wav = _wav_for(72.4)
    p = _pkt(game_tone=72.4, rmvpe=72.3, fcpe=72.31, dual_delta=10.0,
             run_tones=[65.3, 65.3, 72.4, 72.4, 72.4])
    p["dual_f0"]["extractors_agree"] = True
    adj = adjudicate(p, wav, SR, None, [])
    by_hyp = {h["hypothesis"]: h for h in adj["hypotheses"]}
    assert abs(by_hyp[72.4]["game_support_ratio"] - 0.6) < 1e-6
    assert abs(by_hyp[65.3]["game_support_ratio"] - 0.4) < 1e-6
    assert adj["status"] == "resolved_keep"
    assert adj["winning_hypothesis"] == 72.4


def test_b3_game_5of5_vs_3of5_changes_confidence():
    wav = _wav_for(70.0)
    strong = _pkt(game_tone=70.0, rmvpe=70.0, fcpe=70.0, dual_delta=1.0,
                  run_tones=[70.0] * 5)
    weak = _pkt(game_tone=70.0, rmvpe=70.0, fcpe=70.0, dual_delta=1.0,
                run_tones=[70.0, 70.0, 70.0, 58.0, 58.0])
    a = adjudicate(strong, wav, SR, None, [])
    b = adjudicate(weak, wav, SR, None, [])
    assert a["confidence"] > b["confidence"]


def test_b4_separation_sensitive_lowers_confidence_only():
    wav = _wav_for(70.0)
    clean = _pkt(game_tone=70.0, rmvpe=70.0, fcpe=70.0, dual_delta=1.0)
    sens = _pkt(game_tone=70.0, rmvpe=70.0, fcpe=70.0, dual_delta=1.0,
                separation={"separation_sensitive": True})
    a = adjudicate(clean, wav, SR, None, [])
    b = adjudicate(sens, wav, SR, None, [])
    assert b["confidence"] < a["confidence"]
    # sensitivity never picks a different winner by itself
    assert a["winning_hypothesis"] == b["winning_hypothesis"]


def test_b5_third_f0_missing_is_not_opposition():
    # pYIN absent/low-confidence => no third_f0 in opposing families.
    wav = _wav_for(70.0)
    p = _pkt(game_tone=70.0, rmvpe=70.0, fcpe=70.0, dual_delta=1.0)
    adj = adjudicate(p, wav, SR, None, [])
    for h in adj["hypotheses"]:
        assert "third_f0" not in h["opposing"]


def test_b6_pitch_resolution_never_clears_structure_need():
    rec = _pkt()
    rec["state"] = orthogonal_states(
        {**rec, "consensus": {"stability": "GAME_UNSTABLE",
                              "structure_varies": True,
                              "tone_agreement": 1.0,
                              "run_note_counts": [2, 1, 1, 1, 2]}})
    assert rec["state"]["routing_needs"]["structure_adjudication"]
    adj = {"status": "resolved_keep", "winning_hypothesis": 69.96,
           "confidence": 3.0, "margin": 1.0}
    apply_adjudication(rec, adj, None)
    st = rec["state"]
    assert st["routing_needs"]["structure_adjudication"] is True
    assert st["routing_needs"]["pitch_adjudication"] is False
    assert st["decision"] == "needs_structure_adjudication"


def test_b7_unresolved_does_not_loop_back_to_b():
    rec = _pkt()
    rec["state"] = {"routing_needs": {"pitch_adjudication": True,
                                    "structure_adjudication": False,
                                    "phrase_review": False},
                    "decision": "needs_pitch_adjudication"}
    adj = {"status": "unresolved"}
    apply_adjudication(rec, adj, None)
    st = rec["state"]
    assert st["routing_needs"]["pitch_adjudication"] is False
    assert st["routing_needs"]["phrase_review"] is True
    assert st["decision"] == "needs_phrase_review"


def test_b8_b_result_never_overwrites_candidate0():
    rec = _pkt(game_tone=69.96)
    rec["state"] = {"routing_needs": {"pitch_adjudication": True,
                                    "structure_adjudication": False,
                                    "phrase_review": False},
                    "decision": "needs_pitch_adjudication"}
    adj = {"status": "resolved_change", "winning_hypothesis": 58.0}
    apply_adjudication(rec, adj, {"eligible": False, "failed": ["g1"]})
    assert rec["game_tone"] == 69.96            # baseline untouched
    assert adj["status"] == "unresolved"        # gate failed -> demoted
    assert "repair_gate_failed:g1" in adj["reason"]
    assert rec["state"]["decision"] == "needs_phrase_review"


def test_b_hypotheses_include_game_octaves_and_extractors():
    p = _pkt(game_tone=69.96, rmvpe=69.96, fcpe=58.03)
    hs = hypotheses(p, 58.1)
    assert 69.96 in hs
    assert any(abs(h - 57.96) < 0.6 for h in hs)   # lower octave
    assert any(abs(h - 81.96) < 0.6 for h in hs)   # upper octave
    assert any(abs(h - 58.03) < 0.6 for h in hs)   # fcpe alternative
