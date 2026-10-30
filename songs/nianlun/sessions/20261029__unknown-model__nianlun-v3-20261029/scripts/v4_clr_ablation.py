"""受控验证：CLR 音色是否真的改变输出。

做法：取同一小段（p16 前 4 秒），分别用 clr=0(Bright) / clr=3(Normal) / clr=4(Whisper) 渲染，
比较 1/3 倍频程谱形与 MFCC 距离。如果谱形有系统差异，说明 CLR 生效。
"""
import sys, json, io, shutil
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
TMP = NEW/'_clr_test'; TMP.mkdir(exist_ok=True)
cfg = load_config()
COLORS = ['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']

base = load_ustx(NEW/'compiled'/'project.ustx')

def make(color_idx, tag):
    d = load_ustx(NEW/'compiled'/'project.ustx')
    clr = d['expressions'].setdefault('clr', {})
    clr.update(dict(name=clr.get('name','voice color'), abbr='clr', type='Options',
                    min=0, max=len(COLORS)-1, default_value=color_idx, options=COLORS[:]))
    d['tracks'][0]['voice_color_names'] = COLORS[:]
    for part in d['voice_parts']:
        for note in part['notes']:
            pe=[x for x in (note.get('phoneme_expressions') or []) if x.get('abbr')!='clr']
            for j in range(8): pe.append(dict(index=j, abbr='clr', value=color_idx))
            note['phoneme_expressions']=pe
    p = TMP/f'{tag}.ustx'
    save_ustx(d, p)
    out = TMP/f'{tag}.wav'
    r = run_bridge(cfg, ['render','--project',str(p.resolve()),'--out',str(out.resolve()),'--timeout','600'])
    print(f'  {tag}: ok={r.get("ok")} files={len(r.get("files",[]))}')
    if not r.get('ok'): print('   ', str(r.get('errors'))[:200])
    return out

results={}
for idx, name in [(0,'Bright'), (3,'Normal'), (4,'Whisper')]:
    w = make(idx, name)
    if w.exists(): results[name]=w

# ---- spectral comparison over a singing region ----
def spec(p, t0=69.5, t1=73.5):
    a,sr = sf.read(str(p), dtype='float32')
    if a.ndim>1: a=a.mean(1)
    i0,i1 = int(t0*sr), int(t1*sr)
    x = a[i0:i1]
    # average magnitude spectrum in 1/3-octave bands
    n=8192; hop=4096
    frames=[x[i:i+n]*np.hanning(n) for i in range(0, max(1,len(x)-n), hop)]
    if not frames: return None
    S=np.mean([np.abs(np.fft.rfft(f)) for f in frames],axis=0)
    fr=np.fft.rfftfreq(n,1/sr)
    bands=[]
    for fc in [125,250,500,1000,2000,4000,8000]:
        m=(fr>=fc/2**0.1666)&(fr<fc*2**0.1666)
        if m.sum(): bands.append(20*np.log10(S[m].mean()+1e-12))
        else: bands.append(-120)
    return np.array(bands)

print('\n=== 1/3-octave band levels (125..8000 Hz) ===')
sp={}
for k,p in results.items():
    s=spec(p); sp[k]=s
    print(f'  {k:8s}: ' + ' '.join(f'{v:6.1f}' for v in s))

if len(sp)>=2:
    ks=list(sp)
    print('\n=== pairwise spectral distance (dB RMS) ===')
    for i in range(len(ks)):
        for j in range(i+1,len(ks)):
            d=sp[ks[i]]-sp[ks[j]]
            print(f'  {ks[i]:8s} vs {ks[j]:8s}: {np.sqrt((d**2).mean()):5.2f} dB   bands: '+' '.join(f'{v:+.1f}' for v in d))
