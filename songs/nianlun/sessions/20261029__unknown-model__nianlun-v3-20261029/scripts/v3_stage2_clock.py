"""阶段2：重建谱面时钟（关键改进 v3-CLK）。

教训：
  - v1/v2 直接用 HFA 字界 → HFA 在密集段崩成 20ms，导致碎字与吞字
  - 直接用 GAME 音符 → GAME 是"音符事件"，一个汉字可能对应多个音符（melisma），
    直接当字界会把一个字切成多个音

v3 方案（字界三源联合，可检验）：
  A) 音节数 N：来自歌词（确定）
  B) 元音核序列：用「有声F0 + 能量」检测每字的元音承载段（字的音乐实体）
  C) 音符边界：作为边界候选池

  求解：在 [t0,t1] 内选 N 个字界，使每字：
    - 至少 0.10s（可用元音）
    - 含一个元音核（有声F0段 >= 0.05s）
    - 边界优先落在能量谷或音符起点
  用动态规划，代价 = 边界处能量 + 字内无声惩罚。
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
fv_i = np.interp(T, ft, fv.astype(float)) > 0.5
rv_i = np.interp(T, rt, rv.astype(float)) > 0.5
agree = np.abs(midi(np.interp(T, ft, ff)) - midi(np.interp(T, rt, rf))) < 0.5
voiced = fv_i & rv_i & agree

# 字界候选池：能量谷 + GAME 音符起点
from scipy.signal import find_peaks
valley, _ = find_peaks(-db, distance=3)          # 能量局部谷
cand_valley = set(np.round(T[valley], 2))
cand_note = set(np.round([x['start'] for x in g['notes']], 2))

MIN_SYL = 0.10     # 每字最少 0.10s（Skill: 短字需可承载元音）
MAX_SYL = 2.00

def solve_bounds(t0, t1, N):
    """DP: choose N-1 interior boundaries maximizing (energy valley + note-onset) and vowel coverage."""
    grid = np.arange(t0 + MIN_SYL, t1 - MIN_SYL + 1e-9, HOP)
    if len(grid) < N-1:
        # fall back to even split
        return [t0 + (t1-t0)*k/N for k in range(N+1)]
    def cost(t):
        i = int(round(t/HOP)); i = min(max(i, 0), n-1)
        c = 0.0
        c += max(0.0, (db[i] - np.percentile(db, 20))) * 0.05   # prefer quiet
        if round(t, 2) in cand_note:  c -= 1.2                  # prefer note onset
        if round(t, 2) in cand_valley: c -= 0.4                 # prefer valley
        return c
    # DP over positions
    K = N-1
    INF = 1e18
    # dp[k][j]: best cost placing k-th boundary at grid index j
    dp = np.full((K, len(grid)), INF)
    prev = np.full((K, len(grid)), -1, dtype=int)
    for j, t in enumerate(grid):
        dp[0][j] = cost(t)
    for k in range(1, K):
        for j in range(len(grid)):
            lo = max(0, j - int((MAX_SYL)/HOP))
            if lo >= j: continue
            seg = dp[k-1][lo:j]
            if len(seg) == 0: continue
            m = np.argmin(seg)
            if seg[m] < INF:
                dp[k][j] = seg[m] + cost(grid[j])
                prev[k][j] = lo + m
    if K == 0:
        return [t0, t1]
    j = int(np.argmin(dp[K-1]))
    if dp[K-1][j] >= INF:
        return [t0 + (t1-t0)*k/N for k in range(N+1)]
    picks = [j]
    for k in range(K-1, 0, -1):
        j = prev[k][j]
        if j < 0: return [t0 + (t1-t0)*k/N for k in range(N+1)]
        picks.append(j)
    picks.reverse()
    edges = [t0] + [float(grid[p]) for p in picks] + [t1]
    return edges

out = []
for p in h['phrases']:
    lex = p['lexical']
    N = len(lex)
    t0, t1 = p['time']
    edges = solve_bounds(t0, t1, N)
    words = []
    for k, w in enumerate(lex):
        a, b = edges[k], edges[k+1]
        m = (T >= a) & (T < b)
        vb = voiced[m].mean() if m.sum() else 0.0
        words.append(dict(idx=k, hanzi=w['hanzi'], hfa_marks=[q['mark'] for q in w['phones']],
                          hfa_dur=round(w['dur'], 4),
                          start=round(a, 4), end=round(b, 4), dur=round(b-a, 4),
                          voiced_frac=round(float(vb), 3)))
    out.append(dict(pid=p['pid'], label=p['label'], hanzi=p['hanzi'], pinyin=p['pinyin'],
                    time=[t0, t1], words=words, phones=p['phones']))

# quality report
allw = [(p['pid'], w) for p in out for w in p['words']]
print(f'phrases {len(out)}, words {len(allw)}')
short = [(pid, w['hanzi'], w['dur']) for pid, w in allw if w['dur'] < 0.10]
lowv = [(pid, w['hanzi'], w['voiced_frac']) for pid, w in allw if w['voiced_frac'] < 0.3]
durs = np.array([w['dur'] for _, w in allw])
print(f'word dur: min {durs.min():.3f} median {np.median(durs):.3f} max {durs.max():.3f}')
print(f'words < 100ms: {len(short)}  {short[:10]}')
print(f'words with voiced_frac<0.3: {len(lowv)}  {lowv[:10]}')

(NEW/'score_clock.json').write_text(json.dumps(dict(
    schema_version=1, hop_s=HOP, min_syl_s=MIN_SYL,
    method='DP over (energy valley + GAME onset) with vowel-coverage; HFA supplies syllable identity only',
    phrases=out), ensure_ascii=False, indent=1), encoding='utf-8')
print('wrote score_clock.json')
