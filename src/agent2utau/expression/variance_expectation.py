"""Experimental conditional expectation of joint DiffSinger variance draws.

Reduces dependence on one stochastic prediction while retaining conditioning
on actual pitch/phones/durations/speaker. No authored target, per-word rule or
implicit alignment. Dispersion is diagnostic, not a perceptual confidence score.
"""
from collections.abc import Sequence
import numpy as np

CHANNELS=('breathiness','voicing','tension')


def gaussian_frame_noise(seed: int, channels: int, bins: int, frames: int) -> np.ndarray:
    """Frame-major draw: extending a phrase preserves all earlier noise frames.

    Neither another song's longest phrase nor batch packing changes this draw.
    It keeps Gaussian sampling; reproducibility is not naturalness acceptance.
    """
    if min(channels,bins,frames)<1:
        raise ValueError('Positive noise dimensions required')
    x=np.random.default_rng(seed).standard_normal((frames,1,channels,bins)).astype(np.float32)
    return np.ascontiguousarray(x.transpose(1,2,3,0))


def variance_expectation(draws: Sequence[dict], condition_sha256: str) -> dict:
    """Average identically conditioned, uniquely seeded joint predictions.

    Caller hashes ALL model conditions and weights except noise and binds each
    draw to that hash. Native frame clocks must be exactly equal; never align or
    pool changed pitch/context. The estimate is a finite-draw model expectation,
    not a learned human expression or a validated inverse control.
    """
    if len(draws)<3:
        raise ValueError('At least three unique draws are required')
    if len(condition_sha256)!=64:
        raise ValueError('A SHA256 condition binding is required')
    ordered=sorted(draws,key=lambda d:d['seed'])
    if len({d['seed'] for d in ordered})!=len(ordered):
        raise ValueError('Duplicate random seeds are not independent draws')
    clock=np.asarray(ordered[0]['times_ms'],dtype=np.float64)
    if clock.ndim!=1 or len(clock)<2 or not np.isfinite(clock).all() or np.any(np.diff(clock)<=0):
        raise ValueError('Invalid native frame clock')
    for d in ordered:
        if d['condition_sha256']!=condition_sha256:
            raise ValueError('Changed conditioning cannot be pooled')
        if not np.array_equal(np.asarray(d['times_ms']),clock):
            raise ValueError('Changed frame clock cannot be aligned implicitly')
        if set(d['values'])!=set(CHANNELS):
            raise ValueError('Joint variance channels are required')
    mean={};spread={}
    for channel in CHANNELS:
        x=np.asarray([d['values'][channel] for d in ordered],dtype=np.float64)
        if x.shape!=(len(ordered),len(clock)) or not np.isfinite(x).all():
            raise ValueError('Invalid variance draw')
        mean[channel]=np.mean(x,axis=0).astype(np.float32)
        spread[channel]=np.std(x,axis=0,ddof=1).astype(np.float32)
    return dict(schema='conditional-variance-expectation-1',status='experimental',
                condition_sha256=condition_sha256,times_ms=clock.copy(),
                seeds=[d['seed'] for d in ordered],mean=mean,sample_std=spread,
                independent_songs=0,training_performed=False,
                limits=['Finite-draw expectation is not a human target or style fit.',
                        'Sample dispersion measures stochastic variability, not perceptual confidence.',
                        'Acoustic-stage stochasticity is outside this predictor aggregation.'])
