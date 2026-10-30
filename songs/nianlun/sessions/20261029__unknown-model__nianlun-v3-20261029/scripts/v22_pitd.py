"""v22：修复「峰位置 58.6% 都在 0.0」的配方化缺陷。

问题：字头统一用 hd*sin(πf)，hd 多为负 → 起点是该单元最高点（因为滑入是往下走）。
      这导致 58.6% 的单元「最高点=起点」，形态趋同。

根因：字头滑入**方向单一**（几乎都向下）。
真实演唱里，字头方向应由「进入音程」决定，且应有一部分是向上的（从上方进入）。

修正：
  1) 上行大跳 → 从下方进入（负，起点低，最高点在后段）；
  2) 下行大跳 → 从上方进入（正，起点高，最高点在起点）—— 这类应占相当比例；
  3) 级进/同音 → 交替正负，且让约一半单元的起点不是最高点。
  4) 字腹改为以「单峰/单谷」为主（不再是正负对称的正弦，那样最高点总在两端）。
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
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)
    pts=[]

    # --- 字头方向：由音程符号 + 单元序号交替决定（约一半向上/一半向下）---
    mag = 0
    sign = 0
    if li is not None and abs(li)>=5:
        mag = min(130, 20*abs(li)); sign = +1 if li>0 else -1   # 上行从下入(+向上抬)，下行从上入
    elif li is not None and abs(li)>=3:
        mag = 55; sign = +1 if li>0 else -1
    elif li==0:
        mag = 40; sign = +1 if (k%2) else -1
    else:
        mag = 28; sign = +1 if (k%2) else -1
    if reg=='high': mag*=0.85
    hd = -sign*mag     # 进入偏移：上行→负(低起)，下行→正(高起)
    hdur=min(0.12, max(0.060, 0.20*d))
    n1=max(6,int(hdur/d*110)+2)
    for i in range(n1):
        f=i/(n1-1)
        pts.append((hdur/d*f, hd*(1-q5(f))))     # 单调回到 0

    # --- 字腹：单峰或单谷（不是对称正弦，避免最高点总在两端）---
    bs=hdur/d
    tdur=min(0.13, max(0.075, 0.22*d))
    be=1.0-tdur/d
    if be-bs<0.24: bs,be=0.30,0.70
    if mt=='vib':   amp=145.0 if d>=0.52 else 98.0
    elif mt=='slow':amp=88.0 if d>=0.52 else 44.0
    else:           amp=20.0
    if reg=='high': amp*=0.85
    # 峰位与方向按单元条件变化
    which = (k*7 + cnt) % 3
    body_sign = +1 if which==0 else (-1 if which==1 else (1 if mt=='vib' else -1))
    peakpos = 0.35 + 0.30*((k*3) % 5)/4.0     # 0.35..0.65
    nb=max(8,int((be-bs)/0.045)+1)
    for i in range(nb):
        u=bs+(be-bs)*i/(nb-1)
        ph=(u-bs)/max(be-bs,1e-6)
        # 单峰：sin(pi*ph^a) 形状，峰在 peakpos
        if ph <= peakpos:
            val = math.sin(math.pi*0.5*(ph/peakpos))**2
        else:
            val = math.sin(math.pi*0.5*(1-(ph-peakpos)/(1-peakpos)))**2
        pts.append((u, body_sign*amp*val))

    # --- 字尾：方向由离开音程符号决定 ---
    if lo is not None and abs(lo)>=5:
        tsign = -1 if lo>0 else +1
        tmag = min(120, 18*abs(lo))
    elif lo is not None and abs(lo)>=3:
        tsign = -1 if lo>0 else +1; tmag=50
    else:
        tsign = -1 if (k%2) else +1; tmag=30
    if reg=='high': tmag*=0.85
    td = tsign*tmag
    n2=max(6,int(tdur/d*110)+2)
    for i in range(n2):
        f=i/(n2-1)
        pts.append((1.0-tdur/d+tdur/d*f, td*q5(f)))

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

# 检查峰位分布
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))
allv=np.array(allvals,float)
dy=np.abs(np.diff(allv))
print(f'points {len(allv)}  p50 {np.percentile(allv,50):+.0f}  p99 {np.percentile(allv,99):+.0f}')
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

OUT=NEW/'score'/'v22_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
