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

MIN_NOTE_SEC = 0.09          # shorter fragments get merged into a neighbour
SPLIT_SEMITONES = 1.0        # sustained step that triggers a char split
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
    ts, hz, uv = f0["times"], f0["f0_hz"], f0["voiced"]
    runs, cur = [], [idx[0], idx[0]]
    ref = None
    for i in idx:
        v = hz_to_midi(np.array([hz[i]]))[0] if uv[i] else None
        if ref is None and v is not None:
            ref = v
        if v is not None and ref is not None and abs(v - ref) >= SPLIT_SEMITONES:
            runs.append(cur); cur = [i, i]; ref = v
        else:
            cur[1] = i
            if v is not None and ref is not None:
                ref = 0.7 * ref + 0.3 * v  # track slow drift
    runs.append(cur)
    frame = float(ts[1] - ts[0])
    segs = [{"start": float(ts[r[0]]), "end": float(ts[r[1]]) + frame}
            for r in runs]
    segs[0]["start"], segs[-1]["end"] = t0, t1
    # merge too-short fragments into the longer neighbour
    merged = []
    for s in segs:
        if merged and s["end"] - s["start"] < MIN_NOTE_SEC:
            prev = merged[-1]
            if prev["end"] - prev["start"] >= s["end"] - s["start"]:
                prev["end"] = s["end"]; continue
            prev_start = prev["start"]; merged[-1] = s
            merged[-1]["start"] = prev_start; continue
        merged.append(s)
    return merged


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
                "dur": round(max(0.03, s["end"] - s["start"]), 4),
                "tone": max(24, min(96, tone)),
                "conf": conf,
                "voiced_frac": round(frac, 3),
            })
            prev_tone = notes[-1]["tone"]
    return notes, prev_tone
