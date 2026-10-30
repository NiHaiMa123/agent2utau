"""Same judgement applied to 最后一页's auto-pitch version and its hand-drawn v6.

Both are compared against 最后一页's own source F0 (fcpe/rmvpe mean where they agree).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402

LP = REPO / "runs/production/zuihouyiye-from-scratch-20261027"
TICK_MS = 60000.0 / (120.0 * 480.0)


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def source_track():
    z1 = np.load(LP / "observation/fcpe.npz")
    z2 = np.load(LP / "observation/rmvpe.npz")
    t = z1["times"].astype(float)
    c1 = cents(z1["f0_hz"].astype(float))
    c2 = cents(z2["f0_hz"].astype(float))
    v1 = z1["voiced"].astype(bool)
    v2 = z2["voiced"].astype(bool)
    both = v1 & v2 & np.isfinite(c1) & np.isfinite(c2)
    agree = both & (np.abs(c1 - c2) < 100)
    c = np.where(agree, (c1 + c2) / 2.0, np.nan)
    return t, c, agree


def main():
    t_src, c_src, ok = source_track()
    print("source agree frames: %d / %d (%.0f%%)" % (ok.sum(), len(ok), 100 * ok.mean()))

    cases = {
        "lastpage_handdrawn_v6": LP / "render_v6/vocal_vocal.wav",
        "lastpage_autopitch": REPO / "scratch/lastpage_v6_dspitch_fix/vocal_vocal.wav",
    }
    for name, wav in cases.items():
        if not wav.exists():
            print(name, "MISSING", wav)
            continue
        f0 = extract_f0(str(wav))
        tt = np.asarray(f0["times"], float)
        cc = cents(np.asarray(f0["f0_hz"], float))
        rv = np.interp(t_src, tt, cc, left=np.nan, right=np.nan)
        m = ok & np.isfinite(rv)
        d = rv[m] - c_src[m]
        print(
            "%-24s n=%5d  median %+6.1f  |d| median %6.1f  p90 %6.1f   >50c %5.1f%%  >100c %5.1f%%  >200c %5.1f%%"
            % (name, m.sum(), np.median(d), np.median(np.abs(d)), np.percentile(np.abs(d), 90),
               100 * (np.abs(d) > 50).mean(), 100 * (np.abs(d) > 100).mean(),
               100 * (np.abs(d) > 200).mean())
        )

    # also: lastpage's SCORE tone vs source (is the score itself faithful?)
    d = yaml.safe_load((LP / "compiled_v6/project.ustx").read_text(encoding="utf-8"))
    errs, n = [], 0
    for vp in d["voice_parts"]:
        pos = vp["position"]
        for note in vp["notes"]:
            L = str(note["lyric"])
            if L in ("SP", "AP"):
                continue
            a = (pos + note["position"]) * TICK_MS / 1000.0
            b = a + note["duration"] * TICK_MS / 1000.0
            m = (t_src >= a) & (t_src < b) & ok
            if m.sum() < 3:
                continue
            errs.append(float(np.median(c_src[m])) - note["tone"] * 100.0)
            n += 1
    e = np.array(errs)
    print(
        "%-24s n=%5d  median %+6.1f  |d| median %6.1f  p90 %6.1f   >50c %5.1f%%  >100c %5.1f%%"
        % ("lastpage_score_vs_source", len(e), np.median(e), np.median(np.abs(e)),
           np.percentile(np.abs(e), 90), 100 * (np.abs(e) > 50).mean(),
           100 * (np.abs(e) > 100).mean())
    )


if __name__ == "__main__":
    main()
