"""v13：修正深挖——这是图审发现的真实音乐错误。

问题（v12 图审）：
  p0:f0:v0「圆」在 18.75s 从 57 跌到 51.4，深度 -560c（5 个半音），
  持续 ~100ms 后回升。这是巨大的 V 形下陷，音乐上完全错误。

根因：我误用了白烁的分位统计。
  白烁 p1=-513c 是**全体点**的第 1 百分位 —— 只有极少数点这么深。
  白烁字头**中位数仅 -5c**，p10 才 -153c。
  我却在每个字的字头都加 -560c 的深挖 → 每个字都是深 V。

修正原则（回归白烁的真实分布）：
  1) 绝大多数字：字头浅滑入（-40 ~ -90c）
  2) 只有特定音乐条件才深：句首、大跳、同音重咬
  3) 最深不超过 -220c（白烁字头 p10 的量级，不是极值）
  4) 深段必须短促（60-90ms）
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

def seg(u0,u1,depth,d,ramp=0.45):
    span=u1-u0
    if span<=0: return []
    n=max(5,int(span*d/0.010)+1); pts=[]
    for i in range(n):
        f=i/(n-1)
        if f<ramp: a=q5(f/ramp)
        elif f<1-ramp: a=1.0
        else: a=1.0-q5((f-(1-ramp))/ramp)
        pts.append((u0+span*f, depth*a))
    return pts

def design(n,k,cnt,prev,next_):
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)

    # ---- 字头：以自然浅滑入为原则（音乐判断优先于统计拟合）----
    # 一个音节从某音开始时不应明显低于该音；自然滑入一般 30-110c。
    # 只有大跳才需要更深的承接，且不超过 150c。
    if li is not None and abs(li) >= 7:  hd = -150 if li > 0 else 130
    elif li is not None and abs(li) >= 4: hd = -95 if li > 0 else 85
    elif pos == 'first':                hd = -70
    elif li == 0:                       hd = -55
    else:                               hd = -35 if (k % 2 == 0) else -22
    if reg=='high': hd*=0.85
    hdur=min(0.085,max(0.045,0.16*d))
    pts=seg(0.0,hdur/d,hd,d,0.5)

    # ---- 字腹 ----
    b0=min(0.20,hdur/d); b1=1.0-min(0.18,(min(0.075,max(0.040,0.14*d)))/d)
    if b1-b0<0.30: b0,b1=0.32,0.68
    if mt=='vib':   amp=155.0 if d>=0.52 else 105.0
    elif mt=='slow':amp=95.0 if d>=0.52 else 46.0
    else:           amp=22.0
    if reg=='high': amp*=0.85
    cycles=1.0 if d<0.52 else 2.0
    nb=max(7,int((b1-b0)/0.055)+1)
    for i in range(nb):
        u=b0+(b1-b0)*i/(nb-1)
        ph=(u-b0)/max(b1-b0,1e-6)
        pts.append((u, -amp*math.sin(2*math.pi*cycles*ph)*0.5))

    # ---- 字尾：自然释放，多数轻微向下 ----
    if lo is not None and abs(lo) >= 7:  td = -140 if lo > 0 else 120
    elif lo is not None and abs(lo) >= 4: td = -90 if lo > 0 else 80
    elif pos == 'last':                  td = -110
    else:                                td = -45 if (k % 2 == 0) else -28
    if reg=='high': td*=0.85
    tdur=min(0.075,max(0.040,0.14*d))
    pts+=seg(1.0-tdur/d,1.0,td,d,0.5)

    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<2e-4: continue
        out.append((float(np.clip(u,0,1)), float(np.clip(v,-1200,1200))))
    return out

allvals=[]
for pi,part in enumerate(doc['voice_parts']):
    notes=parts[pi]
    xs=list(range(0,int(part['duration'])+1,STEP))
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
    for _ in range(3):
        for j in range(1,len(ys)):
            dv=ys[j]-ys[j-1]
            if abs(dv)>95: ys[j]=ys[j-1]+math.copysign(95,dv)
        for j in range(len(ys)-2,-1,-1):
            dv=ys[j]-ys[j+1]
            if abs(dv)>95: ys[j]=ys[j+1]+math.copysign(95,dv)
    ys=ys-float(np.median(ys))
    yi=[int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves']=[c for c in part.get('curves',[]) if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd',xs=[int(x) for x in xs],ys=yi))
    allvals.extend(yi)

allv=np.array(allvals,float)
ref={1:-513,5:-225,10:-163,25:-52,50:-5,75:16,90:52,95:119,99:410}
print(f'points {len(allv)}  mean|y| {np.mean(np.abs(allv)):.1f} (白烁69.2)  |y|<50 {(np.abs(allv)<50).mean():.1%} (65.4%)  std {np.std(allv):.1f} (124.7)')
print('      v13     白烁')
for q in (1,5,10,25,50,75,90,95,99):
    print(f'p{q:2d}: {np.percentile(allv,q):+7.0f}  {ref[q]:+7.0f}')
print(f'|y|>200 {(np.abs(allv)>200).mean():.2%}  (8.8%)')
dy=np.abs(np.diff(allv))
print(f'|dy| median {np.median(dy):.1f} max {dy.max():.0f}  >400: {(dy>400).sum()}')

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

OUT=NEW/'score'/'v13_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
