"""核实音色差距的实测影响：对比参考工程与 v3 工程的实际 speaker embedding 路径。

只在只读层面确认：
  1) 参考工程的 clr/clNN 具体取值
  2) v3 工程缺失这些设置
  3) 声库支持的音色与 clNN 通道
"""
import sys, json, io
from collections import Counter
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx

REF = Path(r'E:\project\agent2utau\projects\latest\yuai_skill_v17.ustx')
NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

def summarize(p, label):
    d = load_ustx(p)
    tr = d['tracks'][0]
    clr = d['expressions'].get('clr', {})
    print(f'\n=== {label} ===')
    print(f'  clr options: {clr.get("options")}  min/max/default: {clr.get("min")}/{clr.get("max")}/{clr.get("default_value")}')
    # clr per-phoneme
    vals = Counter()
    for part in d['voice_parts']:
        for n in part['notes']:
            for pe in n.get('phoneme_expressions', []):
                if pe.get('abbr') == 'clr':
                    vals[pe.get('value')] += 1
    print(f'  clr phoneme expressions: {sum(vals.values())}, values: {dict(vals)}')
    # clNN curves
    cc = Counter()
    for part in d['voice_parts']:
        for c in part.get('curves', []):
            if c['abbr'].startswith('cl'):
                cc[c['abbr']] += 1
    print(f'  clNN curves: {dict(cc)}')
    # ranges of clNN
    for part in d['voice_parts'][:1]:
        for c in part.get('curves', []):
            if c['abbr'].startswith('cl'):
                print(f"    {c['abbr']}: x[{c['xs'][0]}..{c['xs'][-1]}] n={len(c['xs'])} "
                      f"y range {min(c['ys'])}..{max(c['ys'])}")
    # other curves
    oc = Counter()
    for part in d['voice_parts']:
        for c in part.get('curves', []):
            oc[c['abbr']] += 1
    print(f'  all curves: {dict(oc)}')

summarize(REF, 'reference yuai_skill_v17')
summarize(NEW/'compiled'/'project.ustx', 'nainlun v4b')
