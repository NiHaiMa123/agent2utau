"""Cleanest model-quality metric: rendered vocal vs its OWN score tone.

This isolates "how much does the predictor deviate from the melody it was given",
removing source-trace uncertainty. Compared across both songs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402

TICK_MS = 60000.0 / (120.0 * 480.0)

CASES = {
    "nianlun_A_autopitch": (REPO / "runs/experiments/nianlun-autopitch-fix-20261030/A_v3score_autopitch_vocal.wav",
                            REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"),
    "nianlun_v3_handdrawn": (REPO / "runs/production/nianlun-from-scratch-v3-20261030/render/vocal_vocal.wav",
                             REPO / "runs/production/nianlun-from-scratch-v3-20261030/compiled/project.ustx"),
    "lastpage_autopitch": (REPO / "scratch/lastpage_v6_dspitch_fix/vocal_vocal.wav",
                           REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx"),
    "lastpage_v6_handdrawn": (REPO / "runs/production/zuihouyiye-from-scratch-20261027/render_v6/vocal_vocal.wav",
                              REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx"),
}


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def main():
    for name, (wav, proj) in CASES.items():
        if not (wav.exists() and proj.exists()):
            print("%-24s MISSING" % name)
            continue
        d = yaml.safe_load(proj.read_text(encoding="utf-8"))
        f0 = extract_f0(str(wav))
        tt = np.asarray(f0["times"], float)
        cc = cents(np.asarray(f0["f0_hz"], float))

        errs, short = [], []
        for vp in d["voice_parts"]:
            pos = vp["position"]
            for n in vp["notes"]:
                L = str(n["lyric"])
                if L in ("SP", "AP"):
                    continue
                a = (pos + n["position"]) * TICK_MS / 1000.0
                b = a + n["duration"] * TICK_MS / 1000.0
                m = (tt >= a) & (tt < b) & np.isfinite(cc)
                if m.sum() < 3:
                    continue
                e = float(np.median(cc[m])) - n["tone"] * 100.0
                errs.append(e)
                if n["duration"] * TICK_MS < 200:
                    short.append(e)
        e = np.array(errs)
        s = np.array(short) if short else np.zeros(1)
        print("%-24s n=%3d  |render-score| median %6.1f  p90 %6.1f  >100c %5.1f%%   "
              "short(<200ms) n=%3d median %6.1f"
              % (name, len(e), np.median(np.abs(e)), np.percentile(np.abs(e), 90),
                 100 * (np.abs(e) > 100).mean(), len(short), np.median(np.abs(s))))


if __name__ == "__main__":
    main()
