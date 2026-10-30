import sys, numpy as np, soundfile as sf
sys.path.insert(0, 'src')
sys.stdout.reconfigure(encoding='utf-8')
from agent2utau.analysis.f0 import extract_f0
from agent2utau.analysis.rmvpe import infer_rmvpe
from pathlib import Path
from agent2utau.resources.config import load_config

RUN = 'runs/production/nianlun-from-scratch-v2-20261028'
cfg = load_config()

print('extracting render F0 (fcpe)...', flush=True)
r_fc = extract_f0(f'{RUN}/render/vocal_vocal.wav')
print('  n frames', r_fc['n_frames'], 'voiced', float(r_fc['voiced'].mean()))
np.savez_compressed('scratch/render_fcpe.npz', **{k: v for k, v in r_fc.items() if isinstance(v, np.ndarray)})

print('extracting render F0 (rmvpe)...', flush=True)
r_rm = infer_rmvpe(f'{RUN}/render/vocal_vocal.wav', Path(cfg['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx')
np.savez_compressed('scratch/render_rmvpe.npz', **{k: v for k, v in r_rm.items() if isinstance(v, np.ndarray)})
print('  done')
