"""v9：修正 v8 的系统性负偏移。

问题：v8 的 p50=-47c, p75=-14c, p95=0c → 整条线被压低约 20-30c，
      而白烁 p50=-5, p75=+16, p95=+52 → 基本居中，略偏正。
原因：我把字头/字尾都设计成负向滑出，累积成系统性偏低。

修正：
  1) 字头的方向由「进入音程」决定：上行→从下方入（负），下行→从上方入（正）
  2) 字尾的方向由「离开音程」决定：下行→向下出（负），上行→向上出（正）
  3) 中性情况交替/对称，使整体中位回到 ~0
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
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)
    hdur=min(0.16,max(0.040,0.30*d))
    tdur=min(0.14,max(0.035,0.26*d))

    # ---- 字头方向由进入音程决定（对称）----
    if pos=='first':
        hd = -560 if reg!='high' else -470        # 句首：从下往上进入
    elif li is not None and li>=5:   hd=-480      # 上行：从下方滑入
    elif li is not None and li<=-5:  hd=+420      # 下行：从上方滑入
    elif li==0:                      hd=-300      # 同音重咬：轻下探
    else:
        # 级进：方向跟随音符相对句内走向（由相邻音程符号决定，互补正负）
        hd = -170 if (li is None or li>0) else 170
    if reg=='high': hd*=0.85

    pts=[]
    nh=5 if hdur>0.07 else 4
    for i in range(nh):
        u=(hdur/d)*(i/(nh-1)) if nh>1 else 0.0
        pts.append((u, hd*(1-q5(i/max(nh-1,1)))))

    # ---- 字腹：围绕 0 起伏（正负交替，净均值 0）----
    b0=min(0.22,hdur/d); b1=1.0-min(0.20,tdur/d)
    if b1-b0<0.22: b0,b1=0.28,0.72
    amp=0.0
    if mt=='vib':   amp=120.0 if d>=0.52 else 80.0
    elif mt=='slow':amp=70.0 if d>=0.52 else 30.0
    else:           amp=14.0
    if reg=='high': amp*=0.85
    cycles=1.0 if d<0.52 else 2.0
    nb=max(5,int((b1-b0)/0.07)+1)
    for i in range(nb):
        u=b0+(b1-b0)*i/(nb-1)
        ph=(u-b0)/max(b1-b0,1e-6)
        pts.append((u, -amp*math.sin(math.pi*cycles*ph)**2))

    # ---- 字尾方向由离开音程决定（对称）----
    if pos=='last':
        td=-500 if reg!='high' else -420
    elif lo is not None and lo>=5:   td=-400      # 下接低音：向下滑出
    elif lo is not None and lo<=-5:  td=+370      # 上接高音：向上滑出
    else:
        td = -150 if (lo is None or lo>0) else 150
    if reg=='high': td*=0.85
    nt=5 if tdur>0.06 else 4
    for i in range(1,nt+1):
        u=1.0-(tdur/d)*(1-i/nt)
        pts.append((u, td*q5(i/nt)))

    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<2e-4: continue
        out.append((float(np.clip(u,0,1)), float(np.clip(v,-1200,1200))))
    return out

st=[]
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
    yi=[int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves']=[c for c in part.get('curves',[]) if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd',xs=[int(x) for x in xs],ys=yi))
    st.extend(yi)

allv=np.array(st,float)
print(f'points {len(allv)}')
print(f'mean|y| {np.mean(np.abs(allv)):.1f}c   (白烁 69.2)')
print(f'|y|<50  {(np.abs(allv)<50).mean():.1%}   (白烁 65.4%)')
print(f'std     {np.std(allv):.1f}c   (白烁 124.7)')
print('\npercentiles:      v9       白烁')
ref={1:-513,5:-225,25:-52,50:-5,75:16,95:119,99:410}
for q in (1,5,25,50,75,95,99):
    print(f'  p{q:2d}: {np.percentile(allv,q):+8.0f}   {ref[q]:+8.0f}')
print(f'  |y|>200: {(np.abs(allv)>200).mean():.1%}   (白烁 8.8%)')

COLORS=['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']
MIX=dict(cl01=26,cl02=6,cl03=34,cl05=34)
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

OUT=NEW/'score'/'v9_score.ustx'
save_ustx(doc,OUT)
print(f'\nwrote {OUT}')
