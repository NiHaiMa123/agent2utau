"""v19：修正大跳的实现——消除「反向预兆 + 垂直跳」，改为单调斜坡跨越音符边界。

图审发现（p2:f0:v6, 28.85-28.95s）：
  曲线在接近音符边界时先上冲到 62.8，随后在约 40ms 内垂直跌到 57.5 再跳到 67.5。
  这是「反向预兆 + 垂直跳」的组合，听感会是断裂的爆音。

正确做法（Skill「上行音程衔接」）：
  大跳应在边界前后形成**单调斜坡**，10%-90% 用 60-110ms（白烁中位 53ms，我偏长一点更稳），
  且**不允许反向预兆**：离开前音后径直向目标音走。
实现：
  1) 每个音符内部：字头/字尾不得跨越本音的目标音（即不许先反向后跳）
  2) 音符边界处：留出一个「过渡区」由两侧共同决定，用单调插值
  3) 字头/字尾幅度按音程方向对齐：上行时字头从下方入且直接到达，不做二次反向
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
STEP=5

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
    """字符内部只做「符合本音目标」的动作；边界过渡交给相邻音符共同决定。"""
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)
    target=tone*100.0
    pts=[]

    # 大跳进入：本音是从下方/上方大幅进入时，在字头**单调**走向目标（不回头）
    if li is not None and abs(li)>=5:
        # 起始点放在前音方向（上行则低于目标），在字头 100-140ms 内单调到达
        depth = -min(140, 22*abs(li)) if li>0 else min(140, 22*abs(li))
        hdur=min(0.14, max(0.085, 0.24*d))
        n1=max(7,int(hdur/d*130)+2)
        for i in range(n1):
            f=i/(n1-1)
            pts.append((hdur/d*f, depth*(1-q5(f))))   # 单调 从 depth 到 0
        body_start = hdur/d
    else:
        # 普通字：浅滑入，两端归零（边界连续）
        if abs(li or 0)>=3: hd=-45 if (li>0) else 38
        elif pos=='first':  hd=-45
        elif li==0:         hd=-40
        else:               hd=-22
        if reg=='high': hd*=0.85
        hdur=min(0.10, max(0.055, 0.18*d))
        n1=max(6,int(hdur/d*110)+2)
        for i in range(n1):
            f=i/(n1-1)
            pts.append((hdur/d*f, hd*math.sin(math.pi*f)))
        body_start = hdur/d

    # ---- 字腹 ----
    if lo is not None and abs(lo)>=5:
        tdur=min(0.13, max(0.080, 0.22*d))
        body_end = 1.0-tdur/d
        # 字尾单调走向下一音方向（不提前到达，只是准备）
        out_depth = -min(120, 18*abs(lo)) if lo>0 else min(120, 18*abs(lo))
    else:
        if abs(lo or 0)>=3: td=-40 if (lo>0) else 34
        elif pos=='last':   td=-70
        else:               td=-26
        if reg=='high': td*=0.85
        tdur=min(0.13, max(0.080, 0.22*d))
        body_end = 1.0-tdur/d
        out_depth = None

    if body_end-body_start<0.20:
        body_start, body_end = 0.30, 0.70

    if mt=='vib':   amp=145.0 if d>=0.52 else 98.0
    elif mt=='slow':amp=88.0 if d>=0.52 else 44.0
    else:           amp=20.0
    if reg=='high': amp*=0.85
    cycles=1.0 if d<0.52 else 2.0
    nb=max(8,int((body_end-body_start)/0.05)+1)
    for i in range(nb):
        u=body_start+(body_end-body_start)*i/(nb-1)
        ph=(u-body_start)/max(body_end-body_start,1e-6)
        pts.append((u, -amp*math.sin(math.pi*ph)*math.sin(2*math.pi*cycles*ph)*0.5))

    # ---- 字尾 ----
    if out_depth is not None:
        n2=max(7,int(tdur/d*130)+2)
        for i in range(n2):
            f=i/(n2-1)
            pts.append((1.0-tdur/d+tdur/d*f, out_depth*q5(f)))   # 单调 0 -> out_depth
    else:
        n2=max(6,int(tdur/d*110)+2)
        for i in range(n2):
            f=i/(n2-1)
            pts.append((1.0-tdur/d+tdur/d*f, td*math.sin(math.pi*f)))

    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<2e-4: continue
        out.append((float(np.clip(u,0,1)), float(v)))
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
    if cov.any(): ys=ys-float(np.median(ys[cov]))
    yi=[int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves']=[c for c in part['curves'] if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd',xs=[int(x) for x in xs],ys=yi))
    allvals.extend(yi)

allv=np.array(allvals,float); dy=np.abs(np.diff(allv))
print(f'points {len(allv)}')
print(f'  p50 {np.percentile(allv,50):+.0f}  p99 {np.percentile(allv,99):+.0f}  |y|>200 {(np.abs(allv)>200).mean():.2%}')
print(f'  |dy| median {np.median(dy):.1f} max {dy.max():.0f}')

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

OUT=NEW/'score'/'v19_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
