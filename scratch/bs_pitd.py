"""深入分析白烁 PITD 画法的本质：
  1) PITD 是每 10 tick 一个点 = 密集逐点曲线（这才是「手调」的载体）
  2) 它的形状特征是什么？（相对 before-PITD 的偏移分布、变化率、是否平滑）
  3) 与音符时间的关系（字头/字腹/字尾各段的偏移特征）
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')
doc = load_ustx(REF)
tm = TempoMap.from_doc(doc)
res = doc.get('resolution', 480)
tick_ms = 60000.0/(float(doc['tempos'][0]['bpm'])*res)
print(f'resolution={res} bpm={doc["tempos"][0]["bpm"]} -> 1 tick = {tick_ms:.4f} ms')

for pi,p in enumerate(doc['voice_parts']):
    pitd = next((c for c in p.get('curves',[]) if c['abbr']=='pitd'), None)
    if not pitd: continue
    xs = np.array(pitd['xs'], float); ys = np.array(pitd['ys'], float)
    print(f'\n=== part {pi}: pitd {len(xs)} points, x {xs[0]:.0f}..{xs[-1]:.0f} ticks ===')
    dx = np.diff(xs)
    print(f'  x step: median {np.median(dx):.1f} ticks ({np.median(dx)*tick_ms:.1f} ms), '
          f'min {dx.min():.0f}, max {dx.max():.0f}, all_equal {np.all(dx==dx[0])}')
    print(f'  y: min {ys.min():.0f} max {ys.max():.0f} mean {ys.mean():+.1f} median {np.median(ys):.1f} std {ys.std():.1f}')
    print(f'  y percentiles 5/25/50/75/95: {np.percentile(ys,5):.0f}/{np.percentile(ys,25):.0f}/{np.percentile(ys,50):.0f}/{np.percentile(ys,75):.0f}/{np.percentile(ys,95):.0f}')
    print(f'  |y|>500 frac {(np.abs(ys)>500).mean():.2%}   |y|<50 frac {(np.abs(ys)<50).mean():.2%}')
    dy = np.diff(ys)
    print(f'  point-to-point change: median |dy| {np.median(np.abs(dy)):.1f}c  p90 {np.percentile(np.abs(dy),90):.1f}c  max {np.abs(dy).max():.0f}c')
    # is it smooth? compare |dy| to what a slow curve would give
    print(f'  => 中位逐点变化 {np.median(np.abs(dy)):.1f}c / {np.median(dx)*tick_ms:.0f}ms '
          f'= {np.median(np.abs(dy))/(np.median(dx)*tick_ms)*1000:.0f} c/s')

    # per-note analysis: offset profile relative to note body
    print(f'\n  --- 逐音符的 PITD 形态 ---')
    notes = p['notes']
    rows=[]
    for ni,n in enumerate(notes):
        if n['lyric'] in ('AP','SP'): continue
        na = p['position']+n['position']; nb = na+n['duration']
        m=(xs>=na)&(xs<nb)
        if m.sum()<3: continue
        seg = ys[m]
        rows.append(dict(ni=ni, lyric=n['lyric'], dur=n['duration'], tone=n['tone'],
                         n=int(m.sum()), med=float(np.median(seg)), mn=float(seg.min()),
                         mx=float(seg.max()), std=float(seg.std()),
                         first=float(seg[:max(1,len(seg)//6)].mean()),
                         last=float(seg[-max(1,len(seg)//6):].mean())))
    print(f'  可比音符 {len(rows)}')
    if rows:
        stds=np.array([r['std'] for r in rows])
        meds=np.array([r['med'] for r in rows])
        rng=np.array([r['mx']-r['mn'] for r in rows])
        print(f'  音符内 PITD std: median {np.median(stds):.0f}c  p90 {np.percentile(stds,90):.0f}c')
        print(f'  音符内 PITD 范围: median {np.median(rng):.0f}c  p90 {np.percentile(rng,90):.0f}c')
        print(f'  音符中位偏移分布: 5/50/95 pct = {np.percentile(meds,5):.0f}/{np.percentile(meds,50):.0f}/{np.percentile(meds,95):.0f}c')
        print('\n  前 15 个音符的 PITD 形态:')
        for r in rows[:15]:
            print(f"    {r['lyric']:6s} tone={r['tone']:3d} dur={r['dur']:4d} n={r['n']:3d} "
                  f"med={r['med']:+7.0f} range=[{r['mn']:+6.0f},{r['mx']:+6.0f}] "
                  f"first={r['first']:+6.0f} last={r['last']:+6.0f}")
