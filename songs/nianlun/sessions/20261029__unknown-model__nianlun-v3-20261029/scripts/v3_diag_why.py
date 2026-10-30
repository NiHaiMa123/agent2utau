"""关键问题：如果 F0 贴合不是主因，那什么才是？

对比 v2 与 v3d 渲染音频的其它维度：
  1) 音素时长分布（是否吞字/碎字）
  2) 音频能量包络（动态是否有层次）
  3) 频谱特征（音色是否单调）
  4) 起音/辅音是否清晰（噪声段比例）
  5) 静音/呼吸组织
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')

files = [('source', NEW/'inputs/stems/vocals.wav'),
         ('v2', V2/'render'/'vocal_vocal.wav'),
         ('v3d', NEW/'render'/'vocal_v3d_vocal.wav')]

for name, p in files:
    if not p.exists(): print(f'{name}: missing'); continue
    a, sr = sf.read(str(p), dtype='float32')
    if a.ndim > 1: a = a.mean(1)
    # 20ms frames
    w = int(0.02*sr); n = len(a)//w
    e = np.sqrt((a[:n*w].reshape(n, w)**2).mean(1))
    db = 20*np.log10(np.maximum(e, 1e-9))
    act = db > (np.percentile(db,95)-30)
    # dynamic range within active
    ar = db[act]
    print(f'\n=== {name} ({len(a)/sr:.1f}s) ===')
    print(f'  peak {np.abs(a).max():.3f}  rms {np.sqrt((a**2).mean()):.4f}')
    print(f'  active frames {act.mean():.1%}, dB range {ar.min():.1f}..{ar.max():.1f}')
    print(f'  dB p10/p50/p90: {np.percentile(ar,10):.1f}/{np.percentile(ar,50):.1f}/{np.percentile(ar,90):.1f}  '
          f'IQR {np.percentile(ar,75)-np.percentile(ar,25):.1f}dB')
    # silence runs
    sil = ~act
    runs, c = [], 0
    for s in sil:
        if s: c += 1
        elif c: runs.append(c*0.02); c = 0
    if c: runs.append(c*0.02)
    runs = [r for r in runs if r >= 0.10]
    print(f'  silent gaps >=0.10s: {len(runs)}, total {sum(runs):.1f}s, median {np.median(runs) if runs else 0:.2f}s')
    # energy modulation: how much does 20ms energy vary within 0.5s windows (articulation?)
    k = 25  # 0.5s
    m = n//k*k
    env = e[:m].reshape(m//k, k)
    cv = (env.std(1)/np.maximum(env.mean(1),1e-9))
    print(f'  within-0.5s energy CV: median {np.median(cv):.3f} (higher = more articulation in phrase)')
    # zero crossing rate (proxy for consonant/noise content)
    zcr = (np.abs(np.diff(np.sign(a)))>0).mean()
    print(f'  zero-crossing rate: {zcr:.4f}')
