"""v18：消除字尾尖刺，但保留大跳的到达锐度。

诊断（349 单元全扫）：
  40ms 窗口内 >300c 的有 34 个单元（9.7%），>500c 的 6 个。
  最严重的都在字尾（人/痕/根/纹/盛/份/笨/稳/认/恒）——
  因为字尾释放段只有 40-75ms，却有 90-140c 幅度，变化率过高。

同时：白烁的跳变中位 53ms（比我的 98ms 更锐），所以不能一味加长。
正确做法：
  1) 字尾释放：时间加长到 90-150ms，幅度降到 60-100c
  2) 音符间大跳：保留较锐的到达（约 50-70ms），但必须是单调斜坡，不能先反向再跳
  3) 检测并消除「反向预兆」：滑入前不要先反向走
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
TICK_MS=60000.0/(BPM*RES); STEP=5   # 原生网格

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

    # --- 字头：浅，且**方向与音程同向**（上行从下入、下行从上入），避免反向预兆 ---
    if li is not None and abs(li)>=7:  hd=-120 if li>0 else 105
    elif li is not None and abs(li)>=4:hd=-80 if li>0 else 70
    elif pos=='first':                 hd=-60
    elif li==0:                        hd=-50
    else:                              hd=-30 if (li is not None and li>0) else 26
    if reg=='high': hd*=0.85
    hdur=min(0.11, max(0.060, 0.20*d))     # 加长，降低变化率

    # --- 字尾：明显加长、降幅 ---
    if lo is not None and abs(lo)>=7:  td=-95 if lo>0 else 85
    elif lo is not None and abs(lo)>=4:td=-70 if lo>0 else 62
    elif pos=='last':                  td=-85
    else:                              td=-38 if (lo is not None and lo>0) else 34
    if reg=='high': td*=0.85
    tdur=min(0.15, max(0.090, 0.26*d))     # 90-150ms

    if hdur+tdur > 0.72*d:
        sc=0.72*d/(hdur+tdur); hdur*=sc; tdur*=sc

    pts=[]
    # 字头 0 -> hd -> 0
    n1=max(6,int(hdur/d*120)+2)
    for i in range(n1):
        f=i/(n1-1)
        pts.append((hdur/d*f, hd*math.sin(math.pi*f)))
    # 字腹
    b0=hdur/d; b1=1.0-tdur/d
    if b1-b0<0.22: b0,b1=0.32,0.68
    if mt=='vib':   amp=150.0 if d>=0.52 else 100.0
    elif mt=='slow':amp=92.0 if d>=0.52 else 45.0
    else:           amp=20.0
    if reg=='high': amp*=0.85
    cycles=1.0 if d<0.52 else 2.0
    nb=max(8,int((b1-b0)/0.05)+1)
    for i in range(nb):
        u=b0+(b1-b0)*i/(nb-1)
        ph=(u-b0)/max(b1-b0,1e-6)
        pts.append((u, -amp*math.sin(math.pi*ph)*math.sin(2*math.pi*cycles*ph)*0.5))
    # 字尾 0 -> td -> 0
    n2=max(6,int(tdur/d*120)+2)
    for i in range(n2):
        f=i/(n2-1)
        pts.append((1.0-tdur/d+tdur/d*f, td*math.sin(math.pi*f)))

    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<2e-4: continue
        out.append((float(np.clip(u,0,1)), float(v)))
    out[0]=(0.0,0.0); out[-1]=(1.0,0.0)
    return out

allvals=[]
for pi,part in enumerate(doc['voice_parts']):
    notes=parts[pi]
    xs=list(range(0,int(part['duration'])+1,STEP))
    if xs[-1]!=int(part['duration']): xs.append(int(part['duration']))
    ys=np.zeros(len(xs)); cov=np.zeros(len(xs),bool)
    for ni,n in enumerate(notes):
        nodes=design(n,ni,len(notes),
                     notes[ni-1]['tone'] if ni>0 else None,
                     notes[ni+1]['tone'] if ni+1<len(notes) else None)
        us=np.array([x[0] for x in nodes]); vs=np.array([x[1] for x in nodes])
        for j,x in enumerate(xs):
            t_abs=tm.tick_to_ms(part['position']+x)/1000
            if t_abs<n['a'] or t_abs>n['b']: continue
            u=(t_abs-n['a'])/max(n['b']-n['a'],1e-6)
            ys[j]=float(np.interp(u,us,vs)); cov[j]=True
    for _ in range(2):
        for j in range(1,len(ys)):
            dv=ys[j]-ys[j-1]
            if abs(dv)>45: ys[j]=ys[j-1]+math.copysign(45,dv)
        for j in range(len(ys)-2,-1,-1):
            dv=ys[j]-ys[j+1]
            if abs(dv)>45: ys[j]=ys[j+1]+math.copysign(45,dv)
    if cov.any(): ys=ys-float(np.median(ys[cov]))
    yi=[int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves']=[c for c in part['curves'] if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd',xs=[int(x) for x in xs],ys=yi))
    allvals.extend(yi)

allv=np.array(allvals,float)
dy=np.abs(np.diff(allv))
print(f'points {len(allv)}')
print(f'  p50 {np.percentile(allv,50):+.0f}  p99 {np.percentile(allv,99):+.0f}  |y|>200 {(np.abs(allv)>200).mean():.2%}')
print(f'  |dy| median {np.median(dy):.1f} max {dy.max():.0f}  >45: {(dy>45).sum()}')

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
    part['curves']=[c for c in part['curves'] if not c['abbr'].startswith('cl')]
    dur=int(part['duration'])
    for a_,v_ in MIX.items():
        part['curves'].append(dict(abbr=a_,xs=[0,dur],ys=[v_,v_]))

OUT=NEW/'score'/'v18_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
