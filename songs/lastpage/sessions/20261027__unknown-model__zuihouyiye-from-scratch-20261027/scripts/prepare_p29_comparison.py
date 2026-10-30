from pathlib import Path
import soundfile as sf
import numpy as np

accomp_path = Path("runs/production/zuihouyiye-from-scratch-20261027/observation/stems/source_(other)_vocals_mel_band_roformer.wav")
accomp, sr = sf.read(str(accomp_path), dtype="float32")
if accomp.ndim > 1:
    accomp_mono = accomp.mean(axis=1)
else:
    accomp_mono = accomp

# 195.5s to 200.5s corresponds to Part 29 (3:15.5 to 3:20.5)
start_sample = int(195.5 * sr)
end_sample = int(200.5 * sr)
acc_slice = accomp[start_sample:end_sample]

variants = [
    ("baseline", "scratch/test_p29_baseline_vocal.wav"),
    ("A_solid", "scratch/test_p29_A_solid_vocal.wav"),
    ("B_strong", "scratch/test_p29_B_strong_vocal.wav"),
]

for name, wav_path in variants:
    p = Path(wav_path)
    if not p.exists():
        continue
    voc, _ = sf.read(str(p), dtype="float32")
    if voc.ndim > 1:
        voc = voc.mean(axis=1)
    voc_slice = voc[start_sample:end_sample]
    
    # Save dry vocal slice
    sf.write(f"scratch/p29_{name}_dry.wav", voc_slice, sr)
    
    # Mix with accompaniment (-3.5 dB accomp, 0 dB vocal)
    voc_stereo = np.column_stack([voc_slice, voc_slice])
    mix_slice = voc_stereo * 1.0 + acc_slice * (10 ** (-3.5 / 20.0))
    peak = np.max(np.abs(mix_slice))
    if peak > 0.95:
        mix_slice = mix_slice * (0.92 / peak)
    sf.write(f"scratch/p29_{name}_mix.wav", mix_slice, sr)

print("Comparison slices ready!")
