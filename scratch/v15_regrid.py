"""让 PITD 精确落在原生帧网格上，消除 13c 的插值误差。

原生 pitch 采样：pitch_start_tick + i*pitch_interval_ticks（interval=5，即 5 tick）。
我的 PITD 是 15 tick 网格 → 插值必然有残差。
做法：直接把 PITD 写成 5 tick 网格（每个原生采样点一个值）。
"""
import sys, json, io, math
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'score'/'v14_score.ustx')   # 含连续 PITD
tm = TempoMap.from_doc(doc)

# 原生 pitch 采样间隔
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
intervals = {ph['pitch_interval_ticks'] for ph in bp['phrases']}
print('native pitch_interval_ticks:', intervals)
INT = min(intervals) if intervals else 5

# 每个 part：把 15-tick 的 PITD 重采样到 INT tick 网格
for part in doc['voice_parts']:
    pit = next((c for c in part['curves'] if c['abbr']=='pitd'), None)
    if pit is None: continue
    xs = np.array(pit['xs'], float)
    ys = np.array(pit['ys'], float)
    dur = int(part['duration'])
    new_xs = list(range(0, dur+1, INT))
    if new_xs[-1] != dur: new_xs.append(dur)
    new_ys = [int(round(float(v))) for v in np.interp(np.array(new_xs,float), xs, ys)]
    part['curves'] = [c for c in part['curves'] if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd', xs=[int(x) for x in new_xs], ys=new_ys))

OUT = NEW/'score'/'v15_score.ustx'
save_ustx(doc, OUT)
tot = sum(len(next(c for c in p['curves'] if c['abbr']=='pitd')['xs']) for p in doc['voice_parts'])
print(f'PITD now on {INT}-tick grid; total points {tot}')
print(f'wrote {OUT}')
