"""Do the worst auto-pitch errors land on a NEIGHBOUR's tone instead of the
note's own tone? That would be frame-allocation drift, not model noise.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
AUT = REPO / "scratch/nianlun_v3_rebuild/autopitch.json"
BASE = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"


def main():
    aut = json.loads(AUT.read_text(encoding="utf-8"))
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    parts = {p["position"]: p for p in base["voice_parts"]}

    rows = []
    for ph in aut["phrases"]:
        part = parts[ph["part_position"]]
        notes = part["notes"]
        pos0 = ph["part_position"]
        nt = np.asarray([pos0 + n["position"] for n in notes])
        ticks = np.asarray(ph["ticks"]) + ph["position"]
        tones = np.asarray(ph["tones"]) * 100.0
        for i, n in enumerate(notes):
            a = pos0 + n["position"]
            m = (ticks >= a) & (ticks < a + n["duration"])
            if m.sum() < 5:
                continue
            rows.append(
                dict(
                    part=pos0, i=i, n=len(notes), lyric=n["lyric"], tone=n["tone"] * 100.0,
                    dur=n["duration"], pred=float(np.median(tones[m])),
                    prev=[notes[j]["tone"] * 100.0 for j in range(max(0, i - 2), i)],
                    nxt=[notes[j]["tone"] * 100.0 for j in range(i + 1, min(len(notes), i + 3))],
                )
            )

    bad = [r for r in rows if abs(r["pred"] - r["tone"]) > 200]
    print("notes with |pred - own tone| > 200c: %d / %d" % (len(bad), len(rows)))

    expl = 0
    detail = []
    for r in bad:
        cands = r["prev"] + r["nxt"]
        if not cands:
            continue
        best = min(cands, key=lambda c: abs(r["pred"] - c))
        if abs(r["pred"] - best) < 120:
            expl += 1
            detail.append((r, best))
    print("of those, prediction sits within 120c of a NEIGHBOUR note's tone: %d (%.0f%%)"
          % (expl, 100 * expl / max(len(bad), 1)))

    print("\nexamples:")
    for r, best in detail[:12]:
        print("  part %7d note %2d/%-2d %-2s tone %5.0f dur %4d  pred %6.1f  -> neighbour %5.0f  (off own %+6.0f)"
              % (r["part"], r["i"] + 1, r["n"], r["lyric"], r["tone"], r["dur"], r["pred"], best,
                 r["pred"] - r["tone"]))

    # distribution of duration among unexplained bad notes
    unexp = [r for r in bad if not any(abs(r["pred"] - c) < 120 for c in r["prev"] + r["nxt"])]
    if unexp:
        d = np.array([r["dur"] for r in unexp]) * 60000 / (120 * 480)
        print("\nunexplained bad notes: %d ; duration median %.0fms  min %.0f  max %.0f"
              % (len(unexp), np.median(d), d.min(), d.max()))
        print("  their |pred - tone| median %.0fc" % np.median([abs(r["pred"] - r["tone"]) for r in unexp]))


if __name__ == "__main__":
    main()
