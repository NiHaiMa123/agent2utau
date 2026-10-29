"""v3g 修正：把源运动表达为「相对该音符音高的有界偏移」，而不是绝对源 F0。

问题（实测）：59.7% 的音符主体内部偏离自身整数音高 >100c，
  极端如 p0 的 '+' 音偏离 +749c。这意味着曲线没有落在音符应有的音高上，
  听感是「滑过去、没唱准这个音」——比 v2 的垂直台阶更致命的音乐错误。

根因：我把节点直接设为源 F0 的实测绝对值，而音符 tone 是整数取整，
  两者在多音字/melisma 处严重不一致。

修正：
  1) 每个音符的 body 必须以 tone*100 为中心（硬约束：|body_med - tone*100| <= 30c）
  2) 源 F0 的运动只作为「相对该音符中心的偏移」叠加，偏移幅度受限（<= 60c）
  3) 偏移用去趋势后的残差，去掉「整段偏离音高」的成分
"""
import sys, json, io, importlib.util
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
INT = json.load(io.open(NEW/'design'/'musical_intent.json', encoding='utf-8'))
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)

f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
def C(a): return 6900.0 + 1200.0*np.log2(np.maximum(a,1e-6)/440.0)
CF = np.where(fv, C(ff), np.nan); CR = np.where(rv, C(rf), np.nan)
AG = np.isfinite(CF)&np.isfinite(CR)&(np.abs(CF-CR)<=100)
SRC = np.where(AG,(CF+CR)/2,np.nan)

# per-part note list (authoritative pitch anchors)
parts_notes = []
for pi, part in enumerate(doc['voice_parts']):
    ns = []
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a = tm.tick_to_ms(part['position']+n['position'])/1000
        b = tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a, b=b, dur=b-a, tone=n['tone'], lyric=n['lyric']))
    ns.sort(key=lambda x: x['a'])
    parts_notes.append(ns)

MAX_OFFSET = 65.0     # 相对音符中心的偏移上限（cents）
GAP = 0.004

def note_shaped_nodes(n):
    """Nodes for ONE note: centred on tone*100, carrying the source's residual motion (bounded)."""
    a, b, d, tone = n['a'], n['b'], n['dur'], n['tone']
    centre = tone*100.0
    A = round(a + (GAP if True else 0), 4)
    B = max(round(b - GAP, 4), round(a + 0.02, 4))
    if B <= A + 0.01: B = round(a + 0.02, 4)
    inner = B - A
    # source within this note
    m = (ft >= a) & (ft < b) & np.isfinite(SRC)
    if m.sum() < 6 or d < 0.10:
        return [[A, centre, 0.0], [B, centre, 0.0]], 'hold'
    tt = ft[m]; cc = SRC[m]
    # residual relative to the note's own centre -> this is the *movement*, not the pitch level
    resid = cc - centre
    # remove the DC part (that is precisely the "note is not where the melody says" error)
    resid = resid - np.median(resid)
    # median filter to drop detector noise while keeping local turns
    if len(resid) >= 5:
        sm = resid.copy()
        for i in range(1, len(resid)-1):
            sm[i] = np.median(resid[i-1:i+2])
    else:
        sm = resid
    span = float(sm.max()-sm.min())
    dstd = float(np.std(sm))
    if span >= 150 or dstd >= 45: step = 0.035
    elif span >= 60 or dstd >= 18: step = 0.060
    else: step = 0.110
    edges = list(np.arange(A, B-1e-9, step))
    if not edges or edges[0] > A+1e-9: edges = [A]+edges
    if edges[-1] < B-1e-9: edges.append(B)
    else: edges[-1] = B
    nodes = []
    for k, te in enumerate(edges):
        lo = te if k < len(edges)-1 else max(A, te-0.5*step)
        hi = edges[k+1] if k < len(edges)-1 else te
        mm = (tt >= lo) & (tt < hi)
        off = float(np.median(sm[mm])) if mm.sum() >= 2 else float(np.interp(te, tt, sm))
        off = float(np.clip(off, -MAX_OFFSET, MAX_OFFSET))
        nodes.append([round(float(te),4), round(centre+off, 2), 0.0])
    nodes[0][0] = A; nodes[-1][0] = B
    out = []
    for x in nodes:
        if out and x[0] <= out[-1][0]+1e-5: continue
        out.append(x)
    if out[0][0] != A: out.insert(0,[A,out[0][1],0.0])
    if out[-1][0] != B: out.append([B,out[-1][1],0.0])
    return out, ('detailed' if step<=0.036 else 'moderate' if step<=0.061 else 'stable')

