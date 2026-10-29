import sys, json, io, numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'
d = np.load(f'{RUN}/observation/fcpe.npz'); s_t, s_fc, s_vfc = d['times'], d['f0_hz'], d['voiced']
d2 = np.load(f'{RUN}/observation/rmvpe.npz'); s_rm, s_vrm = d2['f0_hz'], d2['voiced']

def midi(hz): return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)
mid_fc, mid_rm = midi(s_fc), midi(s_rm)
agree = s_vfc & s_vrm & (np.abs(mid_fc-mid_rm) < 0.5)   # <50c disagreement
print(f'reliable frames (both voiced, <50c apart): {agree.mean():.1%}')

g = json.load(io.open(f'{RUN}/observation/game.json', encoding='utf-8'))
notes = g['notes']
print('GAME notes:', len(notes), 'span', notes[0]['start'], '-', notes[-1]['start']+notes[-1]['dur'])
print('voiced flags: voiced', sum(n['voiced'] for n in notes), 'unvoiced', sum(not n['voiced'] for n in notes))

errs, durs, n_used = [], [], 0
for n in notes:
    a, b = n['start'], n['start']+n['dur']
    m = (s_t >= a+0.25*n['dur']) & (s_t < b-0.25*n['dur']) & agree
    durs.append(n['dur'])
    if m.sum() < 2: continue
    med = np.median(mid_fc[m])
    errs.append((med - n['tone'])*100); n_used += 1
errs = np.array(errs); durs = np.array(durs)
print(f'\nGAME tone vs source F0 (reliable frames, middle 50% of each GAME note): n={n_used}')
print(f'  median |Δ| {np.median(np.abs(errs)):.1f}c  p75 {np.percentile(np.abs(errs),75):.1f}  p90 {np.percentile(np.abs(errs),90):.1f}')
for thr in (50,100,200,400,600):
    print(f'  |Δ|>{thr}c: {(np.abs(errs)>thr).mean():6.1%}')

# Distribution of GAME note durations
print(f'\nGAME note dur: <0.08s {(durs<0.08).sum()}, <0.15s {(durs<0.15).sum()}, median {np.median(durs):.3f}s')
print('GAME notes with dur<0.1s:', [(round(n['start'],2), round(n['dur'],3), round(n['tone'],2), n['voiced']) for n in notes if n['dur']<0.1][:20])

# Are GAME notes non-overlapping / contiguous?
gaps = []
for a, b in zip(notes, notes[1:]):
    gp = b['start'] - (a['start']+a['dur'])
    gaps.append(gp)
gaps = np.array(gaps)
print(f'\nGAME inter-note gap: median {np.median(gaps)*1000:.0f}ms, >100ms {(gaps>0.1).sum()}, >300ms {(gaps>0.3).sum()}, min {gaps.min()*1000:.0f}ms')
