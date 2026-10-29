"""判断 46c 偏差的性质：是设计错了，还是原唱本身在快速波动？

方法：对每个字，比较
  (a) 设计线在其窗口内的标准差 vs
  (b) 原唱 F0 在其窗口内的标准差
若 (b) >> (a)，说明我们做了合理的平滑（去掉了源抖动），偏差来自抖动而非错误。
若 (a) >> (b)，说明我们加了源里没有的运动。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
def midi(hz): return 69+12*np.log2(np.maximum(hz,1e-6)/440)
s = np.load(NEW/'inputs/fcpe.npz'); s2 = np.load(NEW/'inputs/rmvpe.npz')
st = s['times'].astype(float)
cf = np.where(s['voiced'], midi(s['f0_hz'])*100, np.nan)
cr = np.where(s2['voiced'], midi(s2['f0_hz'])*100, np.nan)
ok = np.isfinite(cf)&np.isfinite(cr)&(np.abs(cf-cr)<=100)
src = np.where(ok,(cf+cr)/2,np.nan)

p = json.load(io.open(NEW/'compiled/pitch.json',encoding='utf-8'))
dt = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in p['phrases']])
dc = np.concatenate([np.asarray(x['final_cents'],float) for x in p['phrases']])
o = np.argsort(dt); dt,dc = dt[o],dc[o]

W = json.load(io.open(NEW/'words_v3.json',encoding='utf-8'))
rows = []
for ph in W['phrases']:
    for w in ph['words']:
        a,b = w['start'], w['end']; d = b-a
        lo,hi = a+0.22*d, b-0.22*d
        T = np.arange(lo,hi,0.01)
        if len(T) < 5: continue
        i = np.clip(np.rint(T*100).astype(int),0,len(st)-1)
        ss = src[i]; m = np.isfinite(ss)
        if m.sum() < 5: continue
        des = np.interp(T[m], dt, dc)
        rows.append(dict(hanzi=w['hanzi'], dur=d,
                         src_std=float(np.std(ss[m])), des_std=float(np.std(des)),
                         err=float(np.median(des-ss[m]))))

sr = np.array([r['src_std'] for r in rows]); dr = np.array([r['des_std'] for r in rows])
er = np.array([r['err'] for r in rows])
print(f'syllables {len(rows)}')
print(f'  source within-syllable std: median {np.median(sr):.1f}c  p90 {np.percentile(sr,90):.1f}c')
print(f'  design within-syllable std: median {np.median(dr):.1f}c  p90 {np.percentile(dr,90):.1f}c')
print(f'  ratio design/source: median {np.median(dr/np.maximum(sr,1e-6)):.2f}')
print(f'\n  median error {np.median(er):+.1f}c, med|err| {np.median(np.abs(er)):.1f}c')
print(f'  correlation(src_std, |err|): {np.corrcoef(sr, np.abs(er))[0,1]:.3f}')

# how much error is explained by source jitter?
print(f'\n  if we matched source perfectly, err would be 0.')
print(f'  source jitter (std) alone could produce up to ~{np.median(sr):.0f}c typical deviation from a smooth fit')
big_src = sr > np.percentile(sr, 75)
big_des = dr > np.percentile(dr, 75)
print(f'\n  |err| for high-source-jitter syllables: {np.median(np.abs(er[big_src])):.1f}c')
print(f'  |err| for low-source-jitter  syllables: {np.median(np.abs(er[~big_src])):.1f}c')

# duration effect
short = np.array([r['dur']<0.30 for r in rows])
print(f'\n  |err| short syllables (<0.30s): {np.median(np.abs(er[short])):.1f}c (n={short.sum()})')
print(f'  |err| long  syllables (>=0.30s): {np.median(np.abs(er[~short])):.1f}c (n={(~short).sum()})')
