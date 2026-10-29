import librosa
import numpy as np
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
inst_wav = obs_dir / "stems" / "source_(other)_vocals_mel_band_roformer.wav"

y, sr = librosa.load(str(inst_wav), sr=22050, duration=120.0)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
tempo_val = float(np.atleast_1d(tempo)[0])
beat_times = librosa.frames_to_time(beats, sr=sr)
beat_intervals = np.diff(beat_times)

print(f"Estimated tempo: {tempo_val:.2f} BPM")
print(f"First 10 beat times: {np.round(beat_times[:10], 3)}")
print(f"Mean beat interval: {np.mean(beat_intervals):.4f}s -> {60.0 / np.mean(beat_intervals):.2f} BPM")
