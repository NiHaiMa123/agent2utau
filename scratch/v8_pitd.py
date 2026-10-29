"""v8：极端偏移改为「持续段」（白烁实测：|y|>300 的段中位 23ms、p90 125ms、峰值 432c）。

之前 v7 的问题是极端值只有 1-2 个点宽，采样网格抓不到 → std 上不去。
修正：
  - 字头滑入：持续 40-120ms 的深偏移，再平滑回到 0
  - 字尾滑出：持续 40-100ms 的深偏移
  - 大跳换音：在边界处给一段持续偏移（这是白烁最常见的用法：负向 115/157）
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
TICK_MS=60000.0/(BPM*RES); STEP=max(2,int(round(12.0/TICK_MS)))   # 更细：12ms
print(f'step {STEP} ticks = {STEP*TICK_MS:.1f}ms')

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

    # 段时长（秒），白烁实测 23ms 中位 / 125ms p90
    hdur = min(0.16, max(0.040, 0.30*d))
    tdur = min(0.14, max(0.035, 0.26*d))

    # ---- 字头：持续深偏移段 ----
    if pos=='first':       depth=-620
    elif li is not None and li>=5:  depth=-520
    elif li is not None and li<=-5: depth=+440
    elif li==0:            depth=-330
    else:                  depth=-200
    if reg=='high': depth*=0.85

    pts=[]
    nh=5 if hdur>0.07 else 4
    for i in range(nh):
        u=(hdur/d)*(i/(nh-1)) if nh>1 else 0.0
        # 先深后回到 0，用 q5 缓出
        pts.append((u, depth*(1-q5(i/max(nh-1,1)))))

    # ---- 字腹 ----
    b0=min(0.22, hdur/d); b1=1.0-min(0.20, tdur/d)
    if b1-b0<0.22: b0,b1=0.28,0.72
    amp = 0.0
    if mt=='vib':  amp = 120.0 if d>=0.52 else 80.0
    elif mt=='slow': amp = 70.0 if d>=0.52 else 30.0
    else: amp = 14.0
    if reg=='high': amp*=0.85
    cycles = 1.0 if d<0.52 else 2.0
    nb=max(5,int((b1-b0)/0.07)+1)
    for i in range(nb):
        u=b0+(b1-b0)*i/(nb-1)
        ph=(u-b0)/max(b1-b0,1e-6)
        pts.append((u, -amp*math.sin(math.pi*cycles*ph)**2))

    # ---- 字尾：持续深偏移段 ----
    if pos=='last':        tdepth=-560
    elif lo is not None and lo>=5:  tdepth=-440
    elif lo is not None and lo<=-5: tdepth=+400
    else:                  tdepth=-180
    if reg=='high': tdepth*=0.85
    nt=5 if tdur>0.06 else 4
    for i in range(1,nt+1):
        u=1.0-(tdur/d)*(1-i/nt)
        pts.append((u, tdepth*q5(i/nt)))

    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<2e-4: continue
        out.append((float(np.clip(u,0,1)), float(np.clip(v,-1200,1200))))
    return out

st=dict(pts=0,absm=[],zf=[],sd=[],p99=[],over200=[])
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
    arr=np.array(yi,float)
    st['pts']+=len(xs); st['absm'].append(float(np.mean(np.abs(arr))))
    st['zf'].append(float((np.abs(arr)<50).mean())); st['sd'].append(float(np.std(arr)))
    st['p99'].append(float(np.percentile(arr,1))); st['over200'].append(float((np.abs(arr)>200).mean()))

allv=np.concatenate([np.array(p['curves'][-1]['ys'],float) for p in doc['voice_parts']])
print(f"points {st['pts']} ({st['pts']/51:.0f}/part)")
print(f"mean|y| {np.median(st['absm']):.1f}c   (白烁 69.2)")
print(f"|y|<50   {np.median(st['zf']):.1%}   (白烁 65.4%)")
print(f"std      {np.median(st['sd']):.1f}c   (白烁 124.7)")
print(f"\nall-value percentiles vs 白烁:")
for q in (1,5,25,50,75,95,99):
    print(f"  p{q:2d}: {np.percentile(allv,q):+8.0f}c   (白烁参考 p{q})")
print(f"  |y|>200: {(np.abs(allv)>200).mean():.1%}   (白烁 8.8%)")
print(f"  |y|>400: {(np.abs(allv)>400).mean():.1%}   (白烁 2.5%)")

# 音色层
COLORS=['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']
MIX=dict(cl01=26, cl02=6, cl03=34, cl05=34)
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
    doc['expressions'].setdefault(abbr, dict(name=f'{abbr} mix',abbr=abbr,type='Curve',
                                             min=0,max=100,default_value=0))
for part in doc['voice_parts']:
    part['curves']=[c for c in part.get('curves',[]) if not c['abbr'].startswith('cl')]
    dur=int(part['duration'])
    for a_,v_ in MIX.items():
        part['curves'].append(dict(abbr=a_,xs=[0,dur],ys=[v_,v_]))
print(f"\nvoice mix {MIX}")

OUT=NEW/'score'/'v8_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
