"""Evaluate an Agent's explicit functional design, without reading reference/F0 arrays.

This is a design-space helper, not a USTX/native or musical judgement engine.
See references/source-condition-to-function.md for the plan contract.
"""
import argparse
import bisect
import json
import math
from pathlib import Path


def q5(u):
    return u*u*u*(10+u*(-15+6*u))


def checked_nodes(nodes, name, positive=False):
    if len(nodes)<2 or any(len(n)!=2 or not all(math.isfinite(v) for v in n) for n in nodes):
        raise ValueError(f'{name}: finite [seconds,value] nodes required')
    if any(b[0]<=a[0] for a,b in zip(nodes,nodes[1:])):
        raise ValueError(f'{name}: time must increase')
    if positive and any(n[1]<=0 for n in nodes):
        raise ValueError(f'{name}: positive values required')


def span(nodes,t):
    return min(max(bisect.bisect_right([n[0] for n in nodes],t)-1,0),len(nodes)-2)


def smooth_value(nodes,t):
    i=span(nodes,t);a,b=nodes[i:i+2]
    u=min(1,max(0,(t-a[0])/(b[0]-a[0])))
    return a[1]+(b[1]-a[1])*q5(u)


def integrated_rate(nodes,t):
    # Exact integral of piecewise-linear Hz; no f(t)*t substitution.
    total=0.
    for a,b in zip(nodes,nodes[1:]):
        d=max(0,min(t,b[0])-a[0])
        total+=a[1]*d+(b[1]-a[1])*d*d/(2*(b[0]-a[0]))
        if t<=b[0]:
            break
    return total


def center_value(nodes,t):
    i=span(nodes,t);a,b=nodes[i:i+2]
    dt=b[0]-a[0];u=(t-a[0])/dt
    # Offset form keeps an explicitly constant center exactly constant.
    return (a[1]+(-2*u**3+3*u*u)*(b[1]-a[1])
            +(u**3-2*u*u+u)*dt*a[2]+(u**3-u*u)*dt*b[2])


def component_value(c,t):
    a,b=c['support_s']
    if t<=a or t>=b:
        return 0.
    if c['family']=='finite_return':
        peak=c['peak_s'];amp=c['peak_c']
        return amp*(q5((t-a)/(peak-a)) if t<=peak else 1-q5((t-peak)/(b-peak)))
    attack,release=c['attack_end_s'],c['release_start_s']
    env=q5((t-a)/(attack-a)) if t<attack else q5((b-t)/(b-release)) if t>release else 1.
    depth=smooth_value(c['depth_nodes'],t)
    phase=c['phase_rad']+2*math.pi*integrated_rate(c['rate_nodes'],t)
    return env*depth*math.sin(phase)


