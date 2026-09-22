"""R2.1-E/F/G/I/J regression tests: onset/portamento/ornament/match/QA."""
import numpy as np

from agent2utau.expression.contour import (
    ContourSignal, HOP_S, segment_ids)
from agent2utau.expression.contour_qa import (
    contour_position_metrics, modulation_metrics, portamento_metrics,
    turning_point_metrics)
from agent2utau.expression.events import (
    PitchEvent, detect_onset_events, detect_ornament_events,
    detect_portamento_events, detect_residual_artifact_regions,
    detect_vibrato_events, match_pitch_events)


def _sig(times, cents, conf=1.0):
    times = np.asarray(times, dtype=float)
    cents = np.asarray(cents, dtype=float)
    voiced = ~np.isnan(cents)
    return ContourSignal(
        times=times, cents=cents, raw_cents=cents.copy(), voiced=voiced,
        confidence=np.where(voiced, conf, 0.0),
        note_idx=np.zeros(len(times), dtype=int), phoneme_idx=None,
        source="source", extractor="fcpe",
        segment_id=segment_ids(times, voiced))


def _note(start, dur, tone=60.0, lyric="a"):
    return {"lyric": lyric, "tone": tone, "abs_start_s": start,
            "dur_s": dur}


# ------------------------------------------------------------- onset
def test_onset_scoop_detected_with_settle():
    t = np.arange(0, 1.0, HOP_S)
    cents = np.full(len(t), 6000.0)
    nuc = 0.10                          # nucleus 100ms in
    v = (t >= nuc) & (t <= nuc + 0.30)
    cents[v] += -90 * np.exp(-((t[v] - nuc - 0.04) / 0.07) ** 2)
    sig = _sig(t, cents)
    ev = detect_onset_events(sig, [_note(0, 1.0)], {0: nuc})
    assert len(ev) == 1 and ev[0].type == "scoop"
    assert ev[0].params["settle_time_ms"] is not None
    assert 20 < ev[0].params["peak_time_ms"] < 80
    # event end = real settle, not fixed +80ms
    assert ev[0].end_s < nuc + 0.45


def test_onset_overshoot_detected():
    t = np.arange(0, 1.0, HOP_S)
    cents = np.full(len(t), 6000.0)
    nuc = 0.10
    v = (t >= nuc) & (t <= nuc + 0.25)
    cents[v] += 70 * np.exp(-((t[v] - nuc - 0.03) / 0.05) ** 2)
    ev = detect_onset_events(_sig(t, cents), [_note(0, 1.0)], {0: nuc})
    assert len(ev) == 1 and ev[0].type == "overshoot"


def test_onset_undershoot_detected_separately():
    t = np.arange(0, 1.0, HOP_S)
    cents = np.full(len(t), 6000.0)
    nuc = 0.10
    v = (t >= nuc + 0.04) & (t <= nuc + 0.22)
    cents[v] += -75 * np.exp(-((t[v] - nuc - 0.09) / 0.035) ** 2)
    ev = detect_onset_events(_sig(t, cents), [_note(0, 1.0)], {0: nuc})
    assert len(ev) == 1
    assert ev[0].type == "undershoot"
    assert ev[0].start_s >= nuc - 0.08


def test_onset_single_frame_spike_rejected():
    t = np.arange(0, 1.0, HOP_S)
    cents = np.full(len(t), 6000.0)
    cents[int(0.12 / HOP_S)] += 300      # 10ms spike — not a gesture
    ev = detect_onset_events(_sig(t, cents), [_note(0, 1.0)], {0: 0.10})
    assert ev == []


def test_onset_no_gesture_no_event():
    t = np.arange(0, 1.0, HOP_S)
    cents = np.full(len(t), 6000.0)
    ev = detect_onset_events(_sig(t, cents), [_note(0, 1.0)], {0: 0.10})
    assert ev == []


