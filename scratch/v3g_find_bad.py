"""定位剩余 12 个 >100c 的音符：重映射到原生短语时的重采样是否越界。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project.ustx')
tm = TempoMap.from_doc(doc)
pitch = json.load(io.open(NEW/'compiled'/'pitch.json', encoding='utf-8'))
dt = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pitch['phrases']])
dc = np.concatenate([np.asarray(x['final_cents'],float) for x in pitch['phrases']])
o=np.argsort(dt); dt,dc=dt[o],dc[o]

bad=[]
for pi,part in enumerate(doc['voice_parts']):
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        d=b-a
        if d<0.02: continue
        lo,hi=a+0.25*d,b-0.25*d
        if hi<=lo: continue
        T=np.arange(lo,hi,0.005)
        if len(T)<3: continue
        c=np.interp(T,dt,dc)
        dev=float(np.median(c))-n['tone']*100
        if abs(dev)>100:
            bad.append((pi,n['lyric'],round(a,2),round(d,3),n['tone'],round(float(np.median(c)),0),round(dev)))
print(f'notes with body dev >100c: {len(bad)}')
for x in sorted(bad,key=lambda z:-abs(z[6])):
    print(f'  p{x[0]} {x[1]} @{x[2]}s dur={x[3]} tone={x[4]} body_med={x[5]} dev={x[6]:+}c')

# check part support vs note span for those
print('\ncheck: does the note fall outside its part plan support?')
plans = json.load(io.open(NEW/'design'/'plan.json',encoding='utf-8'))['phrases']
for x in sorted(bad,key=lambda z:-abs(z[6]))[:5]:
    part=doc['voice_parts'][x[0]]
    pa=tm.tick_to_ms(part['position'])/1000
    pb=tm.tick_to_ms(part['position']+part['duration'])/1000
    print(f"  p{x[0]}: note {x[2]}..{x[2]+x[3]:.2f}, part {pa:.2f}..{pb:.2f}, plan support {plans[x[0]]['support_s']}")
