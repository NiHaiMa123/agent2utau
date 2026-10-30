"""用本地缓存的 whisper 模型做 ASR 反向识别（离线，不走网络）。"""
import sys, json, io, os, re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')

from faster_whisper import WhisperModel
snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
snaps = sorted((snap/'snapshots').iterdir())
model_dir = snaps[-1]
print(f'model: {model_dir}')
m = WhisperModel(str(model_dir), device='cpu', compute_type='int8')

CANON = ('圆圈勾勒成指纹 印在我的嘴唇 回忆苦涩的吻痕 是树根 春去秋来的茂盛 却遮住了黄昏 '
         '寒夜剩我一个人 等清晨 世间最毒的仇恨 是有缘却无份 可惜你从未心疼 我的笨 '
         '荒草丛生的青春 倒也过的安稳 代替你陪着我的 是年轮 数着一圈圈年轮 我认真 '
         '将心事都封存 密密麻麻是我的自尊 修改一次次离分 我承认 曾幻想过永恒 可惜从没人陪我演这剧本')
def norm(s): return re.sub(r'[^\u4e00-\u9fff]', '', s)
CAN = norm(CANON)
canon_bigrams = {CAN[i:i+2] for i in range(len(CAN)-1)}

targets = [('source', NEW/'inputs/stems/vocals.wav'),
           ('v2', V2/'render'/'vocal_vocal.wav'),
           ('v3(ours)', NEW/'render'/'vocal_v3h_vocal.wav')]

out = {}
for name, p in targets:
    if not p.exists(): print(f'{name}: missing'); continue
    segs, info = m.transcribe(str(p), language='zh', beam_size=5, vad_filter=False)
    txt = ''.join(s.text for s in segs)
    t = norm(txt)
    tb = [t[i:i+2] for i in range(len(t)-1)]
    br = sum(1 for g in tb if g in canon_bigrams)/max(len(tb),1)
    in_canon = sum(1 for c in t if c in set(CAN))/max(len(t),1)
    out[name] = dict(chars=len(t), bigram_recall=round(br,4), in_canon=round(in_canon,4), text=txt[:600])
    print(f'\n{name}: {len(t)} chars  bigram-recall {br:.1%}  in-canon {in_canon:.1%}')
    print(f'  {txt[:260]}')

(NEW/'evaluation'/'asr_roundtrip.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print('\nwrote evaluation/asr_roundtrip.json')
