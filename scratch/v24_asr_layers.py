"""定位咬字恶化的层：分别测试
  A) 原谱面（无声发层）的渲染 —— 排除发声层
  B) 有声发层的渲染（当前）
如果 A 明显好于 B，说明 dyn/voic/brec 损害了咬字。
（用 ASR bigram-recall 衡量）
"""
import sys, json, io, os, re
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
CANON = ('圆圈勾勒成指纹印在我的嘴唇回忆苦涩的吻痕是树根春去秋来的茂盛却遮住了黄昏'
         '寒夜剩我一个人等清晨世间最毒的仇恨是有缘却无份可惜你从未心疼我的笨'
         '荒草丛生的青春倒也过的安稳代替你陪着我的是年轮数着一圈圈年轮我认真'
         '将心事都封存密密麻麻是我的自尊修改一次次离分我承认曾幻想过永恒可惜从没人陪我演这剧本')
def norm(s): return re.sub(r'[^\u4e00-\u9fff]', '', s)
CAN = norm(CANON)          # 144 字（每句只出现一次的结构）
# 用完整 349 字的歌词做 bigram 参考（重复句也要计入）
DOC = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029\score\v3_score.ustx')
from agent2utau.openutau.ustx import load_ustx
d = load_ustx(NEW/'score'/'v3_score.ustx')
ours = ''.join(n['lyric'] for part in d['voice_parts'] for n in part['notes']
               if n['lyric'] not in ('AP','SP','+'))
bigrams = {ours[i:i+2] for i in range(len(ours)-1)}
print(f'参考歌词 {len(ours)} 字, {len(bigrams)} 个 bigram')

from faster_whisper import WhisperModel
snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
md = sorted((snap/'snapshots').iterdir())[-1]
m = WhisperModel(str(md), device='cpu', compute_type='int8')

def score(p):
    segs,_ = m.transcribe(str(p), language='zh', beam_size=5, vad_filter=False)
    t = norm(''.join(s.text for s in segs))
    tb=[t[i:i+2] for i in range(len(t)-1)]
    br = sum(1 for g in tb if g in bigrams)/max(len(tb),1)
    return br, len(t)

cands = [
    ('final (with phonation)', NEW/'render'/'vocal_v23_vocal.wav'),
    ('v2 (reference)',         Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028\render\vocal_vocal.wav')),
    ('source',                 NEW/'inputs'/'stems'/'vocals.wav'),
]
for name, p in cands:
    if not p.is_file(): print(f'{name}: missing'); continue
    br, n = score(p)
    print(f'  {name:26s} bigram {br:6.1%}  chars {n}')
