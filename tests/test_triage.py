import numpy as np

from agent2utau.diagnostic.triage import (classify, detect_plateaus,
                                        pick_baseline, safe_retune_gate)


def _n(start, dur=0.3, tone=60.0):
    return {"start": start, "dur": dur, "tone": tone, "voiced": True}


def test_pick_baseline_medoid():
    # run 2 is the outlier (extra note + shifted onset); medoid = others
    base = [_n(1.0), _n(2.0), _n(3.0)]
    runs = [list(base), [_n(1.01), _n(2.0), _n(3.02)],
            [_n(1.3), _n(2.0), _n(2.4), _n(3.0)],  # odd one
            [_n(0.99), _n(2.01), _n(2.98)]]
    r = pick_baseline(runs)
    assert r["index"] != 2
    assert len(r["costs"]) == 4


def test_plateaus_single_stable():
    t = np.arange(0, 1.0, 0.01)
    v = np.full_like(t, 60.0)
    pl = detect_plateaus(t, v, 0.1, 0.9)
    assert len(pl) == 1
    assert abs(pl[0]["center_midi"] - 60.0) < 0.01


def test_plateaus_two_levels():
    t = np.arange(0, 1.0, 0.01)
    v = np.where(t < 0.5, 60.0, 62.0).astype(float)
    pl = detect_plateaus(t, v, 0.0, 1.0)
    assert len(pl) == 2
    assert pl[0]["center_midi"] < pl[1]["center_midi"]


def test_plateaus_gap_breaks():
    t = np.arange(0, 1.0, 0.01)
    v = np.full_like(t, 60.0)
    v[40:50] = np.nan  # 100ms gap
    pl = detect_plateaus(t, v, 0.0, 1.0)
    assert len(pl) == 2


def _pkt(**kw):
    base = {"flags": [], "consensus": {"stability": "GAME_STABLE",
                                       "run_note_counts": [1] * 5,
                                       "structure_varies": False},
            "rmvpe": {"center_midi": 60.0, "iqr_cents": 10},
            "fcpe": {"center_midi": 60.0, "iqr_cents": 10},
            "dual_f0": {"rmvpe_vs_fcpe_cents": 5.0, "extractors_agree": True,
                        "both_oppose_game": False}}
    base.update(kw)
    return base


def test_classify_healthy():
    assert classify(_pkt(), [{"center_midi": 60.0}]) == "GAME_LIKELY_CORRECT"


def test_classify_extractor_conflict():
    p = _pkt(dual_f0={"rmvpe_vs_fcpe_cents": -1193.0,
                      "extractors_agree": False, "both_oppose_game": False},
             flags=["possible_octave_error"])
    assert classify(p, []) == "F0_EXTRACTOR_CONFLICT"


def test_classify_pitch_hard():
    p = _pkt(flags=["wrong_pitch"],
             rmvpe={"center_midi": 70.0, "iqr_cents": 15},
             fcpe={"center_midi": 69.9, "iqr_cents": 20},
             dual_f0={"rmvpe_vs_fcpe_cents": -10.0, "extractors_agree": True,
                      "both_oppose_game": True})
    assert classify(p, [{"center_midi": 70.0}]) == "PITCH_HARD_SUSPICIOUS"


def test_classify_structure_hard():
    p = _pkt(consensus={"stability": "GAME_UNSTABLE",
                        "run_note_counts": [2, 1, 2, 1, 1],
                        "structure_varies": True})
    plats = [{"center_midi": 60.0}, {"center_midi": 63.0}]
    assert classify(p, plats) == "STRUCTURE_CANDIDATE"


def test_plateau_80ms_boundary():
    # 8 frames @10ms = 80ms inclusive -> plateau; 7 frames = 70ms -> not
    t = np.arange(0, 1.0, 0.01)
    v = np.full_like(t, np.nan)
    v[10:18] = 60.0                       # 8 frames
    assert len(detect_plateaus(t, v, 0.0, 1.0)) == 1
    v2 = np.full_like(t, np.nan)
    v2[10:17] = 60.0                      # 7 frames = 70ms
    assert len(detect_plateaus(t, v2, 0.0, 1.0)) == 0


def test_structure_ambiguity_blocks_pitch_hard():
    # §5.1: dual F0 both oppose GAME but structure varies -> never
    # PITCH_HARD_SUSPICIOUS
    p = _pkt(flags=["wrong_pitch"],
             consensus={"stability": "GAME_UNSTABLE",
                        "run_note_counts": [2, 1, 2, 1, 1],
                        "structure_varies": True},
             rmvpe={"center_midi": 70.0, "iqr_cents": 10},
             fcpe={"center_midi": 69.9, "iqr_cents": 10},
             dual_f0={"rmvpe_vs_fcpe_cents": -10.0,
                      "extractors_agree": True, "both_oppose_game": True})
    plats = [{"center_midi": 70.0}, {"center_midi": 72.0}]
    assert classify(p, plats) in ("STRUCTURE_CANDIDATE",
                                  "AMBIGUOUS_ORNAMENT")


