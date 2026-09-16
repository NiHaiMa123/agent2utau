"""Mix rendered vocal (mono) over instrumental (stereo) on the same timeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def mix(vocal_wav: str | Path, accomp_wav: str | Path, out_wav: Path,
        vocal_gain_db: float = 0.0, accomp_gain_db: float = 0.0,
        headroom_db: float = -1.0,
        reference_vocal: str | Path | None = None,
        auto_balance: bool = True, min_vocal_to_accomp_db: float = -3.0) -> dict:
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
    balance = {}
    if auto_balance:
        # Measure matching active 400ms windows: whole-file RMS would count
        # the intro/interlude as weak singing and over-amplify the vocal.
        hop = max(1, round(asr * 0.4))
        def levels(x):
            energy = np.mean(x.astype(np.float64) ** 2, axis=1)
            return np.array([np.sqrt(energy[i:i + hop].mean())
                             for i in range(0, n, hop)])
        vr, ar = levels(v), levels(a)
        active = vr > max(10 ** (-45 / 20), float(vr.max()) * 0.08)
        if active.sum() >= 2:
            vdb = 20 * np.log10(np.maximum(vr[active], 1e-8))
            adb = 20 * np.log10(np.maximum(ar[active], 1e-8)) + accomp_gain_db
            target = adb + min_vocal_to_accomp_db
            if reference_vocal is not None:
                ref, rsr = sf.read(str(reference_vocal), dtype="float32", always_2d=True)
                if rsr != asr:
                    import librosa
                    ref = librosa.resample(ref.T, orig_sr=rsr, target_sr=asr).T
                ref = ref[:n]
                ref = np.pad(ref, ((0, max(0, n - len(ref))), (0, 0)))
                rdb = 20 * np.log10(np.maximum(levels(ref)[active], 1e-8))
                target = np.maximum(target, rdb)
            requested = float(np.median(target - vdb))
            auto_gain = float(np.clip(requested, -18.0, 24.0))
            vocal_gain_db += auto_gain
            balance = {"active_windows": int(active.sum()),
                       "auto_vocal_gain_db": round(auto_gain, 3),
                       "gain_limited": abs(requested - auto_gain) > 0.01,
                       "vocal_to_accomp_before_db": round(float(np.median(vdb - adb)), 3),
                       "vocal_to_accomp_after_db": round(float(np.median(vdb - adb)) + vocal_gain_db, 3)}
        else:
            balance = {"active_windows": int(active.sum()), "warning": "insufficient_vocal"}
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
            "normalized": peak > ceiling,
            "vocal_gain_db": round(vocal_gain_db, 3),
            "accomp_gain_db": accomp_gain_db,
            "master_gain_db": round(20 * np.log10(ceiling / peak), 3) if peak > ceiling else 0.0,
            "balance": balance}
