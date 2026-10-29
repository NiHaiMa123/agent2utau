"""确认咬字差距的真正来源：音高曲线（PITD）是否损害咬字？

消融：把 PITD 全部归零（只保留音符阶梯），测咬字 recall。
这直接回答「音高设计是否损害可懂度」。
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
T = NEW/'_ablate2'; T.mkdir(exist_ok=True)

doc = load_ustx(NEW/'compiled'/'project_final.ustx')
LYRIC = ''.join(n['lyric'] for part in doc['voice_parts'] for n in part['notes']
                if n['lyric'] not in ('AP','SP','+'))
BIGR = {LYRIC[i:i+2] for i in range(len(LYRIC)-1)}

snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
md = sorted((snap/'snapshots').iterdir())[-1]
m = WhisperModel(str(md), device='cpu', compute_type='int8')
def norm(s): return re.sub(r'[^\u4e00-\u9fff]','',s)
HALLUC = re.compile(r'(作词|作曲|李宗盛|优优独播|YoYo|字幕|志愿者)')

def recall(wav):
    a,sr = sf.read(str(wav), dtype='float32')
    if a.ndim>1: a=a.mean(1)
    a = a[int(18*sr):int(243*sr)]
    total=len(a)/sr; parts=[]; t=0.0; tmp=T/'c.wav'
    while t < total:
        t2=min(t+6.0,total)
        if t2-t<1.5: break
        sf.write(str(tmp), a[int(t*sr):int(t2*sr)], sr)
        segs,_=m.transcribe(str(tmp),language='zh',beam_size=5,vad_filter=False)
        for s in segs:
            if HALLUC.search(s.text): continue
            x=norm(s.text)
            if len(x)>=2: parts.append(x)
        t+=4.0
    dedup=[]
    for p in parts:
        if dedup and (p in dedup[-1] or dedup[-1] in p):
            if len(p)>len(dedup[-1]): dedup[-1]=p
            continue
        dedup.append(p)
    txt=''.join(dedup)
    tb=[txt[i:i+2] for i in range(len(txt)-1)]
    return sum(1 for g in tb if g in BIGR)/max(len(tb),1), len(txt)

# 变体：PITD 归零（只留音符阶梯 + 清音色层保留）
d = load_ustx(NEW/'compiled'/'project_final.ustx')
for part in d['voice_parts']:
    part['curves'] = [c for c in part['curves'] if c['abbr'] != 'pitd']
p = T/'no-pitd.ustx'; save_ustx(d, p)
res = run_bridge(cfg, ['render','--project',str(p.resolve()),
                       '--out',str((T/'no-pitd.wav').resolve()),'--timeout','1200'])
print(f'render ok={res.get("ok")}')
w = T/'no-pitd_vocal.wav'
if w.is_file():
    r,n = recall(w)
    print(f'no-PITD (pure note steps) : recall {r:6.1%}  chars {n}')
print(f'current (with PITD)       : recall  56.0%  chars 451')
