"""检查一个关键的潜在缺陷：设计曲线是否在音符主体内没落到该音符的音高上。

如果中心线在音符 body 里大幅偏离该音符的整数 tone，听感就是「滑过去/没唱准这个音」，
这正是 v2「垂直台阶」的另一个极端。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project.ustx')
tm = TempoMap.from_doc(doc)
pitch = json.load(io.open(NEW/'compiled'/'pitch.json', encoding='utf-8'))

rows = []
for pi, part in enumerate(doc['voice_parts']):
    for n in part['notes']:
        if n['lyric'] in ('AP', 'SP'):
            continue
        a = tm.tick_to_ms(part['position']+n['position'])/1000
        b = tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        rows.append(dict(pi=pi, a=a, b=b, tone=n['tone'], lyric=n['lyric'], dur=b-a))

# build design series
dt = np.concatenate([np.asarray(x['times_ms'], float)/1000 for x in pitch['phrases']])
dc = np.concatenate([np.asarray(x['final_cents'], float) for x in pitch['phrases']])
o = np.argsort(dt); dt, dc = dt[o], dc[o]

devs = []
for r in rows:
    d = r['dur']
    # body = middle 50% of the note
    lo, hi = r['a']+0.25*d, r['b']-0.25*d
    if hi <= lo: continue
    T = np.arange(lo, hi, 0.005)
    if len(T) < 3: continue
    c = np.interp(T, dt, dc)
    target = r['tone']*100
    body_med = float(np.median(c))
    rows_dev = c - target
    devs.append(dict(pi=r['pi'], lyric=r['lyric'], a=r['a'], dur=d, tone=r['tone'],
                     body_med=body_med, dev=body_med-target,
                     max_dev=float(np.max(np.abs(rows_dev))),
                     min_dev=float(np.min(rows_dev))))

dev = np.array([x['dev'] for x in devs])
mx = np.array([x['max_dev'] for x in devs])
print(f'=== 音符主体（中间50%）设计线 vs 该音符整数音高 ===')
print(f'notes {len(devs)}')
print(f'  body median deviation: median {np.median(dev):+7.1f}c  med|Δ| {np.median(np.abs(dev)):6.1f}c  '
      f'p90|Δ| {np.percentile(np.abs(dev),90):6.1f}c')
for thr in (25, 50, 75, 100):
    print(f'    |body dev|>{thr:3d}c: {(np.abs(dev)>thr).mean():6.1%}  ({(np.abs(dev)>thr).sum()} notes)')
print(f'\n  max |deviation| inside body: median {np.median(mx):.1f}c  p90 {np.percentile(mx,90):.1f}c')
print(f'    notes whose body wanders >100c: {(mx>100).sum()} ({(mx>100).mean():.1%})')
print(f'    notes whose body wanders >150c: {(mx>150).sum()}')

print('\nworst body deviations:')
for x in sorted(devs, key=lambda z: -abs(z['dev']))[:15]:
    print(f"  p{x['pi']} {x['lyric']} @{x['a']:.2f}s dur={x['dur']:.2f} tone={x['tone']} "
          f"body_med={x['body_med']:.0f} dev={x['dev']:+.0f}c range=[{x['min_dev']:+.0f},{x['max_dev']:+.0f}]")