def test_safe_gate_requires_dual_plateau():
    # §5.3: RMVPE plateau supports target but no FCPE plateau -> reject
    p = _pkt(flags=["wrong_pitch"], game_tone=65.0,
             consensus={"stability": "GAME_STABLE", "presence_rate": 1.0,
                        "tone_agreement": 1.0, "structure_varies": False,
                        "run_note_counts": [1] * 5},
             rmvpe={"center_midi": 72.0, "iqr_cents": 10},
             fcpe={"center_midi": 72.1, "iqr_cents": 10},
             dual_f0={"rmvpe_vs_fcpe_cents": 10.0, "extractors_agree": True,
                      "both_oppose_game": True,
                      "game_vs_rmvpe_cents": 700.0,
                      "game_vs_fcpe_cents": 710.0})
    rp = [{"center_midi": 72.0, "start": 1.0, "end": 1.4}]
    g1 = safe_retune_gate(p, rp, [{"center_midi": 72.0, "start": 1.0,
                                   "end": 1.4}], [])
    assert g1["eligible"] and g1["gates"]["dual_plateau_agree"]
    g2 = safe_retune_gate(p, rp, [], [])
    assert not g2["eligible"]
    assert "fcpe_plateau_supports" in g2["failed"]


def test_plateau_end_equals_start_plus_dur():
    t = np.arange(0, 1.0, 0.01)
    v = np.where((t >= 0.3) & (t <= 0.6), 60.0, np.nan)
    for p in detect_plateaus(t, v, 0.0, 1.0):
        assert abs((p["end"] - p["start"]) - p["dur"]) < 0.011


def test_safe_gate_rejects_multi_plateau_fcpe():
    # §5.2: FCPE shows target AND another plateau -> not unique -> reject
    p = _pkt(flags=["wrong_pitch"], game_tone=65.0,
             consensus={"stability": "GAME_STABLE", "presence_rate": 1.0,
                        "tone_agreement": 1.0, "structure_varies": False,
                        "run_note_counts": [1] * 5},
             rmvpe={"center_midi": 72.0, "iqr_cents": 10},
             fcpe={"center_midi": 72.1, "iqr_cents": 10},
             dual_f0={"rmvpe_vs_fcpe_cents": 10.0, "extractors_agree": True,
                      "both_oppose_game": True,
                      "game_vs_rmvpe_cents": 700.0,
                      "game_vs_fcpe_cents": 710.0})
    rp = [{"center_midi": 72.0, "start": 1.0, "end": 1.4}]
    fp_multi = [{"center_midi": 72.0, "start": 1.0, "end": 1.2},
                {"center_midi": 65.0, "start": 1.2, "end": 1.4}]
    g = safe_retune_gate(p, rp, fp_multi, [])
    assert not g["eligible"]
    assert "single_stable_plateau" in g["failed"]


def test_safe_gate_rejects_nonoverlapping_plateaus():
    # §5.2: both have the plateau but at different times -> reject
    p = _pkt(flags=["wrong_pitch"], game_tone=65.0,
             consensus={"stability": "GAME_STABLE", "presence_rate": 1.0,
                        "tone_agreement": 1.0, "structure_varies": False,
                        "run_note_counts": [1] * 5},
             rmvpe={"center_midi": 72.0, "iqr_cents": 10},
             fcpe={"center_midi": 72.1, "iqr_cents": 10},
             dual_f0={"rmvpe_vs_fcpe_cents": 10.0, "extractors_agree": True,
                      "both_oppose_game": True,
                      "game_vs_rmvpe_cents": 700.0,
                      "game_vs_fcpe_cents": 710.0})
    rp = [{"center_midi": 72.0, "start": 1.0, "end": 1.2}]
    fp = [{"center_midi": 72.0, "start": 1.3, "end": 1.5}]
    g = safe_retune_gate(p, rp, fp, [])
    assert not g["eligible"]
    assert "plateau_temporal_overlap" in g["failed"]


def test_orthogonal_states_simultaneous():
    # §5.4: pitch conflict + structure unstable + sensitive can coexist
    from agent2utau.diagnostic.triage import orthogonal_states
    p = _pkt(flags=["possible_octave_error"],
             consensus={"stability": "GAME_UNSTABLE",
                        "run_note_counts": [2, 1, 1, 1, 2],
                        "structure_varies": True, "tone_agreement": 0.6},
             dual_f0={"rmvpe_vs_fcpe_cents": -1193.0,
                      "extractors_agree": False, "both_oppose_game": False},
             separation={"separation_sensitive": True})
    st = orthogonal_states(p)
    assert st["pitch_state"] == "extractor_conflict"
    assert st["structure_state"] == "split_merge_variable"
    assert st["identity_state"] == "variable"
    assert st["separation_state"] == "sensitive"
    # A4: pitch+structure needs coexist; decision is the top-priority step
    assert st["routing_needs"]["pitch_adjudication"] is True
    assert st["routing_needs"]["structure_adjudication"] is True
    assert st["decision"] == "needs_pitch_adjudication"


