import sys
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from agent2utau.openutau.ustx import load_ustx, TempoMap
p = 'runs/production/nianlun-from-scratch-v2-20261028/compiled/project.ustx'
d = load_ustx(p)
tm = TempoMap.from_doc(d)
for i, pt in enumerate(d['voice_parts']):
    t0 = tm.tick_to_ms(pt['position'])
    sung = ''.join(n['lyric'] for n in pt['notes'] if n['lyric'] not in ('AP', 'SP', '+'))
    print(f'p{i:02d} {t0/1000:7.2f}s n={len(pt["notes"]):2d} {sung}')
