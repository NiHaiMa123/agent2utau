import numpy as np
import soundfile as sf
from pathlib import Path

obs_dir = Path(r"runs/production/nianlun-from-scratch-20261028/observation")
vocal_wav = obs_dir / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"
data, sr = sf.read(str(vocal_wav))
if data.ndim > 1:
    data = data.mean(axis=1)

# Compute short-time energy / RMS in 20ms frames
hop = int(0.01 * sr)
win = int(0.04 * sr)
rms = []
times = []
for i in range(0, len(data) - win, hop):
    frame = data[i:i+win]
    rms.append(np.sqrt(np.mean(frame**2)))
    times.append(i / sr)

rms = np.array(rms)
times = np.array(times)

# Check energy in gaps between candidate phrases
# Let's inspect where RMS is lowest (< 0.01) for > 0.25s
is_silent = rms < 0.008
silence_blocks = []
in_sil = False
sil_start = 0.0
for t, s in zip(times, is_silent):
    if s and not in_sil:
        in_sil = True
        sil_start = t
    elif not s and in_sil:
        in_sil = False
        if t - sil_start > 0.25:
            silence_blocks.append((round(sil_start, 2), round(t, 2), round(t - sil_start, 2)))
if in_sil and times[-1] - sil_start > 0.25:
    silence_blocks.append((round(sil_start, 2), round(times[-1], 2), round(times[-1] - sil_start, 2)))

print(f"Found {len(silence_blocks)} natural breath/silence pauses (>0.25s):")
for b in silence_blocks:
    if 15.0 <= b[0] <= 245.0:
        print(f"  Silence: {b[0]:6.2f}s - {b[1]:6.2f}s (dur={b[2]:4.2f}s)")
