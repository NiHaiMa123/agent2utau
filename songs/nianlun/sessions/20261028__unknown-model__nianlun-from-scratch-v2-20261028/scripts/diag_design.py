import sys, json, io, numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'

p = json.load(io.open(f'{RUN}/compiled/pitch.json', encoding='utf-8'))
print('pitch.json keys:', list(p))
ph = p['phrases']
print('n phrases', len(ph), 'phrase0 keys', list(ph[0]))
print('times_ms head', ph[0]['times_ms'][:4])
print('final_cents head', np.asarray(ph[0]['final_cents'])[:6])
print('before_pitd head', np.asarray(ph[0]['before_pitd_cents'])[:6])
print('pitch_start_tick', ph[0].get('pitch_start_tick'), 'interval', ph[0].get('pitch_interval_ticks'))

# compare design final_cents vs source fcpe
def midi(hz):
    return 69 + 12*np.log2(np.maximum(hz, 1e-6)/440)
d = np.load(f'{RUN}/observation/fcpe.npz'); s_t, s_fc, s_vfc = d['times'], d['f0_hz'], d['voiced']

allerr = []
for phr in ph:
    t = np.asarray(phr['times_ms'], float)/1000
    fc = np.asarray(phr['final_cents'], float)
    m = (s_t >= t[0]) & (s_t <= t[-1]) & s_vfc
    if m.sum() < 5: continue
    # source midi -> cents relative to 6900 (C4+? just use diff of midi*100)
    smidi = np.interp(s_t[m], t, fc/100)
    err = (midi(s_fc[m]) - smidi)*100
    allerr.append(err)
allerr = np.concatenate(allerr)
print(f'\nDESIGN final line vs source FCPE: n={len(allerr)} med|Δ|={np.median(np.abs(allerr)):.1f}c p90={np.percentile(np.abs(allerr),90):.1f} >100c={(np.abs(allerr)>100).mean():.1%}')
print(f'  meaning: design line is {allerr.mean():+.1f}c relative to source (positive=design higher)')
