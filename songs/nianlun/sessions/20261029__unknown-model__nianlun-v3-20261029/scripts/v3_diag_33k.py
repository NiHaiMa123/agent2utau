"""定位 33984c 的来源：检查 p00 的第一个字在设计里的基线值。"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
p0 = W['phrases'][0]
print('p00', p0['hanzi'], p0['time'])
for w in p0['words']:
    print(f"  {w['hanzi']} {w['start']}-{w['end']} pitch={w['pitch_cents']} cov={w['voiced_cover']}")
plan = json.load(io.open(NEW/'design'/'plan_native.json', encoding='utf-8'))
print('\nplan_native phrase0 nodes (first 3):', plan['phrases'][0]['center_nodes'][:3])
# check part plan
pp = json.load(io.open(NEW/'design'/'plan.json', encoding='utf-8'))
print('part plan0 nodes (first 4):', pp['phrases'][0]['center_nodes'][:4])
print('part plan0 support:', pp['phrases'][0]['support_s'])
