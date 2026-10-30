"""Decisive test: does the render realize the requested pitch curve?
   design final_cents (what we asked) vs render F0 (what came out).
   Both on the same 10ms absolute grid. Restricted to reliably-voiced frames.
"""
import sys, json, io, numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'

def midi(hz): return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)

# render F0
r = np.load('scratch/render_fcpe.npz'); rt, rf, rv = r['times'], r['f0_hz'], r['voiced']
r2 = np.load('scratch/render_rmvpe.npz'); rmt, rmf, rmv = r2['times'], r2['f0_hz'], r2['voiced']
# source F0 (for reference)
s = np.load(f'{RUN}/observation/fcpe.npz'); st, sf, sv = s['times'], s['f0_hz'], s['voiced']
s2 = np.load(f'{RUN}/observation/rmvpe.npz'); smf, smv = s2['f0_hz'], s2['voiced']

# design: assemble a continuous design grid from pitch.json phrases
p = json.load(io.open(f'{RUN}/compiled/pitch.json', encoding='utf-8'))
dt, dc = [], []
for phr in p['phrases']:
    t = np.asarray(phr['times_ms'], float)/1000
    c = np.asarray(phr['final_cents'], float)
    dt.append(t); dc.append(c)
dt = np.concatenate(dt); dc = np.concatenate(dc)
order = np.argsort(dt); dt, dc = dt[order], dc[order]

T = np.arange(18.0, 243.0, 0.01)
design_c = np.interp(T, dt, dc)

rnd_midi = np.interp(T, rt, midi(rf)); rnd_v = np.interp(T, rt, rv.astype(float)) > 0.5
rnd_rm_midi = np.interp(T, rmt, midi(rmf)); rnd_rm_v = np.interp(T, rmt, rmv.astype(float)) > 0.5
src_midi = np.interp(T, st, midi(sf)); src_v = np.interp(T, st, sv.astype(float)) > 0.5
src_rm_midi = np.interp(T, st, midi(smf)); src_rm_v = np.interp(T, st, smv.astype(float)) > 0.5

# render reliable where both detectors voiced and agree
rnd_ok = rnd_v & rnd_rm_v & (np.abs(rnd_midi - rnd_rm_midi) < 0.5)
src_ok = src_v & src_rm_v & (np.abs(src_midi - src_rm_midi) < 0.5)

design_midi = design_c/100

print('=== A. render vs DESIGN (engine fidelity) ===')
m = rnd_ok
d = (rnd_midi - design_midi)[m]*100
print(f'  n={m.sum()}  median {np.median(d):+6.1f}c  med|Δ| {np.median(np.abs(d)):6.1f}c  p90|Δ| {np.percentile(np.abs(d),90):6.1f}')
print(f'  |Δ|>50c {(np.abs(d)>50).mean():6.1%}   >100c {(np.abs(d)>100).mean():6.1%}   >200c {(np.abs(d)>200).mean():6.1%}')

print('\n=== B. DESIGN vs SOURCE (is the target right?) ===')
m2 = src_ok & (T <= dt.max())
d2 = (design_midi - src_midi)[m2]*100
print(f'  n={m2.sum()}  median {np.median(d2):+6.1f}c  med|Δ| {np.median(np.abs(d2)):6.1f}c  p90|Δ| {np.percentile(np.abs(d2),90):6.1f}')
print(f'  |Δ|>50c {(np.abs(d2)>50).mean():6.1%}   >100c {(np.abs(d2)>100).mean():6.1%}   >200c {(np.abs(d2)>200).mean():6.1%}')

print('\n=== C. render vs SOURCE (end-to-end, only where both agree) ===')
m3 = rnd_ok & src_ok
d3 = (rnd_midi - src_midi)[m3]*100
print(f'  n={m3.sum()}  median {np.median(d3):+6.1f}c  med|Δ| {np.median(np.abs(d3)):6.1f}c  p90|Δ| {np.percentile(np.abs(d3),90):6.1f}')
print(f'  |Δ|>50c {(np.abs(d3)>50).mean():6.1%}   >100c {(np.abs(d3)>100).mean():6.1%}   >200c {(np.abs(d3)>200).mean():6.1%}')

# Which dominates? if A small and B large -> target wrong.
print('\n=== verdict ===')
print(f'  A (engine) med|Δ| {np.median(np.abs(d)):.1f}c   B (target) med|Δ| {np.median(np.abs(d2)):.1f}c')
