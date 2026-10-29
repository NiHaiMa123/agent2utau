"""检查是否整句系统性音高偏移（移调/调性问题）。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
def midi(h): return 69+12*np.log2(np.maximum(h,1e-6)/440)
def load(p):
    d=np.load(p); return d['times'].astype(float), d['f0_hz'].astype(float), d['voiced'].astype(bool)

pitch=json.load(io.open(NEW/'compiled'/'pitch.json',encoding='utf-8'))
st,s1,sv1=load(NEW/'inputs'/'fcpe.npz'); _,s2,sv2=load(NEW/'inputs'/'rmvpe.npz')
SC=np.where(sv1&sv2&(np.abs(midi(s1)-midi(s2))<0.5),(midi(s1)+midi(s2))/2*100,np.nan)

print('per-phrase SIGNED median offset (design - source):')
signed=[]
for k,ph in enumerate(pitch['phrases']):
    t=np.asarray(ph['times_ms'],float)/1000
    c=np.asarray(ph['final_cents'],float)
    m=(st>=t[0])&(st<=t[-1])&np.isfinite(SC)
    if m.sum()<20: continue
    s=SC[m]; d=np.interp(st[m],t,c)
    off=float(np.median(d-s))
    signed.append((k, round(t[0],1), off))
    if k<14 or abs(off)>80:
        print(f'  ph{k:2d} @{t[0]:7.1f}s  signed offset {off:+8.1f}c')

so=np.array([x[2] for x in signed])
print(f'\nsigned offsets: median {np.median(so):+.1f}c  mean {so.mean():+.1f}c  std {so.std():.1f}c')
print(f'  |offset|>50c: {(np.abs(so)>50).sum()}/{len(so)}')
print(f'  all same sign? pos {(so>0).sum()}, neg {(so<0).sum()}')

# is our melody consistently sharp or flat relative to source?
print(f'\n=> if predominantly one sign, it is a systematic transposition/octave issue')
print(f'   median offset {np.median(so):+.1f}c = {np.median(so)/100:+.2f} semitones')
