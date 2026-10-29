"""阶段8：整曲混音（人声 + 分离伴奏），固定增益、拒绝削波。"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
VOC = NEW/'render'/'vocal_v3f_vocal.wav'
INST = NEW/'inputs'/'stems'/'instrumental.wav'

v, sr = sf.read(str(VOC), dtype='float32')
inst, sr2 = sf.read(str(INST), dtype='float32')
print(f'vocal {len(v)/sr:.2f}s  inst {len(inst)/sr:.2f}s  sr {sr}/{sr2}')
if v.ndim > 1: v = v.mean(1)
if inst.ndim > 1: inst = inst.mean(1)
assert sr == sr2

L = max(len(v), len(inst))
vv = np.zeros(L, np.float64); vv[:len(v)] = v
ii = np.zeros(L, np.float64); ii[:len(inst)] = inst

def db(x): return 20*np.log10(max(x, 1e-12))
print(f'vocal rms {db(np.sqrt((vv**2).mean())):.2f}dB  inst rms {db(np.sqrt((ii**2).mean())):.2f}dB')

# explicit fixed gains (no auto-balance): vocal 0 dB, instrumental -6.5 dB
GV, GI = 10**(0/20), 10**(-6.5/20)
mix = vv*GV + ii*GI
peak = np.abs(mix).max()
print(f'pre-limit peak {peak:.4f} ({db(peak):.2f}dBFS)')
if peak > 0.999:
    # single global headroom, declared (not per-segment normalisation)
    g = 0.98/peak
    mix *= g
    print(f'applied single global headroom {db(g):.3f} dB -> peak {np.abs(mix).max():.4f}')
    GV *= g; GI *= g

out = NEW/'render'/'nianlun_v3_mix.wav'
sf.write(str(out), mix.astype(np.float32), sr, subtype='PCM_24')
info = sf.info(str(out))
print(f'wrote {out}  {info.duration:.2f}s peak {np.abs(mix).max():.4f}')

# also a vocal-only delivery at matched loudness to the source vocal
si, _ = sf.read(str(NEW/'inputs'/'stems'/'vocals.wav'), dtype='float32')
if si.ndim > 1: si = si.mean(1)
vo = vv.copy()
mine = np.sqrt((vo[vo!=0]**2).mean()); theirs = np.sqrt((si**2).mean())
g = theirs/max(mine,1e-9)
print(f'vocal-only match gain {db(g):+.2f} dB (ours {db(mine):.2f} -> source {db(theirs):.2f})')
vc = vo*g
if np.abs(vc).max() > 0.999: vc *= 0.98/np.abs(vc).max()
out2 = NEW/'render'/'nianlun_v3_vocal_matched.wav'
sf.write(str(out2), vc.astype(np.float32), sr, subtype='PCM_24')
print(f'wrote {out2} peak {np.abs(vc).max():.4f}')

meta = dict(vocal=str(VOC), instrumental=str(INST), mix=str(out), vocal_matched=str(out2),
            sample_rate=sr, gains_db=dict(vocal=round(20*np.log10(GV),3),
                                          instrumental=round(20*np.log10(GI),3)),
            mix_peak=float(np.abs(mix).max()), duration_s=round(L/sr,2),
            note='fixed explicit gains; single global headroom only if needed; no per-segment normalisation')
(NEW/'render'/'mix_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
print('wrote mix_meta.json')
