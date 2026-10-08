"""Continuous multi-function renderer with explicit, caller-provided parameters.

This defines the mathematical output representation; it does not identify
gestures or predict Baishuo expression parameters from an input song.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.interpolate import CubicHermiteSpline

def _smooth(u):
    v=np.clip(u,0.,1.)
    return v*v*(3-2*v)

@dataclass(frozen=True)
class LocalGesture:
    start_s:float
    peak_s:float
    end_s:float
    amplitude_c:float
    label:str='unclassified'

    def evaluate(self,t):
        if not self.start_s<self.peak_s<self.end_s:raise ValueError('gesture times must increase')
        t=np.asarray(t,float)
        rising=_smooth((t-self.start_s)/(self.peak_s-self.start_s))
        falling=1-_smooth((t-self.peak_s)/(self.end_s-self.peak_s))
        return self.amplitude_c*np.where(t<=self.peak_s,rising,falling)

@dataclass(frozen=True)
class VibratoSegment:
    start_s:float
    attack_end_s:float
    release_start_s:float
    end_s:float
    depth_start_c:float
    depth_end_c:float
    rate_start_hz:float
    rate_end_hz:float
    phase_rad:float=0.

    def evaluate(self,t):
        if not self.start_s<self.attack_end_s<=self.release_start_s<self.end_s:
            raise ValueError('ordered attack, sustain and release required')
        if min(self.depth_start_c,self.depth_end_c)<0 or min(self.rate_start_hz,self.rate_end_hz)<=0:
            raise ValueError('nonnegative depth and positive frequency required')
        t=np.asarray(t,float);x=t-self.start_s;duration=self.end_s-self.start_s
        q=np.clip(x/duration,0,1)
        envelope=_smooth(x/(self.attack_end_s-self.start_s))*(1-_smooth((t-self.release_start_s)/(self.end_s-self.release_start_s)))
        depth=((1-q)*self.depth_start_c+q*self.depth_end_c)*envelope
        # Integrate frequency in seconds. Multiplying f(t)*t doubles chirp rate.
        phase=self.phase_rad+2*np.pi*(self.rate_start_hz*x+.5*(self.rate_end_hz-self.rate_start_hz)*x*x/duration)
        return depth*np.sin(phase)


def compose_curve(times,anchor_times,anchor_cents,anchor_slopes_c_per_s,*,gestures=(),vibratos=(),voiced=None):
    """C1 base plus overlapping C1 finite-support events, with explicit UV output.

    Adjacent base spans share value AND slope at each anchor. Unknown phonetic
    effects are not silently modeled as ornaments; no random jitter is added.
    A gap must be represented by voiced=False; values there stay NaN.
    """
    t=np.asarray(times,float);a=np.asarray(anchor_times,float);y=np.asarray(anchor_cents,float);s=np.asarray(anchor_slopes_c_per_s,float)
    if t.ndim!=1 or not np.isfinite(t).all() or np.any(np.diff(t)<=0):raise ValueError('increasing finite sample clock required')
    if a.ndim!=1 or len(a)<2 or a.shape!=y.shape or a.shape!=s.shape or not np.isfinite(np.r_[a,y,s]).all() or np.any(np.diff(a)<=0):
        raise ValueError('matching finite anchors and slopes on an increasing clock required')
    if len(t) and (t[0]<a[0] or t[-1]>a[-1]):raise ValueError('base anchors must cover requested clock')
    curve=CubicHermiteSpline(a,y,s)(t)
    for event in (*gestures,*vibratos):curve+=event.evaluate(t)
    if voiced is not None:
        mask=np.asarray(voiced,bool)
        if mask.shape!=t.shape:raise ValueError('voicing mask shape mismatch')
        curve=np.where(mask,curve,np.nan)
    return curve
