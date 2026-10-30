"""验证：音符边界附近的误差，是否因为原唱本身在那里滑动（换音过渡）？

如果原唱在边界 ±100ms 内的 F0 跨度很大，那么任何「分明的音符」都会与之偏离。
这不是我的错误，而是「翻唱的离散音符」与「原唱连续滑动」的本质差异。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
def midi(h): return 69+12*np.log2(np.maximum(h,1e-6)/440)
def load(p):
    d=np.load(p); return d['times'].astype(float), d['f0_hz'].astype(float), d['voiced'].astype(bool)
st,s1,sv1=load(NEW/'inputs'/'fcpe.npz'); _,s2,sv2=load(NEW/'inputs'/'rmvpe.npz')
SC=np.where(sv1&sv2&(np.abs(midi(s1)-midi(s2))<0.5),(midi(s1)+midi(s2))/2*100,np.nan)

doc=load_ustx(NEW/'compiled'/'project.ustx'); tm=TempoMap.from_doc(doc)
notes=[]
for part in doc['voice_parts']:
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        notes.append((a,b,n['tone'],n['lyric']))
notes.sort()

print('=== 原唱在每个音符「中部」的实测音高 vs 该音符整数音高 ===')
middev=[]
spanmid=[]
for a,b,tone,lyr in notes:
    d=b-a
    if d<0.12: continue
    m=(st>=a+0.3*d)&(st<b-0.3*d)&np.isfinite(SC)
    if m.sum()<3: continue
    mid=float(np.median(SC[m]))
    middev.append(mid-tone*100)
    spanmid.append(float(np.percentile(SC[m],95)-np.percentile(SC[m],5)))
middev=np.array(middev); spanmid=np.array(spanmid)
print(f'  n={len(middev)}')
print(f'  source-mid vs note-tone: median {np.median(middev):+7.1f}c  med|Δ| {np.median(np.abs(middev)):6.1f}c  p90 {np.percentile(np.abs(middev),90):6.1f}c')
print(f'    |Δ|>50c: {(np.abs(middev)>50).mean():.1%}   >100c: {(np.abs(middev)>100).mean():.1%}')
print(f'  source intra-note span (mid): median {np.median(spanmid):.0f}c  p90 {np.percentile(spanmid,90):.0f}c')

print('\n=== 原唱在音符「边界」附近的滑动量 ===')
bspan=[]
for a,b,tone,lyr in notes:
    for edge in (a,b):
        m=(st>=edge-0.06)&(st<edge+0.06)&np.isfinite(SC)
        if m.sum()>=6:
            bspan.append(float(np.percentile(SC[m],95)-np.percentile(SC[m],5)))
bspan=np.array(bspan)
print(f'  n={len(bspan)}  ±60ms 内源F0跨度: median {np.median(bspan):.0f}c  p90 {np.percentile(bspan,90):.0f}c')
print(f'  => 若这里跨度很大，说明原唱在换音处连续滑动，与离散音符天然不同')

# 结论性对照：如果用「源中部实测值」当音高（不取整到半音），误差会是多少？
print(f'\n=== 假设改用「源中部实测中值」做音符音高（不量化到整数半音） ===')
print(f'  则 body 误差中位会降到约 {np.median(np.abs(middev)):.0f}c（当前 25.7c）')
print(f'  但音符 tone 必须是整数（USTX 限制），余量只能靠 PITD —— 当前 PITD 已承载这部分')

# 检查我们的 PITD 是否真的补上了这个余量
pitch=json.load(io.open(NEW/'compiled'/'pitch.json',encoding='utf-8'))
dt=np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pitch['phrases']])
dc=np.concatenate([np.asarray(x['final_cents'],float) for x in pitch['phrases']])
o=np.argsort(dt); dt,dc=dt[o],dc[o]
res=[]
for a,b,tone,lyr in notes:
    d=b-a
    if d<0.12: continue
    m=(st>=a+0.3*d)&(st<b-0.3*d)&np.isfinite(SC)
    if m.sum()<3: continue
    src_mid=float(np.median(SC[m]))
    ours=float(np.median(np.interp(st[m],dt,dc)))
    res.append(ours-src_mid)
res=np.array(res)
print(f'\n  我们的最终线在音符中部的误差: median {np.median(res):+.1f}c  med|Δ| {np.median(np.abs(res)):.1f}c')
print(f'  （如果 PITD 正确补偿，这里应接近 0）')
