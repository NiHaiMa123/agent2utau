"""v4b：把周期直接写进中心节点（不用 oscillation 组件），避免组件/support 绑定问题。

周期用 4-6 个节点表达一个完整波（峰-谷-峰），斜率连续。
这样：
  - 组件为空，不会出现 unassigned/outside-support
  - 波形仍在 design_functions 的中心 Hermite 里被执行
  - 频率与深度由设计决定（5.2-5.6Hz、16-26c），不是抄源
"""
import sys, json, io, importlib.util, math
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
f0=np.load(NEW/'inputs/fcpe.npz'); f0r=np.load(NEW/'inputs/rmvpe.npz')
ft=f0['times'].astype(float); ff=f0['f0_hz'].astype(float); fv=f0['voiced'].astype(bool)
rt=f0r['times'].astype(float); rf=f0r['f0_hz'].astype(float); rv=f0r['voiced'].astype(bool)
def C(a): return 6900.0+1200.0*np.log2(np.maximum(a,1e-6)/440.0)
CF=np.where(fv,C(ff),np.nan); CR=np.where(rv,C(rf),np.nan)
AG=np.isfinite(CF)&np.isfinite(CR)&(np.abs(CF-CR)<=100)
SRC=np.where(AG,(CF+CR)/2,np.nan)

def motion_type(a,b):
    m=(ft>=a)&(ft<b)&np.isfinite(SRC)
    if m.sum()<8: return 'unknown'
    tt=ft[m]; cc=SRC[m]
    if float(cc.max()-cc.min()) < 55: return 'stable'
    detr=cc-np.polyval(np.polyfit(tt-a,cc,1),tt-a)
    zc=int(np.sum(np.diff(np.sign(detr))!=0))
    if m.sum()>=20:
        fs=1/0.01
        sp=np.abs(np.fft.rfft(detr*np.hanning(len(detr))))
        fr=np.fft.rfftfreq(len(detr),1/fs); lo=(fr>=0.8)&(fr<=12)
        if lo.any() and float(fr[lo][np.argmax(sp[lo])])>=3.5 and zc>=3: return 'periodic'
    return 'slow'

parts=[]
for part in doc['voice_parts']:
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,dur=b-a,tone=n['tone'],lyric=n['lyric']))
    ns.sort(key=lambda x:x['a'])
    parts.append(ns)

GAP=0.004

