import sys, numpy as np, json, io
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from agent2utau.openutau.ustx import load_ustx, TempoMap

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'
fc = np.load(f'{RUN}/observation/fcpe.npz')
rm = np.load(f'{RUN}/observation/rmvpe.npz')
t = fc['times']; f_fc = fc['f0_hz']; v_fc = fc['voiced']
f_rm = rm['f0_hz']; v_rm = rm['voiced']
both = v_fc & v_rm
print(f'frames {len(t)}, fcpe voiced {v_fc.mean():.2%}, rmvpe voiced {v_rm.mean():.2%}, both {both.mean():.2%}')

def cents(a, b):
    return 1200*np.log2(np.maximum(a,1e-6)/np.maximum(b,1e-6))

d = cents(f_fc[both], f_rm[both])
print(f'dual-detector cents diff: median {np.median(np.abs(d)):.2f}, p90 {np.percentile(np.abs(d),90):.2f}')
for thr in (50, 100, 200, 400):
    print(f'  |diff|>{thr}c: {(np.abs(d)>thr).mean():.2%}')

# per-note: compare USTX tone to source F0 median within note span
doc = load_ustx(f'{RUN}/compiled/project.ustx')
tm = TempoMap.from_doc(doc)
rows = []
for pt in doc['voice_parts']:
    for n in pt['notes']:
        if n['lyric'] in ('AP', 'SP', '+'):
            continue
        a = tm.tick_to_ms(pt['position']+n['position'])/1000
        b = tm.tick_to_ms(pt['position']+n['position']+n['duration'])/1000
        m = (t >= a) & (t < b) & both
        if m.sum() < 3:
            continue
        med_fc = np.median(f_fc[m]); med_rm = np.median(f_rm[m])
        midi_fc = 69+12*np.log2(med_fc/440); midi_rm = 69+12*np.log2(med_rm/440)
        rows.append((n['lyric'], n['tone'], midi_fc, midi_rm, b-a))

tone = np.array([r[1] for r in rows])
mfc = np.array([r[2] for r in rows]); mrm = np.array([r[3] for r in rows])
print(f'\nnotes with F0 coverage: {len(rows)}')
for nm, v in (('fcpe', mfc), ('rmvpe', mrm)):
    e = (v-tone)*100
    print(f'  score-vs-{nm}: median {np.median(np.abs(e)):.1f}c, p90 {np.percentile(np.abs(e),90):.1f}c, >100c {(np.abs(e)>100).mean():.2%}')
dd = (mfc-mrm)*100
print(f'  detector-vs-detector per note: median {np.median(np.abs(dd)):.1f}c, >100c {(np.abs(dd)>100).mean():.2%}')

# how many notes have dur < 100ms
durs = np.array([r[4] for r in rows])
print(f'\nnote dur: median {np.median(durs)*1000:.0f}ms, <100ms {(durs<0.1).sum()}, <60ms {(durs<0.06).sum()}')
