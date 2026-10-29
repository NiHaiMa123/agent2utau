"""阶段1（修订）：用真实有声段 + 权威歌词重建 51 句结构。

结构依据：
  - 17 个真实有声段（能量检测，不依赖ASR）
  - GAME 每段音符数（校验字数）
  - 权威歌词（百度百科）
  - 歌曲结构：主歌A(4句) 主歌B(4句) 预副歌(4句) 副歌(4句) 高潮(6句) | 间奏 |
              重复 | 间奏 | 尾副歌(6句)
"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
segs = json.load(io.open(NEW / 'vocal_segments.json', encoding='utf-8'))['segments']
g = json.load(io.open(NEW / 'inputs/game.json', encoding='utf-8'))
notes = g['notes']

A = ['圆圈勾勒成指纹', '印在我的嘴唇', '回忆苦涩的吻痕', '是树根']
B = ['春去秋来的茂盛', '却遮住了黄昏', '寒夜剩我一个人', '等清晨']
C = ['世间最毒的仇恨', '是有缘却无份', '可惜你从未心疼', '我的笨']
D = ['荒草丛生的青春', '倒也过的安稳', '代替你陪着我的', '是年轮']
E = ['数着一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
     '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']
TAIL = ['一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
        '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']

# 各段的歌词归属（按真实有声段与 GAME 音符数校验）
# seg0-1 = A前半(圆圈勾勒成指纹 / 印在我的嘴唇)  -> 因为 seg1 只有 1.48s 4 notes
# seg2 = A后半(回忆苦涩的吻痕 是树根)
BLOCKS = [
    # (segment indices, lines, label)
    ((0, 1), ['圆圈勾勒成指纹', '印在我的嘴唇'], 'verseA1'),
    ((2,),   ['回忆苦涩的吻痕', '是树根'], 'verseA2'),
    ((3,),   ['春去秋来的茂盛', '却遮住了黄昏'], 'verseB1'),
    ((4,),   ['寒夜剩我一个人', '等清晨'], 'verseB2'),
    ((5,),   ['世间最毒的仇恨', '是有缘却无份'], 'preC1'),
    ((5,),   ['可惜你从未心疼', '我的笨'], 'preC2'),
    ((6,),   ['荒草丛生的青春', '倒也过的安稳'], 'preD1'),
    ((6,),   ['代替你陪着我的', '是年轮'], 'preD2'),
    ((7,),   ['数着一圈圈年轮', '我认真'], 'chorus1a'),
    ((7,),   ['将心事都封存'], 'chorus1b'),
    ((7,),   ['密密麻麻是我的自尊'], 'chorus1c'),
    ((7,),   ['修改一次次离分', '我承认'], 'chorus1d'),
    ((7,),   ['曾幻想过永恒'], 'chorus1e'),
    ((7,),   ['可惜从没人陪我演这剧本'], 'chorus1f'),
    ((8, 9), A[:2], 'verseA1_r'),
    ((8,),   A[2:], 'verseA2_r'),
    ((8,),   B[:2], 'verseB1_r'),
    ((10,),  B[2:], 'verseB2_r'),
    ((10,),  C[:2], 'preC1_r'),
    ((10,),  C[2:], 'preC2_r'),
    ((10,),  D[:2], 'preD1_r'),
    ((10,),  D[2:], 'preD2_r'),
    ((11,),  E[:2], 'chorus2a'),
    ((11,),  E[2:3], 'chorus2b'),
    ((11,),  E[3:4], 'chorus2c'),
    ((11,),  E[4:6], 'chorus2d'),
    ((11,),  E[6:7], 'chorus2e'),
    ((11,),  E[7:8], 'chorus2f'),
    ((13, 14), TAIL[:2], 'chorus3a'),
    ((13,),  TAIL[2:3], 'chorus3b'),
    ((13,),  TAIL[3:4], 'chorus3c'),
    ((13,),  TAIL[4:6], 'chorus3d'),
    ((13,),  TAIL[6:7], 'chorus3e'),
    ((13,),  TAIL[7:8], 'chorus3f'),
    ((15, 16), ['可惜从没人陪我演这剧本'], 'outro'),
]

print(f'real vocal segments: {len(segs)}')
total = 0
rows = []
for segidx, lines, label in BLOCKS:
    t0 = min(segs[i][0] for i in segidx)
    t1 = max(segs[i][1] for i in segidx)
    nchar = sum(len(l) for l in lines)
    total += nchar
    rows.append(dict(label=label, seg=list(segidx), t=[t0, t1], lines=lines, n=nchar))

print(f'total blocks {len(rows)}, total chars {total}')
for r in rows:
    print(f'  {r["label"]:12s} {r["t"][0]:7.2f}-{r["t"][1]:7.2f} {r["n"]:2d}字  {" / ".join(r["lines"])}')

# check coverage vs GAME notes
print('\nGAME note counts per block (should be >= char count roughly, melisma adds):')
for r in rows:
    ns = [n for n in notes if r['t'][0] <= n['start'] < r['t'][1]]
    print(f'  {r["label"]:12s} chars={r["n"]:2d} game_notes={len(ns):3d}  ratio {len(ns)/max(r["n"],1):.2f}')
