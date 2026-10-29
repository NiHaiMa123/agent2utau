import json
from agent2utau.openutau.ustx import load_ustx, TempoMap

doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/compiled_v4/project.ustx')
phones = json.loads(open('runs/production/zuihouyiye-from-scratch-20261027/compiled_v4/phones.json', encoding='utf-8').read())
tm = TempoMap.from_doc(doc)

v1_parts = list(range(0, 10))
v2_parts = list(range(16, 26))

for i in range(10):
    p1 = doc['voice_parts'][v1_parts[i]]
    p2 = doc['voice_parts'][v2_parts[i]]
    ph1 = [x['phoneme'] for x in phones['parts'][v1_parts[i]]['phrases'][0]['phones']]
    ph2 = [x['phoneme'] for x in phones['parts'][v2_parts[i]]['phrases'][0]['phones']]

    l1 = [(n.get('lyric'), n['tone']) for n in p1['notes']]
    l2 = [(n.get('lyric'), n['tone']) for n in p2['notes']]

    print(f"\n==================== Line {i+1} ====================")
    print(f"V1 (Part {v1_parts[i]:2d}): {l1}")
    print(f"   Phones: {ph1}")
    print(f"V2 (Part {v2_parts[i]:2d}): {l2}")
    print(f"   Phones: {ph2}")
