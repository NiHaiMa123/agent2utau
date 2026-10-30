"""阶段1c：用权威歌词 + 真实有声段重建 51 句，准备 HFA 输入。

与 v2 的差别：
  - 歌词用权威版本（修正 ASR 的 9 处错字：寒夜/清晨/世间/有缘却无份/笨/丛生/倒也过/数着/自尊）
  - 句界与切片由真实有声段 + GAME 音符分布决定，不沿用 v2 手写表
"""
import sys, json, io, hashlib
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
from pypinyin import lazy_pinyin

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW / 'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
g = json.load(io.open(NEW / 'inputs/game.json', encoding='utf-8'))
notes = g['notes']
segs = json.load(io.open(NEW / 'vocal_segments.json', encoding='utf-8'))['segments']

A1 = ['圆圈勾勒成指纹', '印在我的嘴唇']
A2 = ['回忆苦涩的吻痕', '是树根']
B1 = ['春去秋来的茂盛', '却遮住了黄昏']
B2 = ['寒夜剩我一个人', '等清晨']
C1 = ['世间最毒的仇恨', '是有缘却无份']
C2 = ['可惜你从未心疼', '我的笨']
D1 = ['荒草丛生的青春', '倒也过的安稳']
D2 = ['代替你陪着我的', '是年轮']
E = ['数着一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
     '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']
TAIL = ['一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
        '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']

def notes_in(t0, t1):
    return [i for i, n in enumerate(notes) if t0 <= n['start'] < t1]

def first_note_starts(t0, t1):
    return [n['start'] for n in notes if t0 <= n['start'] < t1]

# 51 phrases: (label, lines, seg_range, char_target_hint)
# seg_range 给定时，句界在该段内按 GAME 音符的首音分布切分
SPEC = [
    # ---- 主歌A 第一遍 ----
    ('A1a', A1[:1], (0, 0)),
    ('A1b', A1[1:], (1, 1)),
    ('A2a', A2[:1], (2, 2)),
    ('A2b', A2[1:], (2, 2)),
    ('B1a', B1[:1], (3, 3)),
    ('B1b', B1[1:], (3, 3)),
    ('B2a', B2[:1], (4, 4)),
    ('B2b', B2[1:], (4, 4)),
    # ---- 预副歌 ----
    ('C1a', C1[:1], (5, 5)),
    ('C1b', C1[1:], (5, 5)),
    ('C2a', C2[:1], (5, 5)),
    ('C2b', C2[1:], (5, 5)),
    ('D1a', D1[:1], (6, 6)),
    ('D1b', D1[1:], (6, 6)),
    ('D2a', D2[:1], (6, 6)),
    ('D2b', D2[1:], (6, 6)),
    # ---- 副歌1 ----
    ('E1a', E[0:2], (7, 7)),
    ('E1b', E[2:3], (7, 7)),
    ('E1c', E[3:4], (7, 7)),
    ('E1d', E[4:6], (7, 7)),
    ('E1e', E[6:7], (7, 7)),
    ('E1f', E[7:8], (7, 7)),
    # ---- 主歌A 第二遍 ----
    ('A2a_a', A1[:1], (8, 8)),
    ('A2b_a', A1[1:], (8, 8)),
    ('A2c_a', A2[:1], (8, 8)),
    ('A2d_a', A2[1:], (8, 8)),
    ('B2a_a', B1[:1], (8, 8)),
    ('B2b_a', B1[1:], (8, 8)),
    ('B2c_a', B2[:1], (10, 10)),
    ('B2d_a', B2[1:], (10, 10)),
    # ---- 预副歌 第二遍 ----
    ('C2a_a', C1[:1], (10, 10)),
    ('C2b_a', C1[1:], (10, 10)),
    ('C2c_a', C2[:1], (10, 10)),
    ('C2d_a', C2[1:], (10, 10)),
    ('D2a_a', D1[:1], (10, 10)),
    ('D2b_a', D1[1:], (10, 10)),
    ('D2c_a', D2[:1], (10, 10)),
    ('D2d_a', D2[1:], (10, 10)),
    # ---- 副歌2 ----
    ('E2a', E[0:2], (11, 11)),
    ('E2b', E[2:3], (11, 11)),
    ('E2c', E[3:4], (11, 11)),
    ('E2d', E[4:6], (11, 11)),
    ('E2e', E[6:7], (11, 11)),
    ('E2f', E[7:8], (11, 11)),
    # ---- 副歌3 / 尾 ----
    ('E3a', TAIL[0:2], (13, 14)),
    ('E3b', TAIL[2:3], (13, 13)),
    ('E3c', TAIL[3:4], (13, 13)),
    ('E3d', TAIL[4:6], (13, 13)),
    ('E3e', TAIL[6:7], (13, 13)),
    ('E3f', TAIL[7:8], (13, 13)),
    ('OUT', ['可惜从没人陪我演这剧本'], (15, 16)),
]
print(f'spec phrases: {len(SPEC)}')

