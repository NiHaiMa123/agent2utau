"""阶段5d：knowledge_context + freeze intent lock + 完整 compile plan。"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.knowledge import collect_context
from agent2utau.openutau.ustx import sha256

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'; NAT = NEW/'native'; SCORE = NEW/'score'/'v3_score.ustx'
OBS = NEW/'inputs/stems/vocals.wav'   # 绑定的源（分离人声）

# ---------- knowledge context ----------
# 从表1/表2 检索与本次任务相关：虚实/强弱/音高入口/长音/气口 + 已知阴性
ENT = ['PER:S1', 'PER:S2'] if False else None
# 先用最小可用的显式检索：查 knowledge-table.json 有哪些 entity id
kt = json.load(io.open('docs/knowledge/acoustic-manifestations-20261009/knowledge-table.json', encoding='utf-8'))
ents = [e['id'] for e in kt['entities']]
print(f'table1 entities: {len(ents)}, sample: {ents[:8]}')

cfgk = json.load(io.open('docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json', encoding='utf-8'))
print('registry keys:', list(cfgk))
print('response_indices:', cfgk['response_indices'])
print(f'response_packets: {len(cfgk["response_packets"])}')
