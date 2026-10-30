import sys, numpy as np, soundfile as sf
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'
for p in [f'{RUN}/render/vocal_vocal.wav',
          f'{RUN}/observation/stems/source_(vocals)_vocals_mel_band_roformer.wav']:
    info = sf.info(p)
    print(p.split('/')[-1], info.samplerate, info.channels, f'{info.duration:.2f}s')
    a, sr = sf.read(p, dtype='float32')
    if a.ndim > 1: a = a.mean(1)
    print(f'   peak {np.abs(a).max():.4f}  rms {np.sqrt((a**2).mean()):.4f}')
    # short-window rms envelope every 0.5s
    w = int(0.5*sr)
    env = np.sqrt(np.add.reduceat(a[:len(a)//w*w]**2, np.arange(0, len(a)//w*w, w))/w)
    print('   env dB (0.5s):', np.round(20*np.log10(np.maximum(env,1e-9)), 1)[:40])
