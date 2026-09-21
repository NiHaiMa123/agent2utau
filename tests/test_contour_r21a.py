"""R2.1-A regression tests: segment-safe contour/trend (plan §R2.1-A)."""
import numpy as np

from agent2utau.expression.contour import (
    ContourSignal, HOP_S, MIN_GAP_S, build_contour_signal,
    robust_pitch_trend, segment_ids, voiced_segments)


def _sig(times, cents, voiced, **kw):
    cents = np.asarray(cents, dtype=float)
    voiced = np.asarray(voiced, dtype=bool)
    valid = voiced & ~np.isnan(cents)
    return ContourSignal(
        times=np.asarray(times, dtype=float), cents=cents,
        raw_cents=cents.copy(), voiced=valid,
        confidence=np.where(valid, 1.0, 0.0),
        note_idx=np.full(len(times), -1, dtype=int),
        phoneme_idx=None, source="source", extractor="fcpe",
        segment_id=segment_ids(times, valid), **kw)


def test_segments_split_on_300ms_silence():
    t = np.arange(0, 2.0, HOP_S)
    cents = np.full(len(t), 6000.0)
    voiced = (t < 0.8) | (t >= 1.1)          # 300ms gap
    cents[~voiced] = np.nan
    segs = voiced_segments(t, voiced & ~np.isnan(cents))
    assert len(segs) == 2
    assert t[segs[0][1] - 1] <= 0.8 + 1e-9
    assert t[segs[1][0]] >= 1.1 - 1e-9


def test_trend_no_ramp_across_gap():
    t = np.arange(0, 2.0, HOP_S)
    cents = np.where(t < 0.8, 6000.0, 6500.0)
    voiced = (t < 0.8) | (t >= 1.1)
    cents[~voiced] = np.nan
    sig = _sig(t, cents, voiced)
    trend, mod = robust_pitch_trend(sig)
    # gap stays nan — no interpolated bridge
    assert np.all(np.isnan(trend[(t > 0.8) & (t < 1.1)]))
    # frames within 100ms of the gap edge keep their own level
    a_edge = (t >= 0.70) & (t <= 0.80)
    b_edge = (t >= 1.10) & (t <= 1.20)
    assert np.nanmax(np.abs(trend[a_edge] - 6000.0)) < 30.0
    assert np.nanmax(np.abs(trend[b_edge] - 6500.0)) < 30.0
    # segment interiors are flat
    mid = (t >= 0.2) & (t <= 0.6)
    assert np.nanmax(np.abs(trend[mid] - 6000.0)) < 5.0


def test_interior_hole_stays_in_segment():
    t = np.arange(0, 1.0, HOP_S)
    cents = np.full(len(t), 6000.0)
    voiced = np.ones(len(t), dtype=bool)
    voiced[40:45] = False                  # 50ms hole < MIN_GAP_S
    cents[~voiced] = np.nan
    segs = voiced_segments(t, voiced & ~np.isnan(cents))
    assert len(segs) == 1
    sig = _sig(t, cents, voiced)
    trend, _ = robust_pitch_trend(sig)
    assert np.isnan(trend[42])             # unvoiced frame stays nan
    assert abs(trend[39] - 6000.0) < 5.0
    assert abs(trend[45] - 6000.0) < 5.0


def test_phoneme_idx_filled():
    t = np.arange(0, 0.5, HOP_S)
    cents = np.full(len(t), 6000.0)
    phonemes = [{"abs_start_s": 0.0, "dur_s": 0.2, "symbol": "a"},
                {"abs_start_s": 0.2, "dur_s": 0.3, "symbol": "i"}]
    sig = _sig(t, cents, np.ones(len(t), bool))
    # rebuild through build_contour_signal to exercise the real path
    f0 = {"times": t, "f0_hz": 440.0 * np.ones(len(t)),
          "voiced": np.ones(len(t), bool)}
    notes = [{"lyric": "x", "tone": 69, "abs_start_s": 0.0, "dur_s": 0.5}]
    sig = build_contour_signal(f0, f0, notes, phonemes=phonemes,
                               t0_s=0.0, t1_s=0.5)
    assert sig.phoneme_idx is not None
    assert (sig.phoneme_idx[:20] == 0).all()
    assert (sig.phoneme_idx[20:50] == 1).all()
    assert sig.phoneme_idx[50] == -1     # t=0.5 is the right-open boundary
    assert sig.provenance["n_phonemes"] == 2


def test_segment_id_exposed():
    t = np.arange(0, 1.5, HOP_S)
    cents = np.full(len(t), 6000.0)
    voiced = (t < 0.5) | (t >= 0.7)
    cents[~voiced] = np.nan
    sig = _sig(t, cents, voiced)
    assert sig.segment_id is not None
    assert sig.segment_id[t < 0.5].max() == 0
    assert sig.segment_id[(t >= 0.7)].min() == 1
    assert (sig.segment_id[(t >= 0.5) & (t < 0.7)] == -1).all()
