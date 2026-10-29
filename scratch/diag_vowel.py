"""Precise: compare ONLY inside true vowel nuclei (exclude consonant/transition).
Question: within the vowel body, does the design follow the source, and how well?
"""
import sys, json, io, numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from agent2utau.openutau.ustx import load_ustx, TempoMap

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'
def midi(hz): return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)

s = np.load(f'{RUN}/observation/fcpe.npz'); st, sf, sv = s['times'], s['f0_hz'], s['voiced']
s2 = np.load(f'{RUN}/observation/rmvpe.npz'); smf, smv = s2['f0_hz'], s2['voiced']
c_fc = midi(sf)*100; c_rm = midi(smf)*100
ok = sv & smv & (np.abs(c_fc-c_rm) < 50)
c_use = np.where(ok, (c_fc+c_rm)/2, np.nan)

# vowel phones from HFA
h = json.load(io.open(f'{RUN}/hfa/hfa_summary.json', encoding='utf-8'))
VOWELS = set('a o e i u v ai ei ao ou an en ang eng ong ia ie iao iou ian in iang ing iong ua uo uai uei uan uen uang ueng van vn er'.split())
vowel_spans = []
for ph in h['phrases']:
    for p in ph['phones']:
        if p['mark'] in VOWELS and p['dur_s'] > 0.05:
            vowel_spans.append((p['start_s'], p['end_s']))
print(f'vowel nuclei from HFA: {len(vowel_spans)}')

p = json.load(io.open(f'{RUN}/compiled/pitch.json', encoding='utf-8'))
dt, dc = [], []
for phr in p['phrases']:
    dt.append(np.asarray(phr['times_ms'], float)/1000)
    dc.append(np.asarray(phr['final_cents'], float))
dt = np.concatenate(dt); dc = np.concatenate(dc)
o = np.argsort(dt); dt, dc = dt[o], dc[o]

n_in = 0; errs = []; srcs = []; dess = []
for a, b in vowel_spans:
    dur = b-a
    lo, hi = a + 0.20*dur, b - 0.20*dur     # inside vowel body, skip 20% edges
    m = (st >= lo) & (st < hi) & ok
    if m.sum() < 4: continue
    n_in += 1
    src = c_use[m]; des = np.interp(st[m], dt, dc)
    errs.append(des-src); srcs.append(src); dess.append(des)
errs = np.concatenate(errs); srcs = np.concatenate(srcs); dess = np.concatenate(dess)
print(f'\n=== INSIDE vowel body (20% edges removed): {n_in} nuclei, {len(errs)} frames ===')
print(f'  design vs source: median {np.median(errs):+6.1f}c  med|Δ| {np.median(np.abs(errs)):5.1f}c  p90|Δ| {np.percentile(np.abs(errs),90):6.1f}')
for thr in (50, 100, 200):
    print(f'    |Δ|>{thr:4d}c: {(np.abs(errs)>thr).mean():6.1%}')

# Correlation of *shape* (remove per-vowel mean) => does design follow source movement?
r_shapes = []
i = 0
for a, b in vowel_spans:
    dur = b-a
    lo, hi = a + 0.20*dur, b - 0.20*dur
    m = (st >= lo) & (st < hi) & ok
    if m.sum() < 6: continue
    src = c_use[m]; des = np.interp(st[m], dt, dc)
    if np.std(src) > 5 and np.std(des) > 5:
        r_shapes.append(np.corrcoef(src, des)[0,1])
r_shapes = np.array(r_shapes)
print(f'\n  per-vowel SHAPE correlation: n={len(r_shapes)} median r={np.median(r_shapes):.3f}')
print(f'    r>0.8: {(r_shapes>0.8).mean():.1%}   r<0.4: {(r_shapes<0.4).mean():.1%}')

print(f'\n  source vowel-body std: median {np.median([np.std(x) for x in srcs]):.1f}c')
print(f'  design vowel-body std: median {np.median([np.std(x) for x in dess]):.1f}c')
