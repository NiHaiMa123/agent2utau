"""把 v5 的密集 PITD 通过 compile-functions 编码，并核查读回。

compile-functions 的工作方式是：读 baseline 的 before_pitd，把我们的目标写成 PITD 偏移。
所以需要用「设计目标 = tone*100 + 我的 PITD 形状」来构造 plan。
"""
import sys, json, io
import numpy as np, yaml
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap, sha256
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
SCORE = NEW/'score'/'v5_score.ustx'
NAT = NEW/'native_v5'; NAT.mkdir(exist_ok=True)

# export baseline (with our PITD already present -> compiler strips pitd then re-encodes;
# so we encode from a clean score and apply our own pitd afterwards)
CLEAN = NEW/'score'/'v3_score.ustx'
for cmd,out in [('export-pitch', NAT/'baseline_pitch.json'), ('export-phonemes', NAT/'baseline_phones.json')]:
    r = run_bridge(cfg,[cmd,'--project',str(CLEAN.resolve()),'--out',str(out.resolve())])
    print(f'{cmd}: ok={r.get("ok")}')
bp = json.load(io.open(NAT/'baseline_pitch.json',encoding='utf-8'))
print(f'baseline phrases {len(bp["phrases"])}')

# our designed final line = note tone*100 + our dense PITD shape
doc = load_ustx(SCORE)
tm = TempoMap.from_doc(doc)
parts_pitd=[]
for part in doc['voice_parts']:
    pit = next(c for c in part['curves'] if c['abbr']=='pitd')
    xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
    parts_pitd.append((part['position'], xs, ys))

def pitd_at(part_index, abs_tick):
    pos, xs, ys = parts_pitd[part_index]
    rel = abs_tick - pos
    if rel < xs[0] or rel > xs[-1]: return 0.0
    return float(np.interp(rel, xs, ys))

# build note-tone reference line per phrase
doc_clean = load_ustx(CLEAN)
tm2 = TempoMap.from_doc(doc_clean)
plans=[]
for k, npz in enumerate(bp['phrases']):
    times = np.asarray(npz['times_ms'],float)/1000
    # which part owns this phrase
    pidx = next(i for i,pt in enumerate(doc_clean['voice_parts'])
                if pt['position']==npz['part_position'])
    part = doc_clean['voice_parts'][pidx]
    # per-sample: find the note covering each time, take its tone, add our pitd
    tgt=[]
    notes = part['notes']
    for t in times:
        tick_abs = tm2.ms_to_tick(t*1000)
        tone = None
        for n in notes:
            na = part['position']+n['position']; nb = na+n['duration']
            if na-2 <= tick_abs <= nb+2:
                tone = n['tone']; break
        if tone is None:
            # nearest note
            best=min(notes, key=lambda n: abs((part['position']+n['position']+n['duration']/2)-tick_abs))
            tone = best['tone']
        tgt.append(tone*100.0 + pitd_at(pidx, tick_abs))
    tgt = np.array(tgt)
    # compress to a handful of nodes? No: compile-functions expects a design it samples.
    # Use a linear-per-segment node set equal to the dense target (it re-samples identically).
    nodes=[]
    for i,(t,v) in enumerate(zip(times,tgt)):
        if i==0 or abs(v-nodes[-1][1])>0.5 or i==len(times)-1:
            nodes.append([float(t), float(v), 0.0])
    if nodes[0][0]!=float(times[0]): nodes.insert(0,[float(times[0]),float(tgt[0]),0.0])
    if nodes[-1][0]!=float(times[-1]): nodes.append([float(times[-1]),float(tgt[-1]),0.0])
    # strictly increasing
    uniq=[]
    for x in nodes:
        if uniq and x[0]<=uniq[-1][0]: continue
        uniq.append(x)
    amp=float(tgt.max()-tgt.min())
    plans.append(dict(schema=1,origin='agent_designed',support_s=[float(times[0]),float(times[-1])],
        center_nodes=uniq,components=[],
        decisions=[dict(support_s=[float(times[0]),float(times[-1])],
            condition='native phrase', choice='dense designed pitch line (16ms grid)',
            alternative='sparse nodes', reason='hand-drawn pitch lines need dense control',
            uncertainty='grid', component_ids=[])],
        expectations=[dict(support_s=[float(times[0]),float(times[-1])],
            range_c=[0.0, round(amp+60.0,2)], purpose='keep designed envelope')]))
    npz['_nodes']=len(uniq)

print(f'plans {len(plans)}, nodes total {sum(len(p["center_nodes"]) for p in plans)}')

# write compile plan
ih = {str(CLEAN.resolve()): sha256(CLEAN),
      str((NEW/'inputs'/'stems'/'vocals.wav').resolve()): sha256(NEW/'inputs'/'stems'/'vocals.wav')}
pos2 = {p['position']: i for i,p in enumerate(doc_clean['voice_parts'])}
out_ph=[]
for npz,pl in zip(bp['phrases'],plans):
    out_ph.append(dict(part_index=pos2[npz['part_position']], position=npz['position'], design=pl))
kc = json.load(io.open(NEW/'design'/'compile_plan.json',encoding='utf-8'))
kc['project'] = str(CLEAN.resolve())
kc['input_hashes'] = ih
kc['phrases'] = out_ph
(NEW/'design'/'compile_plan_v5.json').write_text(json.dumps(kc,ensure_ascii=False,indent=1),encoding='utf-8')
print('wrote compile_plan_v5.json')
