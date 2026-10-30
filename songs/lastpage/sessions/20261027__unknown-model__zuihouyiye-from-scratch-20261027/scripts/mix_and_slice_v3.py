import json
from pathlib import Path
import numpy as np
import soundfile as sf
import yaml

from agent2utau.audio.mix import mix

run_dir = Path(r"E:\project\agent2utau\runs\production\zuihouyiye-from-scratch-20261027")
obs_dir = run_dir / "observation"
render_dir = run_dir / "render_v3"
scratch_dir = Path(r"C:\Users\Administrator\.gemini\antigravity\brain\b2b81b71-bb8d-4b65-85f8-9e23b357ea81\scratch")


def main():
    vocal_wav = render_dir / "vocal_vocal.wav"
    if not vocal_wav.exists():
        vocal_wav = render_dir / "vocal.wav"
    assert vocal_wav.exists(), f"Rendered vocal not found: {vocal_wav}"

    accomp_wav = obs_dir / "stems" / "source_(other)_vocals_mel_band_roformer.wav"
    mix_path = render_dir / "zuihouyiye_lingyuan_cover_mix_v3.wav"

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

    print("Mix v3 result:", json.dumps(mix_res, ensure_ascii=False))

    mix_audio, sr = sf.read(str(mix_path), dtype="float32")
    vocal_audio, _ = sf.read(str(vocal_wav), dtype="float32")
    if vocal_audio.ndim > 1:
        vocal_audio = vocal_audio.mean(axis=1)

    first_half_mix = mix_audio[int(13.5 * sr) : int(102.0 * sr)]
    sf.write(str(render_dir / "first_half_mix_v3.wav"), first_half_mix, sr)

    slices_dir = scratch_dir / "baishuo_audio" / "slices"
    manifest = json.loads((run_dir / "hfa_inputs" / "slices_manifest.json").read_text(encoding="utf-8"))
    items = manifest["phrases"][:16]

    for gi in range(4):
        g_items = items[gi * 4 : (gi + 1) * 4]
        s0 = max(0.0, float(g_items[0]["slice_start_s"]))
        s1 = float(g_items[-1]["slice_end_s"])
        sf.write(str(slices_dir / f"g{gi+1}_ours_v3.wav"), vocal_audio[int(s0 * sr) : int(s1 * sr)], sr, subtype="PCM_16")

    proj_data = yaml.safe_load((run_dir / "compiled_v3" / "project.ustx").read_text(encoding="utf-8"))
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
    print("Sliced first half and created project_with_accompaniment.ustx for v3 successfully!")


if __name__ == "__main__":
    main()
