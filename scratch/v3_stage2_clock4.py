"""阶段2（v3-CLK4 最终）：自建字时钟。

核心判断（依据 Skill）：
  - HFA 是观测，给出「这个位置有一个什么音节」可信；
    但它在快节奏/段首会崩成 20ms，字长不可信。
  - GAME 是「音符事件」：旋律换音必对应字界候选；一个字的 melisma 会跨多音符。
  - 逐帧 F0 给出真实发声区间与元音核。

自建时钟的算法（可检验、可复现）：
  1) 对每段取 [t0,t1] = 真实有声区间（能量+双F0检测）
  2) 该段的歌词串（权威），字数 N
  3) 用「音符起点 + 能量起音」构造边界候选池 C
  4) DP 选 N-1 个边界，目标函数最小化：
       (a) 每字时长偏离"该字 HFA 相对比例"的平方（用 HFA 作弱先验，不当真值）
       (b) 每字内部有声覆盖率不足的惩罚（保证每字有元音核）
       (c) 边界落在音符起点的奖励
  5) 硬约束：每字 >= 0.10s（不足时降低该段下限并记录）
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
from scipy.signal import find_peaks
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
man = json.load(io.open(NEW/'hfa_blocks'/'manifest.json', encoding='utf-8'))
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')

HOP = 0.01
n = len(v)//int(HOP*sr)
E = np.sqrt((v[:n*int(HOP*sr)].reshape(n, int(HOP*sr))**2).mean(1))
DB = 20*np.log10(np.maximum(E, 1e-9))
T = (np.arange(n)+0.5)*HOP

def midi(hz): return 69+12*np.log2(np.maximum(hz, 1e-6)/440)
ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
# sample to the same 10ms grid T
idx_f = np.clip((T/ft[1]).astype(int), 0, len(ft)-1)
VOICED = fv[idx_f] & rv[idx_f] & (np.abs(midi(ff[idx_f]) - midi(rf[idx_f])) < 0.5)

def cents_of(arr): return 6900.0 + 1200.0*np.log2(np.maximum(arr, 1e-6)/440.0)
C_F = np.where(fv, cents_of(ff), np.nan)
C_R = np.where(rv, cents_of(rf), np.nan)
AGREE = np.isfinite(C_F) & np.isfinite(C_R) & (np.abs(C_F-C_R) <= 100)
C_SRC = np.where(AGREE, (C_F+C_R)/2, np.nan)

def voiced_frac(a, b):
    m = (T >= a) & (T < b)
    return float(VOICED[m].mean()) if m.sum() else 0.0

# ---- boundary candidate pool ----
flux = np.maximum(np.diff(DB, prepend=DB[0]), 0)
pk, _ = find_peaks(flux, height=1.2, distance=3)
onset_e = set(np.round(T[pk], 2))
onset_n = set(np.round([x['start'] for x in g['notes']], 2))

def build_clock(t0, t1, N, hfa_rel, min_syl):
    """DP: N syllables inside [t0,t1]. hfa_rel = relative proportions from HFA (weak prior)."""
    # allowed edges on 10ms grid
    grid = np.arange(t0, t1 + 1e-9, HOP)
    grid = np.round(grid, 2)
    G = len(grid)
    if G < N + 1 or N < 1:
        edges = np.linspace(t0, t1, N+1)
        return [round(float(x), 4) for x in edges], 'fallback_even'
    # cumulative voiced frames for fast coverage
    vo = VOICED[(T >= t0) & (T < t1 + HOP)].astype(np.int32)
    if len(vo) < G: vo = np.r_[vo, np.zeros(G-len(vo), np.int32)]
    vo = vo[:G]
    cvo = np.r_[0, np.cumsum(vo)]
    # cumulative "onset score"
    onc = np.zeros(G)
    for k, tt in enumerate(grid):
        s = 0.0
        if tt in onset_n: s += 1.0
        if tt in onset_e: s += 0.5
        onc[k] += s
    conc = np.r_[0, np.cumsum(onc)]
    cum_rel = np.r_[0, np.cumsum(hfa_rel)] / max(sum(hfa_rel), 1e-9)
    # expected boundary position for syllable k
    def exp_pos(k):
        return t0 + (t1-t0)*cum_rel[k]
    INF = 1e18
    # dp[k][j]: min cost with k boundaries placed, k-th boundary at grid j (k=1..N-1)
    K = N-1
    if K == 0:
        return [round(t0,4), round(t1,4)], 'one_syllable'
    dp = np.full((K, G), INF); prev = np.full((K, G), -1, np.int32)
    # first boundary
    for j in range(G):
        dur = grid[j] - t0
        if dur < min_syl - 1e-9: continue
        cov = (cvo[j]-cvo[0]) / max(j, 1)
        cost = 3.0*(1.0-cov)**2 - onc[j]*0.5
        cost += 2.0*((grid[j]-exp_pos(1))/(t1-t0))**2
        dp[0][j] = cost
    for k in range(1, K):
        for j in range(G):
            # previous boundary i must leave >= min_syl
            jmin = int(np.ceil((min_syl)/HOP))
            lo = max(0, j - int(2.5/HOP))
            hi = j - jmin
            if hi < 0: continue
            lo = max(lo, 0)
            seg = dp[k-1][lo:hi+1]
            if len(seg) == 0 or np.all(seg >= INF): continue
            m = int(np.argmin(seg))
            i = lo + m
            dur = grid[j]-grid[i]
            a = cvo[i+1]; b = cvo[j]
            cov = (b-a)/max(j-i, 1)
            cost = seg[m] + 3.0*(1.0-cov)**2 - onc[j]*0.5
            cost += 2.0*((grid[j]-exp_pos(k+1))/(t1-t0))**2
            dp[k][j] = cost; prev[k][j] = i
    # final: last boundary must leave >= min_syl to t1
    best, bj = INF, -1
    for j in range(G):
        if dp[K-1][j] >= INF: continue
        dur = t1 - grid[j]
        if dur < min_syl - 1e-9: continue
        a = cvo[j+1]; b = cvo[G-1]+0
        cov = (b-a)/max(G-1-j, 1)
        cost = dp[K-1][j] + 3.0*(1.0-cov)**2
        if cost < best: best, bj = cost, j
    if bj < 0:
        edges = np.linspace(t0, t1, N+1)
        return [round(float(x), 4) for x in edges], 'dp_infeasible'
    picks = [bj]
    for k in range(K-1, 0, -1):
        bj = int(prev[k][bj])
        if bj < 0:
            edges = np.linspace(t0, t1, N+1)
            return [round(float(x), 4) for x in edges], 'dp_traceback_fail'
        picks.append(bj)
    picks.reverse()
    edges = [t0] + [float(grid[p]) for p in picks] + [t1]
    return [round(e, 4) for e in edges], 'dp'


# HFA relative proportions (weak prior) per block
hfa_lex = {}
for b in man['blocks']:
    p = NEW/'hfa_blocks_out'/'TextGrid'/f"{b['name']}.TextGrid"
    txt = p.read_text(encoding='utf-8')
    import re as _re
    m = _re.search(r'name = "words"(.*?)(?=\n\titem \[|\Z)', txt, _re.S)
    ivs = _re.findall(r'xmin = ([-\d.eE+]+)\s*\n\s*xmax = ([-\d.eE+]+)\s*\n\s*text = "([^"]*)"', m.group(1))
    lex = [(t, float(b0)-float(a0)) for a0, b0, t in ivs if t not in ('SP','AP','EP','')]
    hfa_lex[b['name']] = lex

out, report = [], []
for b in man['blocks']:
    t0, t1 = b['voiced']
    N = b['n_chars']
    lex = hfa_lex.get(b['name'], [])
    if len(lex) == N:
        rel = [max(d, 0.01) for _, d in lex]
    else:
        rel = [1.0]*N
    min_syl = 0.10 if (t1-t0)/N >= 0.11 else max(0.05, (t1-t0)/N*0.8)
    edges, how = build_clock(t0, t1, N, rel, min_syl)
    words = []
    ci = 0
    for li, line in enumerate(b['lines']):
        for ch in line:
            a, c = edges[ci], edges[ci+1]
            words.append(dict(block=b['name'], line_idx=li, char_idx=ci, hanzi=ch,
                              start=a, end=c, dur=round(c-a, 4),
                              voiced_frac=round(voiced_frac(a, c), 3),
                              method=how))
            ci += 1
    out.extend(words)
    report.append(dict(block=b['name'], N=N, how=how, min_syl=round(min_syl,3),
                       t=[t0, t1], edges=edges))

print(f'blocks {len(report)}, words {len(out)}')
d = np.array([w['dur'] for w in out])
vf = np.array([w['voiced_frac'] for w in out])
print(f'dur: min {d.min():.3f} p5 {np.percentile(d,5):.3f} median {np.median(d):.3f} max {d.max():.3f}')
print(f'words < 0.10s: {(d<0.10).sum()}  < 0.08s: {(d<0.08).sum()}')
print(f'voiced_frac: median {np.median(vf):.2f}, <0.3: {(vf<0.3).sum()}')
print('\nworst voiced coverage:')
for w in sorted(out, key=lambda x: x['voiced_frac'])[:12]:
    print(f"   {w['block']} {w['hanzi']} {w['start']:.2f}-{w['end']:.2f} ({w['dur']:.3f}) vf={w['voiced_frac']}")
print('\nmethod usage:')
from collections import Counter
print(dict(Counter(r['how'] for r in report)))

(NEW/'words_v3.json').write_text(json.dumps(dict(
    schema_version=1,
    method='HFA syllable identity (count) + DP clock over energy-onsets/GAME-onsets with voiced-coverage constraint; HFA durations only as weak relative prior',
    blocks=report, words=out), ensure_ascii=False, indent=1), encoding='utf-8')
print('\nwrote words_v3.json')
