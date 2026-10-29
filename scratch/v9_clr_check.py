"""验证音色层是否真的生效：对比「有 clNN 混合」与「无混合」的渲染频谱。"""
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
TAG = NEW/'_clrcheck'; TAG.mkdir(exist_ok=True)

def render_variant(strip_cl, tag):
    d = load_ustx(NEW/'compiled'/'project_v9.ustx')
    if strip_cl:
        for part in d['voice_parts']:
            part['curves']=[c for c in part.get('curves',[]) if not c['abbr'].startswith('cl')]
        for note_pe in []: pass
    p = TAG/f'{tag}.ustx'; save_ustx(d,p)
    out = TAG/f'{tag}.wav'
    r = run_bridge(cfg,['render','--project',str(p.resolve()),'--out',str(out.resolve()),'--timeout','900'])
    print(f'  {tag}: ok={r.get("ok")}')
    return out

print('rendering variants...')
a = render_variant(False, 'with_cl')
b = render_variant(True,  'no_cl')

def bands(p, t0=69.5, t1=74.0):
    x,sr = sf.read(str(p), dtype='float32')
    if x.ndim>1: x=x.mean(1)
    x = x[int(t0*sr):int(t1*sr)]
    n=8192; hop=4096
    fr=[x[i:i+n]*np.hanning(n) for i in range(0,max(1,len(x)-n),hop)]
    if not fr: return None
    S=np.mean([np.abs(np.fft.rfft(f)) for f in fr],axis=0)
    f=np.fft.rfftfreq(n,1/sr)
    out=[]
    for fc in [125,250,500,1000,2000,4000,8000]:
        m=(f>=fc/2**0.1666)&(f<fc*2**0.1666)
        out.append(20*np.log10(S[m].mean()+1e-12) if m.sum() else -120)
    return np.array(out)

sa=bands(a); sb=bands(b)
if sa is not None and sb is not None:
    print('\n1/3-octave bands (125..8000 Hz):')
    print('  with_cl: ' + ' '.join(f'{v:6.1f}' for v in sa))
    print('  no_cl  : ' + ' '.join(f'{v:6.1f}' for v in sb))
    d=sa-sb
    print('  diff   : ' + ' '.join(f'{v:+6.1f}' for v in d))
    print(f'\nRMS spectral difference: {np.sqrt((d**2).mean()):.2f} dB')
    print(f'=> {"CLR/clNN IS consuming" if np.sqrt((d**2).mean())>0.8 else "difference small - check whether clNN is consumed"}')
