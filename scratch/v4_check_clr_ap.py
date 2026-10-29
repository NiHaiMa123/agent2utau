"""两个高价值检查：

A) CLR 音色：工程 clr 的 options=[''] max=0 → 5 种音色一个都没启用。
   需要按正确格式写入 clr（音素级 phoneme_expressions 或 clNN 曲线）。

B) AP 呼吸载频：AP 音符带具体 tone，可能让换气听起来像「唱了一个音」。
   检查 AP 的 tone 与前后唱字的关系。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

# ---------- B ----------
doc = load_ustx(NEW/'compiled'/'project.ustx')
tm = TempoMap.from_doc(doc)
print('=== AP/SP 呼吸音符检查 ===')
for pi, part in enumerate(doc['voice_parts']):
    ns = part['notes']
    for k, n in enumerate(ns):
        if n['lyric'] not in ('AP','SP'): continue
        a = tm.tick_to_ms(part['position']+n['position'])/1000
        prev = next((m for m in reversed(ns[:k]) if m['lyric'] not in ('AP','SP')), None)
        nxt  = next((m for m in ns[k+1:] if m['lyric'] not in ('AP','SP')), None)
        print(f"  p{pi} {n['lyric']} @{a:7.2f}s tone={n['tone']:3d} dur={tm.tick_to_ms(n['duration'])/1000:.2f}s"
              f"  prev={prev['tone'] if prev else None} next={nxt['tone'] if nxt else None}")

# ---------- A ----------
print('\n=== CLR 音色可用性 ===')
import yaml
cfg = Path(r'E:\software\OpenUtau-win-x64_dpV2\OpenUtau-win-x64')
ch = cfg/'Singers'/'YousaV1.65c'/'character.yaml'
if ch.is_file():
    y = yaml.safe_load(ch.read_text(encoding='utf-8'))
    print('character.yaml subbanks:')
    for sb in y.get('subbanks', []):
        print('  ', sb)
print()
# reference: how did the published 雨爱 project set the voice colour?
ref = Path(r'E:\project\agent2utau\projects\latest\yuai_skill_v17.ustx')
if ref.is_file():
    d2 = load_ustx(ref)
    tr = d2['tracks'][0]
    print('reference yuai_skill_v17:')
    print('  voice_color_names:', tr.get('voice_color_names'))
    clr = d2['expressions'].get('clr')
    print('  clr:', {k: clr.get(k) for k in ('min','max','default_value')} if clr else None,
          'options:', (clr or {}).get('options'))
    n=0; vals=set()
    for part in d2['voice_parts']:
        for note in part['notes']:
            for pe in note.get('phoneme_expressions', []):
                if pe['abbr']=='clr': n+=1; vals.add(pe['value'])
    print(f'  clr phoneme_expressions: {n}, distinct values: {sorted(vals)[:10]}')
    ncl=set(); 
    for part in d2['voice_parts']:
        for c in part.get('curves', []):
            if c['abbr'].startswith('cl'): ncl.add(c['abbr'])
    print(f'  clNN curves: {sorted(ncl)}')
