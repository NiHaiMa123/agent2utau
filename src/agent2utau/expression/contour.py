"""Contour signal + robust trend/modulation decomposition (plan §9.1/§9.2).

A ContourSignal is ONE extractor's view of ONE audio (source vocal or
neutral render) on the shared absolute project timeline — never warped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

HOP_S = 0.010


@dataclass
class ContourSignal:
    times: np.ndarray            # seconds, absolute project time
    cents: np.ndarray            # filtered contour (nan where unvoiced)
    raw_cents: np.ndarray        # unfiltered contour for diagnostics
    voiced: np.ndarray           # bool
    confidence: np.ndarray       # 0..1, from extractor-family agreement
    note_idx: np.ndarray         # index into notes, -1 = gap
    phoneme_idx: np.ndarray | None
    source: str                  # "source" | "neutral" | "render"
    extractor: str               # "fcpe" | "rmvpe" | ...


@dataclass
class PitchEvent:
    type: str                    # stable/scoop/overshoot/portamento/ornament/
                                 # vibrato/noise/artifact
    note_indices: list
    start_s: float
    end_s: float
    confidence: float
    params: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)


def _f0_arrays(f0):
    from agent2utau.analysis.f0 import hz_to_midi
    return (np.asarray(f0["times"], dtype=float),
            hz_to_midi(np.asarray(f0["f0_hz"])) * 100.0,
            np.asarray(f0["voiced"], dtype=bool))


def _sample(grid, times, vals, voiced):
    v = np.interp(grid, times, vals, left=np.nan, right=np.nan)
    ok = np.interp(grid, times, voiced.astype(float),
                   left=0.0, right=0.0) > 0.5
    return v, ok


def build_contour_signal(f0_primary, f0_secondary, notes, phonemes=None,
                         t0_s=None, t1_s=None, extractor="fcpe",
                         source="source", disagree_full_c=300.0):
    """Uniform 10ms grid contour for one signal with a second extractor as
    confidence evidence (agreement -> 1, full-octave disagreement -> 0)."""
    pt, pc, pv = _f0_arrays(f0_primary)
    st_, sc, sv = _f0_arrays(f0_secondary)
    if t0_s is None:
        t0_s = max(pt[0], st_[0])
    if t1_s is None:
        t1_s = min(pt[-1], st_[-1])
    g = t0_s + np.arange(int(round((t1_s - t0_s) / HOP_S)) + 1) * HOP_S

    P, Pok = _sample(g, pt, pc, pv)
    S, Sok = _sample(g, st_, sc, sv)
    conf = np.where(Pok & Sok,
                    np.clip(1.0 - np.abs(P - S) / disagree_full_c, 0, 1),
                    np.where(Pok, 0.4, 0.0))

    cents = P.copy()
    # declared robust smoothing only: 3-frame median kills single-frame spikes
    ok = Pok.copy()
    med = cents.copy()
    kern = 3
    for i in range(len(cents)):
        lo, hi = max(0, i - kern // 2), min(len(cents), i + kern // 2 + 1)
        w = cents[lo:hi][ok[lo:hi]]
        med[i] = np.median(w) if len(w) else np.nan
    cents = med
    cents[~Pok] = np.nan

    note_idx = np.full(len(g), -1, dtype=int)
    for i, n in enumerate(notes):
        s, e = n["abs_start_s"], n["abs_start_s"] + n["dur_s"]
        note_idx[(g >= s) & (g < e)] = i
    return ContourSignal(times=g, cents=cents, raw_cents=P, voiced=Pok,
                         confidence=conf, note_idx=note_idx,
                         phoneme_idx=None, source=source,
                         extractor=extractor)


def _fill_voiced(times, cents, voiced):
    """Linear interp across unvoiced holes for filtering; returns filled."""
    ok = voiced & ~np.isnan(cents)
    if ok.sum() < 4:
        return cents.copy()
    return np.interp(times, times[ok], cents[ok])


def robust_pitch_trend(contour: ContourSignal, cutoff_hz=3.0):
    """Zero-phase-ish trend/modulation split.

    Savitzky-Golay (window ~ 1/cutoff, poly 3, interp edges) on the
    voiced-filled contour; unvoiced frames restored to nan afterwards.
    Returns (trend_cents, modulation_cents).
    """
    from scipy.signal import savgol_filter
    t, c, v = contour.times, contour.cents, contour.voiced
    filled = _fill_voiced(t, c, v)
    win = max(5, int(round(1.0 / cutoff_hz / HOP_S)) | 1)
    win = min(win, len(filled) - 1 if (len(filled) - 1) % 2 == 1
              else len(filled) - 2)
    if win < 5:
        trend = filled.copy()
    else:
        trend = savgol_filter(filled, win, 3, mode="interp")
    mod = filled - trend
    trend[~v] = np.nan
    mod[~v] = np.nan
    return trend, mod
