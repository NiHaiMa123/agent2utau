"""核查 99 个"无元音核"字：是解析问题还是对齐真的把元音吞了。"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))

VOWELS = set('a o e i u v ai ei ao ao ou an en ang eng ong ia ie iao iou ian in iang ing iong '
             'ua uo uai uei uan uen uang ueng van vn er'.split())

ptr = [p for p in h['phrases'] if p['pid'] in ('p01', 'p24')]
for p in ptr:
    print(f"=== {p['pid']} {p['hanzi']} ===")
    for w in p['lexical']:
        vs = [q['mark'] for q in w['phones']]
        print(f"  {w['hanzi']} {w['start']:7.3f}-{w['end']:7.3f} ({w['dur']:.3f}) phones={vs} vowel={w.get('vowel')}")

# classification of the 99
from collections import Counter
cnt = Counter()
examples = {}
for p in h['phrases']:
    for w in p['lexical']:
        if w.get('vowel') is None:
            marks = tuple(q['mark'] for q in w['phones'])
            if not marks:
                k = 'NO_PHONES'
            else:
                k = 'PHONES_BUT_NO_VOWEL'
            cnt[k] += 1
            examples.setdefault(k, []).append((p['pid'], w['hanzi'], round(w['dur'],3), marks))
print('\nclassification:', dict(cnt))
for k, v in examples.items():
    print(f'\n{k} examples:')
    for e in v[:12]: print('   ', e)
