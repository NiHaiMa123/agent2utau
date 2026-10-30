"""检查音高是否被量化到半音格：统计 pitch_cents 对 100 的余数分布。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
w = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
pc = np.array([x['pitch_cents'] for p in w['phrases'] for x in p['words'] if x['pitch_cents'] is not None])
print(f'n={len(pc)}')
res = pc % 100
# if quantized to semitone, res would be ~0 (mod 100)
print(f'cents mod 100: mean {res.mean():.1f}  std {res.std():.1f}  '
      f'frac |res-50|>40: {(np.abs(res-50)>40).mean():.1%}')
print('histogram of (pc mod 100) in bins of 10:')
h, _ = np.histogram(res, bins=10, range=(0,100))
for i, c in enumerate(h):
    print(f'  {i*10:3d}-{i*10+10:3d}: {c:3d} {"#"*c}')

# also check: are many values EXACTLY on integers?
print(f'\nexact integers (pc == round(pc)): {(pc == np.round(pc)).mean():.1%}')
print(f'exact multiples of 10: {(pc % 10 == 0).mean():.1%}')

# inspect the 19 big jumps in context
print('\nbig-jump contexts:')
for p in w['phrases']:
    ws = [x for x in p['words'] if x['pitch_cents'] is not None]
    for a, b in zip(ws, ws[1:]):
        if abs(b['pitch_cents']-a['pitch_cents']) > 700:
            print(f"  {p['pid']}: {a['hanzi']}({a['start']:.2f}-{a['end']:.2f}, cov={a['voiced_cover']}) "
                  f"{a['pitch_cents']:.0f} -> {b['hanzi']}({b['start']:.2f}-{b['end']:.2f}, cov={b['voiced_cover']}) "
                  f"{b['pitch_cents']:.0f}")
