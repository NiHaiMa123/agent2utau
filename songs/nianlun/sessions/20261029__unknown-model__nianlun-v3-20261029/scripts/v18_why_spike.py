"""验证：681c 的 40ms 变化是「旋律本身的音符音高差」，而非 PITD 造成的尖刺。

方法：把同一时刻的 PITD 拿掉（用 before_pitd 即 note 阶梯线），看 40ms 变化有多大。
如果去掉 PITD 后仍是 600c+，说明是旋律的离散音符本身，任何实现都会有这个斜率。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))

def series(phrases, key):
    t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in phrases])
    c = np.concatenate([np.asarray(x[key],float) for x in phrases])
    o = np.argsort(t); return t[o], c[o]

dt, dc = series(pf['phrases'], 'final_cents')
bt, bc = series(bp['phrases'], 'before_pitd_cents')

def scan(t, c, units, label):
    res=[]
    for u in units:
        s0,s1=u['support_s']
        T=np.arange(s0,s1,0.005)
        if len(T)<12: continue
        C=np.interp(T,t,c)
        W=8
        diffs=np.array([C[i+W]-C[i] for i in range(len(C)-W)])
        res.append((u['id'], u['lyric'], float(np.max(np.abs(diffs)))))
    a=np.array([r[2] for r in res])
    print(f'{label}: median {np.median(a):.0f}c  p90 {np.percentile(a,90):.0f}  max {a.max():.0f}  '
          f'>300: {(a>300).sum()}  >500: {(a>500).sum()}')
    return res

print('40ms 窗口内最大音高变化（349 单元）:')
r_final = scan(dt, dc, inv['units'], '  含我的 PITD（最终线）')
r_base  = scan(bt, bc, inv['units'], '  仅音符阶梯（无 PITD）')

d = {x[0]: x[2] for x in r_final}
b = {x[0]: x[2] for x in r_base}
print('\n差异（PITD 让变化变大还是变小）:')
worse = [(k, d[k], b[k]) for k in d if k in b and d[k] > b[k] + 50]
better = [(k, d[k], b[k]) for k in d if k in b and d[k] < b[k] - 50]
print(f'  比无PITD更陡的单元: {len(worse)}   更平缓的: {len(better)}')
for k,x,y in sorted(worse, key=lambda z:-z[1])[:10]:
    print(f'    {k}: final {x:.0f}c  base {y:.0f}c')
print('\n最陡的 8 个单元（最终线 vs 仅音符阶梯）:')
for k in sorted(d, key=lambda z:-d[z])[:8]:
    print(f'  {k}: final {d[k]:.0f}c   base {b.get(k,0):.0f}c')
