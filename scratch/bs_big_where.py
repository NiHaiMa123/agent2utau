"""关键问题：白烁的大 PITD 值出现在哪里？

假设 A：音符边界附近（换音过渡）
假设 B：长音内部（深颤音）
假设 C：与音符音高变化有关（大跳）

用位置分布判定。
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

rows=[]   # (abs_u_in_note, value, note_dur_ticks, tone, note_index, prev_tone)
for pi,part in enumerate(doc['voice_parts']):
    pit = next((c for c in part.get('curves',[]) if c['abbr']=='pitd'), None)
    if not pit: continue
    xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
    notes = part['notes']
    for ni,n in enumerate(notes):
        if n['lyric'] in ('AP','SP','EP'): continue
        na=part['position']+n['position']; nb=na+n['duration']
        m=(xs>=na)&(xs<=nb)
        if m.sum()<6: continue
        u=(xs[m]-na)/max(nb-na,1)
        v=ys[m]
        prev = notes[ni-1]['tone'] if ni>0 else None
        for a,b in zip(u,v):
            rows.append((a,b,n['duration'],n['tone'],ni,prev))

A=np.array([[r[0] for r in rows],[r[1] for r in rows],
            [r[2] for r in rows],[r[3] for r in rows]]).T
u=A[:,0]; y=A[:,1]; dur=A[:,2]; tone=A[:,3]
big=np.abs(y)>300
print(f'总点 {len(y)}, |y|>300 的点 {big.sum()} ({big.mean():.2%})')

print('\n=== 假设A：大值是否在音符边界附近 ===')
for lo,hi in [(0,0.10),(0.10,0.25),(0.25,0.75),(0.75,0.90),(0.90,1.01)]:
    m=(u>=lo)&(u<hi)
    if m.sum():
        print(f'  u {lo:.2f}-{hi:.2f}: n={m.sum():5d}  |y|>300 占比 {(np.abs(y[m])>300).mean():6.2%}  '
              f'median|y| {np.median(np.abs(y[m])):6.1f}c')

print('\n=== 假设B：大值是否与音符时长有关 ===')
for lo,hi in [(0,240),(240,480),(480,960),(960,100000)]:
    m=(dur>=lo)&(dur<hi)
    if m.sum():
        print(f'  dur {lo:5.0f}-{hi:6.0f}t ({lo*1.5625:.0f}-{hi*1.5625:.0f}ms): n={m.sum():5d}  '
              f'|y|>300 占比 {(np.abs(y[m])>300).mean():6.2%}  median|y| {np.median(np.abs(y[m])):6.1f}c')

print('\n=== 假设C：大值是否在音符间音程大的位置 ===')
# 用相邻 tone 差分组（对每个音符的所有点）
rows2=[]
for r in rows:
    rows2.append(r)
# per-note tone jumps
note_jump={}
for pi,part in enumerate(doc['voice_parts']):
    notes=part['notes']
    for ni,n in enumerate(notes):
        if ni>0 and n['lyric'] not in ('AP','SP','EP') and notes[ni-1]['lyric'] not in ('AP','SP','EP'):
            note_jump[(pi,ni)]=n['tone']-notes[ni-1]['tone']
groups={}
for pi,part in enumerate(doc['voice_parts']):
    pit = next((c for c in part.get('curves',[]) if c['abbr']=='pitd'), None)
    if not pit: continue
    xs=np.array(pit['xs'],float); ys=np.array(pit['ys'],float)
    for ni,n in enumerate(part['notes']):
        na=part['position']+n['position']; nb=na+n['duration']
        m=(xs>=na)&(xs<=nb)
        if m.sum()<6: continue
        j=note_jump.get((pi,ni))
        key='first' if j is None else ('unison' if j==0 else 'step' if abs(j)<=2 else 'small' if abs(j)<=4 else 'big')
        groups.setdefault(key,[]).extend(ys[m].tolist())
for k,v in groups.items():
    v=np.array(v)
    print(f'  {k:8s}: n={len(v):5d}  |y|>300 占比 {(np.abs(v)>300).mean():6.2%}  '
          f'median|y| {np.median(np.abs(v)):6.1f}  p95|y| {np.percentile(np.abs(v),95):6.0f}')
