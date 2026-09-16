"""Voiced-block and syllable-onset detection on a separated vocal stem.

Blocks = contiguous voiced regions split by gaps >= gap (roughly lyric
phrases). "Voiced" = f0 uv AND short-term RMS above gate (instrumental
leakage can be pitched but is quiet). Within a block, librosa onset_detect
finds syllable onsets. These replace ASR word times when lyrics come from
an LRC/reference file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

GAP_SEC = 0.9
MIN_BLOCK_SEC = 0.6
RMS_GATE_DB = -42.0
RMS_WIN = 2048


def frame_rms(wav: np.ndarray, sr: int, times: np.ndarray,
              win: int = RMS_WIN) -> np.ndarray:
    """RMS of wav at each frame time (seconds), aligned to `times`."""
    c = np.concatenate([[0.0], np.cumsum(wav.astype(np.float64) ** 2)])
    i0 = np.minimum((times * sr).astype(np.int64), len(wav) - 1)
    i1 = np.minimum(i0 + win, len(wav))
    return np.sqrt(np.maximum((c[i1] - c[i0]) / np.maximum(i1 - i0, 1), 0))


def gate_voiced(f0: dict, rms: np.ndarray,
                gate_db: float = RMS_GATE_DB) -> dict:
    """Return f0 copy with voiced &= rms > gate."""
    return {**f0, "voiced": f0["voiced"] & (rms > 10 ** (gate_db / 20))}


def voiced_blocks(f0: dict, gap: float = GAP_SEC,
                  min_len: float = MIN_BLOCK_SEC) -> list[tuple[float, float]]:
    """Merge voiced f0 frames into [start,end] second blocks."""
    ts, uv = f0["times"], f0["voiced"]
    idx = np.where(uv)[0]
    if idx.size == 0:
        return []
    frame = float(ts[1] - ts[0]) if len(ts) > 1 else 0.01
    blocks, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if ts[i] - ts[prev] > gap:
            blocks.append((float(ts[s]), float(ts[prev]) + frame))
            s = i
        prev = i
    blocks.append((float(ts[s]), float(ts[prev]) + frame))
    return [b for b in blocks if b[1] - b[0] >= min_len]


def voiced_extent(f0: dict, t0: float, t1: float,
                  pad: float = 0.15) -> tuple[float, float] | None:
    """Actual voiced extent inside window [t0,t1], padded."""
    ts, uv = f0["times"], f0["voiced"]
    m = (ts >= t0) & (ts < t1) & uv
    idx = np.where(m)[0]
    if idx.size == 0:
        return None
    frame = float(ts[1] - ts[0]) if len(ts) > 1 else 0.01
    return max(t0, float(ts[idx[0]]) - pad), min(t1, float(ts[idx[-1]])
                                                 + frame + pad)


def detect_onsets(wav_path: str | Path, t0: float, t1: float) -> list[float]:
    """Onset times (seconds, absolute) within [t0,t1] of the vocal wav."""
    import librosa
    wav, sr = sf.read(str(wav_path), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    i0, i1 = int(t0 * sr), min(len(wav), int(t1 * sr))
    clip = wav[i0:i1]
    if len(clip) < sr // 4:
        return []
    on = librosa.onset.onset_detect(
        y=clip, sr=sr, hop_length=512, units="time",
        backtrack=True, delta=0.05, wait=3)
    times = [t0 + float(o) for o in on]
    if not times or times[0] - t0 > 0.25:
        times.insert(0, t0)
    return sorted(times)
