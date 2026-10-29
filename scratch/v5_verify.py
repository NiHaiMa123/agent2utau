"""核查 v5 的 PITD 是否保留：对比设计目标 vs 编译后 PITD 的实际值。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')

v5 = load_ustx(NEW/'compiled'/'project.ustx')
bs = load_ustx(REF)

def pitd_stats(doc, label):
    tot=0; pts=0; zfrac=[]; absmean=[]; stds=[]
    for part in doc['voice_parts']:
        pit = next((c for c in part.get('curves',[]) if c['abbr']=='pitd'), None)
        if not pit: continue
        xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
        tot+=1; pts+=len(xs)
        zfrac.append(float((np.abs(ys)<50).mean()))
        absmean.append(float(np.mean(np.abs(ys))))
        stds.append(float(np.std(ys)))
    print(f'=== {label} ===')
    print(f'  parts with pitd {tot}, total points {pts} ({pts/max(tot,1):.0f}/part)')
    print(f'  |y|<50c fraction: median {np.median(zfrac):.1%}')
    print(f'  mean|y| per part: median {np.median(absmean):.1f}c')
    print(f'  std per part: median {np.median(stds):.1f}c')
    return pts

pitd_stats(bs, '白烁 雨爱')
pitd_stats(v5, '我们 v5 年轮')

# 逐音符：字头/字腹/字尾的偏移中位（与白烁同口径）
def profile(doc, label):
    tm = TempoMap.from_doc(doc)
    prof=[]
    for pi,part in enumerate(doc['voice_parts']):
        pit = next((c for c in part.get('curves',[]) if c['abbr']=='pitd'), None)
        if not pit: continue
        xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
        for n in part['notes']:
            if n['lyric'] in ('AP','SP'): continue
            na=part['position']+n['position']; nb=na+n['duration']
            m=(xs>=na)&(xs<=nb)
            if m.sum()<6: continue
            u=(xs[m]-na)/max(nb-na,1)
            v=ys[m]
            prof.append((u,v))
    if not prof: return
    u=np.concatenate([p[0] for p in prof]); y=np.concatenate([p[1] for p in prof])
    print(f'\n{label}: 字内位置分箱的 PITD 中位/p10')
    for lo,hi in [(0,0.15),(0.15,0.35),(0.35,0.65),(0.65,0.85),(0.85,1.01)]:
        m=(u>=lo)&(u<hi)
        if m.sum()>10:
            print(f'  u {lo:.2f}-{hi:.2f}: n={m.sum():5d}  median {np.median(y[m]):+7.1f}c  p10 {np.percentile(y[m],10):+7.1f}c  std {np.std(y[m]):5.1f}c')
profile(bs,'白烁')
profile(v5,'v5')
