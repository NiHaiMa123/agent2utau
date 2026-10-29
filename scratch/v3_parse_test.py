"""验证 TextGrid 解析正确性（旧解析的问题：把 words/phones 两块的 xmin 混在一起）"""
import sys, re, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

p = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029\hfa\TextGrid\p01.TextGrid')
txt = p.read_text(encoding='utf-8')

# Correct approach: split by "item [n]:" and parse each tier separately
tiers = {}
for m in re.finditer(r'item \[\d+\]:\s*\n\s*class = "(\w+)"\s*\n\s*name = "(\w+)"(.*?)(?=\n\titem \[|\Z)',
                     txt, re.S):
    cls, name, body = m.group(1), m.group(2), m.group(3)
    ivs = re.findall(r'intervals \[\d+\]:\s*\n\s*xmin = ([-\d.eE+]+)\s*\n\s*xmax = ([-\d.eE+]+)\s*\n\s*text = "([^"]*)"', body)
    tiers[name] = [dict(start=float(a), end=float(b), mark=t) for a, b, t in ivs]

print('tiers:', list(tiers))
for name, ivs in tiers.items():
    print(f'\n{name}: {len(ivs)} intervals, total {sum(i["end"]-i["start"] for i in ivs):.3f}s')
    for i in ivs:
        print(f"  {i['mark']:8s} {i['start']:7.3f} - {i['end']:7.3f}  dur {i['end']-i['start']:.3f}")
