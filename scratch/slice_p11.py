import soundfile as sf
from pathlib import Path

run_dir = Path(r"runs/production/zuihouyiye-from-scratch-20261027")
mix_v3_path = run_dir / "render_v3" / "zuihouyiye_lingyuan_cover_mix_v3.wav"
vocal_v3_path = run_dir / "render_v3" / "vocal_vocal.wav"
src_vocal_path = run_dir / "observation" / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"

data_vocal, sr_vocal = sf.read(vocal_v3_path)
data_src, sr_src = sf.read(src_vocal_path)

def slice_and_save(data, sr, t0, t1, out_path):
    i0 = int(round(t0 * sr))
    i1 = int(round(t1 * sr))
    sf.write(out_path, data[i0:i1], sr)

slice_and_save(data_vocal, sr_vocal, 77.0, 81.0, "scratch/slice_77_81_vocal.wav")
slice_and_save(data_src, sr_src, 77.0, 81.0, "scratch/slice_77_81_src.wav")
print("Saved 77-81 slices")
