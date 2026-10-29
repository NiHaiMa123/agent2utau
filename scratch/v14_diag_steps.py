"""检查编译后的 PITD 为何仍有 141 个 >200c 的步：
  对比「我写的 PITD」(score/v14_score.ustx) 与「编译后的 PITD」(compiled/project_v14.ustx)。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
for label, p in [('score (我写的 PITD)', NEW/'score'/'v14_score.ustx'),
                 ('compiled (编译后)', NEW/'compiled'/'project_v14.ustx')]:
    d = load_ustx(p)
    ys=[]; steps=[]
    for part in d['voice_parts']:
        pit=next((c for c in part.get('curves',[]) if c['abbr']=='pitd'),None)
        if not pit: continue
        y=np.array(pit['ys'],float); x=np.array(pit['xs'],float)
        ys.extend(y.tolist())
        dy=np.abs(np.diff(y))
        steps.append(dy)
    y=np.array(ys); allsteps=np.concatenate(steps)
    print(f'=== {label} ===')
    print(f'  points {len(y)}  p50 {np.percentile(y,50):+.0f}  p99 {np.percentile(y,99):+.0f}')
    print(f'  |dy| median {np.median(allsteps):.1f}  p99 {np.percentile(allsteps,99):.1f}  max {allsteps.max():.0f}')
    print(f'  steps >200: {(allsteps>200).sum()}  >400: {(allsteps>400).sum()}')

# where are the big steps in the compiled version?
d = load_ustx(NEW/'compiled'/'project_v14.ustx')
for pi, part in enumerate(d['voice_parts']):
    pit=next((c for c in part.get('curves',[]) if c['abbr']=='pitd'),None)
    if not pit: continue
    y=np.array(pit['ys'],float); x=np.array(pit['xs'],float)
    dy=np.abs(np.diff(y))
    idx=np.where(dy>200)[0]
    if len(idx):
        print(f'\npart{pi}: {len(idx)} big steps')
        for i in idx[:6]:
            print(f'   tick {x[i]:8.0f} -> {x[i+1]:8.0f}   {y[i]:+7.0f} -> {y[i+1]:+7.0f}  (dy {dy[i]:.0f})')
        print(f'   part duration {part["duration"]}  notes {len(part["notes"])}')
        break
