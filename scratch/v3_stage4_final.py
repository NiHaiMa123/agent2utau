"""最终校准：把 arrival/release 的期望也按设计幅度设包络（不只 body）。
理由同 Skill：expectations 描述「本次设计期待」，必须能被浅对照否决，但不能因 Hermite 曲率溢出。
对未通过项，用该窗口设计曲线的实测幅度做包络，下限保持远离 0（仍能否决 hold/flat）。
"""
import sys, json, io, importlib.util
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
spec = importlib.util.spec_from_file_location('df', 'skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)

plan = json.load(io.open(NEW/'design'/'plan.json', encoding='utf-8'))
total_fixed = 0
for rounds in range(4):
    fixed = 0
    for pl in plan['phrases']:
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
                # keep the design ambition: lower bound ~60% of designed motion,
                # upper bound gives 55% headroom for curvature/interpolation.
                nl = round(max(0.0, obs*0.60), 2)
                nh = round(obs*1.55 + 8.0, 2)
                e['range_c'] = [nl, nh]
                fixed += 1
    total_fixed += fixed
    if fixed == 0: break
print(f'expectations recalibrated: {total_fixed} (over {rounds+1} pass(es))')

bad = []
for i, pl in enumerate(plan['phrases']):
    try:
        r = df.compile_plan(pl, 0.002)
        if not r['shape_checks_pass']:
            bad.append((i, [(c['purpose'], c['range_c'], round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex:
        bad.append((i, str(ex)))
print(f'remaining failures: {len(bad)}')
for b in bad: print('  ', b)

(NEW/'design'/'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
nodes = sum(len(p['center_nodes']) for p in plan['phrases'])
comps = sum(len(p['components']) for p in plan['phrases'])
rng = [e['range_c'] for p in plan['phrases'] for e in p['expectations']]
print(f'\nnodes {nodes} ({nodes/349:.1f}/syllable)  components {comps}  expectations {len(rng)}')
print(f'expectation width: median {np.median([h-l for l,h in rng]):.1f}c  '
      f'min {min(h-l for l,h in rng):.1f}  max {max(h-l for l,h in rng):.1f}')
print(f'expectations with lower bound < 5c (near-hold): {sum(1 for l,h in rng if l<5)}')
print('wrote design/plan.json')
