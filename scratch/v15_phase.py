"""最后一步：把 PITD 网格精确锚定到原生 pitch 采样相位，消除末端的 3-8c 舍入差。

原生采样：pitch_start_tick + i*interval。我之前从 tick 0 开始按 5 对齐，
相位与之不符（pitch_start_tick 未必是 5 的倍数），导致末端帧取到插值中间值。
做法：PITD 的 xs 用 pitch_start_tick + i*interval - part.position 生成。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
compiled = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(compiled)

# 每个 part 的原生采样 tick 列表（相对 part.position）
cs = {}
for p in compiled['voice_parts']:
    cs[int(p['position'])] = np.array(
        [next(c for c in p['curves'] if c['abbr']=='pitd')['xs'] for _ in [0]][0], float)
cur = {}
for p in compiled['voice_parts']:
    pit = next(c for c in p['curves'] if c['abbr']=='pitd')
    cur[int(p['position'])] = (np.array(pit['xs'],float), np.array(pit['ys'],float))

# 建立 part -> 原生采样 tick 序列
sampling = {}
for ph in bp['phrases']:
    pos = int(ph['part_position'])
    start = int(ph['pitch_start_tick']) - pos
    n = len(ph['times_ms'])
    interval = int(ph['pitch_interval_ticks'])
    ticks = start + np.arange(n)*interval
    sampling.setdefault(pos, []).append(ticks)

aligned = 0
for part in compiled['voice_parts']:
    pos = int(part['position'])
    if pos not in sampling or pos not in cur: continue
    xs, ys = cur[pos]
    allt = np.unique(np.concatenate(sampling[pos]))
    # 在差异处，用当前曲线插值得到值，但 xs 用精确采样 tick（含首尾延伸）
    new_xs = allt.astype(int).tolist()
    new_ys = [int(round(float(v))) for v in np.interp(allt.astype(float), xs, ys)]
    # 补首尾：若采样起点早于当前 xs[0] 或晚于 xs[-1]，也要覆盖
    lo_missing = []
    if new_xs[0] > int(xs[0]):
        ext = list(range(int(xs[0]), new_xs[0], 5))
        lo_missing = [(x, int(round(float(np.interp(x, xs, ys))))) for x in ext]
    new_xs = [x for x,_ in lo_missing] + new_xs
    new_ys = [y for _,y in lo_missing] + new_ys
    pit = next(c for c in part['curves'] if c['abbr']=='pitd')
    pit['xs'] = [int(x) for x in new_xs]
    pit['ys'] = new_ys
    aligned += 1

print(f'PITD aligned to native sampling phase in {aligned} parts')
steps=[]
for p in compiled['voice_parts']:
    pit=next(c for c in p['curves'] if c['abbr']=='pitd')
    if len(pit['ys'])>1: steps.append(np.abs(np.diff(np.array(pit['ys'],float))))
a=np.concatenate(steps)
print(f'  |dy| median {np.median(a):.1f} max {a.max():.0f} steps>200 {(a>200).sum()}')
tot=sum(len(next(c for c in p['curves'] if c['abbr']=='pitd')['xs']) for p in compiled['voice_parts'])
print(f'  total points {tot}')

save_ustx(compiled, NEW/'compiled'/'project_final.ustx')
print('wrote project_final.ustx')
