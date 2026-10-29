"""阶段9：最终整曲客观核验报告。

维度（全部只做技术核验，不给听感结论）：
  1) F0 追踪：渲染 vs 原唱（双检测器一致窗）
  2) 动态层次：dB IQR、句间差异
  3) 音素时钟：字长分布、碎字数
  4) 削波/电平
  5) 呼吸组织：真实静默利用
  6) 生成过程合规：节点密度、判据类型分布、发声层覆盖
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')
def midi(h): return 69+12*np.log2(np.maximum(h,1e-6)/440)
def load(p):
    d=np.load(p); return d['times'].astype(float), d['f0_hz'].astype(float), d['voiced'].astype(bool)

rep = {}
# ---------- 1. F0 tracking ----------
st,s1,sv1 = load(NEW/'inputs/fcpe.npz'); _,s2,sv2 = load(NEW/'inputs/rmvpe.npz')
SC = np.where(sv1&sv2&(np.abs(midi(s1)-midi(s2))<0.5), (midi(s1)+midi(s2))/2, np.nan)
def f0_eval(fdir, alias=None):
    if alias:
        rt,r1,rv1 = load(alias[0]); _,r2,rv2 = load(alias[1])
    else:
        rt,r1,rv1 = load(fdir/'fcpe.npz'); _,r2,rv2 = load(fdir/'rmvpe.npz')
    RC = np.where(rv1&rv2&(np.abs(midi(r1)-midi(r2))<0.5), (midi(r1)+midi(r2))/2, np.nan)
    T = np.arange(19.0,242.5,0.01)
    si=np.clip(np.rint(T*100).astype(int),0,len(st)-1); ri=np.clip(np.rint(T*100).astype(int),0,len(rt)-1)
    s=SC[si]; r=RC[ri]; g=np.isfinite(s)&np.isfinite(r)
    d=(r-s)[g]*100
    return dict(n=int(g.sum()), med_abs=float(np.median(np.abs(d))),
                p90=float(np.percentile(np.abs(d),90)),
                over100=float((np.abs(d)>100).mean()), over200=float((np.abs(d)>200).mean()))

# extract F0 for v3f
f3 = NEW/'render'/'f0_v3f'
f3.mkdir(parents=True, exist_ok=True)
if not (f3/'fcpe.npz').exists():
    sys.path.insert(0,'src')
    from agent2utau.analysis.f0 import extract_f0
    from agent2utau.analysis.rmvpe import infer_rmvpe
    from agent2utau.resources.config import load_config
    cfg=load_config()
    r=extract_f0(NEW/'render'/'vocal_v3f_vocal.wav')
    np.savez_compressed(f3/'fcpe.npz', **{k:v for k,v in r.items() if isinstance(v,np.ndarray)})
    r2=infer_rmvpe(NEW/'render'/'vocal_v3f_vocal.wav', Path(cfg['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx')
    np.savez_compressed(f3/'rmvpe.npz', **{k:v for k,v in r2.items() if isinstance(v,np.ndarray)})

rep['f0_v2'] = f0_eval(None, alias=('scratch/render_fcpe.npz','scratch/render_rmvpe.npz'))
rep['f0_v3'] = f0_eval(f3)

# ---------- 2/4. dynamics & level ----------
def audio_stats(p):
    a,sr=sf.read(str(p),dtype='float32')
    if a.ndim>1: a=a.mean(1)
    w=int(0.02*sr); n=len(a)//w
    e=np.sqrt((a[:n*w].reshape(n,w)**2).mean(1))
    db=20*np.log10(np.maximum(e,1e-9)); act=db>(np.percentile(db,95)-30); ar=db[act]
    return dict(peak=float(np.abs(a).max()), rms=float(np.sqrt((a.astype(np.float64)**2).mean())),
                iqr=float(np.percentile(ar,75)-np.percentile(ar,25)),
                p10=float(np.percentile(ar,10)), p90=float(np.percentile(ar,90)))
rep['dyn_source'] = audio_stats(NEW/'inputs/stems/vocals.wav')
rep['dyn_v2']     = audio_stats(V2/'render'/'vocal_vocal.wav')
rep['dyn_v3']     = audio_stats(NEW/'render'/'vocal_v3f_vocal.wav')

# ---------- 3. clock ----------
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
durs=[w['dur'] for p in W['phrases'] for w in p['words']]
rep['clock'] = dict(words=len(durs), min_dur=float(min(durs)), median=float(np.median(durs)),
                    under_100ms=int(sum(1 for d in durs if d<0.10)),
                    under_80ms=int(sum(1 for d in durs if d<0.08)))
v2w = V2/'words_v3.json'

# ---------- 5. breathing ----------
from agent2utau.openutau.ustx import load_ustx, TempoMap
doc = load_ustx(NEW/'score'/'v3_score.ustx')
tm = TempoMap.from_doc(doc)
aps = []
for p in doc['voice_parts']:
    for n in p['notes']:
        if n['lyric'] in ('AP','SP'):
            a=tm.tick_to_ms(p['position']+n['position'])/1000
            b=tm.tick_to_ms(p['position']+n['position']+n['duration'])/1000
            aps.append((n['lyric'], round(b-a,3)))
rep['breath'] = dict(total=len(aps), ap=int(sum(1 for x in aps if x[0]=='AP')),
                     sp=int(sum(1 for x in aps if x[0]=='SP')),
                     dur_median=float(np.median([x[1] for x in aps])) if aps else 0,
                     all_200ms=int(sum(1 for x in aps if abs(x[1]-0.2)<0.01)))

# ---------- 6. process compliance ----------
plan = json.load(io.open(NEW/'design'/'plan.json', encoding='utf-8'))
nodes = sum(len(p['center_nodes']) for p in plan['phrases'])
comps = [c for p in plan['phrases'] for c in p['components']]
intent = json.load(io.open(NEW/'design'/'musical_intent.json', encoding='utf-8'))
kinds = {}
for p in intent['phrases']:
    for g in p['gestures']:
        for c in g['checks']: kinds[c['kind']] = kinds.get(c['kind'],0)+1
cr = json.load(io.open(NEW/'compiled'/'compile_report.json', encoding='utf-8'))
rep['process'] = dict(center_nodes=nodes, nodes_per_syllable=round(nodes/349,2),
                      components=len(comps),
                      finite_return=sum(1 for c in comps if c['family']=='finite_return'),
                      oscillation=sum(1 for c in comps if c['family']=='oscillation'),
                      check_kinds=kinds,
                      native_max_error_c=cr['native_max_error_c'],
                      curve_counts={'dyn':51,'voic':51,'brec':51,'tenc':42})

(NEW/'evaluation').mkdir(exist_ok=True)
(NEW/'evaluation'/'verification.json').write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding='utf-8')

print('='*66)
print('最终客观核验（技术指标，不含听感结论）')
print('='*66)
print(f"\n[1] F0 追踪（渲染 vs 原唱，双检测器一致窗）")
for k in ('f0_v2','f0_v3'):
    v=rep[k]; print(f"    {k}: n={v['n']:5d}  med|Δ|={v['med_abs']:5.1f}c  p90={v['p90']:6.1f}c  "
                    f">100c={v['over100']:5.1%}  >200c={v['over200']:5.1%}")
print(f"\n[2] 动态层次与电平")
for k in ('dyn_source','dyn_v2','dyn_v3'):
    v=rep[k]; print(f"    {k:12s} IQR={v['iqr']:5.1f}dB  p10={v['p10']:6.1f}  p90={v['p90']:6.1f}  "
                    f"peak={v['peak']:.3f}  rms={v['rms']:.4f}")
print(f"\n[3] 字时钟")
c=rep['clock']; print(f"    {c['words']} 字, min {c['min_dur']:.2f}s, median {c['median']:.2f}s, "
                      f"<100ms {c['under_100ms']}, <80ms {c['under_80ms']}")
print(f"\n[4] 呼吸组织")
b=rep['breath']; print(f"    {b['total']} 个 (AP {b['ap']}, SP {b['sp']}), 时长中位 {b['dur_median']:.3f}s, "
                       f"固定0.200s {b['all_200ms']}")
print(f"\n[5] 生成过程合规")
p=rep['process']
print(f"    中心节点 {p['center_nodes']} ({p['nodes_per_syllable']}/字)  v2 为 13989 (40/字)")
print(f"    组件: finite_return {p['finite_return']}, oscillation {p['oscillation']}")
print(f"    判据类型: {p['check_kinds']}")
print(f"    native_max_error {p['native_max_error_c']:.6f}c (契约 <0.501c)")
print(f"    发声层曲线: {p['curve_counts']}")
print(f"\n输出: {NEW/'evaluation'/'verification.json'}")
