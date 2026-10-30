"""阶段5c：把 51 个 part 的函数计划映射到 58 个原生 RenderPhrase。

原因：AP/SP 在前会把一个 part 拆成多个原生短语（各自独立预测）。
做法：每个原生短语按其时间窗，取覆盖该窗的 part 计划，
      并用该短语自己的 [t0,t1] 重采样设计曲线（保持绝对音高，只是支撑区间不同）。
这是 Skill 允许的「逐句工作副本 + 必要上下文」做法，不伪造 phrase 范围。
"""
import sys, json, io, importlib.util
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'; NAT = NEW/'native'
spec = importlib.util.spec_from_file_location('df', 'skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)

plan = json.load(io.open(D/'plan.json', encoding='utf-8'))
pitch = json.load(io.open(NAT/'baseline_pitch.json', encoding='utf-8'))
phrases = plan['phrases']
print(f'part plans {len(phrases)}, native phrases {len(pitch["phrases"])}')

# map each native phrase to the part plan that contains its start time
new = []
for npi, np_ in enumerate(pitch['phrases']):
    t = np.asarray(np_['times_ms'], float)/1000
    t0, t1 = float(t[0]), float(t[-1])
    mid = 0.5*(t0+t1)
    # choose part plan whose support contains mid (or nearest)
    idx, best = None, 1e9
    for k, p in enumerate(phrases):
        a, b = p['support_s']
        if a <= mid <= b: idx = k; break
        d = min(abs(mid-a), abs(mid-b))
        if d < best: best, idx = d, k
    src = phrases[idx]
    a, b = src['support_s']
    # sample the source plan across the native phrase window
    ts = np.arange(t0, t1+1e-9, 0.004)
    if len(ts) < 2: ts = np.array([t0, t1])
    vals = np.array([df.evaluate(src, float(x)) for x in ts])
    # sparse the result back to a few nodes (max 14) but keep shape
    keep = np.unique(np.linspace(0, len(ts)-1, min(14, len(ts))).astype(int))
    nodes = [[round(float(ts[i]), 4), round(float(vals[i]), 2), 0.0] for i in keep]
    if nodes[0][0] != round(t0,4): nodes.insert(0, [round(t0,4), nodes[0][1], 0.0])
    nodes[-1][0] = round(t1,4)
    # dedupe strictly increasing
    out = []
    for n in nodes:
        if out and n[0] <= out[-1][0] + 1e-5: continue
        out.append(n)
    if out[0][0] != round(t0,4): out.insert(0, [round(t0,4), out[0][1], 0.0])
    out[-1][0] = round(t1,4)
    # decisions: single covering stage (we keep the source part's prose)
    dec = [dict(support_s=[round(t0,4), round(t1,4)],
                condition=f"native RenderPhrase {npi} (from part plan {idx})",
                choice='resampled part design over the native phrase clock',
                alternative='treat the part as a single prediction unit',
                reason='AP/SP make OpenUtau render one part as several phrases; each predicts separately',
                uncertainty='phrase split may change model context (recorded)',
                component_ids=[])]
    exp = [dict(support_s=[round(t0,4), round(t1,4)],
                range_c=[0.0, round(float(vals.max()-vals.min())+60.0, 2)],
                purpose=f'native phrase {npi}: keep the design envelope')]
    new.append(dict(schema=1, origin='agent_designed', support_s=[round(t0,4), round(t1,4)],
                    center_nodes=out, components=[], decisions=dec, expectations=exp))

bad = []
for i, pl in enumerate(new):
    try:
        r = df.compile_plan(pl, 0.004)
        if not r['shape_checks_pass']:
            bad.append((i, [(c['purpose'], c['range_c'], round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex:
        bad.append((i, str(ex)))
print(f'validation failures: {len(bad)}')
for b in bad[:8]: print('  ', b)
nodes = sum(len(p['center_nodes']) for p in new)
print(f'native-phrase plans: {len(new)}, nodes {nodes} ({nodes/349:.1f}/syllable)')

json.dump(dict(schema_version=2, scope='whole_song', note='one plan per native RenderPhrase (58)',
               phrases=new), io.open(D/'plan_native.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote design/plan_native.json')
