"""核验谱面：字的音高 vs 源 F0，字的顺序 vs 歌词，AP/SP 位置。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))

f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
def cents(a): return 6900.0 + 1200.0*np.log2(np.maximum(a, 1e-6)/440.0)
C_F = np.where(fv, cents(ff), np.nan); C_R = np.where(rv, cents(rf), np.nan)
AGREE = np.isfinite(C_F) & np.isfinite(C_R) & (np.abs(C_F-C_R) <= 100)
C_SRC = np.where(AGREE, (C_F+C_R)/2, np.nan)

# walk all parts, compare tone*100 to source median
errs = []
sung_text = []
for pi, part in enumerate(doc['voice_parts']):
    txt = []
    for n in part['notes']:
        if n['lyric'] in ('AP', 'SP'):
            continue
        a = tm.tick_to_ms(part['position']+n['position'])/1000
        b = tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        if n['lyric'] != '+':
            txt.append(n['lyric'])
        m = (ft >= a+0.2*(b-a)) & (ft < b-0.2*(b-a)) & np.isfinite(C_SRC)
        if m.sum() >= 2:
            src = float(np.median(C_SRC[m]))
            errs.append((n['tone']*100 - src, pi, n['lyric'], round(a,2), n['tone'], round(src/100,2)))
    sung_text.append(''.join(txt))

print(f'sung notes compared: {len(errs)}')
e = np.array([x[0] for x in errs])
print(f'tone vs source: median {np.median(e):+.1f}c  med|Δ| {np.median(np.abs(e)):.1f}c  '
      f'p90|Δ| {np.percentile(np.abs(e),90):.1f}c')
for thr in (50, 100, 200):
    print(f'  |Δ|>{thr}c: {(np.abs(e)>thr).mean():.1%}')

# lyric check vs words_v3
print('\nlyric sequence check:')
bad = 0
for pi, (part, wp) in enumerate(zip(doc['voice_parts'], W['phrases'])):
    if sung_text[pi] != wp['hanzi']:
        print(f"  MISMATCH p{pi}: score「{sung_text[pi]}」 vs words「{wp['hanzi']}」")
        bad += 1
print(f'  mismatched parts: {bad}/51')

# AP/SP
br = [(pi, n['lyric']) for pi, part in enumerate(doc['voice_parts'])
      for n in part['notes'] if n['lyric'] in ('AP','SP')]
print(f"\nAP/SP notes: {len(br)}  ({sum(1 for x in br if x[1]=='AP')} AP, "
      f"{sum(1 for x in br if x[1]=='SP')} SP)")
print('\nworst pitch deviations:')
for x in sorted(errs, key=lambda z: -abs(z[0]))[:15]:
    print(f"   p{x[1]} {x[2]} @{x[3]}s tone={x[4]} src={x[5]} Δ={x[0]:+.0f}c")