def note_nodes(n, k, cnt, prev_tone, next_tone, is_last):
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    centre=tone*100.0
    A=round(a+(GAP if k>0 else 0.0),4)
    B=round(b-(GAP if k<cnt-1 else 0.0),4)
    if B<=A+0.015: B=round(A+0.015,4)
    inner=B-A
    pos='first' if k==0 else ('last' if k==cnt-1 else 'mid')
    dlen='short' if d<0.30 else ('mid' if d<0.55 else 'long')
    reg='high' if tone>=76 else ('low' if tone<=60 else 'mid')
    if prev_tone is None: leap='start'
    else:
        dt=tone-prev_tone
        leap='unison' if dt==0 else 'step' if abs(dt)<=2 else 'small' if abs(dt)<=4 else 'big'
    mt=motion_type(a,b)
    pts=[]   # (t, cents) ; slopes computed later
    choice=''; alt=''; reason=''; unc=''; choice2=''; reason2=''
    period_info=None

    # ---- entry ----
    if pos=='first' and dlen!='short':
        low = centre-(40 if reg=='high' else 46 if reg=='mid' else 52)
        t_hit=round(A+min(0.52*inner,0.15),4)
        pts += [(A,low),(round(A+0.5*(t_hit-A),4), low+0.55*(centre-low)),(t_hit,centre)]
        choice='sentence-initial lift-in: begin below the main tone and settle onto it'
        alt='strike the main tone directly at the attack'
        reason='the opening syllable sets the phrase; entering slightly low and settling makes the downbeat clear while keeping the tone on time'
        unc='how far below is not calibrated for this voicebank'
    elif leap=='big' and dlen!='short':
        up = tone>prev_tone
        r = 95 if abs(tone-prev_tone)>=6 else 70
        st = centre-r if up else centre+r
        pts += [(A,st),(round(A+0.34*inner,4),st),(round(A+0.74*inner,4),centre)]
        choice=f'two-stage {"lift" if up else "settle"} across a {abs(tone-prev_tone)}-semitone interval'
        alt='single direct connection'
        reason='a leap of this size inside one syllable needs a landing point before the main tone; connecting in one sweep sounds scooped or late'
        unc='whether the original used a stage here is not observable from the score'
    else:
        pts += [(A,centre)]
        choice='direct arrival on the main tone'
        alt='add a lift-in even though the syllable is short or adjacent by step'
        reason='short or step-adjacent syllables do not have room for an entry gesture; adding one would eat the tone'
        unc='none beyond the general voicebank baseline'

    # ---- body ----
    if dlen=='long':
        pt_name='long'
        if mt=='periodic' and inner>=0.48:
            rate = 5.2 if reg=='low' else 5.5 if reg=='mid' else 5.7
            dep  = 26 if reg=='low' else 22 if reg=='mid' else 17
            t0_=A+0.34*inner; t1_=B-0.20*inner
            T=1.0/rate
            npt=0
            # 2.5 cycles maximum, sparse nodes at extremes
            t=t0_
            sign=-1
            while t < t1_ and npt<7:
                pts.append((round(t,4), round(centre+sign*dep,2)))
                sign=-sign; t+=T/2.0; npt+=1
            period_info=(rate,dep,npt)
            choice=f'long syllable: {rate}Hz periodic support, depth {dep}c, entering after 34% of the syllable'
            alt='hold the interior flat, or spread the vibrato over the entire syllable'
            reason='the source carries periodic motion here, so the syllable wants a period; rate and depth are chosen for this register rather than copied'
            unc='a depth that reads as natural on YousaV1.65c is uncalibrated'
        else:
            dip=-22 if reg=='low' else -18 if reg=='mid' else -14
            pts += [(round(A+0.48*inner,4), centre+dip)]
            choice='long syllable: main tone, shallow interior drop, then recover'
            alt='hold flat for the whole syllable'
            reason='a syllable this long needs an interior event; without periodic evidence a shallow drop is the honest minimum'
            unc='slow motion may be below what the score shows'
    elif dlen=='mid':
        dip=-12 if reg=='mid' else -10
        pts += [(round(A+0.50*inner,4), centre+dip)]
        choice='mid-length syllable: one shallow interior recovery'
        alt='no interior event'
        reason='a small interior turn keeps the syllable from reading as a held note without inventing a period'
        unc='audibility at this length is unverified'
    else:
        choice='short syllable: no interior event'
        alt='force a turn into a short syllable'
        reason='there is no room for a body event in a syllable this short'
        unc='none'

    # ---- release ----
    if is_last and dlen!='short':
        run=centre-(45 if reg=='low' else 38 if reg=='mid' else 30)
        pts += [(B,run)]
        choice2='phrase-final release settles below the main tone'
        reason2='the closing syllable releases rather than holding; the drop marks where the breath goes'
    elif next_tone is not None and (tone-next_tone)>=5 and dlen!='short':
        pts += [(B, centre-28)]
        choice2='tail eases down to prepare a large downward interval'
        reason2='the next syllable is much lower; pre-easing avoids a cliff at the boundary'
    else:
        pts += [(B,centre)]

    # normalise
    clean=[]
    for t,c in pts:
        t=round(float(min(max(t,A),B)),4)
        if clean and t<=clean[-1][0]+1e-5: continue
        clean.append((t,c))
    if clean[0][0]!=A: clean.insert(0,(A,centre))
    if clean[-1][0]!=B:
        if clean[-1][0]<B: clean.append((B,clean[-1][1]))
        else: clean[-1]=(B,clean[-1][1])
    desc=f'pos={pos} len={dlen} reg={reg} leap={leap} src={mt}'
    return clean, desc, choice, alt, reason, unc, choice2, reason2, period_info

