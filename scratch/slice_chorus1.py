import soundfile as sf
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
vocal_wav = obs_dir / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"
data, sr = sf.read(str(vocal_wav))

t0, t1 = 69.5, 78.5
chunk = data[int(t0*sr):int(t1*sr)]
out_slice = Path(r"scratch/chorus1_start.wav")
sf.write(str(out_slice), chunk, sr)
print(f"Wrote slice {out_slice}")
