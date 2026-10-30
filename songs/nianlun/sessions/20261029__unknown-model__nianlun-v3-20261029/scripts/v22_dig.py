"""深入检查「峰位置 205/348 同一值」和「choice 仅 12 种」是否真的是配方化。

峰位置是我的分析窗（去两端25%）造成的假象还是真实设计？
choice 只有 12 种是因为 plan.json 是 v4b（条件分类式）生成的，
而真正的曲线来自 v20_pitd.py（逐字参数化）。需要区分：
  - plan.json（意图记录）是否仍在用条件分类
  - 实际曲线（v20_pitd）是否逐字参数化
"""
import sys, json, io
import numpy as np
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

# 峰位置：用完整单元（不删两端）重算
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))
t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
c = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
o=np.argsort(t); t,c=t[o],c[o]

pk_full=[]; pk_centered=[]
for u in inv['units']:
    s0,s1=u['support_s']
    if s1-s0<0.08: continue
    U=np.linspace(0,1,20)
    C=np.interp(s0+(s1-s0)*U,t,c)
    pk_full.append(float(U[int(np.argmax(C))]))            # 绝对最高点
    Cc=C-C.mean()
    pk_centered.append(float(U[int(np.argmax(np.abs(Cc)))]))  # 最大偏离

for name, arr in [('绝对最高点位置', pk_full), ('最大偏离位置', pk_centered)]:
    a=np.array(arr)
    cnt=Counter(np.round(a,2))
    print(f'{name}: 不同取值 {len(cnt)} 个, 最常见 {cnt.most_common(1)[0][0]} 出现 {cnt.most_common(1)[0][1]} 次 ({cnt.most_common(1)[0][1]/len(a):.1%})')
    print(f'  top5: {cnt.most_common(5)}')

# 检查 plan.json 是哪个版本，与曲线是否一致
plan = json.load(io.open(NEW/'design'/'plan.json', encoding='utf-8'))
print(f"\nplan.json note: {plan.get('note','')[:100]}")
print(f"plan phrases {len(plan['phrases'])}, 每句 decisions 数: "
      f"{[len(p['decisions']) for p in plan['phrases'][:6]]}")
print(f"plan 是否有 center_nodes 参数化: {len(plan['phrases'][0]['center_nodes'])} 节点")

# 实际曲线的节点来源是 v20_pitd.py（逐字参数化），plan.json 只是意图记录
print("\n结论判断：")
print("  plan.json 的 condition 文本来自 v4b 的条件分类（83 种），")
print("  但实际曲线 v20_pitd.py 是逐字参数化（字头深度按音程、字尾按音程、字腹按源运动类型+时长）。")
print("  → 需要核实 v20_pitd 的参数是否真的逐字不同")
