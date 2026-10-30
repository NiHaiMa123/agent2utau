"""阶段2（修正 v3-CLK2）：用「有声音段」而非边界 DP 来定字界。

物理事实：每个汉字的音乐实体 = 一段连续有声（元音核）。
所以正确的做法是：
  1) 在句子 [t0,t1] 内切出"有声音段"（连续 voiced，允许短空隙）
  2) 有声音段数应与字数接近（melisma 会把一段拉长，不会增加段数太多）
  3) 若段数 == 字数 → 直接一对一
     若段数 < 字数  → 在最长段内按能量谷再切
     若段数 > 字数  → 合并最相近的段（辅音分离造成的假段）
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')

HOP = 0.01
n = len(v)//int(HOP*sr)
e = np.sqrt((v[:n*int(HOP*sr)].reshape(n, int(HOP*sr))**2).mean(1))
db = 20*np.log10(np.maximum(e, 1e-9))
T = (np.arange(n)+0.5)*HOP

def midi(hz): return 69+12*np.log2(np.maximum(hz, 1e-6)/440)
ft, ff, fv = f0['times'], f0['f0_hz'], f0['voiced']
rt, rf, rv = f0r['times'], f0r['f0_hz'], f0r['voiced']
voiced = (np.interp(T, ft, fv.astype(float)) > 0.5) & \
         (np.interp(T, rt, rv.astype(float)) > 0.5) & \
         (np.abs(midi(np.interp(T, ft, ff)) - midi(np.interp(T, rt, rf))) < 0.5)

MIN_NUC = 0.06     # 元音核最短
MERGE_GAP = 0.05   # 小于这个空隙的有声段合并（辅音造成的假断）

def voiced_runs(a, b, voiced_mask, min_len=MIN_NUC, merge_gap=MERGE_GAP):
    idx = np.where((T >= a) & (T < b))[0]
    if len(idx) == 0: return []
    runs, s = [], None
    for i in idx:
        if voiced_mask[i] and s is None: s = i
        elif not voiced_mask[i] and s is not None:
            runs.append((T[s], T[i])); s = None
    if s is not None: runs.append((T[s], T[idx[-1]]+HOP))
    merged = []
    for r in runs:
        if merged and r[0]-merged[-1][1] < merge_gap: merged[-1] = (merged[-1][0], r[1])
        else: merged.append(list(r))
    return [(a0, b0) for a0, b0 in merged if b0-a0 >= min_len]

out, diag = [], []
for p in h['phrases']:
    lex = p['lexical']; N = len(lex)
    t0, t1 = p['time']
    runs = voiced_runs(t0, t1, voiced)
    diag.append(dict(pid=p['pid'], hanzi=p['hanzi'], N=N, n_runs=len(runs),
                     runs=[[round(a,3), round(b,3)] for a, b in runs]))
    out.append(dict(pid=p['pid'], n=N, t=[t0, t1], runs=runs))

print('phrase | chars | voiced runs | match')
ok = 0
for d in diag:
    m = 'EXACT' if d['n_runs'] == d['N'] else ('FEWER' if d['n_runs'] < d['N'] else 'MORE')
    if d['n_runs'] == d['N']: ok += 1
    print(f"  {d['pid']} {d['hanzi']:12s} N={d['N']:2d} runs={d['n_runs']:2d} {m}")
print(f'\nexact match: {ok}/{len(diag)}')

from collections import Counter
print('distribution of (runs - N):', dict(Counter(d['n_runs']-d['N'] for d in diag)))
(NEW/'voiced_runs.json').write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding='utf-8')
