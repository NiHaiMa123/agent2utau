import yaml

d5 = yaml.safe_load(open('runs/production/zuihouyiye-from-scratch-20261027/compiled_v5/project.ustx', encoding='utf-8'))
p29 = d5['voice_parts'][29]
bpm = d5['tempos'][0]['bpm']
beat_ticks = 480
def t2s(tick):
    return tick / beat_ticks * (60.0 / bpm)

st = t2s(p29['position'])
print(f"Part 29 start: {st:.2f}s (Position: {p29['position']})")

notes = p29['notes']
for n in notes:
    dur = t2s(n['duration'])
    pos = t2s(n['position'])
    abs_time = st + pos
    m_s = f"{int(abs_time//60)}:{abs_time%60:04.1f}"
    print(f"  [{m_s}] lyric={n['lyric']:<5} tone={n['tone']} pos={n['position']} dur={n['duration']}")

curves = {c['abbr']: (c['xs'], c['ys']) for c in p29.get('curves', [])}
print("\nCurves in Part 29 around notes:")
for abbr in ('voic', 'tenc', 'brec'):
    if abbr in curves:
        xs, ys = curves[abbr]
        print(f"Curve {abbr}:")
        for x, y in zip(xs, ys):
            abs_time = st + t2s(x)
            m_s = f"{int(abs_time//60)}:{abs_time%60:04.1f}"
            print(f"    [{m_s}] tick={x:5d}: {y:4d}")
