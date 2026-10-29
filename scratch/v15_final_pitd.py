"""用连续 PITD 覆盖编译结果。

事实：compile-functions 按「原生短语」独立编码 PITD，短语边界重新对齐 before_pitd，
      导致相邻短语间出现 400c+ 跳变（实测 part0 tick 1110: -261 -> +170）。
做法：把 score/v14_score.ustx 里我自己写的、跨音符连续的 PITD 写回编译后的工程。
"""
import sys
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
compiled = load_ustx(NEW/'compiled'/'project_v14.ustx')
mine = load_ustx(NEW/'score'/'v14_score.ustx')

mymap = {}
for mpart in mine['voice_parts']:
    pit = next((c for c in mpart['curves'] if c['abbr'] == 'pitd'), None)
    if pit is not None:
        mymap[int(mpart['position'])] = pit

print(f'mine pitd parts: {len(mymap)}  compiled parts: {len(compiled["voice_parts"])}')

replaced = 0
for cpart in compiled['voice_parts']:
    pit = mymap.get(int(cpart['position']))
    if pit is None:
        continue
    cpart['curves'] = [c for c in cpart['curves'] if c['abbr'] != 'pitd']
    cpart['curves'].append(dict(abbr='pitd', xs=list(pit['xs']), ys=list(pit['ys'])))
    replaced += 1
print(f'replaced: {replaced}')

steps = []
for part in compiled['voice_parts']:
    pit = next((c for c in part['curves'] if c['abbr'] == 'pitd'), None)
    if pit is None:
        continue
    y = np.array(pit['ys'], float)
    if len(y) > 1:
        steps.append(np.abs(np.diff(y)))
if steps:
    allst = np.concatenate(steps)
    print(f"after replacement: |dy| median {np.median(allst):.1f}  max {allst.max():.0f}  "
          f"steps>200 {int((allst>200).sum())}")

OUT = NEW/'compiled'/'project_final.ustx'
save_ustx(compiled, OUT)
print(f'wrote {OUT}')
