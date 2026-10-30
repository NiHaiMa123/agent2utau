import soundfile as sf
import numpy as np
from pathlib import Path

run_dir = Path(r"runs/production/zuihouyiye-from-scratch-20261027")
mix_v3_path = run_dir / "render_v3" / "zuihouyiye_lingyuan_cover_mix_v3.wav"
vocal_v3_path = run_dir / "render_v3" / "vocal_vocal.wav"
src_vocal_path = run_dir / "observation" / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"

data_mix, sr_mix = sf.read(mix_v3_path)
data_vocal, sr_vocal = sf.read(vocal_v3_path)
data_src, sr_src = sf.read(src_vocal_path)

def slice_and_save(data, sr, t0, t1, out_path):
    i0 = int(round(t0 * sr))
    i1 = int(round(t1 * sr))
    sub = data[i0:i1]
    sf.write(out_path, sub, sr)
    print(f"Saved {out_path} ({t0}s - {t1}s, {len(sub)} samples)")

# Slices around 1:08:
# 1. 64s - 71s (Phrase 9 "在回忆里完整" entering 66.5s-69.2s "整")
slice_and_save(data_mix, sr_mix, 64.0, 71.0, "scratch/slice_64_71_mix.wav")
slice_and_save(data_vocal, sr_vocal, 64.0, 71.0, "scratch/slice_64_71_vocal.wav")
slice_and_save(data_src, sr_src, 64.0, 71.0, "scratch/slice_64_71_src.wav")

# 2. 72s - 77.5s (Phrase 10 "想把你抱进身体里面")
slice_and_save(data_mix, sr_mix, 72.0, 77.5, "scratch/slice_72_77_mix.wav")
slice_and_save(data_vocal, sr_vocal, 72.0, 77.5, "scratch/slice_72_77_vocal.wav")
slice_and_save(data_src, sr_src, 72.0, 77.5, "scratch/slice_72_77_src.wav")

# 3. 80.5s - 86.0s (Phrase 12 "嘴角那颗没落下的泪")
slice_and_save(data_mix, sr_mix, 80.5, 86.0, "scratch/slice_80_86_mix.wav")
slice_and_save(data_vocal, sr_vocal, 80.5, 86.0, "scratch/slice_80_86_vocal.wav")
slice_and_save(data_src, sr_src, 80.5, 86.0, "scratch/slice_80_86_src.wav")
