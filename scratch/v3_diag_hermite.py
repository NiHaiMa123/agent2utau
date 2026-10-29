import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
plan = json.load(io.open(NEW/'design'/'compile_plan.json', encoding='utf-8'))
ph = plan['phrases'][0]['design']
print('support', ph['support_s'])
print('nodes:')
for n in ph['center_nodes']:
    print(f'  t={n[0]:9.4f}  c={n[1]:9.2f}  slope={n[2]:9.2f}')
print('\ncomponents:', ph['components'])
import importlib.util
spec = importlib.util.spec_from_file_location('df','skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)
for t in np.linspace(ph['support_s'][0], ph['support_s'][1], 12):
    print(f'  t={t:8.3f} eval={df.evaluate(ph, float(t)):10.2f}')
