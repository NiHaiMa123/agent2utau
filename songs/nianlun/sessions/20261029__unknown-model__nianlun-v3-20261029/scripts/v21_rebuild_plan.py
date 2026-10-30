"""完整重建 v21 工程：编译 v21_score → assemble → finalize → final。"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap, sha256

VER = 'v21'
NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
D = NEW/'design'

# 复用 v22 的 compile_plan 结构，替换为 v21_score 的设计
kcp = json.load(io.open(D/'compile_plan_v22.json', encoding='utf-8'))
SC = NEW/'score'/f'{VER}_score.ustx'
kcp['project'] = str(SC.resolve())
kcp['input_hashes'] = {str(SC.resolve()): sha256(SC),
    str((NEW/'inputs'/'stems'/'vocals.wav').resolve()): sha256(NEW/'inputs'/'stems'/'vocals.wav')}
(D/f'compile_plan_{VER}.json').write_text(json.dumps(kcp, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'compile plan for {VER} written')
