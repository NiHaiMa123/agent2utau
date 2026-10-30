import sys, numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'

def load(p):
    d = np.load(p)
    return d['times'], d['f0_hz'], d['voiced']

s_t, s_fc, s_vfc = load(f'{RUN}/observation/fcpe.npz')
_, s_rm, s_vrm = load(f'{RUN}/observation/rmvpe.npz')
r_t, r_fc, r_vfc = load('scratch/render_fcpe.npz')
_, r_rm, r_vrm = load('scratch/render_rmvpe.npz')

def midi(hz):
    return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)

# source grid is 10ms starting at 0; render grid probably same
print('src times 0..3:', s_t[:4], ' render times 0..3:', r_t[:4])
print('src step', np.diff(s_t[:5]), 'render step', np.diff(r_t[:5]))

# interpolate to common 10ms grid
T = s_t
src_fc = midi(s_fc); rnd_fc = midi(np.interp(T, r_t, r_fc))
src_rm = midi(s_rm); rnd_rm = midi(np.interp(T, r_t, r_rm))
# voiced mask by nearest
r_vfc_i = np.interp(T, r_t, r_vfc.astype(float)) > 0.5
r_vrm_i = np.interp(T, r_t, r_vrm.astype(float)) > 0.5

in_song = (T > 18) & (T < 243)
valid = s_vfc & s_vrm & r_vfc_i & r_vrm_i & in_song
print(f'\ncomparable frames: {valid.sum()} / {in_song.sum()} ({(valid.sum()/in_song.sum()):.1%})')

for nm, a, b in (('fcpe', src_fc, rnd_fc), ('rmvpe', src_rm, rnd_rm)):
    d = (b - a)[valid]*100
    print(f'{nm}: median |Δ| {np.median(np.abs(d)):6.1f}c  p75 {np.percentile(np.abs(d),75):6.1f}  p90 {np.percentile(np.abs(d),90):6.1f}  mean {d.mean():+7.1f}')
    for thr in (50, 100, 200, 500):
        print(f'      |Δ|>{thr:4d}c: {(np.abs(d)>thr).mean():6.1%}')

# per-second error map
print('\nper-5s median |Δ| (fcpe):')
for t0 in range(15, 245, 10):
    m = valid & (T >= t0) & (T < t0+10)
    if m.sum() < 20: continue
    d = (rnd_fc - src_fc)[m]*100
    print(f'  {t0:3d}-{t0+10:3d}s  n={m.sum():4d}  med|Δ|={np.median(np.abs(d)):6.1f}c  mean={d.mean():+6.1f}c')
