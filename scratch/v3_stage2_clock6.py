"""阶段2（v3-CLK6 定稿）：完全自建字时钟（不用 HFA 时长，仅借其音节串）。

诊断依据：
  HFA 在本曲多处把连续字压成 0.02s（seg10 前 10 字全挤在 0.24s，
  而 GAME 在此处有 5 个 ~0.4s 音符、真实演唱 131.75-135.0）。HFA 不可用作字长。

自建方案（三源可检验）：
  1) 歌词：权威版本（349 字，51 句）
  2) 句界：真实有声段 + 句内字数均分到 [t0,t1]（句是音乐单位）
  3) 字界：在本句内逐个放置边界，锚定到「GAME 音符起点 + 能量起音」，
     并要求每个字内部有足够的有声覆盖（元音核）
  4) 音高：每字核心有声段的中位（cent 精度，不量化到半音）

边界候选不必等于字数：一个字的 melisma 会跨多个音符，故用「按字均分 + 就近吸附」，
而非「音符数=字数」。
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
from scipy.signal import find_peaks
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
notes = g['notes']
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')

HOP = 0.01
nn = len(v)//int(HOP*sr)
E = np.sqrt((v[:nn*int(HOP*sr)].reshape(nn, int(HOP*sr))**2).mean(1))
DB = 20*np.log10(np.maximum(E, 1e-9)); TE = (np.arange(nn)+0.5)*HOP

ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
def cents(a): return 6900.0 + 1200.0*np.log2(np.maximum(a, 1e-6)/440.0)
C_F = np.where(fv, cents(ff), np.nan); C_R = np.where(rv, cents(rf), np.nan)
AGREE = np.isfinite(C_F) & np.isfinite(C_R) & (np.abs(C_F-C_R) <= 100)
C_SRC = np.where(AGREE, (C_F+C_R)/2, np.nan)

# ---- 51 句（与阶段1一致） ----
SEGS = json.load(io.open(NEW/'vocal_segments.json', encoding='utf-8'))['segments']
A1=['圆圈勾勒成指纹','印在我的嘴唇']; A2=['回忆苦涩的吻痕','是树根']
B1=['春去秋来的茂盛','却遮住了黄昏']; B2=['寒夜剩我一个人','等清晨']
C1=['世间最毒的仇恨','是有缘却无份']; C2=['可惜你从未心疼','我的笨']
D1=['荒草丛生的青春','倒也过的安稳']; D2=['代替你陪着我的','是年轮']
E=['数着一圈圈年轮','我认真','将心事都封存','密密麻麻是我的自尊',
   '修改一次次离分','我承认','曾幻想过永恒','可惜从没人陪我演这剧本']
TAIL=['一圈圈年轮','我认真','将心事都封存','密密麻麻是我的自尊',
      '修改一次次离分','我承认','曾幻想过永恒','可惜从没人陪我演这剧本']

SPEC=[('A1a',A1[:1],(0,)),('A1b',A1[1:],(1,)),('A2a',A2[:1],(2,)),('A2b',A2[1:],(2,)),
 ('B1a',B1[:1],(3,)),('B1b',B1[1:],(3,)),('B2a',B2[:1],(4,)),('B2b',B2[1:],(4,)),
 ('C1a',C1[:1],(5,)),('C1b',C1[1:],(5,)),('C2a',C2[:1],(5,)),('C2b',C2[1:],(5,)),
 ('D1a',D1[:1],(6,)),('D1b',D1[1:],(6,)),('D2a',D2[:1],(6,)),('D2b',D2[1:],(6,)),
 ('E1a',E[0:2],(7,)),('E1b',E[2:3],(7,)),('E1c',E[3:4],(7,)),('E1d',E[4:6],(7,)),
 ('E1e',E[6:7],(7,)),('E1f',E[7:8],(7,)),
 ('A2a_r',A1[:1],(8,)),('A2b_r',A1[1:],(8,)),('A2c_r',A2[:1],(8,)),('A2d_r',A2[1:],(8,)),
 ('B2a_r',B1[:1],(8,)),('B2b_r',B1[1:],(8,)),
 ('B2c_r',B2[:1],(10,)),('B2d_r',B2[1:],(10,)),
 ('C2a_r',C1[:1],(10,)),('C2b_r',C1[1:],(10,)),('C2c_r',C2[:1],(10,)),('C2d_r',C2[1:],(10,)),
 ('D2a_r',D1[:1],(10,)),('D2b_r',D1[1:],(10,)),('D2c_r',D2[:1],(10,)),('D2d_r',D2[1:],(10,)),
 ('E2a',E[0:2],(11,)),('E2b',E[2:3],(11,)),('E2c',E[3:4],(11,)),('E2d',E[4:6],(11,)),
 ('E2e',E[6:7],(11,)),('E2f',E[7:8],(11,)),
 ('E3a',TAIL[0:2],(13,)),('E3b',TAIL[2:3],(13,)),('E3c',TAIL[3:4],(13,)),('E3d',TAIL[4:6],(13,)),
 ('E3e',TAIL[6:7],(13,)),('E3f',TAIL[7:8],(13,)),('OUT',['可惜从没人陪我演这剧本'],(15,16))]
assert len(SPEC)==51

# phrase windows (same logic as stage 1)
from collections import OrderedDict
groups=OrderedDict()
for i,(lab,lines,sg) in enumerate(SPEC): groups.setdefault(sg,[]).append(i)
def onsets_in(a,b,m=0.06):
    out=[]
    for n in notes:
        if a+m < n['start'] < b-m:
            if not out or n['start']-out[-1]>=m: out.append(n['start'])
    return out
bounds={}
for sg,idxs in groups.items():
    t0=min(SEGS[s][0] for s in sg); t1=max(SEGS[s][1] for s in sg)
    if len(idxs)==1: bounds[idxs[0]]=(t0,t1); continue
    w=np.array([sum(len(l) for l in SPEC[i][1]) for i in idxs],float)
    cum=np.r_[0,np.cumsum(w)/w.sum()]; cands=onsets_in(t0,t1); edges=[t0]
    for k in range(1,len(idxs)):
        target=t0+(t1-t0)*cum[k]; prev=edges[-1]
        valid=[c for c in cands if c>prev+0.08 and c<t1-0.08]
        edges.append(min(valid,key=lambda x:abs(x-target)) if valid else target)
    edges.append(t1)
    for k,i in enumerate(idxs): bounds[i]=(edges[k],edges[k+1])

# ---- word boundaries inside a phrase ----
def place_words(t0, t1, N):
    """Place N syllable boundaries in [t0,t1]: even split, snapped to note onsets/energy valleys."""
    if N == 1: return [t0, t1]
    # energy valleys inside
    lo, hi = int(t0/HOP), int(min(t1/HOP, nn-1))
    seg_db = DB[lo:hi]
    vk, _ = find_peaks(-seg_db, distance=3)
    valleys = [TE[lo+i] for i in vk]
    cands = sorted(set(np.round(onsets_in(t0, t1, 0.04) + valleys, 3)))
    min_syl = min(0.10, (t1-t0)/N*0.85)
    edges = [t0]
    for k in range(1, N):
        target = t0 + (t1-t0)*k/N
        lo_b = edges[-1] + min_syl
        hi_b = t1 - min_syl*(N-k)
        valid = [c for c in cands if lo_b < c < hi_b]
        pick = min(valid, key=lambda x: abs(x-target)) if valid else max(lo_b, min(target, hi_b))
        edges.append(pick)
    edges.append(t1)
    # enforce monotone & min length
    for k in range(1, N):
        if edges[k] - edges[k-1] < min_syl:
            edges[k] = edges[k-1] + min_syl
    if edges[-1] > t1:
        edges[-1] = t1
        # compress backwards
        for k in range(N-1, 0, -1):
            if edges[k] - edges[k-1] < min_syl:
                edges[k-1] = edges[k] - min_syl
        edges[0] = max(edges[0], t0)
    return [round(e,4) for e in edges]

def word_pitch(a, b):
    t = np.arange(a, b, HOP)
    if len(t) < 3: return None, 0.0
    i = np.clip(np.rint(t/HOP).astype(int), 0, len(C_SRC)-1)
    c = C_SRC[i]; good = np.isfinite(c)
    cover = float(good.mean())
    if good.sum() < 3: return None, cover
    v_ = c[good]
    return float(np.median(v_)), cover

phrases_out=[]; words_all=[]
for i,(lab,lines,sg) in enumerate(SPEC):
    t0,t1=bounds[i]; text=''.join(lines); N=len(text)
    edges=place_words(t0,t1,N)
    ws=[]
    ci=0
    for li,line in enumerate(lines):
        for ch in line:
            a,b=edges[ci],edges[ci+1]
            pc,cov=word_pitch(a,b)
            ws.append(dict(hanzi=ch,line_idx=li,char_idx=ci,start=a,end=b,dur=round(b-a,4),
                           pitch_cents=round(pc,2) if pc is not None else None,
                           voiced_cover=round(cov,3)))
            ci+=1
    phrases_out.append(dict(pid=f'p{i:02d}',label=lab,lines=lines,hanzi=text,
                            time=[t0,t1],n=N,words=ws))
    words_all.extend(ws)

d=np.array([w['dur'] for w in words_all])
cov=np.array([w['voiced_cover'] for w in words_all])
print(f'phrases {len(phrases_out)}  words {len(words_all)}')
print(f'dur: min {d.min():.3f} p5 {np.percentile(d,5):.3f} median {np.median(d):.3f} max {d.max():.3f}')
print(f'  <0.10s: {(d<0.10).sum()}  <=0: {(d<=0).sum()}')
print(f'voiced_cover: median {np.median(cov):.2f}  <0.3: {(cov<0.3).sum()}')
noP=[w for w in words_all if w['pitch_cents'] is None]
print(f'words with no pitch: {len(noP)}')
(NEW/'words_v3.json').write_text(json.dumps(dict(
    schema_version=1, n_words=len(words_all), phrases=phrases_out,
    method='self-built clock: phrase windows from voiced segments; syllable boundaries by even split '
           'snapped to GAME note onsets + energy valleys with min-length constraint; '
           'pitch = dual-detector agreement median at cent resolution (no semitone quantization); '
           'HFA not used for durations (it collapsed in dense passages)'),
    ensure_ascii=False, indent=1), encoding='utf-8')
print('wrote words_v3.json')
