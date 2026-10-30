"""定位 p90=281c 的来源：是音符边界瞬变，还是音符内部？

把每帧误差按「距最近音符边界的距离」分组统计。
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

doc=load_ustx(NEW/'compiled'/'project.ustx'); tm=TempoMap.from_doc(doc)
st,s1,sv1=load(NEW/'inputs'/'fcpe.npz'); _,s2,sv2=load(NEW/'inputs'/'rmvpe.npz')
SC=np.where(sv1&sv2&(np.abs(midi(s1)-midi(s2))<0.5),(midi(s1)+midi(s2))/2*100,np.nan)

# note boundaries
bounds=[]
for part in doc['voice_parts']:
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        bounds += [a,b]
bounds=np.array(sorted(bounds))

pitch=json.load(io.open(NEW/'compiled'/'pitch.json',encoding='utf-8'))
dt=np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pitch['phrases']])
dc=np.concatenate([np.asarray(x['final_cents'],float) for x in pitch['phrases']])
o=np.argsort(dt); dt,dc=dt[o],dc[o]

T=np.arange(19.0,242.5,0.01)
si=np.clip(np.rint(T*100).astype(int),0,len(st)-1)
s=SC[si]; des=np.interp(T,dt,dc)
g=np.isfinite(s)
err=np.abs(des-s)
# distance to nearest boundary
idx=np.searchsorted(bounds,T)
dists=np.minimum(np.abs(T-bounds[np.clip(idx,0,len(bounds)-1)]),
                 np.abs(T-bounds[np.clip(idx-1,0,len(bounds)-1)]))

print('误差按「距最近音符边界」分组：')
for lo,hi in [(0,0.02),(0.02,0.05),(0.05,0.10),(0.10,0.20),(0.20,1e9)]:
    m=g&(dists>=lo)&(dists<hi)
    if m.sum()<50: continue
    e=err[m]
    print(f'  {lo*1000:5.0f}-{hi*1000 if hi<1e8 else 99999:5.0f}ms: n={m.sum():5d}  '
          f'med|Δ| {np.median(e):6.1f}c  p90 {np.percentile(e,90):7.1f}c  >100c {(e>100).mean():5.1%}')
