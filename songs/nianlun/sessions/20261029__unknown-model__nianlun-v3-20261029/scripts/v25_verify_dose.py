"""两个关键验证：
  1) ASR 重复性（噪声底）：同一音频重复识别 3 次，recall 波动多大
  2) +20ms 剂量是否真的改变了辅音占比（不能只看 recall）
只有当改善 > 噪声底时才算有效。
"""
import sys, json, io, os, re
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx
from agent2utau.openutau.bridge import run_bridge
from agent2utau.resources.config import load_config
from faster_whisper import WhisperModel

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
T = NEW/'_vel'
cfg = load_config()
ONSETS = set('b p m f d t n l g k h j q x zh ch sh r z c s y w'.split())
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
LYRIC = ''.join(n['lyric'] for part in doc['voice_parts'] for n in part['notes']
                if n['lyric'] not in ('AP','SP','+'))
BIGR = {LYRIC[i:i+2] for i in range(len(LYRIC)-1)}

snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
md = sorted((snap/'snapshots').iterdir())[-1]
wm = WhisperModel(str(md), device='cpu', compute_type='int8')
def norm(s): return re.sub(r'[^\u4e00-\u9fff]','',s)
HALLUC = re.compile(r'(作词|作曲|李宗盛|优优独播|YoYo|字幕|志愿者)')

def recall(wav, tmpname='c.wav'):
    a,sr = sf.read(str(wav), dtype='float32')
    if a.ndim>1: a=a.mean(1)
    a = a[int(18*sr):int(243*sr)]
    total=len(a)/sr; parts=[]; t=0.0; tmp=T/tmpname
    while t < total:
        t2=min(t+6.0,total)
        if t2-t<1.5: break
        sf.write(str(tmp), a[int(t*sr):int(t2*sr)], sr)
        segs,_=wm.transcribe(str(tmp),language='zh',beam_size=5,vad_filter=False)
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
    txt=''.join(dedup); tb=[txt[i:i+2] for i in range(len(txt)-1)]
    return sum(1 for g in tb if g in BIGR)/max(len(tb),1)

print('=== 1) ASR 重复性（同一音频 3 次，beam_size=5 应确定性） ===')
base = NEW/'render'/'vocal_v23_vocal.wav'
rs = [recall(base, f'r{i}.wav') for i in range(3)]
print(f'  current: {[f"{x:.1%}" for x in rs]}  std {np.std(rs):.3%}')

plus20 = T/'vowel20_vocal.wav'
if plus20.is_file():
    rs2 = [recall(plus20, f's{i}.wav') for i in range(2)]
    print(f'  +20ms  : {[f"{x:.1%}" for x in rs2]}')

print('\n=== 2) 辅音占比是否真的改变 ===')
def ratio(proj):
    ph_out = T/'_ph.json'
    r = run_bridge(cfg, ['export-phonemes','--project',str(proj.resolve()),
                         '--out',str(ph_out.resolve())])
    if not r.get('ok'): return None
    d = json.load(io.open(ph_out, encoding='utf-8'))
    con=0.0; vow=0.0; nc=0; nv=0
    for part in d['parts']:
        for phrase in part['phrases']:
            for q in phrase['phones']:
                mk=q['phoneme'].split('/',1)[-1]
                if mk in ('SP','AP','EP',''): continue
                dd=q['end_ms']-q['start_ms']
                if mk in ONSETS: con+=dd; nc+=1
                else: vow+=dd; nv+=1
    return con/(con+vow), con/max(nc,1), vow/max(nv,1)

for label, proj in [('current', NEW/'compiled'/'project_final.ustx'),
                    ('+20ms', T/'vowel20.ustx'),
                    ('+35ms', T/'vowel35.ustx')]:
    if not proj.is_file(): continue
    rr = ratio(proj)
    if rr:
        print(f'  {label:8s} 辅音占比 {rr[0]:.1%}  辅音中位 {rr[1]:.0f}ms  元音中位 {rr[2]:.0f}ms')
print(f'  原唱参考    辅音占比 29.7%  辅音中位 114ms  元音中位 292ms')
