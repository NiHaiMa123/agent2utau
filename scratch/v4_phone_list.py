import sys, json, io
from collections import Counter
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
ph = json.load(io.open(NEW/'compiled'/'phones.json', encoding='utf-8'))
rows=[]
for part in ph['parts']:
    for phrase in part['phrases']:
        for q in phrase['phones']:
            rows.append(dict(mark=q['phoneme'], dur=(q['end_ms']-q['start_ms'])/1000,
                             start=q['start_ms']/1000))
c=Counter(r['mark'] for r in rows)
print(f'distinct phonemes: {len(c)}')
print(', '.join(f'{k}({v})' for k,v in c.most_common()))
