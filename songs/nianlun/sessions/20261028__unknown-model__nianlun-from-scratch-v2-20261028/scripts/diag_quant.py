"""Is the residual systematic = integer-semitone quantization of the melody?"""
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

# For each note, source median (semitone float) vs tone (int)
offs = []
for pt in doc['voice_parts']:
    for n in pt['notes']:
        if n['lyric'] in ('AP','SP','+'): continue
        a = tm.tick_to_ms(pt['position']+n['position'])/1000
        b = tm.tick_to_ms(pt['position']+n['position']+n['duration'])/1000
        dur = b-a
        m = (st >= a+0.25*dur) & (st < b-0.25*dur) & ok
        if m.sum() < 3: continue
        src_semi = np.nanmedian(c_use[m])/100
        offs.append(src_semi - n['tone'])
offs = np.array(offs)
print(f'notes: {len(offs)}')
print(f'source_semitone - note_tone: median {np.median(offs):+.3f} semitones = {np.median(offs)*100:+.1f}c')
print(f'  |offset| in cents: median {np.median(np.abs(offs))*100:.1f}c, p90 {np.percentile(np.abs(offs),90)*100:.1f}c')
print(f'  NOTE: a pure int-quantization would give offsets uniform in +-0.5 semi (med|.| ~25c)')

# check: is the design's vowel-body pitch equal to tone*100 + 0.8*residual?
# compare design median inside vowel to tone*100 and to source median
p = json.load(io.open(f'{RUN}/compiled/pitch.json', encoding='utf-8'))
dt, dc = [], []
for phr in p['phrases']:
    dt.append(np.asarray(phr['times_ms'], float)/1000); dc.append(np.asarray(phr['final_cents'], float))
dt = np.concatenate(dt); dc = np.concatenate(dc); o = np.argsort(dt); dt, dc = dt[o], dc[o]

rows = []
for pt in doc['voice_parts']:
    for n in pt['notes']:
        if n['lyric'] in ('AP','SP','+'): continue
        a = tm.tick_to_ms(pt['position']+n['position'])/1000
        b = tm.tick_to_ms(pt['position']+n['position']+n['duration'])/1000
        dur = b-a
        m = (st >= a+0.25*dur) & (st < b-0.25*dur) & ok
        if m.sum() < 3: continue
        src_med = np.nanmedian(c_use[m])
        des_med = np.median(np.interp(st[m], dt, dc))
        rows.append((src_med, des_med, n['tone']*100))
rows = np.array(rows)
print(f'\ndesign_median - source_median : median {np.median(rows[:,1]-rows[:,0]):+.1f}c')
print(f'design_median - tone*100      : median {np.median(rows[:,1]-rows[:,2]):+.1f}c')
print(f'tone*100      - source_median : median {np.median(rows[:,2]-rows[:,0]):+.1f}c')
print('\n=> if design_median ~= tone*100, the plan centers on the quantized tone (loses sub-semitone)')
print(f'   |design - tone*100| median {np.median(np.abs(rows[:,1]-rows[:,2])):.1f}c')
