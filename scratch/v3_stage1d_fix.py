"""修正 E3a 的分段（p44 应只覆盖 seg13 的开头）并重出 HFA 输入。

seg 结构复核：
  seg13 206.77-232.57  副歌3 主段（一圈圈年轮 ... 这剧本）
  seg14 233.01-233.29  极短（0.28s，无 GAME 音符）—— 忽略/并入 SP
  seg15 233.43-237.79  尾句前半
  seg16 238.85-242.67  尾句后半
"""
import sys, json, io, hashlib
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
from pypinyin import lazy_pinyin

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
lyr = json.load(io.open(NEW/'lyrics.json', encoding='utf-8'))
rows = lyr['phrases']

# p44: 只覆盖 seg13 的开头（一圈圈年轮 我认真）
# 用 GAME 音符分布：seg13 有 62 个 voiced 音符，8 个字 → 前 8 个音符区间
g = json.load(io.open(NEW/'inputs/game.json', encoding='utf-8'))
n13 = [n for n in g['notes'] if 206.77 <= n['start'] < 232.57]
print(f'seg13 GAME notes: {len(n13)}')
# 按字符比例（8/51）找切点，吸附到音符起点
tot = 8+6+9+10+6+11
target = 206.77 + (232.57-206.77)*8/tot
onsets = [n['start'] for n in n13]
cut = min(onsets, key=lambda x: abs(x-target))
print(f'  p44 target {target:.2f}s -> snap {cut:.2f}s')
p44 = next(r for r in rows if r['pid']=='p44')
p44['t1'] = round(cut, 3)
p45 = next(r for r in rows if r['pid']=='p45')
p45['t0'] = round(cut, 3)

# 修正 p25/p29 之间的缺口说明（128.83-131.75 是间奏/呼吸，正常）
rows = sorted(rows, key=lambda r: r['t0'])
print('\nmonotonic check:')
bad = 0
for a, b in zip(rows, rows[1:]):
    if a['t1'] > b['t0'] + 0.01:
        print(f"  OVERLAP {a['pid']} {a['t1']} -> {b['pid']} {b['t0']}"); bad += 1
print(f'  overlaps: {bad}')

# regenerate HFA inputs
hfa_dir = NEW/'hfa_inputs'
manifest = {'phrases': []}
for r in rows:
    s0 = max(0.0, r['t0']-0.15); s1 = min(len(v)/sr, r['t1']+0.15)
    data = v[int(s0*sr):int(s1*sr)]
    wav = hfa_dir/f"{r['pid']}.wav"
    sf.write(str(wav), data, sr)
    lab = hfa_dir/f"{r['pid']}.lab"
    lab.write_text(r['pinyin'], encoding='utf-8')
    r['slice'] = [round(s0,3), round(s1,3)]
    r['wav_sha256'] = hashlib.sha256(wav.read_bytes()).hexdigest()
    r['lab_sha256'] = hashlib.sha256(lab.read_bytes()).hexdigest()
    manifest['phrases'].append(r)
(hfa_dir/'slices_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(NEW/'lyrics.json').write_text(json.dumps(dict(schema_version=1, phrases=rows,
    source='百度百科权威歌词 + GAME音符事件 + 真实有声段能量检测', n=len(rows),
    corrections='ASR 9处错字已按权威歌词修正'), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nwrote {len(rows)} phrases, p44 206.77-{cut:.2f}, p45 {cut:.2f}-210.59')
