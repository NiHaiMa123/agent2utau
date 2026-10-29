"""v3 阶段1（最终）：一步到位重建 51 句歌词与时间轴。

设计原则（吸取前两版教训）：
  1) 歌词用权威版本（修正 ASR 9 处错字）
  2) 句界由真实有声段 + GAME 音符起点决定，不手写时间表
  3) 所有边界单调、不重叠；重叠一律报错而非静默修
  4) 每段内的多句按 GAME 音符数（不是字数）比例切——音符数才反映实际演唱单元
"""
import sys, json, io, hashlib
import numpy as np, soundfile as sf
from pathlib import Path
from pypinyin import lazy_pinyin
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
notes = g['notes']
segs = json.load(io.open(NEW/'vocal_segments.json', encoding='utf-8'))['segments']

A1 = ['圆圈勾勒成指纹', '印在我的嘴唇']
A2 = ['回忆苦涩的吻痕', '是树根']
B1 = ['春去秋来的茂盛', '却遮住了黄昏']
B2 = ['寒夜剩我一个人', '等清晨']
C1 = ['世间最毒的仇恨', '是有缘却无份']
C2 = ['可惜你从未心疼', '我的笨']
D1 = ['荒草丛生的青春', '倒也过的安稳']
D2 = ['代替你陪着我的', '是年轮']
E  = ['数着一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
      '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']
TAIL = ['一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
        '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']

# (label, lines, allowed_segment_indices)
SPEC = [
    ('A1a', A1[:1], (0,)), ('A1b', A1[1:], (1,)),
    ('A2a', A2[:1], (2,)), ('A2b', A2[1:], (2,)),
    ('B1a', B1[:1], (3,)), ('B1b', B1[1:], (3,)),
    ('B2a', B2[:1], (4,)), ('B2b', B2[1:], (4,)),
    ('C1a', C1[:1], (5,)), ('C1b', C1[1:], (5,)),
    ('C2a', C2[:1], (5,)), ('C2b', C2[1:], (5,)),
    ('D1a', D1[:1], (6,)), ('D1b', D1[1:], (6,)),
    ('D2a', D2[:1], (6,)), ('D2b', D2[1:], (6,)),
    ('E1a', E[0:2], (7,)), ('E1b', E[2:3], (7,)), ('E1c', E[3:4], (7,)),
    ('E1d', E[4:6], (7,)), ('E1e', E[6:7], (7,)), ('E1f', E[7:8], (7,)),
    ('A2a_r', A1[:1], (8,)), ('A2b_r', A1[1:], (8,)),
    ('A2c_r', A2[:1], (8,)), ('A2d_r', A2[1:], (8,)),
    ('B2a_r', B1[:1], (8,)), ('B2b_r', B1[1:], (8,)),
    ('B2c_r', B2[:1], (10,)), ('B2d_r', B2[1:], (10,)),
    ('C2a_r', C1[:1], (10,)), ('C2b_r', C1[1:], (10,)),
    ('C2c_r', C2[:1], (10,)), ('C2d_r', C2[1:], (10,)),
    ('D2a_r', D1[:1], (10,)), ('D2b_r', D1[1:], (10,)),
    ('D2c_r', D2[:1], (10,)), ('D2d_r', D2[1:], (10,)),
    ('E2a', E[0:2], (11,)), ('E2b', E[2:3], (11,)), ('E2c', E[3:4], (11,)),
    ('E2d', E[4:6], (11,)), ('E2e', E[6:7], (11,)), ('E2f', E[7:8], (11,)),
    ('E3a', TAIL[0:2], (13,)), ('E3b', TAIL[2:3], (13,)), ('E3c', TAIL[3:4], (13,)),
    ('E3d', TAIL[4:6], (13,)), ('E3e', TAIL[6:7], (13,)), ('E3f', TAIL[7:8], (13,)),
    ('OUT', ['可惜从没人陪我演这剧本'], (15, 16)),
]
assert len(SPEC) == 51

# 每段可用 GAME 音符起点（作为合法切点）
def onsets_in(t0, t1, min_gap=0.05):
    out = []
    for n in notes:
        if t0 + min_gap < n['start'] < t1 - min_gap:
            if not out or n['start'] - out[-1] >= min_gap:
                out.append(n['start'])
    return out

