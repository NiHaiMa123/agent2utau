import json

hfa = json.loads(open('runs/production/zuihouyiye-from-scratch-20261027/hfa/hfa_summary.json', encoding='utf-8').read())
print("Total HFA phrases:", len(hfa['phrases']))
for pi in range(16, len(hfa['phrases'])):
    p = hfa['phrases'][pi]
    print(f"P{pi:02d} [{p['phrase_start_s']:6.2f}s - {p['phrase_end_s']:6.2f}s]: '{p['hanzi']}' words={len(p.get('words', []))}")
