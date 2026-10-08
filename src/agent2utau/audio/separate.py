"""Source separation with the user-selected, project-local MelBand Roformer."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "vocals_mel_band_roformer.ckpt"
MODEL_DIR = Path(__file__).resolve().parents[3] / "models/separation/melband_roformer"
CONFIG_FILE = "vocals_mel_band_roformer.yaml"


def separation_settings(model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """Bind new cache identity to the selected local weights, YAML and runtime."""
    from importlib.metadata import version
    settings = {"model": model, "output_format": "WAV",
                "sample_rate": 44100, "normalization_threshold": 0.9,
                "audio_separator_version": version("audio-separator")}
    if model == DEFAULT_MODEL:
        manifest = json.loads((MODEL_DIR / "manifest.json").read_text(encoding="utf-8"))
        for filename in (DEFAULT_MODEL, CONFIG_FILE, "download_checks.json"):
            path = MODEL_DIR / filename
            if not path.is_file() or _sha256(path) != manifest["files"][filename]["sha256"]:
                raise RuntimeError(f"Selected separator bundle missing or changed: {path}")
        settings.update(model_path=str(MODEL_DIR / model),
                        model_sha256=manifest["files"][model]["sha256"],
                        config_path=str(MODEL_DIR / CONFIG_FILE),
                        config_sha256=manifest["files"][CONFIG_FILE]["sha256"],
                        backend="pytorch-auto", mdxc_params={"batch_size": 1,
                        "segment_size": 256, "override_model_segment_size": False,
                        "overlap": None, "pitch_shift": 0})
    else:
        settings["backend"] = "audio-separator-explicit-model"
    return settings


def separation_cache_key(source_sha256: str, settings: dict[str, Any]) -> str:
    """Different source/model/config/runtime conditions get separate artifacts."""
    value = json.dumps({"source_sha256": source_sha256, "settings": settings},
                       sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def separate(wav_path: str | Path, out_dir: Path,
             model: str = DEFAULT_MODEL) -> dict[str, Any]:
    from audio_separator.separator import Separator  # deferred: heavy import

    settings = separation_settings(model)
    out_dir.mkdir(parents=True, exist_ok=True)
    options = dict(output_dir=str(out_dir), output_format=settings["output_format"],
                   sample_rate=settings["sample_rate"],
                   normalization_threshold=settings["normalization_threshold"], log_level=40)
    if model == DEFAULT_MODEL:
        options.update(model_file_dir=str(MODEL_DIR), mdxc_params=settings["mdxc_params"])
    sep = Separator(**options)
    if model == DEFAULT_MODEL and Path(sep.model_file_dir).resolve() != MODEL_DIR.resolve():
        raise RuntimeError("AUDIO_SEPARATOR_MODEL_DIR overrides the selected local model bundle")
    sep.load_model(model)
    outs = sep.separate(str(wav_path))
    stems = {}
    for o in outs:
        p = out_dir / o if not os.path.isabs(o) else Path(o)
        label = str(o).casefold()
        if "(vocals)" in label:
            stems["vocals"] = p
        elif "(instrumental)" in label or "(other)" in label:
            stems["instrumental"] = p
    if "vocals" not in stems or "instrumental" not in stems:
        raise RuntimeError(f"unexpected separator outputs: {outs}")
    model_file = Path(sep.model_instance.model_path) \
        if getattr(sep, "model_instance", None) else None
    return {
        "vocals": str(stems["vocals"]),
        "instrumental": str(stems["instrumental"]),
        "model": model,
        "model_path": str(model_file) if model_file else None,
        "model_sha256": _sha256(model_file) if model_file and model_file.exists() else None,
        "backend": ("pytorch-" + str(sep.model_instance.torch_device)
                    if model == DEFAULT_MODEL else settings["backend"]),
        "model_friendly_name": getattr(sep, "model_friendly_name", model),
        "config_path": settings.get("config_path"),
        "config_sha256": settings.get("config_sha256"),
        "settings": settings,
        "source_sha256": _sha256(Path(wav_path)),
    }


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
