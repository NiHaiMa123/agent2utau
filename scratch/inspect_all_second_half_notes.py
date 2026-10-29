from agent2utau.openutau.ustx import load_ustx, TempoMap

doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx')
tm = TempoMap.from_doc(doc)

for pi in range(16, len(doc['voice_parts'])):
    vp = doc['voice_parts'][pi]
    pos = vp['position']
    print(f"\n=== Part {pi} ({vp['name']}) ===")
    for ni, n in enumerate(vp['notes']):
        ns = tm.tick_to_ms(pos + n['position']) / 1000.0
        ne = tm.tick_to_ms(pos + n['position'] + n['duration']) / 1000.0
        print(f"  note {ni:2d} [{ns:6.2f}s - {ne:6.2f}s] tone={n['tone']} dur={ne-ns:5.3f}s lyric='{n.get('lyric')}'")
