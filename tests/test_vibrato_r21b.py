"""R2.1-B/C/D regression tests: real vibrato events + 3-state compile."""
import numpy as np

from agent2utau.expression.contour import (
    ContourSignal, HOP_S, robust_pitch_trend, segment_ids)
from agent2utau.expression.events import (
    detect_vibrato_events, match_vibrato_events)
from agent2utau.expression.pitch_residual import (
    TICK_MS, VIBRATO_DEPTH_GAIN, compile_C2, compile_C3)


def _sig(times, cents, voiced=None, conf=1.0):
    times = np.asarray(times, dtype=float)
    cents = np.asarray(cents, dtype=float)
    if voiced is None:
        voiced = ~np.isnan(cents)
    voiced = np.asarray(voiced, dtype=bool) & ~np.isnan(cents)
    return ContourSignal(
        times=times, cents=cents, raw_cents=cents.copy(), voiced=voiced,
        confidence=np.where(voiced, conf, 0.0),
        note_idx=np.zeros(len(times), dtype=int), phoneme_idx=None,
        source="source", extractor="fcpe",
        segment_id=segment_ids(times, voiced))


def _note(dur=1.3, tone=60.0, start=0.0):
    return {"lyric": "a", "tone": tone, "abs_start_s": start,
            "dur_s": dur}


