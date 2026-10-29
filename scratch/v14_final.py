"""最终核验 + 交付（v14 = 音乐上合理的版本）。

诚实结论：
  白烁的大 PITD 值（|y|>300c，4.69%）与位置/时长/音程都无关，是逐个字的手调结果，
  没有可归纳的规律。试图用统计分布去拟合会得到「每个字都深挖」的错误结果——
  这正是 v12/v13 图审暴露的问题（句首下探 3-5 个半音）。

  因此本版按音乐判断收敛：
    字头滑入 22-150c（按音程大小）
    字尾释放 28-140c
    字腹周期/慢走势 22-155c（按源运动类型与时长）
    全程斜率受限（<=95c/步），无悬崖
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')
REF = Path(r'E:\project\agent2utau\research\baishuo\projects\雨爱-有参by白烁.ustx')

def audio_stats(p):
    a,sr=sf.read(str(p),dtype='float32')
    if a.ndim>1: a=a.mean(1)
    w=int(0.02*sr); n=len(a)//w
    e=np.sqrt((a[:n*w].reshape(n,w)**2).mean(1)); db=20*np.log10(np.maximum(e,1e-9))
    act=db>(np.percentile(db,95)-30); ar=db[act]
    return dict(iqr=float(np.percentile(ar,75)-np.percentile(ar,25)),
                peak=float(np.abs(a).max()), rms=float(np.sqrt((a.astype(float)**2).mean())),
                full=int((np.abs(a)>=0.99999).sum()), dur=round(len(a)/sr,1))

def pitd_stats(path, label):
    d=load_ustx(path); ys=[]
    for part in d['voice_parts']:
        pit=next((c for c in part.get('curves',[]) if c['abbr']=='pitd'),None)
        if pit: ys.extend(pit['ys'])
    y=np.array(ys,float)
    dy=np.abs(np.diff(y))
    print(f'  {label:16s} n={len(y):6d}  p50={np.percentile(y,50):+6.0f}  p99={np.percentile(y,99):+6.0f}  '
          f'|y|>200 {(np.abs(y)>200).mean():5.2%}  |dy|max {dy.max():.0f}')

print('=== PITD 形状对比 ===')
pitd_stats(REF, '白烁 雨爱')
pitd_stats(NEW/'compiled'/'project_v13.ustx', 'v14(本版)')
pitd_stats(V2/'compiled'/'project.ustx', 'v2(旧)')

print('\n=== 音频指标 ===')
print(f'{"version":14s}  IQR    peak   rms     full  dur')
rows=[]
for k,p in [('source',NEW/'inputs/stems/vocals.wav'),
            ('v2',V2/'render/vocal_vocal.wav'),
            ('v6',NEW/'render/vocal_v6_vocal.wav'),
            ('v10',NEW/'render/vocal_v10_vocal.wav'),
            ('v12',NEW/'render/vocal_v12_vocal.wav'),
            ('v13(最终)',NEW/'render/vocal_v13_vocal.wav')]:
    if not p.exists(): continue
    s=audio_stats(p); rows.append((k,s))
    print(f'{k:14s} {s["iqr"]:5.1f}  {s["peak"]:.3f}  {s["rms"]:.4f}  {s["full"]}  {s["dur"]}')

# 图审记录：实际看过的 3 张
review = dict(schema_version=1,
  method='atlas page inspection; each record states what was actually seen',
  records=[
    dict(version='v11', atlas='p0_f0_v0_000.png', opened=True, result='fail',
         observation='18.75s 出现垂直暴跌，56 -> 50.8（约 -520c，5 个半音），19.4s 亦有阶梯。',
         reason='极端段在 12ms 网格内瞬移，形成悬崖；音乐上句首不可能下探 5 个半音。',
         action='把极端段改为有起有落的平滑段，并加斜率软限幅。'),
    dict(version='v12', atlas='p0_f0_v0_000.png', opened=True, result='fail',
         observation='悬崖已消失，但 18.75s 仍是 V 形下陷 57 -> 51.4（-560c），持续约 100ms。',
         reason='统计拟合导致每个字都深挖；白烁 p1=-513c 只是极少数点，不是句首常态。',
         action='按音乐判断收敛字头深度：普通字 22-95c，大跳最多 150c。'),
    dict(version='v13', atlas='p0_f0_v0_000.png', opened=True, result='keep',
         observation='起音处仅轻微下探后平滑进入 57 平台，音与音之间是连续斜坡而非垂直台阶，'
                     '字腹有可见起伏，无明显尖角。',
         reason='形状符合手绘线条：平滑、幅度克制、无悬崖。',
         action='保留；后续可在长音上加更强的周期支撑（需逐个听）。'),
  ],
  coverage=dict(units_total=349, units_opened=3, note='3/349 实际打开；其余未审，不计覆盖'),
  limitation='349 个单元未逐个打开；本记录不构成覆盖完成')
(NEW/'evaluation'/'visual_review_partial.json').write_text(
    json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
print('\nwrote evaluation/visual_review_partial.json (3/349 actually opened)')

# 交付混音
voc=NEW/'render'/'vocal_v13_vocal.wav'
inst=NEW/'inputs'/'stems'/'instrumental.wav'
v,sr=sf.read(str(voc),dtype='float32'); i,_=sf.read(str(inst),dtype='float32')
if v.ndim>1: v=v.mean(1)
if i.ndim>1: i=i.mean(1)
L=max(len(v),len(i)); vv=np.zeros(L); ii=np.zeros(L)
vv[:len(v)]=v; ii[:len(i)]=i
mix=vv+ii*10**(-6.5/20)
pk=np.abs(mix).max()
g=0.95/pk if pk>0.95 else 1.0
mix*=g
sf.write(str(NEW/'render'/'nianlun_v13_mix.wav'), mix.astype(np.float32), sr, subtype='PCM_24')
si,_=sf.read(str(NEW/'inputs'/'stems'/'vocals.wav'),dtype='float32')
if si.ndim>1: si=si.mean(1)
g2=np.sqrt((si**2).mean())/max(np.sqrt((vv[vv!=0]**2).mean()),1e-9)
vc=vv*g2
if np.abs(vc).max()>0.98: vc*=0.98/np.abs(vc).max()
sf.write(str(NEW/'render'/'nianlun_v13_vocal_matched.wav'), vc.astype(np.float32), sr, subtype='PCM_24')
print(f'mix peak {np.abs(mix).max():.4f}, vocal matched peak {np.abs(vc).max():.4f}')
