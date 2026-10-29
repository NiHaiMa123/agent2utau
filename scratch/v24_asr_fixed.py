"""修正 ASR 分析口径：
  1) 排除明显幻觉段（开头重复字幕文字、与谱面时间不重叠）
  2) 按时间重叠严格对齐，只在重叠>0.5 秒时才算
  3) 给出「有效句」的 recall，并区分「无识别」与「识别错」
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

HALLUC = ('作词','作曲','李宗盛','优优独播剧场','YoYo','字幕','志愿者')

def analyze(wav, label):
    segs,_ = m.transcribe(str(wav), language='zh', beam_size=5, vad_filter=False)
    sents=[]
    for s in segs:
        t = norm(s.text)
        if not t: continue
        if any(h in s.text for h in HALLUC):
            # 幻觉段：只在它与谱面时间不重叠时排除
            ov_any = any(min(ph['b'], s.end)-max(ph['a'], s.start) > 0.5 for ph in phrases)
            if not ov_any:
                continue
        sents.append(dict(a=s.start, b=s.end, t=t))
    # 按时间把 ASR 文本拼到每个谱面句上（重叠>=0.5s 或 >=50% 句长）
    recalls=[]; none_count=0
    for ph in phrases:
        hyp=''
        for s in sents:
            ov = min(ph['b'], s['b']) - max(ph['a'], s['a'])
            if ov >= min(0.5, 0.5*(ph['b']-ph['a'])) or ov > 0.5*(ph['b']-ph['a']):
                hyp += s['t']
        if not hyp:
            none_count += 1
            recalls.append(0.0); continue
        hit = sum(1 for c in ph['text'] if c in hyp)
        recalls.append(hit/max(len(ph['text']),1))
    r=np.array(recalls)
    print(f'{label:8s} phrases {len(phrases)}  no-ASR {none_count}  '
          f'mean recall {r.mean():.1%}  median {np.median(r):.1%}  '
          f'>=80% recall: {(r>=0.8).sum()}  <40%: {(r<0.4).sum()}')
    return r

r_final = analyze(NEW/'render'/'vocal_v23_vocal.wav', 'final')
r_v2    = analyze(Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028\render\vocal_vocal.wav'), 'v2')
r_src   = analyze(NEW/'inputs'/'stems'/'vocals.wav', 'source')
print('\n逐句 recall 对照（final vs v2 vs source）:')
for i,ph in enumerate(phrases):
    print(f'  p{ph["pi"]:2d} {ph["text"][:10]:10s}  final {r_final[i]:.0%}  v2 {r_v2[i]:.0%}  src {r_src[i]:.0%}')
