"""Variant D: keep the model contour, correct each note's offset to the singer.

Why: the auto-pitch render reproduces its own score almost exactly (|d| 0.9c),
so the residual error is the score's semitone quantisation, not the predictor.
A per-note PITD offset (source median minus score tone) moves each note onto the
sung pitch while keeping the model's within-note shape. This is the same manual
step a person does in OpenUtau after "load rendered pitch".
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))

RUN = REPO / "runs/experiments/nianlun-autopitch-fix-20261030"
SRC_USTX = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"
OBS = REPO / "runs/production/nianlun-from-scratch-v3-20261030/observation"
TICK_MS = 60000.0 / (120.0 * 480.0)


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def source_track():
    z1, z2 = np.load(OBS / "fcpe.npz"), np.load(OBS / "rmvpe.npz")
    t = z1["times"].astype(float)
    c1, c2 = cents(z1["f0_hz"].astype(float)), cents(z2["f0_hz"].astype(float))
    ok = (z1["voiced"].astype(bool) & z2["voiced"].astype(bool)
          & np.isfinite(c1) & np.isfinite(c2) & (np.abs(c1 - c2) < 100))
    return t, np.where(ok, (c1 + c2) / 2.0, np.nan)


def main():
    ts, cs = source_track()
    doc = yaml.safe_load(SRC_USTX.read_text(encoding="utf-8"))

    total, skipped = 0, 0
    for vp in doc["voice_parts"]:
        pos = vp["position"]
        xs, ys = [], []
        for n in vp["notes"]:
            L = str(n["lyric"])
            if L in ("SP", "AP"):
                continue
            a = (pos + n["position"]) * TICK_MS / 1000.0
            b = a + n["duration"] * TICK_MS / 1000.0
            m = (ts >= a) & (ts < b) & np.isfinite(cs)
            if m.sum() < 2:
                skipped += 1
                continue
            src_med = float(np.median(cs[m]))
            off = src_med - n["tone"] * 100.0
            off = int(round(float(np.clip(off, -1200.0, 1200.0))))
            x0 = int(n["position"])
            x1 = int(n["position"]) + int(n["duration"])
            # Hold a flat plateau for the whole note: two points, the second one
            # tick before the boundary. Emitting only (x0, x1) would let the next
            # note's value overwrite x1 and smear a ramp across this note.
            xs.extend([x0, max(x0, x1 - 1)])
            ys.extend([off, off])
            total += 1
        # merge duplicate x keeping the later value, then sort
        pairs = {}
        for x, y in zip(xs, ys):
            pairs[int(x)] = int(y)
        ordered = sorted(pairs.items())
        curves = [c for c in vp.get("curves", []) if c.get("abbr") != "pitd"]
        curves.append(dict(abbr="pitd", xs=[p[0] for p in ordered], ys=[p[1] for p in ordered]))
        vp["curves"] = curves

    out = RUN / "D_autopitch_residual.ustx"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False,
                                  default_flow_style=False, width=10_000), encoding="utf-8")
    print("wrote %s ; notes offset=%d skipped=%d" % (out, total, skipped))


if __name__ == "__main__":
    main()
