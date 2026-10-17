"""Independent sample-clock, native DYN reconstruction and bounded PCM metrics."""
import math
import numpy as np

def dynamic_gain(layout):
    n=layout['samples']; gain=np.ones(n,np.float32); curve=layout['dynamic_curve']
    if curve is None:
        if layout['dynamic_end_ms']:raise ValueError('Unexpected DYN clock without curve')
        return gain
    curve=np.asarray(curve,np.float32); ends=layout['dynamic_end_ms']
    if len(curve)!=len(ends) or not np.isfinite(curve).all():raise ValueError('Invalid DYN layout')
    start=(layout['position_ms']-layout['leading_ms'])
    previous=0
    for i,end_ms in enumerate(ends):
        # Frozen 480tick/120bpm. Bound double representation to four ULPs.
        expected=(layout['dynamic_start_tick']+5*(i+1))*(60000/120/480)
        if abs(end_ms-expected)>4*max(math.ulp(expected),math.ulp(end_ms)):
            raise ValueError('DYN end clock differs from frozen project')
        end=min(int((end_ms-start)/1000*44100),n)
        if end<previous or previous<0:raise ValueError('DYN sample range reversed')
        if end>previous:
            a=curve[i]; b=curve[min(i+1,len(curve)-1)]
            offset=np.arange(end-previous,dtype=np.float32)
            factor=a+((b-a)*offset)/np.float32(end-previous)
            gain[previous:end]=factor
        previous=end
    return gain

def require_dynamics(raw,actual,gain):
    if raw.dtype!=np.float32 or actual.dtype!=np.float32 or gain.dtype!=np.float32 or not(raw.shape==actual.shape==gain.shape):
        raise ValueError('Wrong DYN array layout')
    if not np.isfinite(raw).all() or not np.isfinite(actual).all() or not np.isfinite(gain).all():
        raise ValueError('Nonfinite PCM or gain')
    if not np.array_equal(raw*gain,actual):raise ValueError('Actual DYN multiplication differs')

def interval_indices(interval,origin,n,sr=44100):
    a,b=interval
    if not math.isfinite(a+b+origin) or b<=a:raise ValueError('Invalid half-open interval')
    i,j=math.ceil((a-origin)*sr),math.ceil((b-origin)*sr)
    if i<0 or j>n or j<=i: return None
    return i,j

def level(samples):
    if not samples.size or not np.isfinite(samples).all():raise ValueError('Invalid metric samples')
    values=samples.astype(np.float64); rms=float(np.sqrt(np.mean(values*values)))
    peak=float(np.max(np.abs(values)))
    return dict(samples=len(samples),rms=rms,peak=peak,dbfs=None if rms==0 else 20*math.log10(rms),zero_energy=rms==0)

def centered_windows(samples,interval,origin,width_ms,hop_ms=5):
    if width_ms not in (30,50) or hop_ms!=5:raise ValueError('Frozen window widths/hop required')
    a,b=interval; width=width_ms/1000
    if b-a<width:return dict(status='unknown_short_window',centers_s=[],rms=[],peak=[])
    centers=[]; rms=[]; peak=[]; step=0
    while a+width/2+step*hop_ms/1000+width/2<=b:
        center=a+width/2+step*hop_ms/1000
        ix=interval_indices((center-width/2,center+width/2),origin,len(samples))
        if ix is None:return dict(status='unknown_outside_pcm',centers_s=[],rms=[],peak=[])
        m=level(samples[slice(*ix)]);centers.append(center);rms.append(m['rms']);peak.append(m['peak']);step+=1
    return dict(status='computed_proxy_only',centers_s=centers,rms=rms,peak=peak)

def require_finite_subfull(samples):
    if not samples.size or not np.isfinite(samples).all() or np.max(np.abs(samples))>=1:
        raise ValueError('Nonfinite or fullscale PCM; stop delivery')
