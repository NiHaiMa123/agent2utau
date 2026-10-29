import sys, json, io, re, os
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

print('=== 字头起音上升速率 (dB/30ms) ===')
for k,p in [('source', NEW/'inputs/stems/vocals.wav'),
            ('v2', V2/'render'/'vocal_vocal.wav'),
            ('v3i(无起音)', NEW/'render'/'vocal_v3h_vocal.wav'),
            ('v3k(有起音)', NEW/'render'/'vocal_v3k_vocal.wav')]:
    if not p.exists(): continue
    db,t = env(p)
    rises=[]
    for ph in W['phrases']:
        for w in ph['words']:
            i0=int(w['start']/0.005); i1=i0+6
            if i1>=len(db): continue
            seg=db[max(i0-2,0):i1]
            if len(seg)>=3: rises.append(float(seg.max()-seg.min()))
    rises=np.array(rises)
    print(f'  {k:12s} median {np.median(rises):5.1f}dB  p90 {np.percentile(rises,90):5.1f}dB')

print('\n=== 动态层次 ===')
for k,p in [('source', NEW/'inputs/stems/vocals.wav'),
            ('v2', V2/'render'/'vocal_vocal.wav'),
            ('v3k', NEW/'render'/'vocal_v3k_vocal.wav')]:
    if not p.exists(): continue
    a,sr=sf.read(str(p),dtype='float32')
    if a.ndim>1: a=a.mean(1)
    w=int(0.02*sr); n=len(a)//w
    e=np.sqrt((a[:n*w].reshape(n,w)**2).mean(1)); dbb=20*np.log10(np.maximum(e,1e-9))
    act=dbb>(np.percentile(dbb,95)-30); ar=dbb[act]
    print(f'  {k:8s} IQR {np.percentile(ar,75)-np.percentile(ar,25):5.1f}dB  peak {np.abs(a).max():.3f}  rms {np.sqrt((a.astype(float)**2).mean()):.4f}')
