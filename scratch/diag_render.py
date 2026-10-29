import sys, numpy as np, soundfile as sf
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'
p = f'{RUN}/render/vocal_vocal.wav'
a, sr = sf.read(p, dtype='float32')
print('shape', a.shape, 'sr', sr)
print('exact +1 samples:', int((a >= 0.99999).sum()))
print('exact -1 samples:', int((a <= -0.99999).sum()))
print('|a|>0.99:', int((np.abs(a) > 0.99).sum()), 'of', a.size, f'= {(np.abs(a)>0.99).mean():.4%}')
print('|a|>0.95:', f'{(np.abs(a)>0.95).mean():.4%}')
print('|a|>0.8 :', f'{(np.abs(a)>0.8).mean():.4%}')

# zero-crossing / silence map, 1s frames
w = sr
n = len(a)//w
env = np.sqrt((a[:n*w].reshape(n, w)**2).mean(1))
db = 20*np.log10(np.maximum(env, 1e-12))
nz = db > -60
print(f'\n1s frames {n}, audible {nz.mean():.1%}, first audible at {np.argmax(nz)}s')
# find silent gaps inside audible region
first, last = np.argmax(nz), n-1-np.argmax(nz[::-1])
gaps, run = [], 0
for i in range(first, last+1):
    if not nz[i]: run += 1
    else:
        if run >= 2: gaps.append((i-run, run))
        run = 0
print('silent runs >=2s inside song:', gaps[:20])
print('db stats over audible: min %.1f p10 %.1f median %.1f p90 %.1f max %.1f' % (
    db[nz].min(), np.percentile(db[nz],10), np.median(db[nz]),
    np.percentile(db[nz],90), db[nz].max()))
