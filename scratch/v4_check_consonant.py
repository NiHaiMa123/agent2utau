"""检查辅音时长：字头爆发感不足（v3k 1.6dB vs 原唱 3.5dB）的可疑主因。

DiffSinger 里，一个汉字 = 声母(辅音) + 韵母(元音)。
如果声母被压得很短，字头就没有爆发感，听起来就是「糊/软」。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')

ph = json.load(io.open(NEW/'compiled'/'phones.json', encoding='utf-8'))
print('phones.json keys:', list(ph)[:8])

CONSONANT_STARTS = set('b p m f d t n l g k h j q x zh ch sh r z c s y w'.split())
NONLEX = {'SP','AP','EP',''}

rows=[]
for part in ph['parts']:
    for phrase in part['phrases']:
        for q in phrase['phones']:
            mk = q['phoneme']
            if mk in NONLEX: continue
            dur = (q['end_ms']-q['start_ms'])/1000
            rows.append(dict(mark=mk, dur=dur, start=q['start_ms']/1000))
print(f'total phones: {len(rows)}')

consonants = [r for r in rows if r['mark'] in CONSONANT_STARTS]
vowels = [r for r in rows if r['mark'] not in CONSONANT_STARTS]
cd = np.array([r['dur'] for r in consonants])
vd = np.array([r['dur'] for r in vowels])
print(f'\n辅音 {len(cd)} 个: median {np.median(cd)*1000:.0f}ms  p10 {np.percentile(cd,10)*1000:.0f}  p90 {np.percentile(cd,90)*1000:.0f}')
print(f'元音 {len(vd)} 个: median {np.median(vd)*1000:.0f}ms  p10 {np.percentile(vd,10)*1000:.0f}  p90 {np.percentile(vd,90)*1000:.0f}')
print(f'\n辅音 <20ms: {(cd<0.020).sum()} ({(cd<0.020).mean():.1%})')
print(f'辅音 <30ms: {(cd<0.030).sum()} ({(cd<0.030).mean():.1%})')
print(f'辅音 <40ms: {(cd<0.040).sum()} ({(cd<0.040).mean():.1%})')

print('\n辅音时长分布（前 20 最短）:')
for r in sorted(consonants, key=lambda x:x['dur'])[:20]:
    print(f"  {r['mark']:5s} {r['dur']*1000:6.1f}ms @{r['start']:.2f}s")

# 对照 HFA 观测的源辅音时长
h = json.load(io.open(NEW/'hfa_summary.json', encoding='utf-8'))
src_c=[]
for p in h['phrases']:
    for q in p['phones']:
        if q['mark'] in NONLEX: continue
        if q['mark'] in CONSONANT_STARTS:
            src_c.append(q['dur'])
src_c=np.array(src_c)
print(f'\n源 HFA 辅音时长: median {np.median(src_c)*1000:.0f}ms  p10 {np.percentile(src_c,10)*1000:.0f}')
print(f'  <20ms: {(src_c<0.020).sum()}   <30ms: {(src_c<0.030).sum()}')
