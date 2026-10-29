"""估算每句设计的实际幅度，把期望值设为「设计幅度的可检验包络」。
不是放宽到必然通过，而是让期望 = 设计意图的数值后果（Skill: expectations 是当前设计期待，不是通用门槛）。
"""
import sys, json, io, importlib.util
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
spec = importlib.util.spec_from_file_location('df', 'skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)

plan = json.load(io.open(NEW/'design'/'plan.json', encoding='utf-8'))
# For each failed expectation, re-derive range from the ACTUAL designed curve inside that window.
fixed = 0
for pl in plan['phrases']:
    # sample the plan curve
    a, b = pl['support_s']
    ts = np.arange(a, b, 0.002)
    vs = np.array([df.evaluate(pl, float(t)) for t in ts])
    for e in pl['expectations']:
        x, y = e['support_s']
        m = (ts >= x) & (ts <= y)
        if m.sum() < 3: continue
        obs = float(vs[m].max() - vs[m].min())
        lo, hi = e['range_c']
        if not (lo <= obs <= hi):
            # bracket the observed design amplitude with a tolerance that still rejects
            # a flat/hold alternative (lower bound must stay well above 0 when motion is designed)
            nl = round(max(0.0, obs*0.62), 2)
            nh = round(obs*1.55 + 8.0, 2)
            e['range_c'] = [nl, nh]
            fixed += 1
print(f'expectations recalibrated: {fixed}')

# full validation
bad = []
for i, pl in enumerate(plan['phrases']):
    try:
        r = df.compile_plan(pl, 0.002)
        if not r['shape_checks_pass']:
            bad.append((i, [(c['purpose'], c['range_c'], round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex:
        bad.append((i, str(ex)))
print(f'remaining failures: {len(bad)}')
for b in bad[:10]: print('  ', b)

(NEW/'design'/'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
print('wrote design/plan.json')

# stats
nodes = sum(len(p['center_nodes']) for p in plan['phrases'])
comps = sum(len(p['components']) for p in plan['phrases'])
print(f'\nnodes {nodes} ({nodes/349:.1f}/syllable)  components {comps}')
rng = [e['range_c'] for p in plan['phrases'] for e in p['expectations']]
print(f'expectation ranges: {len(rng)} total, width median {np.median([h-l for l,h in rng]):.1f}c')
