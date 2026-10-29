"""用 phoneme_overrides 调整辅音/元音时长比，测咬字是否改善。

目标：辅音占比 26.1% -> 接近原唱 29.7%。
做法：对每个唱字，把「元音音素」的 offset 往后推（正值），
      使元音变短、给辅音让出相对空间。
      注意：offset 单位是毫秒（白烁工程实证：-24, +7, -4, -11, +33）。
先做小剂量实验：元音 offset +20ms，渲染后测 bigram recall。
"""
import sys, json, io, os, re
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
from faster_whisper import WhisperModel

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
T = NEW/'_vel'; T.mkdir(exist_ok=True)
ONSETS = set('b p m f d t n l g k h j q x zh ch sh r z c s y w'.split())

# 从编译后的 phones.json 拿到每个音符的音素序列，找出元音索引
ph = json.load(io.open(NEW/'compiled'/'phones.json', encoding='utf-8'))
# 结构：parts -> phrases -> phones(含 phoneme, note_index?)
print('phones.json phrase keys:', list(ph['parts'][0]['phrases'][0].keys()))
ex = ph['parts'][0]['phrases'][0]['phones'][:6]
for q in ex: print('  ', q)

# 建立 (part, phrase) -> 每音符的音素列表
def vowel_indices(part):
    """返回 {note_index: [vowel phoneme indices]}"""
    out = {}
    for phrase in part['phrases']:
        cur_note = None; idx = 0
        for q in phrase['phones']:
            if 'note_index' in q and q['note_index'] != cur_note:
                cur_note = q['note_index']; idx = 0
            mk = q['phoneme'].split('/',1)[-1]
            if cur_note is not None and mk not in ONSETS and mk not in ('SP','AP','EP',''):
                out.setdefault((phrase['position'], cur_note), []).append(idx)
            idx += 1
    return out
