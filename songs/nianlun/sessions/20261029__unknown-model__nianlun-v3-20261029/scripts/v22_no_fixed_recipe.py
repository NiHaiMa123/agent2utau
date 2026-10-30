"""验证「不得用固定配方」——这是目标的明确要求，也是 v1 被否决的原因。

v1 的问题（审查报告）：
  349 个组件 |peak|=52c 占 296 个；347 个 finite_return 落在 6 个时间归一化签名；
  决策 checks 100% 是 range 自证型。
本版必须证明：决策是逐单元、条件驱动的，不是少数几个常数的重复。

指标：
  1) 每个单元的动作参数是否有足够离散度（不是几个固定值）
  2) 决策的 condition 是否逐单元不同（不是同一句话复制）
  3) 是否存在「时间归一化签名」高度重复
  4) 判据类型是否有多样性
"""
import sys, json, io, hashlib
import numpy as np
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

# ---- 1) 逐单元的曲线形态离散度 ----
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))

t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
c = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
o=np.argsort(t); t,c=t[o],c[o]

# 每个单元：归一化到 0..1，取 12 个采样点作为「形态签名」
sigs=[]
params=[]
for u in inv['units']:
    s0,s1=u['support_s']
    if s1-s0 < 0.08: continue
    U=np.linspace(0,1,12)
    T=s0+(s1-s0)*U
    C=np.interp(T,t,c)
    C=C-C.mean()
    sigs.append(C.tolist())
    # 参数：跨度、峰位、首尾相对
    span=float(C.max()-C.min())
    pk=float(U[int(np.argmax(np.abs(C)))])
    params.append(dict(span=round(span,0), peakpos=round(pk,2)))

sigs=np.array(sigs)
print(f'单元形态签名: {len(sigs)} 个')

# 时间归一化签名的重复度（v1 的问题是 347 个落在 6 个签名）
def quantize(v, step):
    return tuple(np.round(v/step).astype(int).tolist())
for step in (10, 20, 30):
    keys=[quantize(s, step) for s in sigs]
    cnt=Counter(keys)
    top=cnt.most_common(1)[0]
    n_distinct=len(cnt)
    print(f'  量化步长 {step}c: 不同签名 {n_distinct} 个, 最常见签名出现 {top[1]} 次 '
          f'({top[1]/len(sigs):.1%})')

# v1 的对照：6 个签名覆盖 347 个
print(f'\n  参考：v1 的 347 个 finite_return 只落在 6 个签名（最常见约 82 次 = 23.6%）')

# ---- 2) 参数的离散度 ----
sp=np.array([p['span'] for p in params])
pk=np.array([p['peakpos'] for p in params])
print(f'\n单元跨度: 不同取值 {len(set(np.round(sp).astype(int)))} 个, '
      f'median {np.median(sp):.0f}c, 最常见值出现 {Counter(np.round(sp).astype(int)).most_common(1)[0][1]} 次')
print(f'  峰位置: 不同取值 {len(set(np.round(pk,2)))} 个, 最常见出现 {Counter(np.round(pk,2)).most_common(1)[0][1]} 次')
print(f'  跨度取值分布（top5）: {Counter(np.round(sp).astype(int)).most_common(5)}')

# ---- 3) 决策 condition 的多样性 ----
plan = json.load(io.open(NEW/'design'/'plan.json', encoding='utf-8'))
conds=[]; kinds=Counter(); choices=[]
for ph in plan['phrases']:
    for d in ph['decisions']:
        conds.append(d['condition'])
        choices.append(d['choice'])
print(f'\n决策总数 {len(conds)}')
print(f'  不同 condition 文本: {len(set(conds))} 个 ({len(set(conds))/max(len(conds),1):.1%})')
print(f'  不同 choice 文本: {len(set(choices))} 个')
top_cond = Counter(conds).most_common(3)
print(f'  最常见 condition（top3）:')
for k,v in top_cond:
    print(f'    {v:4d}x  {k[:70]}')

# ---- 4) 判据类型多样性（来自 intent）----
intent = json.load(io.open(NEW/'design'/'musical_intent.json', encoding='utf-8'))
for p in intent['phrases']:
    for g in p['gestures']:
        for ck in g['checks']:
            kinds[ck['kind']] += 1
print(f'\n判据类型分布: {dict(kinds)}')
print(f'  （v1 为 100% range 自证型）')

verdict = dict(
  units=len(sigs),
  signature_diversity={f'step{s}': len(set(quantize(x,s) for x in sigs)) for s in (10,20,30)},
  span_distinct=len(set(np.round(sp).astype(int))),
  condition_distinct=len(set(conds)),
  condition_total=len(conds),
  check_kinds=dict(kinds),
)
print('\nsummary:', json.dumps(verdict, ensure_ascii=False))
(NEW/'evaluation'/'no_fixed_recipe_check.json').write_text(
  json.dumps(verdict, ensure_ascii=False, indent=2), encoding='utf-8')
print('wrote evaluation/no_fixed_recipe_check.json')
