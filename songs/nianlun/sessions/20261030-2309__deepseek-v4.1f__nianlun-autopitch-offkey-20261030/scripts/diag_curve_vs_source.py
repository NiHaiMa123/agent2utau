"""Frame-level: is the auto-pitch CURVE itself worse than the score?

Reconstruct the written PITD curve back to absolute cents and compare, frame by
frame, against (a) the score step function and (b) the source F0.
Both songs, identical code.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
TICK_MS = 60000.0 / (120.0 * 480.0)

SONGS = {
    "nianlun": dict(
        obs=REPO / "runs/production/nianlun-from-scratch-v3-20261030/observation",
        project=REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx",
        final=REPO / "scratch/nianlun_v3_rebuild_audio/final.ustx",
        basepitch=REPO / "scratch/nianlun_v3_rebuild/baseline_pitch.json",
    ),
    "lastpage": dict(
        obs=REPO / "runs/production/zuihouyiye-from-scratch-20261027/observation",
        project=REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx",
        final=REPO / "scratch/lastpage_v6_dspitch_fix/project_dspitch_fix.ustx",
        basepitch=None,
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
    agree = (z1["voiced"].astype(bool) & z2["voiced"].astype(bool)
             & np.isfinite(c1) & np.isfinite(c2) & (np.abs(c1 - c2) < 100))
    return t, np.where(agree, (c1 + c2) / 2.0, np.nan), agree


def main():
    for song, cfg in SONGS.items():
        print("\n" + "=" * 78)
        print(song)
        t_src, c_src, ok = source_track(cfg["obs"])

        proj = yaml.safe_load(cfg["project"].read_text(encoding="utf-8"))
        final = yaml.safe_load(cfg["final"].read_text(encoding="utf-8"))
        fparts = {p["position"]: p for p in final["voice_parts"]}

        # score step function in absolute cents at time t
        def score_at(tq):
            for vp in final["voice_parts"]:
                pos = vp["position"]
                a = pos * TICK_MS / 1000.0
                b = (pos + vp["duration"]) * TICK_MS / 1000.0
                if a - 0.5 <= tq < b + 0.5:
                    rel = tq * 1000.0 / TICK_MS - pos
                    for n in vp["notes"]:
                        if n["position"] <= rel < n["position"] + n["duration"]:
                            return n["tone"] * 100.0
            return np.nan

        # auto-pitch curve in absolute cents at time t (pitd is an offset from
        # the note's nominal pitch, applied over the phrase)
        def autopitch_at(tq):
            for vp in final["voice_parts"]:
                pos = vp["position"]
                a = pos * TICK_MS / 1000.0
                b = (pos + vp["duration"]) * TICK_MS / 1000.0
                if not (a - 0.5 <= tq < b + 0.5):
                    continue
                c = [x for x in vp.get("curves", []) if x.get("abbr") == "pitd"]
                if not c:
                    return np.nan
                xs = np.asarray(c[0]["xs"], dtype=float)
                ys = np.asarray(c[0]["ys"], dtype=float)
                rel = tq * 1000.0 / TICK_MS - pos
                if rel < xs.min() or rel > xs.max():
                    return np.nan
                off = float(np.interp(rel, xs, ys))
                # nominal pitch of the note at this time
                for n in vp["notes"]:
                    if n["position"] <= rel < n["position"] + n["duration"]:
                        return n["tone"] * 100.0 + off
                return np.nan
            return np.nan

        grid = t_src[ok][::3]
        sc = np.array([score_at(t) for t in grid])
        ap = np.array([autopitch_at(t) for t in grid])
        sr = np.interp(grid, t_src, c_src)
        m = np.isfinite(sc) & np.isfinite(ap) & np.isfinite(sr)
        print("  frames compared:", m.sum())

        for name, x in [("score", sc), ("autopitch_curve", ap)]:
            e = x[m] - sr[m]
            print(
                "  %-16s vs source: median %+6.1f  |d| median %6.1f  p90 %6.1f  >100c %5.1f%%"
                % (name, np.median(e), np.median(np.abs(e)),
                   np.percentile(np.abs(e), 90), 100 * (np.abs(e) > 100).mean())
            )

        d = ap[m] - sc[m]
        print(
            "  autopitch_curve vs score: |d| median %6.1f  p90 %6.1f  max %6.1f  >100c %5.1f%%"
            % (np.median(np.abs(d)), np.percentile(np.abs(d), 90), np.abs(d).max(),
               100 * (np.abs(d) > 100).mean())
        )


if __name__ == "__main__":
    main()
