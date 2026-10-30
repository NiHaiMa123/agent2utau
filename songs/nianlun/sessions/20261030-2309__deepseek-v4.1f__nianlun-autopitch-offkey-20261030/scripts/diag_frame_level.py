"""Frame-level (note-window independent) comparison against the original singer.

For every 20 ms frame in the sung range, compare the original singer's F0 with
(a) v3's hand-drawn render and (b) the auto-pitch render.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/scripts"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402
from nianlun_v3_source import Source, filled_track  # noqa: E402

V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
SRC = Source(V3)

RENDERS = {
    "v3_handdrawn": V3 / "render" / "vocal_vocal.wav",
    "autopitch": REPO / "scratch/nianlun_v3_rebuild_audio" / "step1_vocal_vocal.wav",
}


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def main():
    # source trace over the whole sung span, 20 ms grid
    grid = np.arange(18.5, 242.0, 0.02)
    sv = np.full(len(grid), np.nan)
    for i, t in enumerate(grid):
        ft = filled_track(SRC, t - 0.02, t + 0.02)
        if ft:
            sv[i] = ft[1][np.argmin(np.abs(ft[0] - t))]
    m0 = np.isfinite(sv)
    print("source frames: %d (%.0f%% of span)" % (m0.sum(), 100 * m0.mean()))

    print("\nframe-level |error| vs original singer (cents):")
    for name, wav in RENDERS.items():
        f0 = extract_f0(str(wav))
        tt, cc = np.asarray(f0["times"], float), cents(np.asarray(f0["f0_hz"], float))
        rv = np.interp(grid, tt, cc, left=np.nan, right=np.nan)
        m = m0 & np.isfinite(rv)
        d = rv[m] - sv[m]
        print(
            "  %-14s n=%5d  median %+6.1f  |d| median %6.1f  p90 %6.1f   "
            "|d|>50c %5.1f%%  >100c %5.1f%%  >200c %5.1f%%"
            % (name, m.sum(), np.median(d), np.median(np.abs(d)),
               np.percentile(np.abs(d), 90),
               100 * (np.abs(d) > 50).mean(), 100 * (np.abs(d) > 100).mean(),
               100 * (np.abs(d) > 200).mean())
        )

    # also: how much of the source's own melodic motion does each keep?
    print("\nper-30s-block |error| median (cents):")
    for name, wav in RENDERS.items():
        f0 = extract_f0(str(wav))
        tt, cc = np.asarray(f0["times"], float), cents(np.asarray(f0["f0_hz"], float))
        rv = np.interp(grid, tt, cc, left=np.nan, right=np.nan)
        row = []
        for a in range(20, 240, 30):
            sel = m0 & np.isfinite(rv) & (grid >= a) & (grid < a + 30)
            row.append(np.median(np.abs(rv[sel] - sv[sel])) if sel.sum() > 100 else np.nan)
        print("  %-14s " % name + "  ".join("%6.1f" % x for x in row))
    print("  %-14s " % "blocks" + "  ".join("%6d" % a for a in range(20, 240, 30)))


if __name__ == "__main__":
    main()
