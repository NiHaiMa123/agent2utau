"""v7：两处针对性改进。

1) PITD 极端值放到白烁水平（std 45 -> ~120）
   白烁的特征：65.4% 的点在 ±50c 内（大部分接近零），但其余点可以到 -200..-1200c。
   也就是说：**大部分时间贴着音高，少数时刻有强烈的一次性滑动**。
   我 v6 的问题是幅度均匀（正弦起伏），缺少「稀疏但强烈」的滑入/滑出。

2) 启用音色层（CLR + clNN）
   白烁用了 cl01/cl02/cl05 混合；我们一直用未配置的默认音色。
"""
import sys, json, io, math
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
RES=int(doc.get('resolution',480)); BPM=float((doc.get('tempos') or [{'bpm':120}])[0]['bpm'])
TICK_MS=60000.0/(BPM*RES); STEP=max(2,int(round(16.0/TICK_MS)))

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
    """关键改动：大部分时间贴 0，但字头/字尾/换音处有「强烈但短促」的一次性偏移。"""
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    li=None if prev is None else tone-prev
    lo=None if next_ is None else tone-next_
    mt=motion(a,b)
    pts=[]
    # 时间分配：滑入与滑出都很短（像白烁那样"一次性"），中间大部分贴 0
    hf = min(0.16, 0.45*(0.09/max(d,0.09)))     # 字头占比：短
    tf = min(0.20, 0.50*(0.10/max(d,0.10)))     # 字尾占比
    b0, b1 = hf, 1.0-tf
    if b1-b0 < 0.20: b0, b1 = 0.30, 0.70

    # ---- 字头：强烈一次性滑入（白烁 p10 -153c，极值可到 -400+）----
    if pos=='first':        hd = -330
    elif li is not None and li>=5:   hd = -260
    elif li is not None and li<=-5:  hd = +230
    elif li==0:             hd = -180
    else:                   hd = -120
    if reg=='high': hd*=0.85
    nh=4 if d>0.28 else 3
    for i in range(nh):
        u=hf*(i/(nh-1)) if nh>1 else 0.0
        pts.append((u, hd*(1-q5(i/max(nh-1,1)))))

    # ---- 字腹：绝大部分贴 0，只有长字/有周期证据才动 ----
    nb=max(4,int((b1-b0)/0.08)+1)
    body_amp = 0.0
    if mt=='vib':
        body_amp = 110.0 if d>=0.52 else 70.0
    elif mt=='slow':
        body_amp = 55.0 if d>=0.52 else 26.0
    else:
        body_amp = 12.0
    if reg=='high': body_amp*=0.85
    cycles = 1.0 if d<0.52 else 2.0
    for i in range(nb):
        u=b0+(b1-b0)*i/(nb-1)
        ph=(u-b0)/max(b1-b0,1e-6)
        # 贴零为主，用 sin^2 让它两端归零
        val = -body_amp*math.sin(math.pi*cycles*ph)**2
        pts.append((u,val))

    # ---- 字尾：强烈一次性滑出（白烁 p10 -220c）----
    if pos=='last':        td=-300
    elif lo is not None and lo>=5:   td=-240
    elif lo is not None and lo<=-5:  td=+220
    else:                  td=-100
    if reg=='high': td*=0.85
    nt=4 if d>0.28 else 3
    for i in range(1,nt+1):
        u=1.0-tf*(1-i/nt)
        pts.append((u, td*q5(i/nt)))

    pts.sort(key=lambda x:x[0])
    out=[]
    for u,v in pts:
        if out and abs(u-out[-1][0])<5e-4: continue
        out.append((float(np.clip(u,0,1)), float(np.clip(v,-1200,1200))))
    return out

st=dict(pts=0,absm=[],zf=[],sd=[])
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

print(f"points {st['pts']} ({st['pts']/51:.0f}/part)")
print(f"mean|y| {np.median(st['absm']):.1f}c   (白烁 69.2)")
print(f"|y|<50   {np.median(st['zf']):.1%}   (白烁 65.4%)")
print(f"std      {np.median(st['sd']):.1f}c   (白烁 124.7)")

# ---------- 音色层 ----------
COLORS=['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']
# dsconfig speakers 顺序 -> clNN: cl01=Bright cl02=Cute cl03=Normal cl04=Whisper cl05=Classic
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
print(f"\nvoice color: clr options set, mix {MIX}")

OUT=NEW/'score'/'v7_score.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
