"""Attribute the auto-pitch deviation to concrete mechanisms.

M1  frames outside any note span (head/tail padding) or over AP/SP rests are
    written into PITD. OpenUtau's own LoadRenderedPitch skips them via
    result.voiced; this writer cannot, because export-autopitch never exports it.
M2  '+' extension blocks carry a tone far from their parent syllable, so the
    melody handed to the pitch model is not the melody being sung.
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

    rows = []
    for ph in aut["phrases"]:
        part = parts[ph["part_position"]]
        notes = part["notes"]
        ticks = np.asarray(ph["ticks"]) + ph["position"]
        tones = np.asarray(ph["tones"]) * 100.0
        nt = np.asarray([ph["part_position"] + n["position"] for n in notes])
        ne = nt + np.asarray([n["duration"] for n in notes])
        for i, n in enumerate(notes):
            m = (ticks >= nt[i]) & (ticks < ne[i])
            if m.sum() < 3:
                continue
            pred = float(np.median(tones[m]))
            # nearest preceding sung (non-'+', non-rest) note
            prev_sung = None
            for j in range(i - 1, -1, -1):
                if notes[j]["lyric"] not in ("AP", "SP") and not notes[j]["lyric"].startswith("+"):
                    prev_sung = notes[j]["tone"]
                    break
            gap_before = 0.0
            if i > 0:
                gap_before = (nt[i] - ne[i - 1]) * TICK_MS
            rows.append(
                dict(
                    part=ph["part_position"], i=i, lyric=n["lyric"], tone=n["tone"],
                    dur_ms=n["duration"] * TICK_MS, pred=pred,
                    dev=pred - n["tone"] * 100.0,
                    nf=int(m.sum()),
                    gap_before_ms=gap_before,
                    prev_tone=notes[i - 1]["tone"] if i > 0 else None,
                    prev_lyric=notes[i - 1]["lyric"] if i > 0 else None,
                    prev_sung=prev_sung,
                    is_rest=n["lyric"] in ("AP", "SP"),
                    is_plus=n["lyric"].startswith("+"),
                )
            )

    def bucket(name, sel):
        if not sel:
            return
        d = np.array([r["dev"] for r in sel])
        print(
            "  %-34s n=%3d  median %+7.1f  p90|d| %7.1f  |d|>100c %3d"
            % (name, len(sel), np.median(d), np.percentile(np.abs(d), 90), (np.abs(d) > 100).sum())
        )

    print("deviation (prediction - score tone) by note class:")
    bucket("all", rows)
    bucket("rest AP/SP", [r for r in rows if r["is_rest"]])
    bucket("'+' extension", [r for r in rows if r["is_plus"]])
    bucket("sung", [r for r in rows if not r["is_rest"] and not r["is_plus"]])
    bucket("sung, prev note is rest", [r for r in rows if not r["is_rest"] and not r["is_plus"] and r["prev_lyric"] in ("AP", "SP")])
    bucket("sung, prev is '+'", [r for r in rows if not r["is_rest"] and not r["is_plus"] and (r["prev_lyric"] or "").startswith("+")])
    bucket("sung, gap>20ms before", [r for r in rows if not r["is_rest"] and not r["is_plus"] and r["gap_before_ms"] > 20])
    bucket("sung, dur<100ms", [r for r in rows if not r["is_rest"] and not r["is_plus"] and r["dur_ms"] < 100])

    # M2: how far is a '+' note's own tone from the last sung note of its syllable?
    jump = []
    for r in rows:
        if r["is_plus"] and r["prev_tone"] is not None:
            jump.append(r["tone"] - r["prev_tone"])
    jump = np.array(jump)
    print(
        "\n'+' tone minus immediately-previous note tone: median %+.1f semitones, "
        "|jump|>=1: %d/%d, >=3: %d"
        % (np.median(jump), (np.abs(jump) >= 1).sum(), len(jump), (np.abs(jump) >= 3).sum())
    )

    # M1: reconstruct what PITD points land outside voiced spans / on rests
    pitd_pts = json.loads((REPO / "scratch/diag_step1_pitch.json").read_text(encoding="utf-8"))
    tot = on_rest = out_span = 0
    for ph in pitd_pts["phrases"]:
        part = parts[ph["part_position"]]
        notes = part["notes"]
        xs = (np.asarray(ph["times_ms"]) - (part["position"] * TICK_MS)) / TICK_MS
        nt = np.asarray([n["position"] for n in notes])
        ne = nt + np.asarray([n["duration"] for n in notes])
        tot += len(xs)
        out_span += int(((xs < nt[0]) | (xs > ne[-1])).sum())
        idx = np.searchsorted(nt, xs, side="right") - 1
        ok = (idx >= 0) & (idx < len(notes))
        rest = np.asarray([n["lyric"] in ("AP", "SP") for n in notes])
        on_rest += int((ok & rest[np.clip(idx, 0, len(notes) - 1)]).sum())
    print(
        "\nPITD sample points: %d total ; outside first..last note %d (%.1f%%) ; over AP/SP rests %d (%.1f%%)"
        % (tot, out_span, 100 * out_span / tot, on_rest, 100 * on_rest / tot)
    )


if __name__ == "__main__":
    main()
