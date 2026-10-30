"""Three-way comparison on identical note windows: source / score / render.

Removes the earlier window mismatch so the numbers are directly comparable.
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

WAVS = {
    "v3": V3 / "render" / "vocal_vocal.wav",
    "dspitch": REPO / "scratch/nianlun_v3_rebuild_audio" / "step1_vocal_vocal.wav",
}


def cents(hz):
    return np.where(hz > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz, 1e-6) / 440.0), np.nan)


def main():
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    aut = json.loads(AUT.read_text(encoding="utf-8"))
    # prediction per note, mean over note window
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

    tracks = {}
    for k, w in WAVS.items():
        f0 = extract_f0(str(w))
        tracks[k] = (np.asarray(f0["times"], float), cents(np.asarray(f0["f0_hz"], float)))

    rows = []
    for pi, part in enumerate(base["voice_parts"]):
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
            src_c = float(np.median(sv[m]))
            row = dict(lyric=n["lyric"], tone=n["tone"] * 100.0, src=src_c,
                       pred=pred.get((pos, i), np.nan))
            for k, (tt, cc) in tracks.items():
                mm = (tt >= a) & (tt < b) & np.isfinite(cc)
                row[k] = float(np.median(cc[mm])) if mm.sum() >= 3 else np.nan
            rows.append(row)

    print("notes:", len(rows))
    print("\nper-note median pitch, error vs source (cents):")
    for k in ["v3", "dspitch"]:
        e = np.array([r[k] - r["src"] for r in rows if np.isfinite(r[k])])
        print(
            "  %-8s n=%3d  median %+7.1f  |err| median %6.1f  p90 %6.1f  |e|>50c %3d  >100c %3d  >200c %3d"
            % (k, len(e), np.median(e), np.median(np.abs(e)), np.percentile(np.abs(e), 90),
               (np.abs(e) > 50).sum(), (np.abs(e) > 100).sum(), (np.abs(e) > 200).sum())
        )
    e = np.array([r["pred"] - r["src"] for r in rows if np.isfinite(r["pred"])])
    print(
        "  %-8s n=%3d  median %+7.1f  |err| median %6.1f  p90 %6.1f  |e|>50c %3d  >100c %3d  >200c %3d"
        % ("pred", len(e), np.median(e), np.median(np.abs(e)), np.percentile(np.abs(e), 90),
           (np.abs(e) > 50).sum(), (np.abs(e) > 100).sum(), (np.abs(e) > 200).sum())
    )
    e = np.array([r["tone"] - r["src"] for r in rows])
    print(
        "  %-8s n=%3d  median %+7.1f  |err| median %6.1f  p90 %6.1f  |e|>50c %3d  >100c %3d  >200c %3d"
        % ("score", len(e), np.median(e), np.median(np.abs(e)), np.percentile(np.abs(e), 90),
           (np.abs(e) > 50).sum(), (np.abs(e) > 100).sum(), (np.abs(e) > 200).sum())
    )

    print("\nrender vs prediction (is the audio following the curve?):")
    for k in ["v3", "dspitch"]:
        e = np.array([r[k] - r["pred"] for r in rows if np.isfinite(r[k]) and np.isfinite(r["pred"])])
        print("  %-8s |d| median %6.1f  p90 %6.1f  |d|>50c %3d/%d"
              % (k, np.median(np.abs(e)), np.percentile(np.abs(e), 90), (np.abs(e) > 50).sum(), len(e)))


if __name__ == "__main__":
    main()