# --------------------------------------------------------- portamento
def _two_note_sig(slide_fn=None, gap=0.0, tone_b=64.0):
    """note A 60.0 0-0.5s, note B 64.0 0.5-1.0s (+gap)."""
    notes = [_note(0.0, 0.5, 60.0), _note(0.5 + gap, 0.5, tone_b)]
    t = np.arange(0, 1.0 + gap + HOP_S, HOP_S)
    cents = np.where(t < 0.5, 6000.0, tone_b * 100.0)
    if slide_fn is not None:
        cents = slide_fn(t, cents)
    sig = _sig(t, cents)
    sig.note_idx = np.where(t < 0.5 + gap, 0, 1)
    return sig, notes


def test_portamento_linear():
    def slide(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        c[v] = 6000 + 400 * (t[v] - 0.40) / 0.20
        return c
    sig, notes = _two_note_sig(slide)
    ev = detect_portamento_events(sig, notes)
    assert len(ev) == 1
    p = ev[0].params
    assert p["trajectory_type"] == "linear"
    assert abs(p["departure_rel_prev_end_ms"] + 100) < 60
    assert abs(p["arrival_rel_next_start_ms"] - 100) < 60
    assert 300 < p["span_cents"] < 500
    assert 120 < p["duration_ms"] < 280


def test_portamento_convex_vs_concave():
    def convex(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        c[v] = 6000 + 400 * np.sqrt((t[v] - 0.40) / 0.20)
        return c
    def concave(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        c[v] = 6000 + 400 * ((t[v] - 0.40) / 0.20) ** 2
        return c
    e1 = detect_portamento_events(*_two_note_sig(convex))[0]
    e2 = detect_portamento_events(*_two_note_sig(concave))[0]
    assert e1.params["trajectory_type"] == "convex"
    assert e2.params["trajectory_type"] == "concave"


def test_portamento_downward_preserves_shape_semantics():
    def convex_down(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        u = (t[v] - 0.40) / 0.20
        c[v] = 6000 - 400 * np.sqrt(u)
        return c
    def concave_down(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        u = (t[v] - 0.40) / 0.20
        c[v] = 6000 - 400 * u ** 2
        return c
    e1 = detect_portamento_events(
        *_two_note_sig(convex_down, tone_b=56.0))[0]
    e2 = detect_portamento_events(
        *_two_note_sig(concave_down, tone_b=56.0))[0]
    assert e1.params["direction"] == "down"
    assert e2.params["direction"] == "down"
    assert e1.params["trajectory_type"] == "convex"
    assert e2.params["trajectory_type"] == "concave"
    assert e1.params["norm_traj"][0] <= 0.05
    assert e1.params["norm_traj"][-1] >= 0.95


def test_portamento_s_curve_by_inflection():
    def s_curve(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        u = (t[v] - 0.40) / 0.20
        smooth = 3 * u ** 2 - 2 * u ** 3
        c[v] = 6000 + 400 * smooth
        return c
    ev = detect_portamento_events(*_two_note_sig(s_curve))
    assert len(ev) == 1
    assert ev[0].params["trajectory_type"] == "s_curve"


def test_portamento_stepped():
    def stepped(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        c[v] = 6000 + np.clip(np.floor((t[v] - 0.40) / 0.05) * 100,
                              0, 400)
        return c
    ev = detect_portamento_events(*_two_note_sig(stepped))
    assert len(ev) == 1
    assert ev[0].params["trajectory_type"] == "stepped"


def test_portamento_instant_jump_is_stepped_or_short():
    ev = detect_portamento_events(*_two_note_sig(None))
    # a direct jump: either classified stepped or essentially zero-length
    assert ev == [] or ev[0].params["trajectory_type"] == "stepped" \
        or ev[0].params["duration_ms"] <= 40


def test_portamento_breath_gap_not_detected():
    sig, notes = _two_note_sig(None, gap=0.15)   # 150ms gap = breath
    assert detect_portamento_events(sig, notes) == []


def test_portamento_off_tolerance_arrival_relaxed_not_missing():
    """A slide that lands sharp/flat but holds a sustained plateau is a
    real portamento with an off-tolerance arrival — flag it, don't drop it
    (P2 from_note=4: source itself arrives ~+40c sharp, a faithful render
    holding +34c was being reported missing under the strict +-30c stay)."""
    def slide(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        c[v] = 6000 + 435 * (t[v] - 0.40) / 0.20
        c[t > 0.60] = 6435.0          # sustained plateau +35c off tone_b
        return c
    sig, notes = _two_note_sig(slide)
    ev = detect_portamento_events(sig, notes)
    assert len(ev) == 1
    p = ev[0].params
    assert p["arrival_relaxed"] is True
    assert 20 < p["arrival_offset_c"] < 50


def test_portamento_wrong_note_landing_still_missing():
    """The relaxed arrival band is capped at min(2*tol, half the interval):
    landing a whole semitone off (65 vs 64) must still report no event."""
    def slide(t, c):
        v = (t >= 0.40) & (t <= 0.60)
        c[v] = 6000 + 500 * (t[v] - 0.40) / 0.20
        c[t > 0.60] = 6500.0          # lands on tone 65 — not tone_b=64
        return c
    sig, notes = _two_note_sig(slide)
    assert detect_portamento_events(sig, notes) == []


# ----------------------------------------------------------- ornament
def _orn_sig(orn_s, dur=1.2):
    t = np.arange(0, dur + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    v = (t >= orn_s) & (t <= orn_s + 0.22)
    cents[v] += 60 * np.sin(2 * np.pi * (t[v] - orn_s) / 0.11)
    return _sig(t, cents), [_note(0, dur)]


def test_ornament_early_middle_late():
    for s in (0.25, 0.55, 0.90):
        sig, notes = _orn_sig(s)
        ev = detect_ornament_events(sig, notes)
        assert len(ev) >= 1, f"ornament at {s}s missed"
        e = min(ev, key=lambda x: abs(x.start_s - s))
        assert abs(e.start_s - s) < 0.15


def test_ornament_vibrato_excluded():
    t = np.arange(0, 1.3 + HOP_S, HOP_S)
    cents = 6000 + np.where(t >= 0.5,
                            50 * np.sin(2 * np.pi * 6.5 * (t - 0.5)), 0)
    sig = _sig(t, cents)
    notes = [_note(0, 1.3)]
    vib = detect_vibrato_events(sig, notes)
    assert vib                            # vibrato detected first
    orn = detect_ornament_events(sig, notes, exclude_events=vib)
    assert orn == []                      # not double-reported as ornament


def test_ornament_exclusion_does_not_collapse_time_gap():
    t = np.arange(0, 1.2 + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    cents += 65 * np.exp(-((t - 0.36) / 0.025) ** 2)
    cents -= 65 * np.exp(-((t - 0.74) / 0.025) ** 2)
    sig = _sig(t, cents)
    notes = [_note(0, 1.2)]
    hole = PitchEvent("vibrato", [0], 0.45, 0.65, 1.0)
    # Each side has only one qualifying extremum. Removing the middle span
    # must not splice the two sides into a fake two-extremum ornament.
    assert detect_ornament_events(sig, notes, exclude_events=[hole]) == []


def test_residual_family_disagreement_is_artifact():
    t = np.arange(0, 0.5, HOP_S)
    r1 = np.zeros(len(t))
    r2 = np.zeros(len(t))
    r2[15:21] = 140.0
    dense = {"times": t, "r_fcpe": r1, "r_rmvpe": r2,
             "note_idx": np.zeros(len(t), dtype=int)}
    ev = detect_residual_artifact_regions(dense)
    assert ev
    assert "residual_disagreement" in ev[0].params["artifact_kinds"]


# ------------------------------------------------------------ matching
def _ev(type_, ni, s, e, **params):
    return PitchEvent(type_, [ni], s, e, 0.8, params=params)


def test_match_exact_and_ambiguous():
    notes = [_note(0.0, 1.0), _note(1.0, 1.0)]
    src = [_ev("vibrato", 0, 0.6, 1.0, rate_hz=6.5, depth_c=50)]
    neu_same = [_ev("vibrato", 0, 0.62, 0.98, rate_hz=6.4, depth_c=40)]
    r = match_pitch_events(src, neu_same, notes)
    assert len(r["matched"]) == 1 and not r["ambiguous"]
    # barely overlapping candidate -> ambiguous, not forced
    neu_far = [_ev("vibrato", 0, 0.05, 0.30, rate_hz=6.5, depth_c=50)]
    r2 = match_pitch_events(src, neu_far, notes)
    assert not r2["matched"]
    assert r2["ambiguous"] or r2["source_only"]


def test_match_wrong_direction_rejected():
    notes = [_note(0.0, 0.5, 60), _note(0.5, 0.5, 64)]
    src = [_ev("portamento", 0, 0.4, 0.6, direction="up",
               trajectory_type="linear", span_cents=400)]
    neu = [_ev("portamento", 0, 0.4, 0.6, direction="down",
               trajectory_type="linear", span_cents=-380)]
    r = match_pitch_events(src, neu, notes)
    assert not r["matched"]            # direction kills the score


# ------------------------------------------------------------------ QA
def test_qa_same_cents_wrong_topology_fails():
    g = np.arange(0, 2.0, HOP_S)
    src = np.full(len(g), 6000.0)
    ren = src.copy()
    v = (g >= 0.8) & (g <= 1.0)
    ren[v] += 18 * np.sin(2 * np.pi * 9 * (g[v] - 0.8))   # subtle wiggle
    mask = np.ones(len(g), bool)
    pos = contour_position_metrics(src, ren, mask)
    topo = turning_point_metrics(src, ren, mask=mask)
    assert pos["med_c"] < 5                      # pointwise looks fine
    assert topo["extra_turns"] >= 4              # but topology catches it


def test_qa_lower_cents_extra_turns_is_regression():
    g = np.arange(0, 2.0, HOP_S)
    src = np.full(len(g), 6000.0)
    ren_a = src + 25                            # flat offset, clean
    ren_b = src + 20 * np.sin(2 * np.pi * 10 * g)  # closer median, wiggly
    mask = np.ones(len(g), bool)
    ta = turning_point_metrics(src, ren_a, mask=mask)
    tb = turning_point_metrics(src, ren_b, mask=mask)
    pa = contour_position_metrics(src, ren_a, mask=mask)
    pb = contour_position_metrics(src, ren_b, mask=mask)
    assert pb["med_c"] < pa["med_c"]            # b wins pointwise...
    assert tb["extra_turns"] > ta["extra_turns"]  # ...but is a regression


def test_turning_point_detail_rows_exactly_match_counts():
    """Attribution rows must come from the exact topology matcher, never a
    second pass that can disagree with missing_turns/extra_turns."""
    g = np.arange(0, 1.0, HOP_S)
    src = 6000 + 50 * np.sin(2 * np.pi * 3.0 * g)
    ren = src.copy()
    ren[g >= 0.55] = 6000.0
    mask = np.ones(len(g), bool)
    q = turning_point_metrics(src, ren, mask=mask)
    assert q["missing_turns"] > 0
    assert len(q["missing_turn_details"]) == q["missing_turns"]
    assert len(q["extra_turn_details"]) == q["extra_turns"]
    assert all("frame_idx" in row and "prominence_c" in row
               for row in q["missing_turn_details"])


def test_topology_edge_jitter_is_stable():
    """An extremum that lands ON a masked-run boundary must not flip the
    count when the same physical dip shifts one frame inward — the run
    edge hides whether the curve really turns, so boundary extrema are
    excluded symmetrically on both sides."""
    g = np.arange(0, 2.0, HOP_S)
    src = np.full(len(g), 6000.0)
    mask = np.ones(len(g), bool)
    mask[105:] = False                        # source run ends at f104
    ren_a = src.copy()
    ren_a[90:104] -= np.linspace(0, 140, 14)  # dip bottoms at f103 (edge)
    ren_b = ren_a.copy()
    ren_b[90:103] -= np.linspace(0, 140, 13)  # same dip bottoms at f102
    ren_b[103] -= 139                         # (edge-1, still a trough)
    ta = turning_point_metrics(src, ren_a, mask=mask)
    tb = turning_point_metrics(src, ren_b, mask=mask)
    assert ta["extra_turns"] == tb["extra_turns"]


def _port_ev(fn, s, e, traj="linear", span=-300.0):
    return PitchEvent("portamento", [fn, fn + 1], s, e, 1.0,
                      params={"from_note": fn, "trajectory_type": traj,
                              "span_cents": span})


def test_event_shape_gate_classes():
    """Absolute shape gate classifies mismatch causes instead of trusting
    raw traj_match flags."""
    from agent2utau.expression.contour_qa import event_shape_gate
    t = np.arange(0, 1.0, HOP_S)
    base = np.full(len(t), 6000.0)
    # source: linear slide 6000->5700 over 0.4-0.6
    src_c = base.copy()
    w = (t >= 0.4) & (t <= 0.6)
    src_c[w] = 6000 - 300 * (t[w] - 0.4) / 0.2
    src_c[t > 0.6] = 5700.0
    src = _sig(t, src_c)
    neu = _sig(t, base)
    # render A: identical shape -> match (label differs deliberately)
    rend_a = _sig(t, src_c)
    # render B: plunge completed in the first 20% of the window then flat
    # — clearly divergent shape, must be classified as distortion
    rb = base.copy()
    w2 = (t >= 0.4) & (t <= 0.44)
    rb[w2] = 6000 - 300 * (t[w2] - 0.4) / 0.04
    rb[t > 0.44] = 5700.0
    rend_b = _sig(t, rb)
    # render C: unvoiced through most of the window
    rc = src_c.copy()
    rc[(t >= 0.38) & (t <= 0.56)] = np.nan
    rend_c = _sig(t, rc)

    se = _port_ev(0, 0.4, 0.6, traj="linear")
    gate = lambda r: event_shape_gate([se], [_port_ev(0, 0.41, 0.6,
                                                     traj="concave")],
                                      neu, src, r)
    ga = gate(rend_a)
    assert ga["events"][0]["class"] == "label_mismatch"   # shape close
    gb = gate(rend_b)
    assert gb["events"][0]["class"] == "distortion"
    assert gb["n_blocking"] == 1 and not gb["gate_passed"]
    gc = gate(rend_c)
    assert gc["events"][0]["class"] == "render_voicing_loss"
    assert gc["events"][0]["blocking"] and not gc["gate_passed"]

    # If the neutral baseline loses voicing in the same window too, the
    # dropout cannot be attributed to the candidate curve.
    neu_c = base.copy()
    neu_c[(t >= 0.38) & (t <= 0.56)] = np.nan
    gd = event_shape_gate([se], [_port_ev(0, 0.41, 0.6,
                                          traj="concave")],
                          _sig(t, neu_c), src, rend_c)
    assert gd["events"][0]["class"] == "shared_voicing_gap"
    assert not gd["events"][0]["blocking"] and gd["gate_passed"]

    # excluded-but-flagged classes never silently pass as match
    assert ga["gate_passed"]


def test_modulation_event_window_honours_artifact_mask():
    g = np.arange(0, 1.0, HOP_S)
    src = np.full(len(g), 6000.0)
    ren = src.copy()
    bad = (g >= 0.30) & (g <= 0.70)
    ren[bad] += 45 * np.sin(2 * np.pi * 6.5 * (g[bad] - 0.30))
    mask = ~bad
    q = modulation_metrics(src, ren, mask=mask,
                           event_windows=[(0, len(g))])
    # The excluded wiggle must not be bridged back into the event metric.
    assert q["windows"][0]["render"] is None


def test_portamento_metrics_resample_unequal_profile_lengths():
    a = PitchEvent("portamento", [0, 1], 0.4, 0.6, 1.0,
                   params={"from_note": 0, "trajectory_type": "linear",
                           "span_cents": 400,
                           "slope_profile": [1, 1, 1, 1],
                           "curv_profile": [0, 0, 0, 0]})
    b = PitchEvent("portamento", [0, 1], 0.41, 0.61, 1.0,
                   params={"from_note": 0, "trajectory_type": "linear",
                           "span_cents": 395,
                           "slope_profile": [1, 1, 1, 1, 1, 1, 1],
                           "curv_profile": [0, 0, 0, 0, 0, 0, 0]})
    q = portamento_metrics([a], [b])[0]
    assert "slope_profile_rmse" in q
    assert "curv_profile_rmse" in q
    assert q["slope_profile_rmse"] == 0.0
