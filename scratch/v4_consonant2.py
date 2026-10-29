import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
ph = json.load(io.open(NEW/'compiled'/'phones.json', encoding='utf-8'))

ONSETS = set('b p m f d t n l g k h j q x zh ch sh r z c s y w'.split())
rows=[]
for part in ph['parts']:
    for phrase in part['phrases']:
        for q in phrase['phones']:
            mk=q['phoneme']
            if '/' in mk: mk=mk.split('/',1)[1]
            if mk in ('SP','AP','EP',''): continue
            rows.append(dict(mark=mk, dur=(q['end_ms']-q['start_ms'])/1000, start=q['start_ms']/1000))

con=[r for r in rows if r['mark'] in ONSETS]
vow=[r for r in rows if r['mark'] not in ONSETS]
cd=np.array([r['dur'] for r in con]); vd=np.array([r['dur'] for r in vow])
print(f'辅音 {len(cd)}: median {np.median(cd)*1000:.0f}ms p10 {np.percentile(cd,10)*1000:.0f} p90 {np.percentile(cd,90)*1000:.0f}')
print(f'元音 {len(vd)}: median {np.median(vd)*1000:.0f}ms p10 {np.percentile(vd,10)*1000:.0f} p90 {np.percentile(vd,90)*1000:.0f}')
for thr in (0.015,0.020,0.030,0.040,0.060):
    print(f'  辅音 <{thr*1000:.0f}ms: {(cd<thr).sum()} ({(cd<thr).mean():.1%})')
print(f'\n最短 20 个辅音:')
for r in sorted(con,key=lambda x:x['dur'])[:20]:
    print(f"  {r['mark']:5s} {r['dur']*1000:6.1f}ms @{r['start']:.2f}s")

# 每个字的首个辅音（字头爆发感来源）
print(f'\n=== 每字声母时长 ===')
W=json.load(io.open(NEW/'words_v3.json',encoding='utf-8'))
byword=[]
for part_i,part in enumerate(ph['parts']):
    for phrase in part['phrases']:
        for q in phrase['phones']:
            mk=q['phoneme'].split('/',1)[-1]
            byword.append((q['start_ms']/1000,(q['end_ms']-q['start_ms'])/1000,mk))
byword.sort()
first_con=[]
for phz in W['phrases']:
    for w in phz['words']:
        a=w['start']
        # phones starting within 25ms of the word onset
        cand=[x for x in byword if a-0.025 <= x[0] <= a+0.05 and x[2] in ONSETS]
        if cand: first_con.append(cand[0])
fc=np.array([x[1] for x in first_con])
print(f'  声母 {len(fc)} 个: median {np.median(fc)*1000:.0f}ms  p10 {np.percentile(fc,10)*1000:.0f}  p25 {np.percentile(fc,25)*1000:.0f}')
print(f'  <20ms: {(fc<0.020).sum()}  <30ms: {(fc<0.030).sum()}  <40ms: {(fc<0.040).sum()}')
