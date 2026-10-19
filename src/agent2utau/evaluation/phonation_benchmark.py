"""Deterministic engineering fixtures, with known *digital* component ratios.

These signals are not physiological vowels or human virtual/firmness labels.
All gain/noise descendants of a context share its split. No song inputs.
"""
from dataclasses import dataclass, asdict
from itertools import product
import hashlib

import numpy as np


@dataclass(frozen=True)
class SignalCase:
    midi: int
    filter_id: str
    motion: str
    snr_db: float
    gain_db: float
    seed: int

    @property
    def context_id(self):
        return f'm{self.midi}-{self.filter_id}-{self.motion}-s{self.seed}'

    @property
    def id(self):
        return f'{self.context_id}-n{self.snr_db:g}-g{self.gain_db:g}'

    @property
    def split(self):
        return 'holdout' if self.midi == 71 or self.seed == 205 else 'development'


def cases():
    return [SignalCase(*v) for v in product(
        [57, 64, 71], ['A', 'B', 'C'], ['steady', 'glide', 'vibrato'],
        [0., 10., 25.], [-30., -18.], [104, 205])]


def generate(case, sr=24000, duration_s=.45):
    """Filter components separately, normalize RMS, then mix at declared SNR.

    The common filter deliberately changes spectral shape. Its names carry no
    phoneme identity. Constant gains are separate descendants, not new labels.
    """
    if (sr < 16000 or duration_s < .2 or not np.isfinite(duration_s)
            or case.filter_id not in {'A','B','C'}
            or case.motion not in {'steady','glide','vibrato'}
            or not np.isfinite([case.midi,case.snr_db,case.gain_db]).all()
            or not 0 <= case.midi <= 127 or not -60 <= case.snr_db <= 80
            or not -60 <= case.gain_db <= -10):
        raise ValueError('Unsupported engineering fixture')
    t=np.arange(round(sr*duration_s))/sr
    cents=np.zeros(len(t))
    if case.motion=='glide':cents=1200*(t/duration_s-.5)
    if case.motion=='vibrato':cents=140*np.sin(2*np.pi*7*t)
    f0=440*2**((case.midi-69)/12+cents/1200)
    phase=2*np.pi*np.cumsum(f0)/sr
    periodic=sum(np.sin(k*phase+.19*k)/(k**1.25) for k in range(1, int(sr/(2*f0.max()))))
    rng=np.random.default_rng(case.seed)
    noise=rng.normal(size=len(t))
    freq=np.fft.rfftfreq(len(t),1/sr)
    resonances={'A':[(600,180),(1400,250),(2800,450)],
                'B':[(350,100),(2300,160),(3400,300)],
                'C':[(850,120),(1200,150),(4100,230)]}[case.filter_id]
    response=.025+sum(np.exp(-.5*((freq-f)/width)**2) for f,width in resonances)
    def filtered(x):
        y=np.fft.irfft(np.fft.rfft(x)*response,n=len(x));y-=y.mean()
        return y/np.sqrt(np.mean(y*y))
    p=filtered(periodic);n=filtered(noise)*10**(-case.snr_db/20)
    y=p+n;gain=10**(case.gain_db/20)/np.sqrt(np.mean(y*y));y*=gain
    if np.max(abs(y))>=.999:raise ValueError('Fixture would clip')
    truth=dict(**asdict(case),id=case.id,context_id=case.context_id,split=case.split,
               output_component_snr_db=float(20*np.log10(np.linalg.norm(p)/np.linalg.norm(n))),
               achieved_rms_dbfs=float(20*np.log10(np.sqrt(np.mean(y*y)))),
               waveform_sha256=hashlib.sha256(y.tobytes()).hexdigest(),
               perceptual_label=None,physiological_label=None)
    return y,t,f0,truth


def measure(case, feature_function, config):
    """Oracle F0 is explicitly engineering truth, never two native detectors."""
    y,t,f0,truth=generate(case);rows=[];excluded={}
    for center in np.arange(.1,.351,.01):
        pitch=float(np.interp(center,t,f0));duration=max(config.min_window_s,config.periods/pitch)
        lo,hi=center-duration/2,center+duration/2
        mask=(t>=lo)&(t<=hi)
        if duration>config.max_window_s or 1200*np.log2(f0[mask].max()/f0[mask].min())>config.local_f0_span_c:
            excluded['nonstationary_or_unsupported_window']=excluded.get('nonstationary_or_unsupported_window',0)+1
            continue
        r=feature_function(y[round(lo*24000):round(hi*24000)],24000,pitch,config)
        if r['status']=='measured':rows.append(r)
        else:excluded[r['reason']]=excluded.get(r['reason'],0)+1
    numeric=['periodicity_ratio_db_proxy','highband_flatness_db','output_spectral_tilt_db_oct','rms_dbfs']
    return dict(truth=truth,reliable_frames=len(rows),excluded=excluded,
                features={k:float(np.median([r[k] for r in rows])) for k in numeric} if rows else None)
