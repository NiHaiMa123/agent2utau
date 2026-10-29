"""v12：消除悬崖——极端偏移必须是「有起有落的平滑段」，不能是垂直边。

诊断（v11 vs 白烁）：
  |dy| 每步 >400c 的步数：v11 有 114 个，白烁 67 个（但 v11 点数仅其 2.4 倍 → 密度高 3.3 倍）
  → 说明我的极端段在 12ms 网格内"瞬移"，图上就是垂直悬崖。

修正：
  1) 极端段的时间 ≥ 60ms（白烁 |y|>300 段中位 23ms，但那是 15.6ms 网格下的 1-2 个点；
     在 12ms 网格下要保证 >= 5 个点才有起落）
  2) 用 q5 缓动：进入 40% 时间、保持 20%、退出 40%
  3) 相邻点最大变化限制（软限幅到 120c/12ms），超出则平滑
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

def shaped_segment(u0, u1, depth, d):
    """有起有落的平滑段：进入 40%、保持 20%、退出 40%。返回 [(u,val)]。"""
    span_u = u1-u0
    if span_u <= 0: return []
    pts=[]
    n = max(6, int(span_u*d/0.010)+1)     # 至少每 10ms 一个点
    for i in range(n):
        f = i/(n-1)
        if f < 0.40:
            a = q5(f/0.40)                  # 0->1 缓入
        elif f < 0.60:
            a = 1.0                         # 保持
        else:
            a = 1.0-q5((f-0.60)/0.40)       # 1->0 缓出
        pts.append((u0+span_u*f, depth*a))
    return pts

def design(n,k,cnt,prev,next_):
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)

    # 极端段时长：保证 >= 0.07s 且有起落（12ms 网格下至少 6 点）
    hdur=min(0.16, max(0.070, 0.28*d))
    tdur=min(0.14, max(0.060, 0.25*d))

    if pos=='first':       hd=-560
    elif li is not None and li>=5:  hd=-480
    elif li is not None and li<=-5: hd=+440
    elif li==0:            hd=-240
    else:
        base = -110 if (li is not None and li>0) else (110 if (li is not None and li<0) else 0)
        hd = base + (30 if k%2 else -30)
    if reg=='high': hd*=0.85

    pts = shaped_segment(0.0, hdur/d, hd, d)

    b0=min(0.26,hdur/d); b1=1.0-min(0.24,tdur/d)
    if b1-b0<0.28: b0,b1=0.32,0.68
    amp=0.0
    if mt=='vib':   amp=150.0 if d>=0.52 else 100.0
    elif mt=='slow':amp=90.0 if d>=0.52 else 44.0
    else:           amp=22.0
    if reg=='high': amp*=0.85
    cycles=1.0 if d<0.52 else 2.0
    nb=max(7,int((b1-b0)/0.055)+1)
    for i in range(nb):
        u=b0+(b1-b0)*i/(nb-1)
        ph=(u-b0)/max(b1-b0,1e-6)
        pts.append((u, -amp*math.sin(2*math.pi*cycles*ph)*0.5))

    if pos=='last':       td=-520
    elif lo is not None and lo>=5:  td=-420
    elif lo is not None and lo<=-5: td=+390
    else:
        base = 80 if (lo is not None and lo<0) else (-80 if (lo is not None and lo>0) else 0)
        td = base + (25 if k%2 else -25)
    if reg=='high': td*=0.85
    tail = shaped_segment(1.0-tdur/d, 1.0, td, d)
    # 段是 1.0-tdur/d -> 1.0，形状方向需要反向（depth 从 0 到 td 再回 0）
    pts += [(u, v) for u,v in tail]

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
    # 软限幅：相邻点变化不超过 110c（避免垂直悬崖），迭代 3 次
    for _ in range(3):
        for j in range(1,len(ys)):
            dv=ys[j]-ys[j-1]
            if abs(dv)>110:
                ys[j]=ys[j-1]+math.copysign(110, dv)
        for j in range(len(ys)-2,-1,-1):
            dv=ys[j]-ys[j+1]
            if abs(dv)>110:
                ys[j]=ys[j+1]+math.copysign(110, dv)
    med=float(np.median(ys)); ys=ys-med
    yi=[int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves']=[c for c in part.get('curves',[]) if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd',xs=[int(x) for x in xs],ys=yi))
    allvals.extend(yi)

allv=np.array(allvals,float)
ref={1:-513,5:-225,25:-52,50:-5,75:16,95:119,99:410}
print(f'points {len(allv)}  mean|y| {np.mean(np.abs(allv)):.1f}  |y|<50 {(np.abs(allv)<50).mean():.1%}  std {np.std(allv):.1f}')
print('      v12     白烁')
for q in (1,5,25,50,75,95,99):
    print(f'p{q:2d}: {np.percentile(allv,q):+7.0f}  {ref[q]:+7.0f}')
print(f'|y|>200 {(np.abs(allv)>200).mean():.1%}  (8.8%)')
dy=np.abs(np.diff(allv))
print(f'|dy|: median {np.median(dy):.1f} p99 {np.percentile(dy,99):.1f} max {dy.max():.0f}  >400: {(dy>400).sum()}')

COLORS=['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']
MIX=dict(cl01=50, cl05=50)
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

OUT=NEW/'score'/'v12_score.ustx'
save_ustx(doc,OUT)
print(f'\nwrote {OUT}')
