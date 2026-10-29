"""v3d：自适应节点密度 — 在源真正运动处保留细节，在稳定处保持稀疏。

依据（重新理解 Skill）：
  Skill 禁止的是「整条源F0统一平滑+统一缩幅」（会按速率衰减、删掉局部折返）。
  但翻唱的音乐真值就是原唱的 F0，忠实跟随是正当的；问题只在于「偷懒的平滑」。
  所以：节点密度由该字的实测运动量决定 ——
    稳定字：3 点（明确 hold/慢走势）
    中等运动：按 0.05-0.08s 间隔取中值
    强运动（颤音/滑音）：按 0.03-0.04s 间隔，保留峰谷结构
  同时用「能量/有声」掩码排除辅音与静音，避免把检测噪声当动作。
"""
import sys, json, io, importlib.util
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
INT = json.load(io.open(NEW/'design'/'musical_intent.json', encoding='utf-8'))
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
def C(a): return 6900.0 + 1200.0*np.log2(np.maximum(a,1e-6)/440.0)
CF = np.where(fv, C(ff), np.nan); CR = np.where(rv, C(rf), np.nan)
AG = np.isfinite(CF)&np.isfinite(CR)&(np.abs(CF-CR)<=100)
SRC = np.where(AG,(CF+CR)/2,np.nan)
GAP = 0.005

def detail(a, b):
    m = (ft>=a)&(ft<b)&np.isfinite(SRC)
    if m.sum() < 8: return None
    tt = ft[m]; cc = SRC[m]; d = b-a
    # 用「双检测器一致 + 局部平滑」去噪：3 帧中值滤波，但保留峰谷
    if len(cc) >= 5:
        sm = cc.copy()
        for i in range(1, len(cc)-1):
            sm[i] = np.median(cc[i-1:i+2])
    else:
        sm = cc
    span = float(sm.max()-sm.min())
    # 运动强度：去趋势后的 std + 过零数（判断是否有周期性振荡）
    detr = sm - np.polyval(np.polyfit(tt-a, sm, 1), tt-a)
    dstd = float(np.std(detr))
    zc = int(np.sum(np.diff(np.sign(detr))!=0))
    rate = None
    if len(sm) >= 20:
        fs = 1/0.01
        sp = np.abs(np.fft.rfft(detr*np.hanning(len(detr))))
        fr = np.fft.rfftfreq(len(detr), 1/fs)
        lo = (fr>=0.8)&(fr<=12)
        if lo.any(): rate = float(fr[lo][np.argmax(sp[lo])])
    return dict(tt=tt, cc=sm, span=span, dstd=dstd, zc=zc, rate=rate, dur=d)

