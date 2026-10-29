"""分析白烁 PITD 的极端值是怎么分布的：
  是「短促尖峰」还是「持续一段的大偏移」？
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')
doc = load_ustx(REF)
tm = TempoMap.from_doc(doc)

allseg=[]
for p in doc['voice_parts']:
    pit = next((c for c in p.get('curves',[]) if c['abbr']=='pitd'), None)
    if not pit: continue
    xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
    # 找 |y|>300 的连续段
    big = np.abs(ys) > 300
    i=0
    while i < len(big):
        if big[i]:
            j=i
            while j<len(big) and big[j]: j+=1
            dur_ticks = xs[j-1]-xs[i] if j-1>=i else 0
            allseg.append(dict(n=j-i, dur_ticks=dur_ticks, dur_ms=dur_ticks*1.5625,
                               peak=float(ys[i:j][np.argmax(np.abs(ys[i:j]))]),
                               mean=float(ys[i:j].mean())))
            i=j
        else: i+=1

print(f'|y|>300c 的连续段: {len(allseg)}')
if allseg:
    ns=np.array([s['n'] for s in allseg])
    dur=np.array([s['dur_ms'] for s in allseg])
    pk=np.array([s['peak'] for s in allseg])
    print(f'  段长(点数): median {np.median(ns):.0f}  p90 {np.percentile(ns,90):.0f}  max {ns.max()}')
    print(f'  段长(ms):   median {np.median(dur):.0f}  p90 {np.percentile(dur,90):.0f}  max {dur.max():.0f}')
    print(f'  峰值: median {np.median(np.abs(pk)):.0f}c  max {np.abs(pk).max():.0f}c')
    print(f'  正/负: pos {(pk>0).sum()}, neg {(pk<0).sum()}')

    print('\n最大的 15 段:')
    for s in sorted(allseg,key=lambda x:-abs(x['peak']))[:15]:
        print(f"   peak {s['peak']:+7.0f}c  n={s['n']:3d}  dur={s['dur_ms']:6.0f}ms  mean={s['mean']:+7.0f}c")

# 整体：|y| 的分位与「持续大偏移」的占比
print('\n=== 全体 PITD 值分布 ===')
allv=[]
for p in doc['voice_parts']:
    pit = next((c for c in p.get('curves',[]) if c['abbr']=='pitd'), None)
    if pit: allv.append(np.array(pit['ys'],float))
allv=np.concatenate(allv)
print(f'  n={len(allv)}')
for q in (1,5,10,25,50,75,90,95,99):
    print(f'  p{q:2d}: {np.percentile(allv,q):+8.0f}c')
print(f'  |y|>200: {(np.abs(allv)>200).mean():.1%}   >400: {(np.abs(allv)>400).mean():.1%}   >800: {(np.abs(allv)>800).mean():.1%}')
