"""学习白烁画法的结构特征（只读归纳，不复制数值）。

已观测特征：
  - PITD 每 15.6ms 一点（密集逐点）
  - 62-68% 的点在 ±50c 内
  - 音符内 PITD 范围中位 256c（远超我之前设计的 ±60c 上限）
  - first/last 常有大偏移 → 字头滑入、字尾滑出是主要动作
  - 满量程 -1200..1200 会用到（2% 的点）

本脚本量化「相对音符中心的偏移随字内位置的分布」，用于指导我自己的画法。
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

# 收集所有音符的「字内归一化位置 -> PITD 值」
prof = []   # list of (u, y)
bysyl = []
for p in doc['voice_parts']:
    pitd = next((c for c in p.get('curves',[]) if c['abbr']=='pitd'), None)
    if not pitd: continue
    xs=np.array(pitd['xs'],float); ys=np.array(pitd['ys'],float)
    for n in p['notes']:
        na = p['position']+n['position']; nb = na+n['duration']
        m=(xs>=na)&(xs<=nb)
        if m.sum()<6: continue
        u=(xs[m]-na)/max(nb-na,1)
        v=ys[m]
        for a,b in zip(u,v): prof.append((a,b))
        bysyl.append(dict(u=u, y=v, dur=n['duration'], lyric=n['lyric']))

prof=np.array(prof)
print(f'样本点 {len(prof)}, 音符 {len(bysyl)}')

# 按字内位置分箱
bins=np.linspace(0,1,11)
print('\n=== 字内归一化位置的 PITD 中位数 / 分位 ===')
print('  u-bin     n      p10    p25    p50    p75    p90')
for i in range(len(bins)-1):
    m=(prof[:,0]>=bins[i])&(prof[:,0]<bins[i+1])
    if m.sum()<20: continue
    v=prof[m,1]
    print(f'  {bins[i]:.1f}-{bins[i+1]:.1f} {m.sum():6d}  {np.percentile(v,10):6.0f} {np.percentile(v,25):6.0f} '
          f'{np.percentile(v,50):6.0f} {np.percentile(v,75):6.0f} {np.percentile(v,90):6.0f}')

# 字头的「滑入」特征：u<0.2 的均值
head = prof[prof[:,0]<0.20,1]
mid  = prof[(prof[:,0]>=0.35)&(prof[:,0]<0.65),1]
tail = prof[prof[:,0]>=0.80,1]
print(f'\n=== 三段对比 ===')
print(f'  字头 u<0.20:  mean {head.mean():+7.1f}c  std {head.std():5.1f}  |y|>100 占比 {(np.abs(head)>100).mean():.1%}')
print(f'  字腹 0.35-0.65: mean {mid.mean():+7.1f}c  std {mid.std():5.1f}  |y|>100 占比 {(np.abs(mid)>100).mean():.2%}')
print(f'  字尾 u>0.80:  mean {tail.mean():+7.1f}c  std {tail.std():5.1f}  |y|>100 占比 {(np.abs(tail)>100).mean():.1%}')

# 长音符 vs 短音符的字腹行为
print(f'\n=== 长/短音符的字腹（0.35-0.65）运动 ===')
for lo,hi,lab in [(0,240,'short<=240t'),(240,480,'mid 240-480t'),(480,10000,'long>480t')]:
    sub=[s for s in bysyl if lo<=s['dur']<hi]
    if not sub: continue
    stds=[]
    for s in sub:
        m=(s['u']>=0.35)&(s['u']<=0.65)
        if m.sum()>=4: stds.append(float(np.std(s['y'][m])))
    if stds:
        print(f'  {lab:16s} n={len(stds):4d}  字腹 std: median {np.median(stds):5.1f}c  p90 {np.percentile(stds,90):6.1f}c')

# PITD 的平滑性：二阶差分
print(f'\n=== 光滑性（同音符内相邻点二阶差分） ===')
d2s=[]
for s in bysyl:
    if len(s['y'])>=5:
        d2=np.diff(s['y'],2)
        d2s.append(np.median(np.abs(d2)))
d2s=np.array(d2s)
print(f'  |二阶差分| median: {np.median(d2s):.1f}c   p90 {np.percentile(d2s,90):.1f}c')
print(f'  => 小值表示曲线平滑，不是噪声')
