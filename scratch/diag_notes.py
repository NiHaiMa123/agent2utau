"""Per-note decomposition: is the integer tone wrong, or is the shape wrong?"""
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

doc = load_ustx(f'{RUN}/compiled/project.ustx')
tm = TempoMap.from_doc(doc)

tone_err, shape_err, spans, melisma = [], [], [], []
for pt in doc['voice_parts']:
    for n in pt['notes']:
        if n['lyric'] in ('AP','SP','+'): continue
        a = tm.tick_to_ms(pt['position']+n['position'])/1000
        b = tm.tick_to_ms(pt['position']+n['position']+n['duration'])/1000
        dur = b-a
        m = (st >= a+0.30*dur) & (st < b-0.30*dur) & ok
        if m.sum() < 3: continue
        src = np.nanmedian(c_use[m])
        tone_err.append((n['tone']*100 - src))
        sp = np.nanpercentile(c_use[m],95) - np.nanpercentile(c_use[m],5)
        spans.append(sp)
        shape_err.append(dur)

tone_err = np.array(tone_err); spans = np.array(spans)
print(f'sung notes with reliable core: {len(tone_err)}')
print('\n=== NOTE TONE (integer MIDI) vs source core median ===')
print(f'  median {np.median(tone_err):+6.1f}c   med|Δ| {np.median(np.abs(tone_err)):5.1f}c')
for thr in (25, 50, 75, 100, 150, 200, 300):
    print(f'  |Δ|>{thr:4d}c : {(np.abs(tone_err)>thr).mean():6.1%}')
print(f'\n  |Δ|<=50c (quantization only): {(np.abs(tone_err)<=50).mean():.1%}')
print(f'  50<|Δ|<=150c (tone off by ~1 semitone): {((np.abs(tone_err)>50)&(np.abs(tone_err)<=150)).mean():.1%}')
print(f'  |Δ|>150c (tone off >=1.5 semitone): {(np.abs(tone_err)>150).mean():.1%}')

print('\n=== SOURCE intra-note span (middle 40%) ===')
print(f'  median {np.median(spans):.0f}c  p75 {np.percentile(spans,75):.0f}  p90 {np.percentile(spans,90):.0f}')
print(f'  span>100c: {(spans>100).mean():.1%}   >200c: {(spans>200).mean():.1%}  >400c: {(spans>400).mean():.1%}')

# Biggest tone errors, listed
print('\n=== worst note tones ===')
idx = np.argsort(-np.abs(tone_err))[:25]
notes = [n for pt in doc['voice_parts'] for n in pt['notes'] if n['lyric'] not in ('AP','SP','+')]
# rebuild aligned list
aligned = []
for pt in doc['voice_parts']:
    for n in pt['notes']:
        if n['lyric'] in ('AP','SP','+'): continue
        a = tm.tick_to_ms(pt['position']+n['position'])/1000
        b = tm.tick_to_ms(pt['position']+n['position']+n['duration'])/1000
        dur = b-a
        m = (st >= a+0.30*dur) & (st < b-0.30*dur) & ok
        if m.sum() < 3: continue
        aligned.append((n['lyric'], round(a,2), n['tone'], round(np.nanmedian(c_use[m])/100,2), int(tone_err[len(aligned)])))
for r in sorted(aligned, key=lambda x: -abs(x[4]))[:25]:
    print(f'   {r[0]} @{r[1]:7.2f}s  tone={r[2]}  source={r[3]:6.2f}  Δ={r[4]:+6d}c')
