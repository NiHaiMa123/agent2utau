import sys, json
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from agent2utau.openutau.ustx import load_ustx, TempoMap
p = 'runs/production/nianlun-from-scratch-v2-20261028/compiled/project.ustx'
d = load_ustx(p)
tm = TempoMap.from_doc(d)
vps = d['voice_parts']
print('n voice_parts', len(vps), 'total notes', sum(len(x['notes']) for x in vps))
print('part0 keys:', list(vps[0]))
print('part0 track', vps[0].get('track'), 'pos', vps[0]['position'], 'n', len(vps[0]['notes']))
for i in (0, 1, 25, 50):
    pt = vps[i]
    ns = pt['notes']
    print(f'--- p{i} pos={pt["position"]} n={len(ns)} ---')
    for n in ns[:5]:
        print('   ', {k: n.get(k) for k in ('position', 'duration', 'tone', 'lyric')},
              'ms', round(tm.tick_to_ms(pt['position'] + n['position']), 1))
# lyric inventory
from collections import Counter
c = Counter()
for pt in vps:
    for n in pt['notes']:
        c[n['lyric']] += 1
print('distinct lyrics:', len(c))
print('top:', c.most_common(12))
print('special:', {k: v for k, v in c.items() if k in ('AP', 'SP', '+', '')})
