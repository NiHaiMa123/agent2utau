from agent2utau.openutau.ustx import load_ustx, TempoMap
doc = load_ustx('runs/production/zuihouyiye-from-scratch-20261027/design/score.ustx')
tm = TempoMap.from_doc(doc)
for pi, vp in enumerate(doc['voice_parts']):
    pos = vp['position']
    for ni, n in enumerate(vp['notes']):
        ns = tm.tick_to_ms(pos + n['position']) / 1000.0
        ne = tm.tick_to_ms(pos + n['position'] + n['duration']) / 1000.0
        if 55.0 <= ns <= 88.0:
            lyric = n.get('lyric', '')
            tone = n['tone']
            dur = ne - ns
            print(f"Part {pi:2d} note {ni:2d} [{ns:6.2f}s - {ne:6.2f}s] lyric='{lyric}' tone={tone} dur={dur:5.3f}s")
