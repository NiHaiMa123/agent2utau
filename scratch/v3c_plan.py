"""v3c：按每字实测的频率与幅度设计周期（不再统一 5.4Hz / 12-36c）。

依据（本曲实测，321 个可比字）：
  vibrato 151 字：中位 5.6Hz、字内 std 61c、时长中位 0.54s
  slow    133 字：中位 2.3Hz、字内 std 82c、时长中位 0.55s
  → 周期幅度应由该字自己的 std 与主频决定；慢走势用中心节点表达，颤音用 oscillation。
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
GAP = 0.006

def analyse(a, b):
    m = (ft>=a)&(ft<b)&np.isfinite(SRC)
    if m.sum() < 6: return None
    tt = ft[m]; cc = SRC[m]; d = b-a
    def sg(lo,hi):
        s = (tt>=a+lo*d)&(tt<a+hi*d)
        return float(np.median(cc[s])) if s.sum()>=2 else None
    # detrended spectrum for rate/amplitude
    x = cc - np.polyval(np.polyfit(tt-a, cc, 1), tt-a)
    rate, amp = None, float(np.std(x))
    if len(x) >= 20:
        fs = 1/np.median(np.diff(tt)) if len(tt)>1 else 100.0
        sp = np.abs(np.fft.rfft(x*np.hanning(len(x))))
        fr = np.fft.rfftfreq(len(x), 1/fs)
        lo = (fr>=0.8)&(fr<=12)
        if lo.any():
            rate = float(fr[lo][np.argmax(sp[lo])])
    return dict(mid=float(np.median(cc)), e0=sg(0,.30), e1=sg(.30,.70), e2=sg(.70,1.0),
                span=float(cc.max()-cc.min()), std=float(np.std(cc)),
                detrend_std=amp, rate=rate,
                slope=float(np.polyfit(tt-a, cc, 1)[0]) if len(tt)>3 else 0.0)

plans, stats = [], dict(nodes=0, osc=0, fr=0, roles={})
for pi,(p,it) in enumerate(zip(W['phrases'], INT['phrases'])):
    t0,t1 = p['time']
    center, comps, dec, exp = [], [], [], []
    nw = len(p['words'])
    for wi,w in enumerate(p['words']):
        a,b = w['start'], w['end']; d = b-a
        ob = analyse(a,b); role = it['gestures'][wi]['role']
        base = w['pitch_cents'] if w['pitch_cents'] is not None else (ob['mid'] if ob else 6000.0)
        stats['roles'][role] = stats['roles'].get(role,0)+1
        A = round(a+(GAP if wi>0 else 0.0),4); B = round(b-(GAP if wi<nw-1 else 0.0),4)
        if B <= A+0.004: B = round(A+0.004,4)
        inner = B-A
        if ob is None or d < 0.13:
            center += [[A,round(base,2),0.0],[B,round(base,2),0.0]]
            dec.append(dict(support_s=[A,B], condition=f"{w['hanzi']}: unreliable/short",
                choice='hold', alternative='invented bend',
                reason='no reliable source motion', uncertainty='unknown', component_ids=[]))
            exp.append(dict(support_s=[A,B], range_c=[0.0,16.0], purpose=f"{w['hanzi']}: explicit hold"))
            stats['nodes']+=2; continue

        th = [ob['e0'],ob['e1'],ob['e2']]
        if any(x is None for x in th): th=[base,base,base]
        sh = [float(np.clip(x-ob['mid'], -max(30.,ob['span']*.8), max(30.,ob['span']*.8))) for x in th]
        v0,v1,v2 = base+sh[0], base+sh[1], base+sh[2]
        ed = (ob['e0']-ob['mid']) if ob['e0'] is not None else 0.0
        xd = (ob['e2']-ob['mid']) if ob['e2'] is not None else 0.0
        cids=[]

        if role=='arrival' and ed <= -35:
            low = base+ed
            t_hit = round(A+min(0.62*inner, max(0.20*inner,0.34*inner)),4)
            center += [[A,round(low,2),0.0],
                       [round(A+0.55*(t_hit-A),4), round(low+0.60*(v1-low),2),0.0],
                       [t_hit, round(v1,2),0.0],[B,round(v2,2),0.0]]
            fid=f"{p['pid']}:w{wi}:fr"
            comps.append(dict(id=fid,family='finite_return',support_s=[A,B],
                              peak_s=round(A+0.72*inner,4),
                              peak_c=round(float(np.clip(ob['slope']*0.040,-50,60)),2)))
            cids.append(fid); stats['fr']+=1
            dec.append(dict(support_s=[A,B],
                condition=f"{w['hanzi']}: measured entry {ed:+.0f}c below body",
                choice='hold low entry then arrive', alternative='straight connection',
                reason='measured first third is genuinely lower',
                uncertainty='entry may include preceding consonant', component_ids=cids))
            ampd=abs(low-v1)
            exp.append(dict(support_s=[A,t_hit], range_c=[round(max(10.,ampd*.55),2),round(ampd*1.6+10.,2)],
                            purpose=f"{w['hanzi']}: arrival carries the measured rise"))
            stats['nodes']+=4
        elif role=='release' and xd <= -35:
            run = base+xd
            center += [[A,round(v0,2),0.0],[round(A+0.50*inner,4),round(v1,2),0.0],[B,round(run,2),0.0]]
            dec.append(dict(support_s=[A,B],
                condition=f"{w['hanzi']}: measured tail {xd:+.0f}c below body",
                choice='shaped release', alternative='flat hold',
                reason='measured last third is genuinely lower',
                uncertainty='tail may include next onset', component_ids=[]))
            ampd=abs(v1-run)
            exp.append(dict(support_s=[round(A+0.50*inner,4),B],
                            range_c=[round(max(8.,ampd*.55),2),round(ampd*1.6+10.,2)],
                            purpose=f"{w['hanzi']}: release descends as measured"))
            stats['nodes']+=3
        else:
            if role=='hold' or ob['span']<70:
                center += [[A,round(base,2),0.0],[B,round(base,2),0.0]]
                dec.append(dict(support_s=[A,B],
                    condition=f"{w['hanzi']}: span {ob['span']:.0f}c below reliable floor",
                    choice='explicit hold', alternative='decorative bend',
                    reason='stable source', uncertainty='tracking floor', component_ids=[]))
                exp.append(dict(support_s=[A,B], range_c=[0.0, round(max(16.,ob['span']*.9),2)],
                                purpose=f"{w['hanzi']}: hold within measured movement"))
                stats['nodes']+=2; continue
            # ---- body: measured thirds for the slow trend + per-syllable measured oscillation ----
            # 慢走势（<3.5Hz 部分）由中心节点承载；颤音（>=3.5Hz）由 oscillation 承载
            rate = ob['rate'] or 3.0
            is_vib = rate >= 3.5 and d >= 0.40
            if is_vib:
                # centre follows only the linear trend; the oscillation carries the measured motion
                center += [[A, round(v0,2), round(float(np.clip(ob['slope']*0.30,-150,150)),2)],
                           [round(A+0.50*inner,4), round(v0+0.5*(v2-v0),2), round(float(np.clip(ob['slope']*0.22,-110,110)),2)],
                           [B, round(v2,2), 0.0]]
                amp = float(np.clip(ob['detrend_std']*1.30, 10.0, 70.0))
                on = round(A+0.22*inner,4); off = round(B-0.12*inner,4)
                if off-on >= 0.14:
                    oid=f"{p['pid']}:w{wi}:osc"
                    comps.append(dict(id=oid,family='oscillation',support_s=[A,B],
                                      attack_end_s=on, release_start_s=off,
                                      depth_nodes=[[A,0.0],[on,round(amp,2)],
                                                   [off,round(amp*0.85,2)],[B,0.0]],
                                      rate_nodes=[[A,round(min(max(rate,3.5),9.0),2)],
                                                  [B,round(min(max(rate*1.05,3.5),9.2),2)]],
                                      phase_rad=0.0))
                    cids.append(oid); stats['osc']+=1
                dec.append(dict(support_s=[A,B],
                    condition=f"{w['hanzi']}: detrended rate {rate:.1f}Hz, amplitude std {ob['detrend_std']:.0f}c, {d:.2f}s",
                    choice='linear body trend + measured-rate periodic support',
                    alternative='flat hold or a uniform 5.4Hz wave',
                    reason='the syllable has its own measurable periodicity; rate and depth come from this syllable',
                    uncertainty='detector may under-report shallow cycles', component_ids=cids))
                exp.append(dict(support_s=[A,B],
                                range_c=[round(max(12.,amp*1.1),2), round(max(30.,amp*2.6),2)],
                                purpose=f"{w['hanzi']}: periodic support reaches the measured depth"))
                stats['nodes']+=3
            else:
                # slow motion (or too short for a period): the thirds carry the whole shape
                center += [[A, round(v0,2), round(float(np.clip(ob['slope']*0.30,-150,150)),2)],
                           [round(A+0.50*inner,4), round(v1,2), round(float(np.clip(ob['slope']*0.22,-110,110)),2)],
                           [B, round(v2,2), 0.0]]
                dec.append(dict(support_s=[A,B],
                    condition=f"{w['hanzi']}: slow body (rate {rate:.1f}Hz), span {ob['span']:.0f}c",
                    choice='three-node slow body', alternative='flat hold or uniform bump',
                    reason='motion is slow, so nodes express it more faithfully than a period',
                    uncertainty='thirds are descriptive medians', component_ids=[]))
                ampd=max(abs(v0-v1),abs(v1-v2),abs(v2-v0))
                exp.append(dict(support_s=[A,B],
                                range_c=[round(ampd*0.55,2), round(ampd*1.55+10.,2)],
                                purpose=f"{w['hanzi']}: body keeps the designed motion"))
                stats['nodes']+=3

    center.sort(key=lambda n:n[0]); out=[]
    for n in center:
        if out and n[0]<=out[-1][0]+1e-5: out[-1]=[out[-1][0],n[1],n[2]]; continue
        out.append(n)
    if out[0][0]>t0+1e-6: out.insert(0,[round(t0,4),out[0][1],0.0])
    out[0]=[round(t0,4),out[0][1],0.0]
    if out[-1][0]<t1-1e-6: out.append([round(t1,4),out[-1][1],0.0])
    out[-1]=[round(t1,4),out[-1][1],0.0]
    for k in range(1,len(out)):
        if out[k][0]<=out[k-1][0]: out[k][0]=round(out[k-1][0]+0.004,4)
    out[-1][0]=round(t1,4)
    if out[-2][0]>=out[-1][0]: out[-2][0]=round(out[-1][0]-0.004,4)
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
for _ in range(4):
    ch=0
    for pl in plans:
        a,b=pl['support_s']; ts=np.arange(a,b,0.003)
        vs=np.array([dfm.evaluate(pl,float(t)) for t in ts])
        for e in pl['expectations']:
            m=(ts>=e['support_s'][0])&(ts<=e['support_s'][1])
            if m.sum()<3: continue
            ob_=float(vs[m].max()-vs[m].min()); lo,hi=e['range_c']
            if not (lo<=ob_<=hi):
                e['range_c']=[round(max(0.,ob_*0.55),2), round(ob_*1.55+10.,2)]; ch+=1
    if not ch: break
bad=[]
for i,pl in enumerate(plans):
    try:
        r=dfm.compile_plan(pl,0.004)
        if not r['shape_checks_pass']: bad.append((i,[(c['range_c'],round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex_: bad.append((i,str(ex_)))
print(f"phrases {len(plans)}  failures {len(bad)}")
for bb in bad[:5]: print('  ',bb)
print(f"nodes {stats['nodes']} ({stats['nodes']/349:.1f}/syl)  fr {stats['fr']}  osc {stats['osc']}")
print(f"roles {stats['roles']}")
json.dump(dict(schema_version=2,scope='whole_song',
               note='v3c: per-syllable measured rate/amplitude for periodic support; thirds for slow motion',
               phrases=plans), io.open(NEW/'design'/'plan.json','w',encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('wrote design/plan.json')
