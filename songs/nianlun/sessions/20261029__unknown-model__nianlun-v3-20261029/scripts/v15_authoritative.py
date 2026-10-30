"""权威验证：只用项目 final 工程里实际的 PITD 曲线与 baseline before_pitd 核对。

不读任何 score 副本 —— 以渲染实际使用的工程为准。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
PROJ = NEW/'compiled'/'project_final.ustx'
BASE = NEW/'compiled'/'baseline.ustx'

r1 = run_bridge(cfg,['export-pitch','--project',str(PROJ.resolve()),
                     '--out',str((NEW/'compiled'/'pitch_final.json').resolve())])
r2 = run_bridge(cfg,['export-pitch','--project',str(BASE.resolve()),
                     '--out',str((NEW/'compiled'/'pitch_baseline.json').resolve())])
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json',encoding='utf-8'))
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json',encoding='utf-8'))

doc = load_ustx(PROJ); tm = TempoMap.from_doc(doc)
# PITD 直接取自工程
cmap = {}
for cp in doc['voice_parts']:
    pit = next((c for c in cp['curves'] if c['abbr']=='pitd'), None)
    if pit: cmap[int(cp['position'])] = (np.array(pit['xs'],float), np.array(pit['ys'],float))

errmax = 0.0; errs=[]
for bph, fph in zip(bp['phrases'], pf['phrases']):
    pos = int(bph['part_position'])
    if pos not in cmap: continue
    xs, ys = cmap[pos]
    times = np.asarray(bph['times_ms'], float)
    ticks = np.array([tm.ms_to_tick(t) - pos for t in times])
    off = np.interp(ticks, xs, ys)
    exp = np.asarray(bph['before_pitd_cents'],float) + off
    act = np.asarray(fph['final_cents'],float)
    e = act - exp
    errs.append(e); errmax = max(errmax, float(np.max(np.abs(e))))

e = np.concatenate(errs)
print(f'frames {len(e)}')
print(f'  max |actual - (before_pitd + project PITD)| = {errmax:.4f} c')
print(f'  median {np.median(np.abs(e)):.4f}  p99 {np.percentile(np.abs(e),99):.4f}  p99.9 {np.percentile(np.abs(e),99.9):.4f}')
n_fail = int((np.abs(e) > 0.501).sum())
print(f'  frames exceeding 0.501c: {n_fail} ({n_fail/len(e):.6%})')
print(f'  => {"PASS" if errmax < 0.501 else "FAIL (max " + f"{errmax:.2f}c)"}')
