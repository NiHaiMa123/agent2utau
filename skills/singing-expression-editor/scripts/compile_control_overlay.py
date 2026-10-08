"""Compile explicit, anchored local control deltas; no artistic action selection.

Pure stdlib. Times use milliseconds, curve x uses part-relative ticks. Values
are native stored units. Caller supplies current expression limits/defaults.
Only tenc/brec/voic/dyn are supported; speaker and conditioning pitch need
their own complete dependency handling. Never silently clips or overwrites.
"""
import bisect
import copy
import math

SUPPORTED = {'tenc', 'brec', 'voic', 'dyn'}

def linear(xs, ys, x, default):
    if not xs or x < xs[0] or x > xs[-1]:
        return default
    i = bisect.bisect_right(xs, x) - 1
    if i == len(xs)-1:
        return ys[i]
    return ys[i] + (ys[i+1]-ys[i]) * (x-xs[i]) / (xs[i+1]-xs[i])

def compile_overlay(curves, events, anchors_ms, ms_to_part_tick, descriptors):
    """Return copied curves and a trace. Each event has channel, purpose, nodes.

    nodes: [{anchor: <caller key>, offset_ms: number, delta: number}, ...].
    First/last delta must be zero: the existing baseline is restored, not a
    hardcoded zero. Event support must be inside an explicitly allowed_ms pair.
    Same-channel overlaps and tick collisions fail. Other curves remain exact.
    """
    result = copy.deepcopy(curves)
    by_channel = {}
    for c in result:
        if c['abbr'] in by_channel:
            raise ValueError('Duplicate baseline channel')
        by_channel[c['abbr']] = c
    groups = {}; trace = []
    for e in events:
        channel = e['channel']
        if channel not in SUPPORTED or channel not in descriptors:
            raise ValueError('Unsupported channel or missing native descriptor')
        if not e.get('purpose'):
            raise ValueError('Explicit purpose required')
        nodes = e['nodes']; times = [anchors_ms[n['anchor']] + n.get('offset_ms', 0) for n in nodes]
        values = [n['delta'] for n in nodes]
        if len(nodes)<3 or not all(math.isfinite(x) for x in times+values):
            raise ValueError('Need finite start/interior/return nodes')
        if any(a>=b for a,b in zip(times,times[1:])) or values[0]!=0 or values[-1]!=0:
            raise ValueError('Strict node order and baseline return required')
        allowed=e['allowed_ms']
        if not (allowed[0]<=times[0]<times[-1]<=allowed[1]):
            raise ValueError('Control leaves explicitly allowed phone support')
        ticks=[round(ms_to_part_tick(t)) for t in times]
        if any(a>=b for a,b in zip(ticks,ticks[1:])):
            raise ValueError('Nodes collide after tick quantization')
        groups.setdefault(channel,[]).append((ticks,values,e))
        trace.append(dict(channel=channel,purpose=e['purpose'],resolved_ms=times,ticks=ticks,deltas=values,allowed_ms=allowed))
    for channel, entries in groups.items():
        entries.sort(key=lambda e:e[0][0])
        if any(a[0][-1]>b[0][0] for a,b in zip(entries,entries[1:])):
            raise ValueError('Same-channel overlap requires an explicit joint plan')
        desc=descriptors[channel]; default=desc['default_value'];low=desc['min'];high=desc['max']
        baseline=by_channel.get(channel,dict(abbr=channel,xs=[],ys=[]))
        bx,by=baseline['xs'],baseline['ys']
        if len(bx)!=len(by) or any(a>=b for a,b in zip(bx,bx[1:])):
            raise ValueError('Invalid baseline knots')
        if bx and ((entries[0][0][0]-1<bx[0] and by[0]!=default) or
                   (entries[-1][0][-1]+1>bx[-1] and by[-1]!=default)):
            raise ValueError('Nondefault baseline edge needs explicit boundary resolution')
        # Additional guards preserve absent-curve defaults outside each support.
        xs=sorted(set(bx+[x for ticks,_,_ in entries for x in ticks]+[x for ticks,_,_ in entries for x in [ticks[0]-1,ticks[-1]+1]]))
        ys=[]
        for x in xs:
            v=linear(bx,by,x,default)
            for ticks,vals,_ in entries:
                if ticks[0]<=x<=ticks[-1]:v+=linear(ticks,vals,x,0)
            if not math.isfinite(v) or v<low or v>high:
                raise ValueError('Control exceeds native range; redesign, do not clip')
            ys.append(round(v))
        compiled=dict(abbr=channel,xs=xs,ys=ys)
        if channel in by_channel:
            result[result.index(by_channel[channel])]=compiled
        else:result.append(compiled)
    return result, trace
