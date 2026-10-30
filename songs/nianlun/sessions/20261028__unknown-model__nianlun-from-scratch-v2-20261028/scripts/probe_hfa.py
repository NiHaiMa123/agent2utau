import sys, json, io, numpy as np
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'

h = json.load(io.open(f'{RUN}/hfa/hfa_summary.json', encoding='utf-8'))
print('hfa keys:', list(h) if isinstance(h, dict) else len(h))
s = json.dumps(h, ensure_ascii=False)
print(s[:1500])
