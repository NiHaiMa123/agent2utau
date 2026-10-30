"""核查工作表中暴露的两个疑点：
  1) 极短单元（<0.10s）—— 是否又出现碎字
  2) 极大 body_dev（>200c）—— 设计线是否又偏离音符
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
sheet = json.load(io.open(NEW/'evaluation'/'visual_review_sheet.json', encoding='utf-8'))
rows = [u for p in sheet['pages'] for u in p]

short = [r for r in rows if r['dur'] < 0.10]
big = [r for r in rows if r['body_dev'] is not None and abs(r['body_dev']) > 200]
print(f'units < 0.10s: {len(short)}')
for r in sorted(short, key=lambda x:x['dur'])[:15]:
    print(f"  {r['id']:12s} {r['lyric']} tone={r['tone']} dur={r['dur']:.3f}s "
          f"design span {r['design_span']:.0f} bodydev {r['body_dev']:+.0f}")

print(f'\nunits |body_dev| > 200c: {len(big)}')
for r in sorted(big, key=lambda x:-abs(x['body_dev']))[:15]:
    print(f"  {r['id']:12s} {r['lyric']} tone={r['tone']} dur={r['dur']:.2f}s "
          f"design {r['design_min']:.0f}..{r['design_max']:.0f} bodydev {r['body_dev']:+.0f}")

# 分布
durs=np.array([r['dur'] for r in rows])
print(f'\nduration: min {durs.min():.3f} p5 {np.percentile(durs,5):.3f} median {np.median(durs):.3f}')
print(f'  <0.08s {(durs<0.08).sum()}  <0.10s {(durs<0.10).sum()}  <0.12s {(durs<0.12).sum()}')
devs=np.array([abs(r['body_dev']) for r in rows if r['body_dev'] is not None])
print(f'|body_dev|: median {np.median(devs):.1f}  p90 {np.percentile(devs,90):.1f}  max {devs.max():.0f}')
