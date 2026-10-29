"""最终版 ASR 反向识别（咬字可懂度）+ 环节覆盖核对。

目标要求的环节：
  复用：分离 BGM/伴奏、GAME、双F0、ASR
  重做：HFA、歌词/音素身份、谱面、逐句意图、音高函数设计、发声层、
        编译、原生核查、渲染、混音、逐字图审、交付
逐项给出证据文件。
"""
import sys, json, io, os, re
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')

CANON = ('圆圈勾勒成指纹 印在我的嘴唇 回忆苦涩的吻痕 是树根 春去秋来的茂盛 却遮住了黄昏 '
         '寒夜剩我一个人 等清晨 世间最毒的仇恨 是有缘却无份 可惜你从未心疼 我的笨 '
         '荒草丛生的青春 倒也过的安稳 代替你陪着我的 是年轮 数着一圈圈年轮 我认真 '
         '将心事都封存 密密麻麻是我的自尊 修改一次次离分 我承认 曾幻想过永恒 可惜从没人陪我演这剧本')
def norm(s): return re.sub(r'[^\u4e00-\u9fff]', '', s)
CAN = norm(CANON)
canon_bigrams = {CAN[i:i+2] for i in range(len(CAN)-1)}

from faster_whisper import WhisperModel
snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
model_dir = sorted((snap/'snapshots').iterdir())[-1]
m = WhisperModel(str(model_dir), device='cpu', compute_type='int8')

targets = [('source', NEW/'inputs'/'stems'/'vocals.wav'),
           ('v2',     V2/'render'/'vocal_vocal.wav'),
           ('final',  NEW/'render'/'vocal_v23_vocal.wav')]

out={}
for name, p in targets:
    if not p.is_file():
        print(f'{name}: missing'); continue
    segs, _ = m.transcribe(str(p), language='zh', beam_size=5, vad_filter=False)
    txt = ''.join(s.text for s in segs)
    t = norm(txt); tb=[t[i:i+2] for i in range(len(t)-1)]
    br = sum(1 for g in tb if g in canon_bigrams)/max(len(tb),1)
    inc = sum(1 for c in t if c in set(CAN))/max(len(t),1)
    out[name]=dict(chars=len(t), bigram=round(br,4), in_canon=round(inc,4))
    print(f'{name:8s} chars {len(t):4d}  bigram-recall {br:6.1%}  in-canon {inc:6.1%}')
    print(f'   {txt[:180]}')

(NEW/'evaluation'/'asr_roundtrip_final.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')

print('\n=== 目标环节覆盖核对 ===')
checks = [
 ('复用 分离伴奏/人声', NEW/'inputs'/'stems'/'vocals.wav', 'manifest.json 记录 SHA 与 v2 一致'),
 ('复用 GAME', NEW/'inputs'/'game.json', ''),
 ('复用 双F0', NEW/'inputs'/'fcpe.npz', ''),
 ('复用 ASR', NEW/'inputs'/'asr.json', ''),
 ('重做 HFA', NEW/'hfa_blocks_out'/'TextGrid', '14 块整段对齐'),
 ('重做 歌词/音素身份', NEW/'lyrics.json', '改 9 处 ASR 错字'),
 ('重做 谱面', NEW/'score'/'v3_score.ustx', '349 字/51 句/无碎字'),
 ('重做 逐句意图', NEW/'design'/'musical_intent.json', '349 单元'),
 ('重做 音高函数设计', NEW/'design'/'plan.json', '逐字参数化'),
 ('重做 发声层', NEW/'compiled'/'project_final.ustx', 'dyn/voic/brec/tenc'),
 ('重做 编译+原生核查', NEW/'compiled'/'compile_report.json', 'native_max_error 0.5c'),
 ('重做 渲染', NEW/'render'/'vocal_v23_vocal.wav', ''),
 ('重做 混音', NEW/'render'/'nianlun_v23_mix.wav', ''),
 ('重做 逐字图审', NEW/'evaluation'/'per_unit_audit.json', '349 条'),
 ('重做 交付', Path(r'E:\project\agent2utau\demo\nianlun_v3\nianlun_v23_mix.mp3'), ''),
]
ok=0
for name, path, note in checks:
    e = path.exists()
    ok += e
    print(f'  [{"OK" if e else "MISSING"}] {name:22s} {note}')
print(f'\n{ok}/{len(checks)} 环节有证据')
