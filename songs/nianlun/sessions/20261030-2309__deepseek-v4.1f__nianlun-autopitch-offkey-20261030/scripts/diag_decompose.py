"""Split the auto-pitch error into inherited-from-score and added-by-model,
and locate where the audible off-key notes concentrate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/scripts"))
from agent2utau.analysis.f0 import extract_f0  # noqa: E402
from nianlun_v3_source import Source, filled_track  # noqa: E402

V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
BASE = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"
AUT = REPO / "scratch/nianlun_v3_rebuild/autopitch.json"
SRC = Source(V3)
TICK_MS = 60000.0 / (120.0 * 480.0)


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def main():
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    aut = json.loads(AUT.read_text(encoding="utf-8"))
    f0 = extract_f0(str(REPO / "scratch/nianlun_v3_rebuild_audio/final_vocal_vocal.wav"))
    tr, cr = np.asarray(f0["times"], float), cents(np.asarray(f0["f0_hz"], float))

    pred = {}
    for ph in aut["phrases"]:
        part = next(p for p in base["voice_parts"] if p["position"] == ph["part_position"])
        ticks = np.asarray(ph["ticks"]) + ph["position"]
        tones = np.asarray(ph["tones"]) * 100.0
        for i, n in enumerate(part["notes"]):
            a = ph["part_position"] + n["position"]
            m = (ticks >= a) & (ticks < a + n["duration"])
            if m.sum() >= 3:
                pred[(ph["part_position"], i)] = float(np.median(tones[m]))

    rows = []
    for part in base["voice_parts"]:
        pos = part["position"]
        for i, n in enumerate(part["notes"]):
            if n["lyric"] in ("AP", "SP"):
                continue
            a = (pos + n["position"]) * TICK_MS / 1000.0
            b = a + n["duration"] * TICK_MS / 1000.0
            ft = filled_track(SRC, a, b)
            if not ft:
                continue
            sg, sv = ft[0], ft[1]
            m = (sg >= a) & (sg < b)
            if m.sum() < 3:
                continue
            mm = (tr >= a) & (tr < b) & np.isfinite(cr)
            rows.append(
                dict(
                    pos=pos, i=i, lyric=n["lyric"], tone=n["tone"] * 100.0,
                    dur_ms=n["duration"] * TICK_MS,
                    src=float(np.median(sv[m])),
                    pred=pred.get((pos, i), np.nan),
                    render=float(np.median(cr[mm])) if mm.sum() >= 3 else np.nan,
                )
            )

    ok = [r for r in rows if np.isfinite(r["render"]) and np.isfinite(r["pred"])]
    rend_r = np.array([r["render"] for r in ok])
    score = np.array([r["tone"] for r in ok])
    predv = np.array([r["pred"] for r in ok])
    src = np.array([r["src"] for r in ok])
    dur = np.array([r["dur_ms"] for r in ok])
    plus = np.array([r["lyric"].startswith("+") for r in ok])

    print("notes:", len(ok))
    print("render vs score   : |d| median %6.1f  p90 %6.1f" % (np.median(np.abs(rend_r - score)), np.percentile(np.abs(rend_r - score), 90)))
    print("render vs pred    : |d| median %6.1f  p90 %6.1f" % (np.median(np.abs(rend_r - predv)), np.percentile(np.abs(rend_r - predv), 90)))
    print("pred vs score     : |d| median %6.1f  p90 %6.1f" % (np.median(np.abs(predv - score)), np.percentile(np.abs(predv - score), 90)))
    print("score vs source   : |d| median %6.1f  p90 %6.1f" % (np.median(np.abs(score - src)), np.percentile(np.abs(score - src), 90)))
    print("render vs source  : |d| median %6.1f  p90 %6.1f" % (np.median(np.abs(rend_r - src)), np.percentile(np.abs(rend_r - src), 90)))

    # decomposition: (render-source) = (score-source) + (pred-score) + (render-pred)
    print("\ndecomposition of render-vs-source error (RMS cents):")
    e1, e2, e3 = score - src, predv - score, rend_r - predv
    print("  score-vs-source RMS %.1f c" % np.sqrt((e1 ** 2).mean()))
    print("  pred-vs-score   RMS %.1f c" % np.sqrt((e2 ** 2).mean()))
    print("  render-vs-pred  RMS %.1f c" % np.sqrt((e3 ** 2).mean()))
    print("  total           RMS %.1f c" % np.sqrt(((rend_r - src) ** 2).mean()))

    print("\nerror concentration by note length:")
    for lo, hi in [(0, 80), (80, 120), (120, 200), (200, 350), (350, 1e9)]:
        sel = (dur >= lo) & (dur < hi)
        if sel.sum() == 0:
            continue
        e = np.abs(rend_r - src)[sel]
        print("  %4.0f-%5.0fms n=%3d  |err| median %6.1f p90 %6.1f  >100c %2d"
              % (lo, min(hi, 9999), sel.sum(), np.median(e), np.percentile(e, 90), (e > 100).sum()))

    print("\nerror by note kind:")
    for name, sel in [("'+' block", plus), ("sung", ~plus)]:
        e = np.abs(rend_r - src)[sel]
        print("  %-10s n=%3d  |err| median %6.1f  p90 %6.1f  >100c %2d"
              % (name, sel.sum(), np.median(e), np.percentile(e, 90), (e > 100).sum()))

    # worst offenders with a musical description
    rows2 = [r for r in ok if np.isfinite(r["render"])]
    rows2.sort(key=lambda r: -abs(r["render"] - r["src"]))
    print("\nworst 18 notes (render vs original singer):")
    for r in rows2[:18]:
        print("  %6.2fs %-2s dur %4.0fms  src %6.0f  score %6.0f  pred %6.0f  render %6.0f  err %+6.0fc"
              % ((r["pos"] + r["i"]) * 0, r["lyric"], r["dur_ms"], r["src"], r["tone"], r["pred"],
                 r["render"], r["render"] - r["src"]))

    # how many notes would a pure score-following render miss by >1 semitone?
    print("\nnotes where SCORE alone is >100c from source: %d / %d (%.0f%%)"
          % ((np.abs(score - src) > 100).sum(), len(ok), 100 * (np.abs(score - src) > 100).mean()))
    print("notes where RENDER is >100c from source: %d / %d (%.0f%%)"
          % ((np.abs(rend_r - src) > 100).sum(), len(ok), 100 * (np.abs(rend_r - src) > 100).mean()))


if __name__ == "__main__":
    main()
