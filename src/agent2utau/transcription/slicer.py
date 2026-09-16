"""Port of OpenUtau's AudioSlicer (which itself ports openvpi/audio-slicer
slicer2.py). Splits a waveform on silence into chunks with offsets.

Parameters match OpenUtau.Core/Analysis/AudioSlicer.cs exactly.
"""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 44100
THRESHOLD = 0.02
HOP = 441
WIN = 1764
MIN_LENGTH = 100       # frames
MIN_INTERVAL = 20      # frames
MAX_SIL_KEPT = 10      # frames


def _rms(samples: np.ndarray) -> np.ndarray:
    y = np.pad(samples.astype(np.float64) ** 2, (WIN // 2, WIN // 2))
    n = len(samples) // HOP
    idx = np.arange(n)[:, None] * HOP + np.arange(WIN)[None, :]
    return np.sqrt(y[idx].mean(axis=1))


def slice_audio(samples: np.ndarray) -> list[tuple[float, np.ndarray]]:
    """Return [(offset_ms, chunk_samples)]."""
    if (len(samples) + HOP - 1) // HOP <= MIN_LENGTH:
        return [(0.0, samples)]
    rms = _rms(samples)
    sil_tags: list[tuple[int, int]] = []
    silence_start = -1
    clip_start = 0
    for i, r in enumerate(rms):
        if r < THRESHOLD:
            if silence_start < 0:
                silence_start = i
            continue
        if silence_start < 0:
            continue
        is_leading = silence_start == 0 and i > MAX_SIL_KEPT
        need_mid = (i - silence_start >= MIN_INTERVAL
                    and i - clip_start >= MIN_LENGTH)
        if not is_leading and not need_mid:
            silence_start = -1
            continue
        if i - silence_start <= MAX_SIL_KEPT:
            pos = int(np.argmin(rms[silence_start:i + 1])) + silence_start
            sil_tags.append((0, pos) if silence_start == 0 else (pos, pos))
            clip_start = pos
        elif i - silence_start <= MAX_SIL_KEPT * 2:
            pos = int(np.argmin(
                rms[i - MAX_SIL_KEPT:silence_start + MAX_SIL_KEPT + 1]))
            pos += i - MAX_SIL_KEPT
            pos_l = int(np.argmin(
                rms[silence_start:silence_start + MAX_SIL_KEPT + 1])
            ) + silence_start
            pos_r = int(np.argmin(rms[i - MAX_SIL_KEPT:i + 1])) \
                + i - MAX_SIL_KEPT
            if silence_start == 0:
                sil_tags.append((0, pos_r))
                clip_start = pos_r
            else:
                sil_tags.append((min(pos_l, pos), max(pos_r, pos)))
                clip_start = max(pos_r, pos)
        else:
            pos_l = int(np.argmin(
                rms[silence_start:silence_start + MAX_SIL_KEPT + 1])
            ) + silence_start
            pos_r = int(np.argmin(rms[i - MAX_SIL_KEPT:i + 1])) \
                + i - MAX_SIL_KEPT
            if silence_start == 0:
                sil_tags.append((0, pos_r))
            else:
                sil_tags.append((pos_l, pos_r))
            clip_start = pos_r
        silence_start = -1

    total = len(rms)
    if silence_start >= 0 and total - silence_start >= MIN_INTERVAL:
        end = min(total, silence_start + MAX_SIL_KEPT)
        pos = int(np.argmin(rms[silence_start:end + 1])) + silence_start
        sil_tags.append((pos, total + 1))

    if not sil_tags:
        return [(0.0, samples)]
    spans = []
    if sil_tags[0][0] > 0:
        spans.append((0, sil_tags[0][0] * HOP))
    for a, b in zip(sil_tags, sil_tags[1:]):
        spans.append((a[1] * HOP, b[0] * HOP))
    if sil_tags[-1][1] < total:
        spans.append((sil_tags[-1][1] * HOP, total * HOP))
    return [(s / SAMPLE_RATE * 1000.0, samples[s:e]) for s, e in spans]
