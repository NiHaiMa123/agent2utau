"""v21：压低字腹过大摆动（18 个 >200c 的音符内部），保持其余不变。

依据：字腹中位 73c、p90 129c 是合理的；
但 18 个音符内部 >200c、最大 546c 属于过大，会让单字听起来「摇晃」。
修正：把超过 200c 的字腹 swing 按比例压到 200c 以内，两端过渡不变。
"""
import sys, json, io, math
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'score'/'v20_score.ustx')
tm = TempoMap.from_doc(doc)

def ms_tick(part_pos, t_ms):
    return int(round(tm.ms_to_tick(t_ms))) - part_pos

CAP = 190.0

for part in doc['voice_parts']:
    pit = next((c for c in part['curves'] if c['abbr']=='pitd'), None)
    if pit is None: continue
    xs = np.array(pit['xs'], float)
    ys = np.array(pit['ys'], float)
    pp = int(part['position'])
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a0 = tm.tick_to_ms(pp+n['position'])
        b0 = tm.tick_to_ms(pp+n['position']+n['duration'])
        d = b0-a0
        if d < 60: continue
        ta = a0 + 0.25*d; tb = b0 - 0.25*d
        m = (xs >= tm.ms_to_tick(ta)-pp) & (xs <= tm.ms_to_tick(tb)-pp)
        if m.sum() < 5: continue
        seg = ys[m]
        swing = float(seg.max()-seg.min())
        if swing <= CAP: continue
        k = CAP/swing
        mid = float(np.mean(seg))
        ys[m] = mid + (seg-mid)*k
    pit['ys'] = [int(round(float(v))) for v in ys]

OUT = NEW/'score'/'v21_score.ustx'
save_ustx(doc, OUT)

# 复核
st=[]
for p in doc['voice_parts']:
    pit=next(c for c in p['curves'] if c['abbr']=='pitd')
    if len(pit['ys'])>1: st.append(np.abs(np.diff(np.array(pit['ys'],float))))
a=np.concatenate(st)
allv=np.concatenate([np.array(p['curves'][-1]['ys'],float) if p['curves'] else np.array([]) for p in doc['voice_parts']])
print(f'|dy| median {np.median(a):.1f} max {a.max():.0f}')
print(f'wrote {OUT}')
