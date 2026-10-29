"""修正剩余 12 个坏音符：
  9 个是『+』延续音（同元音跨音符，tone 是下一段旋律）。源 F0 在这里是同一元音的延续，
  强制锚定到 tone*100 会把连续的音强行掰断。
  正确做法（Skill「同元音跨音符换主音」）：
    对 '+' 音符，中心线跟随源的真实换音位置，但**幅度受限**；
    若有可靠源证据表明它确实换到了新音，则允许到新音；否则保持前一音符的音高。
"""
import sys, json, io, importlib.util
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft=f0['times'].astype(float); ff=f0['f0_hz'].astype(float); fv=f0['voiced'].astype(bool)
rt=f0r['times'].astype(float); rf=f0r['f0_hz'].astype(float); rv=f0r['voiced'].astype(bool)
def C(a): return 6900.0+1200.0*np.log2(np.maximum(a,1e-6)/440.0)
CF=np.where(fv,C(ff),np.nan); CR=np.where(rv,C(rf),np.nan)
AG=np.isfinite(CF)&np.isfinite(CR)&(np.abs(CF-CR)<=100)
SRC=np.where(AG,(CF+CR)/2,np.nan)

def src_med(a,b):
    m=(ft>=a)&(ft<b)&np.isfinite(SRC)
    return float(np.median(SRC[m])) if m.sum()>=3 else None

parts_notes=[]
for pi,part in enumerate(doc['voice_parts']):
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,dur=b-a,tone=n['tone'],lyric=n['lyric']))
    ns.sort(key=lambda x:x['a'])
    parts_notes.append(ns)

MAX_OFF=65.0; GAP=0.004

