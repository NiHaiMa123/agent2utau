"""检查声线配置：当前工程用了什么音色？DiffSinger 的音色由 CLR/speaker 决定。

前两版一直用默认音色（Normal），这可能是「不像泠鸢」的最大原因。
"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
for name in ['score/v3_score.ustx', 'compiled/project.ustx']:
    p = NEW/name
    if not p.exists(): continue
    d = load_ustx(p)
    tr = d['tracks'][0]
    print(f'=== {name} ===')
    print('  singer:', tr.get('singer'))
    print('  phonemizer:', tr.get('phonemizer'))
    print('  voice_color_names:', tr.get('voice_color_names'))
    print('  renderer_settings:', tr.get('renderer_settings'))
    print('  track_expressions:', tr.get('track_expressions'))
    clr = d['expressions'].get('clr')
    print('  clr expr:', {k: clr.get(k) for k in ('min','max','default_value','options')} if clr else None)
    # per-note clr?
    nclr = 0; npart_clr = 0; ncl_keys = set()
    for part in d['voice_parts']:
        for c in part.get('curves', []):
            if c['abbr'].startswith('cl'): npart_clr += 1; ncl_keys.add(c['abbr'])
        for n in part['notes']:
            for pe in n.get('phoneme_expressions', []):
                if pe['abbr'] == 'clr': nclr += 1
    print(f'  clr phoneme_expressions: {nclr}, clNN curves: {npart_clr} {sorted(ncl_keys)}')
    print()

# 声库支持的音色
import yaml
cfg = Path(r'E:\software\OpenUtau-win-x64_dpV2\OpenUtau-win-x64')
ds = cfg/'Singers'/'YousaV1.65c'/'dsconfig.yaml'
if ds.is_file():
    y = yaml.safe_load(ds.read_text(encoding='utf-8'))
    print('dsconfig speakers:', y.get('speakers'))
    print('dsconfig keys:', [k for k in y if 'speaker' in k.lower() or 'color' in k.lower()])
