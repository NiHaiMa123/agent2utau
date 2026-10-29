"""诊断 PITD 偏移分布：哪些片段超出 ±1200c，为什么。"""
import sys, json, io
import numpy as np, yaml
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'; NAT = NEW/'native'
BP = json.load(io.open(NAT/'baseline_pitch_exact.json', encoding='utf-8'))
plan = json.load(io.open(D/'compile_plan.json', encoding='utf-8'))

import importlib.util
spec = importlib.util.spec_from_file_location('df','skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)

doc = yaml.safe_load((NEW/'score'/'v3_score.ustx').read_text(encoding='utf-8'))
pitd_desc = doc.get('expressions',{}).get('pitd',{})
print('pitd descriptor:', {k: pitd_desc.get(k) for k in ('name','min','max','default_value')})

allofs = []
worst = []
for np_, ph in zip(BP['phrases'], plan['phrases']):
    times = np.asarray(np_['times_ms'], float)/1000
    des = ph['design']
    target = np.array([df.evaluate(des, float(t)) for t in times])
    before = np.asarray(np_['before_pitd_cents'], float)
    ofs = target - before
    allofs.append(ofs)
    if ofs.max() > 1200 or ofs.min() < -1200:
        k = int(np.argmax(np.abs(ofs)))
        worst.append((np_['position'], float(times[k]), float(des['support_s'][0]), float(des['support_s'][1]),
                      float(ofs[k]), float(target[k]), float(before[k])))
allofs = np.concatenate(allofs)
print(f'\nPITD offsets: min {allofs.min():.0f} max {allofs.max():.0f}')
print(f'  |ofs|>1200: {(np.abs(allofs)>1200).mean():.4%}  count {(np.abs(allofs)>1200).sum()}')
for thr in (600, 900, 1200, 1500, 2400):
    print(f'  |ofs|>{thr}: {(np.abs(allofs)>thr).sum()}')
print(f'\nphrases exceeding range: {len(worst)}')
for w in worst[:15]:
    print(f'  pos={w[0]} @{w[1]:.2f}s support={w[2]:.2f}-{w[3]:.2f} ofs={w[4]:+.0f}c target={w[5]:.0f} before={w[6]:.0f}')
