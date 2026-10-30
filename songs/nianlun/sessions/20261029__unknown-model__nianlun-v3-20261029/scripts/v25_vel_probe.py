"""验证「辅音占比」假说：受控实验。

假说：我们的辅音占比 26.1% < 原唱 29.7%，因为元音太长（394 vs 292ms）。
      辅音相对被淹没 → 咬字模糊。

做法：不改谱面时长（那是音乐时值），而是用 OpenUtau 的 VEL 音素级时长参数
      缩短元音、保持辅音。测咬字 bigram recall 是否改善。

先查 VEL 的可用范围与语义。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
print('=== expressions 里与时长相关的 ===')
for k,e in doc['expressions'].items():
    if any(s in k.lower() for s in ('vel','atk','dec','gen','ope','shft')):
        print(f"  {k}: type={e.get('type')} min={e.get('min')} max={e.get('max')} default={e.get('default_value')}")

print('\n=== 音符上的默认音素表达式 ===')
p0 = doc['voice_parts'][0]
for n in p0['notes'][:3]:
    print(f"  {n.get('lyric')}: phoneme_expressions={n.get('phoneme_expressions')}")
    print(f"     phoneme_overrides={n.get('phoneme_overrides')}")

print('\n=== VEL 在 OpenUtau DiffSinger 的语义（项目知识表） ===')
import csv
rows = list(csv.DictReader(io.open('docs/knowledge/acoustic-manifestations-20261009/control-details.csv',
                                   encoding='utf-8-sig', newline='')))
for r in rows:
    if (r.get('abbreviation') or '') in ('vel','atk','dec') or 'vel' in (r.get('field') or '').lower():
        print(f"  {r['id']}: {r.get('field')} | default={r.get('default_or_baseline')} | "
              f"limits={r.get('declared_or_code_limits')} | {str(r.get('limitation'))[:100]}")
