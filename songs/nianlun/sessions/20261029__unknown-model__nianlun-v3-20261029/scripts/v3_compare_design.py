"""核心验证：v3 的设计最终线 vs 原唱 F0，并与 v2 同口径对比。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

V3 = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')

def midi(hz): return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)

def load_src(run):
    s = np.load(run/'inputs/fcpe.npz' if (run/'inputs/fcpe.npz').exists() else run/'observation/fcpe.npz')
    s2 = np.load(run/'inputs/rmvpe.npz' if (run/'inputs/rmvpe.npz').exists() else run/'observation/rmvpe.npz')
    cf = np.where(s['voiced'], midi(s['f0_hz'])*100, np.nan)
    cr = np.where(s2['voiced'], midi(s2['f0_hz'])*100, np.nan)
    ok = np.isfinite(cf) & np.isfinite(cr) & (np.abs(cf-cr) <= 100)
    return s['times'].astype(float), np.where(ok, (cf+cr)/2, np.nan)

def design_series(run, name):
    p = json.load(io.open(run/name, encoding='utf-8'))
    t, c = [], []
    for phr in p['phrases']:
        t.append(np.asarray(phr['times_ms'], float)/1000)
        c.append(np.asarray(phr['final_cents'], float))
    t = np.concatenate(t); c = np.concatenate(c)
    o = np.argsort(t)
    return t[o], c[o]

for label, run, name in [('v2 (previous)', V2, 'compiled/pitch.json'),
                         ('v3 (this run)', V3, 'compiled/pitch.json')]:
    st, sc = load_src(run)
    dt, dc = design_series(run, name)
    T = np.arange(max(dt.min(), st.min())+0.01, min(dt.max(), st.max())-0.01, 0.01)
    src = np.interp(T, st, np.nan_to_num(sc, nan=np.nan), left=np.nan, right=np.nan)
    # manual nan-aware interp
    good = np.isfinite(sc)
    src = np.interp(T, st[good], sc[good])
    des = np.interp(T, dt, dc)
    d = des - src
    print(f'\n=== {label} ===')
    print(f'  frames {len(T)}, note count {"58 native" if "v3" in label else "51 native"}')
    print(f'  design vs source: median {np.median(d):+7.1f}c  med|Δ| {np.median(np.abs(d)):6.1f}c  '
          f'p90|Δ| {np.percentile(np.abs(d),90):6.1f}c')
    for thr in (50, 100, 200):
        print(f'    |Δ|>{thr:4d}c: {(np.abs(d)>thr).mean():6.1%}')
