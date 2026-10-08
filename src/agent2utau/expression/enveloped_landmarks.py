"""Physical-clock extrema with independent smooth support envelope.

Landmarks include the continuation outside the fade, so truncating support
does not stretch the last half-wave. Values are actual offsets, not half-ranges.
"""
import numpy as np
from .curve_components import compose_curve


def enveloped_landmarks(times, clock, values, start, attack_end, release_start, end, slopes=None):
    t=np.asarray(times,float);x=np.asarray(clock,float);y=np.asarray(values,float)
    if not start<attack_end<=release_start<end:
        raise ValueError('Invalid landmark envelope')
    if len(x)!=len(y) or len(x)<(3 if slopes is None else 2) or np.any(np.diff(x)<=0) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Invalid phase landmarks')
    if x[0]>start or x[-1]<end:
        raise ValueError('Phase continuation must cover complete envelope support')
    # Zero extrema slopes preserve the supplied crest/trough order. Smooth
    # amplitude fading multiplies this continuing curve; phase is never retimed.
    wave=np.zeros(t.shape);mask=(t>=start)&(t<=end)
    derivatives=np.zeros(len(x)) if slopes is None else np.asarray(slopes,float)
    if derivatives.shape!=x.shape or not np.isfinite(derivatives).all():
        raise ValueError('Invalid landmark slopes')
    wave[mask]=compose_curve(t[mask],x,y,derivatives)
    def smooth(u):
        z=np.clip(u,0,1);return z*z*z*(10+z*(-15+6*z))
    env=smooth((t-start)/(attack_end-start))*smooth((end-t)/(end-release_start))
    return wave*env
