"""扩展判据：检查每个音符内部的「字尾下沉」是否与随后的大跳方向冲突。

v22 图审（p0:f0:v0, 19.4s）：
  字尾 19.35-19.42 从 57.8 下沉到 56.0（-180c），
  随后 19.42 起跳向 61.5（+550c）。这是「先下探再上冲」。
  虽然边界前 60ms 可能在上升（因为已开始跳），但整体形态是错的。
判据改为：检查音符「末尾 25%」的净位移方向是否与下一跳变方向相反。
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
        ns.append(dict(a=a,b=b,tone=n['tone'],lyric=n['lyric'],dur=b-a))
    ns.sort(key=lambda x:x['a'])
    for i,(x,y) in enumerate(zip(ns,ns[1:])):
        jump=y['tone']-x['tone']
        if abs(jump)<3: continue
        d=x['dur']
        if d<0.15: continue
        # 音符末尾 25%
        T=np.arange(x['b']-0.25*d, x['b'], 0.005)
        C=np.interp(T,t,c)
        tail_move = C[-1]-C[0]
        conflict = (jump>0 and tail_move<-40) or (jump<0 and tail_move>40)
        if conflict:
            bad.append((pi,x['lyric'],y['lyric'],jump,x['b'],round(float(tail_move),0)))

print(f'字尾运动与下一跳变方向冲突: {len(bad)}')
for b in sorted(bad,key=lambda z:-abs(z[5]))[:20]:
    print(f"  p{b[0]} {b[1]}->{b[2]} jump{b[3]:+d} @{b[4]:.2f}s  字尾净位移 {b[5]:+.0f}c  (方向相反)")
