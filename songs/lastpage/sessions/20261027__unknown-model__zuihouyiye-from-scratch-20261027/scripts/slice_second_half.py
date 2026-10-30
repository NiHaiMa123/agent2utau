import soundfile as sf
from pathlib import Path

mix_path = "runs/production/zuihouyiye-from-scratch-20261027/render_v4/zuihouyiye_lingyuan_cover_mix_v4.wav"
vocal_path = "runs/production/zuihouyiye-from-scratch-20261027/render_v4/vocal_vocal.wav"
src_path = "runs/production/zuihouyiye-from-scratch-20261027/observation/stems/source_(vocals)_vocals_mel_band_roformer.wav"

data_mix, sr = sf.read(mix_path)
data_vocal, _ = sf.read(vocal_path)
data_src, _ = sf.read(src_path)

def slice_wav(data, sr, t0, t1, out_path):
    i0 = int(round(t0 * sr))
    i1 = int(round(t1 * sr))
    sf.write(out_path, data[i0:i1], sr)

# 1. Verse 2 (127s - 148s)
slice_wav(data_mix, sr, 127.0, 148.0, "scratch/v4_verse2_mix.wav")
slice_wav(data_vocal, sr, 127.0, 148.0, "scratch/v4_verse2_vocal.wav")
slice_wav(data_src, sr, 127.0, 148.0, "scratch/v4_verse2_src.wav")

# 2. Chorus 2 (182s - 204s)
slice_wav(data_mix, sr, 182.0, 204.0, "scratch/v4_chorus2_mix.wav")
slice_wav(data_vocal, sr, 182.0, 204.0, "scratch/v4_chorus2_vocal.wav")
slice_wav(data_src, sr, 182.0, 204.0, "scratch/v4_chorus2_src.wav")

# 3. Chorus 3 / Outro (209s - 238s)
slice_wav(data_mix, sr, 209.0, 238.0, "scratch/v4_chorus3_mix.wav")
slice_wav(data_vocal, sr, 209.0, 238.0, "scratch/v4_chorus3_vocal.wav")
slice_wav(data_src, sr, 209.0, 238.0, "scratch/v4_chorus3_src.wav")
print("Saved second half slices!")
