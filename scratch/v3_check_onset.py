"""检查辅音/起音是否被吞：对比三个版本在「字头 30ms」的能量上升速率。"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))

def env(p):
    a,sr = sf.read(str(p), dtype='float32')
    if a.ndim>1: a=a.mean(1)
    w=int(0.005*sr); n=len(a)//w
    e=np.sqrt((a[:n*w].reshape(n,w)**2).mean(1))
    return 20*np.log10(np.maximum(e,1e-9)), (np.arange(n)+0.5)*0.005

data = {}
for k,p in [('source', NEW/'inputs/stems/vocals.wav'),
            ('v2', V2/'render'/'vocal_vocal.wav'),
            ('v3', NEW/'render'/'vocal_v3h_vocal.wav')]:
    if p.exists(): data[k] = env(p)

print('字头能量上升速率（dB / 30ms），越高＝起音越分明')
for k,(db,t) in data.items():
    rises=[]
    for ph in W['phrases']:
        for w in ph['words']:
            a=w['start']
            i0=int(a/0.005); i1=i0+6   # 30ms
            if i1>=len(db): continue
            seg=db[max(i0-2,0):i1]
            if len(seg)<3: continue
            rises.append(float(seg.max()-seg.min()))
    rises=np.array(rises)
    print(f'  {k:8s} median {np.median(rises):5.1f}dB  p90 {np.percentile(rises,90):5.1f}dB  '
          f'(n={len(rises)})')

print('\n字间静默占比（字尾 40ms 内低于阈值的比例）')
for k,(db,t) in data.items():
    frac=[]
    for ph in W['phrases']:
        for w in ph['words']:
            b=w['end']
            i=int(b/0.005)-8
            if i<0 or i+8>=len(db): continue
            frac.append(float((db[i:i+8] < (np.median(db)+ -25)).mean()))
    frac=np.array(frac)
    print(f'  {k:8s} median {np.median(frac):.2f}  (n={len(frac)})')
