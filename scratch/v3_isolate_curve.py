"""隔离测试：逐条曲线类型加入，找出 OpenUtau 拒绝的格式。"""
import sys, json, copy, subprocess
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
base = load_ustx(NEW/'compiled'/'project.ustx')
T = NEW/'compiled'/'_test.ustx'

def try_export(doc, tag):
    save_ustx(doc, T)
    r = run_bridge(cfg, ['export-pitch', '--project', str(T.resolve()),
                         '--out', str((NEW/'compiled'/'_tp.json').resolve())])
    ok = bool(r.get('ok'))
    print(f'  {tag:28s} -> {"OK" if ok else "FAIL: " + str(r.get("errors"))[:110]}')
    return ok

print('baseline:')
d0 = copy.deepcopy(base)
try_export(d0, 'no extra curves')

for abbr, ymin, ymax in [('dyn', -60, 20), ('voic', 96, 108), ('brec', -8, 8), ('tenc', 2, 12)]:
    d = copy.deepcopy(base)
    p = d['voice_parts'][0]
    dur = int(p['duration'])
    xs = [0, dur//4, dur//2, 3*dur//4, dur]
    ys = [ymin, (ymin+ymax)/2, ymax, (ymin+ymax)/2, ymin]
    p['curves'].append(dict(abbr=abbr, xs=xs, ys=[float(v) for v in ys]))
    print(f'adding {abbr}:')
    try_export(d, f'+ {abbr}')

# try all four together
d = copy.deepcopy(base)
p = d['voice_parts'][0]
dur = int(p['duration'])
for abbr, ymin, ymax in [('dyn',-60,20),('voic',96,108),('brec',-8,8),('tenc',2,12)]:
    xs = [0, dur//4, dur//2, 3*dur//4, dur]
    ys = [ymin,(ymin+ymax)/2,ymax,(ymin+ymax)/2,ymin]
    p['curves'].append(dict(abbr=abbr, xs=xs, ys=[float(v) for v in ys]))
print('all four:')
try_export(d, '+ all four')

# integer ys instead of float
d = copy.deepcopy(base)
p = d['voice_parts'][0]
dur = int(p['duration'])
p['curves'].append(dict(abbr='dyn', xs=[0,dur//2,dur], ys=[-60,0,-60]))
print('int values only:')
try_export(d, '+ dyn int ys')
