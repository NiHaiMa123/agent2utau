"""用正确的指标判断配方化：直接看「逐字参数」的取值分布。

之前的「峰位置」指标无效：因为字头/字尾必须归零（保证边界连续），
最大偏离自然落在端点附近 —— 这是结构约束，不是配方化。

正确指标（对照 v1 的失败特征「349 组件中 |peak|=52c 占 296 个」）：
  1) 每个单元的字头深度、字尾深度、字腹幅度、字腹峰位
  2) 这些参数的取值是否高度集中（少数几个常数）
  3) 参数是否与该单元的音乐条件相关（音程、时长、音区）
可从 v22_pitd.py 的重算获得。这里直接从最终曲线反解这些参数。
"""
import sys, json, io
import numpy as np
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
c = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
o=np.argsort(t); t,c=t[o],c[o]

parts_notes={}
for pi,part in enumerate(doc['voice_parts']):
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,tone=n['tone'],dur=b-a,lyric=n['lyric']))
    ns.sort(key=lambda x:x['a']); parts_notes[pi]=ns

rows=[]
for pi, ns in parts_notes.items():
    for i,n in enumerate(ns):
        d=n['dur']
        if d<0.10: continue
        T=np.arange(n['a'], n['b'], 0.005)
        if len(T)<10: continue
        C=np.interp(T,t,c)
        tone=n['tone']*100.0
        # 字头 = 前 18% 内的最大偏离（相对 tone 与中位）
        head = C[:max(2,int(0.18*len(C)))]
        tail = C[-max(2,int(0.18*len(C))):]
        body = C[int(0.30*len(C)):int(0.70*len(C))]
        if len(body)<3: continue
        med=float(np.median(C))
        rows.append(dict(
            pi=pi, lyric=n['lyric'], dur=round(d,2), tone=n['tone'],
            head_dev=round(float(head[np.argmax(np.abs(head-med))]-med),0),
            tail_dev=round(float(tail[np.argmax(np.abs(tail-med))]-med),0),
            body_span=round(float(body.max()-body.min()),0),
            body_sign=1 if (body.max()-body.mean()) > (body.mean()-body.min()) else -1,
        ))

print(f'notes analyzed: {len(rows)}')
for key in ('head_dev','tail_dev','body_span'):
    v=np.array([r[key] for r in rows])
    cnt=Counter(v.astype(int))
    top=cnt.most_common(1)[0]
    print(f'\n{key}:')
    print(f'  不同取值 {len(cnt)} 个  median {np.median(v):+.0f}  std {v.std():.0f}')
    print(f'  最常见取值 {top[0]} 出现 {top[1]} 次 ({top[1]/len(v):.1%})')
    print(f'  top5: {cnt.most_common(5)}')
    print(f'  |{key}|>0 的比例: {(np.abs(v)>1).mean():.1%}')

# body_sign 分布
bs=Counter(r['body_sign'] for r in rows)
print(f'\n字腹极性: 正 {bs.get(1,0)}, 负 {bs.get(-1,0)}  (平衡说明不是单一方向)')

# 参数与音乐条件的相关性
durs=np.array([r['dur'] for r in rows])
spans=np.array([r['body_span'] for r in rows])
tones=np.array([r['tone'] for r in rows])
print(f'\n字腹幅度 vs 音符时长 相关: {np.corrcoef(durs,spans)[0,1]:.3f}')
print(f'字腹幅度 vs 音区(tone) 相关: {np.corrcoef(tones,spans)[0,1]:.3f}')

out=dict(schema_version=1, notes=len(rows),
  head_dev=dict(distinct=len(set(np.round([r['head_dev'] for r in rows]).astype(int))),
                std=float(np.std([r['head_dev'] for r in rows]))),
  tail_dev=dict(distinct=len(set(np.round([r['tail_dev'] for r in rows]).astype(int))),
                std=float(np.std([r['tail_dev'] for r in rows]))),
  body_span=dict(distinct=len(set(np.round([r['body_span'] for r in rows]).astype(int))),
                 std=float(np.std([r['body_span'] for r in rows]))),
  body_polarity=dict(pos=bs.get(1,0), neg=bs.get(-1,0)),
  corr_bodyspan_dur=float(np.corrcoef(durs,spans)[0,1]),
  corr_bodyspan_tone=float(np.corrcoef(tones,spans)[0,1]),
  reference_v1='349 components: |peak|=52c in 296 of them (85%)')
(NEW/'evaluation'/'no_fixed_recipe_check.json').write_text(
  json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print('\nwrote evaluation/no_fixed_recipe_check.json')
