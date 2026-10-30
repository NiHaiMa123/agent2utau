"""v6：按白烁的强度重画 PITD（我之前的幅度只有其 1/4）。

白烁实测（雨爱 2 个 part / 15763 点）：
  |y|<50c 占 65.4%
  mean|y| 69.2c，std 124.7c
  字头 p10 -153c，字腹 p10 -175c、std 160c，字尾 p10 -220c、std 166c

我的 v5：|y|<50 占 92%，mean|y| 21.6c，std 31c  → 太平、太小

修正：整体放大，并让字腹也有真实运动（不是只有字头字尾动）。
"""
import sys, json, io, math
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap, sha256

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
RES=int(doc.get('resolution',480)); BPM=float((doc.get('tempos') or [{'bpm':120}])[0]['bpm'])
TICK_MS=60000.0/(BPM*RES)
STEP_TICKS=max(2,int(round(16.0/TICK_MS)))
print(f'step {STEP_TICKS} ticks = {STEP_TICKS*TICK_MS:.1f}ms')

f0=np.load(NEW/'inputs/fcpe.npz'); f0r=np.load(NEW/'inputs/rmvpe.npz')
ft=f0['times'].astype(float); ff=f0['f0_hz'].astype(float); fv=f0['voiced'].astype(bool)
rt=f0r['times'].astype(float); rf=f0r['f0_hz'].astype(float); rv=f0r['voiced'].astype(bool)
def C(a): return 6900.0+1200.0*np.log2(np.maximum(a,1e-6)/440.0)
CF=np.where(fv,C(ff),np.nan); CR=np.where(rv,C(rf),np.nan)
AG=np.isfinite(CF)&np.isfinite(CR)&(np.abs(CF-CR)<=100)
SRC=np.where(AG,(CF+CR)/2,np.nan)
def motion(a,b):
    m=(ft>=a)&(ft<b)&np.isfinite(SRC)
    if m.sum()<8: return 'unk'
    cc=SRC[m]
    if float(cc.max()-cc.min())<60: return 'flat'
    detr=cc-np.polyval(np.polyfit(ft[m]-a,cc,1),ft[m]-a)
    zc=int(np.sum(np.diff(np.sign(detr))!=0))
    if m.sum()>=20:
        fs=1/0.01
        sp=np.abs(np.fft.rfft(detr*np.hanning(len(detr))))
        fr=np.fft.rfftfreq(len(detr),1/fs); lo=(fr>=0.8)&(fr<=12)
        if lo.any() and float(fr[lo][np.argmax(sp[lo])])>=3.5 and zc>=3: return 'vib'
    return 'slow'

parts=[]
for part in doc['voice_parts']:
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,dur=b-a,tone=n['tone'],lyric=n['lyric']))
    ns.sort(key=lambda x:x['a']); parts.append(ns)

def q5(u): return u*u*u*(10+u*(-15+6*u))

def design(n,k,cnt,prev,next_):
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)

    # ---- 字头滑入（白烁 p10 ≈ -150c）----
    if pos=='first': hd=-190
    elif li is not None and li>=5: hd=-150
    elif li is not None and li<=-5: hd=+140
    elif li==0: hd=-95
    else: hd=-70
    hf=min(0.20, 0.6*(0.10/max(d,0.10)))

    # ---- 字腹（白烁 std ≈ 160c；长字更大）----
    if d<0.30: ba=45.0
    elif d<0.52: ba=85.0
    else: ba=140.0
    if mt=='flat': ba*=0.55
    elif mt=='vib': ba*=1.15
    if reg=='high': ba*=0.85
    cycles = 1.0 if d<0.52 else 2.0

    # ---- 字尾滑出（白烁 p10 ≈ -220c）----
    if pos=='last': td=-170
    elif lo is not None and lo>=5: td=-140
    elif lo is not None and lo<=-5: td=+130
    else: td=-55
    tf=min(0.24, 0.55*(0.11/max(d,0.11)))

    pts=[]
    # 字头
    nh=3 if d>0.28 else 2
    for i in range(nh):
        u=hf*(i/(nh-1)) if nh>1 else 0.0
        pts.append((u, hd*(1-q5(i/max(nh-1,1)))))
    # 字腹：正弦起伏（1 或 2 个）
    b0=hf; b1=1.0-tf
    if b1-b0<0.12: b0=0.28; b1=0.72
    nb=max(4,int((b1-b0)/0.10)+1)
    for i in range(nb):
        u=b0+(b1-b0)*i/(nb-1)
        ph=(u-b0)/max(b1-b0,1e-6)
        # 起伏：谷在两端，峰在中
        val=-ba*math.sin(math.pi*cycles*ph)**2
        pts.append((u,val))
    # 字尾
    nt=3 if d>0.28 else 2
    for i in range(1,nt+1):
        u=1.0-tf*(1-i/nt)
        pts.append((u, td*q5(i/nt)))
    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<1e-4: continue
        out.append((float(np.clip(u,0,1)),float(v)))
    return out

stats=dict(pts=0, absmean=[], zfrac=[], std=[])
for pi,part in enumerate(doc['voice_parts']):
    notes=parts[pi]
    xs=list(range(0,int(part['duration'])+1,STEP_TICKS))
    if xs[-1]!=int(part['duration']): xs.append(int(part['duration']))
    ys=np.zeros(len(xs))
    for ni,n in enumerate(notes):
        nodes=design(n,ni,len(notes),
                     notes[ni-1]['tone'] if ni>0 else None,
                     notes[ni+1]['tone'] if ni+1<len(notes) else None)
        us=np.array([x[0] for x in nodes]); vs=np.array([x[1] for x in nodes])
        for j,x in enumerate(xs):
            t_abs=tm.tick_to_ms(part['position']+x)/1000
            if t_abs<n['a'] or t_abs>n['b']: continue
            u=(t_abs-n['a'])/max(n['b']-n['a'],1e-6)
            ys[j]=float(np.interp(u,us,vs))
    yi=[int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves']=[c for c in part.get('curves',[]) if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd',xs=[int(x) for x in xs],ys=yi))
    stats['pts']+=len(xs)
    arr=np.array(yi)
    stats['absmean'].append(float(np.mean(np.abs(arr))))
    stats['zfrac'].append(float((np.abs(arr)<50).mean()))
    stats['std'].append(float(np.std(arr)))

print(f"points {stats['pts']} ({stats['pts']/51:.0f}/part)")
print(f"mean|y| median {np.median(stats['absmean']):.1f}c   (白烁 69.2)")
print(f"|y|<50 fraction median {np.median(stats['zfrac']):.1%}   (白烁 65.4%)")
print(f"std median {np.median(stats['std']):.1f}c   (白烁 124.7)")

from agent2utau.openutau.ustx import save_ustx
OUT=NEW/'score'/'v6_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
