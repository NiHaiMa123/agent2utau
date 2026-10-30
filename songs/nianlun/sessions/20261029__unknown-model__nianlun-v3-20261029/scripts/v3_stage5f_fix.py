"""阶段5f：修正重采样 — 原生短语超出 part 设计支撑时用边界值（不外推 Hermite）。

根因：AP 呼吸音符使原生 RenderPhrase 起点早于 part 的演唱起点（18.23 vs 18.73），
      df.evaluate 在主支撑外 Hermite 外推 → 33984c 爆炸。
修正：采样时间 clamp 到 [support0, support1]；并硬校验节点在 4000-9500c。
"""
import sys, json, io, importlib.util
import numpy as np, yaml
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import sha256

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'; NAT = NEW/'native'; SCORE = NEW/'score'/'v3_score.ustx'
spec = importlib.util.spec_from_file_location('df', 'skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)

BP = json.load(io.open(NAT/'baseline_pitch_exact.json', encoding='utf-8'))
PP = json.load(io.open(D/'plan.json', encoding='utf-8'))       # 51 part plans
print(f'native phrases {len(BP["phrases"])}, part plans {len(PP["phrases"])}')

def eval_clamped(plan, t):
    a, b = plan['support_s']
    tt = min(max(float(t), a), b)
    return float(df.evaluate(plan, tt))

new, bad_range = [], []
for npi, np_ in enumerate(BP['phrases']):
    t = np.asarray(np_['times_ms'], float)/1000
    t0, t1 = float(t[0]), float(t[-1])
    mid = 0.5*(t0+t1)
    # choose the part plan containing the phrase midpoint (AP lead may start earlier)
    idx, best = None, 1e9
    for k, p in enumerate(PP['phrases']):
        a, b = p['support_s']
        if a <= mid <= b: idx = k; break
        dd = min(abs(mid-a), abs(mid-b))
        if dd < best: best, idx = dd, k
    src = PP['phrases'][idx]
    ts = np.arange(t0, t1+1e-12, 0.003)
    if len(ts) < 2: ts = np.array([t0, t1])
    else: ts[-1] = t1
    vals = np.array([eval_clamped(src, x) for x in ts])
    if vals.min() < 4000 or vals.max() > 9500:
        bad_range.append((npi, float(vals.min()), float(vals.max())))
    keep = np.unique(np.linspace(0, len(ts)-1, min(16, len(ts))).astype(int))
    nodes = []
    for i in keep:
        tt, vv = float(ts[i]), float(vals[i])
        if nodes and tt <= nodes[-1][0]: continue
        nodes.append([tt, vv, 0.0])
    if nodes[0][0] != t0: nodes.insert(0, [t0, nodes[0][1], 0.0])
    nodes[0][0] = t0
    if nodes[-1][0] < t1: nodes.append([t1, nodes[-1][1], 0.0])
    nodes[-1][0] = t1
    # strict monotone
    out = []
    for n in nodes:
        if out and n[0] <= out[-1][0] + 1e-9: continue
        out.append(n)
    if out[0][0] != t0: out.insert(0, [t0, out[0][1], 0.0])
    out[0][0] = t0
    if out[-1][0] != t1: out.append([t1, out[-1][1], 0.0])
    out[-1][0] = t1
    amp = float(vals.max()-vals.min())
    new.append(dict(schema=1, origin='agent_designed', support_s=[t0, t1],
                    center_nodes=out, components=[],
                    decisions=[dict(support_s=[t0, t1],
                        condition='native RenderPhrase on the baseline clock',
                        choice='Agent part design resampled over this native phrase',
                        alternative='assume the part window equals each native phrase window',
                        reason='AP/SP split one part into several native phrases; outside the '
                               'designed support the boundary value is held (no Hermite extrapolation)',
                        uncertainty='AP lead carriers are not singing pitch',
                        component_ids=[])],
                    expectations=[dict(support_s=[t0, t1],
                                       range_c=[0.0, round(amp+60.0, 2)],
                                       purpose='native phrase keeps the design envelope')]))
    np_['_src_part'] = idx

print(f'out-of-range phrases: {len(bad_range)}')
for b in bad_range[:8]: print('   ', b)

bad = []
for i, pl in enumerate(new):
    try:
        r = df.compile_plan(pl, 0.004)
        if not r['shape_checks_pass']:
            bad.append((i, [(c['range_c'], round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex:
        bad.append((i, str(ex)))
print(f'shape-check failures: {len(bad)}')
for b in bad[:6]: print('  ', b)

allv = np.concatenate([np.array([n[1] for n in p['center_nodes']]) for p in new])
print(f'\nnode cents: min {allv.min():.0f} max {allv.max():.0f} median {np.median(allv):.0f}')

# rebuild compile plan
doc = yaml.safe_load(SCORE.read_text(encoding='utf-8'))
pos2part = {p['position']: i for i, p in enumerate(doc['voice_parts'])}
kc = json.load(io.open(D/'compile_plan.json', encoding='utf-8'))
kc['phrases'] = [dict(part_index=pos2part[np_['part_position']], position=np_['position'], design=pl)
                 for np_, pl in zip(BP['phrases'], new)]
(D/'compile_plan.json').write_text(json.dumps(kc, ensure_ascii=False, indent=1), encoding='utf-8')
pnp = json.load(io.open(D/'plan_native.json', encoding='utf-8'))
pnp['phrases'] = new
(D/'plan_native.json').write_text(json.dumps(pnp, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\ncompile plan rebuilt: {len(kc["phrases"])} phrases, '
      f'nodes {sum(len(p["center_nodes"]) for p in new)}')
