"""Is it a CLOCK problem? Search best time-shift between design curve and source F0."""
import sys, json, io, numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'
def midi(hz): return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)

s = np.load(f'{RUN}/observation/fcpe.npz'); st, sf, sv = s['times'], s['f0_hz'], s['voiced']
s2 = np.load(f'{RUN}/observation/rmvpe.npz'); smf, smv = s2['f0_hz'], s2['voiced']
c_fc = midi(sf)*100; c_rm = midi(smf)*100
ok = sv & smv & (np.abs(c_fc-c_rm) < 50)
c_use = np.where(ok, (c_fc+c_rm)/2, np.nan)

p = json.load(io.open(f'{RUN}/compiled/pitch.json', encoding='utf-8'))

print('=== per-phrase best time shift ===')
shifts = []
for phr in p['phrases']:
    t = np.asarray(phr['times_ms'], float)/1000
    c = np.asarray(phr['final_cents'], float)
    if len(t) < 20: continue
    best = None
    for shift in np.arange(-0.30, 0.301, 0.01):
        m = (st >= t[0]+shift) & (st <= t[-1]+shift) & ok
        if m.sum() < 15: continue
        src = c_use[m]
        des = np.interp(st[m]-shift, t, c)
        e = np.median(np.abs(des-src))
        if best is None or e < best[1]:
            best = (shift, e)
    if best:
        # baseline at shift 0
        m0 = (st >= t[0]) & (st <= t[-1]) & ok
        e0 = np.median(np.abs(np.interp(st[m0], t, c) - c_use[m0])) if m0.sum() >= 15 else np.nan
        shifts.append((phr['position'], best[0], best[1], e0))

sh = np.array([x[1] for x in shifts])
b0 = np.array([x[3] for x in shifts]); b1 = np.array([x[2] for x in shifts])
print(f'  n phrases {len(shifts)}')
print(f'  best shift: median {np.median(sh)*1000:+.0f}ms  mean {sh.mean()*1000:+.0f}ms  p10 {np.percentile(sh,10)*1000:+.0f}  p90 {np.percentile(sh,90)*1000:+.0f}')
print(f'  |shift|>50ms: {(np.abs(sh)>0.05).mean():.1%}   >100ms: {(np.abs(sh)>0.10).mean():.1%}')
print(f'  error at shift0: median {np.median(b0):.1f}c ; at best shift: median {np.median(b1):.1f}c')
print(f'  => if best shift is systematic and error drops a lot, it is a CLOCK problem')

print('\n=== worst-shift phrases ===')
for pos, s_, e1, e0 in sorted(shifts, key=lambda x: -abs(x[1]))[:12]:
    print(f'   pos={pos:6d}  shift {s_*1000:+7.0f}ms   err@0 {e0:6.1f}c -> {e1:6.1f}c')

# Also: test amplitude scaling hypothesis (design = tone + k*source_residual)
print('\n=== amplitude-ratio test: std(design)/std(source) per phrase ===')
rs = []
for phr in p['phrases']:
    t = np.asarray(phr['times_ms'], float)/1000
    c = np.asarray(phr['final_cents'], float)
    m = (st >= t[0]) & (st <= t[-1]) & ok
    if m.sum() < 20: continue
    des = np.interp(st[m], t, c); src = c_use[m]
    rs.append(np.std(des)/max(np.std(src),1e-6))
rs = np.array(rs)
print(f'  ratio median {np.median(rs):.2f}  p25 {np.percentile(rs,25):.2f}  p75 {np.percentile(rs,75):.2f}')
print(f'  ratio<0.6 (over-smoothed): {(rs<0.6).mean():.1%}')
