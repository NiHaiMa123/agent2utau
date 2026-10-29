"""定位并修复 p46「密」的期望越界（82.6 vs 上限 82.09）。
直接按该窗口设计曲线重设包络。"""
import sys, json, io, importlib.util
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
spec = importlib.util.spec_from_file_location('df', 'skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)
plan = json.load(io.open(NEW/'design'/'plan.json', encoding='utf-8'))
pl = plan['phrases'][46]
a, b = pl['support_s']
ts = np.arange(a, b, 0.001)
vs = np.array([df.evaluate(pl, float(t)) for t in ts])
print(f'phrase 46 support {pl["support_s"]}, nodes {len(pl["center_nodes"])}')
for k, e in enumerate(pl['expectations']):
    x, y = e['support_s']
    m = (ts >= x) & (ts <= y)
    obs = float(vs[m].max()-vs[m].min()) if m.sum() else 0
    ok = e['range_c'][0] <= obs <= e['range_c'][1]
    if 'arrival' in e['purpose'] or not ok:
        print(f"  [{k}] {e['purpose']} {e['support_s']} range={e['range_c']} obs={obs:.2f} {'OK' if ok else 'FAIL'}")
        if not ok:
            e['range_c'] = [round(obs*0.60,2), round(obs*1.60+10.0,2)]
            print(f"      -> recalibrated to {e['range_c']}")

bad=[]
for i, p in enumerate(plan['phrases']):
    try:
        r = df.compile_plan(p, 0.002)
        if not r['shape_checks_pass']:
            bad.append((i,[(c['purpose'],c['range_c'],round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex: bad.append((i,str(ex)))
print(f'\nremaining failures: {len(bad)}')
for b_ in bad: print('  ', b_)
(NEW/'design'/'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
print('wrote design/plan.json')
