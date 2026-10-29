"""量化确认：我的 PITD 是否有悬崖（尖角）？

指标：相邻点变化率、二阶差分，与白烁对比。
白烁：中位逐点 |dy| = 11c，二阶差分中位 12c（平滑）。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')

def stats(path, label, tick_ms):
    d = load_ustx(path)
    d1=[]; d2=[]; jumps=[]
    for part in d['voice_parts']:
        pit = next((c for c in part.get('curves',[]) if c['abbr']=='pitd'), None)
        if not pit: continue
        xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
        # per-point change normalised to cents per 12ms
        dt=np.diff(xs)*tick_ms
        dy=np.diff(ys)
        ok=dt>0
        rate=np.abs(dy[ok])/dt[ok]*12.0   # cents per 12ms
        d1.append(rate)
        d2.append(np.abs(np.diff(ys,2)))
        jumps.append(np.abs(dy))
    d1=np.concatenate(d1); d2=np.concatenate(d2); jumps=np.concatenate(jumps)
    print(f'=== {label} ===')
    print(f'  points {len(jumps)+len(d1)*0}')
    print(f'  |dy| per step: median {np.median(jumps):.1f}c  p90 {np.percentile(jumps,90):.1f}  p99 {np.percentile(jumps,99):.1f}  max {jumps.max():.0f}')
    print(f'  2nd difference: median {np.median(d2):.1f}c  p90 {np.percentile(d2,90):.1f}  p99 {np.percentile(d2,99):.1f}')
    print(f'  rate (c/12ms): median {np.median(d1):.1f}  p90 {np.percentile(d1,90):.1f}  p99 {np.percentile(d1,99):.1f}')
    print(f'  steps >200c: {(jumps>200).sum()} ({(jumps>200).mean():.3%})   >400c: {(jumps>400).sum()}')

stats(REF, '白烁 雨爱', 1.5625)
print()
stats(NEW/'compiled'/'project.ustx', 'v11 年轮 (最终线)', 1.042)
