"""公平对比：只在「演唱元音核」窗口内比较设计线 vs 原唱 F0。
元音核 = 该字的连续有声段；排除辅音、AP、静音、过渡。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

V3 = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')

def midi(hz): return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)

def load_src(run):
    s = np.load(run/'inputs/fcpe.npz')
    s2 = np.load(run/'inputs/rmvpe.npz')
    return (s['times'].astype(float),
            np.where(s['voiced'], midi(s['f0_hz'])*100, np.nan),
            np.where(s2['voiced'], midi(s2['f0_hz'])*100, np.nan))

def design(run):
    p = json.load(io.open(run/'compiled/pitch.json', encoding='utf-8'))
    t = np.concatenate([np.asarray(x['times_ms'], float)/1000 for x in p['phrases']])
    c = np.concatenate([np.asarray(x['final_cents'], float) for x in p['phrases']])
    o = np.argsort(t)
    return t[o], c[o]

def vowel_windows(run, words_file):
    w = json.load(io.open(run/words_file, encoding='utf-8'))
    out = []
    for p in w['phrases']:
        for x in p['words']:
            a, b = x['start'], x['end']
            d = b-a
            out.append((a+0.22*d, b-0.22*d))     # 只用字内中间 56%，避开辅音与过渡
    return out

for label, run, wf in [('v2 (previous)', V2, 'words_v3.json'),
                       ('v3 (this run)', V3, 'words_v3.json')]:
    if not (run/wf).exists():
        print(f'{label}: no {wf}'); continue
    st, cf, cr = load_src(run)
    dt, dc = design(run)
    ok = np.isfinite(cf) & np.isfinite(cr) & (np.abs(cf-cr) <= 100)
    src_c = np.where(ok, (cf+cr)/2, np.nan)
    wins = vowel_windows(run, wf)
    errs = []
    for a, b in wins:
        if b <= a: continue
        T = np.arange(a, b, 0.01)
        if len(T) < 3: continue
        i = np.clip(np.rint(T*100).astype(int), 0, len(st)-1)
        s = src_c[i]
        m = np.isfinite(s)
        if m.sum() < 3: continue
        d = np.interp(T[m], dt, dc) - s[m]
        errs.append(d)
    if not errs:
        print(f'{label}: no comparable windows'); continue
    e = np.concatenate(errs)
    print(f'\n=== {label} : inside syllable cores (middle 56%), {len(errs)} syllables, {len(e)} frames ===')
    print(f'  median {np.median(e):+7.1f}c   med|Δ| {np.median(np.abs(e)):6.1f}c   '
          f'p90|Δ| {np.percentile(np.abs(e),90):6.1f}c')
    for thr in (50, 100, 200):
        print(f'    |Δ|>{thr:4d}c: {(np.abs(e)>thr).mean():6.1%}')
