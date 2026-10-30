"""定位咬字恶化：按句统计 ASR 覆盖率，找出最差的句子。

渲染音频 396 字 vs 参考 349 字 —— 多出 47 字，说明有「多余音节」或「拖尾被识别成音节」。
"""
import sys, json, io, os, re
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap
from faster_whisper import WhisperModel

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)

phrases=[]
for pi, part in enumerate(doc['voice_parts']):
    notes=[n for n in part['notes'] if n['lyric'] not in ('AP','SP')]
    if not notes: continue
    a = tm.tick_to_ms(part['position']+notes[0]['position'])/1000
    b = tm.tick_to_ms(part['position']+notes[-1]['position']+notes[-1]['duration'])/1000
    txt = ''.join(n['lyric'] for n in notes if n['lyric']!='+')
    phrases.append(dict(pi=pi, a=a, b=b, text=txt))

snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
md = sorted((snap/'snapshots').iterdir())[-1]
m = WhisperModel(str(md), device='cpu', compute_type='int8')

def norm(s): return re.sub(r'[^\u4e00-\u9fff]','',s)

for label, wav in [('final', NEW/'render'/'vocal_v23_vocal.wav'),
                   ('v2', Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028\render\vocal_vocal.wav'))]:
    segs,_ = m.transcribe(str(wav), language='zh', beam_size=5, vad_filter=False)
    sents = [dict(a=s.start, b=s.end, t=norm(s.text)) for s in segs]
    print(f'\n=== {label}: {len(sents)} ASR segments ===')
    # 对每个谱面句，找时间重叠最多的 ASR 段
    rows=[]
    for ph in phrases:
        best=None; bo=0
        for s in sents:
            ov = min(ph['b'], s['b']) - max(ph['a'], s['a'])
            if ov > bo: bo=ov; best=s
        if best is None or bo < 0.2*(ph['b']-ph['a']): 
            rows.append((ph['pi'], ph['text'], '(no asr)', 0.0)); continue
        ref = ph['text']
        hyp = best['t']
        # 字级匹配率（简单做法：hyp 中出现的 ref 字比例）
        hit = sum(1 for c in ref if c in hyp)
        rows.append((ph['pi'], ref, hyp, hit/max(len(ref),1)))
    bad = sorted(rows, key=lambda x:x[3])[:10]
    print('  最差 10 句:')
    for r in bad:
        print(f"    p{r[0]:2d} recall {r[3]:.0%}  ref「{r[1]}」 hyp「{r[2][:30]}」")
    good = sorted(rows, key=lambda x:-x[3])[:3]
    print('  最好 3 句:')
    for r in good:
        print(f"    p{r[0]:2d} recall {r[3]:.0%}  ref「{r[1]}」")
