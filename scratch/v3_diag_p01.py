import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))
p = next(p for p in h['phrases'] if p['pid']=='p01')
print('time window', p['time'])
print('lexical (HFA order):')
for w in p['lexical']:
    print(f"  {w.get('hanzi')} start={w['start']} end={w['end']} dur={w['dur']}")
print('\nraw words tier:')
for w in p['words']:
    print(f"  {w['mark']:8s} {w['start']:8.3f}-{w['end']:8.3f}")
