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
    # tone at 58 => waveform group converges on the LOWER octave, but a
    # genuine game+rmvpe vs fcpe+waveform tie must NOT auto-resolve —
    # unresolved is the honest answer, majority vote is forbidden.
    wav = _wav_for(58.0)
    p = _pkt()
    adj = adjudicate(p, wav, SR, None, [])
    assert adj["extractor_conflict"] is True
    low = [h for h in adj["hypotheses"]
           if abs(h["hypothesis"] - 58.0) <= 0.5][0]
    assert low["group_scores"]["waveform"] > 0.5   # waveform saw truth
    assert low["group_scores"]["fcpe"] > 0.5
    assert adj["status"] == "unresolved"           # no majority fix
    assert adj["winning_hypothesis"] is not None


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
    # B2 §9.1: pitch result is provisional while structure unresolved;
    # the pitch need stays set for the post-C re-run, and structure
    # adjudication is never cleared by a pitch outcome.
    assert adj["provisional"] is True
    assert st["routing_needs"]["structure_adjudication"] is True
    assert st["routing_needs"]["pitch_adjudication"] is True
    assert st["decision"] == "needs_structure_adjudication"


def test_b6b_pitch_only_resolution_clears_need():
    rec = _pkt(dual_delta=2.0)
    rec["dual_f0"]["extractors_agree"] = True
    rec["state"] = {"routing_needs": {"pitch_adjudication": True,
                                    "structure_adjudication": False,
                                    "phrase_review": False},
                    "decision": "needs_pitch_adjudication"}
    adj = {"status": "resolved_keep", "winning_hypothesis": 69.96}
    apply_adjudication(rec, adj, None)
    st = rec["state"]
    assert st["routing_needs"]["pitch_adjudication"] is False
    assert st["decision"] == "auto_resolved"


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


# ---------------- B2 correctness / calibration ----------------------------

def test_b2_structure_ambiguous_run_tones_not_hypotheses():
    # §9.1: aggregate run_tones over split/merge members are not real
    # written notes — excluded when structure_varies.
    p = _pkt(game_tone=62.0, run_tones=[60.0, 64.0, 62.0])
    p["consensus"]["structure_varies"] = True
    hs = hypotheses(p, None)
    assert 60.0 not in hs and 64.0 not in hs
    # without structure ambiguity they ARE candidates
    p["consensus"]["structure_varies"] = False
    hs = hypotheses(p, None)
    assert 60.0 in hs and 64.0 in hs


def test_b2_mirror_octave_true_low():
    # true = 58 -> winner 58 (not pushed to 70)
    wav = _wav_for(58.0)
    p = _pkt(game_tone=58.0, rmvpe=58.0, fcpe=58.0, dual_delta=2.0)
    p["dual_f0"]["extractors_agree"] = True
    adj = adjudicate(p, wav, SR, None, [])
    assert abs(adj["winning_hypothesis"] - 58.0) <= 0.5
    assert adj["status"] == "resolved_keep"


def test_b2_mirror_octave_true_high():
    # true = 70 -> the lower candidate 58 must NOT win through ACF
    # double-period correlation or harmonic-superset bias.
    wav = _wav_for(70.0)
    p = _pkt(game_tone=70.0, rmvpe=70.0, fcpe=70.0, dual_delta=2.0)
    p["dual_f0"]["extractors_agree"] = True
    adj = adjudicate(p, wav, SR, None, [])
    assert abs(adj["winning_hypothesis"] - 70.0) <= 0.5
    assert adj["status"] == "resolved_keep"
    low = [h for h in adj["hypotheses"]
           if abs(h["hypothesis"] - 58.0) <= 0.5]
    hi = [h for h in adj["hypotheses"]
          if abs(h["hypothesis"] - 70.0) <= 0.5]
    assert hi[0]["score"] > low[0]["score"]


def test_b2_missing_fundamental_conservative():
    # fundamental removed, harmonics 2..7 of 58 present — must not jump
    # an octave up to 116-ish or down; conservative: keep or unresolved.
    f0 = 440.0 * 2 ** ((58.0 - 69) / 12)
    t = np.arange(int(SR * 0.5)) / SR
    seg = sum(np.sin(2 * np.pi * k * f0 * t) / k
              for k in range(2, 8))
    wav = np.zeros(int(SR * 0.7))
    wav[: len(seg)] = np.asarray(seg) * 0.4
    p = _pkt(game_tone=58.0, rmvpe=58.0, fcpe=58.0, dual_delta=2.0)
    p["dual_f0"]["extractors_agree"] = True
    adj = adjudicate(p, wav, SR, None, [])
    assert adj["status"] in ("resolved_keep", "unresolved")
    assert abs(adj["winning_hypothesis"] - 58.0) <= 0.5 \
        or adj["status"] == "unresolved"