def test_a3_stale_wrong_pitch_does_not_override_calibration():
    # §5.1: raw wrong_pitch flag is a feature only — the calibrated
    # plateau re-judgement (plateau matches GAME tone) already cleared it,
    # so pitch_state must be stable and keep_baseline.
    from agent2utau.diagnostic.triage import orthogonal_states
    p = _pkt(flags=["wrong_pitch"], game_tone=60.0,
             plateaus=[{"center_midi": 60.0}])
    p["triage"] = "GAME_LIKELY_CORRECT"
    st = orthogonal_states(p)
    assert st["pitch_state"] == "stable"
    assert st["decision"] == "keep_baseline"


def test_a4_stale_wrong_pitch_flag_needs_no_triage_enum():
    # §5.3: same calibrated-stable outcome must hold WITHOUT trusting the
    # legacy triage label — evidence alone decides.
    from agent2utau.diagnostic.triage import orthogonal_states
    p = _pkt(flags=["wrong_pitch"], game_tone=60.0,
             plateaus=[{"center_midi": 60.0}])
    p["triage"] = "NEEDS_LISTENING_REVIEW"   # stale enum says otherwise
    st = orthogonal_states(p)
    assert st["pitch_state"] == "stable"


def test_a3_safe_eligible_is_pending_adjudication_not_repair():
    # §5.3: SAFE gate cannot bypass M2.3.2B.
    from agent2utau.diagnostic.triage import orthogonal_states
    p = _pkt()
    p["triage"] = "PITCH_HARD_SUSPICIOUS"
    p["dual_f0"]["both_oppose_game"] = True
    p["safe_gate"] = {"eligible": True}
    st = orthogonal_states(p)
    assert st["decision"] == "candidate_pending_adjudication"
    assert st["decision"] != "repair_candidate"


def test_a3_structure_state_independent_of_triage_label():
    # §5.2: extractor-conflict pitch + structure_varies => both states set.
    from agent2utau.diagnostic.triage import orthogonal_states
    p = _pkt(consensus={"stability": "GAME_UNSTABLE",
                        "run_note_counts": [2, 1, 1],
                        "structure_varies": True},
             dual_f0={"rmvpe_vs_fcpe_cents": 1150.0,
                      "extractors_agree": False, "both_oppose_game": False})
    p["triage"] = "F0_EXTRACTOR_CONFLICT"
    st = orthogonal_states(p)
    assert st["pitch_state"] == "extractor_conflict"
    assert st["structure_state"] == "split_merge_variable"
    assert st["routing_needs"]["pitch_adjudication"] is True
    assert st["routing_needs"]["structure_adjudication"] is True
    assert st["decision"] == "needs_pitch_adjudication"


def test_a4_structure_candidate_routes_to_structure_adjudication():
    # A4 §5.1: structure candidates must NOT go straight to human review —
    # M2.3.2C automatic structure adjudication comes first.
    from agent2utau.diagnostic.triage import orthogonal_states
    p = _pkt(consensus={"stability": "GAME_UNSTABLE",
                        "run_note_counts": [2, 1, 1, 1, 1],
                        "structure_varies": True},
             structure_evidence={"plateau_count_agreement": True})
    st = orthogonal_states(p)
    assert st["decision"] == "needs_structure_adjudication"
    assert st["routing_needs"]["structure_adjudication"] is True
    assert st["routing_needs"]["phrase_review"] is False


def test_a4_phrase_review_only_after_bc_unresolved():
    # A4 §5.1: needs_phrase_review is a post-B/C unresolved outcome.
    from agent2utau.diagnostic.triage import orthogonal_states
    p = _pkt(consensus={"stability": "GAME_UNSTABLE",
                        "run_note_counts": [2, 1, 1],
                        "structure_varies": True})
    p["b_c_unresolved"] = True
    st = orthogonal_states(p)
    assert st["routing_needs"]["phrase_review"] is True
    # structure_adjudication still outranks phrase_review while pending
    assert st["decision"] == "needs_structure_adjudication"
    # once structure is resolved-stable, phrase review surfaces
    p["consensus"]["structure_varies"] = False
    st = orthogonal_states(p)
    assert st["decision"] == "needs_phrase_review"


def test_a4_no_a_stage_state_becomes_repair_candidate():
    # A4 §5.5.6: nothing at the A stage may produce repair_candidate,
    # not even a SAFE-eligible packet.
    from agent2utau.diagnostic.triage import orthogonal_states
    for extra in ({}, {"safe_gate": {"eligible": True}},
                  {"triage": "PITCH_HARD_SUSPICIOUS",
                   "safe_gate": {"eligible": True}}):
        p = _pkt(**extra)
        assert orthogonal_states(p)["decision"] != "repair_candidate"


def test_classify_wrong_pitch_single_extractor():
    p = _pkt(flags=["wrong_pitch"],
             fcpe={"center_midi": 60.5, "iqr_cents": 30},
             dual_f0={"rmvpe_vs_fcpe_cents": 300.0, "extractors_agree": False,
                      "both_oppose_game": False})
    # extractors disagree but < 1000c -> not conflict class; flagged ->
    assert classify(p, []) in ("NEEDS_LISTENING_REVIEW",
                               "F0_EXTRACTOR_CONFLICT")
