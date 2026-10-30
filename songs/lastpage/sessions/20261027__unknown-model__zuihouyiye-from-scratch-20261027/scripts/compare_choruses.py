import json
from agent2utau.openutau.ustx import load_ustx, TempoMap

doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/compiled_v4/project.ustx')
phones = json.loads(open('runs/production/zuihouyiye-from-scratch-20261027/compiled_v4/phones.json', encoding='utf-8').read())
tm = TempoMap.from_doc(doc)

c1_parts = [10, 11, 12, 13, 14, 15]
c2_parts = [26, 27, 28, 29, 30, 31]
c3_parts = [32, 33, 34, 35, 36, 37]

for i in range(6):
    p1 = doc['voice_parts'][c1_parts[i]]
    p2 = doc['voice_parts'][c2_parts[i]]
    p3 = doc['voice_parts'][c3_parts[i]]
    ph1 = [x['phoneme'] for x in phones['parts'][c1_parts[i]]['phrases'][0]['phones']]
    ph2 = [x['phoneme'] for x in phones['parts'][c2_parts[i]]['phrases'][0]['phones']]
    ph3 = [x['phoneme'] for x in phones['parts'][c3_parts[i]]['phrases'][0]['phones']]

    l1 = [(n.get('lyric'), n['tone']) for n in p1['notes']]
    l2 = [(n.get('lyric'), n['tone']) for n in p2['notes']]
    l3 = [(n.get('lyric'), n['tone']) for n in p3['notes']]

    print(f"\n==================== Line {i+1} ====================")
    print(f"C1 (Part {c1_parts[i]:2d}): {l1}")
    print(f"   Phones: {ph1}")
    print(f"C2 (Part {c2_parts[i]:2d}): {l2}")
    print(f"   Phones: {ph2}")
    print(f"C3 (Part {c3_parts[i]:2d}): {l3}")
    print(f"   Phones: {ph3}")