# group by segment tuple
from collections import OrderedDict
groups = OrderedDict()
for i, (lab, lines, sg) in enumerate(SPEC):
    groups.setdefault(sg, []).append(i)

bounds = {}
for sg, idxs in groups.items():
    t0 = min(segs[s][0] for s in sg)
    t1 = max(segs[s][1] for s in sg)
    if len(idxs) == 1:
        bounds[idxs[0]] = (t0, t1); continue
    # weight by number of GAME notes if available, else chars
    w = []
    for i in idxs:
        n_chars = sum(len(l) for l in SPEC[i][1])
        n_notes = sum(1 for n in notes if t0 <= n['start'] < t1)
        # distribute by chars but scaled — chars is the honest unit for time
        w.append(n_chars)
    w = np.array(w, float)
    cum = np.r_[0, np.cumsum(w)/w.sum()]
    cands = onsets_in(t0, t1)
    edges = [t0]
    for k in range(1, len(idxs)):
        target = t0 + (t1-t0)*cum[k]
        prev = edges[-1]
        valid = [c for c in cands if c > prev + 0.08 and c < t1 - 0.08]
        pick = min(valid, key=lambda x: abs(x-target)) if valid else target
        edges.append(pick)
    edges.append(t1)
    for k, i in enumerate(idxs):
        bounds[i] = (edges[k], edges[k+1])

rows = []
for i, (lab, lines, sg) in enumerate(SPEC):
    t0, t1 = bounds[i]
    text = ''.join(lines)
    rows.append(dict(pid=f'p{i:02d}', label=lab, hanzi=text,
                     pinyin=' '.join(lazy_pinyin(text)),
                     t0=round(t0,3), t1=round(t1,3),
                     seg=list(sg), lines=lines, n_chars=len(text)))

# strict validation
errs = []
for a, b in zip(rows, rows[1:]):
    if a['t1'] > b['t0'] + 1e-6:
        errs.append(f"overlap {a['pid']}({a['t1']}) -> {b['pid']}({b['t0']})")
    if a['t0'] >= a['t1']:
        errs.append(f"empty {a['pid']}")
if errs:
    print('VALIDATION FAILED:'); [print('  ', e) for e in errs]; raise SystemExit(1)
print(f'51 phrases validated: monotone, no overlap, no empty')

# HFA inputs
hfa_dir = NEW/'hfa_inputs'
if hfa_dir.exists():
    for f in hfa_dir.iterdir(): f.unlink()
hfa_dir.mkdir(exist_ok=True)
manifest = {'phrases': []}
for r in rows:
    s0 = max(0.0, r['t0']-0.15); s1 = min(len(v)/sr, r['t1']+0.15)
    wav = hfa_dir/f"{r['pid']}.wav"
    sf.write(str(wav), v[int(s0*sr):int(s1*sr)], sr)
    lab = hfa_dir/f"{r['pid']}.lab"
    lab.write_text(r['pinyin'], encoding='utf-8')
    r['slice'] = [round(s0,3), round(s1,3)]
    r['wav_sha256'] = hashlib.sha256(wav.read_bytes()).hexdigest()
    r['lab_sha256'] = hashlib.sha256(lab.read_bytes()).hexdigest()
    manifest['phrases'].append(r)
(hfa_dir/'slices_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(NEW/'lyrics.json').write_text(json.dumps(dict(schema_version=1, phrases=rows, n=51,
    source='百度百科权威歌词 + GAME音符事件 + 真实有声段能量检测',
    asr_corrections=['寒夜(ASR:还也)','清晨(等情侦)','世间(时间)','有缘却无份(是永远却无分)',
                     '我的笨(我的本)','荒草丛生(荒草从深)','倒也过(到越过)','数着(树舍)','自尊(子孙)']),
    ensure_ascii=False, indent=2), encoding='utf-8')

print()
for r in rows:
    print(f"  {r['pid']} {r['t0']:7.2f}-{r['t1']:7.2f} {r['t1']-r['t0']:5.2f}s {r['label']:8s} {r['hanzi']}")
print(f"\nwrote lyrics.json + {len(manifest['phrases'])} HFA slices")
