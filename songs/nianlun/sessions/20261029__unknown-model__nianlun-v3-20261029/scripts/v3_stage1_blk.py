"""阶段1（v3 最终方案）：整段一次性 HFA 对齐，不用小切片。

前两版失败的一个重要原因：把歌词切成 51 个小片分别对齐，
切片边界会切掉字头/字尾，HFA 在小片上还会把多个字压进 20ms。

v3：按「连续演唱段」切片（17 个真实有声段，每段 1.5-33s），
每段含完整多句歌词，一次性对齐。段内句界由 HFA 的字位置自然给出。
"""
import sys, json, io, hashlib
import numpy as np, soundfile as sf
from pathlib import Path
from pypinyin import lazy_pinyin
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
segs = json.load(io.open(NEW/'vocal_segments.json', encoding='utf-8'))['segments']

# 17 个真实有声段 -> 歌词归属（按 GAME 音符数与歌曲结构核验）
BLOCKS = [
    (0,  ['圆圈勾勒成指纹']),
    (1,  ['印在我的嘴唇']),
    (2,  ['回忆苦涩的吻痕', '是树根']),
    (3,  ['春去秋来的茂盛', '却遮住了黄昏']),
    (4,  ['寒夜剩我一个人', '等清晨']),
    (5,  ['世间最毒的仇恨', '是有缘却无份', '可惜你从未心疼', '我的笨']),
    (6,  ['荒草丛生的青春', '倒也过的安稳', '代替你陪着我的', '是年轮']),
    (7,  ['数着一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
          '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']),
    (8,  ['圆圈勾勒成指纹', '印在我的嘴唇', '回忆苦涩的吻痕', '是树根',
          '春去秋来的茂盛', '却遮住了黄昏']),
    (9,  []),                      # 1.60s 短段，可能是拖音/气声
    (10, ['寒夜剩我一个人', '等清晨', '世间最毒的仇恨', '是有缘却无份',
          '可惜你从未心疼', '我的笨', '荒草丛生的青春', '倒也过的安稳',
          '代替你陪着我的', '是年轮']),
    (11, ['数着一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
          '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']),
    (12, []),                      # 0.68s
    (13, ['一圈圈年轮', '我认真', '将心事都封存', '密密麻麻是我的自尊',
          '修改一次次离分', '我承认', '曾幻想过永恒', '可惜从没人陪我演这剧本']),
    (14, []),                      # 0.28s
    (15, ['可惜从没人陪我演这剧本']),
    (16, ['可惜从没人陪我演这剧本']),
]

hfa_dir = NEW/'hfa_blocks'
if hfa_dir.exists():
    for f in hfa_dir.iterdir(): f.unlink()
hfa_dir.mkdir(exist_ok=True)

manifest = {'blocks': []}
for si, lines in BLOCKS:
    t0, t1 = segs[si]
    if not lines:
        print(f'  block seg{si} {t0:.2f}-{t1:.2f} : no lyrics (skipped)')
        continue
    text = ''.join(lines)
    py = ' '.join(lazy_pinyin(text))
    s0 = max(0.0, t0 - 0.30); s1 = min(len(v)/sr, t1 + 0.30)
    name = f'seg{si:02d}'
    wav = hfa_dir/f'{name}.wav'
    sf.write(str(wav), v[int(s0*sr):int(s1*sr)], sr)
    lab = hfa_dir/f'{name}.lab'
    lab.write_text(py, encoding='utf-8')
    manifest['blocks'].append(dict(name=name, seg=si, lines=lines, text=text,
                                   n_chars=len(text), slice=[round(s0,3), round(s1,3)],
                                   voiced=[t0, t1]))
    print(f'  {name} seg{si} voiced {t0:.2f}-{t1:.2f} slice {s0:.2f}-{s1:.2f} '
          f'{len(text):2d}字  {text}')

(hfa_dir/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\nwrote {len(manifest['blocks'])} block inputs")
