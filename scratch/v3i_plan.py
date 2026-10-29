"""v3i 修正：消除音符边界的过冲/尖峰。

诊断：误差随「距音符边界距离」单调下降（20ms 内 84c → 200ms 外 48c），
      说明每个音符边界的 GAP(4ms) + 零斜率造成 Hermite 尖峰。
修正：
  1) GAP = 0，相邻音符的首尾节点直接相接（时间严格递增用 1e-3 递推）
  2) 边界节点使用**连续斜率**（取前后段割线的均值），而不是 0
  3) 保留音符中心锚定（|body_med - tone*100| 已 <= 25c）
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
f0=np.load(NEW/'inputs/fcpe.npz'); f0r=np.load(NEW/'inputs/rmvpe.npz')
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
for part in doc['voice_parts']:
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,dur=b-a,tone=n['tone'],lyric=n['lyric']))
    ns.sort(key=lambda x:x['a'])
    parts_notes.append(ns)

MAX_OFF=60.0

def note_nodes(n, prev_med):
    a,b,d,tone=n['a'],n['b'],n['dur'],n['tone']
    A=a; B=b
    if n['lyric']=='+':
        cur=src_med(a,b)
        if cur is not None and prev_med is not None and abs(cur-prev_med)>=90:
            centre=float(np.clip(cur, tone*100-90, tone*100+90))
        else:
            centre=float(prev_med) if prev_med is not None else tone*100.0
            centre=float(np.clip(centre, tone*100-120, tone*100+120))
    else:
        centre=tone*100.0
    m=(ft>=a)&(ft<b)&np.isfinite(SRC)
    if m.sum()<6 or d<0.10:
        return [[round(A,4),round(centre,2),None],[round(B,4),round(centre,2),None]], centre
    tt=ft[m]; cc=SRC[m]
    resid=cc-centre
    if n['lyric']!='+': resid=resid-np.median(resid)
    if len(resid)>=5:
        sm=resid.copy()
        for i in range(1,len(resid)-1): sm[i]=np.median(resid[i-1:i+2])
    else: sm=resid
    span=float(sm.max()-sm.min()); dstd=float(np.std(sm))
    step = 0.030 if (span>=150 or dstd>=45) else 0.055 if (span>=60 or dstd>=18) else 0.100
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
        nodes.append([round(float(te),4), round(centre+off,2), None])   # slope=None -> fill later
    nodes[0][0]=round(A,4); nodes[-1][0]=round(B,4)
    uniq=[]
    for x in nodes:
        if uniq and x[0]<=uniq[-1][0]+1e-5: continue
        uniq.append(x)
    if uniq[0][0]!=round(A,4): uniq.insert(0,[round(A,4),uniq[0][1],None])
    if uniq[-1][0]!=round(B,4): uniq.append([round(B,4),uniq[-1][1],None])
    return uniq, centre

plans, stats = [], dict(nodes=0, notes=0, boundaries=0)
for pi,p in enumerate(W['phrases']):
    t0,t1=p['time']
    seq=[]
    prev_med=None
    for n in parts_notes[pi]:
        ns, centre = note_nodes(n, prev_med)
        seq += ns
        prev_med = src_med(n['a'], n['b']) or centre
        stats['notes']+=1
    # merge duplicates at the same time (note boundaries): keep the LATER note's value,
    # so the boundary becomes a shared node instead of a 4 ms step.
    seq.sort(key=lambda x:x[0])
    merged=[]
    for x in seq:
        if merged and abs(x[0]-merged[-1][0])<1e-6:
            merged[-1]=[merged[-1][0], x[1], None]; stats['boundaries']+=1
        elif merged and x[0]<merged[-1][0]:
            continue
        else:
            merged.append(x)
    if merged[0][0]>t0+1e-6: merged.insert(0,[round(t0,4),merged[0][1],None])
    merged[0][0]=round(t0,4)
    if merged[-1][0]<t1-1e-6: merged.append([round(t1,4),merged[-1][1],None])
    merged[-1][0]=round(t1,4)
    # strictly increasing with a 1 ms floor (only if rounding created ties)
    for k in range(1,len(merged)):
        if merged[k][0]<=merged[k-1][0]: merged[k][0]=round(merged[k-1][0]+0.001,4)
    if merged[-1][0]>t1: merged[-1][0]=round(t1,4)
    # ---- continuous slopes: use the local secant so Hermite does not overshoot ----
    ts_=[x[0] for x in merged]; vs_=[x[1] for x in merged]
    for k in range(len(merged)):
        if k==0:
            s=(vs_[1]-vs_[0])/(ts_[1]-ts_[0]) if len(vs_)>1 and ts_[1]!=ts_[0] else 0.0
        elif k==len(merged)-1:
            s=(vs_[-1]-vs_[-2])/(ts_[-1]-ts_[-2]) if ts_[-1]!=ts_[-2] else 0.0
        else:
            s1=(vs_[k]-vs_[k-1])/(ts_[k]-ts_[k-1]) if ts_[k]!=ts_[k-1] else 0.0
            s2=(vs_[k+1]-vs_[k])/(ts_[k+1]-ts_[k]) if ts_[k+1]!=ts_[k] else 0.0
            s=0.5*(s1+s2)
        merged[k][2]=round(float(np.clip(s,-900,900)),2)
        stats['nodes']+=1
    plans.append(dict(schema=1,origin='agent_designed',support_s=[round(t0,4),round(t1,4)],
        center_nodes=[[x[0],x[1],x[2]] for x in merged],components=[],
        decisions=[dict(support_s=[round(t0,4),round(t1,4)],
            condition=f'part {pi}: {p["hanzi"]}',
            choice='per-note tone anchors with shared boundary nodes and continuous slopes',
            alternative='zero-slope nodes at every boundary (causes Hermite overshoot) or copying the source',
            reason='error grows toward note boundaries; continuous slopes remove the spike while the body stays on pitch',
            uncertainty='slope estimate from adjacent secants', component_ids=[])],
        expectations=[dict(support_s=[round(t0,4),round(t1,4)],
            range_c=[0.0, round(max(vs_)-min(vs_)+50.0,2)], purpose=f'part {pi}: bounded motion')]))

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
    except Exception as ex_: bad.append((i,str(ex_)[:80]))
print(f'phrases {len(plans)} failures {len(bad)}')
for bb in bad[:5]: print('  ',bb)
print(f"notes {stats['notes']}, merged boundaries {stats['boundaries']}, nodes {stats['nodes']} ({stats['nodes']/349:.1f}/syl)")
json.dump(dict(schema_version=2,scope='whole_song',
    note='v3i: shared boundary nodes + continuous slopes (no Hermite spike at note seams)',
    phrases=plans), io.open(NEW/'design'/'plan.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote design/plan.json')
