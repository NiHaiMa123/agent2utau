"""对比 v2 / v3c / v3d 渲染 vs 原唱（同一口径）。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.analysis.f0 import extract_f0
from agent2utau.analysis.rmvpe import infer_rmvpe
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
def midi(hz): return 69+12*np.log2(np.maximum(hz,1e-6)/440)

def ensure_f0(wav, tag):
    d = NEW/'render'/f'f0_{tag}'
    d.mkdir(parents=True, exist_ok=True)
    if not (d/'fcpe.npz').exists():
        r = extract_f0(wav)
        np.savez_compressed(d/'fcpe.npz', **{k:v for k,v in r.items() if isinstance(v,np.ndarray)})
        r2 = infer_rmvpe(wav, Path(cfg['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx')
        np.savez_compressed(d/'rmvpe.npz', **{k:v for k,v in r2.items() if isinstance(v,np.ndarray)})
    return d

def load(p):
    d = np.load(p); return d['times'].astype(float), d['f0_hz'].astype(float), d['voiced'].astype(bool)

# source
st, s1, sv1 = load(NEW/'inputs/fcpe.npz')
_,  s2, sv2 = load(NEW/'inputs/rmvpe.npz')
SC = np.where(sv1 & sv2 & (np.abs(midi(s1)-midi(s2))<0.5), (midi(s1)+midi(s2))/2, np.nan)

def evaluate(f0dir, label, alias=None):
    if alias:
        rt, r1, rv1 = load(Path(alias[0]))
        _,  r2, rv2 = load(Path(alias[1]))
    else:
        rt, r1, rv1 = load(f0dir/'fcpe.npz')
        _,  r2, rv2 = load(f0dir/'rmvpe.npz')
    RC = np.where(rv1 & rv2 & (np.abs(midi(r1)-midi(r2))<0.5), (midi(r1)+midi(r2))/2, np.nan)
    T = np.arange(19.0, 242.5, 0.01)
    si = np.clip(np.rint(T*100).astype(int), 0, len(st)-1)
    ri = np.clip(np.rint(T*100).astype(int), 0, len(rt)-1)
    s = SC[si]; r = RC[ri]
    g = np.isfinite(s) & np.isfinite(r)
    d = (r-s)[g]*100
    print(f'\n=== {label} ===')
    print(f'  frames {g.sum()}   median {np.median(d):+7.1f}c   med|Δ| {np.median(np.abs(d)):6.1f}c   '
          f'p90|Δ| {np.percentile(np.abs(d),90):6.1f}c')
    for thr in (50,100,200):
        print(f'    |Δ|>{thr:4d}c: {(np.abs(d)>thr).mean():6.1%}')
    return np.median(np.abs(d)), (np.abs(d)>100).mean()

res = {}
res['v2'] = evaluate(None, 'v2 render vs source (逐帧抄写源F0)',
                     alias=('scratch/render_fcpe.npz', 'scratch/render_rmvpe.npz'))
if (NEW/'render'/'f0'/'fcpe.npz').exists():
    res['v3c'] = evaluate(NEW/'render'/'f0', 'v3c render vs source (3.3 节点/字)')
res['v3d'] = evaluate(ensure_f0(NEW/'render'/'vocal_v3d_vocal.wav', 'v3d'),
                      'v3d render vs source (自适应密度 15.5 节点/字)')
print('\n--- summary (med|Δ|, frac>100c) ---')
for k,v in res.items():
    print(f'  {k}: {v[0]:6.1f}c , {v[1]:6.1%}')
