import yaml

d4 = yaml.safe_load(open('runs/production/zuihouyiye-from-scratch-20261027/compiled_v4/project.ustx', encoding='utf-8'))
d5 = yaml.safe_load(open('runs/production/zuihouyiye-from-scratch-20261027/compiled_v5/project.ustx', encoding='utf-8'))

for ver, d in [('v4', d4), ('v5', d5)]:
    p13 = d['voice_parts'][13] # Part 13: '如果这是最后的一夜' in Chorus 1
    p29 = d['voice_parts'][29] # Part 29: '如果这是最后的一夜' in Chorus 2 (3:18)
    for p, name in [(p13, 'Part 13 (Chorus 1)'), (p29, 'Part 29 (Chorus 2, 3:18)')]:
        print(f"=== {ver} {name} curves: ===")
        for c in p.get('curves', []):
            if c['abbr'] in ('voic', 'tenc', 'brec', 'dyn'):
                ys = c['ys']
                print(f"  {c['abbr']}: {len(c['xs'])} pts, min={min(ys)}, max={max(ys)}, mean={sum(ys)/len(ys):.1f}")
