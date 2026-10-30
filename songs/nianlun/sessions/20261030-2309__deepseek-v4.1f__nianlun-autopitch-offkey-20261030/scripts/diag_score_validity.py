"""The decisive comparison: is each song's SCORE a valid MIDI melody?

Auto-pitch can only reproduce what the score's tone says. Both songs are judged
by the same rule on their own source F0.
"""
from __future__ import annotations

import numpy as np
import yaml
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
TICK_MS = 60000.0 / (120.0 * 480.0)

SONGS = {
    "nianlun_v3": dict(
        obs=REPO / "runs/production/nianlun-from-scratch-v3-20261030/observation",
        project=REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx",
    ),
    "lastpage_v6": dict(
        obs=REPO / "runs/production/zuihouyiye-from-scratch-20261027/observation",
        project=REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx",
    ),
}


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def source(obs):
    z1, z2 = np.load(obs / "fcpe.npz"), np.load(obs / "rmvpe.npz")
    t = z1["times"].astype(float)
    c1, c2 = cents(z1["f0_hz"].astype(float)), cents(z2["f0_hz"].astype(float))
    agree = (z1["voiced"].astype(bool) & z2["voiced"].astype(bool)
             & np.isfinite(c1) & np.isfinite(c2) & (np.abs(c1 - c2) < 100))
    return t, np.where(agree, (c1 + c2) / 2.0, np.nan)


def main():
    for song, cfg in SONGS.items():
        t, c = source(cfg["obs"])
        d = yaml.safe_load(cfg["project"].read_text(encoding="utf-8"))
        sung, plus, rest = [], [], []
        durs, pdurs = [], []
        for vp in d["voice_parts"]:
            pos = vp["position"]
            for n in vp["notes"]:
                L = str(n["lyric"])
                a = (pos + n["position"]) * TICK_MS / 1000.0
                b = a + n["duration"] * TICK_MS / 1000.0
                m = (t >= a) & (t < b) & np.isfinite(c)
                if m.sum() < 3:
                    continue
                e = float(np.median(c[m])) - n["tone"] * 100.0
                if L in ("SP", "AP"):
                    rest.append(e)
                elif L.startswith("+"):
                    plus.append(e)
                    pdurs.append(n["duration"] * TICK_MS)
                else:
                    sung.append(e)
                    durs.append(n["duration"] * TICK_MS)
        print("\n" + "=" * 74)
        print(song)
        for name, v, dd in [("sung", sung, durs), ("'+' block", plus, pdurs), ("rest", rest, None)]:
            if not v:
                continue
            e = np.abs(np.array(v))
            extra = ("  dur median %.0fms / min %.0fms" % (np.median(dd), min(dd))) if dd else ""
            print("  %-10s n=%3d  |tone-source| median %6.1f  p90 %6.1f  >100c %2d%s"
                  % (name, len(e), np.median(e), np.percentile(e, 90), (e > 100).sum(), extra))
        allv = np.abs(np.array(sung + plus))
        print("  --> score as MIDI: median %.1fc  p90 %.1fc  %.0f%% of notes off by >100c"
              % (np.median(allv), np.percentile(allv, 90), 100 * (allv > 100).mean()))
        tot = len(sung) + len(plus) + len(rest)
        print("  --> '+' share %.0f%% of %d notes ; min sung duration %.0fms"
              % (100 * len(plus) / max(tot, 1), tot, min(durs)))


if __name__ == "__main__":
    main()
