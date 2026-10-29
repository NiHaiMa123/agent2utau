"""最终修正：PITD 必须覆盖原生帧的全部范围（含 part 起点之前的 lead 帧，tick 为负）。

诊断：所有 >3c 的误差都在 tick < 0 的区域（原生短语的 head padding / lead 帧），
      我的 PITD 只从 tick 0 开始，导致这些帧取到的是「无曲线」的默认 0，
      而实际应该有我的值。
修正：把 PITD 的 xs 从「该 part 所有短语的最小 tick」开始，用首值平铺。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

# 1) 从 baseline 导出，找出每个 part 的原生 tick 范围
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
compiled = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(compiled)

# part_position -> [min_tick, max_tick] (relative to part)
rng = {}
for ph in bp['phrases']:
    pos = int(ph['part_position'])
    times = np.asarray(ph['times_ms'], float)
    ticks = np.array([tm.ms_to_tick(t) - pos for t in times])
    lo, hi = float(ticks.min()), float(ticks.max())
    if pos in rng:
        rng[pos][0] = min(rng[pos][0], lo); rng[pos][1] = max(rng[pos][1], hi)
    else:
        rng[pos] = [lo, hi]

print(f'parts with native range: {len(rng)}')
neg = [(p, r[0]) for p, r in rng.items() if r[0] < -1]
print(f'parts whose native range starts before tick 0: {len(neg)}  '
      f'(min {min(r[0] for r in rng.values()):.0f})')

# 2) 扩展每条 PITD 到 [min_tick, max(part.duration, max_tick)]
INT = 5
for part in compiled['voice_parts']:
    pos = int(part['position'])
    pit = next((c for c in part['curves'] if c['abbr']=='pitd'), None)
    if pit is None or pos not in rng: continue
    xs = np.array(pit['xs'], float); ys = np.array(pit['ys'], float)
    lo = int(np.floor(rng[pos][0]/INT)*INT)
    hi = int(np.ceil(max(int(part['duration']), rng[pos][1])/INT)*INT)
    new_xs = list(range(lo, hi+1, INT))
    if new_xs[-1] != hi: new_xs.append(hi)
    # 扩展区用首/末值平铺（与其相邻值一致，避免新增跳变）
    new_ys = [int(round(float(v))) for v in np.interp(np.array(new_xs,float), xs, ys)]
    pit['xs'] = [int(x) for x in new_xs]
    pit['ys'] = new_ys

print(f'PITD extended to native range (step {INT} ticks)')
steps=[]
for p in compiled['voice_parts']:
    pit=next((c for c in p['curves'] if c['abbr']=='pitd'),None)
    if pit and len(pit['ys'])>1: steps.append(np.abs(np.diff(np.array(pit['ys'],float))))
a=np.concatenate(steps)
print(f'  |dy| median {np.median(a):.1f} max {a.max():.0f} steps>200 {(a>200).sum()}')
tot=sum(len(next(c for c in p['curves'] if c['abbr']=='pitd')['xs']) for p in compiled['voice_parts'])
print(f'  total points {tot}')

OUT = NEW/'compiled'/'project_final.ustx'
save_ustx(compiled, OUT)
print(f'wrote {OUT}')
