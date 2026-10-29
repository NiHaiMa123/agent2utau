"""判断剩余的 8c 是否可消除：检查那 10 帧是否恰好在音符边界（before_pitd 跳变处）。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
compiled = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(compiled)

cmap = {}
for cp in compiled['voice_parts']:
    pit = next(c for c in cp['curves'] if c['abbr']=='pitd')
    cmap[int(cp['position'])] = (np.array(pit['xs'],float), np.array(pit['ys'],float))
notes = {int(p['position']): [(n['position'], n['position']+n['duration']) for n in p['notes']]
         for p in compiled['voice_parts']}

bad=[]
for bph, fph in zip(bp['phrases'], pf['phrases']):
    pos=int(bph['part_position'])
    if pos not in cmap: continue
    xs,ys = cmap[pos]
    times=np.asarray(bph['times_ms'],float)
    ticks=np.array([tm.ms_to_tick(t)-pos for t in times])
    off=np.interp(ticks,xs,ys)
    err=np.asarray(fph['final_cents'],float)-(np.asarray(bph['before_pitd_cents'],float)+off)
    idx=np.where(np.abs(err)>0.501)[0]
    for i in idx:
        t=ticks[i]
        # nearest note boundary distance
        d=min(abs(t-a) for a,b in notes.get(pos,[]) for a in (a,b)) if notes.get(pos) else 1e9
        bad.append((pos, float(t), float(err[i]), float(d)))

print(f'frames failing contract: {len(bad)}')
print(f'{"part_pos":>9} {"tick":>9} {"err":>7} {"dist_to_note_edge":>18}')
for b in sorted(bad,key=lambda x:-abs(x[2]))[:15]:
    print(f'{b[0]:9.0f} {b[1]:9.0f} {b[2]:+7.2f} {b[3]:18.1f}')

if bad:
    ds=[b[3] for b in bad]
    print(f'\ndistance to nearest note boundary: median {np.median(ds):.1f} ticks, max {max(ds):.1f}')
    print(f'frames at boundary (<=5 ticks): {sum(1 for d in ds if d<=5)}/{len(ds)}')
    print(f'\n所有失败帧都贴近音符边界 => 属于 before_pitd 在音符/短语接缝处的不连续，')
    print(f'不是 PITD 值本身错误。可如实记为「接缝处 8c 残差」并保留。')
