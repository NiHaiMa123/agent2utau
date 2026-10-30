"""关键检查：用 ASR 反向识别我们渲染的人声，看歌词是否清晰可懂。

如果 ASR 能从我们的音频里识别出正确歌词，说明咬字基本清楚；
如果识别出大量错字/乱码，说明咬字或音素有问题——这才是「差」的可能真相。
对照：同一 ASR 识别原唱。
"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.analysis.lyrics import transcribe

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')

targets = [('source', NEW/'inputs/stems/vocals.wav'),
           ('v2', V2/'render'/'vocal_vocal.wav'),
           ('v3i', NEW/'render'/'vocal_v3h_vocal.wav')]

out = {}
for name, p in targets:
    if not p.exists(): print(f'{name}: missing'); continue
    print(f'transcribing {name} ...', flush=True)
    r = transcribe(p, model='large-v3-turbo')
    txt = ' | '.join(s['text'] for s in r['segments'] if s['end']-s['start'] > 0.5)
    out[name] = dict(segments=len(r['segments']), text=txt)
    print(f'  {name}: {len(r["segments"])} segments')
    print(f'  {txt[:300]}')

(NEW/'evaluation'/'asr_roundtrip.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

# compare with the canonical lyric (character-level overlap)
CANON = ('圆圈勾勒成指纹 印在我的嘴唇 回忆苦涩的吻痕 是树根 春去秋来的茂盛 却遮住了黄昏 '
         '寒夜剩我一个人 等清晨 世间最毒的仇恨 是有缘却无份 可惜你从未心疼 我的笨 '
         '荒草丛生的青春 倒也过的安稳 代替你陪着我的 是年轮 数着一圈圈年轮 我认真 '
         '将心事都封存 密密麻麻是我的自尊 修改一次次离分 我承认 曾幻想过永恒 可惜从没人陪我演这剧本')
import re
def norm(s): return re.sub(r'[^\u4e00-\u9fff]', '', s)
canon_set = set(norm(CANON))
print('\n=== 识别字符与原歌词的覆盖 ===')
for k, v in out.items():
    t = norm(v['text'])
    if not t: continue
    hit = sum(1 for c in t if c in canon_set)
    # bigram recall
    bigrams = {norm(CANON)[i:i+2] for i in range(len(norm(CANON))-1)}
    tb = [t[i:i+2] for i in range(len(t)-1)]
    br = sum(1 for g in tb if g in bigrams)/max(len(tb),1)
    print(f'  {k:8s} chars {len(t):4d}  in-canon {hit/max(len(t),1):.1%}  bigram-recall {br:.1%}')
