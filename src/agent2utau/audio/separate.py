"""Vocal/instrumental separation via audio-separator (ONNX, CPU path).

Model choice is locked here; the resolved model file + hash are recorded in
the run manifest. Works on CPU; GPU provider can be added later without
changing callers.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

# Verified working on this machine's CPU; BS-Roformer/DirectML upgrades are M2+.
DEFAULT_MODEL = "UVR-MDX-NET-Voc_FT.onnx"


def separate(wav_path: str | Path, out_dir: Path,
             model: str = DEFAULT_MODEL) -> dict[str, Any]:
    from audio_separator.separator import Separator  # deferred: heavy import

    out_dir.mkdir(parents=True, exist_ok=True)
    sep = Separator(output_dir=str(out_dir), output_format="WAV", log_level=40)
    sep.load_model(model)
    outs = sep.separate(str(wav_path))
    stems = {}
    for o in outs:
        p = out_dir / o if not os.path.isabs(o) else Path(o)
        if "(Vocals)" in o:
            stems["vocals"] = p
        elif "(Instrumental)" in o:
            stems["instrumental"] = p
    if "vocals" not in stems or "instrumental" not in stems:
        raise RuntimeError(f"unexpected separator outputs: {outs}")
    model_file = Path(sep.model_instance.model_path) \
        if getattr(sep, "model_instance", None) else None
    return {
        "vocals": str(stems["vocals"]),
        "instrumental": str(stems["instrumental"]),
        "model": model,
        "model_sha256": _sha256(model_file) if model_file and model_file.exists() else None,
        "backend": "onnxruntime-cpu",
    }


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