def _vib_sig(dur, vib_s, vib_e, rate=6.5, depth=50.0, phase=0.0,
             ramp=None, trend=None):
    t = np.arange(0, dur + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    if trend is not None:
        cents += trend(t)
    v = (t >= vib_s) & (t <= vib_e)
    env = np.full(len(t), depth)
    if ramp is not None:
        frac = np.clip((t - vib_s) / max(vib_e - vib_s, 1e-6), 0, 1)
        env = ramp[0] + (ramp[1] - ramp[0]) * frac
    cents[v] += env[v] * np.sin(2 * np.pi * rate * (t[v] - vib_s) + phase)
    return _sig(t, cents)


def _ev(sig, note=None):
    return detect_vibrato_events(sig, [note or _note()])


# ---- R2.1-B: real event boundaries -----------------------------------

def test_vibrato_tail_only():
    sig = _vib_sig(1.3, 0.85, 1.3, rate=6.5, depth=50)
    ev = _ev(sig)
    assert len(ev) == 1
    e = ev[0]
    assert abs(e.start_s - 0.85) < 0.12
    assert abs(e.end_s - 1.3) < 0.10
    assert abs(e.params["rate_hz"] - 6.5) < 0.4
    assert abs(e.params["depth_c"] - 50) < 10
    assert e.params["stable_cycle_count"] >= 2.0   # trimmed stable span


def test_vibrato_middle_only():
    sig = _vib_sig(1.4, 0.40, 0.85, rate=6.0, depth=45)
    ev = _ev(sig)
    assert len(ev) == 1
    assert abs(ev[0].start_s - 0.40) < 0.12
    assert abs(ev[0].end_s - 0.85) < 0.12


def test_vibrato_regular_then_irregular():
    t = np.arange(0, 1.4 + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    v = (t >= 0.2) & (t <= 0.65)
    cents[v] += 45 * np.sin(2 * np.pi * 6.5 * (t[v] - 0.2))
    rng = np.random.default_rng(7)
    v2 = t > 0.65
    cents[v2] += rng.normal(0, 30, v2.sum())          # aperiodic wiggle
    ev = _ev(_sig(t, cents))
    assert len(ev) == 1
    assert abs(ev[0].start_s - 0.2) < 0.12
    assert abs(ev[0].end_s - 0.65) < 0.15   # stops at the irregular half


def test_vibrato_depth_ramp():
    sig = _vib_sig(1.3, 0.5, 1.3, rate=6.5, ramp=(20.0, 60.0))
    ev = _ev(sig)
    assert len(ev) == 1
    env = ev[0].params["depth_envelope_c"]
    assert env[0] < env[-1]                 # envelope captures the ramp
    assert 25 < ev[0].params["depth_c"] < 55


def test_vibrato_phase_difference():
    a = _ev(_vib_sig(1.3, 0.5, 1.3, phase=0.0))[0]
    b = _ev(_vib_sig(1.3, 0.5, 1.3, phase=1.2))[0]
    # phases are fitted relative to each event's own start; re-reference
    # both to absolute time 0 via phase_origin_s before comparing
    def abs_phase(e):
        w = 2 * np.pi * e.params["rate_hz"]
        return (e.params["phase_rad"]
                - w * e.params["phase_origin_s"]) % (2 * np.pi)
    dp = abs(abs_phase(a) - abs_phase(b)) % (2 * np.pi)
    dp = min(dp, 2 * np.pi - dp)
    assert abs(dp - 1.2) < 0.45


def test_no_vibrato_slow_trend_rejected():
    sig = _vib_sig(1.3, 2.0, 3.0,
                   trend=lambda t: 80 * np.sin(np.pi * t / 1.3))
    assert _ev(sig) == []


def test_aperiodic_jitter_rejected():
    rng = np.random.default_rng(3)
    t = np.arange(0, 1.3 + HOP_S, HOP_S)
    cents = 6000 + rng.normal(0, 25, len(t)).cumsum() * 0.1 \
        + rng.normal(0, 20, len(t))
    ev = _ev(_sig(t, cents))
    assert ev == [] or ev[0].confidence < 0.45


# ---- R2.1-C/D: match states + compile consumes real spans -------------

def _pitd_on_grid(pitd, t):
    xs = np.asarray(pitd["xs"], dtype=float) * TICK_MS / 1000.0
    ys = np.asarray(pitd["ys"], dtype=float)
    if not len(xs):
        return np.full(len(t), np.nan)
    return np.interp(t, xs, ys, left=np.nan, right=np.nan)


def _dense_and_sigs(src_cents, neu_cents, dur=1.3):
    t = np.arange(0, dur + HOP_S, HOP_S)
    src = _sig(t, src_cents)
    neu = _sig(t, neu_cents)
    dense = {"times": t,
             "resid_consensus": src_cents - neu_cents,
             "resid_consistent": np.ones(len(t), bool)}
    return dense, src, neu


def test_compile_source_only_tail_vibrato():
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    vib = np.where(t >= 0.8, 50 * np.sin(2 * np.pi * 6.5 * (t - 0.8)), 0)
    dense, src, neu = _dense_and_sigs(6000 + vib, np.full(len(t), 6000.0),
                                      dur)
    vm = match_vibrato_events(detect_vibrato_events(src, [_note(dur)]),
                              detect_vibrato_events(neu, [_note(dur)]),
                              [_note(dur)])
    assert vm[0]["match_state"] == "source_only"
    assert vm[0]["recommended_representation"] == "note_vibrato"
    pitd, marks, _prov = compile_C3(dense, src, neu, [_note(dur)], 0, vm)
    assert 0 in marks
    assert abs(marks[0]["period"] - 1000 / 6.5) < 8
    # written depth is calibrated 1/0.69x so render amplitude matches
    assert abs(marks[0]["depth"] - 50 / 0.69) < 18
    # length comes from the real event span, not a fixed 65%
    assert abs(marks[0]["length"] - (dur - vm[0]["source_span_s"][0])
               / dur * 100) < 1.5
    assert marks[0]["length"] < 55.0


def test_compile_matched_does_not_double_add():
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    src_vib = np.where(t >= 0.8,
                       50 * np.sin(2 * np.pi * 6.5 * (t - 0.8)), 0)
    neu_vib = np.where(t >= 0.8,
                       30 * np.sin(2 * np.pi * 6.5 * (t - 0.8) + 0.4), 0)
    dense, src, neu = _dense_and_sigs(6000 + src_vib, 6000 + neu_vib, dur)
    vm = match_vibrato_events(detect_vibrato_events(src, [_note(dur)]),
                              detect_vibrato_events(neu, [_note(dur)]),
                              [_note(dur)])
    assert vm[0]["match_state"] == "matched"
    assert vm[0]["recommended_representation"] == "note_vibrato"
    pitd, marks, _prov = compile_C3(dense, src, neu, [_note(dur)], 0, vm)
    assert marks[0]["depth"] < 100

    # Algebraic render surrogate: neutral + PITD + rendered note-vibrato
    # must reconstruct SOURCE. This specifically catches omission of
    # -neutral modulation in the matched case.
    ctl = _pitd_on_grid(pitd, t)
    sv = vm[0]["source_vibrato"]
    w = 2 * np.pi * sv["rate_hz"]
    fit = marks[0]["depth"] * VIBRATO_DEPTH_GAIN * np.sin(
        w * (t - sv["phase_origin_s"]) + sv["phase_rad"])
    span = (t >= vm[0]["source_span_s"][0]) & \
           (t <= vm[0]["source_span_s"][1]) & ~np.isnan(ctl)
    recon = (6000 + neu_vib) + ctl + fit
    assert np.median(np.abs(recon[span] - (6000 + src_vib)[span])) < 15


def test_compile_neutral_only_suppression():
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    neu_vib = np.where(t >= 0.8,
                       40 * np.sin(2 * np.pi * 6.5 * (t - 0.8)), 0)
    dense, src, neu = _dense_and_sigs(np.full(len(t), 6000.0),
                                      6000 + neu_vib, dur)
    vm = match_vibrato_events(detect_vibrato_events(src, [_note(dur)]),
                              detect_vibrato_events(neu, [_note(dur)]),
                              [_note(dur)])
    assert vm[0]["match_state"] == "neutral_only"
    assert vm[0]["recommended_representation"] == "suppress_neutral"
    pitd, marks, _prov = compile_C3(dense, src, neu, [_note(dur)], 0, vm)
    # Suppression keeps the base note's vibrato marks unchanged: the
    # compiled project derives from the same base as the neutral render,
    # so its engine modulation recurs and the full residual cancels it.
    # Writing depth=0 instead would leave -mod_n in PITD with nothing to
    # cancel (L7-A first-render failure mode).
    assert 0 not in marks
    ctl = _pitd_on_grid(pitd, t)
    span = (t >= vm[0]["neutral_span_s"][0]) & \
           (t <= vm[0]["neutral_span_s"][1]) & ~np.isnan(ctl)
    recon = 6000 + neu_vib + ctl
    assert np.median(np.abs(recon[span] - 6000.0)) < 12
    assert np.percentile(np.abs(ctl[span]), 90) > 15


def test_compile_note_vibrato_accounts_for_base_vibrato():
    """Base note had its own engine vibrato (present in the neutral
    render). Compiling source vibrato onto it must write
    PITD = residual + V_base - V_compiled, so the render lands on SOURCE
    without the old engine term leaking through."""
    from agent2utau.expression.pitch_residual import _engine_vib_model
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    src_vib = np.where(t >= 0.8,
                       50 * np.sin(2 * np.pi * 6.5 * (t - 0.8) + 0.9), 0)
    base_marks = {"length": 70, "period": 150, "depth": 30, "in": 10,
                  "out": 10, "shift": 25, "drift": 0, "volLink": 0}
    Vb = _engine_vib_model(base_marks, 0.0, dur, t, VIBRATO_DEPTH_GAIN)
    dense, src, neu = _dense_and_sigs(6000 + src_vib, 6000 + Vb, dur)
    vm = match_vibrato_events(detect_vibrato_events(src, [_note(dur)]),
                              [], [_note(dur)])
    assert vm[0]["recommended_representation"] == "note_vibrato"
    pitd, marks, _prov = compile_C3(dense, src, neu, [_note(dur)], 0, vm,
                                  base_vibrato={0: base_marks})
    Vc = _engine_vib_model(marks[0], 0.0, dur, t, VIBRATO_DEPTH_GAIN)
    ctl = _pitd_on_grid(pitd, t)
    # render = (neutral minus its own engine vib) + PITD + compiled vib
    recon = (6000 + Vb) - Vb + ctl + Vc
    span = (t >= 0.8) & (t <= dur) & ~np.isnan(ctl)
    assert np.median(np.abs(recon[span] - (6000 + src_vib)[span])) < 15


def test_compile_c2_baseline_path_still_runs():
    """C2 is a frozen historical baseline and must remain callable.

    Turn-protection belongs to C3; C2 must not accidentally reference
    C3-only source/native-vibrato state.
    """
    dur = 0.30
    t = np.arange(0, dur + HOP_S, HOP_S)
    tri = np.maximum(0.0, 1.0 - np.abs(t - 0.15) / 0.08)
    src_c = 6000.0 + 20.0 * tri
    neu_c = np.full(len(t), 6000.0)
    dense, _src, _neu = _dense_and_sigs(src_c, neu_c, dur)
    dense["state"] = np.zeros(len(t), dtype=int)
    pitd, marks = compile_C2(dense, [_note(dur)], 0, [], max_err_c=10.0)
    assert marks == {}
    assert pitd["abbr"] == "pitd"
    assert len(pitd["xs"]) >= 2


def test_compile_c3_preserves_prominent_source_turn_below_error_budget():
    """A QA-significant SOURCE turn must not disappear only because the
    residual's vertical interpolation error is below max_err_c.

    Native vibrato spans are handled separately; this covers ordinary
    non-vibrato expression topology (L7-C simplifier-loss regression).
    """
    dur = 0.30
    t = np.arange(0, dur + HOP_S, HOP_S)
    # SOURCE has a clear 30c turn at 0.15s.  Neutral already follows most
    # of it, so the correction itself is only 8c — small enough that a
    # 10c vertical simplifier would normally erase the residual extremum.
    tri = np.maximum(0.0, 1.0 - np.abs(t - 0.15) / 0.08)
    src_c = 6000.0 + 30.0 * tri
    neu_c = 6000.0 + 22.0 * tri
    dense, src, neu = _dense_and_sigs(src_c, neu_c, dur)
    pitd, marks, _prov = compile_C3(
        dense, src, neu, [_note(dur)], 0, [], max_err_c=10.0)
    assert marks == {}
    xs_s = np.asarray(pitd["xs"], dtype=float) * TICK_MS / 1000.0
    # The source turn itself must survive as a PITD keypoint.
    assert np.min(np.abs(xs_s - 0.15)) <= 0.012


def test_mid_note_vibrato_stays_pitd():
    dur = 1.4
    t = np.arange(0, dur + HOP_S, HOP_S)
    vib = np.where((t >= 0.4) & (t <= 0.85),
                   45 * np.sin(2 * np.pi * 6.0 * (t - 0.4)), 0)
    dense, src, neu = _dense_and_sigs(6000 + vib, np.full(len(t), 6000.0),
                                      dur)
    n = _note(dur)
    vm = match_vibrato_events(detect_vibrato_events(src, [n]),
                              detect_vibrato_events(neu, [n]), [n])
    assert vm[0]["recommended_representation"] == "irregular_pitd"
    pitd, marks, _prov = compile_C3(dense, src, neu, [n], 0, vm)
    assert marks == {}                  # not forced into note vibrato


def test_tail_vibrato_that_stops_early_stays_pitd():
    dur = 1.3
    sig = _vib_sig(dur, 0.72, 1.16, rate=6.5, depth=50)
    ev = detect_vibrato_events(sig, [_note(dur)])
    assert ev
    vm = match_vibrato_events(ev, [], [_note(dur)])
    # note-vibrato cannot encode an event that ends materially before tail
    assert vm[0]["recommended_representation"] == "irregular_pitd"


def test_vibrato_does_not_bridge_invalid_evidence_hole():
    dur = 1.2
    t = np.arange(0, dur + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    v = (t >= 0.35) & (t <= 0.85)
    cents[v] += 50 * np.sin(2 * np.pi * 6.5 * (t[v] - 0.35))
    voiced = np.ones(len(t), dtype=bool)
    voiced[(t >= 0.55) & (t <= 0.72)] = False
    sig = _sig(t, cents, voiced=voiced)
    # each side of the evidence hole has too few cycles; the detector must
    # not interpolate validity and join them into one accepted event.
    assert detect_vibrato_events(sig, [_note(dur)]) == []


# ---- R2.1-L1: detector phase -> native OpenUtau shift -----------------

def test_compile_writes_native_shift_from_phase():
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    vib = np.where(t >= 0.8,
                   50 * np.sin(2 * np.pi * 6.5 * (t - 0.8) + 0.9), 0)
    dense, src, neu = _dense_and_sigs(6000 + vib, np.full(len(t), 6000.0),
                                      dur)
    vm = match_vibrato_events(detect_vibrato_events(src, [_note(dur)]),
                              [], [_note(dur)])
    assert vm[0]["recommended_representation"] == "note_vibrato"
    pitd, marks, prov = compile_C3(dense, src, neu, [_note(dur)], 0, vm)
    sv = vm[0]["source_vibrato"]
    ev_s = vm[0]["source_span_s"][0]
    expected = ((sv["phase_rad"]
                 + 2 * np.pi * sv["rate_hz"]
                 * (ev_s - sv["phase_origin_s"])) / (2 * np.pi)) % 1.0 * 100
    assert abs(marks[0]["shift"] - expected) < 1.5
    assert prov[0]["computed_shift_pct"] == marks[0]["shift"] or \
        abs(prov[0]["computed_shift_pct"] - expected) < 1.5


def test_compiled_engine_sine_matches_detector_phase():
    """OpenUtau semantics: phase arg = 2pi[(nPos-nStart)/nPeriod+shift/100].
    The compiled mark must reproduce the detected source phase, not leave
    a ~pi cancellation for closed-loop to rescue."""
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    vib = np.where(t >= 0.8,
                   50 * np.sin(2 * np.pi * 6.5 * (t - 0.8) + 0.9), 0)
    dense, src, neu = _dense_and_sigs(6000 + vib, np.full(len(t), 6000.0),
                                      dur)
    vm = match_vibrato_events(detect_vibrato_events(src, [_note(dur)]),
                              [], [_note(dur)])
    pitd, marks, prov = compile_C3(dense, src, neu, [_note(dur)], 0, vm)
    sv = vm[0]["source_vibrato"]
    mk = marks[0]
    n_start_t = dur * (1.0 - mk["length"] / 100.0)
    period_s = mk["period"] / 1000.0
    eng = np.sin(2 * np.pi * ((t - n_start_t) / period_s
                              + mk["shift"] / 100.0))
    det = np.sin(2 * np.pi * sv["rate_hz"]
                 * (t - sv["phase_origin_s"]) + sv["phase_rad"])
    lo, hi = vm[0]["source_span_s"]
    span = (t >= lo + 0.05) & (t <= hi - 0.05)   # avoid fade edges
    assert np.corrcoef(eng[span], det[span])[0, 1] > 0.97


# ---- R2.1-L3: evidence-bounded vibrato boundaries ----------------------

def test_vibrato_boundary_clamped_by_unvoiced_tail():
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    v = (t >= 0.40) & (t <= 0.95)
    cents[v] += 50 * np.sin(2 * np.pi * 6.5 * (t[v] - 0.40))
    voiced = np.ones(len(t), dtype=bool)
    voiced[t > 0.95] = False    # unvoiced inside the quarter-period window
    sig = _sig(t, cents, voiced=voiced)
    ev = _ev(sig, _note(dur))
    assert len(ev) == 1
    # extension must not cross the unvoiced region
    assert ev[0].end_s <= 0.96
    assert ev[0].params["boundary_end_reason"] in \
        ("voiced_or_confidence_gap", "segment_boundary")


def test_vibrato_boundary_stops_near_zero_return_on_fading_tail():
    """A fading vibrato tail should not force a full quarter-period extension.

    This test covers near-zero return only. It is intentionally NOT evidence
    of a true modulation-envelope/energy-collapse detector."""
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    v = (t >= 0.5) & (t <= 1.0)
    frac = (t[v] - 0.5) / 0.5
    env = 50 * np.clip(1.6 - 1.6 * frac, 0.0, 1.0)   # dies by ~0.81s... 
    env = np.where(frac < 0.625, 50.0, 50 * (1 - (frac - 0.625) / 0.375))
    cents[v] += env * np.sin(2 * np.pi * 6.5 * (t[v] - 0.5))
    sig = _sig(t, cents)
    ev = _ev(sig, _note(dur))
    assert len(ev) == 1
    assert ev[0].end_s < 1.15
    assert ev[0].params["boundary_end_reason"] in \
        ("zero_return", "quarter_period")


def test_vibrato_boundary_segment_clamp():
    """A voiced gap right after the last extremum clamps the boundary at
    the segment edge — never extends into another voiced segment."""
    dur = 1.4
    t = np.arange(0, dur + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    v = (t >= 0.6) & (t <= 1.05)
    cents[v] += 50 * np.sin(2 * np.pi * 6.5 * (t[v] - 0.6))
    voiced = np.ones(len(t), dtype=bool)
    voiced[(t > 1.07) & (t < 1.20)] = False     # 130ms gap -> new segment
    sig = _sig(t, cents, voiced=voiced)
    ev = _ev(sig, _note(dur))
    assert len(ev) == 1
    assert ev[0].end_s <= 1.08


def test_vibrato_asymmetric_waveform_still_detected():
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    v = t >= 0.55
    cents[v] += (45 * np.sin(2 * np.pi * 6.5 * (t[v] - 0.55))
                 + 15 * np.sin(4 * np.pi * 6.5 * (t[v] - 0.55)))
    ev = _ev(_sig(t, cents), _note(dur))
    assert len(ev) == 1
    assert abs(ev[0].params["rate_hz"] - 6.5) < 0.6


# ---- R2.1-L4: evidence vs stable cycle gates ---------------------------

def test_evidence_and_stable_cycles_reported_separately():
    """Weak leading half-cycle is trimmed: evidence count (raw chain)
    differs from stable count (trimmed run); both gates apply."""
    dur = 1.3
    t = np.arange(0, dur + HOP_S, HOP_S)
    cents = np.full(len(t), 6000.0)
    v = (t >= 0.5) & (t <= 1.3)
    env = np.where(t[v] < 0.5 + 0.5 / 6.5, 32.0, 50.0)  # weak first half
    cents[v] += env * np.sin(2 * np.pi * 6.5 * (t[v] - 0.5))
    ev = _ev(_sig(t, cents), _note(dur))
    assert len(ev) == 1
    p = ev[0].params
    assert p["evidence_cycle_count"] >= 2.5
    assert p["stable_cycle_count"] >= 2.0
    assert p["evidence_cycle_count"] >= p["stable_cycle_count"]


def test_short_raw_chain_rejected_by_evidence_gate():
    """Only ~2 real cycles: raw evidence below 2.5 must reject, even if
    the trimmed run could still pass a lower stable threshold."""
    dur = 1.3
    sig = _vib_sig(dur, 0.95, 1.24, rate=6.5, depth=50)  # ~1.9 cycles
    assert _ev(sig, _note(dur)) == []


def test_closed_loop_preserves_protected_portamento():
    """L7-B: lane-protected windows must keep v1's own keypoints
    verbatim — a global simplifier pass over mixed frames thins the
    portamento ramp and the render loses the event (P2 from_note=6
    matched->missing regression)."""
    from agent2utau.expression.contour import PitchEvent
    from agent2utau.expression.pitch_residual import closed_loop_update

    dur = 2.0
    t = np.arange(0, dur + HOP_S, HOP_S)
    note = _note(dur)
    # v1 pitd: flat 0 except a dense portamento ramp in [0.8, 1.0]s
    v1_t = np.arange(0.0, dur, 0.02)
    v1_y = np.zeros(len(v1_t))
    ramp = (v1_t >= 0.8) & (v1_t <= 1.0)
    v1_y[ramp] = -200.0 * (v1_t[ramp] - 0.8) / 0.2
    v1_y[v1_t > 1.0] = -200.0
    pitd = {"abbr": "pitd",
            "xs": (v1_t * 1000 / TICK_MS).astype(int).tolist(),
            "ys": v1_y.astype(int).tolist()}
    # source = render + constant +80c error everywhere
    src = _sig(t, np.full(len(t), 6080.0))
    rnd = _sig(t, np.full(len(t), 6000.0))
    port = PitchEvent(type="portamento", note_indices=[0],
                      start_s=0.8, end_s=1.0, confidence=1.0,
                      params={"from_note": 0})
    out = closed_loop_update(pitd, src, rnd, [note], 0,
                             protected_events=[port])
    xs = np.asarray(out["xs"]) * TICK_MS / 1000.0
    ys = np.asarray(out["ys"], dtype=float)
    # inside the protected window the corrected curve must equal v1's
    # ramp (within 1c rounding), not +80c and not a thinned chord
    for tt, vv in zip(v1_t[ramp][::3], v1_y[ramp][::3]):
        assert abs(np.interp(tt, xs, ys) - vv) <= 2.0, \
            f"protected portamento degraded at t={tt}"
    # unprotected region still gets the correction
    assert np.interp(0.4, xs, ys) > 50.0
    assert np.interp(1.5, xs, ys) > -200.0 + 50.0
