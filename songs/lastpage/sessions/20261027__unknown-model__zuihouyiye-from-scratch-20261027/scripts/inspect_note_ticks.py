from agent2utau.openutau.ustx import load_ustx
doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx')
for pi in [9, 10, 11, 12, 13, 14]:
    vp = doc['voice_parts'][pi]
    print(f"=== Part {pi} ({vp['name']}) ===")
    for ni, n in enumerate(vp['notes']):
        print(f"  note {ni:2d} pos={n['position']:5d} dur={n['duration']:5d} tone={n['tone']} lyric='{n.get('lyric')}'")