# 为同一 seg 内的多个句按 GAME 音符数比例切分时间
from collections import defaultdict
by_seg = defaultdict(list)
for i, (lab, lines, sg) in enumerate(SPEC):
    by_seg[sg].append(i)

bounds = {}
for sg, idxs in by_seg.items():
    t0 = min(segs[s][0] for s in sg)
    t1 = max(segs[s][1] for s in sg)
    if len(idxs) == 1:
        bounds[idxs[0]] = (t0, t1); continue
    # weight by char count
    w = np.array([sum(len(l) for l in SPEC[i][1]) for i in idxs], float)
    starts = first_note_starts(t0, t1)
    # use GAME note onsets near cumulative char-proportional positions
    cum = np.r_[0, np.cumsum(w)/w.sum()]
    edges = [t0]
    for k in range(1, len(idxs)):
        target = t0 + (t1-t0)*cum[k]
        # snap to nearest GAME note onset
        if starts:
            nearest = min(starts, key=lambda x: abs(x-target))
            if t0 < nearest < t1: target = nearest
        edges.append(target)
    edges.append(t1)
    for k, i in enumerate(idxs):
        bounds[i] = (edges[k], edges[k+1])

rows = []
for i, (lab, lines, sg) in enumerate(SPEC):
    t0, t1 = bounds[i]
    text = ''.join(lines)
    py = ' '.join(lazy_pinyin(text))
    rows.append(dict(pid=f'p{i:02d}', label=lab, hanzi=text, pinyin=py,
                     t0=round(t0,3), t1=round(t1,3), seg=list(sg), lines=lines))

# validate monotone, non-overlapping
for a, b in zip(rows, rows[1:]):
    if a['t1'] > b['t0'] + 0.01:
        print(f"  WARN overlap {a['pid']} {a['t1']} -> {b['pid']} {b['t0']}")

# prepare HFA inputs
hfa_dir = NEW / 'hfa_inputs'; hfa_dir.mkdir(exist_ok=True)
manifest = {'phrases': []}
for r in rows:
    s0 = max(0.0, r['t0'] - 0.15); s1 = min(len(v)/sr, r['t1'] + 0.15)
    data = v[int(s0*sr):int(s1*sr)]
    wav = hfa_dir / f"{r['pid']}.wav"; wav.write_bytes(b'')
    sf.write(str(wav), data, sr)
    lab = hfa_dir / f"{r['pid']}.lab"
    lab.write_text(r['pinyin'], encoding='utf-8')
    r['slice'] = [round(s0,3), round(s1,3)]
    r['wav_sha256'] = hashlib.sha256(wav.read_bytes()).hexdigest()
    r['lab_sha256'] = hashlib.sha256(lab.read_bytes()).hexdigest()
    manifest['phrases'].append(r)

(hfa_dir/'slices_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(NEW/'lyrics.json').write_text(json.dumps(dict(schema_version=1, phrases=rows,
    source='百度百科权威歌词 + GAME音符事件 + 真实有声段能量检测', n=len(rows)), ensure_ascii=False, indent=2), encoding='utf-8')

print(f'\n{len(rows)} phrases:')
for r in rows:
    print(f"  {r['pid']} {r['t0']:7.2f}-{r['t1']:7.2f} {r['label']:7s} {r['hanzi']}")
print(f'\nwrote {NEW}/lyrics.json + hfa_inputs/')
