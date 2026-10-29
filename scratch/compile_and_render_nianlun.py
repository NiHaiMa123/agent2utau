import json
from pathlib import Path
import subprocess
import yaml
import soundfile as sf
import numpy as np
import shutil

from agent2utau.audio.mix import mix

run_dir = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
design_dir = run_dir / "design"
compiled_dir = run_dir / "compiled"
render_dir = run_dir / "render"
obs_dir = run_dir / "observation"

if compiled_dir.exists():
    shutil.rmtree(compiled_dir)
render_dir.mkdir(parents=True, exist_ok=True)

# 1. Compile functions
print("Compiling project for nianlun...")
cmd_compile = [
    r"E:\project\agent2utau\.venv\Scripts\python.exe",
    "-m", "agent2utau.cli", "compile-functions",
    "--plan", str(design_dir / "plan.json"),
    "--out", str(compiled_dir),
]
res_c = subprocess.run(cmd_compile, capture_output=True, text=True, check=True)
print(res_c.stdout)

# Check native max error
rep = json.loads((compiled_dir / "compile_report.json").read_text(encoding="utf-8"))
native_err = rep.get("native_max_error_c", 999.0)
print(f"Compilation native max error: {native_err} cents (Contract: < 0.501c)")
assert native_err < 0.501, f"Native error exceeded 0.501c: {native_err}"

# 2. Render vocal project with DiffSinger
print("Rendering vocal with DiffSinger...")
proj_path = compiled_dir / "project.ustx"
vocal_wav_target = render_dir / "vocal.wav"
cmd_render = [
    r"E:\project\agent2utau\.venv\Scripts\python.exe",
    "-m", "agent2utau.cli", "render-project",
    "--project", str(proj_path),
    "--out", str(vocal_wav_target),
]
res_r = subprocess.run(cmd_render, capture_output=True, text=True, check=True)
print(res_r.stdout)

vocal_wav = render_dir / "vocal_vocal.wav"
if not vocal_wav.exists():
    vocal_wav = render_dir / "vocal.wav"
assert vocal_wav.exists(), f"Rendered vocal not found: {vocal_wav}"

# 3. Mix with accompaniment
accomp_wav = obs_dir / "stems" / "source_(other)_vocals_mel_band_roformer.wav"
mix_path = render_dir / "nianlun_lingyuan_cover_mix.wav"

vocal_gain_db = 0.0
accomp_gain_db = -4.0
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

print("Mix result:", json.dumps(mix_res, ensure_ascii=False))

# 4. Slices for listening audition
mix_audio, sr = sf.read(str(mix_path), dtype="float32")
vocal_audio, _ = sf.read(str(vocal_wav), dtype="float32")
if vocal_audio.ndim > 1:
    vocal_audio = vocal_audio.mean(axis=1)

# Slice 1: Verse 1 (18s to 35s, p00-p04)
sf.write("scratch/nianlun_verse1_vocal.wav", vocal_audio[int(18.0 * sr) : int(35.0 * sr)], sr)
sf.write("scratch/nianlun_verse1_mix.wav", mix_audio[int(18.0 * sr) : int(35.0 * sr)], sr)

# Slice 2: Chorus 1 (70s to 97s, p16-p21)
sf.write("scratch/nianlun_chorus1_vocal.wav", vocal_audio[int(70.0 * sr) : int(97.0 * sr)], sr)
sf.write("scratch/nianlun_chorus1_mix.wav", mix_audio[int(70.0 * sr) : int(97.0 * sr)], sr)

# Slice 3: Chorus 2 Climax (157s to 185s, p38-p43)
sf.write("scratch/nianlun_chorus2_vocal.wav", vocal_audio[int(157.0 * sr) : int(185.0 * sr)], sr)
sf.write("scratch/nianlun_chorus2_mix.wav", mix_audio[int(157.0 * sr) : int(185.0 * sr)], sr)

# Slice 4: Chorus 3 & Outro (206s to 243s, p44-p50)
sf.write("scratch/nianlun_chorus3_vocal.wav", vocal_audio[int(206.0 * sr) : int(243.0 * sr)], sr)
sf.write("scratch/nianlun_chorus3_mix.wav", mix_audio[int(206.0 * sr) : int(243.0 * sr)], sr)

# 5. Create project_with_accompaniment.ustx
proj_data = yaml.safe_load(proj_path.read_text(encoding="utf-8"))
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
print("Nianlun compile, render, mix, slices, and project_with_accompaniment completed successfully!")
