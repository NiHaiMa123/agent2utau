"""真实乐句结构探测：用分离人声能量 + GAME 音符事件，找出实际演唱区间，
不依赖 ASR 分段（ASR 漏了第一段主歌）。"""
import sys, json, io, numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

v, sr = sf.read(str(NEW / 'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
print(f'vocals {len(v)/sr:.2f}s  sr={sr}')

# 20ms RMS envelope
win = int(0.02*sr); n = len(v)//win
e = np.sqrt((v[:n*win].reshape(n, win)**2).mean(1))
db = 20*np.log10(np.maximum(e, 1e-9))
t = (np.arange(n)+0.5)*0.02

# adaptive threshold: speech/silence split via histogram gap
print(f'db range: {db.min():.1f} .. {db.max():.1f}, median {np.median(db):.1f}')
# voiced = above (median of top quartile) - 25dB, and at least -45
thr = max(np.percentile(db, 95) - 28.0, -48.0)
print(f'threshold {thr:.1f} dB')
act = db > thr

# smooth: close gaps < 120ms (consonants/breaths inside a phrase)
gap_max = int(0.12/0.02)
runs = []
i = 0
while i < n:
    if act[i]:
        j = i
        while j < n and act[j]: j += 1
        runs.append([i, j]); i = j
    else:
        i += 1
merged = []
for r in runs:
    if merged and (r[0]-merged[-1][1]) <= gap_max:
        merged[-1][1] = r[1]
    else:
        merged.append(r)
# drop runs shorter than 0.25s
merged = [r for r in merged if (r[1]-r[0])*0.02 >= 0.25]
print(f'\nvoiced runs (>=0.25s after merge): {len(merged)}')
segs = [(t[a], t[b-1]+0.02) for a, b in merged]
for k, (a, b) in enumerate(segs):
    print(f'  seg{k:2d} {a:7.2f} - {b:7.2f}   {b-a:6.2f}s')

# GAME notes density per seg
g = json.load(io.open(NEW / 'inputs/game.json', encoding='utf-8'))
notes = g['notes']
print('\nGAME notes per seg:')
for k, (a, b) in enumerate(segs):
    ns = [x for x in notes if a <= x['start'] < b]
    vn = [x for x in ns if x['voiced']]
    print(f'  seg{k:2d} {a:7.2f}-{b:7.2f}  notes={len(ns):3d} (voiced {len(vn):3d})  {'#'*len(ns)}')

json.dump(dict(threshold_db=float(thr), segments=[[round(a,3), round(b,3)] for a,b in segs]),
          io.open(NEW/'vocal_segments.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\nwrote {NEW}/vocal_segments.json')
