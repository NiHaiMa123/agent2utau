"""核查：元音核过短是因为切片切断了字，还是 HFA 本身在密集区崩了。

方法：把切片窗口放大（前后各 0.6s）重跑几个失败句，看是否改善。
同时检查：这些短字在绝对时间上是否相邻（密集区）。
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)

# add 've' and rebuild
NUCLEI = set("""a o e i u v E i0 ir er ai ei ao ou an en ang ang eng ong
ia ie iao iu ian in iang ing iong ua uo uai ui uan un uang ueng van vn ve En""".split())

short = []
for p in h['phrases']:
    for w in p['lexical']:
        nuc = None
        for q in reversed(w['phones']):
            if q['mark'] in NUCLEI:
                nuc = q; break
        w['nucleus'] = nuc
        if nuc is None or nuc['dur'] < 0.04:
            short.append((p['pid'], w['hanzi'], w['start'], w['dur'], nuc['dur'] if nuc else 0))

print(f'unusable nuclei: {len(short)}')
print('\ntimeline of unusable-nucleus words:')
for s in short:
    print(f"  {s[0]} {s[1]} @{s[2]:7.3f}s  word={s[3]:.3f}s  nuc={s[4]:.3f}s")

# cluster check: are they adjacent?
ts = sorted(s[2] for s in short)
gaps = np.diff(ts)
print(f'\nmax gap between them {gaps.max():.2f}s; clusters (gap<0.5s): {sum(g<0.5 for g in gaps)}/{len(gaps)}')

# check energy at those points
win = int(0.02*sr); n = len(v)//win
e = np.sqrt((v[:n*win].reshape(n, win)**2).mean(1))
db = 20*np.log10(np.maximum(e, 1e-9)); t = (np.arange(n)+0.5)*0.02
print('\nenergy at those words vs local median:')
for s in short[:20]:
    m = (t >= s[2]) & (t < s[2]+max(s[3], 0.02))
    loc = (t >= s[2]-0.5) & (t < s[2]+0.5)
    if m.sum():
        print(f"  {s[0]} {s[1]} @{s[2]:7.3f} word_db={db[m].mean():6.1f} local_med={np.median(db[loc]):6.1f}")
