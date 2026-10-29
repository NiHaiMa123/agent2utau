import sys, json, yaml
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from agent2utau.openutau.ustx import load_ustx

for name in ['project.ustx', 'project_voiced.ustx']:
    p = f'runs/production/nianlun-v3-20261029/compiled/{name}'
    try:
        d = load_ustx(p)
        ok = True
        msg = 'loads'
    except Exception as e:
        ok = False
        msg = f'FAILS: {e}'
        d = None
    print(f'{name}: {msg}')
    if not ok:
        # inspect raw yaml around curves
        raw = open(p, encoding='utf-8').read()
        i = raw.find('curves:')
        print(raw[i:i+900])
