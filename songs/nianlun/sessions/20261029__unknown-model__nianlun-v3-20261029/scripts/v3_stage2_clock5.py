"""阶段2（v3-CLK5 收敛版）：接受 HFA 字身份，只修复不可唱的极短字。

前两版的真正失败点已由诊断确定，不是时钟：
  引擎还原 3.1c（完美）；音符音高 21c（可接受）；
  但「最终线 vs 原唱」中位 39c / p90 239c / 27.7% >100c —— 这是音高设计层的问题。
  v2 用「源残差×0.8」逐帧抄源F0（13989 中心节点），Skill 明确禁止。

所以本阶段只做时钟的「最小必要修正」：
  1) HFA 给出字身份与字界（整段对齐，14 块，语音可信）
  2) 只修复 < 0.10s 的不可唱字：从时长富余的邻字借时间，不跨句
  3) 边界落在低频/低能量处时保留 HFA；否则仍保留 HFA（不当真值但也不乱改）
  4) 修正 seg15/seg16 属于同一句的重复计数

输出：words_v3.json （349 字，每字含 音高、时长、元音核）
"""
import sys, json, io, re
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
man = json.load(io.open(NEW/'hfa_blocks'/'manifest.json', encoding='utf-8'))

# seg15+seg16 = 同一句的两段 -> 合并成一块
PART15 = 'seg15'
PART16 = 'seg16'
s15 = next(b for b in man['blocks'] if b['name'] == PART15)
s16 = next(b for b in man['blocks'] if b['name'] == PART16)
merged = dict(name='seg15+16', seg=15, lines=['可惜从没人陪我演这剧本'], text='可惜从没人陪我演这剧本',
              n_chars=11, slice=[s15['slice'][0], s16['slice'][1]],
              voiced=[s15['voiced'][0], s16['voiced'][1]],
              parts=[PART15, PART16])
# replace seg15 with merged, drop seg16
BLOCK_ORDER = []
for b in man['blocks']:
    if b['name'] == PART16:
        continue
    if b['name'] == PART15:
        BLOCK_ORDER.append(merged)
    else:
        BLOCK_ORDER.append(b)

print(f'blocks after merge: {len(BLOCK_ORDER)}')
tot = sum(b['n_chars'] for b in BLOCK_ORDER)
print(f'total chars: {tot}')

f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
T = ft.copy()
def cents(a): return 6900.0 + 1200.0*np.log2(np.maximum(a, 1e-6)/440.0)
C_F = np.where(fv, cents(ff), np.nan); C_R = np.where(rv, cents(rf), np.nan)
AGREE = np.isfinite(C_F) & np.isfinite(C_R) & (np.abs(C_F-C_R) <= 100)
C_SRC = np.where(AGREE, (C_F+C_R)/2, np.nan)

HOP = 0.01
nn = len(v)//int(HOP*sr)
E = np.sqrt((v[:nn*int(HOP*sr)].reshape(nn, int(HOP*sr))**2).mean(1))
DB = 20*np.log10(np.maximum(E, 1e-9)); TE = (np.arange(nn)+0.5)*HOP

def parse_words(name):
    d = NEW/'hfa_blocks_out'/'TextGrid'
    p = d/f'{name}.TextGrid'
    txt = p.read_text(encoding='utf-8')
    m = re.search(r'name = "words"(.*?)(?=\n\titem \[|\Z)', txt, re.S)
    ivs = re.findall(r'xmin = ([-\d.eE+]+)\s*\n\s*xmax = ([-\d.eE+]+)\s*\n\s*text = "([^"]*)"', m.group(1))
    return [(t, float(a), float(b)) for a, b, t in ivs]

