"""重建 compile plan（v3b）：原生短语映射 + 精确 support + clamp 外推。"""
import sys, json, io, importlib.util
import numpy as np, yaml
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'; NAT = NEW/'native'; SCORE = NEW/'score'/'v3_score.ustx'
spec = importlib.util.spec_from_file_location('df','skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)

BP = json.load(io.open(NAT/'baseline_pitch_exact.json', encoding='utf-8'))
PP = json.load(io.open(D/'plan.json', encoding='utf-8'))['phrases']

def ev(pl, t):
    a,b = pl['support_s']
    return float(df.evaluate(pl, min(max(float(t),a),b)))

new = []
for np_ in BP['phrases']:
    t = np.asarray(np_['times_ms'], float)/1000
    t0, t1 = float(t[0]), float(t[-1]); mid = 0.5*(t0+t1)
    idx, best = None, 1e9
    for k,p in enumerate(PP):
        a,b = p['support_s']
        if a <= mid <= b: idx = k; break
        d = min(abs(mid-a), abs(mid-b))
        if d < best: best, idx = d, k
    src = PP[idx]
    ts = np.arange(t0, t1+1e-12, 0.003)
    if len(ts) < 2: ts = np.array([t0,t1])
    else: ts[-1] = t1
    vals = np.array([ev(src, x) for x in ts])
    keep = np.unique(np.linspace(0, len(ts)-1, min(16, len(ts))).astype(int))
    nodes = []
    for i in keep:
        tt, vv = float(ts[i]), float(vals[i])
        if nodes and tt <= nodes[-1][0]: continue
        nodes.append([tt,vv,0.0])
    if nodes[0][0] != t0: nodes.insert(0,[t0,nodes[0][1],0.0])
    nodes[0][0] = t0
    if nodes[-1][0] < t1: nodes.append([t1,nodes[-1][1],0.0])
    nodes[-1][0] = t1
    out = []
    for n in nodes:
        if out and n[0] <= out[-1][0]: continue
        out.append(n)
    if out[0][0] != t0: out.insert(0,[t0,out[0][1],0.0])
    out[0][0] = t0
    if out[-1][0] != t1: out.append([t1,out[-1][1],0.0])
    out[-1][0] = t1
    amp = float(vals.max()-vals.min())
    new.append(dict(schema=1, origin='agent_designed', support_s=[t0,t1], center_nodes=out,
                    components=[],
                    decisions=[dict(support_s=[t0,t1],
                        condition='native RenderPhrase', choice='Agent part design resampled here',
                        alternative='assume part window == phrase window',
                        reason='AP/SP split a part into several native phrases; outside the designed '
                               'support the boundary value is held (no Hermite extrapolation)',
                        uncertainty='AP carriers are not singing pitch', component_ids=[])],
                    expectations=[dict(support_s=[t0,t1], range_c=[0.0, round(amp+60.0,2)],
                                       purpose='native phrase keeps the design envelope')]))

bad=[]
for i,pl in enumerate(new):
    try:
        r = df.compile_plan(pl,0.004)
        if not r['shape_checks_pass']: bad.append((i,[(c['range_c'],round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex: bad.append((i,str(ex)))
print(f'native plans {len(new)}  failures {len(bad)}')
for b in bad[:5]: print('  ',b)
allv = np.concatenate([np.array([n[1] for n in p['center_nodes']]) for p in new])
print(f'node cents: {allv.min():.0f} .. {allv.max():.0f}  median {np.median(allv):.0f}')

doc = yaml.safe_load(SCORE.read_text(encoding='utf-8'))
pos2 = {p['position']: i for i,p in enumerate(doc['voice_parts'])}
kc = json.load(io.open(D/'compile_plan.json', encoding='utf-8'))
kc['phrases'] = [dict(part_index=pos2[np_['part_position']], position=np_['position'], design=pl)
                 for np_,pl in zip(BP['phrases'], new)]
(D/'compile_plan.json').write_text(json.dumps(kc, ensure_ascii=False, indent=1), encoding='utf-8')
json.dump(dict(schema_version=2, scope='whole_song', phrases=new),
          io.open(D/'plan_native.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'compile plan rebuilt: {len(kc["phrases"])} phrases')
