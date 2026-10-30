"""Split the auto-pitch error by note kind, both songs.

If the extra error concentrates on short notes and '+' blocks, then the cause is
note fragmentation (the predictor's fixed frame grid cannot resolve them), not a
missing parameter.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
TICK_MS = 60000.0 / (120.0 * 480.0)

SONGS = {
    "nianlun": dict(
        obs=REPO / "runs/production/nianlun-from-scratch-v3-20261030/observation",
        project=REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx",
        ap=REPO / "scratch/nianlun_v3_rebuild/autopitch.json",
    ),
    "lastpage": dict(
        obs=REPO / "runs/production/zuihouyiye-from-scratch-20261027/observation",
        project=REPO / "runs/production/zuihouyiye-from-scratch-20261027/compiled_v6/project.ustx",
        ap=REPO / "scratch/lastpage_v6_dspitch_fix/official_autopitch.json",
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
        proj = yaml.safe_load(cfg["project"].read_text(encoding="utf-8"))
        ap = json.loads(cfg["ap"].read_text(encoding="utf-8"))
        parts = {p["position"]: p for p in proj["voice_parts"]}
        ap_by = {}
        for ph in ap["phrases"]:
            ap_by.setdefault(ph["part_position"], []).append(ph)

        rows = []
        for ppos, phs in ap_by.items():
            part = parts.get(ppos)
            if part is None:
                continue
            for ph in phs:
                ticks = np.asarray(ph["ticks"]) + ph["position"]
                tones = np.asarray(ph["tones"]) * 100.0
                for n in part["notes"]:
                    L = str(n["lyric"])
                    if L in ("SP", "AP"):
                        continue
                    a_t = ppos + n["position"]
                    m = (ticks >= a_t) & (ticks < a_t + n["duration"])
                    if m.sum() < 3:
                        continue
                    pred = float(np.median(tones[m]))
                    ta = a_t * TICK_MS / 1000.0
                    tb = ta + n["duration"] * TICK_MS / 1000.0
                    ms = (t >= ta) & (t < tb) & np.isfinite(c)
                    if ms.sum() < 3:
                        continue
                    src = float(np.median(c[ms]))
                    rows.append(dict(kind="plus" if L.startswith("+") else "sung",
                                     dur=n["duration"] * TICK_MS,
                                     pred_err=pred - src,
                                     score_err=n["tone"] * 100.0 - src))
        print("\n" + "=" * 76)
        print(song, "notes:", len(rows))

        def show(name, sel):
            if not sel:
                return
            pe = np.abs(np.array([r["pred_err"] for r in sel]))
            se = np.abs(np.array([r["score_err"] for r in sel]))
            print("  %-22s n=%3d  score %6.1fc -> autopitch %6.1fc  (added %+6.1f)  >100c %2d"
                  % (name, len(sel), np.median(se), np.median(pe),
                     np.median(pe) - np.median(se), (pe > 100).sum()))

        show("all", rows)
        show("sung", [r for r in rows if r["kind"] == "sung"])
        show("'+' block", [r for r in rows if r["kind"] == "plus"])
        for lo, hi in [(0, 120), (120, 200), (200, 350), (350, 1e9)]:
            show("dur %3.0f-%4.0fms" % (lo, min(hi, 9999)),
                 [r for r in rows if lo <= r["dur"] < hi])

        short = [r for r in rows if r["dur"] < 200]
        print("  short(<200ms) share: %.0f%%  ; their contribution to >100c errors: %d/%d"
              % (100 * len(short) / len(rows),
                 sum(1 for r in short if abs(r["pred_err"]) > 100),
                 sum(1 for r in rows if abs(r["pred_err"]) > 100)))


if __name__ == "__main__":
    main()
