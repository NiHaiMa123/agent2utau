"""Did variant D's per-note offset actually land? Compare per-note medians."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402

RUN = REPO / "runs/experiments/nianlun-autopitch-fix-20261030"
OBS = REPO / "runs/production/nianlun-from-scratch-v3-20261030/observation"
TICK_MS = 60000.0 / (120.0 * 480.0)


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
    for tag, wav, proj in [
        ("A", RUN / "A_v3score_autopitch_vocal.wav", REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"),
        ("D", RUN / "D_vocal.wav", RUN / "D_autopitch_residual.ustx"),
    ]:
        d = yaml.safe_load(proj.read_text(encoding="utf-8"))
        f0 = extract_f0(str(wav))
        tt = np.asarray(f0["times"], float)
        cc = cents(np.asarray(f0["f0_hz"], float))
        per_note = []
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
                per_note.append(float(np.median(cc[m])) - float(np.median(cs[ms])))
        e = np.array(per_note)
        print("%s  per-note (render minus source) n=%d  median %+6.1f  |e| median %6.1f  p90 %6.1f  >100c %.1f%%"
              % (tag, len(e), np.median(e), np.median(np.abs(e)),
                 np.percentile(np.abs(e), 90), 100 * (np.abs(e) > 100).mean()))


if __name__ == "__main__":
    main()
