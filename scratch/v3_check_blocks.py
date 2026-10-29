"""检查整段 HFA 对齐质量：字长分布、元音核、与能量的一致性。"""
import sys, json, io, re
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
man = json.load(io.open(NEW/'hfa_blocks'/'manifest.json', encoding='utf-8'))

def parse_tg(path):
    txt = path.read_text(encoding='utf-8')
    tiers = {}
    for m in re.finditer(r'item \[\d+\]:\s*\n\s*class = "(\w+)"\s*\n\s*name = "(\w+)"(.*?)(?=\n\titem \[|\Z)',
                         txt, re.S):
        name, body = m.group(2), m.group(3)
        ivs = re.findall(r'intervals \[\d+\]:\s*\n\s*xmin = ([-\d.eE+]+)\s*\n\s*xmax = ([-\d.eE+]+)\s*\n\s*text = "([^"]*)"', body)
        tiers[name] = [dict(start=float(a), end=float(b), mark=t) for a, b, t in ivs]
    return tiers

allw = []
for b in man['blocks']:
    p = NEW/'hfa_blocks_out'/'TextGrid'/f"{b['name']}.TextGrid"
    if not p.is_file():
        p = NEW/'hfa_blocks'/'TextGrid'/f"{b['name']}.TextGrid"
    print(f"{b['name']}: {p.is_file()} {p}")
    if not p.is_file(): continue
    tg = parse_tg(p)
    off = b['slice'][0]
    lex = [w for w in tg.get('words', []) if w['mark'] not in ('SP', 'AP', 'EP', '')]
    print(f"   words={len(lex)} expected={b['n_chars']}")
    for k, w in enumerate(lex):
        allw.append(dict(block=b['name'], idx=k, mark=w['mark'],
                         start=w['start']+off, end=w['end']+off, dur=w['end']-w['start']))

d = np.array([w['dur'] for w in allw])
print(f'\ntotal words {len(allw)}')
print(f'dur: min {d.min():.3f} p5 {np.percentile(d,5):.3f} median {np.median(d):.3f} max {d.max():.3f}')
print(f'< 0.05s: {(d<0.05).sum()}   < 0.08s: {(d<0.08).sum()}   < 0.10s: {(d<0.10).sum()}')
print('\nshortest 15:')
for w in sorted(allw, key=lambda x: x['dur'])[:15]:
    print(f"   {w['block']} {w['mark']:8s} {w['dur']:.3f}s @{w['start']:.2f}")
