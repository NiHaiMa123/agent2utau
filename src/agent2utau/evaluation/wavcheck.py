"""Rendered-WAV structural checks: non-silence, duration, clipping, NaN."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

import numpy as np


def analyze_wav(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    with wave.open(str(p), "rb") as w:
        n_ch = w.getnchannels()
        sw = w.getsampwidth()
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        a = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sw == 1:
        a = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128.0
    else:
        raise ValueError(f"unsupported sample width {sw}")
    if n_ch > 1:
        a = a.reshape(-1, n_ch).mean(axis=1)
    dur = len(a) / sr
    peak = float(np.max(np.abs(a))) if len(a) else 0.0
    rms = float(np.sqrt(np.mean(a ** 2))) if len(a) else 0.0
    nan = int(np.isnan(a).sum())
    # voiced fraction: windows above -50dBFS rms
    win = max(1, int(0.02 * sr))
    m = len(a) // win * win
    frames = a[:m].reshape(-1, win)
    wrms = np.sqrt(np.mean(frames ** 2, axis=1))
    voiced = float((wrms > 10 ** (-50 / 20)).mean())
    return {
        "file": str(p),
        "sample_rate": sr,
        "channels": n_ch,
        "duration_s": round(dur, 3),
        "peak": round(peak, 5),
        "rms": round(rms, 6),
        "nan_count": nan,
        "voiced_fraction": round(voiced, 4),
        "non_silent": peak > 1e-4 and voiced > 0.05,
        "clipping": peak >= 0.999,
    }
