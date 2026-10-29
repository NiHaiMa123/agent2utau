"""直接压制最终工程 project_final.ustx 里的 PITD 字腹摆动（>190c 的缩放）。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)
CAP = 190.0

fixed = 0
for part in doc['voice_parts']:
    pit = next((c for c in part['curves'] if c['abbr']=='pitd'), None)
    if pit is None: continue
    xs = np.array(pit['xs'], float); ys = np.array(pit['ys'], float)
    pp = int(part['position'])
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a0 = tm.tick_to_ms(pp+n['position']); b0 = tm.tick_to_ms(pp+n['position']+n['duration'])
        d = b0-a0
        if d < 60: continue
        # 字腹 = 音符内部去掉两端 25%
        ta = a0 + 0.25*d; tb = b0 - 0.25*d
        m = (xs >= tm.ms_to_tick(ta)-pp) & (xs <= tm.ms_to_tick(tb)-pp)
        if m.sum() < 5: continue
        seg = ys[m]
        swing = float(seg.max()-seg.min())
        if swing <= CAP: continue
        k = CAP/swing
        mid = float(np.mean(seg))
        ys[m] = mid + (seg-mid)*k
        fixed += 1
    pit['ys'] = [int(round(float(v))) for v in ys]

print(f'notes with capped body swing: {fixed}')
save_ustx(doc, NEW/'compiled'/'project_final.ustx')

# 复核 swing
t=[]; c=[]
for p in doc['voice_parts']:
    pit=next(x for x in p['curves'] if x['abbr']=='pitd')
    xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
    pp=int(p['position'])
    ms=np.array([tm.tick_to_ms(pp+x) for x in xs])
    t.append(ms); c.append(ys)
t=np.concatenate(t); c=np.concatenate(c)
o=np.argsort(t); t,c=t[o],c[o]
sw=[]
for part in doc['voice_parts']:
    pp=int(part['position'])
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a0=tm.tick_to_ms(pp+n['position']); b0=tm.tick_to_ms(pp+n['position']+n['duration'])
        d=b0-a0
        if d<60: continue
        T=np.arange(a0+0.25*d, b0-0.25*d, 5.0)
        if len(T)<5: continue
        C=np.interp(T,t,c)
        sw.append(float(C.max()-C.min()))
sw=np.array(sw)
print(f'body swing after cap: median {np.median(sw):.0f}c  p90 {np.percentile(sw,90):.0f}c  max {sw.max():.0f}c')
print(f'  >200c: {(sw>200).sum()}   >190c: {(sw>190).sum()}')
