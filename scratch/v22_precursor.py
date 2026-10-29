"""定位 v22 的边界尖刺：在所有音符边界处检查「先反向再跳」的形态。

判据：边界前 60ms 内的运动方向，是否与接下来的跳变方向相反。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
c = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
o=np.argsort(t); t,c=t[o],c[o]

bad=[]
for pi,part in enumerate(doc['voice_parts']):
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,tone=n['tone'],lyric=n['lyric']))
    ns.sort(key=lambda x:x['a'])
    for x,y in zip(ns,ns[1:]):
        jump=y['tone']-x['tone']
        if abs(jump)<2: continue
        tb=x['b']
        # 边界前 60ms 的走向
        Tb=np.arange(tb-0.06, tb, 0.005)
        Cb=np.interp(Tb,t,c)
        pre = Cb[-1]-Cb[0] if len(Cb)>1 else 0.0
        # 反向预兆：jump>0 但 pre<-25；或 jump<0 但 pre>25
        if (jump>0 and pre<-25) or (jump<0 and pre>25):
            bad.append((pi, x['lyric'], y['lyric'], jump, tb, round(float(pre),0)))

print(f'音符间「反向预兆」: {len(bad)}')
for b in sorted(bad, key=lambda z:-abs(z[5]))[:20]:
    print(f"  p{b[0]} {b[1]}->{b[2]} jump{b[3]:+d} @{b[4]:.2f}s  边界前60ms走向 {b[5]:+.0f}c")
