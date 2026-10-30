"""v11 编译 + 组装 + 渲染（全流程封装）。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap, sha256
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
SC = NEW/'score'/'v11_score.ustx'
CLEAN = NEW/'score'/'v3_score.ustx'
NAT = NEW/'native_v11'; NAT.mkdir(exist_ok=True)

for cmd,out in [('export-pitch',NAT/'bp.json'),('export-phonemes',NAT/'bph.json')]:
    r = run_bridge(cfg,[cmd,'--project',str(CLEAN.resolve()),'--out',str(out.resolve())])
    print(cmd, r.get('ok'))
bp = json.load(io.open(NAT/'bp.json',encoding='utf-8'))

d = load_ustx(SC); tm = TempoMap.from_doc(d)
pitds=[]
for part in d['voice_parts']:
    pit = next(c for c in part['curves'] if c['abbr']=='pitd')
    pitds.append((part['position'], np.array(pit['xs'],float), np.array(pit['ys'],float)))

plans=[]
for npz in bp['phrases']:
    times=np.asarray(npz['times_ms'],float)/1000
    pidx=next(i for i,p in enumerate(d['voice_parts']) if p['position']==npz['part_position'])
    pos,xs,ys=pitds[pidx]; part=d['voice_parts'][pidx]; notes=part['notes']
    tgt=[]
    for t in times:
        tk=tm.ms_to_tick(t*1000); tone=None
        for n in notes:
            na=part['position']+n['position']; nb=na+n['duration']
            if na-2<=tk<=nb+2: tone=n['tone']; break
        if tone is None:
            b=min(notes,key=lambda n:abs((part['position']+n['position']+n['duration']/2)-tk)); tone=b['tone']
        rel=tk-pos
        off=float(np.interp(rel,xs,ys)) if xs[0]<=rel<=xs[-1] else 0.0
        tgt.append(tone*100.0+off)
    tgt=np.array(tgt); nodes=[]
    for i,(t,v) in enumerate(zip(times,tgt)):
        if i==0 or abs(v-nodes[-1][1])>0.5 or i==len(times)-1: nodes.append([float(t),float(v),0.0])
    if nodes[0][0]!=float(times[0]): nodes.insert(0,[float(times[0]),float(tgt[0]),0.0])
    if nodes[-1][0]!=float(times[-1]): nodes.append([float(times[-1]),float(tgt[-1]),0.0])
    u=[]
    for x in nodes:
        if u and x[0]<=u[-1][0]: continue
        u.append(x)
    amp=float(tgt.max()-tgt.min())
    plans.append(dict(schema=1,origin='agent_designed',support_s=[float(times[0]),float(times[-1])],
        center_nodes=u,components=[],
        decisions=[dict(support_s=[float(times[0]),float(times[-1])],condition='native phrase',
          choice='dense hand-drawn pitch line (12ms), zero-mean corrected',
          alternative='sparse nodes or source-F0 copy',
          reason='a sung line needs dense control and a centred baseline',
          uncertainty='grid',component_ids=[])],
        expectations=[dict(support_s=[float(times[0]),float(times[-1])],
          range_c=[0.0,round(amp+60.0,2)],purpose='envelope')]))
pos2={p['position']:i for i,p in enumerate(d['voice_parts'])}
kcp=json.load(io.open(NEW/'design'/'compile_plan_v5.json',encoding='utf-8'))
kcp['project']=str(SC.resolve())
kcp['input_hashes']={str(SC.resolve()):sha256(SC),
                     str((NEW/'inputs'/'stems'/'vocals.wav').resolve()):sha256(NEW/'inputs'/'stems'/'vocals.wav')}
kcp['phrases']=[dict(part_index=pos2[n['part_position']],position=n['position'],design=pl)
                for n,pl in zip(bp['phrases'],plans)]
(NEW/'design'/'compile_plan_v11.json').write_text(json.dumps(kcp,ensure_ascii=False,indent=1),encoding='utf-8')
print('compile plan written; nodes', sum(len(p['center_nodes']) for p in plans))
