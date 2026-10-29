"""重新量化：音符间大跳的完成时间，并与白烁对比。

之前测的是「10%->90% 跨越时间」，但图上看起来近乎垂直。
更严格的指标：从「离开前音 10%」到「到达后音 90%」的时间，以及最大速度（c/s）。
同时测白烁做同样统计。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')
cfg = load_config()

def transition_stats(doc, pitch_json_path, label, min_semis=4):
    tm = TempoMap.from_doc(doc)
    pf = json.load(io.open(pitch_json_path, encoding='utf-8'))
    dt = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
    dc = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
    o=np.argsort(dt); dt,dc=dt[o],dc[o]
    res=[]
    for part in doc['voice_parts']:
        notes=[n for n in part['notes'] if n['lyric'] not in ('AP','SP','EP')]
        for a,b in zip(notes, notes[1:]):
            if a['lyric'] in ('+','') or b['lyric'] in ('+',''): continue
            jump=b['tone']-a['tone']
            if abs(jump)<min_semis: continue
            tb = tm.tick_to_ms(part['position']+a['position']+a['duration'])/1000
            s=a['tone']*100.0; e=b['tone']*100.0
            T=np.arange(tb-0.25, tb+0.25, 0.002)
            C=np.interp(T,dt,dc)
            lo,hi=min(s,e),max(s,e); span=hi-lo
            if span<300: continue
            # 在 tb 前 30ms 到 tb 后 200ms 内找穿越点
            m=(T>=tb-0.03)&(T<=tb+0.20)
            if not m.any(): continue
            Tm,Cm=T[m],C[m]
            if e>s:
                i10=np.where(Cm>=lo+0.10*span)[0]; i90=np.where(Cm>=lo+0.90*span)[0]
            else:
                i10=np.where(Cm<=hi-0.10*span)[0]; i90=np.where(Cm<=hi-0.90*span)[0]
            if not len(i10) or not len(i90): continue
            a0=i10[0]; b0=i90[0]
            if b0<=a0: continue
            dur=(Tm[b0]-Tm[a0])*1000
            # max speed
            dC=np.abs(np.diff(Cm))/(np.diff(Tm)+1e-12)
            res.append(dict(jump=jump, dur_ms=dur, max_speed=float(dC.max()), t=tb))
    if not res:
        print(f'{label}: no transitions'); return None
    ds=np.array([r['dur_ms'] for r in res])
    sp=np.array([r['max_speed'] for r in res])
    print(f'=== {label} ===  n={len(res)}')
    print(f'  10-90% 时间: median {np.median(ds):.0f}ms  p10 {np.percentile(ds,10):.0f}  p90 {np.percentile(ds,90):.0f}')
    print(f'  最大速度: median {np.median(sp):.0f}c/s  p10 {np.percentile(sp,10):.0f}  p90 {np.percentile(sp,90):.0f}')
    print(f'  <40ms: {(ds<40).sum()}  <25ms: {(ds<25).sum()}  <15ms: {(ds<15).sum()}')
    return res

# ours
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
ours = transition_stats(doc, NEW/'compiled'/'pitch_final.json', '本版年轮')

# baishuo: export its pitch
out = NEW/'compiled'/'pitch_baishuo.json'
r = run_bridge(cfg, ['export-pitch','--project',str(REF.resolve()),'--out',str(out.resolve())])
print('export baishuo:', r.get('ok'))
bs = load_ustx(REF)
theirs = transition_stats(bs, out, '白烁 雨爱')
