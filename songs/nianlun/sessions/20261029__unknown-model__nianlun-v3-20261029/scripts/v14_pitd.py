"""修音符边界跳变：相邻音符的 PITD 在边界处必须连续。

问题：part0 在 ticks 1110/2355/2990/3705/4200 处 |dy| 约 450c，
      因为前一音符结束时偏移 -269c，后一音符开始时偏移 +182c。

根因：每个音符的起始/结束偏移独立设计，未保证跨音符连续。
修正：所有音符的边界偏移统一为 0（即边界处贴着音符音高），
      滑入/滑出只发生在音符内部、不到达边界。
"""
import sys, json, io, math
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
RES=int(doc.get('resolution',480)); BPM=float((doc.get('tempos') or [{'bpm':120}])[0]['bpm'])
TICK_MS=60000.0/(BPM*RES); STEP=max(2,int(round(12.0/TICK_MS)))

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
    """边界一律为 0；动作在音符内部完成，两端用缓动回到 0。"""
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)

    # 字头深度（音乐判断）
    if li is not None and abs(li)>=7:  hd=-150 if li>0 else 130
    elif li is not None and abs(li)>=4:hd=-95 if li>0 else 85
    elif pos=='first':                 hd=-70
    elif li==0:                        hd=-55
    else:                              hd=-35 if k%2==0 else -22
    if reg=='high': hd*=0.85
    # 字尾深度
    if lo is not None and abs(lo)>=7:  td=-140 if lo>0 else 120
    elif lo is not None and abs(lo)>=4:td=-90 if lo>0 else 80
    elif pos=='last':                  td=-110
    else:                              td=-45 if k%2==0 else -28
    if reg=='high': td*=0.85

    hdur=min(0.085,max(0.045,0.16*d))
    tdur=min(0.075,max(0.040,0.14*d))
    # 保证字头+字尾不占满整个音符，中间留出主体
    if hdur+tdur > 0.65*d:
        scale=0.65*d/(hdur+tdur); hdur*=scale; tdur*=scale

    pts=[]
    # --- 字头：0 -> hd -> 0（两端为 0，保证边界连续）---
    n1=max(5,int(hdur/d*100)+2)
    for i in range(n1):
        f=i/(n1-1)
        amp = math.sin(math.pi*f)          # 0..1..0
        pts.append((hdur/d*f, hd*amp))
    # --- 字腹 ---
    b0=hdur/d; b1=1.0-tdur/d
    if b1-b0<0.25: b0,b1=0.32,0.68
    if mt=='vib':   amp=155.0 if d>=0.52 else 105.0
    elif mt=='slow':amp=95.0 if d>=0.52 else 46.0
    else:           amp=22.0
    if reg=='high': amp*=0.85
    cycles=1.0 if d<0.52 else 2.0
    nb=max(7,int((b1-b0)/0.055)+1)
    for i in range(nb):
        u=b0+(b1-b0)*i/(nb-1)
        ph=(u-b0)/max(b1-b0,1e-6)
        # 两端为 0 的双极起伏
        pts.append((u, -amp*math.sin(math.pi*ph)*math.sin(2*math.pi*cycles*ph)*0.5))
    # --- 字尾：0 -> td -> 0 ---
    n2=max(5,int(tdur/d*100)+2)
    for i in range(n2):
        f=i/(n2-1)
        amp=math.sin(math.pi*f)
        pts.append((1.0-tdur/d+tdur/d*f, td*amp))

    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<2e-4: continue
        out.append((float(np.clip(u,0,1)), float(v)))
    # 强制两端为 0
    out[0]=(0.0, 0.0); out[-1]=(1.0, 0.0)
    return out

allvals=[]
for pi,part in enumerate(doc['voice_parts']):
    notes=parts[pi]
    xs=list(range(0,int(part['duration'])+1,STEP))
    if xs[-1]!=int(part['duration']): xs.append(int(part['duration']))
    ys=np.zeros(len(xs))
    covered=np.zeros(len(xs),bool)
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
            covered[j]=True
    # 软限幅（进一步保证无悬崖）
    for _ in range(2):
        for j in range(1,len(ys)):
            dv=ys[j]-ys[j-1]
            if abs(dv)>90: ys[j]=ys[j-1]+math.copysign(90,dv)
        for j in range(len(ys)-2,-1,-1):
            dv=ys[j]-ys[j+1]
            if abs(dv)>90: ys[j]=ys[j+1]+math.copysign(90,dv)
    ys=ys-float(np.median(ys[covered])) if covered.any() else ys
    yi=[int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves']=[c for c in part.get('curves',[]) if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd',xs=[int(x) for x in xs],ys=yi))
    allvals.extend(yi)

allv=np.array(allvals,float)
dy=np.abs(np.diff(allv))
print(f'points {len(allv)}')
print(f'  p50 {np.percentile(allv,50):+.0f}  p99 {np.percentile(allv,99):+.0f}  |y|>200 {(np.abs(allv)>200).mean():.2%}')
print(f'  |dy| median {np.median(dy):.1f}  p99 {np.percentile(dy,99):.1f}  max {dy.max():.0f}  >200: {(dy>200).sum()}')

COLORS=['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']
MIX=dict(cl01=50,cl05=50)
clr=doc['expressions'].setdefault('clr',{})
clr.update(dict(name=clr.get('name','voice color'),abbr='clr',type='Options',
                min=0,max=len(COLORS)-1,default_value=0,options=COLORS[:]))
doc['tracks'][0]['voice_color_names']=COLORS[:]
for part in doc['voice_parts']:
    for note in part['notes']:
        pe=[x for x in (note.get('phoneme_expressions') or []) if x.get('abbr')!='clr']
        for j in range(8): pe.append(dict(index=j,abbr='clr',value=0))
        note['phoneme_expressions']=pe
for abbr in ('cl01','cl02','cl03','cl04','cl05'):
    doc['expressions'].setdefault(abbr,dict(name=f'{abbr} mix',abbr=abbr,type='Curve',min=0,max=100,default_value=0))
for part in doc['voice_parts']:
    part['curves']=[c for c in part.get('curves',[]) if not c['abbr'].startswith('cl')]
    dur=int(part['duration'])
    for a_,v_ in MIX.items():
        part['curves'].append(dict(abbr=a_,xs=[0,dur],ys=[v_,v_]))

OUT=NEW/'score'/'v14_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
