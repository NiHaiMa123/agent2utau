"""解矛盾：为什么锚定音符后 F0 端到端更差？

检查渲染 F0 与「设计线」的一致性——如果渲染没有跟随设计，问题是引擎/工程；
如果渲染跟随了设计，问题就是设计与原唱不一致。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
def midi(h): return 69+12*np.log2(np.maximum(h,1e-6)/440)
def load(p):
    d=np.load(p); return d['times'].astype(float), d['f0_hz'].astype(float), d['voiced'].astype(bool)

pitch=json.load(io.open(NEW/'compiled'/'pitch.json',encoding='utf-8'))
dt=np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pitch['phrases']])
dc=np.concatenate([np.asarray(x['final_cents'],float) for x in pitch['phrases']])
o=np.argsort(dt); dt,dc=dt[o],dc[o]

rt,r1,rv1 = load(NEW/'render'/'f0_v3h'/'fcpe.npz')
_, r2, rv2 = load(NEW/'render'/'f3h_none.npz') if False else load(NEW/'render'/'f0_v3h'/'rmvpe.npz')
RC = np.where(rv1&rv2&(np.abs(midi(r1)-midi(r2))<0.5),(midi(r1)+midi(r2))/2,np.nan)

T=np.arange(19.0,242.5,0.01)
ri=np.clip(np.rint(T*100).astype(int),0,len(rt)-1)
r=RC[ri]; des=np.interp(T,dt,dc)/100
g=np.isfinite(r)
d=(r-des)[g]*100
print('=== 渲染 vs 设计线（引擎是否跟随） ===')
print(f'  frames {g.sum()}  med|Δ| {np.median(np.abs(d)):.2f}c  p90 {np.percentile(np.abs(d),90):.2f}c')
print(f'  >50c {(np.abs(d)>50).mean():.2%}   >100c {(np.abs(d)>100).mean():.2%}')

# source on the same grid
st,s1,sv1 = load(NEW/'inputs'/'fcpe.npz'); _,s2,sv2=load(NEW/'inputs'/'rmvpe.npz')
SC=np.where(sv1&sv2&(np.abs(midi(s1)-midi(s2))<0.5),(midi(s1)+midi(s2))/2,np.nan)
si=np.clip(np.rint(T*100).astype(int),0,len(st)-1)
s=SC[si]
gs=g&np.isfinite(s)
print(f'\n=== 设计线 vs 原唱 (n={gs.sum()}) ===')
e=(des[gs]-s[gs])*100
print(f'  med|Δ| {np.median(np.abs(e)):.1f}c  p90 {np.percentile(np.abs(e),90):.1f}c')
print(f'  >100c {(np.abs(e)>100).mean():.1%}  >200c {(np.abs(e)>200).mean():.1%}')

# Where is the error concentrated? per-phrase
print('\n=== per-phrase 设计 vs 原唱 (worst 12) ===')
rows=[]
for k,ph in enumerate(pitch['phrases']):
    t0=np.asarray(ph['times_ms'],float)[0]/1000; t1=np.asarray(ph['times_ms'],float)[-1]/1000
    m=(T>=t0)&(T<=t1)&np.isfinite(s)
    if m.sum()<20: continue
    e=(des[m]-s[m])*100
    rows.append((k, round(t0,1), round(t1,1), round(float(np.median(np.abs(e))),1),
                 round(float((np.abs(e)>100).mean()*100),1)))
for r_ in sorted(rows,key=lambda x:-x[3])[:12]:
    print(f"  ph{r_[0]:2d} {r_[1]:7.1f}-{r_[2]:7.1f}s  med|Δ| {r_[3]:6.1f}c  >100c {r_[4]:5.1f}%")
print(f'\nphrase med|Δ| distribution: median {np.median([x[3] for x in rows]):.1f}c, '
      f'p90 {np.percentile([x[3] for x in rows],90):.1f}c')
