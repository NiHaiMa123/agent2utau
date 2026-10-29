"""v18 最终化：连续 PITD 写回 + 扩展到原生 tick 全域 + 相位对齐 + 验证。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()

compiled = load_ustx(NEW/'compiled'/'project_v18.ustx')
mine = load_ustx(NEW/'score'/'v18_score.ustx')

# 1) 用我的连续 PITD 覆盖
mymap = {}
for mp in mine['voice_parts']:
    pit = next((c for c in mp['curves'] if c['abbr']=='pitd'), None)
    if pit: mymap[int(mp['position'])] = (list(pit['xs']), list(pit['ys']))
n=0
for cp in compiled['voice_parts']:
    key = int(cp['position'])
    if key not in mymap: continue
    xs, ys = mymap[key]
    cp['curves'] = [c for c in cp['curves'] if c['abbr']!='pitd']
    cp['curves'].append(dict(abbr='pitd', xs=xs, ys=ys))
    n += 1
print(f'PITD replaced in {n} parts')

# 2) 扩展到原生 tick 全域（含负 tick lead 帧）
out_p = NEW/'compiled'/'pitch_baseline.json'
r = run_bridge(cfg, ['export-pitch','--project',str((NEW/'compiled'/'baseline.ustx').resolve()),
                     '--out',str(out_p.resolve())])
bp = json.load(io.open(out_p, encoding='utf-8'))
tm = TempoMap.from_doc(compiled)

sampling = {}
for ph in bp['phrases']:
    pos = int(ph['part_position'])
    start = int(ph['pitch_start_tick']) - pos
    interval = int(ph['pitch_interval_ticks'])
    ticks = start + np.arange(len(ph['times_ms']))*interval
    sampling.setdefault(pos, []).append(ticks)

ext=0
for part in compiled['voice_parts']:
    pos = int(part['position'])
    if pos not in sampling: continue
    pit = next((c for c in part['curves'] if c['abbr']=='pitd'), None)
    if pit is None: continue
    xs = np.array(pit['xs'], float); ys = np.array(pit['ys'], float)
    allt = np.unique(np.concatenate(sampling[pos]))
    lo = int(min(allt.min(), xs[0])); hi = int(max(allt.max(), xs[-1]))
    # 5-tick 均匀网格覆盖 [lo,hi]，并在原生采样 tick 处也放点
    grid = set(range(lo - lo%5, hi+1, 5))
    grid.update(int(t) for t in allt)
    gx = sorted(grid)
    gy = [int(round(float(v))) for v in np.interp(np.array(gx,float), xs, ys)]
    pit['xs'] = gx; pit['ys'] = gy
    ext += 1
print(f'extended to native range in {ext} parts')

save_ustx(compiled, NEW/'compiled'/'project_final.ustx')
steps=[]
for p in compiled['voice_parts']:
    pit=next(c for c in p['curves'] if c['abbr']=='pitd')
    if len(pit['ys'])>1: steps.append(np.abs(np.diff(np.array(pit['ys'],float))))
a=np.concatenate(steps)
print(f'  |dy| median {np.median(a):.1f} max {a.max():.0f}  >45: {(a>45).sum()}')
print('wrote project_final.ustx')
