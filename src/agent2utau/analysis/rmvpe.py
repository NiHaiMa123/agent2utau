"""RMVPE pitch estimation via the OpenUtau-bundled onnx model.

Matches OpenUtau.Core/Analysis/Rmvpe.cs: resample to 16 kHz, hop 160
(10 ms frames), threshold 0.03, model `uv` output 1 = UNVOICED.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

SAMPLE_RATE = 16000
HOP = 160
THRESHOLD = 0.03


def infer_rmvpe(wav_path: str | Path,
                model_path: str | Path | None = None,
                threshold: float = THRESHOLD) -> dict[str, Any]:
    import onnxruntime as ort
    wav, sr = sf.read(str(wav_path), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sr != SAMPLE_RATE:
        import librosa
        wav = librosa.resample(wav, orig_sr=sr, target_sr=SAMPLE_RATE)
    if model_path is None:
        model_path = _default_model()
    sess = ort.InferenceSession(str(model_path),
                                providers=["CPUExecutionProvider"])
    f0, uv = sess.run(None, {
        "waveform": np.clip(wav, -1, 1)[None, :].astype(np.float32),
        "threshold": np.array(threshold, dtype=np.float32)})
    f0 = np.asarray(f0[0], dtype=np.float32)
    voiced = ~np.asarray(uv[0], dtype=bool)  # uv==1 means UNVOICED
    n = min(len(f0), len(voiced))
    times = np.arange(n) * HOP / SAMPLE_RATE
    return {"schema_version": "1", "backend": "rmvpe-onnx",
            "sr": SAMPLE_RATE, "hop": HOP, "frame_ms": 10.0,
            "n_frames": n, "f0_hz": f0[:n], "voiced": voiced[:n],
            "times": times.astype(np.float32)}


def _default_model() -> Path:
    import os
    for root in (os.environ.get("OPENUTAU_DIR"),
                 r"E:\software\OpenUtau-win-x64 (6)"):
        if root:
            for sub in ("rmvpe/rmvpe.onnx", "RMVPE/rmvpe.onnx"):
                p = Path(root) / "Dependencies" / sub
                if p.exists():
                    return p
    raise FileNotFoundError("rmvpe.onnx not installed")
