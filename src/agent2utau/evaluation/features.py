"""Descriptive features of explicit samples; no plans or musical selectors."""
from dataclasses import asdict, dataclass
import numpy as np
from scipy.signal import find_peaks


@dataclass(frozen=True)
class Thresholds:
    prominence_c: float = 6.0
    min_window_s: float = 0.15
    min_samples: int = 8
    max_gap_s: float = 0.04
    min_cycle_hz: float = 3.0
    max_cycle_hz: float = 12.0
    jump_c: float = 80.0
    slope_change_c_per_s: float = 18000.0
    coupling_abs_r: float = 0.9
    redundancy_error_units: float = 1.0

    def __post_init__(self):
        if any(not np.isfinite(v) or v <= 0 for v in asdict(self).values()):
            raise ValueError('Thresholds must be finite and positive')
        if self.min_cycle_hz >= self.max_cycle_hz or not 0 < self.coupling_abs_r <= 1:
            raise ValueError('Invalid cycle/correlation range')
        if not isinstance(self.min_samples, int) or self.min_samples < 3:
            raise ValueError('min_samples must be an integer >=3')


def shape_features(times, cents, cfg=Thresholds()):
    t=np.asarray(times, float);y=np.asarray(cents, float)
    base=dict(samples=len(t),duration_s=float(t[-1]-t[0]) if t.ndim==1 and len(t) and np.all(np.isfinite(t)) else 0.)
    if t.ndim!=1 or y.ndim!=1 or len(t)!=len(y) or not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)):
        return dict(base,status='unknown',reason='invalid_samples')
    if len(t)<cfg.min_samples or base['duration_s']<cfg.min_window_s:
        return dict(base,status='unknown',reason='short_support')
    dt=np.diff(t)
    if np.any(dt<=0) or np.max(dt)>cfg.max_gap_s:
        return dict(base,status='unknown',reason='nonmonotonic_or_missing_samples')
    x=t-t[0];slope,intercept=np.polyfit(x,y,1);residual=y-(slope*x+intercept)
    peaks,_=find_peaks(residual,prominence=cfg.prominence_c)
    valleys,_=find_peaks(-residual,prominence=cfg.prominence_c)
    extrema=[]
    for i,kind in sorted([(int(i),'peak') for i in peaks]+[(int(i),'valley') for i in valleys]):
        if extrema and extrema[-1][1]==kind:
            old=extrema[-1][0]
            if (residual[i]>residual[old])==(kind=='peak'): extrema[-1]=(i,kind)
        else:extrema.append((i,kind))
    cycles=[]
    for (a,k),(b,_),(c,k2) in zip(extrema,extrema[1:],extrema[2:]):
        if k!='peak' or k2!='peak':continue
        hz=1/(t[c]-t[a]);amplitude=float((residual[a]+residual[c])/2-residual[b])
        if cfg.min_cycle_hz<=hz<=cfg.max_cycle_hz and amplitude>=cfg.prominence_c:
            cycles.append(dict(start_s=float(t[a]),valley_s=float(t[b]),end_s=float(t[c]),hz=float(hz),peak_to_trough_c=amplitude,asymmetry=float((t[b]-t[a])/(t[c]-t[a]))))
    amplitudes=[c['peak_to_trough_c'] for c in cycles];rates=[c['hz'] for c in cycles]
    span=float(np.ptp(residual));rawspan=float(np.ptp(y))
    morphology='oscillatory_candidate' if len(cycles)>=2 else ('platform' if rawspan<cfg.prominence_c else ('drift' if span<cfg.prominence_c else 'finite_movement'))
    return dict(base,status='evaluated',morphology=morphology,trend_c_per_s=float(slope),residual_range_c=span,raw_range_c=rawspan,
                extrema=[dict(time_s=float(t[i]),kind=k,residual_c=float(residual[i])) for i,k in extrema],cycles=cycles,
                amplitude_ratios=[b/a for a,b in zip(amplitudes,amplitudes[1:])],rate_changes_hz=np.diff(rates).tolist(),
                entry_range_c=float(np.ptp(residual[:max(2,len(y)//5)])),exit_range_c=float(np.ptp(residual[-max(2,len(y)//5):])),
                leading_partial_s=float(t[extrema[0][0]]-t[0]) if extrema else None,trailing_partial_s=float(t[-1]-t[extrema[-1][0]]) if extrema else None,
                limitations=['linear detrend is descriptive','extrema are candidates, not perceived vibrato','no naturalness label'])


def boundary_candidates(times,cents,regions,cfg=Thresholds()):
    """Adjacent sample jumps; non-singing interiors are counted and excluded."""
    t=np.asarray(times,float);y=np.asarray(cents,float)
    if len(t)!=len(y) or len(t)<2 or not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)) or np.any(np.diff(t)<=0):
        return dict(status='unknown',findings=[],excluded_non_singing=0,unknown_region=0)
    def kind(at):
        hits=[r['region_type'] for r in regions if r['start_s']<=at<r['end_s']]
        return hits[0] if len(hits)==1 else 'unknown'
    jumps=abs(np.diff(y));speeds=np.diff(y)/np.diff(t)
    indices=set(np.flatnonzero(jumps>=cfg.jump_c).tolist())
    indices.update((np.flatnonzero(abs(np.diff(speeds))>=cfg.slope_change_c_per_s)+1).tolist())
    found=[];excluded=unknown=0
    for i in sorted(indices):
        if t[i+1]-t[i]>cfg.max_gap_s:unknown+=1;continue
        a,b=kind(t[i]),kind(t[i+1])
        if a==b=='non_singing':excluded+=1;continue
        if 'unknown' in [a,b]:unknown+=1;continue
        corner=i>0 and abs(speeds[i]-speeds[i-1])>=cfg.slope_change_c_per_s
        previous=kind(t[i-1]) if corner else a
        if previous=='unknown':unknown+=1;continue
        found.append(dict(index=i,time_range=[float(t[i-1] if corner else t[i]),float(t[i+1])],code='non_singing_transition_risk' if 'non_singing' in [previous,a,b] else 'singing_boundary_risk',jump_c=float(jumps[i]),slope_change_c_per_s=float(abs(speeds[i]-speeds[i-1])) if i else None))
    return dict(status='evaluated',findings=found,excluded_non_singing=excluded,unknown_region=unknown)


def control_coupling(a,b,default_a=0.,default_b=0.,cfg=Thresholds()):
    a=np.asarray(a,float)-default_a;b=np.asarray(b,float)-default_b
    if a.ndim!=1 or b.ndim!=1 or len(a)!=len(b) or not len(a) or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        return dict(status='unknown')
    on_a=abs(a)>1e-9;on_b=abs(b)>1e-9
    correlation=float(np.corrcoef(a,b)[0,1]) if np.std(a)>1e-9 and np.std(b)>1e-9 else None
    return dict(status='evaluated',samples=len(a),both=int(sum(on_a&on_b)),a_only=int(sum(on_a&~on_b)),b_only=int(sum(~on_a&on_b)),neither=int(sum(~on_a&~on_b)),correlation=correlation,coupling_risk=correlation is not None and abs(correlation)>=cfg.coupling_abs_r,causal=False)


def polyline_complexity(xs,ys,tolerance=1.):
    """RDP count under explicit vertical interpolation error, never edits input."""
    x=np.asarray(xs,float);y=np.asarray(ys,float)
    if len(x)!=len(y) or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or (len(x)>1 and np.any(np.diff(x)<=0)):
        return dict(status='unknown',points=len(x))
    if len(x)<3:return dict(status='evaluated',points=len(x),retained=len(x),tolerance_units=tolerance)
    keep={0,len(x)-1};stack=[(0,len(x)-1)]
    while stack:
        a,b=stack.pop()
        if b<=a+1:continue
        z=y[a]+(y[b]-y[a])*(x[a+1:b]-x[a])/(x[b]-x[a]);err=abs(y[a+1:b]-z);i=a+1+int(np.argmax(err))
        if err[i-a-1]>tolerance:
            keep.add(i);stack.extend([(a,i),(i,b)])
    return dict(status='evaluated',points=len(x),retained=len(keep),tolerance_units=tolerance,interpretation='vertical-error polyline proxy, not Core reconstruction or sound quality')


VOWELS=set('a o e i u v ai ei ao ou an en ang eng ong er ir in ing ie ia iao ian iang iong ua uo uai uan uang ue un vn van ueng ve ng'.split())
EN_VOWELS=set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW AX'.split())
CONSONANTS=set('b p m f d t n l g k h j q x zh ch sh r z c s w y'.split())|set('B CH D DH F G HH JH K L M N NG P R S SH T TH V W Y Z ZH'.split())


def phone_kind(symbol):
    suffix=symbol.split('/')[-1]
    if suffix.upper() in {'AP','SP','SIL','PAU'}:return 'non_singing'
    if suffix in VOWELS or suffix.rstrip('012') in EN_VOWELS:return 'vowel'
    if suffix in CONSONANTS:return 'consonant'
    return 'unknown'


def vowel_groups(phones):
    groups=[]
    for ph in phones:
        if ph['region_type']!='vowel' or ph.get('ownership_status')!='matched':continue
        if groups and groups[-1]['symbol']==ph['symbol'] and groups[-1]['primary_index']==ph['primary_index'] and abs(groups[-1]['end_s']-ph['start_s'])<1e-6:
            groups[-1]['end_s']=ph['end_s'];groups[-1]['phone_ids'].append(ph['id'])
        else:groups.append(dict(symbol=ph['symbol'],primary_index=ph['primary_index'],start_s=ph['start_s'],end_s=ph['end_s'],phone_ids=[ph['id']],region_type='vowel'))
    return groups
