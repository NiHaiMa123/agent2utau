"""Where does the auto-pitch line itself go wrong?

Hypotheses to test against the exported predictor output:
  H1  notes shorter than one model frame get no frame of their own -> predictor
      output for that span belongs to a neighbour.
  H2  the pitch model's head/tail padding & rest frames are not masked here, so
      silence artifacts get written into PITD (OpenUtau masks via result.voiced).
  H3  '+' slur notes carry a different tone than their sung parent, so the model
      is fed a nominal melody that is not the melody being sung.
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
FRAME_MS = 512 / 44100 * 1000  # hop 512 @44.1k -> 11.61 ms
FRAME_TICK = FRAME_MS / TICK_MS  # ticks per model frame (~11.1 ticks)


def main():
    aut = json.loads(AUT.read_text(encoding="utf-8"))
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    parts = {p["position"]: p for p in base["voice_parts"]}

    # frame spacing actually present in the predictor output
    dts = []
    for ph in aut["phrases"]:
        dts.extend(np.diff(ph["ticks"]).tolist())
    dts = np.array(dts)
    print("predictor tick spacing: median %.2f ticks  (=%.2f ms)  uniq %s"
          % (np.median(dts), np.median(dts) * TICK_MS, sorted(set(np.round(dts, 1)))[:6]))

    rows = []
    for ph in aut["phrases"]:
        part = parts[ph["part_position"]]
        notes = part["notes"]
        ticks = np.asarray(ph["ticks"]) + ph["position"]
        tones = np.asarray(ph["tones"]) * 100.0
        for i, n in enumerate(notes):
            a = ph["part_position"] + n["position"]
            b = a + n["duration"]
            m = (ticks >= a) & (ticks < b)
            rows.append(
                dict(
                    part=ph["part_position"], i=i, lyric=n["lyric"], tone=n["tone"],
                    dur=n["duration"], dur_ms=n["duration"] * TICK_MS,
                    nf=int(m.sum()),
                    pred=float(np.median(tones[m])) if m.sum() else float("nan"),
                )
            )

    nf = np.array([r["nf"] for r in rows])
    dur = np.array([r["dur_ms"] for r in rows])
    print("\nnotes total %d ; frames per note: median %d  min %d" % (len(rows), int(np.median(nf)), nf.min()))
    for lo, hi in [(0, 15), (15, 25), (25, 40), (40, 60), (60, 120), (120, 1e9)]:
        sel = [r for r in rows if lo <= r["dur_ms"] < hi]
        if not sel:
            continue
        d = np.array([r["pred"] - r["tone"] * 100 for r in sel if np.isfinite(r["pred"])])
        print(
            "  dur %5.0f-%6.0fms  n=%3d  frames/note %.1f  |dev|>100c %3d  median dev %+7.1f"
            % (lo, min(hi, 9999), len(sel), np.mean([r["nf"] for r in sel]),
               (np.abs(d) > 100).sum(), np.median(d))
        )

    # H3: are '+' notes given a tone different from the preceding sung note?
    plus_bad = 0
    plus = 0
    jumps = []
    for k, p in parts.items():
        ns = p["notes"]
        for i, n in enumerate(ns):
            if n["lyric"].startswith("+") and i > 0:
                plus += 1
                j = n["tone"] - ns[i - 1]["tone"]
                jumps.append(j)
                if abs(j) >= 2:
                    plus_bad += 1
    jumps = np.array(jumps)
    print("\n'+' notes %d ; tone jump vs previous note >=2 semitones: %d (%.0f%%) ; max %d"
          % (plus, plus_bad, 100 * plus_bad / max(plus, 1), np.abs(jumps).max()))
    print("  jump histogram:", {int(k): int(v) for k, v in zip(*np.unique(jumps, return_counts=True))})

    # H1/H2: pads. Does the prediction for frames outside note spans differ a lot
    # from the nearest note tone? Those are the frames OpenUtau would mask.
    pads = []
    for ph in aut["phrases"]:
        part = parts[ph["part_position"]]
        notes = part["notes"]
        nt = np.asarray([ph["part_position"] + n["position"] for n in notes])
        ne = np.asarray([ph["part_position"] + n["position"] + n["duration"] for n in notes])
        ticks = np.asarray(ph["ticks"]) + ph["position"]
        tones = np.asarray(ph["tones"]) * 100.0
        m = (ticks < nt[0]) | (ticks >= ne[-1])
        if m.sum():
            pads.append(tones[m])
    if pads:
        p = np.concatenate(pads)
        print("\nframes outside the note span (padding): %d  cents range %.0f..%.0f" % (len(p), p.min(), p.max()))


if __name__ == "__main__":
    main()
