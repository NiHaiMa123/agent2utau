"""R2.1-E/F/G/I/J regression tests: onset/portamento/ornament/match/QA."""
import numpy as np

from agent2utau.expression.contour import (
    ContourSignal, HOP_S, segment_ids)
from agent2utau.expression.contour_qa import (
    contour_position_metrics, turning_point_metrics)
from agent2utau.expression.events import (
    PitchEvent, detect_onset_events, detect_ornament_events,
    detect_portamento_events, detect_vibrato_events, match_pitch_events)


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
    cents = np.where(t < 0.5, 6000.0, 6400.0)
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
