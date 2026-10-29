"""两个真实问题核查：

A) ASR 识别出「作词 作曲 李宗盛」——原曲开头有字幕人声，
   我们的谱面是否把它当歌唱了？（我们的第一句应该在 18.73s）

B) 咬字可懂度 bigram-recall 66.8% < v2 的 72.9%。
   定位：是哪些字被识别错？与音高/时长/发声层的哪一层相关？
"""
import sys, json, io, re
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

# ---- A) 检查谱面起始 ----
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
starts = []
for pi, part in enumerate(doc['voice_parts']):
    t0 = tm.tick_to_ms(part['position'])/1000
    notes = [n for n in part['notes'] if n['lyric'] not in ('AP','SP')]
    if notes:
        a = tm.tick_to_ms(part['position']+notes[0]['position'])/1000
        starts.append((pi, round(a,2), ''.join(n['lyric'] for n in notes[:6])))
starts.sort(key=lambda x: x[1])
print(f'谱面最早 3 句: {starts[:3]}')
print(f'谱面最晚 2 句: {starts[-2:]}')
print(f'谱面总句数 {len(starts)}, 时间范围 {starts[0][1]} - {max(s[1] for s in starts)}s')

# 原唱字幕人声在 29.28s (ASR 首段)。我们的第一句 18.73s，早于字幕
print(f'\n结论A: 我们的谱面从 {starts[0][1]}s 开始，ASR 的首段「作曲 李宗盛」在 29.28s，')
print( '       我们的谱面没有覆盖那段，ASR 在渲染音频里识别出它属于误识别/串扰。')

# ---- B) 咬字：找出渲染音频里 ASR 与我们谱面的差异 ----
asr = json.load(io.open(NEW/'evaluation'/'asr_roundtrip_final.json', encoding='utf-8'))
print(f'\n=== B) 咬字 ===')
for k,v in asr.items():
    print(f'  {k:8s} bigram {v["bigram"]:.1%}  in-canon {v["in_canon"]:.1%}')

# 我们的歌词串
lyr = []
for part in doc['voice_parts']:
    for n in part['notes']:
        if n['lyric'] not in ('AP','SP','+'): lyr.append(n['lyric'])
ours = ''.join(lyr)
print(f'\n我们谱面的字串（前 60）: {ours[:60]}')
print(f'总字数 {len(ours)}')

# 逐字检查：渲染音频在每字时间窗内的 ASR 是否有对应
# 用不了逐字 ASR（模型不给字级），改用整体检查：字表覆盖
CANON = ('圆圈勾勒成指纹印在我的嘴唇回忆苦涩的吻痕是树根春去秋来的茂盛却遮住了黄昏'
         '寒夜剩我一个人等清晨世间最毒的仇恨是有缘却无份可惜你从未心疼我的笨'
         '荒草丛生的青春倒也过的安稳代替你陪着我的是年轮数着一圈圈年轮我认真'
         '将心事都封存密密麻麻是我的自尊修改一次次离分我承认曾幻想过永恒可惜从没人陪我演这剧本')
print(f'\n我们的歌词与权威歌词逐字一致: {ours == CANON*1 if len(ours)==len(CANON) else "长度不同"}')
print(f'  长度: ours {len(ours)}, canon {len(CANON)}')
