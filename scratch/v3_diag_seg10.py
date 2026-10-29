import sys, re, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
p = NEW/'hfa_blocks_out'/'TextGrid'/'seg10.TextGrid'
txt = p.read_text(encoding='utf-8')
print('xmax =', re.search(r'xmax = ([\d.]+)', txt).group(1))
m = re.search(r'name = "words"(.*?)(?=\n\titem \[|\Z)', txt, re.S)
ivs = re.findall(r'xmin = ([-\d.eE+]+)\s*\n\s*xmax = ([-\d.eE+]+)\s*\n\s*text = "([^"]*)"', m.group(1))
print(f'words: {len(ivs)}, first 20:')
off = 131.45
for a, b, t in ivs[:20]:
    print(f'  {t:8s} rel {float(a):7.3f}-{float(b):7.3f}  abs {float(a)+off:8.3f}-{float(b)+off:8.3f}  dur {float(b)-float(a):.3f}')

man = json.load(io.open(NEW/'hfa_blocks'/'manifest.json', encoding='utf-8'))
b = next(x for x in man['blocks'] if x['name']=='seg10')
print('\nblock info:', b['slice'], b['voiced'], b['n_chars'])
# GAME notes near start
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
print('\nGAME notes 131.0-134.0:')
for n in g['notes']:
    if 131.0 <= n['start'] < 134.0:
        print(f"  {n['start']:.3f} dur={n['dur']:.3f} tone={n['tone']:.2f} voiced={n['voiced']}")
