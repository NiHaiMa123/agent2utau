import sys, json
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from agent2utau.openutau.ustx import load_ustx

d = load_ustx('runs/production/nianlun-v3-20261029/compiled/project.ustx')
p = d['voice_parts'][0]
print('part0 keys:', list(p))
print('part0 curves:')
for c in p.get('curves', []):
    print('  abbr=', c['abbr'], 'n=', len(c['xs']), 'xs[:4]=', c['xs'][:4], 'ys[:4]=', c['ys'][:4])
print('\nexpressions:')
for k, e in d['expressions'].items():
    print(f"  {k}: min={e.get('min')} max={e.get('max')} default={e.get('default_value')} type={e.get('type')}")