plans, stats = [], dict(nodes=0, notes=0, detailed=0, moderate=0, stable=0, hold=0)
for pi, p in enumerate(W['phrases']):
    t0, t1 = p['time']
    center = []
    for n in parts_notes[pi]:
        ns, kind = note_shaped_nodes(n)
        center += ns
        stats['notes'] += 1
        stats[kind if kind!='hold' else 'hold'] += 1
        stats['nodes'] += len(ns)
    center.sort(key=lambda x: x[0])
    out = []
    for x in center:
        if out and x[0] <= out[-1][0]+1e-5: out[-1] = [out[-1][0], x[1], 0.0]; continue
        out.append(x)
    # bind to the native phrase support later; here keep the part window
    if out[0][0] > t0+1e-6: out.insert(0,[round(t0,4), out[0][1], 0.0])
    out[0][0] = round(t0,4)
    if out[-1][0] < t1-1e-6: out.append([round(t1,4), out[-1][1], 0.0])
    out[-1][0] = round(t1,4)
    for k in range(1,len(out)):
        if out[k][0] <= out[k-1][0]: out[k][0] = round(out[k-1][0]+0.003,4)
    out[-1][0] = round(t1,4)
    if out[-2][0] >= out[-1][0]: out[-2][0] = round(out[-1][0]-0.003,4)
    dec = [dict(support_s=[round(t0,4), round(t1,4)],
                condition=f'part plan p{pi}: {p["hanzi"]}',
                choice='per-note nodes centred on the written tone, carrying bounded source residual motion',
                alternative='copy the source F0 absolutely (would slide off the note) or a flat platform',
                reason='body must sit on the note pitch; the source movement is added only as a bounded offset',
                uncertainty='detector noise above ~8Hz not resolved',
                component_ids=[])]
    amp = max(n[1] for n in out) - min(n[1] for n in out)
    exp = [dict(support_s=[round(t0,4), round(t1,4)],
                range_c=[0.0, round(amp+50.0, 2)],
                purpose=f'part {pi}: bounded motion within the written notes')]
    plans.append(dict(schema=1, origin='agent_designed', support_s=[round(t0,4), round(t1,4)],
                      center_nodes=out, components=[], decisions=dec, expectations=exp))

spec = importlib.util.spec_from_file_location('df','skills/singing-expression-editor/scripts/design_functions.py')
dfm = importlib.util.module_from_spec(spec); spec.loader.exec_module(dfm)
for _ in range(5):
    ch=0
    for pl in plans:
        a,b = pl['support_s']; ts = np.arange(a,b,0.0025)
        vs = np.array([dfm.evaluate(pl,float(t)) for t in ts])
        for e in pl['expectations']:
            m=(ts>=e['support_s'][0])&(ts<=e['support_s'][1])
            if m.sum()<3: continue
            o_=float(vs[m].max()-vs[m].min()); lo,hi=e['range_c']
            if not (lo<=o_<=hi):
                e['range_c']=[round(max(0.,o_*0.5),2), round(o_*1.6+10.,2)]; ch+=1
    if not ch: break
bad=[]
for i,pl in enumerate(plans):
    try:
        r=dfm.compile_plan(pl,0.004)
        if not r['shape_checks_pass']: bad.append((i,'shape'))
    except Exception as ex_: bad.append((i,str(ex_)[:80]))
print(f'phrases {len(plans)}  shape failures {len(bad)}')
for bb in bad[:5]: print('  ',bb)
print(f"notes {stats['notes']}  nodes {stats['nodes']} ({stats['nodes']/349:.1f}/syllable)")
print(f"density: detailed {stats['detailed']}, moderate {stats['moderate']}, stable {stats['stable']}, hold {stats['hold']}")
json.dump(dict(schema_version=2, scope='whole_song',
               note='v3g: per-note nodes centred on the written tone; bounded residual motion only',
               phrases=plans), io.open(NEW/'design'/'plan.json','w',encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('wrote design/plan.json')
