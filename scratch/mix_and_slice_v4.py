import json
from pathlib import Path
import numpy as np
import soundfile as sf
import yaml

from agent2utau.audio.mix import mix

run_dir = Path(r"E:\project\agent2utau\runs\production\zuihouyiye-from-scratch-20261027")
obs_dir = run_dir / "observation"
render_dir = run_dir / "render_v4"

vocal_wav = render_dir / "vocal_vocal.wav"
if not vocal_wav.exists():
    vocal_wav = render_dir / "vocal.wav"
assert vocal_wav.exists(), f"Rendered vocal not found: {vocal_wav}"

accomp_wav = obs_dir / "stems" / "source_(other)_vocals_mel_band_roformer.wav"
mix_path = render_dir / "zuihouyiye_lingyuan_cover_mix_v4.wav"

vocal_gain_db = 1.0
accomp_gain_db = -3.5
while True:
    try:
        mix_res = mix(vocal_wav, accomp_wav, mix_path, vocal_gain_db=vocal_gain_db, accomp_gain_db=accomp_gain_db)
        if mix_res["peak"] <= 0.92:
            break
        vocal_gain_db = round(vocal_gain_db - 1.0, 2)
        accomp_gain_db = round(accomp_gain_db - 1.0, 2)
    except ValueError:
        vocal_gain_db = round(vocal_gain_db - 1.5, 2)
        accomp_gain_db = round(accomp_gain_db - 1.5, 2)

print("Mix v4 result:", json.dumps(mix_res, ensure_ascii=False))

mix_audio, sr = sf.read(str(mix_path), dtype="float32")
vocal_audio, _ = sf.read(str(vocal_wav), dtype="float32")
if vocal_audio.ndim > 1:
    vocal_audio = vocal_audio.mean(axis=1)

first_half_mix = mix_audio[int(13.5 * sr) : int(102.0 * sr)]
sf.write(str(render_dir / "first_half_mix_v4.wav"), first_half_mix, sr)

# Save test audition slices in scratch:
# 1. 64s - 71s (Phrase 9 "在回忆里完整" entering 66.5s-69.2s "整")
sf.write("scratch/v4_slice_64_71_vocal.wav", vocal_audio[int(64.0 * sr) : int(71.0 * sr)], sr)
sf.write("scratch/v4_slice_64_71_mix.wav", mix_audio[int(64.0 * sr) : int(71.0 * sr)], sr)

# 2. 72s - 77.5s (Phrase 10 "想把你抱进身体里面")
sf.write("scratch/v4_slice_72_77_vocal.wav", vocal_audio[int(72.0 * sr) : int(77.5 * sr)], sr)
sf.write("scratch/v4_slice_72_77_mix.wav", mix_audio[int(72.0 * sr) : int(77.5 * sr)], sr)

# 3. 77s - 81s (Phrase 11 "不敢让你看见")
sf.write("scratch/v4_slice_77_81_vocal.wav", vocal_audio[int(77.0 * sr) : int(81.0 * sr)], sr)
sf.write("scratch/v4_slice_77_81_mix.wav", mix_audio[int(77.0 * sr) : int(81.0 * sr)], sr)

# 4. 80.5s - 86.0s (Phrase 12 "嘴角那颗没落下的泪")
sf.write("scratch/v4_slice_80_86_vocal.wav", vocal_audio[int(80.5 * sr) : int(86.0 * sr)], sr)
sf.write("scratch/v4_slice_80_86_mix.wav", mix_audio[int(80.5 * sr) : int(86.0 * sr)], sr)

# Create project_with_accompaniment.ustx for v4
proj_data = yaml.safe_load((run_dir / "compiled_v4" / "project.ustx").read_text(encoding="utf-8"))
proj_with_acc = dict(proj_data)
tracks = list(proj_with_acc.get("tracks", []))
tracks.append({
    "singer": "",
    "phonemizer": "OpenUtau.Core.DefaultPhonemizer",
    "renderer": "CLASSIC",
    "mute": False,
    "solo": False,
    "volume": float(accomp_gain_db),
    "pan": 0.0,
    "track_name": "Accompaniment",
    "track_color": "Blue",
    "track_expressions": [],
    "voice_color_names": [""],
})
proj_with_acc["tracks"] = tracks
proj_with_acc["wave_parts"] = [{
    "name": "Instrumental",
    "comment": "",
    "track_no": 1,
    "position": 0,
    "filepath": str(accomp_wav),
    "relative_path": "../observation/stems/source_(other)_vocals_mel_band_roformer.wav",
    "file_duration_ms": float(len(mix_audio) / sr * 1000.0),
    "skip_ms": 0.0,
    "trim_ms": 0.0,
}]
(render_dir / "project_with_accompaniment.ustx").write_text(
    yaml.safe_dump(proj_with_acc, allow_unicode=True, sort_keys=False),
    encoding="utf-8",
)
print("Slices and project_with_accompaniment.ustx for v4 created successfully!")
