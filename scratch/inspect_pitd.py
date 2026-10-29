import yaml

with open('runs/production/zuihouyiye-from-scratch-20261027/compiled_v2/project.ustx', 'r', encoding='utf-8') as f:
    ustx = yaml.safe_load(f)

voice_parts = [p for p in ustx.get('voice_parts', []) if p.get('track_no') == 0]
print('Voice parts:', len(voice_parts))
part0 = voice_parts[0]
notes = part0.get('notes', [])
print('Total notes:', len(notes))
curves = part0.get('curves', [])
for c in curves:
    print('Curve:', c.get('abbr'), 'points:', len(c.get('xs', [])))

pitd = next((c for c in curves if c.get('abbr') == 'PITD'), None)
if pitd:
    xs = pitd.get('xs', [])
    ys = pitd.get('ys', [])
    print(f'PITD xs range: {min(xs)} to {max(xs)}, ys range: {min(ys)} to {max(ys)}')
    # Sample some values
    for x, y in zip(xs[:30], ys[:30]):
        print(f'  x={x}, y={y}')
else:
    print('No PITD curve found!')

for i in range(min(10, len(notes))):
    n = notes[i]
    pitch = n.get('pitch', {})
    print('Note', i, 'lyric:', n.get('lyric'), 'tone:', n.get('tone'), 'pos:', n.get('position'), 'dur:', n.get('duration'), 'pitch:', pitch)
