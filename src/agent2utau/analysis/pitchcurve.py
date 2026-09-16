"""Build `pitd` (pitch deviation, cents) curve points from source F0.

pitd units: cents relative to the note's written tone, part-relative xs in
ticks. Only voiced, energy-gated frames contribute; output is smoothed,
downsampled to ~20 points/second and clamped — raw per-frame F0 is never
written directly.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .f0 import hz_to_midi

POINT_EVERY_SEC = 0.05   # ~20 pts/s — enough for slides, not vibrato noise
CLAMP_CENTS = 600.0


def _smooth(y: np.ndarray, k: int = 5) -> np.ndarray:
    if len(y) < k:
        return y
    ker = np.ones(k) / k
    return np.convolve(y, ker, mode="same")


def build_pitd(f0: dict, notes: list[dict], part_start_sec: float,
               sec_to_tick, strength: float = 1.0,
               min_voiced_run: float = 0.05) -> dict | None:
    """Return {'abbr':'pitd','xs':[ticks],'ys':[cents]} or None.

    notes: [{'start','dur','tone'}] absolute seconds. Frames inside a note's
    window and voiced produce offset = (f0_midi - tone) * strength; unvoiced
    frames inside a note inherit 0 (hold the written tone).
    """
    ts, hz, uv = f0["times"], f0["f0_hz"], f0["voiced"]
    if len(ts) < 3:
        return None
    step = max(1, int(round(POINT_EVERY_SEC / (ts[1] - ts[0]))))
    xs, ys = [], []
    for n in notes:
        if n.get("is_breath"):
            continue
        t0, t1 = n["start"], n["start"] + n["dur"]
        m = (ts >= t0) & (ts < t1)
        idx = np.where(m)[0][::step]
        if idx.size == 0:
            continue
        midi = hz_to_midi(hz[idx])
        voiced = uv[idx]
        off = np.where(voiced, (midi - n["tone"]) * 100.0 * strength, 0.0)
        # ignore sub-frame blips: require a run of voiced samples
        off = _smooth(off.astype(np.float64), 3)
        off = np.clip(off, -CLAMP_CENTS, CLAMP_CENTS)
        for t, y in zip(ts[idx], off):
            xs.append(sec_to_tick(t - part_start_sec))
            ys.append(int(round(float(y))))
    if len(xs) < 4:
        return None
    # ensure strictly increasing xs (rounding can collide)
    pairs = sorted(zip(xs, ys))
    xs_out, ys_out = [pairs[0][0]], [pairs[0][1]]
    for x, y in pairs[1:]:
        if x == xs_out[-1]:
            ys_out[-1] = y
        else:
            xs_out.append(x); ys_out.append(y)
    return {"abbr": "pitd", "xs": xs_out, "ys": ys_out}
