"""Execute supplied sparse musical landmarks bound to native phone/note clocks.

No reference curves, lyric branches, gesture selection, fitting or random pitch
are present here. Intent and all shape/clock parameters belong to the plan.
"""
import numpy as np
from .curve_components import compose_curve,LocalGesture,VibratoSegment
from .enveloped_landmarks import enveloped_landmarks


def resolve(anchor, notes, plan, times):
    kind=anchor['kind'];index=anchor.get('index');offset=float(anchor.get('offset_s',0.))
    if kind=='phrase_start':value=float(times[0])
    elif kind=='phrase_end':value=float(times[-1])
    elif kind in ('note_start','note_end'):
        byid={n['note_index']:n for n in notes}
        if index not in byid:raise ValueError('Unknown note anchor')
        value=byid[index]['start_ms' if kind=='note_start' else 'end_ms']/1000
    elif kind in ('phone_start','phone_end'):
        byid={p['phone_index']:p for p in plan['phone_geometry']}
        if index not in byid:raise ValueError('Unknown phone anchor')
        value=byid[index]['start_ms' if kind=='phone_start' else 'end_ms']/1000
    else:raise ValueError('Unsupported clock anchor')
    return value+offset


def context_target(notes,plan,times):
    t=np.asarray(times,float)
    if t.ndim!=1 or not np.isfinite(t).all() or np.any(np.diff(t)<=0):raise ValueError('Invalid sample clock')
    if [q['note_index'] for q in plan['note_targets']]!=[n['note_index'] for n in notes]:raise ValueError('Incomplete note ownership')
    if {n['primary_index'] for n in notes}!={g['primary_index'] for g in plan['groups']}:raise ValueError('Incomplete syllable ownership')
    if len(plan['groups'])!=len({g['primary_index'] for g in plan['groups']}):raise ValueError('Duplicate syllable actions')
    if any(a['execution_state']=='unsupported' for a in plan['events']):raise ValueError('Unsupported action must not be substituted')
    nodes=plan['melody_nodes'];clock=np.array([resolve(q['anchor'],notes,plan,t) for q in nodes]);cents=np.array([q['cents'] for q in nodes]);slopes=np.array([q.get('slope_c_per_s',0.) for q in nodes])
    melody=compose_curve(t,clock,cents,slopes)
    parts={k:np.zeros(t.shape) for k in ['body','articulation','release','periodic']}
    budgets=plan['budgets'];ids=set()
    for event in plan['events']:
        if event['id'] in ids:raise ValueError('Duplicate event identity')
        ids.add(event['id']);kind=event['kind'];a=resolve(event['start'],notes,plan,t);b=resolve(event['end'],notes,plan,t)
        if a<t[0]-1e-9 or b>t[-1]+1e-9 or a>=b:raise ValueError('Action outside owned phrase support')
        if kind=='local_gesture':
            peak=resolve(event['peak'],notes,plan,t);amp=float(event['amplitude_c']);channel=event['channel']
            if channel not in ['body','articulation','release']:raise ValueError('Unknown local channel')
            if abs(amp)>budgets[channel]:raise ValueError('Declared local budget exceeded')
            parts[channel]+=LocalGesture(a,peak,b,amp,event['label']).evaluate(t)
        elif kind in ('body_landmarks','periodic_landmarks'):
            channel='body' if kind=='body_landmarks' else 'periodic'
            qs=event['nodes'];tt=[resolve(q['anchor'],notes,plan,t) for q in qs];yy=[q['cents'] for q in qs]
            if tt[0]!=a or tt[-1]!=b or yy[0]!=0 or yy[-1]!=0:raise ValueError('Landmark action needs zero-valued support endpoints')
            if max(abs(v) for v in yy)>budgets[channel]:raise ValueError('Declared landmark budget exceeded')
            mask=(t>=a)&(t<=b);parts[channel][mask]+=compose_curve(t[mask],tt,yy,[q.get('slope_c_per_s',0.) for q in qs])
        elif kind in ('enveloped_periodic_landmarks','sparse_enveloped_route'):
            qs=event['nodes'];tt=[resolve(q['anchor'],notes,plan,t) for q in qs];yy=[q['cents'] for q in qs]
            if max(abs(v) for v in yy)>budgets['periodic']:raise ValueError('Declared landmark budget exceeded')
            attack=resolve(event['attack_end'],notes,plan,t);release=resolve(event['release_start'],notes,plan,t)
            slopes=[float(n.get('slope_c_per_s',0)) for n in event['nodes']] if kind=='sparse_enveloped_route' else None
            parts['periodic']+=enveloped_landmarks(t,tt,yy,a,attack,release,b,slopes=slopes)
        elif kind=='dynamic_periodic':
            attack=resolve(event['attack_end'],notes,plan,t);release=resolve(event['release_start'],notes,plan,t)
            ds,de=event['depth_start_c'],event['depth_end_c'];fs,fe=event['rate_start_hz'],event['rate_end_hz']
            if max(ds,de)>budgets['periodic']:raise ValueError('Declared periodic budget exceeded')
            if not 0<min(fs,fe)<=max(fs,fe)<=9:raise ValueError('Invalid periodic rate')
            parts['periodic']+=VibratoSegment(a,attack,release,b,ds,de,fs,fe,event['phase_rad']).evaluate(t)
        else:raise ValueError('Unsupported action kind')
    for channel in parts:
        if np.max(abs(parts[channel]),initial=0)>budgets[channel]+1e-7:raise ValueError('Stacked channel exceeds declared budget')
    target=melody+sum(parts.values())
    if not np.isfinite(target).all():raise ValueError('Missing pitch target')
    return dict(target=target,melody=melody,**parts)
