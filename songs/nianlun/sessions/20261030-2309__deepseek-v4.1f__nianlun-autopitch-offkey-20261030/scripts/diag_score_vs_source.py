"""Root-cause measurement.

A. How far is the SCORE's nominal tone from the source singer's F0, per note?
   v3 hid any such gap by hand-drawing PITD straight onto the source F0 trace;
   auto-pitch replaces that with the model's own prediction, which follows the
   score. So the score-vs-source gap IS the audible error.
B. Why do '+' extension blocks carry a different tone from their parent syllable?
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
from nianlun_v3_source import Source, filled_track  # noqa: E402

V3 = REPO / "runs/production/nianlun-from-scratch-v3-20261030"
BASE = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"
TICK_MS = 60000.0 / (120.0 * 480.0)
SRC = Source(V3)


def main():
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))

    rows = []
    for part in base["voice_parts"]:
        pos = part["position"]
        notes = part["notes"]
        for i, n in enumerate(notes):
            if n["lyric"] in ("AP", "SP"):
                continue
            a = (pos + n["position"]) * TICK_MS / 1000.0
            b = (pos + n["position"] + n["duration"]) * TICK_MS / 1000.0
            ft = filled_track(SRC, a, b)
            if not ft:
                continue
            t, c = ft[0], ft[1]
            m = (t >= a) & (t < b)
            if m.sum() < 3:
                continue
            src_c = float(np.median(c[m]))
            rows.append(
                dict(
                    part=pos, i=i, lyric=n["lyric"], tone=n["tone"],
                    tone_c=n["tone"] * 100.0, src_c=src_c,
                    err_tone_vs_src=src_c - n["tone"] * 100.0,
                    is_plus=n["lyric"].startswith("+"),
                )
            )

    print("notes with source coverage:", len(rows))
    for name, sel in [
        ("all", rows),
        ("sung (no +)", [r for r in rows if not r["is_plus"]]),
        ("'+' extension", [r for r in rows if r["is_plus"]]),
    ]:
        if not sel:
            continue
        e = np.array([r["err_tone_vs_src"] for r in sel])
        print(
            "  %-16s n=%3d  score-tone - source: median %+7.1fc  mean %+7.1fc  p05 %+7.1f p95 %+7.1f  "
            "|e|>50c %3d  >100c %3d  >200c %3d"
            % (name, len(sel), np.median(e), e.mean(), np.percentile(e, 5), np.percentile(e, 95),
               (np.abs(e) > 50).sum(), (np.abs(e) > 100).sum(), (np.abs(e) > 200).sum())
        )

    # per-syllable: does the '+' block sit on the same pitch as its parent?
    print("\n'+' blocks vs their parent syllable (score tone vs source):")
    shown = 0
    for r in rows:
        if r["is_plus"] and abs(r["err_tone_vs_src"]) > 100 and shown < 12:
            print(
                "  part %7d note %2d %-2s  tone %3d (%.0fc)  source %.0fc  -> score off by %+.0fc"
                % (r["part"], r["i"], r["lyric"], r["tone"], r["tone_c"], r["src_c"], r["err_tone_vs_src"])
            )
            shown += 1

    np.save(REPO / "scratch/diag_score_vs_src.npy",
            np.array([[r["tone_c"], r["src_c"], float(r["is_plus"])] for r in rows]))


if __name__ == "__main__":
    main()
