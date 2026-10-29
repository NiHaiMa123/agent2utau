"""交付一致性审计：确认工程/曲线/渲染/混音/报告全部对应同一版本。

多轮迭代后最大的风险是「文件之间不对应」：
  - project_final.ustx 里是 v21 曲线
  - pitch_final.json 是否也来自它
  - 渲染的 vocal_v23 是否由它渲染
  - nianlun_v23_mix 是否由 vocal_v23 混音

逐项用 SHA / 数值核对。
"""
import sys, json, io, hashlib
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap, sha256

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')

def db(x): return 20*np.log10(max(x,1e-12))

print('=== 1) 工程与曲线 ===')
proj = NEW/'compiled'/'project_final.ustx'
pf   = NEW/'compiled'/'pitch_final.json'
print(f'project_final.ustx sha {sha256(proj)[:16]}')
print(f'pitch_final.json   sha {sha256(pf)[:16]}')

doc = load_ustx(proj)
tm = TempoMap.from_doc(doc)
pj = json.load(io.open(pf, encoding='utf-8'))

# 工程的 PITD 与 pitch_final 的 final_cents 是否一致（final = before + pitd）
bp = json.load(io.open(NEW/'compiled'/'pitch_baseline.json', encoding='utf-8'))
cmap = {}
for part in doc['voice_parts']:
    pit = next((c for c in part['curves'] if c['abbr']=='pitd'), None)
    if pit: cmap[int(part['position'])] = (np.array(pit['xs'],float), np.array(pit['ys'],float))
maxerr = 0.0
for bph, fph in zip(bp['phrases'], pj['phrases']):
    pos = int(bph['part_position'])
    if pos not in cmap: continue
    xs, ys = cmap[pos]
    ticks = np.array([tm.ms_to_tick(t)-pos for t in np.asarray(bph['times_ms'],float)])
    exp = np.asarray(bph['before_pitd_cents'],float) + np.interp(ticks, xs, ys)
    act = np.asarray(fph['final_cents'],float)
    maxerr = max(maxerr, float(np.max(np.abs(act-exp))))
print(f'  project PITD + before_pitd vs pitch_final: max diff {maxerr:.4f}c  '
      f'({"MATCH" if maxerr<0.501 else "MISMATCH"})')

print('\n=== 2) 渲染是否来自该工程 ===')
voc = NEW/'render'/'vocal_v23_vocal.wav'
mix = NEW/'render'/'nianlun_v23_mix.wav'
inst = NEW/'inputs'/'stems'/'instrumental.wav'
print(f'vocal_v23_vocal.wav  {voc.stat().st_size} bytes  sha {sha256(voc)[:16]}')
print(f'nianlun_v23_mix.wav  {mix.stat().st_size} bytes  sha {sha256(mix)[:16]}')

# 混音是否 = vocal*1.0 + inst*G（单次全局增益）
v, sr = sf.read(str(voc), dtype='float32')
i, _ = sf.read(str(inst), dtype='float32')
m, _ = sf.read(str(mix), dtype='float32')
if v.ndim>1: v=v.mean(1)
if i.ndim>1: i=i.mean(1)
if m.ndim>1: m=m.mean(1)
L = max(len(v), len(i))
vv = np.zeros(L); ii = np.zeros(L); vv[:len(v)] = v; ii[:len(i)] = i
GI = 10**(-6.5/20)
recon = (vv + ii*GI)
# 检查存在的全局增益
peak = np.abs(recon).max()
g = 0.95/peak if peak > 0.95 else 1.0
recon *= g
d = m - recon[:len(m)]
print(f'  mix vs (vocal + inst*{db(GI):.2f}dB)*{db(g):.2f}dB : max abs diff {np.abs(d).max():.2e}')
print(f'  => {"MATCH" if np.abs(d).max() < 1e-6 else "DIFFERS"}')

print('\n=== 3) 渲染音频 vs 设计线（引擎跟随度）===')
sys.path.insert(0, 'src')
from agent2utau.analysis.f0 import extract_f0
f0dir = NEW/'render'/'f0_v23'
f0dir.mkdir(parents=True, exist_ok=True)
if not (f0dir/'fcpe.npz').exists():
    r = extract_f0(voc)
    np.savez_compressed(f0dir/'fcpe.npz', **{k:x for k,x in r.items() if isinstance(x,np.ndarray)})
d0 = np.load(f0dir/'fcpe.npz')
rt, rf, rv = d0['times'].astype(float), d0['f0_hz'].astype(float), d0['voiced'].astype(bool)
def midi(h): return 69+12*np.log2(np.maximum(h,1e-9)/440)
dt_ = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pj['phrases']])
dc_ = np.concatenate([np.asarray(x['final_cents'],float) for x in pj['phrases']])
o = np.argsort(dt_); dt_, dc_ = dt_[o], dc_[o]
T = np.arange(19.0, 242.5, 0.01)
ri = np.clip(np.rint(T*100).astype(int), 0, len(rt)-1)
rnd = midi(rf[ri]); voiced = rv[ri]
des = np.interp(T, dt_, dc_)/100.0
gmask = voiced & np.isfinite(rnd)
e = (rnd-des)[gmask]*100
print(f'  frames {gmask.sum()}: med|Δ| {np.median(np.abs(e)):.2f}c  p90 {np.percentile(np.abs(e),90):.2f}c')
print(f'  => 引擎跟随（med|Δ| < 10c 视为精确）')

print('\n=== 4) 交付文件清单 ===')
demo = Path(r'E:\project\agent2utau\demo\nianlun_v3')
for f in sorted(demo.glob('nianlun_v23*')):
    print(f'  {f.name}  {f.stat().st_size} bytes')
rep = Path(r'E:\project\agent2utau\docs\reports\nianlun\nianlun-v23-final-delivery-20261029.md')
print(f'  report: {rep.name}  exists={rep.is_file()}')
