"""修最后 3 处大跳的反向步进（part2 @28.89s, part19 @86.38/86.47s）。

这些反向来自字腹正弦起伏与边界过渡叠加。
做法：在大跳边界 ±120ms 内，对最终曲线做单调化后处理，并保证与两侧衔接。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)

TARGETS = [(2, 28.89), (19, 86.38), (19, 86.47)]

for pi, tb in TARGETS:
    part = doc['voice_parts'][pi]
    pp = int(part['position'])
    pit = next((c for c in part['curves'] if c['abbr']=='pitd'), None)
    if pit is None: continue
    xs = np.array(pit['xs'], float); ys = np.array(pit['ys'], float)
    # 找该边界两侧音符
    ns = []
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a = tm.tick_to_ms(pp+n['position'])/1000
        b = tm.tick_to_ms(pp+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,tone=n['tone']))
    ns.sort(key=lambda x:x['a'])
    left = next((n for n in ns if abs(n['b']-tb) < 0.05), None)
    if left is None: continue
    i = ns.index(left); right = ns[i+1] if i+1 < len(ns) else None
    if right is None: continue
    jump = right['tone']-left['tone']
    if abs(jump) < 4: continue

    # part 相对 tick 窗口
    tk_lo = tm.ms_to_tick((tb-0.13)*1000) - pp
    tk_hi = tm.ms_to_tick((tb+0.13)*1000) - pp
    m = (xs >= tk_lo) & (xs <= tk_hi)
    if m.sum() < 4: continue
    seg = ys[m].copy()
    if jump > 0:
        for j in range(1, len(seg)):
            if seg[j] < seg[j-1]: seg[j] = seg[j-1]
    else:
        for j in range(1, len(seg)):
            if seg[j] > seg[j-1]: seg[j] = seg[j-1]
    ys[m] = seg
    pit['ys'] = [int(round(float(v))) for v in ys]
    print(f'part {pi} @{tb}s: monotonic-ized jump {jump:+d} semis over {int(m.sum())} points')

save_ustx(doc, NEW/'compiled'/'project_final.ustx')
print('wrote project_final.ustx')
