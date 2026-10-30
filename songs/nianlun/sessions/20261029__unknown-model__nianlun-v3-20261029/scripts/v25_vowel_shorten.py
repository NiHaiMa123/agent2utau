"""用 phoneme_overrides 缩短元音，提高辅音占比，测咬字。

依据：
  我们辅音占比 26.1%，原唱 29.7%（元音 394ms vs 292ms，辅音 140 vs 114）。
  phoneme_overrides = [{index, offset}]，offset 单位 ms（白烁工程实证）。
  对「元音音素」给正 offset（后推起点）→ 元音变短。
剂量：+20 / +35 ms 两档。
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

doc = load_ustx(NEW/'compiled'/'project_final.ustx')
LYRIC = ''.join(n['lyric'] for part in doc['voice_parts'] for n in part['notes']
                if n['lyric'] not in ('AP','SP','+'))
BIGR = {LYRIC[i:i+2] for i in range(len(LYRIC)-1)}

# 从 phones.json 建立 (part_position, phrase_position) -> 每 note 的元音 phone_index
ph = json.load(io.open(NEW/'compiled'/'phones.json', encoding='utf-8'))
vmap = {}   # part_position -> {note_local_index -> [vowel indices]}
for pi, part in enumerate(ph['parts']):
    pos = int(part.get('part_position', doc['voice_parts'][pi]['position']))
    d = {}
    for phrase in part['phrases']:
        for q in phrase['phones']:
            mk = q['phoneme'].split('/',1)[-1]
            if mk in ONSETS or mk in ('SP','AP','EP',''): continue
            for own in q.get('owner_note_indices') or []:
                d.setdefault(own, []).append(q['phone_index'])
    vmap[pos] = d
print(f'parts mapped: {len(vmap)}; sample note->vowels: '
      f'{list(vmap[list(vmap)[0]].items())[:3]}')

snap = Path(os.path.expanduser('~'))/'.cache'/'huggingface'/'hub'/'models--mobiuslabsgmbh--faster-whisper-large-v3-turbo'
md = sorted((snap/'snapshots').iterdir())[-1]
wm = WhisperModel(str(md), device='cpu', compute_type='int8')
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

for dose in (20, 35):
    d = load_ustx(NEW/'compiled'/'project_final.ustx')
    n_set = 0
    for part in d['voice_parts']:
        pos = int(part['position'])
        vm = vmap.get(pos, {})
        for ni, n in enumerate(part['notes']):
            if n['lyric'] in ('AP','SP','+'): continue
            idxs = vm.get(ni, [])
            if not idxs: continue
            ov = [x for x in (n.get('phoneme_overrides') or []) if x.get('index') not in idxs]
            for ix in idxs:
                ov.append(dict(index=int(ix), offset=int(dose)))
            n['phoneme_overrides'] = ov
            n_set += 1
    p = T/f'vowel{dose}.ustx'; save_ustx(d, p)
    res = run_bridge(cfg, ['render','--project',str(p.resolve()),
                           '--out',str((T/f'vowel{dose}.wav').resolve()),'--timeout','1500'])
    print(f'\ndose +{dose}ms: notes {n_set}, render ok={res.get("ok")}')
    w = T/f'vowel{dose}_vocal.wav'
    if w.is_file():
        print(f'  bigram recall {recall(w):.1%}')
print(f'\nbaseline (current): 56.0%')
