import yaml

with open('runs/production/zuihouyiye-from-scratch-20261027/compiled_v2/project.ustx', 'r', encoding='utf-8') as f:
    ustx = yaml.safe_load(f)

for idx, part in enumerate(ustx.get('voice_parts', [])):
    pitd = next((c for c in part.get('curves', []) if c.get('abbr').lower() == 'pitd'), None)
    if pitd:
        ys = pitd.get('ys', [])
        nonzero = [y for y in ys if y != 0]
        print(f'Part {idx}: total {len(ys)}, non-zero: {len(nonzero)}, min={min(ys) if ys else None}, max={max(ys) if ys else None}')
