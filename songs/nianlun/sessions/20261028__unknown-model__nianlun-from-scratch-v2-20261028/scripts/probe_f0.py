import numpy as np, json, io, sys
sys.stdout.reconfigure(encoding='utf-8')
run = 'runs/production/nianlun-from-scratch-v2-20261028'
for name in ['observation/fcpe.npz', 'observation/rmvpe.npz']:
    d = np.load(f'{run}/{name}', allow_pickle=True)
    print('==', name, '==')
    for k in d.files:
        a = d[k]
        print(f'  {k}: shape={a.shape} dtype={a.dtype}', (a.ravel()[:5] if a.size else ''))
