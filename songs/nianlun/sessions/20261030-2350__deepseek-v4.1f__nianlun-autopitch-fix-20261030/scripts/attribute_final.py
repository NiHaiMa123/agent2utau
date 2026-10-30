"""Final attribution: where does the auto-pitch render actually deviate?

Method (strict, no rest frames, no interpolation across gaps):
  * For every sung note, take the render's F0 frames strictly inside the note.
  * Compare against (a) the note's own score tone, (b) the source F0 in that same span.
  * Attribute the source error by note kind and length.
Also measures contour roughness: how step-wise the pitch moves frame to frame,
because a singer glides where 12-TET notes step.
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
NIAN = REPO / "runs/experiments/nianlun-autopitch-fix-20261030"


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def src_track(obs):
    z1, z2 = np.load(obs / "fcpe.npz"), np.load(obs / "rmvpe.npz")
    t = z1["times"].astype(float)
    c1, c2 = cents(z1["f0_hz"].astype(float)), cents(z2["f0_hz"].astype(float))
    ok = (z1["voiced"].astype(bool) & z2["voiced"].astype(bool)
          & np.isfinite(c1) & np.isfinite(c2) & (np.abs(c1 - c2) < 100))
    return t, np.where(ok, (c1 + c2) / 2.0, np.nan)


def analyse(tag, wav, proj, obs):
    d = yaml.safe_load(proj.read_text(encoding="utf-8"))
    f0 = extract_f0(str(wav))
    tt = np.asarray(f0["times"], float)
    cc = cents(np.asarray(f0["f0_hz"], float))
    ts, cs = src_track(obs)

    rows = []
    for vp in d["voice_parts"]:
        pos = vp["position"]
        for n in vp["notes"]:
            L = str(n["lyric"])
            if L in ("SP", "AP"):
                continue
            a = (pos + n["position"]) * TICK_MS / 1000.0
            b = a + n["duration"] * TICK_MS / 1000.0
            # inset the window to avoid boundary glide contamination
            pad = min(0.02, 0.25 * (b - a))
            m = (tt >= a + pad) & (tt <= b - pad) & np.isfinite(cc)
            if m.sum() < 2:
                continue
            r = float(np.median(cc[m]))
            ms = (ts >= a) & (ts < b) & np.isfinite(cs)
            s = float(np.median(cs[ms])) if ms.sum() >= 2 else np.nan
            rows.append(dict(kind="plus" if L.startswith("+") else "sung",
                             dur=n["duration"] * TICK_MS,
                             tone=n["tone"] * 100.0,
                             render=r, src=s))

    print("\n" + "=" * 80)
    print(tag, " notes:", len(rows))
    e_score = np.array([r["render"] - r["tone"] for r in rows])
    have_src = [r for r in rows if np.isfinite(r["src"])]
    e_src = np.array([r["render"] - r["src"] for r in have_src])
    s_src = np.array([r["tone"] - r["src"] for r in have_src])
    print("  render vs OWN SCORE : |d| median %5.1f  p90 %5.1f  (>100c %.1f%%)" %
          (np.median(np.abs(e_score)), np.percentile(np.abs(e_score), 90),
           100 * (np.abs(e_score) > 100).mean()))
    print("  score  vs SOURCE    : |d| median %5.1f  p90 %5.1f  (>100c %.1f%%)  [n=%d]" %
          (np.median(np.abs(s_src)), np.percentile(np.abs(s_src), 90),
           100 * (np.abs(s_src) > 100).mean(), len(have_src)))
    print("  render vs SOURCE    : |d| median %5.1f  p90 %5.1f  (>100c %.1f%%)" %
          (np.median(np.abs(e_src)), np.percentile(np.abs(e_src), 90),
           100 * (np.abs(e_src) > 100).mean()))

    def band(name, sel):
        if not sel:
            return
        e = np.abs(np.array([r["render"] - r["src"] for r in sel if np.isfinite(r["src"])]))
        if not len(e):
            return
        print("    %-18s n=%3d  |err| median %6.1f  p90 %6.1f" %
              (name, len(e), np.median(e), np.percentile(e, 90)))

    print("  by kind / length (render vs source):")
    band("'+' block", [r for r in have_src if r["kind"] == "plus"])
    band("sung", [r for r in have_src if r["kind"] == "sung"])
    for lo, hi in [(0, 150), (150, 250), (250, 400), (400, 1e9)]:
        band("dur %3.0f-%4.0fms" % (lo, min(hi, 9999)),
             [r for r in have_src if lo <= r["dur"] < hi])

    # contour roughness: frame-to-frame delta inside voiced stretches
    m = np.isfinite(cc)
    dd = np.abs(np.diff(cc[m]))
    srcm = np.isfinite(cs)
    sdd = np.abs(np.diff(cs[srcm]))
    print("  contour step per frame (median / p90):")
    print("    render %6.1f / %6.1f c    source %6.1f / %6.1f c" %
          (np.median(dd), np.percentile(dd, 90), np.median(sdd), np.percentile(sdd, 90)))


def main():
    analyse("骞磋疆 A (v3 score + autopitch)",
            NIAN / "A_v3score_autopitch_vocal.wav",
            REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx",
            REPO / "runs/production/nianlun-from-scratch-v3-20261030/observation")
    analyse("鏈€鍚庝竴椤?(v6 score + autopitch)",
            REPO / "scratch/lastpage_v6_dspitch_fix/vocal_vocal.wav",
            REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx",
            REPO / "runs/production/zuihouyiye-from-scratch-20261027/observation")


if __name__ == "__main__":
    main()
