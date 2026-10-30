"""独立字边界方案：用「能量起音 + 韵母核检测」重建字界，HFA 只提供音素身份。

思路（符合 Skill：HFA 是观测不是真值）：
  1) 用音节数 N 与可用发声区间 [a,b]
  2) 检测元音核（F0 有声 + 能量峰）作为字锚点
  3) 用 GAME 音符起点作为强候选边界（旋律换音必是字界候选）
  4) 联合求解：边界必须在合理范围，且每字有可承载元音
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
from scipy.signal import find_peaks

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')

# energy envelope 10ms
hop = int(0.01*sr); n = len(v)//hop
e = np.sqrt((v[:n*hop].reshape(n, hop)**2).mean(1))
db = 20*np.log10(np.maximum(e, 1e-9))
t = (np.arange(n)+0.5)*0.01

# voiced F0 (dual agreement)
def midi(hz): return 69+12*np.log2(np.maximum(hz,1e-6)/440)
ft, ff, fv = f0['times'], f0['f0_hz'], f0['voiced']
rt, rf, rv = f0r['times'], f0r['f0_hz'], f0r['voiced']
fmini = midi(np.interp(t, ft, ff)); rmini = midi(np.interp(t, rt, rf))
fv_i = np.interp(t, ft, fv.astype(float)) > 0.5
rv_i = np.interp(t, rt, rv.astype(float)) > 0.5
voiced = fv_i & rv_i & (np.abs(fmini-rmini) < 0.5)

# onsets from energy derivative (spectral flux proxy)
d = np.diff(db, prepend=db[0])
flux = np.maximum(d, 0)
peaks, props = find_peaks(flux, height=1.5, distance=4)   # min 40ms apart
onset_t = t[peaks]

print(f'energy onsets detected: {len(onset_t)}')
print(f'GAME note onsets: {len(g["notes"])}')

# per phrase: propose boundaries
results = []
for p in h['phrases']:
    hz = p['hanzi']; N = len(hz)
    t0, t1 = p['time']
    # candidate onsets in phrase
    cand = sorted(set(
        [round(x, 3) for x in onset_t if t0 < x < t1] +
        [round(x['start'], 3) for x in g['notes'] if t0 < x['start'] < t1]
    ))
    # merge candidates closer than 60ms
    merged = []
    for c in cand:
        if not merged or c - merged[-1] >= 0.06:
            merged.append(c)
    results.append(dict(pid=p['pid'], hanzi=hz, t0=t0, t1=t1, n=N,
                        n_cand=len(merged), cand=merged[:40],
                        hfa_durs=[round(w['dur'], 3) for w in p['lexical']]))

print(f'\nphrase | chars | candidates | verdict')
for r in results:
    ok = 'OK' if r['n_cand'] >= r['n'] else 'TOO_FEW_CANDIDATES'
    hfa_min = min(r['hfa_durs']) if r['hfa_durs'] else 0
    print(f"  {r['pid']} {r['hanzi']:12s} n={r['n']:2d} cand={r['n_cand']:2d} hfamin={hfa_min:.3f}  {ok}")