def test_b2_breathy_noisy_signal():
    rng = np.random.default_rng(2)
    seg = _seg(65.0, noise=0.25)
    wav = np.zeros(int(SR * 0.7))
    wav[: len(seg)] = seg + rng.normal(0, 0.15, len(seg))
    p = _pkt(game_tone=65.0, rmvpe=65.0, fcpe=65.0, dual_delta=2.0)
    p["dual_f0"]["extractors_agree"] = True
    adj = adjudicate(p, wav, SR, None, [])
    # either confirms 65 or stays unresolved — must not flip octaves
    assert adj["status"] != "resolved_change" \
        or abs(adj["winning_hypothesis"] - 65.0) < 6.0


def test_b2_silence_unvoiced_unresolved():
    wav = np.zeros(int(SR * 0.6))
    p = _pkt()
    adj = adjudicate(p, wav, SR, None, [])
    assert adj["status"] == "unresolved"


def test_b2_vibrato_keeps_true_f0():
    f0 = 440.0 * 2 ** ((62.0 - 69) / 12)
    t = np.arange(int(SR * 0.5)) / SR
    vib = f0 * (1 + 0.02 * np.sin(2 * np.pi * 5.5 * t))
    phase = np.cumsum(vib) / SR * 2 * np.pi
    seg = sum(np.sin(k * phase) / k for k in range(1, 6)) * 0.4
    wav = np.zeros(int(SR * 0.7))
    wav[: len(seg)] = np.asarray(seg)
    p = _pkt(game_tone=62.0, rmvpe=62.0, fcpe=62.0, dual_delta=2.0)
    p["dual_f0"]["extractors_agree"] = True
    adj = adjudicate(p, wav, SR, None, [])
    assert abs(adj["winning_hypothesis"] - 62.0) <= 0.5


def test_b2_short_note_low_cycles():
    wav = _wav_for(70.0, dur=0.12)
    p = _pkt(game_tone=70.0, dur=0.12, rmvpe=70.0, fcpe=70.0,
             dual_delta=2.0)
    p["dual_f0"]["extractors_agree"] = True
    adj = adjudicate(p, wav, SR, None, [])
    assert abs(adj["winning_hypothesis"] - 70.0) <= 0.5 \
        or adj["status"] == "unresolved"


def test_b2_pyin_plus_acf_is_one_independence_group():
    # §9.5: pYIN + ACF share the waveform mechanism — alone they cannot
    # satisfy the >=2 independent-group requirement.
    wav = _wav_for(58.0)
    p = _pkt(game_tone=69.96, rmvpe=None, fcpe=None, dual_delta=0.0)
    third = {"times": np.array([0.1, 0.2]), "midi": np.array([58.0, 58.0]),
             "voiced_prob": np.array([0.9, 0.9])}
    # widen window coverage: fake a dense third track
    third = {"times": np.arange(0, 0.5, 0.01),
             "midi": np.full(50, 58.0),
             "voiced_prob": np.full(50, 0.9)}
    adj = adjudicate(p, wav, SR, third, [])
    w = [h for h in adj["hypotheses"]
         if h["hypothesis"] == adj["winning_hypothesis"]][0]
    assert adj["supporting_independence_groups"] == ["waveform"] or \
        adj["status"] == "unresolved"


def test_b2_change_requires_waveform_group():
    # extractors alone (no waveform support) cannot drive a pitch change
    wav = np.zeros(int(SR * 0.6))  # silence -> no waveform evidence
    p = _pkt(game_tone=60.0, rmvpe=64.0, fcpe=64.0, dual_delta=5.0)
    p["dual_f0"]["extractors_agree"] = True
    p["dual_f0"]["both_oppose_game"] = True
    p["consensus"]["run_tones"] = [60.0] * 5
    adj = adjudicate(p, wav, SR, None, [])
    assert adj["status"] == "unresolved"