def validate(plan):
    if set(plan)!={'schema','origin','support_s','center_nodes','components','decisions','expectations'}:
        raise ValueError('unknown/missing fields; imported profiles and samples are not accepted')
    if plan['schema']!=1 or plan['origin']!='agent_designed':
        raise ValueError('an explicit Agent design is required')
    a,b=plan['support_s']
    if not all(math.isfinite(v) for v in (a,b)) or b<=a:
        raise ValueError('positive finite support required')
    nodes=plan['center_nodes']
    if any(len(n)!=3 for n in nodes):
        raise ValueError('center nodes are [seconds,absolute cents,cents/second slope]')
    checked_nodes([n[:2] for n in nodes],'center')
    if any(not math.isfinite(n[2]) for n in nodes) or nodes[0][0]!=a or nodes[-1][0]!=b:
        raise ValueError('center must cover the exact support, with finite slopes')
    allowed={'finite_return':{'id','family','support_s','peak_s','peak_c'},
             'oscillation':{'id','family','support_s','attack_end_s','release_start_s','depth_nodes','rate_nodes','phase_rad'}}
    seen=set()
    for c in plan['components']:
        if c.get('family') not in allowed or set(c)!=allowed[c['family']]:
            raise ValueError('unsupported family/fields; choose or implement the intended function')
        if c['id'] in seen:
            raise ValueError('duplicate component')
        seen.add(c['id'])
        x,y=c['support_s']
        if not all(math.isfinite(v) for v in [x,y]) or not a<=x<y<=b:
            raise ValueError('component outside current support')
        if c['family']=='finite_return':
            if not all(math.isfinite(v) for v in [c['peak_s'],c['peak_c']]) or not x<c['peak_s']<y:
                raise ValueError('finite return peak must lie inside support')
        else:
            if not x<c['attack_end_s']<=c['release_start_s']<y:
                raise ValueError('invalid independent entry/exit envelope')
            for key in ['depth_nodes','rate_nodes']:
                checked_nodes(c[key],key,positive=key=='rate_nodes')
                if c[key][0][0]!=x or c[key][-1][0]!=y:
                    raise ValueError(f'{key}: must cover exact component support')
            if any(n[1]<0 for n in c['depth_nodes']) or not math.isfinite(c['phase_rad']):
                raise ValueError('nonnegative depth and finite phase required')
    decisions=plan['decisions']
    if not decisions or decisions[0]['support_s'][0]!=a or decisions[-1]['support_s'][1]!=b:
        raise ValueError('decision stages must cover full support')
    prev=a
    for d in decisions:
        if set(d)!={'support_s','condition','choice','alternative','reason','uncertainty','component_ids'}:
            raise ValueError('incomplete condition/function decision')
        x,y=d['support_s']
        if not all(math.isfinite(v) for v in [x,y]) or x!=prev or y<=x or y>b:
            raise ValueError('decision gap/overlap/order error')
        prev=y
        if not all(isinstance(d[k],str) and d[k].strip() for k in ['condition','choice','alternative','reason','uncertainty']):
            raise ValueError('conditions, choices and counterchoices must be explicit')
        if any(i not in seen for i in d['component_ids']):
            raise ValueError('decision points to missing component')
    used={i for d in decisions for i in d['component_ids']}
    if used!=seen:
        raise ValueError('unassigned component')
    if not plan['expectations']:
        raise ValueError('local shape expectations required')
    for e in plan['expectations']:
        if set(e)!={'support_s','range_c','purpose'} or not isinstance(e['purpose'],str) or not e['purpose'].strip():
            raise ValueError('expectation fields required')
        x,y=e['support_s'];lo,hi=e['range_c']
        if not all(math.isfinite(v) for v in [x,y,lo,hi]) or not a<=x<y<=b or not 0<=lo<=hi:
            raise ValueError('invalid local expectation')


def evaluate(plan,t):
    return center_value(plan['center_nodes'],t)+sum(component_value(c,t) for c in plan['components'])


def compile_plan(plan,step_s=.001):
    validate(plan)
    if not math.isfinite(step_s) or not 0<step_s<=.01:
        raise ValueError('diagnostic sampling step must be in (0,.01] seconds')
    a,b=plan['support_s'];n=math.ceil((b-a)/step_s)
    times=[a+(b-a)*i/n for i in range(n+1)]
    # Include authored nodes and expectation ends, do not silently miss narrow supports.
    times=sorted(set(times+[n[0] for n in plan['center_nodes']]+[v for e in plan['expectations'] for v in e['support_s']]
                     +[v for c in plan['components'] for v in c['support_s']]
                     +[c['peak_s'] for c in plan['components'] if c['family']=='finite_return']))
    values=[evaluate(plan,t) for t in times]
    checks=[]
    for e in plan['expectations']:
        vals=[v for t,v in zip(times,values) if e['support_s'][0]<=t<=e['support_s'][1]]
        r=max(vals)-min(vals);lo,hi=e['range_c']
        checks.append({**e,'observed_range_c':r,'pass':lo<=r<=hi})
    return {'times_s':times,'cents':values,'local_checks':checks,'shape_checks_pass':all(c['pass'] for c in checks),
            'native_written':False,'audio_rendered':False,'musical_quality_validated':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--step-s',type=float,default=.001)
    args=ap.parse_args();result=compile_plan(json.loads(args.plan.read_text(encoding='utf-8')),args.step_s)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    if not result['shape_checks_pass']:
        raise SystemExit('designed local shape failed; result preserved')


if __name__=='__main__':
    main()
