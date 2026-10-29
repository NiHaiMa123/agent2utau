import yaml

with open('runs/production/zuihouyiye-from-scratch-20261027/compiled_v2/project.ustx', 'r', encoding='utf-8') as f:
    ustx = yaml.safe_load(f)

part0 = ustx['voice_parts'][0]
pitd = next((c for c in part0.get('curves', []) if c.get('abbr').lower() == 'pitd'), None)
if pitd:
    xs = pitd.get('xs', [])
    ys = pitd.get('ys', [])
    print(f'PITD xs len: {len(xs)}, ys len: {len(ys)}')
    for i in range(0, min(50, len(xs)), 2):
        print(f'  i={i} x={xs[i]} y={ys[i]}')
