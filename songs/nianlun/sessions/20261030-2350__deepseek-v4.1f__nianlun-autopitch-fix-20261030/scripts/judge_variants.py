"""Judge all 骞磋疆 auto-pitch variants against the original singer, one rule.

Candidates:
  A_v3score_autopitch   v3 score as-is, model predicts (the current broken result)
  B_plusmerge           '+' blocks folded back into their parent syllable
  C_plusmerge_short     B + short notes absorbed
  (reference) v3 hand-drawn render, and the v3 score's own fidelity
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402

RUN = REPO / "runs/experiments/nianlun-autopitch-fix-20261030"
V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
TICK_MS = 60000.0 / (120.0 * 480.0)

CASES = {
    "A_v3score_autopitch": RUN / "A_v3score_autopitch_vocal.wav",
    "B_plusmerge": RUN / "B_plusmerge_vocal.wav",
    "C_plusmerge_short": RUN / "C_plusmerge_short_vocal.wav",
    "D_autopitch_residual": RUN / "D_vocal.wav",
    "v3_handdrawn(ref)": V3 / "render/vocal_vocal.wav",
}


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def source():
    obs = V3 / "observation"
    z1, z2 = np.load(obs / "fcpe.npz"), np.load(obs / "rmvpe.npz")
    t = z1["times"].astype(float)
    c1, c2 = cents(z1["f0_hz"].astype(float)), cents(z2["f0_hz"].astype(float))
    agree = (z1["voiced"].astype(bool) & z2["voiced"].astype(bool)
             & np.isfinite(c1) & np.isfinite(c2) & (np.abs(c1 - c2) < 100))
    return t, np.where(agree, (c1 + c2) / 2.0, np.nan), agree


def main():
    t_src, c_src, ok = source()
    print("source agree frames: %d (%.0f%%)\n" % (ok.sum(), 100 * ok.mean()))
    print("%-22s %6s %9s %9s %8s %8s %8s" %
          ("candidate", "frames", "median", "|d| med", "p90", ">100c", ">200c"))
    rows = {}
    for name, wav in CASES.items():
        if not wav.exists():
            print("%-22s MISSING" % name)
            continue
        f0 = extract_f0(str(wav))
        tt = np.asarray(f0["times"], float)
        cc = cents(np.asarray(f0["f0_hz"], float))
        rv = np.interp(t_src, tt, cc, left=np.nan, right=np.nan)
        m = ok & np.isfinite(rv)
        e = rv[m] - c_src[m]
        rows[name] = (e, m)
        print("%-22s %6d %+9.1f %9.1f %8.1f %7.1f%% %7.1f%%" %
              (name, m.sum(), np.median(e), np.median(np.abs(e)),
               np.percentile(np.abs(e), 90),
               100 * (np.abs(e) > 100).mean(), 100 * (np.abs(e) > 200).mean()))

    # paired improvement vs A on identical frames
    if "A_v3score_autopitch" in rows:
        base_e, base_m = rows["A_v3score_autopitch"]
        print("\npaired against A (same frames):")
        for name, (e, m) in rows.items():
            if name == "A_v3score_autopitch":
                continue
            common = base_m & m
            # realign: recompute both on the intersection of source frames
            continue
        # simpler: report |error| reduction in aggregate
        a_med = np.median(np.abs(rows["A_v3score_autopitch"][0]))
        for name, (e, m) in rows.items():
            if name == "A_v3score_autopitch":
                continue
            med = np.median(np.abs(e))
            print("  %-22s |d| median %.1f -> %.1f  (%+.1f%%)" %
                  (name, a_med, med, 100 * (med - a_med) / a_med))


if __name__ == "__main__":
    main()