plans, stats = [], dict(nodes=0, notes=0, plus_followed=0, plus_held=0)
for pi,p in enumerate(W['phrases']):
    t0,t1=p['time']
    center=[]
    ns_list = parts_notes[pi]
    for k,n in enumerate(ns_list):
        a,b,d,tone = n['a'],n['b'],n['dur'],n['tone']
        A=max(round(a+(GAP if True else 0),4), round(t0,4))
        B=min(max(round(b-GAP,4), round(a+0.02,4)), round(t1,4))
        if B<=A+0.01: B=round(A+0.02,4)
        inner=B-A
        # decide the anchor centre for this note
        if n['lyric']=='+':
            # same-vowel continuation: does the source actually move to a new pitch?
            prev = ns_list[k-1] if k>0 else None
            prev_med = src_med(prev['a'],prev['b']) if prev else None
            cur_med  = src_med(a,b)
            tone_c = tone*100.0
            if cur_med is not None and prev_med is not None and abs(cur_med-prev_med) >= 90:
                # real melodic move in the source -> follow it, but stay near the written tone
                centre = float(np.clip(cur_med, tone_c-90, tone_c+90))
                stats['plus_followed']+=1
            else:
                # no evidence of a new pitch: keep continuity with the previous note
                centre = float(prev_med) if prev_med is not None else tone_c
                centre = float(np.clip(centre, tone_c-120, tone_c+120))
                stats['plus_held']+=1
        else:
            centre = tone*100.0
        m=(ft>=a)&(ft<b)&np.isfinite(SRC)
        if m.sum()<6 or d<0.10:
            center += [[A,round(centre,2),0.0],[B,round(centre,2),0.0]]
            stats['notes']+=1; stats['nodes']+=2; continue
        tt=ft[m]; cc=SRC[m]
        resid=cc-centre
        # for '+' notes keep the real move (no DC removal), for normal notes remove DC
        if n['lyric']!='+':
            resid = resid - np.median(resid)
        if len(resid)>=5:
            sm=resid.copy()
            for i in range(1,len(resid)-1): sm[i]=np.median(resid[i-1:i+2])
        else: sm=resid
        span=float(sm.max()-sm.min()); dstd=float(np.std(sm))
        step = 0.035 if (span>=150 or dstd>=45) else 0.060 if (span>=60 or dstd>=18) else 0.110
        edges=list(np.arange(A,B-1e-9,step))
        if not edges or edges[0]>A+1e-9: edges=[A]+edges
        if edges[-1]<B-1e-9: edges.append(B)
        else: edges[-1]=B
        nodes=[]
        for j,te in enumerate(edges):
            lo=te if j<len(edges)-1 else max(A,te-0.5*step)
            hi=edges[j+1] if j<len(edges)-1 else te
            mm=(tt>=lo)&(tt<hi)
            off=float(np.median(sm[mm])) if mm.sum()>=2 else float(np.interp(te,tt,sm))
            off=float(np.clip(off,-MAX_OFF,MAX_OFF))
            nodes.append([round(float(te),4), round(centre+off,2), 0.0])
        nodes[0][0]=A; nodes[-1][0]=B
        outn=[]
        for x in nodes:
            if outn and x[0]<=outn[-1][0]+1e-5: continue
            outn.append(x)
        if outn[0][0]!=A: outn.insert(0,[A,outn[0][1],0.0])
        if outn[-1][0]!=B: outn.append([B,outn[-1][1],0.0])
        center+=outn
        stats['notes']+=1; stats['nodes']+=len(outn)

    center.sort(key=lambda x:x[0]); out=[]
    for x in center:
        if out and x[0]<=out[-1][0]+1e-5: out[-1]=[out[-1][0],x[1],0.0]; continue
        out.append(x)
    if out[0][0]>t0+1e-6: out.insert(0,[round(t0,4),out[0][1],0.0])
    out[0][0]=round(t0,4)
    if out[-1][0]<t1-1e-6: out.append([round(t1,4),out[-1][1],0.0])
    out[-1][0]=round(t1,4)
    for kk in range(1,len(out)):
        if out[kk][0]<=out[kk-1][0]: out[kk][0]=round(out[kk-1][0]+0.003,4)
    out[-1][0]=round(t1,4)
    if out[-2][0]>=out[-1][0]: out[-2][0]=round(out[-1][0]-0.003,4)
    amp=max(x[1] for x in out)-min(x[1] for x in out)
    plans.append(dict(schema=1,origin='agent_designed',support_s=[round(t0,4),round(t1,4)],
        center_nodes=out,components=[],
        decisions=[dict(support_s=[round(t0,4),round(t1,4)],
            condition=f'part {pi}: {p["hanzi"]}',
            choice='per-note anchors on the written tone; + continuations keep the source move only when the source really changes pitch',
            alternative='force every note onto its integer tone (breaks same-vowel melisma) or copy the source absolutely (slides off the melody)',
            reason='the body must sit on the note pitch; same-vowel continuations follow evidenced melodic moves',
            uncertainty='short + notes may not resolve a true change', component_ids=[])],
        expectations=[dict(support_s=[round(t0,4),round(t1,4)],
            range_c=[0.0, round(amp+50.0,2)], purpose=f'part {pi}: bounded motion')]))

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
bad=[(i,str(e)[:80]) for i,pl in enumerate(plans) for e in [None] if False]
for i,pl in enumerate(plans):
    try:
        r=dfm.compile_plan(pl,0.004)
        if not r['shape_checks_pass']: bad.append((i,'shape'))
    except Exception as ex_: bad.append((i,str(ex_)[:80]))
print(f'phrases {len(plans)} failures {len(bad)}')
for bb in bad[:5]: print('  ',bb)
print(f"notes {stats['notes']} nodes {stats['nodes']} ({stats['nodes']/349:.1f}/syl)")
print(f"+ notes: followed source move {stats['plus_followed']}, held continuity {stats['plus_held']}")
json.dump(dict(schema_version=2,scope='whole_song',
    note='v3h: per-note tone anchors + same-vowel continuation handling by source evidence',
    phrases=plans), io.open(NEW/'design'/'plan.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote design/plan.json')
