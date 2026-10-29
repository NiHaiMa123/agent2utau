import json

hfa = json.loads(open('runs/production/zuihouyiye-from-scratch-20261027/hfa/hfa_summary.json', encoding='utf-8').read())
for pi in range(16, len(hfa['phrases'])):
    p = hfa['phrases'][pi]
    w0 = p['words'][0]['start_s'] if p['words'] else 0
    w1 = p['words'][-1]['end_s'] if p['words'] else 0
    print(f"P{pi:02d} [{w0:6.2f}s - {w1:6.2f}s]: '{p['hanzi']}' words={' '.join([w['word'] for w in p['words']])}")
