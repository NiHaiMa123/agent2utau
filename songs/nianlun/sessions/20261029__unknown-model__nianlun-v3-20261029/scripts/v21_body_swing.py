"""检查字腹（音符内部的慢走势+周期）幅度是否过大。

图审 p19:f0:v1「改」：字腹 83.3-83.7s 内有 64 -> 64.7 -> 63.5 的摆动（约 ±1 半音），
再加上边界过渡，整段 swing 达 627c（6 个半音）。对单字来说可能过大。

量化：每个单元在「自身音符内部、去掉两端 25%」的 swing。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)

t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
c = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
o=np.argsort(t); t,c=t[o],c[o]

notes_by_part={}
for pi,part in enumerate(doc['voice_parts']):
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,tone=n['tone'],lyric=n['lyric'],dur=b-a))
    ns.sort(key=lambda x:x['a']); notes_by_part[pi]=ns

rows=[]
for pi, ns in notes_by_part.items():
    for n in ns:
        T=np.arange(n['a'], n['b'], 0.005)
        if len(T)<12: continue
        C=np.interp(T,t,c)
        lo=int(0.25*len(C)); hi=int(0.75*len(C))
        if hi-lo<5: continue
        inner=C[lo:hi]
        rows.append(dict(pi=pi, lyric=n['lyric'], tone=n['tone'], dur=round(n['dur'],2),
                         t0=round(n['a'],2), swing=round(float(inner.max()-inner.min()),0)))

sw=np.array([r['swing'] for r in rows])
print(f'notes with interior sample: {len(rows)}')
print(f'字腹内部（去两端25%）swing: median {np.median(sw):.0f}c  p75 {np.percentile(sw,75):.0f}  p90 {np.percentile(sw,90):.0f}  max {sw.max():.0f}')
for thr in (200,300,450,600):
    print(f'  >{thr}c: {(sw>thr).sum()} ({(sw>thr).mean():.1%})')

print('\n最大的 15 个:')
for r in sorted(rows, key=lambda x:-x['swing'])[:15]:
    print(f"  p{r['pi']} {r['lyric']} @{r['t0']:.2f}s dur={r['dur']}s tone={r['tone']} swing={r['swing']}c")

# 按音符时长分组
print('\n按音符时长分组:')
for lo,hi,lab in [(0,0.30,'<0.30s'),(0.30,0.55,'0.30-0.55s'),(0.55,99,'>=0.55s')]:
    sub=[r['swing'] for r in rows if lo<=r['dur']<hi]
    if sub: print(f'  {lab:12s} n={len(sub):4d} median {np.median(sub):.0f}c  p90 {np.percentile(sub,90):.0f}c')
