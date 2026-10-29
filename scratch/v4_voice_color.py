"""阶段：音色层（CLR + clNN）—— 这是「像不像泠鸢」的关键层。

事实（已核实）：
  YousaV1.65c 有 5 个音色嵌入：Bright / Cute / Normal / Whisper / Classic
  dsconfig.speakers 顺序 = clNN 通道语义：
      cl01=Bright  cl02=Cute  cl03=Normal  cl04=Whisper  cl05=Classic
  参考工程 yuai_skill_v17 用 cl01=50, cl03=10, cl05=40（50 Bright + 10 Normal + 40 Classic）
  而 v3/v4 工程的 clr options=[''] 、0 个音素表达式 → 一直在用未配置的默认音色

本阶段：
  1) 把 clr 的 options 设为 5 个音色名，max=4（与参考工程一致的声明格式）
  2) 为每个音素写 clr = 0（Bright 作为基底，与参考工程同格式）
  3) 写 clNN 混合曲线：cl01 / cl03 / cl05
     —— 目标不是复制雨爱配方，而是按《年轮》的条件重新设计：
        原唱张碧晨是偏厚实的中低女声，需要比雨爱更多的 Normal/Classic、更少 Bright
  4) 曲线以整曲 2 点常量形式写入每个 part（与参考工程一致的写法）
"""
import sys, json, io
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
SRC = NEW/'compiled'/'project.ustx'

COLORS = ['Yousa_Bright', 'Yousa_Classic', 'Yousa_Cute', 'Yousa_Normal', 'Yousa_Whisper']
# 注意：参考工程的 clr.options 顺序 = voice_color_names 的顺序
# voice_color_names 在工程里是 ['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']
# 而 clr.value=0 指向 voice_color_names[0] = Bright

doc = load_ustx(SRC)

# ---- 1) clr 声明 ----
clr = doc['expressions'].setdefault('clr', {})
clr['name'] = clr.get('name', 'voice color')
clr['abbr'] = 'clr'
clr['type'] = 'Options'
clr['min'] = 0
clr['max'] = len(COLORS)-1
clr['default_value'] = 0
clr['options'] = COLORS[:]
print('clr declared:', {k: clr.get(k) for k in ('min','max','default_value')}, 'options:', clr['options'])

# voice_color_names 必须与 options 一致
tr = doc['tracks'][0]
tr['voice_color_names'] = COLORS[:]
print('track voice_color_names:', tr['voice_color_names'])

# ---- 2) 每音素 clr（Bright 基底）----
n_clr = 0
for part in doc['voice_parts']:
    for note in part['notes']:
        pe = note.get('phoneme_expressions') or []
        pe = [x for x in pe if x.get('abbr') != 'clr']
        # 写 8 个索引，覆盖一个字最多 8 个音素
        for j in range(8):
            pe.append(dict(index=j, abbr='clr', value=0))
        note['phoneme_expressions'] = pe
        n_clr += 1
print(f'notes given clr: {n_clr}')

# ---- 3) clNN 音色混合（按《年轮》条件设计）----
# 设计依据：原唱张碧晨为中低女声、厚实、少气声；Bright 偏亮偏薄，Classic 偏厚
# 与雨爱(50/10/40)相比：降低 Bright、提高 Normal 与 Classic、少量 Cute 保留亲和度
MIX = dict(cl01=26.0, cl02=6.0, cl03=34.0, cl04=0.0, cl05=34.0)
print(f'\nvoice mix: cl01(Bright)={MIX["cl01"]}, cl02(Cute)={MIX["cl02"]}, '
      f'cl03(Normal)={MIX["cl03"]}, cl04(Whisper)={MIX["cl04"]}, cl05(Classic)={MIX["cl05"]}')

n_mix = 0
for part in doc['voice_parts']:
    part['curves'] = [c for c in part.get('curves', []) if not c['abbr'].startswith('cl')]
    dur = int(part['duration'])
    for abbr, val in MIX.items():
        if val <= 0: continue
        part['curves'].append(dict(abbr=abbr, xs=[0, dur], ys=[int(round(val)), int(round(val))]))
        n_mix += 1
print(f'clNN curves written: {n_mix}')

# 确保 clNN 在 expressions 里声明为 Curve 且范围 0..100
for abbr in ('cl01','cl02','cl03','cl04','cl05'):
    e = doc['expressions'].get(abbr)
    if e is None:
        doc['expressions'][abbr] = dict(name=f'{abbr} mix', abbr=abbr, type='Curve',
                                        min=0, max=100, default_value=0)
print('clNN expressions declared')

OUT = NEW/'compiled'/'project_voiced.ustx'
# 基于 project_voiced（已含 dyn/voic/brec/tenc）？这里先从带发声层的版本出发更稳妥
prev = NEW/'compiled'/'project_voiced.ustx'
if prev.is_file():
    doc2 = load_ustx(prev)
    # 把音色设置套到带发声层的版本上
    doc2['expressions'] = dict(doc2['expressions'])
    doc2['expressions']['clr'] = clr
    for abbr in ('cl01','cl02','cl03','cl04','cl05'):
        doc2['expressions'][abbr] = doc['expressions'][abbr]
    doc2['tracks'][0]['voice_color_names'] = COLORS[:]
    for part in doc2['voice_parts']:
        for note in part['notes']:
            pe = [x for x in (note.get('phoneme_expressions') or []) if x.get('abbr')!='clr']
            for j in range(8):
                pe.append(dict(index=j, abbr='clr', value=0))
            note['phoneme_expressions'] = pe
        part['curves'] = [c for c in part.get('curves', []) if not c['abbr'].startswith('cl')]
        dur = int(part['duration'])
        for abbr, val in MIX.items():
            if val <= 0: continue
            part['curves'].append(dict(abbr=abbr, xs=[0, dur], ys=[int(round(val)), int(round(val))]))
    save_ustx(doc2, OUT)
    print(f'\nwrote {OUT} (on top of the phonation layer)')
else:
    save_ustx(doc, OUT)
    print(f'\nwrote {OUT} (base only; phonation layer not present)')
