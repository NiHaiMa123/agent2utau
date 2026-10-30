"""Does the earlier 'functional' auto-pitch render show the same failure mode?

Same per-note metric as the v3-rebuild diagnosis, measured against the original
singer's F0 trace.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/scripts"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402
from nianlun_v3_source import Source, filled_track  # noqa: E402

V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
SRC = Source(V3)
TICK_MS = 60000.0 / (120.0 * 480.0)

CASES = [
    ("func_dspitch", REPO / "scratch/nianlun_func_dspitch/nianlun_functional_dspitch.ustx",
     REPO / "scratch/nianlun_func_dspitch/vocal_vocal.wav"),
]


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def main():
    for name, proj, wav in CASES:
        if not (proj.exists() and wav.exists()):
            print("missing", name)
            continue
        d = yaml.safe_load(proj.read_text(encoding="utf-8"))
        f0 = extract_f0(str(wav))
        tr, cr = np.asarray(f0["times"], float), cents(np.asarray(f0["f0_hz"], float))
        rows = []
        for part in d["voice_parts"]:
            pos = part["position"]
            for n in part["notes"]:
                if n["lyric"] in ("AP", "SP"):
                    continue
                a = (pos + n["position"]) * TICK_MS / 1000.0
                b = a + n["duration"] * TICK_MS / 1000.0
                ft = filled_track(SRC, a, b)
                if not ft:
                    continue
                m = (ft[0] >= a) & (ft[0] < b)
                if m.sum() < 3:
                    continue
                src_c = float(np.median(ft[1][m]))
                mm = (tr >= a) & (tr < b) & np.isfinite(cr)
                if mm.sum() < 3:
                    continue
                rows.append((n["lyric"], n["tone"] * 100.0, (b - a) * 1000,
                             float(np.median(cr[mm])), src_c))
        e = np.array([r[3] - r[4] for r in rows])
        score_e = np.array([r[1] - r[4] for r in rows])
        dur = np.array([r[2] for r in rows])
        print("== %s  notes %d" % (name, len(rows)))
        print("  render vs source: |err| median %6.1f  p90 %6.1f  >100c %d (%.0f%%)"
              % (np.median(np.abs(e)), np.percentile(np.abs(e), 90),
                 (np.abs(e) > 100).sum(), 100 * (np.abs(e) > 100).mean()))
        print("  score  vs source: |err| median %6.1f  p90 %6.1f  >100c %d (%.0f%%)"
              % (np.median(np.abs(score_e)), np.percentile(np.abs(score_e), 90),
                 (np.abs(score_e) > 100).sum(), 100 * (np.abs(score_e) > 100).mean()))
        for lo, hi in [(0, 120), (120, 200), (200, 1e9)]:
            sel = (dur >= lo) & (dur < hi)
            if sel.sum() == 0:
                continue
            ee = np.abs(e)[sel]
            print("    dur %4.0f-%5.0fms n=%3d  |err| median %6.1f  p90 %6.1f"
                  % (lo, min(hi, 9999), sel.sum(), np.median(ee), np.percentile(ee, 90)))


if __name__ == "__main__":
    main()
