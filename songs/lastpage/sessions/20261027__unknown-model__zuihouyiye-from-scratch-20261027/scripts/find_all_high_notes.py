from agent2utau.openutau.ustx import load_ustx
doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx')
for pi, vp in enumerate(doc['voice_parts']):
    for ni, n in enumerate(vp['notes']):
        if n['tone'] >= 72:
            print(f"Part {pi:2d} note {ni:2d} pos={n['position']:5d} dur={n['duration']:5d} tone={n['tone']} lyric='{n.get('lyric')}'")
