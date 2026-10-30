"""咬字 13.3pp 差距的真正来源排查（前三个消融已排除音高与发声层）。

现在检查：辅音时长占比与总时长。
  咬字依赖辅音瞬态。如果辅音相对元音太短，辅音会被元音盖住。
对照：
  A) 我们谱面：音符时长 vs 原生辅音时长
  B) 原唱：HFA 观测的辅音/元音时长
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
ONSETS = set('b p m f d t n l g k h j q x zh ch sh r z c s y w'.split())

# 我们编译后的音素
ph = json.load(io.open(NEW/'compiled'/'phones.json', encoding='utf-8'))
ours_con=[]; ours_vow=[]
for part in ph['parts']:
    for phrase in part['phrases']:
        for q in phrase['phones']:
            mk = q['phoneme'].split('/',1)[-1]
            if mk in ('SP','AP','EP',''): continue
            d = (q['end_ms']-q['start_ms'])
            (ours_con if mk in ONSETS else ours_vow).append(d)

oc = np.array(ours_con); ov = np.array(ours_vow)
print('=== 我们（编译后的原生音素）===')
print(f'  辅音 {len(oc)}: median {np.median(oc):.0f}ms  p10 {np.percentile(oc,10):.0f}  p90 {np.percentile(oc,90):.0f}')
print(f'  元音 {len(ov)}: median {np.median(ov):.0f}ms  p10 {np.percentile(ov,10):.0f}  p90 {np.percentile(ov,90):.0f}')
print(f'  辅音占比: {oc.sum()/(oc.sum()+ov.sum()):.1%}')

# 原唱 HFA 观测
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))
sc=[]; sv=[]
for p in h['phrases']:
    for q in p['phones']:
        mk = q['mark']
        if mk in ('SP','AP','EP',''): continue
        d = q['dur']*1000
        (sc if mk in ONSETS else sv).append(d)
sc=np.array(sc); sv=np.array(sv)
print('\n=== 原唱（HFA 观测）===')
print(f'  辅音 {len(sc)}: median {np.median(sc):.0f}ms  p10 {np.percentile(sc,10):.0f}  p90 {np.percentile(sc,90):.0f}')
print(f'  元音 {len(sv)}: median {np.median(sv):.0f}ms  p10 {np.percentile(sv,10):.0f}  p90 {np.percentile(sv,90):.0f}')
print(f'  辅音占比: {sc.sum()/(sc.sum()+sv.sum()):.1%}')

print('\n=== 对比 ===')
print(f'  辅音中位: 我们 {np.median(oc):.0f}ms  vs  原唱 {np.median(sc):.0f}ms  '
      f'({np.median(oc)/max(np.median(sc),1):.2f}x)')
print(f'  元音中位: 我们 {np.median(ov):.0f}ms  vs  原唱 {np.median(sv):.0f}ms  '
      f'({np.median(ov)/max(np.median(sv),1):.2f}x)')
print(f'  辅音占比: 我们 {oc.sum()/(oc.sum()+ov.sum()):.1%}  vs  原唱 {sc.sum()/(sc.sum()+sv.sum()):.1%}')
