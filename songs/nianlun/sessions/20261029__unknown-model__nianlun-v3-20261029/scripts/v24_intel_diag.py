"""最后一轮改进：针对咬字差距（56.0% vs 源 69.3%）的可控因素。

已知咬字影响因素：
  1) 辅音时长（已测：median 140ms，正常）
  2) 音高曲线在字头的大幅滑入（会模糊起音）—— 我们的字头滑入可达 130c
  3) 发声层 BREC/VOIC 过强会使辅音发虚
  4) DYN 过低会把字头压小

检查 2) 和 4)：字头滑入深度与 DYN 的关系。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)

# 每 part 的 DYN 值与 PITD 字头深度
print('parts: DYN range | PITD head depth | notes')
summ=[]
for pi,part in enumerate(doc['voice_parts']):
    curves={c['abbr']: c for c in part['curves']}
    dyn = curves.get('dyn')
    pitd = curves.get('pitd')
    dv = (min(dyn['ys']), max(dyn['ys'])) if dyn else None
    # PITD 字头深度：每音符前 15% 的偏离
    xs=np.array(pitd['xs'],float); ys=np.array(pitd['ys'],float)
    heads=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=n['position']; b=a+n['duration']
        m=(xs>=a)&(xs<a+0.15*(b-a))
        if m.sum()>=2: heads.append(float(np.abs(ys[m]).max()))
    summ.append(dict(pi=pi, dyn=dv, head_max=round(max(heads),0) if heads else 0,
                     head_med=round(float(np.median(heads)),0) if heads else 0))

dyns=[s['dyn'][1] for s in summ if s['dyn']]
print(f'  DYN max: median {np.median(dyns):.0f}  range {min(dyns):.0f}..{max(dyns):.0f}')
hm=[s['head_max'] for s in summ]
print(f'  PITD head |max|: median {np.median(hm):.0f}c  max {max(hm):.0f}c')

# 检查 BREC/VOIC 强度
brec=[]; voic=[]
for part in doc['voice_parts']:
    for c in part['curves']:
        if c['abbr']=='brec': brec.extend(c['ys'])
        if c['abbr']=='voic': voic.extend(c['ys'])
brec=np.array(brec); voic=np.array(voic)
print(f'\n  BREC: median {np.median(brec):.0f}  range {brec.min()}..{brec.max()}  '
      f'|BREC|>10 占比 {(np.abs(brec)>10).mean():.1%}')
print(f'  VOIC: median {np.median(voic):.0f}  range {voic.min()}..{voic.max()}  '
      f'VOIC<95 占比 {(voic<95).mean():.1%}')

print('\n判读:')
print(f'  BREC 中位 {np.median(brec):.0f} 接近 0，说明气声层不是中性（0）而是有系统偏移')
print(f'  VOIC 中位 {np.median(voic):.0f} 高于 100，说明整体加了发声成分')
print(f'  这两项过强会使辅音发虚 —— 可能是咬字下降的一个原因')