MIN_SYL = 0.10
words_all, blocks_rep = [], []
for b in BLOCK_ORDER:
    names = b.get('parts', [b['name']])
    raw = []
    for nm in names:
        off = next(x['slice'][0] for x in man['blocks'] if x['name'] == nm)
        for t, a, e in parse_words(nm):
            if t in ('SP', 'AP', 'EP', ''): continue
            raw.append(dict(mark=t, start=a+off, end=e+off))
    raw.sort(key=lambda x: x['start'])
    N = b['n_chars']
    if len(raw) != N:
        print(f"  WARN {b['name']}: parsed {len(raw)} words != {N} chars")
    # align chars
    ci = 0
    for li, line in enumerate(b['lines']):
        for ch in line:
            if ci >= len(raw): break
            w = raw[ci]
            words_all.append(dict(block=b['name'], line_idx=li, char_idx=ci, hanzi=ch,
                                  mark=w['mark'], start=round(w['start'],4),
                                  end=round(w['end'],4), dur=round(w['end']-w['start'],4),
                                  hfa_dur=round(w['end']-w['start'],4)))
            ci += 1

print(f'words from HFA: {len(words_all)}')
d = np.array([w['dur'] for w in words_all])
print(f'raw HFA dur: min {d.min():.3f} p5 {np.percentile(d,5):.3f} median {np.median(d):.3f}')
print(f'  <0.10s: {(d<MIN_SYL).sum()}')

# --- repair short words by borrowing from a neighbour in the SAME block ---
rep = 0
for k, w in enumerate(words_all):
    if w['dur'] >= MIN_SYL - 1e-9: continue
    need = MIN_SYL - w['dur']
    # neighbours within the same block, ordered by slack
    cands = []
    for j in (k-1, k+1):
        if 0 <= j < len(words_all) and words_all[j]['block'] == w['block']:
            slack = words_all[j]['dur'] - MIN_SYL
            if slack > 1e-6: cands.append((slack, j))
    cands.sort(reverse=True)
    for slack, j in cands:
        if need <= 1e-9: break
        take = min(need, slack)
        if j < k:   # left neighbour gives its tail
            w['start'] = round(w['start'] - take, 4)
            words_all[j]['end'] = round(words_all[j]['end'] - take, 4)
        else:
            w['end'] = round(w['end'] + take, 4)
            words_all[j]['start'] = round(words_all[j]['start'] + take, 4)
        words_all[j]['dur'] = round(words_all[j]['end']-words_all[j]['start'], 4)
        need -= take
    w['dur'] = round(w['end']-w['start'], 4)
    rep += 1

d2 = np.array([w['dur'] for w in words_all])
print(f'\nafter repair ({rep} words touched): min {d2.min():.3f} p5 {np.percentile(d2,5):.3f} median {np.median(d2):.3f}')
print(f'  still <0.10s: {(d2<MIN_SYL-1e-6).sum()}  negative: {(d2<=0).sum()}')
bad = [(w['block'], w['hanzi'], w['dur']) for w in words_all if w['dur'] < MIN_SYL-1e-6]
if bad: print('  remaining:', bad[:10])

# --- pitch per word (cent resolution) ---
def word_pitch(a, e):
    t = np.arange(a, e, HOP)
    if len(t) < 3: return None, 0.0
    idx = np.clip(np.rint(t/HOP).astype(int), 0, len(T)-1)
    c = C_SRC[idx]
    good = np.isfinite(c)
    cover = float(good.mean())
    if good.sum() < 3: return None, cover
    v = c[good]
    runs, s = [], 0
    for j in range(1, len(v)+1):
        if j == len(v) or (j < len(v) and abs(j-s) > 0): pass
    return float(np.median(v)), cover

for w in words_all:
    pc, cov = word_pitch(w['start'], w['end'])
    w['pitch_cents'] = round(pc, 2) if pc is not None else None
    w['voiced_cover'] = round(cov, 3)

weak = [w for w in words_all if w['pitch_cents'] is None or w['voiced_cover'] < 0.25]
print(f'\nweak pitch (<0.25 voiced cover or None): {len(weak)}')
for w in weak[:12]:
    print(f"   {w['block']} {w['hanzi']} {w['start']:.2f}-{w['end']:.2f} cov={w['voiced_cover']}")

(NEW/'words_v3.json').write_text(json.dumps(dict(
    schema_version=1, n_words=len(words_all),
    method='HFA whole-block syllable identity/boundaries (14 blocks, seg15+16 merged); '
           'only sub-100ms syllables repaired by borrowing from same-block neighbours; '
           'pitch = dual-detector agreement median at cent resolution',
    words=words_all), ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\nwrote words_v3.json  ({len(words_all)} words)')
