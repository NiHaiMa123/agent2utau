"""ASR timing + F0 → note events (melisma-aware).

Each Hanzi char becomes 1..N notes. Within a char's window, F0 median in
overlapping windows is compared; a pitch change >= SPLIT_SEMITONES sustained
for >= MIN_NOTE_SEC splits the char into multiple notes (lyric "+" for
continuations). Unvoiced/uncertain chars still emit a note at the nearest
voiced median or the char's context pitch — flagged low confidence.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .f0 import hz_to_midi

MIN_NOTE_SEC = 0.09          # minimum sustained stable region for a split
SPLIT_SEMITONES = 1.25       # sustained step that triggers a char split
MIN_VOICED_FOR_PITCH = 0.35  # below this the note keeps context pitch
DEFAULT_TONE = 60            # C4 fallback


def _seg_pitch(f0: dict, t0: float, t1: float) -> tuple[float | None, float]:
    m = (f0["times"] >= t0) & (f0["times"] < t1) & f0["voiced"]
    total = max(1, int(((f0["times"] >= t0) & (f0["times"] < t1)).sum()))
    frac = float(m.sum() / total)
    if m.sum() < 3:
        return None, frac
    return float(np.median(hz_to_midi(f0["f0_hz"][m]))), frac


def _split_char(f0: dict, t0: float, t1: float) -> list[dict]:
    """Split [t0,t1] into runs of near-constant pitch (melisma)."""
    m = (f0["times"] >= t0) & (f0["times"] < t1)
    idx = np.where(m)[0]
    if idx.size < 3:
        return [{"start": t0, "end": t1}]
    from scipy.ndimage import median_filter
    ts, hz, uv = f0["times"], f0["f0_hz"], f0["voiced"]
    valid = idx[uv[idx]]
    if valid.size < 3:
        return [{"start": t0, "end": t1}]
    frame = float(ts[1] - ts[0])
    # Interpolation only helps segmentation within this already aligned
    # syllable; note pitch/confidence still uses original voiced frames.
    pitch = np.interp(ts[idx], ts[valid], hz_to_midi(hz[valid]))
    width = max(3, int(round(0.05 / frame)) | 1)
    pitch = median_filter(pitch, size=width, mode="nearest")
    hold = max(3, int(np.ceil(MIN_NOTE_SEC / frame)))
    base = float(np.median(pitch[:hold]))
    boundaries, last = [t0], 0
    j = hold
    while j + hold <= len(idx):
        candidate = pitch[j:j + hold]
        center = float(np.median(candidate))
        # A single leap or a vibrato half-cycle must not create a new note.
        if (j - last >= hold and abs(center - base) >= SPLIT_SEMITONES
                and np.max(np.abs(candidate - center)) < 0.65
                and t1 - float(ts[idx[j]]) >= MIN_NOTE_SEC):
            boundaries.append(float(ts[idx[j]]))
            base, last = center, j
            j += hold
        else:
            j += 1
    boundaries.append(t1)
    return [{"start": a, "end": b} for a, b in zip(boundaries, boundaries[1:])]


def build_notes(chars: list[dict], f0: dict, prev_tone: int = DEFAULT_TONE
                ) -> tuple[list[dict], int]:
    """chars: [{'char','start','end'}] (seconds). Returns (notes, last_tone)."""
    notes = []
    for ch in chars:
        sub = _split_char(f0, ch["start"], ch["end"])
        for j, s in enumerate(sub):
            midi, frac = _seg_pitch(f0, s["start"], s["end"])
            conf = "voiced" if frac >= MIN_VOICED_FOR_PITCH and midi is not None \
                else "weak"
            tone = int(round(midi)) if midi is not None else prev_tone
            notes.append({
                "lyric": ch["char"] if j == 0 else "+",
                "start": round(s["start"], 4),
                "end": round(s["end"], 4),
                "dur": round(max(0.03, s["end"] - s["start"]), 4),
                "tone": max(24, min(96, tone)),
                "conf": conf,
                "voiced_frac": round(frac, 3),
            })
            prev_tone = notes[-1]["tone"]
    return notes, prev_tone
