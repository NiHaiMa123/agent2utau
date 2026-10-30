"""全曲扫描：找出所有「近乎垂直的大跳」（尖刺），逐单元定位。

指标：在 40ms 窗口内，音高变化 > 300c（3 个半音）即为尖刺。
与白烁同口径对比（白烁实测中位 53ms 完成 10-90%，p10 仅 9ms —— 他也有快跳，
但他的快跳不是「先反向再垂直」的尖刺形态）。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))

inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))
units = inv['units']

dt = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
dc = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
o=np.argsort(dt); dt,dc=dt[o],dc[o]

# 对每个单元：在 [t0,t1] 内检测 40ms 窗口内的最大变化
rows=[]
for u in units:
    s0,s1 = u['support_s']
    T=np.arange(s0,s1,0.005)
    if len(T)<10: continue
    C=np.interp(T,dt,dc)
    # sliding 40ms window (8 samples)
    W=8
    if len(C)<=W: continue
    diffs=np.array([C[i+W]-C[i] for i in range(len(C)-W)])
    k=int(np.argmax(np.abs(diffs)))
    spike=float(diffs[k])
    # also count reversals right before the spike
    rows.append(dict(id=u['id'], lyric=u['lyric'], t0=round(float(T[k]),3),
                     spike=round(spike,0), dur=round(s1-s0,2)))

sp=np.array([abs(r['spike']) for r in rows])
print(f'units scanned: {len(rows)}')
print(f'40ms 窗口内最大变化: median {np.median(sp):.0f}c  p90 {np.percentile(sp,90):.0f}c  max {sp.max():.0f}c')
for thr in (200,300,400,500):
    print(f'  >{thr}c: {(sp>thr).sum()} units ({(sp>thr).mean():.1%})')

print('\n最严重的 20 个（可能是尖刺）:')
for r in sorted(rows, key=lambda x:-abs(x['spike']))[:20]:
    print(f"  {r['id']:12s} {r['lyric']} @{r['t0']:.2f}s  40ms内 {r['spike']:+.0f}c  dur={r['dur']}s")

(Path(NEW/'evaluation')/'spike_scan.json').write_text(
    json.dumps(dict(schema_version=1, metric='max |pitch change| inside a 40ms window per unit',
                    units=rows), ensure_ascii=False, indent=1), encoding='utf-8')
print('\nwrote evaluation/spike_scan.json')
