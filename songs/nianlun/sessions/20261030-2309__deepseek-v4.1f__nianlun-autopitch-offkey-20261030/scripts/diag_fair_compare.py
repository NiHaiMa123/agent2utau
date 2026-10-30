"""Apply ONE identical judgement to both songs and to both methods.

Source  = each project's own fcpe/rmvpe agreeing frames (same rule both songs).
Methods = hand-drawn (v3 / v6) vs auto-pitch (dspitch).
Judge   = frame-level |render - source| on the common 20 ms grid.
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

SONGS = {
    "nianlun": dict(
        obs=REPO / "runs/production/nianlun-from-scratch-v3-20261030/observation",
        project=REPO / "runs/production/nianlun-from-scratch-v3-20261030/compiled/project.ustx",
        handdrawn=REPO / "runs/production/nianlun-from-scratch-v3-20261030/render/vocal_vocal.wav",
        autopitch=REPO / "scratch/nianlun_v3_rebuild_audio/step1_vocal_vocal.wav",
    ),
    "lastpage": dict(
        obs=REPO / "runs/production/zuihouyiye-from-scratch-20261027/observation",
        project=REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx",
        handdrawn=REPO / "runs/production/zuihouyiye-from-scratch-20261027/render_v6/vocal_vocal.wav",
        autopitch=REPO / "scratch/lastpage_v6_dspitch_fix/vocal_vocal.wav",
    ),
}


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def source_track(obs):
    z1 = np.load(obs / "fcpe.npz")
    z2 = np.load(obs / "rmvpe.npz")
    t = z1["times"].astype(float)
    c1 = cents(z1["f0_hz"].astype(float))
    c2 = cents(z2["f0_hz"].astype(float))
    v1 = z1["voiced"].astype(bool)
    v2 = z2["voiced"].astype(bool)
    agree = v1 & v2 & np.isfinite(c1) & np.isfinite(c2) & (np.abs(c1 - c2) < 100)
    c = np.where(agree, (c1 + c2) / 2.0, np.nan)
    return t, c, agree


def main():
    for song, cfg in SONGS.items():
        print("\n" + "=" * 78)
        print(song)
        t_src, c_src, ok = source_track(cfg["obs"])
        print("  source agree frames %d/%d (%.0f%%)" % (ok.sum(), len(ok), 100 * ok.mean()))

        d = yaml.safe_load(cfg["project"].read_text(encoding="utf-8"))
        # note counts
        plus = sum(1 for vp in d["voice_parts"] for n in vp["notes"] if str(n["lyric"]).startswith("+"))
        sung = sum(1 for vp in d["voice_parts"] for n in vp["notes"]
                   if str(n["lyric"]) not in ("SP", "AP") and not str(n["lyric"]).startswith("+"))
        tot = sum(len(vp["notes"]) for vp in d["voice_parts"])
        durs = [n["duration"] * TICK_MS for vp in d["voice_parts"] for n in vp["notes"]
                if str(n["lyric"]) not in ("SP", "AP")]
        print("  notes %d (sung %d, '+' %d = %.0f%%)  min sung dur %.0fms" %
              (tot, sung, plus, 100 * plus / max(tot, 1), min(durs)))

        for method in ("handdrawn", "autopitch"):
            wav = cfg[method]
            if not wav.exists():
                print("  %-10s MISSING" % method)
                continue
            f0 = extract_f0(str(wav))
            tt = np.asarray(f0["times"], float)
            cc = cents(np.asarray(f0["f0_hz"], float))
            rv = np.interp(t_src, tt, cc, left=np.nan, right=np.nan)
            m = ok & np.isfinite(rv)
            e = rv[m] - c_src[m]
            print(
                "  %-10s n=%5d  median %+6.1f  |d| median %6.1f  p90 %6.1f  "
                ">50c %5.1f%%  >100c %5.1f%%  >200c %5.1f%%"
                % (method, m.sum(), np.median(e), np.median(np.abs(e)),
                   np.percentile(np.abs(e), 90),
                   100 * (np.abs(e) > 50).mean(), 100 * (np.abs(e) > 100).mean(),
                   100 * (np.abs(e) > 200).mean())
            )

        # score tone vs source
        errs = []
        for vp in d["voice_parts"]:
            pos = vp["position"]
            for note in vp["notes"]:
                L = str(note["lyric"])
                if L in ("SP", "AP"):
                    continue
                a = (pos + note["position"]) * TICK_MS / 1000.0
                b = a + note["duration"] * TICK_MS / 1000.0
                mm = (t_src >= a) & (t_src < b) & ok
                if mm.sum() < 3:
                    continue
                errs.append(float(np.median(c_src[mm])) - note["tone"] * 100.0)
        e = np.array(errs)
        print(
            "  %-10s n=%5d  median %+6.1f  |d| median %6.1f  p90 %6.1f  >50c %5.1f%%  >100c %5.1f%%"
            % ("score", len(e), np.median(e), np.median(np.abs(e)),
               np.percentile(np.abs(e), 90), 100 * (np.abs(e) > 50).mean(),
               100 * (np.abs(e) > 100).mean())
        )


if __name__ == "__main__":
    main()
