"""Per-note judgement of every 骞磋疆 auto-pitch variant against the original singer.

Per-note median is the metric that matters here: it asks "does this note sit on
the sung pitch", which is what a listener hears as in-tune / off-key. Frame-level
|error| is diluted by the transitions between notes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402

RUN = REPO / "runs/experiments/nianlun-autopitch-fix-20261030"
V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
OBS = V3 / "observation"
TICK_MS = 60000.0 / (120.0 * 480.0)

CASES = [
    ("A_baseline_autopitch", RUN / "A_v3score_autopitch_vocal.wav",
     REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"),
    ("B_plusmerge", RUN / "B_plusmerge_vocal.wav", RUN / "B_plusmerge.ustx"),
    ("C_plusmerge_short", RUN / "C_plusmerge_short_vocal.wav", RUN / "C_plusmerge_short.ustx"),
    ("D_residual_fix", RUN / "D_vocal.wav", RUN / "D_autopitch_residual.ustx"),
    ("v3_handdrawn_ref", V3 / "render/vocal_vocal.wav", V3 / "compiled/project.ustx"),
]


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def src():
    z1, z2 = np.load(OBS / "fcpe.npz"), np.load(OBS / "rmvpe.npz")
    t = z1["times"].astype(float)
    c1, c2 = cents(z1["f0_hz"].astype(float)), cents(z2["f0_hz"].astype(float))
    ok = (z1["voiced"].astype(bool) & z2["voiced"].astype(bool)
          & np.isfinite(c1) & np.isfinite(c2) & (np.abs(c1 - c2) < 100))
    return t, np.where(ok, (c1 + c2) / 2.0, np.nan)


def main():
    ts, cs = src()
    print("%-22s %5s %9s %9s %9s %9s" %
          ("variant", "notes", "|e| med", "p90", ">100c", ">200c"))
    for tag, wav, proj in CASES:
        if not (wav.exists() and proj.exists()):
            print("%-22s MISSING" % tag)
            continue
        d = yaml.safe_load(proj.read_text(encoding="utf-8"))
        f0 = extract_f0(str(wav))
        tt = np.asarray(f0["times"], float)
        cc = cents(np.asarray(f0["f0_hz"], float))
        errs = []
        for vp in d["voice_parts"]:
            pos = vp["position"]
            for n in vp["notes"]:
                L = str(n["lyric"])
                if L in ("SP", "AP"):
                    continue
                a = (pos + n["position"]) * TICK_MS / 1000.0
                b = a + n["duration"] * TICK_MS / 1000.0
                m = (tt >= a) & (tt < b) & np.isfinite(cc)
                ms = (ts >= a) & (ts < b) & np.isfinite(cs)
                if m.sum() < 2 or ms.sum() < 2:
                    continue
                errs.append(float(np.median(cc[m])) - float(np.median(cs[ms])))
        e = np.array(errs)
        print("%-22s %5d %9.1f %9.1f %8.1f%% %8.1f%%" %
              (tag, len(e), np.median(np.abs(e)), np.percentile(np.abs(e), 90),
               100 * (np.abs(e) > 100).mean(), 100 * (np.abs(e) > 200).mean()))


if __name__ == "__main__":
    main()
