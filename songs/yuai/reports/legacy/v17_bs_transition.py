"""白烁的跳变速度：直接用其工程的 note.tone + PITD 计算最终线（无需渲染/声库）。

最终线 ≈ note tone*100 + PITD（该时刻，part 相对 tick）。
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

def build_final(part):
    """sample final line on 2ms grid across the part."""
    pit = next((c for c in part['curves'] if c['abbr']=='pitd'), None)
    if pit is None: return None, None
    xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
    dur=int(part['duration'])
    tick_grid=np.arange(xs[0], xs[-1]+1, 2)
    off=np.interp(tick_grid, xs, ys)
    # note tone at each tick
    tone=np.zeros(len(tick_grid))
    for n in part['notes']:
        na=n['position']; nb=na+n['duration']
        m=(tick_grid>=na)&(tick_grid<nb)
        tone[m]=n['tone']
    # carry last tone into gaps
    for i in range(1,len(tone)):
        if tone[i]==0 and tone[i-1]!=0: tone[i]=tone[i-1]
    final = tone*100.0 + off
    ms = np.array([tm.tick_to_ms(x) for x in tick_grid])/1000
    return ms, final

allres=[]
for part in doc['voice_parts']:
    ms,final = build_final(part)
    if ms is None: continue
    notes=[n for n in part['notes'] if n['lyric'] not in ('AP','SP','EP')]
    for a,b in zip(notes, notes[1:]):
        if a['lyric'] in ('+','') or b['lyric'] in ('+',''): continue
        jump=b['tone']-a['tone']
        if abs(jump)<4: continue
        tb = tm.tick_to_ms(part['position']+a['position']+a['duration'])/1000
        s=a['tone']*100.0; e=b['tone']*100.0
        m=(ms>=tb-0.06)&(ms<=tb+0.20)
        if m.sum()<10: continue
        Tm=ms[m]; Cm=final[m]
        lo,hi=min(s,e),max(s,e); span=hi-lo
        if span<300: continue
        if e>s:
            i10=np.where(Cm>=lo+0.10*span)[0]; i90=np.where(Cm>=lo+0.90*span)[0]
        else:
            i10=np.where(Cm<=hi-0.10*span)[0]; i90=np.where(Cm<=hi-0.90*span)[0]
        if not len(i10) or not len(i90): continue
        a0,b0=i10[0],i90[0]
        if b0<=a0: continue
        dC=np.abs(np.diff(Cm))/(np.diff(Tm)+1e-12)
        allres.append(dict(jump=jump, dur_ms=(Tm[b0]-Tm[a0])*1000, max_speed=float(dC.max())))

if allres:
    ds=np.array([r['dur_ms'] for r in allres]); sp=np.array([r['max_speed'] for r in allres])
    print(f'=== 白烁 雨爱 ===  n={len(allres)}')
    print(f'  10-90% 时间: median {np.median(ds):.0f}ms  p10 {np.percentile(ds,10):.0f}  p90 {np.percentile(ds,90):.0f}')
    print(f'  最大速度: median {np.median(sp):.0f}c/s  p10 {np.percentile(sp,10):.0f}  p90 {np.percentile(sp,90):.0f}')
    print(f'  <40ms: {(ds<40).sum()}  <25ms: {(ds<25).sum()}  <15ms: {(ds<15).sum()}')
    print(f'\n对比本版: median 98ms, 最大速度 6637c/s, <40ms: 0')
