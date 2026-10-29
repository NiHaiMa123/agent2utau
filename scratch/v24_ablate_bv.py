"""受控消融：把 BREC 与 VOIC 归零（恢复模型预测基底），测咬字 bigram recall。

如果归零后咬字显著改善，说明我加的发声层损害了咬字（辅音质感），
应改用更保守的发声层。
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
T = NEW/'_ablate'; T.mkdir(exist_ok=True)

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
    total=len(a)/sr; parts=[]; t=0.0
    tmp=T/'c.wav'
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

variants = []
# A: current
variants.append(('current', None))
# B: BREC/VOIC removed (neutral)
variants.append(('no-breс-voic', 'strip_bv'))

for tag, op in variants:
    if op is None:
        variants_doc = None
        wav = NEW/'render'/'vocal_v23_vocal.wav'
        r, n = recall(wav)
        print(f'{tag:16s} recall {r:6.1%}  chars {n}')
        continue
    d = load_ustx(NEW/'compiled'/'project_final.ustx')
    for part in d['voice_parts']:
        part['curves'] = [c for c in part['curves'] if c['abbr'] not in ('brec','voic')]
    p = T/f'{tag}.ustx'; save_ustx(d, p)
    res = run_bridge(cfg, ['render','--project',str(p.resolve()),
                           '--out',str((T/f'{tag}.wav').resolve()),'--timeout','1200'])
    print(f'{tag:16s} render ok={res.get("ok")}')
    w = T/f'{tag}_vocal.wav'
    if w.is_file():
        r, n = recall(w)
        print(f'{tag:16s} recall {r:6.1%}  chars {n}')