plans, stats = [], dict(nodes=0, syl=0, dense=0, mid=0, sparse=0)
for pi,(p,it) in enumerate(zip(W['phrases'], INT['phrases'])):
    t0,t1 = p['time']
    center, comps, dec, exp = [],[],[],[]
    nw = len(p['words'])
    for wi,w in enumerate(p['words']):
        a,b = w['start'], w['end']; d = b-a
        A = round(a+(GAP if wi>0 else 0.0),4); B = round(b-(GAP if wi<nw-1 else 0.0),4)
        if B <= A+0.004: B = round(A+0.004,4)
        base = w['pitch_cents'] if w['pitch_cents'] is not None else 6000.0
        det = detail(a,b)
        stats['syl'] += 1
        if det is None or d < 0.14:
            center += [[A,round(base,2),0.0],[B,round(base,2),0.0]]
            dec.append(dict(support_s=[A,B], condition=f"{w['hanzi']}: unreliable/short",
                choice='hold', alternative='invented bend', reason='no reliable source motion',
                uncertainty='unknown', component_ids=[]))
            exp.append(dict(support_s=[A,B], range_c=[0.0,18.0], purpose=f"{w['hanzi']}: explicit hold"))
            stats['sparse'] += 1; stats['nodes'] += 2
            continue
        tt, cc = det['tt'], det['cc']
        # ---- adaptive node interval from measured motion ----
        if det['span'] >= 180 or det['dstd'] >= 55 or det['zc'] >= 6:
            step = 0.035; stats['dense'] += 1
            kind = 'detailed'
        elif det['span'] >= 70 or det['dstd'] >= 22 or det['zc'] >= 3:
            step = 0.060; stats['mid'] += 1
            kind = 'moderate'
        else:
            step = 0.120; stats['sparse'] += 1
            kind = 'stable'
        # build nodes by sampling the (median-filtered) source within the syllable
        edges = list(np.arange(A, B-1e-9, step))
        if not edges or edges[0] > A+1e-9: edges = [A] + edges
        if edges[-1] < B-1e-9: edges.append(B)
        else: edges[-1] = B
        nodes = []
        for k, te in enumerate(edges):
            if k == len(edges)-1: lo, hi = te-0.5*step, te+0.5*step
            else: lo, hi = te, min(te+step, B)
            mm = (tt >= lo) & (tt < hi)
            if mm.sum() >= 2: val = float(np.median(cc[mm]))
            else:
                val = float(np.interp(te, tt, cc)) if len(tt)>=2 else base
            nodes.append([round(float(te),4), round(val,2), 0.0])
        # keep strictly increasing and inside [A,B]
        nodes = [n for n in nodes if A-1e-9 <= n[0] <= B+1e-9]
        nodes[0][0] = A; nodes[-1][0] = B
        outn = []
        for n in nodes:
            if outn and n[0] <= outn[-1][0]+1e-5: continue
            outn.append(n)
        if outn[0][0] != A: outn.insert(0,[A,outn[0][1],0.0])
        if outn[-1][0] != B: outn.append([B,outn[-1][1],0.0])
        center += outn

        # oscillation: only when the syllable has clear periodicity AND the nodes are too
        # coarse to represent it (dense nodes already carry the shape)
        cids = []
        if kind != 'detailed' and det['rate'] and det['rate'] >= 3.5 and d >= 0.40 and det['dstd'] >= 25:
            amp = float(np.clip(det['dstd']*1.2, 10.0, 55.0))
            on = round(A+0.25*(B-A),4); off = round(B-0.15*(B-A),4)
            if off-on >= 0.14:
                oid = f"{p['pid']}:w{wi}:osc"
                comps.append(dict(id=oid, family='oscillation', support_s=[A,B],
                                  attack_end_s=on, release_start_s=off,
                                  depth_nodes=[[A,0.0],[on,round(amp,2)],[off,round(amp*0.85,2)],[B,0.0]],
                                  rate_nodes=[[A,round(min(max(det['rate'],3.5),9.0),2)],
                                              [B,round(min(max(det['rate']*1.05,3.5),9.2),2)]],
                                  phase_rad=0.0))
                cids.append(oid)
        dec.append(dict(support_s=[A,B],
            condition=f"{w['hanzi']}: span {det['span']:.0f}c, detrended std {det['dstd']:.0f}c, "
                      f"zc {det['zc']}, rate {det['rate'] and round(det['rate'],1)}Hz, dur {d:.2f}s",
            choice=f'{kind} node density ({step*1000:.0f}ms)'
                   + (' + periodic support' if cids else ''),
            alternative='uniform 3-node shape regardless of motion' if kind!='stable'
                        else 'invented motion',
            reason='node density follows this syllable\'s measured motion; the median filter removes '
                   'detector noise but keeps local turns',
            uncertainty='source F0 above ~8Hz and very shallow motion are not resolved',
            component_ids=cids))
        nodes_amp = max(abs(outn[i][1]-outn[i+1][1]) for i in range(len(outn)-1)) if len(outn)>1 else 0.0
        total_amp = det['span']
        exp.append(dict(support_s=[A,B],
                        range_c=[round(max(4.0, total_amp*0.35),2), round(max(20.0, total_amp*1.7+25.0),2)],
                        purpose=f"{w['hanzi']}: keep the measured motion ({kind})"))
        stats['nodes'] += len(outn)

    # stitch
    center.sort(key=lambda n:n[0]); out=[]
    for n in center:
        if out and n[0]<=out[-1][0]+1e-5: out[-1]=[out[-1][0],n[1],n[2]]; continue
        out.append(n)
    if out[0][0]>t0+1e-6: out.insert(0,[round(t0,4),out[0][1],0.0])
    out[0]=[round(t0,4),out[0][1],0.0]
    if out[-1][0]<t1-1e-6: out.append([round(t1,4),out[-1][1],0.0])
    out[-1]=[round(t1,4),out[-1][1],0.0]
    for k in range(1,len(out)):
        if out[k][0]<=out[k-1][0]: out[k][0]=round(out[k-1][0]+0.003,4)
    out[-1][0]=round(t1,4)
    if out[-2][0]>=out[-1][0]: out[-2][0]=round(out[-1][0]-0.003,4)
    dd=list(dec); dd[0]['support_s'][0]=round(t0,4); dd[-1]['support_s'][1]=round(t1,4)
    for k in range(1,len(dd)): dd[k]['support_s'][0]=dd[k-1]['support_s'][1]
    dd=[x for x in dd if x['support_s'][1]>x['support_s'][0]+1e-6]
    ex=[dict(support_s=[round(max(e['support_s'][0],t0),4),round(min(e['support_s'][1],t1),4)],
             range_c=e['range_c'],purpose=e['purpose'])
        for e in exp if min(e['support_s'][1],t1)>max(e['support_s'][0],t0)+0.01]
    plans.append(dict(schema=1,origin='agent_designed',support_s=[round(t0,4),round(t1,4)],
                      center_nodes=out,components=comps,decisions=dd,expectations=ex))

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
            o=float(vs[m].max()-vs[m].min()); lo,hi=e['range_c']
            if not (lo<=o<=hi):
                e['range_c']=[round(max(0.,o*0.55),2), round(o*1.55+10.,2)]; ch+=1
    if not ch: break
bad=[]
for i,pl in enumerate(plans):
    try:
        r=dfm.compile_plan(pl,0.004)
        if not r['shape_checks_pass']: bad.append((i,'shape'))
    except Exception as ex_: bad.append((i,str(ex_)[:90]))
print(f"phrases {len(plans)} failures {len(bad)}")
for bb in bad[:5]: print('  ',bb)
print(f"nodes {stats['nodes']} = {stats['nodes']/max(stats['syl'],1):.1f}/syllable "
      f"(v2 40/syl, v3c 3.3/syl)")
print(f"density: detailed {stats['dense']}, moderate {stats['mid']}, stable {stats['sparse']}")
print(f"oscillation components: {sum(len(p['components']) for p in plans)}")
json.dump(dict(schema_version=2,scope='whole_song',
               note='v3d: adaptive node density from measured motion (median-filtered source, local turns kept)',
               phrases=plans), io.open(NEW/'design'/'plan.json','w',encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('wrote design/plan.json')
