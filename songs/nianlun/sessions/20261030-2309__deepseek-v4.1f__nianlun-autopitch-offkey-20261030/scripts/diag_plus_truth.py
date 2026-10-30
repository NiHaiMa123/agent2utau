"""Correct the '+' block question with |error| (absolute), not signed percentiles.

Is a '+' block's tone closer to or farther from the source than a sung note's?
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/scripts"))
from nianlun_v3_source import Source, filled_track  # noqa: E402

V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
SRC = Source(V3)
TICK_MS = 60000.0 / (120.0 * 480.0)


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def main():
    p = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))

    groups = {"sung": [], "plus": [], "rest": []}
    for vp in d["voice_parts"]:
        pos = vp["position"]
        for n in vp["notes"]:
            L = str(n["lyric"])
            key = "rest" if L in ("SP", "AP") else ("plus" if L.startswith("+") else "sung")
            a = (pos + n["position"]) * TICK_MS / 1000.0
            b = a + n["duration"] * TICK_MS / 1000.0
            ft = filled_track(SRC, a, b)
            if not ft:
                continue
            m = (ft[0] >= a) & (ft[0] < b)
            if m.sum() < 3:
                continue
            groups[key].append(float(np.median(ft[1][m])) - n["tone"] * 100.0)

    print("score tone vs source, |error| in cents:")
    for k, v in groups.items():
        if not v:
            continue
        e = np.abs(np.array(v))
        print("  %-6s n=%3d  |e| median %6.1f  p90 %6.1f  >100c %2d" %
              (k, len(e), np.median(e), np.percentile(e, 90), (e > 100).sum()))

    # For '+' blocks, compare against the PARENT's source too: is the jump real?
    print("\n'+' blocks: is the tone jump to the parent a real pitch change?")
    jumps_real = []
    for vp in d["voice_parts"]:
        pos = vp["position"]
        ns = vp["notes"]
        for i, n in enumerate(ns):
            if not str(n["lyric"]).startswith("+"):
                continue
            for j in range(i - 1, -1, -1):
                if not str(ns[j]["lyric"]).startswith("+"):
                    a1 = (pos + ns[j]["position"]) * TICK_MS / 1000.0
                    a2 = a1 + ns[j]["duration"] * TICK_MS / 1000.0
                    b1 = (pos + n["position"]) * TICK_MS / 1000.0
                    b2 = b1 + n["duration"] * TICK_MS / 1000.0
                    f1 = filled_track(SRC, a1, a2)
                    f2 = filled_track(SRC, b1, b2)
                    if not f1 or not f2:
                        break
                    m1 = (f1[0] >= a1) & (f1[0] < a2)
                    m2 = (f2[0] >= b1) & (f2[0] < b2)
                    if m1.sum() < 3 or m2.sum() < 3:
                        break
                    score_jump = n["tone"] - ns[j]["tone"]
                    real_jump = float(np.median(f2[1][m2]) - np.median(f1[1][m1])) / 100.0
                    jumps_real.append((score_jump, real_jump))
                    break
    if jumps_real:
        sj = np.array([x[0] for x in jumps_real])
        rj = np.array([x[1] for x in jumps_real])
        print("  n=%d" % len(sj))
        print("  score jump (semitones): mean %+.2f  |jump| mean %.2f" % (sj.mean(), np.abs(sj).mean()))
        print("  real  jump (semitones): mean %+.2f  |jump| mean %.2f" % (rj.mean(), np.abs(rj).mean()))
        diff = sj - rj
        print("  score minus real: mean %+.2f  |diff| mean %.2f  median %.2f semitones" %
              (diff.mean(), np.abs(diff).mean(), np.median(np.abs(diff))))
        print("  correlation(score jump, real jump) = %.3f" % float(np.corrcoef(sj, rj)[0, 1]))


if __name__ == "__main__":
    main()
