"""v20：强制单调约束，彻底消除反向预兆。

原则（音乐上正确）：
  若本音的音高低于下一个音（上行跳），则本音尾部到下一音头部之间，
  最终线必须**非递减**；反之非递增。
  字腹、字头、字尾的所有动作都必须满足该约束。

实现：先生成候选曲线，再做「方向单调化」后处理：
  对每个音符边界 (i -> i+1)，若 tone[i+1] > tone[i]，
  则在 [b_i - 0.12, a_{i+1} + 0.12] 窗口内强制 non-decreasing（累积取最大）。
  下行同理取最小。
"""
import sys, json, io, math
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'score'/'v19_score.ustx')   # 基于 v19 的曲线
tm = TempoMap.from_doc(doc)
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
    """音符内部动作；大跳不做字尾准备（交给边界单调化处理）。"""
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)
    pts=[]

    # 字头
    if li is not None and abs(li)>=5:
        depth = -min(130, 20*abs(li)) if li>0 else min(130, 20*abs(li))
        hdur=min(0.13, max(0.080, 0.22*d))
        n1=max(7,int(hdur/d*130)+2)
        for i in range(n1):
            f=i/(n1-1)
            pts.append((hdur/d*f, depth*(1-q5(f))))     # 单调到 0
        bs=hdur/d
    else:
        hd = (-42 if (li is not None and li>0) else (36 if (li is not None and li<0) else (-42 if pos=='first' else -20)))
        if reg=='high': hd*=0.85
        hdur=min(0.09, max(0.050, 0.16*d))
        n1=max(6,int(hdur/d*110)+2)
        for i in range(n1):
            f=i/(n1-1)
            pts.append((hdur/d*f, hd*math.sin(math.pi*f)))
        bs=hdur/d

    # 字腹
    tdur=min(0.11, max(0.070, 0.20*d))
    be=1.0-tdur/d
    if be-bs<0.22: bs,be=0.30,0.70
    if mt=='vib':   amp=145.0 if d>=0.52 else 98.0
    elif mt=='slow':amp=88.0 if d>=0.52 else 44.0
    else:           amp=20.0
    if reg=='high': amp*=0.85
    cycles=1.0 if d<0.52 else 2.0
    nb=max(8,int((be-bs)/0.05)+1)
    for i in range(nb):
        u=bs+(be-bs)*i/(nb-1)
        ph=(u-bs)/max(be-bs,1e-6)
        pts.append((u, -amp*math.sin(math.pi*ph)*math.sin(2*math.pi*cycles*ph)*0.5))

    # 字尾：只用很浅的释放，且不朝下一音的反方向走
    if lo is not None and abs(lo)>=5:
        td = 0.0            # 大跳前不预动，边界由单调化处理
        nt_=4
    else:
        td = (-35 if (lo is not None and lo>0) else (30 if (lo is not None and lo<0) else -30))
        if reg=='high': td*=0.85
        nt_=max(6,int(tdur/d*110)+2)
    if nt_==4:
        for i in range(1,5):
            f=i/4
            pts.append((1.0-tdur/d+tdur/d*f, td*f))   # 线性到 td(=0)
    else:
        for i in range(nt_):
            f=i/(nt_-1)
            pts.append((1.0-tdur/d+tdur/d*f, td*math.sin(math.pi*f)))

    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<2e-4: continue
        out.append((float(np.clip(u,0,1)), float(v)))
    return out

# ---- 生成 + 边界单调化 ----
allvals=[]
for pi,part in enumerate(doc['voice_parts']):
    notes=parts[pi]
    xs=list(range(0,int(part['duration'])+1,STEP))
    if xs[-1]!=int(part['duration']): xs.append(int(part['duration']))
    xsArr=np.array(xs,float)
    tick_ms=np.array([tm.tick_to_ms(part['position']+x) for x in xsArr])/1000
    ys=np.zeros(len(xs)); cov=np.zeros(len(xs),bool)
    for ni,n in enumerate(notes):
        nodes=design(n,ni,len(notes),
                     notes[ni-1]['tone'] if ni>0 else None,
                     notes[ni+1]['tone'] if ni+1<len(notes) else None)
        us=np.array([x[0] for x in nodes]); vs=np.array([x[1] for x in nodes])
        m=(tick_ms>=n['a'])&(tick_ms<=n['b'])
        if not m.any(): continue
        u=(tick_ms[m]-n['a'])/max(n['b']-n['a'],1e-6)
        ys[m]=np.interp(u,us,vs); cov[m]=True

    # 边界单调化：在每个音符交界 ±0.11s 内消除反向预兆
    for ni in range(len(notes)-1):
        a_t=notes[ni]['b']          # 边界时刻
        lo_i=np.searchsorted(tick_ms, a_t-0.11)
        hi_i=np.searchsorted(tick_ms, a_t+0.11)
        if hi_i-lo_i < 3: continue
        seg=ys[lo_i:hi_i].copy()
        if notes[ni+1]['tone'] > notes[ni]['tone']:
            # 非递减
            for j in range(1,len(seg)):
                if seg[j] < seg[j-1]: seg[j]=seg[j-1]
        elif notes[ni+1]['tone'] < notes[ni]['tone']:
            for j in range(1,len(seg)):
                if seg[j] > seg[j-1]: seg[j]=seg[j-1]
        ys[lo_i:hi_i]=seg

    if cov.any(): ys=ys-float(np.median(ys[cov]))
    yi=[int(round(float(np.clip(v,-1200,1200)))) for v in ys]
    part['curves']=[c for c in part['curves'] if c['abbr']!='pitd']
    part['curves'].append(dict(abbr='pitd',xs=[int(x) for x in xs],ys=yi))
    allvals.extend(yi)

allv=np.array(allvals,float); dy=np.abs(np.diff(allv))
print(f'points {len(allv)}  p50 {np.percentile(allv,50):+.0f}  p99 {np.percentile(allv,99):+.0f}')
print(f'  |dy| median {np.median(dy):.1f} max {dy.max():.0f}  >200 {(dy>200).sum()}')

OUT=NEW/'score'/'v20_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
