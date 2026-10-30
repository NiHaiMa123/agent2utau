"""从实际 HFA 输出统计所有音素符号，建立正确的元音表。"""
import sys, json, io
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))

c = Counter()
for p in h['phrases']:
    for q in p['phones']:
        c[q['mark']] += 1
print('all phone symbols (%d distinct):' % len(c))
for k, v in c.most_common():
    print(f'  {k:8s} {v:4d}')

# position analysis: which symbols are the LAST phone of a syllable (nucleus candidate)?
last = Counter(); first = Counter()
for p in h['phrases']:
    for w in p['lexical']:
        ps = [q['mark'] for q in w['phones']]
        if ps:
            last[ps[-1]] += 1
            first[ps[0]] += 1
print('\nsyllable-final symbols (nucleus/final):')
for k, v in last.most_common():
    print(f'  {k:8s} {v:4d}')
print('\nsyllable-initial symbols (onset):')
for k, v in first.most_common():
    print(f'  {k:8s} {v:4d}')
