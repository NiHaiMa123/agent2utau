"""Mix rendered vocal (mono) over instrumental (stereo) on the same timeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def mix(vocal_wav: str | Path, accomp_wav: str | Path, out_wav: Path,
        vocal_gain_db: float = 0.0, accomp_gain_db: float = 0.0,
        headroom_db: float = -1.0) -> dict:
    v, vsr = sf.read(str(vocal_wav), dtype="float32")
    a, asr = sf.read(str(accomp_wav), dtype="float32")
    if vsr != asr:
        import librosa
        v = librosa.resample(v.T, orig_sr=vsr, target_sr=asr).T
        vsr = asr
    if v.ndim == 1:
        v = np.stack([v, v], axis=1)
    if a.ndim == 1:
        a = np.stack([a, a], axis=1)
    n = max(len(v), len(a))
    def pad(x):
        return np.vstack([x, np.zeros((n - len(x), x.shape[1]), np.float32)])
    v, a = pad(v), pad(a)
    v *= 10 ** (vocal_gain_db / 20)
    a *= 10 ** (accomp_gain_db / 20)
    out = v + a
    peak = float(np.abs(out).max())
    ceiling = 10 ** (headroom_db / 20)
    if peak > ceiling:
        out *= ceiling / peak
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_wav), out, vsr, subtype="PCM_16")
    return {"out": str(out_wav), "sr": vsr, "dur_s": n / vsr,
            "peak": round(float(np.abs(out).max()), 4),
            "normalized": peak > ceiling}