def test_b2_provisional_when_structure_pending():
    # §9.1/9.7: pitch+structure concurrent -> B provisional, C first.
    rec = _pkt()
    rec["state"] = {"routing_needs": {"pitch_adjudication": True,
                                    "structure_adjudication": True,
                                    "phrase_review": False},
                    "decision": "needs_pitch_adjudication"}
    adj = {"status": "resolved_keep", "winning_hypothesis": 69.96}
    apply_adjudication(rec, adj, None)
    assert adj["provisional"] is True
    st = rec["state"]
    assert st["routing_needs"]["pitch_adjudication"] is True  # rerun post-C
    assert st["decision"] == "needs_structure_adjudication"


def _waveform_group(adj, hyp):
    return [h for h in adj["hypotheses"]
            if h["hypothesis"] == hyp][0]["group_scores"]["waveform"]


def test_b3_correlated_waveform_features_do_not_inflate_group():
    # §7.2: pYIN+ACF+harmonic all pointing at the same wrong-octave
    # answer is ONE waveform vote, not three.
    wav = _wav_for(58.0)
    p = _pkt(game_tone=70.0, rmvpe=None, fcpe=None, dual_delta=0.0,
             run_tones=[70.0] * 5)
    third = {"times": np.arange(0, 0.5, 0.01), "midi": np.full(50, 58.0),
             "voiced_prob": np.full(50, 0.9)}
    adj_both = adjudicate(p, wav, SR, third, [])
    adj_acf_only = adjudicate(p, wav, SR, None, [])
    hyp = adj_both["winning_hypothesis"]
    g_both = _waveform_group(adj_both, hyp)
    g_acf = _waveform_group(adj_acf_only, hyp)
    # bounded: stacking correlated features can't push past ~1.0 nor
    # materially exceed the single-feature group score
    assert g_both <= 1.0 + 1e-9
    assert abs(g_both - g_acf) < 0.25


def test_b3_cross_group_convergence_does_increase_confidence():
    # waveform alone vs waveform+fcpe: real cross-group evidence should
    # legitimately raise the score — that's not correlation inflation.
    wav = _wav_for(58.0)
    p = _pkt(game_tone=70.0, rmvpe=None, fcpe=None, dual_delta=0.0,
             run_tones=[70.0] * 5)
    alone = adjudicate(p, wav, SR, None, [])
    p2 = _pkt(game_tone=70.0, rmvpe=None, fcpe=58.0, dual_delta=0.0,
              run_tones=[70.0] * 5)
    with_f = adjudicate(p2, wav, SR, None, [])
    assert with_f["confidence"] > alone["confidence"]


def test_b3_extra_correlated_feature_cannot_flip_decision():
    # pYIN on top of identical ACF+harmonic must not turn unresolved
    # into resolved by itself (extractor conflict, nothing else).
    wav = _wav_for(58.0)
    p = _pkt(game_tone=70.0, rmvpe=70.0, fcpe=58.0, run_tones=[70.0] * 5)
    third = {"times": np.arange(0, 0.5, 0.01), "midi": np.full(50, 58.0),
             "voiced_prob": np.full(50, 0.9)}
    adj_no = adjudicate(p, wav, SR, None, [])
    adj_yes = adjudicate(p, wav, SR, third, [])
    # same winner & same group count either way; status cannot flip
    # from unresolved purely due to the added correlated feature
    assert adj_no["status"] == adj_yes["status"]
    assert (len(adj_no["supporting_independence_groups"])
            == len(adj_yes["supporting_independence_groups"]))


def test_b2_safe_gate_binds_explicit_target():
    # §9.6: gate verifies the B winning hypothesis, not rmvpe's center.
    from agent2utau.diagnostic.triage import safe_retune_gate
    p = _pkt(game_tone=60.0, rmvpe=64.0, fcpe=64.0)
    plats = [{"center_midi": 64.0, "start": 0.0, "end": 0.5, "dur": 0.5}]
    gate = safe_retune_gate(p, plats, plats, [], target_midi=64.0)
    assert gate["rmvpe_target_plateau"] is not None
    # a target with no plateau support must fail
    gate2 = safe_retune_gate(p, plats, plats, [], target_midi=55.0)
    assert gate2["rmvpe_target_plateau"] is None
    assert "rmvpe_plateau_supports" in gate2["failed"]
