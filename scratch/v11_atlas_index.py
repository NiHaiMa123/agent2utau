"""逐元音图审：把 349 个元音按通道/音区/时长分组，抽样检查并对每个单元记录实际观察。

做法：
  - 从 compiler 生成的 atlas 里取每个单元的图
  - 实际打开并读取（read_image），记录具体观察
  - 共 349 个，全部覆盖成本很高；按 Skill 允许「短字可邻接、长字连续重叠页」
    这里采用：全部 349 个按批分页（每页 6 个），逐页实际打开审阅
先产出「分页清单 + 每单元元数据」，用于逐页审阅。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
ATLAS = NEW/'compiled'/'execution-review'/'atlas'
doc = load_ustx(NEW/'compiled'/'project.ustx')
tm = TempoMap.from_doc(doc)

# inventory of units (349 vowels per compiler)
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))
units = inv.get('units', [])
print(f'inventory units: {len(units)}')
if units:
    print('unit keys:', list(units[0].keys())[:14])
    print('sample:', json.dumps({k: units[0][k] for k in list(units[0])[:10]}, ensure_ascii=False))

# atlas files
pngs = sorted(ATLAS.glob('*.png'))
print(f'\natlas pngs: {len(pngs)}')
print('first 4:', [p.name for p in pngs[:4]])
