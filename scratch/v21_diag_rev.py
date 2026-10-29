"""确认：大跳处的反向步进来自 before_pitd（音符阶梯），还是我的 PITD？

如果 PITD 在窗口内已单调，但最终线仍反向，那就是 before_pitd 的贡献。
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
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))

for pi, tb in [(2, 28.89), (19, 86.38)]:
    pp = int(doc['voice_parts'][pi]['position'])
    # PITD in window
    pit = next(c for c in doc['voice_parts'][pi]['curves'] if c['abbr']=='pitd')
    xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
    lo=tm.ms_to_tick((tb-0.13)*1000)-pp; hi=tm.ms_to_tick((tb+0.13)*1000)-pp
    m=(xs>=lo)&(xs<=hi)
    seg=ys[m]
    d=np.diff(seg)
    print(f'part {pi} @{tb}s:')
    print(f'  my PITD in window: {len(seg)} pts, min step {d.min():.0f}, max step {d.max():.0f}, '
          f'monotone {"UP" if d.min()>=-2 else ("DOWN" if d.max()<=2 else "NO")}')

    # final line
    t=np.array([]); c=np.array([])
    for ph in pf['phrases']:
        if int(ph['part_position'])==pp:
            t=np.asarray(ph['times_ms'],float)/1000; c=np.asarray(ph['final_cents'],float); break
    T=np.arange(tb-0.13, tb+0.13, 0.002)
    if len(t):
        C=np.interp(T,t,c)
        dd=np.diff(C)
        print(f'  final line: min step {dd.min():.0f}c, max step {dd.max():.0f}c, '
              f'counter(<-15) {(dd<-15).sum()}, counter(>15) {(dd>15).sum()}')

    # baseline
    t2=np.array([]); c2=np.array([])
    for ph in bp['phrases']:
        if int(ph['part_position'])==pp:
            t2=np.asarray(ph['times_ms'],float)/1000; c2=np.asarray(ph['before_pitd_cents'],float); break
    if len(t2):
        B=np.interp(T,t2,c2)
        db_=np.diff(B)
        print(f'  before_pitd: min step {db_.min():.0f}c, max step {db_.max():.0f}c')
