"""Is the auto-pitch line systematically misaligned in time against the score?

If the predictor's frames are allocated to notes differently from the score's
tick grid (short notes / rests / phrase padding), the melody is right but shifted
or stretched -> sounds off-key even though every frame is "in tune".
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
AUT = REPO / "scratch/nianlun_v3_rebuild/autopitch.json"
BASE = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"
TICK_MS = 60000.0 / (120.0 * 480.0)


def main():
    aut = json.loads(AUT.read_text(encoding="utf-8"))
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    parts = {p["position"]: p for p in base["voice_parts"]}

    # Build score-vs-prediction pairs on the predictor's own tick grid.
    t_all, score_all, pred_all = [], [], []
    for ph in aut["phrases"]:
        part = parts[ph["part_position"]]
        notes = part["notes"]
        pos0 = ph["part_position"]
        nt = np.asarray([pos0 + n["position"] for n in notes])
        dur = np.asarray([n["duration"] for n in notes])
        tone = np.asarray([n["tone"] for n in notes], dtype=float) * 100.0
        ticks = np.asarray(ph["ticks"], dtype=float) + ph["position"]
        idx = np.searchsorted(nt, ticks, side="right") - 1
        idx = np.clip(idx, 0, len(notes) - 1)
        t_all.append(ticks * TICK_MS)
        score_all.append(tone[idx])
        pred_all.append(np.asarray(ph["tones"]) * 100.0)

    t = np.concatenate(t_all)
    sc = np.concatenate(score_all)
    pr = np.concatenate(pred_all)
    o = np.argsort(t)
    t, sc, pr = t[o], sc[o], pr[o]

    # de-mean and cross-correlate to find best lag
    def corr_at(lag_ms):
        # shift prediction in time by lag, compare to score
        p2 = np.interp(t, np.sort(t) + lag_ms, pr)
        a = sc - sc.mean()
        b = p2 - p2.mean()
        return float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

    lags = np.arange(-200, 201, 5)
    cs = [(l, corr_at(l)) for l in lags]
    best = max(cs, key=lambda x: x[1])
    print("prediction vs score on predictor grid: r(lag=0)=%.3f   best lag %+d ms -> r=%.3f"
          % (dict(cs)[0], best[0], best[1]))

    # per-phrase: the phrase is a fixed mapping; check drift WITHIN phrases
    print("\nper-phrase r at lag 0 (first 12 phrases):")
    for i, ph in enumerate(aut["phrases"][:12]):
        part = parts[ph["part_position"]]
        notes = part["notes"]
        pos0 = ph["part_position"]
        nt = np.asarray([pos0 + n["position"] for n in notes])
        tone = np.asarray([n["tone"] for n in notes], dtype=float) * 100.0
        ticks = np.asarray(ph["ticks"], dtype=float) + ph["position"]
        idx = np.clip(np.searchsorted(nt, ticks, side="right") - 1, 0, len(notes) - 1)
        s = tone[idx]
        p = np.asarray(ph["tones"]) * 100.0
        a, b = s - s.mean(), p - p.mean()
        r = float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
        print("  phrase %2d  part %7d  n=%3d  r=%.3f  score range %.0f..%.0f  pred %.0f..%.0f"
              % (i, pos0, len(ticks), r, s.min(), s.max(), p.min(), p.max()))


if __name__ == "__main__":
    main()
