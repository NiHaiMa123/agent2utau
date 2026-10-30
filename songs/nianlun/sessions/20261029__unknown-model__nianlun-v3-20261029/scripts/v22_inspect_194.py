import sys, json, io
import numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:/project/agent2utau/runs/production/nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))

# part 0 notes around 19.4s
p0 = doc['voice_parts'][0]
print('part0 notes 19.0-19.8s:')
for n in p0['notes']:
    a = tm.tick_to_ms(p0['position']+n['position'])/1000
    b = tm.tick_to_ms(p0['position']+n['position']+n['duration'])/1000
    if 19.0 <= a <= 19.8:
        print(f"  {n['lyric']:4s} {a:.3f}-{b:.3f} tone={n['tone']}")

# final line and before_pitd around 19.35-19.50
for ph in pf['phrases']:
    if int(ph['part_position']) == int(p0['position']):
        tt = np.asarray(ph['times_ms'],float)/1000
        cc = np.asarray(ph['final_cents'],float)
        m = (tt>=19.30)&(tt<=19.50)
        print('\nfinal line 19.30-19.50:')
        for x,y in zip(tt[m][::5], cc[m][::5]):
            print(f'  {x:.3f}  {y:.1f}')
        break

for ph in bp['phrases']:
    if int(ph['part_position']) == int(p0['position']):
        tt = np.asarray(ph['times_ms'],float)/1000
        cc = np.asarray(ph['before_pitd_cents'],float)
        m = (tt>=19.30)&(tt<=19.50)
        print('\nbefore_pitd 19.30-19.50:')
        for x,y in zip(tt[m][::10], cc[m][::10]):
            print(f'  {x:.3f}  {y:.1f}')
        break
