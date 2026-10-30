"""诊断 cover=0 bug：检查 F0 时间网格与绝对时间的对应。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
f0 = np.load(NEW/'inputs/fcpe.npz')
print('fcpe keys:', f0.files)
t = f0['times']; v = f0['voiced']; hz = f0['f0_hz']
print(f'times: {t[0]} .. {t[-1]}  n={len(t)} step={t[1]-t[0]}')
print(f'voiced frac {v.mean():.3f}')
# at 18.73-18.99
m = (t >= 18.73) & (t < 18.99)
print(f'frames in [18.73,18.99): {m.sum()}, voiced {v[m].sum()}')
print('sample times', t[m][:5])

# check the actual voiced fraction in a known singing region
m2 = (t >= 19.0) & (t < 20.0)
print(f'frames in [19,20): {m2.sum()}, voiced {v[m2].mean():.3f}')

# is f0_hz zero where voiced is False?
print('f0>0 count:', (hz > 0).sum(), 'voiced count:', v.sum())
print('any voiced but f0==0:', ((v) & (hz == 0)).sum())
