"""Rhythm evidence checks before phonetic/expression mapping.

These checks nominate conflicts; they do not automatically lengthen words or
classify source F0 as wrong. A fixed score clock needs independent anchors.
"""
from __future__ import annotations

import numpy as np


def fixed_recording_shift(reference_s, recording_s, *, residual_limit_s,
                          coverage_bins=4, minimum_per_bin=4):
    """Estimate one recording shift, checking every temporal region separately.

    Caller supplies verified corresponding musical anchors, not arbitrary
    nearest syllables. Tempo changes or incompatible takes must not be hidden
    with per-word warping. Bounds are task evidence tolerances, not style rules.
    """
    ref=np.asarray(reference_s,dtype=float);rec=np.asarray(recording_s,dtype=float)
    if ref.ndim!=1 or rec.shape!=ref.shape or len(ref)<coverage_bins*minimum_per_bin:
        raise ValueError('Insufficient corresponding rhythm anchors')
    if not np.isfinite(ref).all() or not np.isfinite(rec).all() or np.ptp(ref)<=0:
        raise ValueError('Invalid rhythm clock anchors')
    offsets=rec-ref;shift=float(np.median(offsets));residual=offsets-shift
    # All supplied anchor pairs are independently bound; do not silently drop
    # inconvenient regions after choosing the clock.
    if np.max(abs(residual))>residual_limit_s:
        raise ValueError('A single recording shift is unsupported; review take/tempo/anchors')
    bins=np.minimum(((ref-ref.min())/np.ptp(ref)*coverage_bins).astype(int),coverage_bins-1)
    regions=[]
    for i in range(coverage_bins):
        m=bins==i
        if m.sum()<minimum_per_bin:
            raise ValueError('Recording clock lacks distributed musical support')
        regions.append(dict(region=i,anchors=int(m.sum()),reference_s=[float(ref[m].min()),float(ref[m].max())],max_abs_residual_s=float(np.max(abs(residual[m]))),median_residual_s=float(np.median(residual[m]))))
    return dict(shift_s=shift,scale=1.,anchors=len(ref),max_abs_residual_s=float(np.max(abs(residual))),regions=regions)


def syllable_timing_conflicts(reference_vowel_s, target_vowel_s, *,
                             duration_ratio_bounds, next_reference_s=None,
                             next_target_s=None, boundary_limit_s=None):
    """Compare a matched syllable and its following boundary in a shared clock.

    Ratio bounds only surface review candidates. A legitimately different
    performance may pass review with different durations. No mutation here.
    """
    a,b=map(float,reference_vowel_s);c,d=map(float,target_vowel_s)
    if b<=a or d<=c:raise ValueError('Nonpositive vowel support')
    ratio=(d-c)/(b-a);lo,hi=duration_ratio_bounds
    reasons=[]
    if ratio<lo:reasons.append('vowel_compressed')
    if ratio>hi:reasons.append('vowel_expanded')
    boundary_delta=None
    if next_reference_s is not None and next_target_s is not None:
        boundary_delta=float(next_target_s-next_reference_s)
        if boundary_limit_s is not None and abs(boundary_delta)>boundary_limit_s:
            reasons.append('following_word_boundary_displaced')
    return dict(duration_ratio=ratio,following_boundary_delta_s=boundary_delta,review_reasons=reasons)
