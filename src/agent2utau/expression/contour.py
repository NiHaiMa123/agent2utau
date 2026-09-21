"""Contour signal + robust trend/modulation decomposition (plan §9.1/§9.2).

A ContourSignal is ONE extractor's view of ONE audio (source vocal or
neutral render) on the shared absolute project timeline — never warped.

Segmentation contract (R2.1-A): contiguous voiced frames separated by
unvoiced/invalid runs shorter than MIN_GAP_S stay in one segment (the
holes are bridged for filtering); runs >= MIN_GAP_S split segments and
NO filter/trend may cross the boundary — trend is nan inside the gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

HOP_S = 0.010
MIN_GAP_S = 0.08          # unvoiced run >= this splits a segment
EDGE_PAD_S = 0.05         # declared padding used inside a segment edge


@dataclass
class ContourSignal:
    times: np.ndarray            # seconds, absolute project time
    cents: np.ndarray            # filtered contour (nan where unvoiced)
    raw_cents: np.ndarray        # unfiltered contour for diagnostics
    voiced: np.ndarray           # bool
    confidence: np.ndarray       # 0..1, from extractor-family agreement
    note_idx: np.ndarray         # index into notes, -1 = gap
    phoneme_idx: np.ndarray | None   # index into phonemes, -1 = gap
    source: str                  # "source" | "neutral" | "render"
    extractor: str               # "fcpe" | "rmvpe" | ...
    segment_id: np.ndarray | None = None   # voiced-segment id, -1 = gap
    provenance: dict = field(default_factory=dict)


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


def voiced_segments(times, valid, min_gap_s=MIN_GAP_S):
    """[(lo, hi)) index spans of contiguous valid frames.

    A run of invalid frames >= min_gap_s ends the segment; shorter runs
    are interior holes and stay inside the segment.
    """
    times = np.asarray(times, dtype=float)
    valid = np.asarray(valid, dtype=bool)
    n = len(times)
    segs = []
    i = 0
    while i < n:
        if not valid[i]:
            i += 1
            continue
        lo = i
        j = i
        while j < n:
            if valid[j]:
                j += 1
                continue
            k = j
            while k < n and not valid[k]:
                k += 1
            gap = (times[k - 1] - times[j]) + HOP_S if k < n else np.inf
            if gap >= min_gap_s:
                break
            j = k                       # interior hole: keep going
        segs.append((lo, j))
        i = j
    return segs


def segment_ids(times, valid, min_gap_s=MIN_GAP_S):
    seg = np.full(len(times), -1, dtype=int)
    for sid, (lo, hi) in enumerate(voiced_segments(times, valid, min_gap_s)):
        seg[lo:hi] = sid
    return seg


def _median3_segmented(cents, valid, seg_id):
    """3-frame median restricted to same-segment valid frames."""
    out = np.full(len(cents), np.nan)
    for i in range(len(cents)):
        if not valid[i]:
            continue
        sid = seg_id[i]
        w = [cents[k] for k in (i - 1, i, i + 1)
             if 0 <= k < len(cents) and valid[k] and seg_id[k] == sid]
        out[i] = float(np.median(w))
    return out


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

    valid = Pok & ~np.isnan(P)
    seg_id = segment_ids(g, valid)
    cents = _median3_segmented(P, valid, seg_id)

    note_idx = np.full(len(g), -1, dtype=int)
    for i, n in enumerate(notes):
        s, e = n["abs_start_s"], n["abs_start_s"] + n["dur_s"]
        note_idx[(g >= s) & (g < e)] = i

    phoneme_idx = None
    if phonemes is not None:
        phoneme_idx = np.full(len(g), -1, dtype=int)
        for i, ph in enumerate(phonemes):
            ps = ph.get("abs_start_s", ph.get("start_s"))
            pe = ph.get("abs_end_s")
            if pe is None:
                pe = ps + ph.get("dur_s", 0.0)
            phoneme_idx[(g >= ps) & (g < pe)] = i

    return ContourSignal(
        times=g, cents=cents, raw_cents=P, voiced=valid, confidence=conf,
        note_idx=note_idx, phoneme_idx=phoneme_idx, source=source,
        extractor=extractor, segment_id=seg_id,
        provenance={
            "hop_s": HOP_S, "min_gap_s": MIN_GAP_S,
            "prefilter": "median3_segmented",
            "n_segments": int(seg_id.max() + 1),
            "disagree_full_c": disagree_full_c,
            "n_phonemes": 0 if phonemes is None else len(phonemes)})


def _fill_segment(times, cents, valid, lo, hi):
    """Linear interp interior holes inside [lo,hi); no cross-gap fill."""
    idx = np.arange(lo, hi)
    ok = valid[lo:hi] & ~np.isnan(cents[lo:hi])
    filled = cents[lo:hi].copy()
    if ok.sum() >= 2:
        filled[~ok] = np.interp(idx[~ok], idx[ok], cents[lo:hi][ok])
    elif ok.sum() == 1:
        filled[~ok] = cents[lo:hi][ok][0]
    return filled


def robust_pitch_trend(contour: ContourSignal, cutoff_hz=3.0):
    """Zero-phase-ish trend/modulation split, per voiced segment.

    Savitzky-Golay (window ~ 1/cutoff, poly 3) applied inside each voiced
    segment only — never across a >= MIN_GAP_S unvoiced break. Interior
    holes are linearly filled before filtering; gap frames stay nan.
    Very short segments fall back to a degree-1 polyfit trend.
    Returns (trend_cents, modulation_cents).
    """
    from scipy.signal import savgol_filter
    t, c, v = contour.times, contour.cents, contour.voiced
    seg = contour.segment_id
    if seg is None:
        seg = segment_ids(t, v & ~np.isnan(c))
    trend = np.full(len(t), np.nan)
    mod = np.full(len(t), np.nan)
    win_full = max(5, int(round(1.0 / cutoff_hz / HOP_S)) | 1)
    for lo, hi in voiced_segments(t, v & ~np.isnan(c)):
        n = hi - lo
        filled = _fill_segment(t, c, v, lo, hi)
        if n < 5:
            tr = np.full(n, float(np.nanmedian(filled)))
        else:
            win = min(win_full, n if n % 2 == 1 else n - 1)
            if win >= 5:
                tr = savgol_filter(filled, win, 3, mode="interp")
            else:
                k = np.arange(n, dtype=float)
                p = np.polyfit(k, filled, 1)
                tr = np.polyval(p, k)
        tr[~v[lo:hi]] = np.nan
        trend[lo:hi] = tr
        mod[lo:hi] = np.where(v[lo:hi], filled - tr, np.nan)
    return trend, mod
