"""音色候选对比：几个 CLR 单色 + 混合，测频谱与源人声的距离，找最接近的方向。

注意：这不是「和原唱比」——原唱是张碧晨，我们用的是泠鸢声库。
目标是找到「泠鸢音色中最适合这首歌气质、且不显薄的」。
所以指标用「相对源人声的谱形相似度」作参考，最终仍要人耳判断。
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
T = NEW/'_clrtest2'; T.mkdir(exist_ok=True)
COLORS=['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']

CANDS = [
    ('normal100',      dict(cl03=100)),
    ('classic100',     dict(cl05=100)),
    ('normal70_cl30',  dict(cl03=70, cl05=30)),
    ('bright50_cl50',  dict(cl01=50, cl05=50)),
    ('mix_A_26-6-34-34', dict(cl01=26, cl02=6, cl03=34, cl05=34)),
]

def render(mix, tag):
    d = load_ustx(NEW/'compiled'/'project.ustx')   # clean compiled (no curves except pitd)
    for part in d['voice_parts']:
        part['curves']=[c for c in part.get('curves',[]) if not c['abbr'].startswith('cl')]
    dur_by_part=[int(p['duration']) for p in d['voice_parts']]
    for mi,(abbr,val) in enumerate(mix.items()):
        for part,dur in zip(d['voice_parts'],dur_by_part):
            part['curves'].append(dict(abbr=abbr,xs=[0,dur],ys=[val,val]))
    p=T/f'{tag}.ustx'; save_ustx(d,p)
    r=run_bridge(cfg,['render','--project',str(p.resolve()),'--out',str(T/f'{tag}.wav'),'--timeout','900'])
    print(f'  {tag}: ok={r.get("ok")}')
    return T/f'{tag}_vocal.wav'

def bands(p, t0=69.5, t1=74.0):
    x,sr=sf.read(str(p),dtype='float32')
    if x.ndim>1: x=x.mean(1)
    x=x[int(t0*sr):int(t1*sr)]
    n=8192;hop=4096
    fr=[x[i:i+n]*np.hanning(n) for i in range(0,max(1,len(x)-n),hop)]
    if not fr: return None
    S=np.mean([np.abs(np.fft.rfft(f)) for f in fr],axis=0)
    f=np.fft.rfftfreq(n,1/sr)
    return np.array([20*np.log10(S[(f>=fc/2**0.1666)&(f<fc*2**0.1666)].mean()+1e-12)
                     for fc in [125,250,500,1000,2000,4000,8000]])

res={}
for tag,mix in CANDS:
    w=render(mix,tag)
    if w.exists():
        b=bands(w)
        if b is not None: res[tag]=b

# source reference (same window)
src=bands(NEW/'inputs'/'stems'/'vocals.wav')
print('\n1/3-octave bands:')
print(f'  {"variant":20s} ' + ' '.join(f'{fc:>7}' for fc in [125,250,500,1000,2000,4000,8000]))
if src is not None:
    print(f'  {"SOURCE(张碧晨)":20s} ' + ' '.join(f'{v:7.1f}' for v in src))
for k,v in res.items():
    print(f'  {k:20s} ' + ' '.join(f'{x:7.1f}' for x in v))

if src is not None:
    print('\n距源人声的谱形 RMS 距离（越小越接近源音色）:')
    for k,v in sorted(res.items(), key=lambda kv: np.sqrt(((kv[1]-src)**2).mean())):
        print(f'  {k:20s} {np.sqrt(((v-src)**2).mean()):6.2f} dB')
