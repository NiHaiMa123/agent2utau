"""最终 ASR 口径：分段识别（每 8 秒一段，带 0.5s 重叠），避免整段幻觉吞掉开头。

这是标准做法：Whisper 长音频会产生「幻觉段」，分段可消除。
"""
import sys, json, io, os, re
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap
from faster_whisper import WhisperModel

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)

phrases=[]
for pi, part in enumerate(doc['voice_parts']):
    notes=[n for n in part['notes'] if n['lyric'] not in ('AP','SP')]
    if not notes: continue
    a = tm.tick_to_ms(part['position']+notes[0]['position'])/1000
    b = tm.tick_to_ms(part['position']+notes[-1]['position']+notes[-1]['duration'])/1000
    phrases.append(dict(pi=pi, a=a, b=b,
                        text=''.join(n['lyric'] for n in notes if n['lyric']!='+')))

snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
md = sorted((snap/'snapshots').iterdir())[-1]
m = WhisperModel(str(md), device='cpu', compute_type='int8')
def norm(s): return re.sub(r'[^\u4e00-\u9fff]','',s)

WIN, HOP = 8.0, 7.5

def transcribe_chunked(wav):
    a, sr = sf.read(str(wav), dtype='float32')
    if a.ndim>1: a=a.mean(1)
    out=[]
    t0=0.0
    while t0 < len(a)/sr:
        t1=min(t0+WIN, len(a)/sr)
        if t1-t0 < 1.5: break
        clip=a[int(t0*sr):int(t1*sr)]
        tmp=NEW/'_chunk.wav'; sf.write(str(tmp), clip, sr)
        segs,_=m.transcribe(str(tmp), language='zh', beam_size=5, vad_filter=False)
        for s in segs:
            txt=norm(s.text)
            if txt: out.append(dict(a=s.start+t0, b=s.end+t0, t=txt))
        t0 += HOP
    # 去重（同一起始±0.3s 只留最长）
    out.sort(key=lambda x:(x['a'], -len(x['t'])))
    dedup=[]
    for x in out:
        if any(abs(x['a']-y['a'])<0.35 for y in dedup): continue
        dedup.append(x)
    return dedup

def analyze(wav,label):
    sents=transcribe_chunked(wav)
    rec=[]
    for ph in phrases:
        hyp=''
        for s in sents:
            ov=min(ph['b'],s['b'])-max(ph['a'],s['a'])
            if ov > 0.4*min(ph['b']-ph['a'], s['b']-s['a']): hyp+=s['t']
        rec.append(sum(1 for c in ph['text'] if c in hyp)/max(len(ph['text']),1) if hyp else 0.0)
    r=np.array(rec)
    print(f'{label:8s} mean {r.mean():5.1%}  median {np.median(r):5.1%}  '
          f'>=80% {(r>=0.8).sum():2d}/{len(r)}  <40% {(r<0.4).sum():2d}')
    return r

print('分段 ASR（8s 窗口，0.5s 重叠）:')
r_f = analyze(NEW/'render'/'vocal_v23_vocal.wav','final')
r_v = analyze(V2/'render'/'vocal_vocal.wav','v2')
r_s = analyze(NEW/'inputs'/'stems'/'vocals.wav','source')

print('\n逐句（final / v2 / source）:')
for i,ph in enumerate(phrases):
    flag = ' <-- 低' if r_f[i]<0.4 else ''
    print(f'  p{ph["pi"]:2d} {ph["text"][:10]:10s} {r_f[i]:.0%} / {r_v[i]:.0%} / {r_s[i]:.0%}{flag}')

(NEW/'evaluation'/'asr_chunked_final.json').write_text(json.dumps(dict(
    method='8s windows with 0.5s overlap (avoids Whisper long-form hallucination)',
    final_mean=float(r_f.mean()), v2_mean=float(r_v.mean()), source_mean=float(r_s.mean()),
    final_ge80=int((r_f>=0.8).sum()), final_lt40=int((r_f<0.4).sum()),
    per_phrase=[dict(pid=ph['pi'], text=ph['text'], final=float(r_f[i]),
                     v2=float(r_v[i]), source=float(r_s[i])) for i,ph in enumerate(phrases)]
), ensure_ascii=False, indent=2), encoding='utf-8')
print('\nwrote evaluation/asr_chunked_final.json')
