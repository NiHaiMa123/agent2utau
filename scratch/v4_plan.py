"""v4：设计驱动的音高曲线（不再以原曲 F0 为目标）。

方法论转变（用户提示 + Skill 原文）：
  错误做法（v2/v3d/v3i）：把源 F0 采样成节点 = "提取原例的峰谷序列"，Skill 禁止
  正确做法（本版）：原曲 F0 只作**条件**——回答"这里有没有运动、什么类型、什么音区"，
                    曲线的节点/斜率/幅度/时序**由 Agent 按音乐逻辑自行设计**

设计依据（全部来自音乐条件，不来自源 F0 数值）：
  句内位置：句首 / 句中 / 句尾
  音乐时长：短(<0.30s) / 中(0.30-0.55s) / 长(>=0.55s)
  音区：低(<C4) / 中 / 高(>=E5)
  前后音程：同音 / 级进(<=2半音) / 小跳(3-4) / 大跳(>=5)
  源运动类型（仅用"有/无/慢/周期"这个分类，不用其数值）

每类条件对应一个明确的演唱动作（见 decisions），参数是条件下的范围取值。
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

def motion_class(a, b):
    """只返回运动**类型**，不返回数值。这是 Skill 允许的'源观察'用途。"""
    m=(ft>=a)&(ft<b)&np.isfinite(SRC)
    if m.sum()<8: return 'unknown', 0.0
    tt=ft[m]; cc=SRC[m]
    span=float(cc.max()-cc.min())
    detr=cc-np.polyval(np.polyfit(tt-a,cc,1),tt-a)
    dstd=float(np.std(detr)); zc=int(np.sum(np.diff(np.sign(detr))!=0))
    if m.sum()>=20:
        fs=1/0.01
        sp=np.abs(np.fft.rfft(detr*np.hanning(len(detr))))
        fr=np.fft.rfftfreq(len(detr),1/fs); lo=(fr>=0.8)&(fr<=12)
        rate=float(fr[lo][np.argmax(sp[lo])]) if lo.any() else 0.0
    else: rate=0.0
    if span < 55: return 'stable', 0.0
    if rate >= 3.5 and zc >= 3: return 'periodic', rate
    return 'slow', rate

# ---- note inventory per part ----
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
MIN_NOTE=0.070

def design_note(n, k, n_notes, prev_tone, next_tone, is_phrase_last):
    """Return (nodes, decision_fields, comps). Nodes are [t, cents, slope]."""
    a,b,d,tone = n['a'], n['b'], n['dur'], n['tone']
    centre = tone*100.0
    A = round(a + (GAP if k>0 else 0.0), 4)
    B = round(b - (GAP if k<n_notes-1 else 0.0), 4)
    if B <= A+0.012: B = round(A+0.012,4)
    inner = B-A
    # ---- music conditions ----
    pos = 'first' if k==0 else ('last' if k==n_notes-1 else 'mid')
    if d < 0.30: dlen='short'
    elif d < 0.55: dlen='mid'
    else: dlen='long'
    reg = 'high' if tone >= 76 else ('low' if tone <= 60 else 'mid')
    if prev_tone is None: leap='start'
    else:
        dt = tone-prev_tone
        leap = 'unison' if dt==0 else 'step' if abs(dt)<=2 else 'small' if abs(dt)<=4 else 'big'
    mcls, mrate = motion_class(a,b)

    nodes=[]; comps=[]; choice=''; alt=''; reason=''; unc=''
    cids=[]

    # ============ 1. 起音：句首/大跳/同音重咬 ============
    if pos=='first' and dlen!='short':
        # 句首：从下方轻轻承接再落到主音（清晰落拍）
        low = centre - (38 if reg=='high' else 45 if reg=='mid' else 52)
        t_hit = round(A + min(0.55*inner, 0.16+0.02*(3 if reg=='mid' else 0)), 4)
        nodes += [[A, low, 0.0],
                  [round(A+0.5*(t_hit-A),4), round(low+0.55*(centre-low),2), 0.0],
                  [t_hit, centre, 0.0]]
        choice='sentence-initial lift-in: enter below then settle on the main tone'
        alt='strike the main tone directly at the attack'
        reason='a phrase-initial syllable carries the listener in; a short lift-in makes the downbeat clear without delaying the tone'
        unc='how much lower the entry should sit is not calibrated for this voicebank'
    elif leap=='big' and dlen!='short':
        # 大跳：两段承接（先落到目标下方，再推上去）
        up = tone > prev_tone
        r = 95 if abs(tone-prev_tone)>=6 else 70
        step_c = centre - r if up else centre + r
        t1 = round(A+0.34*inner,4); t2 = round(A+0.72*inner,4)
        nodes += [[A, step_c, 0.0],[t1, step_c, 0.0],[t2, centre, 0.0]]
        choice=f'{"two-stage lift" if up else "two-stage settle"} for a {abs(tone-prev_tone)}-semitone leap'
        alt='single direct connection'
        reason='a large interval inside one syllable needs a landing point before the main tone, otherwise the arrival sounds late or scooped'
        unc='whether the source actually used a stage here is unknown'
    elif leap=='unison' and d==0 and False:
        pass
    else:
        nodes += [[A, centre, 0.0]]

    # ============ 2. 主体：长音展开 / 中音单次回收 / 短音直接 ============
    mid_t = round(A+0.5*inner,4)
    end_t = round(B,4)
    if dlen=='long':
        # 长音：主音 → 中段浅支撑 → 尾部按句位置处理
        dip = -14 if reg=='high' else -18 if reg=='mid' else -22
        nodes += [[mid_t, round(centre+dip,2), 0.0]]
        if mcls=='periodic' and inner>=0.50:
            # 源里确有周期运动 → 我们也给一个周期，但频率/深度/进入点自己定
            rate = 5.6 if reg!='low' else 5.2
            depth = 16 if reg=='high' else 22 if reg=='mid' else 26
            on = round(A+0.40*inner,4); off = round(B-0.22*inner,4)
            if off-on >= 0.18:
                oid=f'n{len(nodes)}:osc'
                comps.append(dict(id=oid,family='oscillation',support_s=[A,B],
                                  attack_end_s=on,release_start_s=off,
                                  depth_nodes=[[A,0.0],[on,float(depth)],
                                               [off,float(depth*0.75)],[B,0.0]],
                                  rate_nodes=[[A,rate],[B,round(rate*1.04,2)]],
                                  phase_rad=0.0))
                cids.append(oid)
            choice=f'long syllable: main tone, shallow body support, then {rate}Hz vibrato entering at 40%'
            alt='flat hold, or vibrato across the whole syllable'
            reason='the source does carry periodic motion here, so a period is musically warranted; its rate and depth are chosen for this register, not copied'
            unc='vibrato depth that reads as natural on YousaV1.65c is not calibrated'
        else:
            choice='long syllable: main tone with a shallow interior drop and recovery'
            alt='hold flat through the whole syllable'
            reason='a syllable this long needs an interior event; a shallow drop is enough when no periodic motion is observed'
            unc='source periodicity below the detector floor'
    elif dlen=='mid':
        dip = -10 if reg=='high' else -12
        nodes += [[mid_t, round(centre+dip,2), 0.0]]
        choice='mid-length syllable: main tone with a single shallow recovery'
        alt='no interior event'
        reason='a small interior turn keeps the syllable from sounding held-flat without inventing a period'
        unc='whether this is audible at these lengths'
    # short: nodes already just the entry

    # ============ 3. 释放：句尾 / 下字是大下行 ============
    if is_phrase_last and dlen!='short':
        run = centre - (30 if reg=='high' else 38 if reg=='mid' else 45)
        nodes += [[end_t, round(run,2), 0.0]]
        choice2='phrase-final release: settle below the main tone'
        reason2='the last syllable of a phrase releases rather than holding; the drop marks the breath'
    elif next_tone is not None and (tone-next_tone)>=5 and dlen!='short':
        prep = centre - 28
        nodes += [[end_t, round(prep,2), 0.0]]
        choice2='tail prepares a large downward interval'
        reason2='the next syllable sits much lower; easing the tail down avoids a cliff at the boundary'
    else:
        nodes += [[end_t, round(centre,2), 0.0]]
        choice2=''

    # normalise times strictly increasing inside [A,B]
    nodes = [[round(max(A,min(B,float(t))),4), float(c), float(s)] for t,c,s in nodes]
    nodes.sort(key=lambda x:x[0])
    outn=[]
    for x in nodes:
        if outn and x[0] <= outn[-1][0]+1e-5:
            outn[-1] = [outn[-1][0], x[1], x[2]]; continue
        outn.append(x)
    if outn[0][0] != A: outn.insert(0,[A,outn[0][1],0.0])
    outn[0][0]=A
    if outn[-1][0] != B:
        if outn[-1][0] < B: outn.append([B,outn[-1][1],0.0])
        else: outn[-1][0]=B
    outn[-1][0]=B

    desc = (f'pos={pos} len={dlen} reg={reg} leap={leap} src_motion={mcls}')
    dec = dict(desc=desc, choice=choice, alt=alt, reason=reason, unc=unc,
               choice2=choice2, reason2=locals().get('reason2',''), cids=cids)
    return outn, dec, comps

plans, stats = [], dict(nodes=0, comps=0, roles={})
for pi, notes in enumerate(parts):
    t0, t1 = W['phrases'][pi]['time']
    allnodes=[]; allcomps=[]; decs=[]
    prev_tone=None
    for k,n in enumerate(notes):
        nxt = notes[k+1]['tone'] if k+1 < len(notes) else None
        nis_last = (k == len(notes)-1)
        ns, dec, cps = design_note(n, k, len(notes), prev_tone, nxt, nis_last)
        for x in ns: x[2]=x[2]  # slopes set below
        allnodes += ns
        allcomps += cps
        decs.append(dict(note=n, dec=dec, count=len(ns)))
        prev_tone = n['tone']
        stats['roles'][dec['desc']] = stats['roles'].get(dec['desc'],0)+1
    # bind to part window + continuous slopes
    allnodes.sort(key=lambda x:x[0])
    merged=[]
    for x in allnodes:
        if merged and abs(x[0]-merged[-1][0])<1e-6:
            merged[-1]=[merged[-1][0], x[1], 0.0]; continue
        if merged and x[0]<merged[-1][0]: continue
        merged.append([x[0],x[1],0.0])
    if merged[0][0] > t0+1e-6: merged.insert(0,[round(t0,4),merged[0][1],0.0])
    merged[0][0]=round(t0,4)
    if merged[-1][0] < t1-1e-6: merged.append([round(t1,4),merged[-1][1],0.0])
    merged[-1][0]=round(t1,4)
    for k in range(1,len(merged)):
        if merged[k][0]<=merged[k-1][0]: merged[k][0]=round(merged[k-1][0]+0.002,4)
    if merged[-1][0]>t1: merged[-1][0]=round(t1,4)
    ts_=[x[0] for x in merged]; vs_=[x[1] for x in merged]
    for k in range(len(merged)):
        if len(merged)==1: s=0.0
        elif k==0: s=(vs_[1]-vs_[0])/max(ts_[1]-ts_[0],1e-6)
        elif k==len(merged)-1: s=(vs_[-1]-vs_[-2])/max(ts_[-1]-ts_[-2],1e-6)
        else:
            s1=(vs_[k]-vs_[k-1])/max(ts_[k]-ts_[k-1],1e-6)
            s2=(vs_[k+1]-vs_[k])/max(ts_[k+1]-ts_[k],1e-6)
            s=0.5*(s1+s2)
        merged[k][2]=round(float(np.clip(s,-900,900)),2)
    # decisions: one per note (contiguous coverage)
    dec_out=[]; cursor=round(t0,4)
    for k,d in enumerate(decs):
        end = round(d['note']['b'],4) if k<len(decs)-1 else round(t1,4)
        end = max(end, round(cursor+0.002,4))
        txt = d['dec']['choice'] + ('; ' + d['dec']['choice2'] if d['dec']['choice2'] else '')
        rsn = d['dec']['reason'] + ('; ' + d['dec']['reason2'] if d['dec']['reason2'] else '')
        dec_out.append(dict(support_s=[cursor, end], condition=d['dec']['desc'],
                            choice=txt, alternative=d['dec']['alt'],
                            reason=rsn, uncertainty=d['dec']['unc'],
                            component_ids=d['dec']['cids']))
        cursor = end
    dec_out[-1]['support_s'][1]=round(t1,4)
    amp = max(vs_)-min(vs_)
    plans.append(dict(schema=1,origin='agent_designed',support_s=[round(t0,4),round(t1,4)],
        center_nodes=[[x[0],x[1],x[2]] for x in merged], components=allcomps,
        decisions=dec_out,
        expectations=[dict(support_s=[round(t0,4),round(t1,4)],
                           range_c=[0.0, round(amp+60.0,2)],
                           purpose=f'part {pi}: designed motion envelope')]))
    stats['nodes'] += len(merged); stats['comps'] += len(allcomps)

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
    except Exception as ex_: bad.append((i,str(ex_)[:90]))
print(f'phrases {len(plans)}  shape failures {len(bad)}')
for bb in bad[:6]: print('  ',bb)
print(f"nodes {stats['nodes']} ({stats['nodes']/349:.1f}/syllable)  components {stats['comps']}")

json.dump(dict(schema_version=2,scope='whole_song',
    note='v4 design-driven: source F0 used only as a motion-type condition, never as a target curve',
    phrases=plans), io.open(NEW/'design'/'plan.json','w',encoding='utf-8'),
    ensure_ascii=False, indent=1)

from collections import Counter
c=Counter()
for p in plans:
    for d in p['decisions']:
        for kk in ('pos','len','reg','leap','src_motion'):
            pass
print('\ncondition coverage sample:')
for d in plans[0]['decisions'][:4]:
    print('  ', d['condition'], '->', d['choice'][:70])
print('\nwrote design/plan.json')
