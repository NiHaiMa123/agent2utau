"""Final check: is the melody handed to the predictor a *smooth* version of the
score, and is the score's own melody already too coarse for the source?

Frame-grid pitch of the model prediction vs the score's step function:
 - if the prediction rounds/holds notes, the model is behaving like a
   "note-following" predictor, which is the expected DiffSinger behaviour.
 - the audible error then equals the score's quantization error (12-TET rounding
   of a portamento-heavy vocal line), NOT a bug in the render.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/scripts"))
from nianlun_v3_source import Source, filled_track  # noqa: E402

V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
BASE = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"
AUT = REPO / "scratch/nianlun_v3_rebuild/autopitch.json"
SRC = Source(V3)
TICK_MS = 60000.0 / (120.0 * 480.0)


def main():
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    aut = json.loads(AUT.read_text(encoding="utf-8"))
    parts = {p["position"]: p for p in base["voice_parts"]}

    # score step function on the predictor grid
    ss = []
    for ph in aut["phrases"]:
        part = parts[ph["part_position"]]
        pos0 = ph["part_position"]
        nt = np.asarray([pos0 + n["position"] for n in part["notes"]])
        tone = np.asarray([n["tone"] for n in part["notes"]], dtype=float) * 100.0
        ticks = np.asarray(ph["ticks"]) + ph["position"]
        idx = np.clip(np.searchsorted(nt, ticks, side="right") - 1, 0, len(part["notes"]) - 1)
        ss.append((ticks * TICK_MS / 1000.0, tone[idx], np.asarray(ph["tones"]) * 100.0))
    t = np.concatenate([s[0] for s in ss])
    sc = np.concatenate([s[1] for s in ss])
    pr = np.concatenate([s[2] for s in ss])
    o = np.argsort(t)
    t, sc, pr = t[o], sc[o], pr[o]

    # source at the same times
    src = np.full(len(t), np.nan)
    for i, ti in enumerate(t):
        ft = filled_track(SRC, ti - 0.02, ti + 0.02)
        if ft:
            src[i] = ft[1][np.argmin(np.abs(ft[0] - ti))]
    m = np.isfinite(src)

    # melodic motion: how much does the source move within a 100 ms window
    step_ms = 100.0
    j = np.searchsorted(t, t + step_ms / 1000.0)
    j = np.clip(j, 0, len(t) - 1)
    src_motion = np.abs(src[j] - src)
    ok = m & np.isfinite(src_motion)
    print("source pitch motion per 100ms: median %.0fc  p90 %.0fc  >50c: %.0f%%"
          % (np.median(src_motion[ok]), np.percentile(src_motion[ok], 90),
             100 * (src_motion[ok] > 50).mean()))

    score_motion = np.abs(sc[j] - sc)
    pred_motion = np.abs(pr[j] - pr)
    print("score  pitch motion per 100ms: median %.0fc  p90 %.0fc  >50c: %.0f%%"
          % (np.median(score_motion), np.percentile(score_motion, 90),
             100 * (score_motion > 50).mean()))
    print("pred   pitch motion per 100ms: median %.0fc  p90 %.0fc  >50c: %.0f%%"
          % (np.median(pred_motion), np.percentile(pred_motion, 90),
             100 * (pred_motion > 50).mean()))

    # how well does the prediction reproduce the source's *shape* (correlation)?
    for name, x in [("score", sc), ("pred", pr)]:
        a = x[m] - x[m].mean()
        b = src[m] - src[m].mean()
        r = float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
        # after removing the best constant offset
        e = x[m] - src[m]
        print("%s vs source: r=%.3f  bias %+.1fc  |err| median %.1fc" % (name, r, np.median(e), np.median(np.abs(e))))


if __name__ == "__main__":
    main()
