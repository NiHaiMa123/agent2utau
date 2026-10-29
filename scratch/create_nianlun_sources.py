import hashlib
import json
from pathlib import Path

run_dir = Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
obs_dir = run_dir / "observation"
hfa_dir = run_dir / "hfa"
design_dir = run_dir / "design"

def sha256_f(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

flac_path = Path(r"E:\data\music\年轮 - 张碧晨.flac")

sources = [
    {
        "id": "source_flac",
        "role": "source_observation",
        "file": {
            "path": str(flac_path),
            "sha256": sha256_f(flac_path),
        },
        "description": "Original input FLAC audio of 张碧晨《年轮》."
    },
    {
        "id": "source_wav",
        "role": "source_observation",
        "file": {
            "path": str(obs_dir / "source.wav"),
            "sha256": sha256_f(obs_dir / "source.wav"),
        },
        "description": "Decoded PCM WAV from the original FLAC."
    },
    {
        "id": "separated_vocal",
        "role": "source_observation",
        "file": {
            "path": str(obs_dir / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"),
            "sha256": sha256_f(obs_dir / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"),
        },
        "description": "Separated dry vocal stem from MelBand Roformer."
    },
    {
        "id": "separated_inst",
        "role": "source_observation",
        "file": {
            "path": str(obs_dir / "stems" / "source_(other)_vocals_mel_band_roformer.wav"),
            "sha256": sha256_f(obs_dir / "stems" / "source_(other)_vocals_mel_band_roformer.wav"),
        },
        "description": "Separated instrumental backing track stem from MelBand Roformer."
    },
    {
        "id": "asr_obs",
        "role": "source_observation",
        "file": {
            "path": str(obs_dir / "asr.json"),
            "sha256": sha256_f(obs_dir / "asr.json"),
        },
        "description": "Whisper ASR transcription segments."
    },
    {
        "id": "game_obs",
        "role": "source_observation",
        "file": {
            "path": str(obs_dir / "game.json"),
            "sha256": sha256_f(obs_dir / "game.json"),
        },
        "description": "GAME transcription notes."
    },
    {
        "id": "fcpe_obs",
        "role": "source_observation",
        "file": {
            "path": str(obs_dir / "fcpe.npz"),
            "sha256": sha256_f(obs_dir / "fcpe.npz"),
        },
        "description": "FCPE frame-level pitch extraction."
    },
    {
        "id": "rmvpe_obs",
        "role": "source_observation",
        "file": {
            "path": str(obs_dir / "rmvpe.npz"),
            "sha256": sha256_f(obs_dir / "rmvpe.npz"),
        },
        "description": "RMVPE frame-level pitch extraction."
    },
    {
        "id": "hfa_summary",
        "role": "source_observation",
        "file": {
            "path": str(hfa_dir / "hfa_summary.json"),
            "sha256": sha256_f(hfa_dir / "hfa_summary.json"),
        },
        "description": "HubertFA forced alignment word and phone boundaries."
    },
    {
        "id": "score_ustx",
        "role": "source_observation",
        "file": {
            "path": str(design_dir / "score.ustx"),
            "sha256": sha256_f(design_dir / "score.ustx"),
        },
        "description": "Initial score project for OpenUtau with 51 phrases."
    },
    {
        "id": "baseline_pitch",
        "role": "source_observation",
        "file": {
            "path": str(design_dir / "baseline_pitch.json"),
            "sha256": sha256_f(design_dir / "baseline_pitch.json"),
        },
        "description": "Exported baseline pitch curves from OpenUtau Core."
    },
    {
        "id": "baseline_phones",
        "role": "source_observation",
        "file": {
            "path": str(design_dir / "baseline_phones.json"),
            "sha256": sha256_f(design_dir / "baseline_phones.json"),
        },
        "description": "Exported baseline phoneme timings from OpenUtau Core."
    },
    {
        "id": "native_provenance",
        "role": "source_observation",
        "file": {
            "path": str(design_dir / "native_provenance.json"),
            "sha256": sha256_f(design_dir / "native_provenance.json"),
        },
        "description": "Native environment and asset provenance receipt."
    },
]

sources_doc = {"schema_version": 1, "sources": sources}
out_file = design_dir / "sources.json"
out_file.write_text(json.dumps(sources_doc, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {out_file} with {len(sources)} sources.")
