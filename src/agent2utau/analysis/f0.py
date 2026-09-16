"""F0 extraction. Primary backend: torchfcpe (bundled CFNaiveMelPE, CPU).

Returns per-frame {f0_hz, uv(voiced flag), times}. Units documented:
f0 in Hz, times in seconds, sr/hop recorded for downstream conversion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

_FCPE = None


def _fcpe(device: str = "cpu"):
    global _FCPE
    if _FCPE is None:
        import torchfcpe
        _FCPE = torchfcpe.spawn_bundled_infer_model(device=device)
    return _FCPE


def extract_f0(wav_path: str | Path, device: str = "cpu",
               f0_min: float = 65.0, f0_max: float = 1100.0,
               threshold: float = 0.006) -> dict[str, Any]:
    import torch
    wav, sr = sf.read(str(wav_path), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sr != 44100:
        import librosa
        wav = librosa.resample(wav, orig_sr=sr, target_sr=44100)
        sr = 44100
    # torchfcpe prints INFO/WARN to stdout — keep CLI stdout JSON-clean
    import contextlib, sys
    with contextlib.redirect_stdout(sys.stderr):
        model = _fcpe(device)
        hop = model.get_hop_size()
        wav_t = torch.from_numpy(wav[None, :])
        n_frames = int(np.ceil(len(wav) / hop)) + 1
        out = model.infer(wav_t, sr=sr, decoder_mode="local_argmax",
                          threshold=threshold, f0_min=f0_min, f0_max=f0_max,
                          interp_uv=True, retur_uv=True,
                          output_interp_target_length=n_frames)
    f0, uv = out if isinstance(out, tuple) else (out, out > 0)
    f0 = np.asarray(f0.cpu()).squeeze()
    uv = np.asarray(uv.cpu()).squeeze() > 0.5
    assert f0.ndim == 1 and uv.ndim == 1, (f0.shape, uv.shape)
    n = min(n_frames, len(f0), len(uv))
    f0 = f0[:n]; uv = uv[:n]
    times = np.arange(n) * hop / sr
    return {
        "schema_version": "1",
        "backend": f"torchfcpe:{type(model).__name__}",
        "device": device,
        "sr": sr,
        "hop": hop,
        "frame_ms": hop / sr * 1000.0,
        "n_frames": n,
        "f0_hz": f0.astype(np.float32),
        "voiced": uv.astype(bool),
        "times": times.astype(np.float32),
    }


def segment_f0(f0: dict[str, Any], t0: float, t1: float) -> dict[str, Any]:
    """Slice [t0,t1] seconds; times rebased to 0."""
    i0 = int(np.searchsorted(f0["times"], t0))
    i1 = int(np.searchsorted(f0["times"], t1))
    return {
        **{k: v for k, v in f0.items()
           if k not in ("f0_hz", "voiced", "times", "n_frames")},
        "n_frames": i1 - i0,
        "f0_hz": f0["f0_hz"][i0:i1],
        "voiced": f0["voiced"][i0:i1],
        "times": f0["times"][i0:i1] - t0,
    }


def hz_to_midi(hz: np.ndarray) -> np.ndarray:
    return 69.0 + 12.0 * np.log2(np.maximum(hz, 1e-6) / 440.0)


def median_note_midi(f0: dict, t0: float, t1: float,
                     min_voiced: float = 0.4) -> tuple[float | None, float]:
    """Median MIDI of voiced frames in [t0,t1]; returns (midi, voiced_frac)."""
    m = (f0["times"] >= t0) & (f0["times"] < t1) & f0["voiced"]
    total = max(1, int(((f0["times"] >= t0) & (f0["times"] < t1)).sum()))
    frac = m.sum() / total
    if frac < min_voiced or m.sum() < 3:
        return None, float(frac)
    return float(np.median(hz_to_midi(f0["f0_hz"][m]))), float(frac)
