"""阶段5b：build_inventory + knowledge_context + freeze intent lock。

注意 compile-functions 要求 plan 覆盖「输入工程的全部原生 RenderPhrase」，
而我们的 51 个 part 产生 58 个原生短语（AP/SP 把部分 part 拆开）。
所以计划必须按原生短语数（58）给，而不是 part 数（51）。
"""
import sys, json, io, copy
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.evaluation.execution_review import build_inventory
from agent2utau.openutau.ustx import load_ustx, sha256, TempoMap
from agent2utau.knowledge import collect_context

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'; NAT = NEW/'native'
SCORE = NEW/'score'/'v3_score.ustx'

inv = NEW/'design'/'review-inventory.json'
res = build_inventory(SCORE, inv, NAT/'baseline_pitch.json', NAT/'baseline_phones.json',
                      NAT/'baseline_provenance.json')
print(f'inventory: {inv}')
iv = json.load(io.open(inv, encoding='utf-8'))
print('inventory keys:', list(iv)[:12])
units = iv.get('units') or iv.get('inventory') or []
print(f'inventory units: {len(units)}')

pitch = json.load(io.open(NAT/'baseline_pitch.json', encoding='utf-8'))
print(f'\nnative pitch phrases: {len(pitch["phrases"])}')
for i, p in enumerate(pitch['phrases'][:6]):
    print(f"  ph{i}: part_position={p['part_position']} position={p['position']} "
          f"t={p['times_ms'][0]/1000:.2f}-{p['times_ms'][-1]/1000:.2f}")
