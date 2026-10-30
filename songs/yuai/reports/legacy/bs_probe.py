"""研究白烁工程的音高线画法（只读研究，不复制数值）。

关注：
  1) 音高线用什么载体：note.pitch / PITD / 两者
  2) 节点密度（每字多少点、每平均多少点）
  3) 节点的时间分布（是否在字头密集、字腹稀疏）
  4) 斜率设置（是否零斜率、是否连续）
  5) 幅度分布（相对音符中心的偏移范围）
"""
import sys, json, io
import numpy as np
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')
doc = load_ustx(REF)
tm = TempoMap.from_doc(doc)
print('=== 白烁《雨爱》工程结构 ===')
print('keys:', [k for k in doc])
print('tracks:', len(doc['tracks']))
for i,tr in enumerate(doc['tracks']):
    print(f'  t{i}: singer={tr.get("singer")} mute={tr.get("mute")} volume={tr.get("volume")}')
print('voice_parts:', len(doc['voice_parts']))
tot_notes = sum(len(p['notes']) for p in doc['voice_parts'])
print('total notes:', tot_notes)

# curves
cc = Counter()
for p in doc['voice_parts']:
    for c in p.get('curves', []):
        cc[c['abbr']] += 1
print('\n所有曲线:', dict(cc))

# note.pitch points
np_pts = []
for pi,p in enumerate(doc['voice_parts']):
    for ni,n in enumerate(p['notes']):
        data = n.get('pitch', {}).get('data', [])
        if data: np_pts.append((pi,ni,len(data),data))
print(f'\nnote.pitch 非空音符: {len(np_pts)} / {tot_notes}')
if np_pts:
    cnts = [x[2] for x in np_pts]
    print(f'  每音符 pitch 点数: median {np.median(cnts):.1f}  p10 {np.percentile(cnts,10):.0f}  p90 {np.percentile(cnts,90):.0f}  max {max(cnts)}')
    print('\n  示例（前 3 个）:')
    for pi,ni,nc,data in np_pts[:3]:
        n = doc['voice_parts'][pi]['notes'][ni]
        print(f'   p{pi}n{ni} lyric={n["lyric"]} tone={n["tone"]} dur={n["duration"]}ticks points={nc}')
        for d in data[:12]:
            print(f'      x={d.get("x"):6} y={d.get("y"):6} shape={d.get("shape")}')

# PITD curve details
print('\n=== PITD 曲线 ===')
for p in doc['voice_parts']:
    for c in p.get('curves', []):
        if c['abbr'] == 'pitd':
            xs=np.array(c['xs']); ys=np.array(c['ys'])
            print(f'  part pos={p["position"]} dur={p["duration"]} pitd points={len(xs)}')
            print(f'    x range {xs.min()}..{xs.max()}  step median {np.median(np.diff(xs)) if len(xs)>1 else 0}')
            print(f'    y range {ys.min()}..{ys.max()}  median {np.median(ys)}  zero frac {(ys==0).mean():.1%}')
            print(f'    first 10 y: {ys[:10].tolist()}')
            break
    else:
        continue
    break
