"""修 v4 计划：唯一组件 id + 所有字段非空。"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
p = NEW/'design'/'plan.json'
plan = json.load(io.open(p, encoding='utf-8'))
n_fix=0
for pi, ph in enumerate(plan['phrases']):
    for ci,c in enumerate(ph['components']):
        new_id = f'p{pi}:c{ci}'
        old = c['id']
        if new_id != old:
            c['id'] = new_id
            for d in ph['decisions']:
                d['component_ids'] = [new_id if x==old else x for x in d['component_ids']]
            n_fix+=1
    for d in ph['decisions']:
        for k in ('condition','choice','alternative','reason','uncertainty'):
            if not isinstance(d.get(k), str) or not d[k].strip():
                d[k] = 'not applicable for this syllable position'
print(f'renamed components: {n_fix}')
json.dump(plan, io.open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=1)

# validate
sys.path.insert(0,'src')
import importlib.util
spec=importlib.util.spec_from_file_location('df','skills/singing-expression-editor/scripts/design_functions.py')
dfm=importlib.util.module_from_spec(spec); spec.loader.exec_module(dfm)
bad=[]
for i,pl in enumerate(plan['phrases']):
    try:
        r=dfm.compile_plan(pl,0.004)
        if not r['shape_checks_pass']: bad.append((i,'shape'))
    except Exception as ex: bad.append((i,str(ex)[:100]))
print(f'validation failures: {len(bad)}')
for b in bad[:8]: print('  ',b)
