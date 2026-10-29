"""v3h 最终核验：F0 / 动态 / 音符主体贴合 / 时钟。"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.analysis.f0 import extract_f0
from agent2utau.analysis.rmvpe import infer_rmvpe
from agent2utau.resources.config import load_config
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')
cfg = load_config()
def midi(h): return 69+12*np.log2(np.maximum(h,1e-6)/440)
def load(p):
    d=np.load(p); return d['times'].astype(float), d['f0_hz'].astype(float), d['voiced'].astype(bool)

WAV = NEW/'render'/'vocal_v3h_vocal.wav'
f0d = NEW/'render'/'f0_v3h'; f0d.mkdir(parents=True, exist_ok=True)
if not (f0d/'fcpe.npz').exists():
    r=extract_f0(WAV); np.savez_compressed(f0d/'fcpe.npz',**{k:v for k,v in r.items() if isinstance(v,np.ndarray)})
    r2=infer_rmvpe(WAV, Path(cfg['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx')
    np.savez_compressed(f0d/'rmvpe.npz',**{k:v for k,v in r2.items() if isinstance(v,np.ndarray)})

st,s1,sv1 = load(NEW/'inputs/fcpe.npz'); _,s2,sv2 = load(NEW/'inputs/rmvpe.npz')
SC = np.where(sv1&sv2&(np.abs(midi(s1)-midi(s2))<0.5),(midi(s1)+midi(s2))/2,np.nan)

def f0_eval(fd, alias=None):
    if alias: rt,r1,rv1=load(alias[0]); _,r2,rv2=load(alias[1])
    else: rt,r1,rv1=load(fd/'fcpe.npz'); _,r2,rv2=load(fd/'rmvpe.npz')
    RC=np.where(rv1&rv2&(np.abs(midi(r1)-midi(r2))<0.5),(midi(r1)+midi(r2))/2,np.nan)
    T=np.arange(19.0,242.5,0.01)
    si=np.clip(np.rint(T*100).astype(int),0,len(st)-1); ri=np.clip(np.rint(T*100).astype(int),0,len(rt)-1)
    s=SC[si]; r=RC[ri]; g=np.isfinite(s)&np.isfinite(r); d=(r-s)[g]*100
    return dict(n=int(g.sum()), med=float(np.median(np.abs(d))), p90=float(np.percentile(np.abs(d),90)),
                o100=float((np.abs(d)>100).mean()), o200=float((np.abs(d)>200).mean()))

def dyn(p):
    a,sr=sf.read(str(p),dtype='float32')
    if a.ndim>1: a=a.mean(1)
    w=int(0.02*sr); n=len(a)//w
    e=np.sqrt((a[:n*w].reshape(n,w)**2).mean(1)); db=20*np.log10(np.maximum(e,1e-9))
    act=db>(np.percentile(db,95)-30); ar=db[act]
    return dict(iqr=float(np.percentile(ar,75)-np.percentile(ar,25)), peak=float(np.abs(a).max()),
                rms=float(np.sqrt((a.astype(np.float64)**2).mean())))

# note-body check on the compiled project
doc=load_ustx(NEW/'compiled'/'project.ustx'); tm=TempoMap.from_doc(doc)
pitch=json.load(io.open(NEW/'compiled'/'pitch.json',encoding='utf-8'))
dt=np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pitch['phrases']])
dc=np.concatenate([np.asarray(x['final_cents'],float) for x in pitch['phrases']])
o=np.argsort(dt); dt,dc=dt[o],dc[o]
devs=[]
for part in doc['voice_parts']:
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        d=b-a
        if d<0.05: continue
        T=np.arange(a+0.25*d,b-0.25*d,0.005)
        if len(T)<3: continue
        devs.append(float(np.median(np.interp(T,dt,dc)))-n['tone']*100)
devs=np.array(devs)

rep=dict(
  f0_v2=f0_eval(None, alias=('scratch/render_fcpe.npz','scratch/render_rmvpe.npz')),
  f0_v3h=f0_eval(f0d),
  dyn_source=dyn(NEW/'inputs/stems/vocals.wav'),
  dyn_v2=dyn(V2/'render'/'vocal_vocal.wav'),
  dyn_v3h=dyn(WAV),
  note_body=dict(notes=int(len(devs)), med_abs=float(np.median(np.abs(devs))),
                 p90=float(np.percentile(np.abs(devs),90)),
                 over100=float((np.abs(devs)>100).mean()),
                 over50=float((np.abs(devs)>50).mean())),
)
print('='*60)
print('v3h 最终核验')
print('='*60)
f=rep['f0_v3h']; g=rep['f0_v2']
print(f'\nF0 vs 原唱:')
print(f'  v2  med|Δ| {g["med"]:5.1f}c  p90 {g["p90"]:6.1f}  >100c {g["o100"]:5.1%}  >200c {g["o200"]:5.1%}')
print(f'  v3h med|Δ| {f["med"]:5.1f}c  p90 {f["p90"]:6.1f}  >100c {f["o100"]:5.1%}  >200c {f["o200"]:5.1%}')
print(f'\n音符主体贴合（设计线 vs 该音 tone）:')
nb=rep['note_body']
print(f'  {nb["notes"]} notes  med|Δ| {nb["med_abs"]:.1f}c  p90 {nb["p90"]:.1f}c  >50c {nb["over50"]:.1%}  >100c {nb["over100"]:.1%}')
print(f'\n动态:')
for k in ('dyn_source','dyn_v2','dyn_v3h'):
    v=rep[k]; print(f'  {k:12s} IQR {v["iqr"]:5.1f}dB  peak {v["peak"]:.3f}  rms {v["rms"]:.4f}')
(NEW/'evaluation').mkdir(exist_ok=True)
(NEW/'evaluation'/'verification_v3h.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'\nwrote evaluation/verification_v3h.json')
