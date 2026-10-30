"""整曲客观核验：v3 渲染人声 F0 vs 原唱 F0，与 v2 同口径对比。"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.analysis.f0 import extract_f0
from agent2utau.analysis.rmvpe import infer_rmvpe
from agent2utau.resources.config import load_config

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
cfg = load_config()
WAV = NEW/'render'/'vocal_v3_vocal.wav'
info = sf.info(str(WAV))
print(f'render: {info.duration:.2f}s {info.samplerate}Hz')

out = NEW/'render'/'f0'
out.mkdir(parents=True, exist_ok=True)
if not (out/'fcpe.npz').exists():
    def midi(hz): return 69+12*np.log2(np.maximum(hz,1e-6)/440)
    r = extract_f0(WAV)
    np.savez_compressed(out/'fcpe.npz', **{k:v for k,v in r.items() if isinstance(v,np.ndarray)})
    r2 = infer_rmvpe(WAV, Path(cfg['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx')
    np.savez_compressed(out/'rmvpe.npz', **{k:v for k,v in r2.items() if isinstance(v,np.ndarray)})
    print('F0 extracted')
else:
    print('F0 cached')

def midi(hz): return 69+12*np.log2(np.maximum(hz,1e-6)/440)
def load(p):
    d = np.load(p); return d['times'].astype(float), d['f0_hz'].astype(float), d['voiced'].astype(bool)

def load_alias(p, want):
    """v2 render F0 lives in scratch/render_fcpe.npz & render_rmvpe.npz."""
    if p.exists(): return load(p)
    alt = Path('scratch')/f'render_{want}.npz'
    return load(alt)

def cmp(run_dir, wav_f0, label, legacy=False):
    def src_dir(rd):
        for cand in (rd/'inputs', rd/'observation'):
            if (cand/'fcpe.npz').exists(): return cand
        raise SystemExit(f'no source F0 under {rd}')
    sd = src_dir(run_dir)
    st, sf_, sv = load(sd/'fcpe.npz')
    st2, sf2, sv2 = load(sd/'rmvpe.npz')
    rt, rf, rv = load_alias(wav_f0/'fcpe.npz', 'fcpe')
    rt2, rf2, rv2 = load_alias(wav_f0/'rmvpe.npz', 'rmvpe')
    sc = np.where(sv & sv2 & (np.abs(midi(sf_)-midi(sf2))<0.5), (midi(sf_)+midi(sf2))/2, np.nan)
    rc = np.where(rv & rv2 & (np.abs(midi(rf)-midi(rf2))<0.5), (midi(rf)+midi(rf2))/2, np.nan)
    T = st[(st>18)&(st<243)]
    src = np.interp(T, st, np.nan_to_num(sc, nan=0.0))
    rnd = np.interp(T, rt, np.nan_to_num(rc, nan=0.0))
    g = np.isfinite(sc)[ (st>18)&(st<243) ] & (np.interp(T, rt, rv & rv2) > 0.5)
    d = (rnd-src)[g]*100
    print(f'\n=== {label} ===')
    print(f'  comparable frames {g.sum()}')
    print(f'  median {np.median(d):+7.1f}c  med|Δ| {np.median(np.abs(d)):6.1f}c  p90|Δ| {np.percentile(np.abs(d),90):6.1f}c')
    for thr in (50,100,200):
        print(f'    |Δ|>{thr:4d}c: {(np.abs(d)>thr).mean():6.1%}')
    return d

# v2 baseline (already extracted)
V2 = Path(r'E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028')
d2 = cmp(V2, Path('scratch'), 'v2 render vs source')
d3 = cmp(NEW, out, 'v3 render vs source')
print(f'\nIMPROVEMENT: med|Δ| {np.median(np.abs(d2)):.1f}c -> {np.median(np.abs(d3)):.1f}c '
      f'({np.median(np.abs(d3))/np.median(np.abs(d2)):.0%} of v2)')
print(f'  >100c: {(np.abs(d2)>100).mean():.1%} -> {(np.abs(d3)>100).mean():.1%}')
