"""核对 HFA 对齐质量：元音数是否合理、字界是否与能量一致。"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))
ph = h['phrases']

VOWELS = set('a o e i u v ai ei ao ou an en ang eng ong ia ie iao iou ian in iang ing iong '
             'ua uo uai uei uan uen uang ueng van vn er'.split())

print('=== vowel-poor phrases (n_vowels < n_words) ===')
for p in ph:
    if len(p['vowel_spans']) < len(p['lexical']):
        print(f"  {p['pid']} {p['hanzi']}  words={len(p['lexical'])} vowels={len(p['vowel_spans'])}")
        print(f"     phones: {[q['mark'] for q in p['phones']]}")

print('\n=== p01 detail ===')
p1 = next(p for p in ph if p['pid'] == 'p01')
for w in p1['words']:
    print(f"  word {w['mark']:8s} {w['start']:8.3f}-{w['end']:8.3f}")
print('  phones:')
for q in p1['phones']:
    print(f"    {q['mark']:8s} {q['start']:8.3f}-{q['end']:8.3f}  {'VOWEL' if q['mark'] in VOWELS else ''}")

# global check: are word boundaries inside phrase?
print('\n=== word span vs phrase span ===')
bad = 0
for p in ph:
    lex = p['lexical']
    if not lex: continue
    w0, w1 = lex[0]['start'], lex[-1]['end']
    t0, t1 = p['time']
    if w0 < t0 - 0.20 or w1 > t1 + 0.20:
        print(f"  {p['pid']} words {w0:.2f}-{w1:.2f} outside phrase {t0:.2f}-{t1:.2f}"); bad += 1
print(f'  out-of-range: {bad}')

# total covered time vs total phrase time
tot_phrase = sum(p['time'][1]-p['time'][0] for p in ph)
tot_word = sum(sum(w['dur'] for w in p['lexical']) for p in ph)
print(f'\ntotal phrase span {tot_phrase:.1f}s, total lexical word dur {tot_word:.1f}s '
      f'({tot_word/tot_phrase:.1%})')

# any overlapping words?
ov = 0
for p in ph:
    for a, b in zip(p['lexical'], p['lexical'][1:]):
        if a['end'] > b['start'] + 1e-6: ov += 1
print(f'overlapping lexical word pairs: {ov}')

# min word duration
allw = [(p['pid'], w) for p in ph for w in p['lexical']]
short = [(pid, w['hanzi'], round(w['dur'],3)) for pid, w in allw if w['dur'] < 0.10]
print(f'\nwords shorter than 100ms: {len(short)}')
for s in short[:15]: print('   ', s)
