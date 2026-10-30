"""区分：源字内 73c std 是「颤音」还是「装饰/滑音/换音」？

用频域分析：计算每字源 F0 的主频（detrended）。
  主频 4-8Hz → 颤音（vibrato）
  主频 <2Hz   → 慢走势/滑音
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
def midi(hz): return 69+12*np.log2(np.maximum(hz,1e-6)/440)
s = np.load(NEW/'inputs/fcpe.npz'); s2 = np.load(NEW/'inputs/rmvpe.npz')
st = s['times'].astype(float)
cf = np.where(s['voiced'], midi(s['f0_hz'])*100, np.nan)
cr = np.where(s2['voiced'], midi(s2['f0_hz'])*100, np.nan)
ok = np.isfinite(cf)&np.isfinite(cr)&(np.abs(cf-cr)<=100)
src = np.where(ok,(cf+cr)/2,np.nan)
W = json.load(io.open(NEW/'words_v3.json',encoding='utf-8'))

from collections import Counter
kinds = Counter(); details = []
for ph in W['phrases']:
    for w in ph['words']:
        a,b = w['start'], w['end']; d = b-a
        if d < 0.35: kinds['too_short'] += 1; continue
        T = np.arange(a,b,0.01)
        i = np.clip(np.rint(T*100).astype(int),0,len(st)-1)
        v = src[i]; m = np.isfinite(v)
        if m.sum() < 20: kinds['sparse'] += 1; continue
        t = T[m]; x = v[m]
        # detrend with linear fit
        x = x - np.polyval(np.polyfit(t, x, 1), t)
        # FFT
        n = len(x)
        fs = 1/0.01
        sp = np.abs(np.fft.rfft(x*np.hanning(n)))
        fr = np.fft.rfftfreq(n, 1/fs)
        lo = (fr>=0.5)&(fr<=12)
        if not lo.any(): kinds['nofreq'] += 1; continue
        pk = fr[lo][np.argmax(sp[lo])]
        amp = float(np.std(x))
        if pk >= 3.5:
            kinds['vibrato'] += 1; details.append(('vib', w['hanzi'], d, round(amp,0), round(pk,1)))
        elif pk >= 1.2:
            kinds['slow'] += 1; details.append(('slow', w['hanzi'], d, round(amp,0), round(pk,1)))
        else:
            kinds['drift'] += 1; details.append(('drift', w['hanzi'], d, round(amp,0), round(pk,1)))
print('syllable motion types:', dict(kinds))
for k in ('vib','slow','drift'):
    sub = [d for d in details if d[0]==k]
    if sub:
        amps=[d[3] for d in sub]; frs=[d[4] for d in sub]; durs=[d[2] for d in sub]
        print(f'  {k}: n={len(sub)}, std median {np.median(amps):.0f}c, freq median {np.median(frs):.1f}Hz, dur median {np.median(durs):.2f}s')
print('\nsample vibrato syllables:')
for d in sorted([d for d in details if d[0]=='vib'], key=lambda z:-z[3])[:10]:
    print('   ', d)
