import sys, json, io
import numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'runs/production/nianlun-v3-20261029')
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)
t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
c = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
o = np.argsort(t); t, c = t[o], c[o]

T = np.arange(28.60, 29.30, 0.005)
C = np.interp(T, t, c)
m = (T >= 28.78) & (T <= 29.02)
seg = C[m]; d = np.diff(seg)
print('p2:f0:v6 boundary 28.78-29.02:')
print(f'  range {seg.min():.0f}..{seg.max():.0f}')
print(f'  monotone increasing (all diffs >= -2c): {np.all(d >= -2)}')
print(f'  negative steps < -15c: {(d < -15).sum()}   min step {d.min():.1f}c')
m2 = (T >= 28.62) & (T <= 28.86)
print(f'  body 28.62-28.86 swing: {C[m2].max()-C[m2].min():.0f}c')

# 全局：所有大跳边界是否单调
import collections
parts_notes = {}
for pi, part in enumerate(doc['voice_parts']):
    ns = []
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a = tm.tick_to_ms(part['position']+n['position'])/1000
        b = tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a, b=b, tone=n['tone']))
    ns.sort(key=lambda x: x['a'])
    parts_notes[pi] = ns

bad = []
total = 0
for pi, ns in parts_notes.items():
    for a, b in zip(ns, ns[1:]):
        jump = b['tone'] - a['tone']
        if abs(jump) < 4: continue
        total += 1
        TT = np.arange(a['b']-0.12, a['b']+0.12, 0.005)
        CC = np.interp(TT, t, c)
        dd = np.diff(CC)
        wrong = (dd < -15).sum() if jump > 0 else (dd > 15).sum()
        if wrong > 2:
            bad.append((pi, a['b'], jump, int(wrong)))

print(f'\nlarge leaps (>=4 semitones): {total}')
print(f'  leaps with >2 counter-direction steps in +/-120ms: {len(bad)}')
for x in bad[:10]:
    print(f'    part {x[0]} @{x[1]:.2f}s jump {x[2]:+d} semis, {x[3]} counter steps')
