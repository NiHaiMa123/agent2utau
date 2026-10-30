"""定位 13c 误差的来源：具体哪些 tick 偏、偏在哪。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
mine = load_ustx(NEW/'score'/'v15_score.ustx')
compiled = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(compiled)

mymap = {}
for mp in mine['voice_parts']:
    pit = next(c for c in mp['curves'] if c['abbr']=='pitd')
    mymap[int(mp['position'])] = (np.array(pit['xs'],float), np.array(pit['ys'],float))
# what PITD did the compiler actually write?
cmap = {}
for cp in compiled['voice_parts']:
    pit = next((c for c in cp['curves'] if c['abbr']=='pitd'), None)
    if pit: cmap[int(cp['position'])] = (np.array(pit['xs'],float), np.array(pit['ys'],float))

# find worst frames
worst=[]
for bph, fph in zip(bp['phrases'], pf['phrases']):
    pos=int(bph['part_position'])
    if pos not in mymap: continue
    xs, ys = mymap[pos]
    times=np.asarray(bph['times_ms'],float)
    ticks=np.array([tm.ms_to_tick(t)-pos for t in times])
    off=np.interp(ticks,xs,ys)
    actual=np.asarray(fph['final_cents'],float)
    before=np.asarray(bph['before_pitd_cents'],float)
    err=actual-(before+off)
    idx=np.argsort(-np.abs(err))[:5]
    for i in idx:
        if abs(err[i])>3:
            worst.append((pos, ticks[i], before[i], off[i], actual[i], err[i]))

worst.sort(key=lambda x:-abs(x[5]))
print(f'frames with |err|>3c: {len(worst)}')
for w in worst[:15]:
    print(f"  part pos={w[0]:6.0f} tick={w[1]:8.0f} before={w[2]:9.1f} myPITD={w[3]:+7.0f} "
          f"actual={w[4]:9.1f} err={w[5]:+7.1f}")

# check: does compiler-written pitd equal mine?
print('\n=== PITD written by compiler vs mine ===')
diffs=[]
for pos in list(mymap)[:5]:
    xs,ys = mymap[pos]
    if pos not in cmap: continue
    cxs,cys = cmap[pos]
    # compare at overlapping ticks
    n=min(len(xs),len(cxs))
    d=np.abs(np.interp(cxs, xs, ys) - cys)
    diffs.append(d)
    print(f'  pos {pos}: mine {len(xs)} pts, compiled {len(cxs)} pts, max|diff| {d.max():.0f}')
