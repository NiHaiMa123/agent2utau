"""厘清 +20ms 改善的真实机制。

观测：offset +20ms 使
  辅音占比 26.1% -> 26.5%（+0.4pp）
  辅音中位 148 -> 150ms（+2ms）
  元音中位 407 -> 404ms（-3ms）
  recall 56.0% -> 57.4%（+1.4pp）

机制假说：
  H1) offset 正位移把元音起点后推，使「辅音到元音的过渡」更清晰（起音更分明）
  H2) offset 改变了音素网格对齐，间接影响了声学输入
  H3) +1.4pp 虽可重复，但样本量小、可能不具普遍意义

检验 H1：看「字头能量上升速率」是否改善（这是起音分明的直接指标）。
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
T = NEW/'_vel'
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)

words=[]
for pi,part in enumerate(doc['voice_parts']):
    for n in part['notes']:
        if n['lyric'] in ('AP','SP','+'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        words.append(a)
print(f'唱字起点 {len(words)} 个')

def onset_rise(wav):
    a,sr = sf.read(str(wav), dtype='float32')
    if a.ndim>1: a=a.mean(1)
    w=int(0.005*sr); nb=len(a)//w
    db=20*np.log10(np.maximum(np.sqrt((a[:nb*w].reshape(nb,w)**2).mean(1)),1e-9))
    rises=[]
    for t in words:
        i=int(t/0.005)
        if i<2 or i+6>=len(db): continue
        seg=db[i-2:i+6]
        rises.append(float(seg.max()-seg.min()))
    return np.array(rises)

for label, w in [('baseline', NEW/'render'/'vocal_v23_vocal.wav'),
                 ('+20ms', T/'vowel20_vocal.wav'),
                 ('+35ms', T/'vowel35_vocal.wav')]:
    if not w.is_file(): print(f'{label}: missing'); continue
    r=onset_rise(w)
    print(f'  {label:8s} 字头上升 median {np.median(r):5.1f}dB  p90 {np.percentile(r,90):5.1f}dB')

# 源参考
src = NEW/'inputs'/'stems'/'vocals.wav'
r=onset_rise(src)
print(f'  {"source":8s} 字头上升 median {np.median(r):5.1f}dB  p90 {np.percentile(r,90):5.1f}dB')
