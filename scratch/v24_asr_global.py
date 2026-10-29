"""可靠的咬字指标：全局 bigram recall（不做逐句对齐）。

为什么不用逐句对齐：
  原唱（真值）在逐句口径下只有 39.9% —— 因为原唱的实际演唱时机
  与我们谱面的句窗不完全一致，对齐失败。这证明该口径不可用。

全局口径（更稳健）：
  1) 分段转写（8s 窗）避免长音频幻觉
  2) 过滤已知幻觉短语
  3) 把 18-243s 内全部 ASR 文本拼起来
  4) 与我们 349 字歌词算 bigram recall
参考基准：原唱自身应得高分；若原唱不是最高，说明该方法仍不可用。
"""
import sys, json, io, os, re
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx
from faster_whisper import WhisperModel

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')
doc = load_ustx(NEW/'score'/'v3_score.ustx')
LYRIC = ''.join(n['lyric'] for part in doc['voice_parts'] for n in part['notes']
                if n['lyric'] not in ('AP','SP','+'))
BIGR = {LYRIC[i:i+2] for i in range(len(LYRIC)-1)}
print(f'参考歌词 {len(LYRIC)} 字, {len(BIGR)} bigram')

snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
md = sorted((snap/'snapshots').iterdir())[-1]
m = WhisperModel(str(md), device='cpu', compute_type='int8')
def norm(s): return re.sub(r'[^\u4e00-\u9fff]','',s)

HALLUC_PAT = re.compile(r'(作词|作曲|李宗盛|优优独播|YoYo|字幕|志愿者|谢谢观看|请不吝)')
WIN, HOP = 6.0, 4.0
TMP = NEW/'_chunk.wav'

def asr_text(wav, start=18.0, end=243.0):
    a, sr = sf.read(str(wav), dtype='float32')
    if a.ndim>1: a=a.mean(1)
    i0, i1 = int(start*sr), int(end*sr)
    a = a[i0:i1]
    total = len(a)/sr
    parts=[]
    t=0.0
    while t < total:
        t2=min(t+WIN, total)
        if t2-t < 1.5: break
        sf.write(str(TMP), a[int(t*sr):int(t2*sr)], sr)
        segs,_ = m.transcribe(str(TMP), language='zh', beam_size=5, vad_filter=False)
        for s in segs:
            if HALLUC_PAT.search(s.text): continue
            txt = norm(s.text)
            if len(txt) >= 2: parts.append(txt)
        t += HOP
    # 用最长公共子序列思路去重：重叠窗口会产生重复文本，
    # 这里简单去重：如果某段是前一端的子串就跳过
    dedup=[]
    for p in parts:
        if dedup and (p in dedup[-1] or dedup[-1] in p):
            if len(p) > len(dedup[-1]): dedup[-1]=p
            continue
        dedup.append(p)
    return ''.join(dedup)

results={}
for name, wav in [('source', NEW/'inputs'/'stems'/'vocals.wav'),
                  ('v2', V2/'render'/'vocal_vocal.wav'),
                  ('final', NEW/'render'/'vocal_v23_vocal.wav')]:
    if not wav.is_file(): print(f'{name}: missing'); continue
    t = asr_text(wav)
    tb = [t[i:i+2] for i in range(len(t)-1)]
    rec = sum(1 for g in tb if g in BIGR)/max(len(tb),1)
    inl = sum(1 for c in t if c in set(LYRIC))/max(len(t),1)
    results[name]=dict(chars=len(t), bigram_recall=round(rec,4), in_lyric=round(inl,4), text=t[:400])
    print(f'{name:8s} chars {len(t):4d}  bigram-recall {rec:6.1%}  in-lyric {inl:6.1%}')

(NEW/'evaluation'/'asr_global.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('\n判据：原唱应是最高的（真值）。')
if results:
    best = max(results, key=lambda k: results[k]['bigram_recall'])
    print(f'  实际最高: {best} ({results[best]["bigram_recall"]:.1%})')
    print(f'  => {"方法可用" if best=="source" else "方法仍不可靠，不能用于判分"}')
print('wrote evaluation/asr_global.json')