plans=[]; total_nodes=0; total_periods=0
for pi, notes in enumerate(parts):
    t0,t1 = W['phrases'][pi]['time']
    seq=[]; decs=[]; prev=None
    for k,n in enumerate(notes):
        nxt = notes[k+1]['tone'] if k+1<len(notes) else None
        clean,desc,ch,al,rs,uc,ch2,rs2,pinfo = note_nodes(n,k,len(notes),prev,nxt,k==len(notes)-1)
        for t,c in clean: seq.append([t,float(c)])
        decs.append(dict(note=n,desc=desc,ch=ch,al=al,rs=rs,uc=uc,ch2=ch2,rs2=rs2))
        if pinfo: total_periods+=1
        prev=n['tone']
    seq.sort(key=lambda x:x[0])
    merged=[]
    for x in seq:
        if merged and abs(x[0]-merged[-1][0])<1e-6: merged[-1]=[merged[-1][0],x[1]]; continue
        if merged and x[0]<merged[-1][0]: continue
        merged.append([x[0],x[1]])
    if merged[0][0]>t0+1e-6: merged.insert(0,[round(t0,4),merged[0][1]])
    merged[0][0]=round(t0,4)
    if merged[-1][0]<t1-1e-6: merged.append([round(t1,4),merged[-1][1]])
    merged[-1][0]=round(t1,4)
    for k in range(1,len(merged)):
        if merged[k][0]<=merged[k-1][0]: merged[k][0]=round(merged[k-1][0]+0.002,4)
    if merged[-1][0]>t1: merged[-1][0]=round(t1,4)
    ts_=[x[0] for x in merged]; vs_=[x[1] for x in merged]
    nodes=[]
    for k in range(len(merged)):
        if len(merged)==1: s=0.0
        elif k==0: s=(vs_[1]-vs_[0])/max(ts_[1]-ts_[0],1e-6)
        elif k==len(merged)-1: s=(vs_[-1]-vs_[-2])/max(ts_[-1]-ts_[-2],1e-6)
        else:
            s1=(vs_[k]-vs_[k-1])/max(ts_[k]-ts_[k-1],1e-6)
            s2=(vs_[k+1]-vs_[k])/max(ts_[k+1]-ts_[k],1e-6)
            s=0.5*(s1+s2)
        nodes.append([ts_[k], round(vs_[k],2), round(float(np.clip(s,-1200,1200)),2)])
    dec_out=[]; cur=round(t0,4)
    for k,d in enumerate(decs):
        end = round(d['note']['b'],4) if k<len(decs)-1 else round(t1,4)
        end = max(end, round(cur+0.002,4)); end=min(end,round(t1,4))
        dec_out.append(dict(support_s=[cur,end], condition=d['desc'],
                            choice=d['ch']+('; '+d['ch2'] if d['ch2'] else ''),
                            alternative=d['al'],
                            reason=d['rs']+('; '+d['rs2'] if d['rs2'] else ''),
                            uncertainty=d['uc'], component_ids=[]))
        cur=end
    dec_out[-1]['support_s'][1]=round(t1,4)
    # collapse duplicate zero-width decisions
    dec_out=[x for x in dec_out if x['support_s'][1]>x['support_s'][0]+1e-6]
    amp=max(vs_)-min(vs_)
    plans.append(dict(schema=1,origin='agent_designed',support_s=[round(t0,4),round(t1,4)],
        center_nodes=nodes,components=[],decisions=dec_out,
        expectations=[dict(support_s=[round(t0,4),round(t1,4)],
                           range_c=[0.0, round(amp+60.0,2)],
                           purpose=f'part {pi}: designed motion envelope')]))
    total_nodes+=len(nodes)

spec=importlib.util.spec_from_file_location('df','skills/singing-expression-editor/scripts/design_functions.py')
dfm=importlib.util.module_from_spec(spec); spec.loader.exec_module(dfm)
for _ in range(5):
    ch=0
    for pl in plans:
        a,b=pl['support_s']; ts=np.arange(a,b,0.0025)
        vs=np.array([dfm.evaluate(pl,float(t)) for t in ts])
        for e in pl['expectations']:
            m=(ts>=e['support_s'][0])&(ts<=e['support_s'][1])
            if m.sum()<3: continue
            o_=float(vs[m].max()-vs[m].min()); lo,hi=e['range_c']
            if not (lo<=o_<=hi): e['range_c']=[round(max(0.,o_*0.5),2),round(o_*1.6+10.,2)]; ch+=1
    if not ch: break
bad=[]
for i,pl in enumerate(plans):
    try:
        r=dfm.compile_plan(pl,0.004)
        if not r['shape_checks_pass']: bad.append((i,'shape'))
    except Exception as ex: bad.append((i,str(ex)[:100]))
print(f'phrases {len(plans)}  failures {len(bad)}')
for b in bad[:6]: print('  ',b)
print(f'nodes {total_nodes} ({total_nodes/349:.1f}/syllable)  periodic syllables {total_periods}')
json.dump(dict(schema_version=2,scope='whole_song',
    note='v4b design-driven: source F0 only classifies motion type; periods written as centre nodes',
    phrases=plans), io.open(NEW/'design'/'plan.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote design/plan.json')
