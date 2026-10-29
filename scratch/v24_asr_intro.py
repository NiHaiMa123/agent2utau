"""定位 6 个 recall <40% 的句子：
  p0,p1,p2,p3 (开头四句) 和 p7,p29 (等清晨)
猜测：
  - p0-p3 在 18.7-30.8s，可能被 ASR 的开头幻觉「作词作曲李宗盛」吃掉
  - p7/p29「等清晨」是 3 字短句，可能太短
先验证 p0-p3 是否因为幻觉段导致时间错位。
"""
import sys, json, io, os, re
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap
from faster_whisper import WhisperModel

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)

snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
md = sorted((snap/'snapshots').iterdir())[-1]
m = WhisperModel(str(md), device='cpu', compute_type='int8')

wav = NEW/'render'/'vocal_v23_vocal.wav'
segs,_ = m.transcribe(str(wav), language='zh', beam_size=5, vad_filter=False)
print('渲染音频的 ASR 段（前 8 个，含时间）:')
for i,s in enumerate(segs):
    if i>=8: break
    print(f'  {s.start:7.2f}-{s.end:7.2f}  {s.text}')

print('\n谱面开头四句的时间:')
for pi in (0,1,2,3,7):
    part = doc['voice_parts'][pi]
    notes=[n for n in part['notes'] if n['lyric'] not in ('AP','SP')]
    a = tm.tick_to_ms(part['position']+notes[0]['position'])/1000
    b = tm.tick_to_ms(part['position']+notes[-1]['position']+notes[-1]['duration'])/1000
    txt = ''.join(n['lyric'] for n in notes if n['lyric']!='+')
    print(f'  p{pi}: {a:.2f}-{b:.2f}s  「{txt}」')

# 裁剪开头 20-31s 单独识别，排除幻觉
import soundfile as sf
a, sr = sf.read(str(wav), dtype='float32')
if a.ndim>1: a=a.mean(1)
clip = a[int(20*sr):int(31*sr)]
tmp = NEW/'_asr_clip.wav'
sf.write(str(tmp), clip, sr)
segs2,_ = m.transcribe(str(tmp), language='zh', beam_size=5, vad_filter=False)
print('\n单独识别 20-31s:')
for s in segs2:
    print(f'  {s.start+20:7.2f}-{s.end+20:7.2f}  {s.text}')
