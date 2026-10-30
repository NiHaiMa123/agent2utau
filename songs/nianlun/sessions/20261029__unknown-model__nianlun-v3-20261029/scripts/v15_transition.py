"""量化音符间大跳的实现速度。
79.55s 从 65 到 57（8 个半音）——这是旋律本身（p18:n2 密 tone=65 -> n3 麻 tone=57）。
问题：完成这个跳变用了多久？如果 <60ms 就是"瞬间跳"，听感会是断裂。
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
pitch = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))

# 全局：找所有 >=4 半音的相邻音符跳变，测量 10%-90% 完成时间
dt = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pitch['phrases']])
dc = np.concatenate([np.asarray(x['final_cents'],float) for x in pitch['phrases']])
o=np.argsort(dt); dt,dc=dt[o],dc[o]

transitions=[]
for pi,part in enumerate(doc['voice_parts']):
    notes = [n for n in part['notes'] if n['lyric'] not in ('AP','SP')]
    for a,b in zip(notes, notes[1:]):
        if a['lyric']=='+' or b['lyric']=='+': continue
        jump = b['tone']-a['tone']
        if abs(jump) < 4: continue
        # boundary time
        ta = tm.tick_to_ms(part['position']+a['position'])/1000
        tb = tm.tick_to_ms(part['position']+a['position']+a['duration'])/1000
        start_c = a['tone']*100.0; end_c = b['tone']*100.0
        # measure over [tb-0.15, tb+0.15]
        T = np.arange(tb-0.15, tb+0.15, 0.005)
        C = np.interp(T, dt, dc)
        lo = min(start_c, end_c); hi = max(start_c, end_c)
        span = hi-lo
        if span < 300: continue
        # 10% and 90% crossing (in the direction of travel)
        if end_c > start_c:
            i10 = np.where(C >= lo + 0.10*span)[0]
            i90 = np.where(C >= lo + 0.90*span)[0]
        else:
            i10 = np.where(C <= hi - 0.10*span)[0]
            i90 = np.where(C <= hi - 0.90*span)[0]
        if len(i10)==0 or len(i90)==0: continue
        # restrict to after the boundary
        i10 = i10[i10 >= int(0.15/0.005)]
        i90 = i90[i90 >= int(0.15/0.005)]
        if len(i10)==0 or len(i90)==0: continue
        dur = (T[i90[0]] - T[i10[0]])*1000
        transitions.append((pi, a['lyric'], b['lyric'], jump, dur, tb))

print(f'相邻音符 >=4 半音的跳变: {len(transitions)}')
ds = np.array([t[4] for t in transitions])
print(f'  10->90% 完成时间: median {np.median(ds):.0f}ms  p10 {np.percentile(ds,10):.0f}  p90 {np.percentile(ds,90):.0f}')
print(f'  <60ms: {(ds<60).sum()}  <40ms: {(ds<40).sum()}  <20ms: {(ds<20).sum()}')

print('\n最陡的 12 个（跳变幅度大且时间短）:')
for t in sorted(transitions, key=lambda x: x[4])[:12]:
    print(f"  p{t[0]} {t[1]}->{t[2]} {t[3]:+d}半音 @{t[5]:.2f}s  10-90% {t[4]:.0f}ms")
