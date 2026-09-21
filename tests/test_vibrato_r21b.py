"""R2.1-B/C/D regression tests: real vibrato events + 3-state compile."""
import numpy as np

from agent2utau.expression.contour import (
    ContourSignal, HOP_S, robust_pitch_trend, segment_ids)
from agent2utau.expression.events import (
    detect_vibrato_events, match_vibrato_events)
from agent2utau.expression.pitch_residual import compile_C3


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
    assert e.params["stable_cycle_count"] >= 2.5


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
    pitd, marks = compile_C3(dense, src, neu, [_note(dur)], 0, vm)
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
    if vm[0]["recommended_representation"] == "note_vibrato":
        pitd, marks = compile_C3(dense, src, neu, [_note(dur)], 0, vm)
        # override writes SOURCE depth once — not source+neutral stacked
        assert marks[0]["depth"] < 100


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
    pitd, marks = compile_C3(dense, src, neu, [_note(dur)], 0, vm)
    assert marks[0]["depth"] == 0
    # residual inside the suppressed span must not carry -neutral vibrato
    span = (dense["times"] >= vm[0]["neutral_span_s"][0]) & \
           (dense["times"] <= vm[0]["neutral_span_s"][1])
    assert np.nanmax(np.abs(np.asarray(pitd["ys"]))) < 200


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
    pitd, marks = compile_C3(dense, src, neu, [n], 0, vm)
    assert marks == {}                  # not forced into note vibrato
