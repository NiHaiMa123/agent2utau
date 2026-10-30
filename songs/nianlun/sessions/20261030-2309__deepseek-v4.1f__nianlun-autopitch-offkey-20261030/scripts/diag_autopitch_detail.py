"""Detailed inspection of suspected auto-pitch artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
AUT = REPO / "scratch/nianlun_v3_rebuild/autopitch.json"
BASE = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"
PITCH = REPO / "scratch/nianlun_v3_rebuild/baseline_pitch.json"
FINAL = REPO / "scratch/nianlun_v3_rebuild_audio/final.ustx"
TICK_MS = 60000.0 / (120.0 * 480.0)


def main():
    aut = json.loads(AUT.read_text(encoding="utf-8"))
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    pit = json.loads(PITCH.read_text(encoding="utf-8"))
    final = yaml.safe_load(FINAL.read_text(encoding="utf-8"))

    parts = {p["position"]: p for p in base["voice_parts"]}
    fparts = {p["position"]: p for p in final["voice_parts"]}
    print("parts base/final:", len(parts), len(fparts))
    # note equality
    same = all(parts[k]["notes"] == fparts[k]["notes"] for k in parts if k in fparts)
    print("notes identical base vs final:", same)
    print("final curves:", [(c["abbr"], len(c["xs"])) for c in list(fparts.values())[0].get("curves", [])])

    # ---- 1. where are pitd points written, relative to phrase span / rests?
    pitd_in = 0
    pitd_before = 0
    pitd_after = 0
    pitd_over_rest = 0
    worst = []
    n_ph = 0
    for k, part in fparts.items():
        cur = [c for c in part.get("curves", []) if c.get("abbr") == "pitd"]
        if not cur:
            continue
        n_ph += 1
        xs = np.asarray(cur[0]["xs"])
        ys = np.asarray(cur[0]["ys"], dtype=float)
        dur = part["duration"]
        notes = part["notes"]
        nt = np.asarray([n["position"] for n in notes])
        ne = np.asarray([n["position"] + n["duration"] for n in notes])
        rest = np.asarray([n["lyric"] in ("AP", "SP") for n in notes])
        pitd_before += int((xs < nt[0]).sum())
        pitd_after += int((xs > ne[-1]).sum())
        pitd_in += len(xs)
        for x, y in zip(xs, ys):
            i = np.searchsorted(nt, x, side="right") - 1
            if 0 <= i < len(nt) and rest[i]:
                pitd_over_rest += 1
        print(
            "  part %7d dur %5d  pitd %4d pts  x[%d..%d]  note[%d..%d]  y[%+d..%+d]"
            % (k, dur, len(xs), xs.min(), xs.max(), nt[0], ne[-1], ys.min(), ys.max())
        )
        n_ph += 0
    print(
        "pitd points total %d ; before first note %d ; after last note %d ; over AP/SP %d"
        % (pitd_in, pitd_before, pitd_after, pitd_over_rest)
    )

    # ---- 2. per-note: prediction vs score, plus frame counts and note kind
    key = {}
    for b in pit["phrases"]:
        key[(b["part_position"], b["position"])] = np.asarray(b["before_pitd_cents"], dtype=float)
    rows = []
    for ph in aut["phrases"]:
        part = parts[ph["part_position"]]
        notes = part["notes"]
        nt = np.asarray([ph["part_position"] + n["position"] for n in notes])
        ne = np.asarray([ph["part_position"] + n["position"] + n["duration"] for n in notes])
        ticks = np.asarray(ph["ticks"]) + ph["position"]
        tones = np.asarray(ph["tones"]) * 100.0
        for i, n in enumerate(notes):
            m = (ticks >= nt[i]) & (ticks < ne[i])
            if m.sum() < 3:
                continue
            rows.append(
                dict(
                    part=ph["part_position"],
                    i=i,
                    lyric=n["lyric"],
                    tone=n["tone"],
                    dur=n["duration"],
                    pred=float(np.median(tones[m])),
                    dev=float(np.median(tones[m]) - n["tone"] * 100),
                    nf=int(m.sum()),
                )
            )
    print("notes measured", len(rows))
    for name, sel in [
        ("all", rows),
        ("AP/SP", [r for r in rows if r["lyric"] in ("AP", "SP")]),
        ("slur +", [r for r in rows if r["lyric"].startswith("+")]),
        ("sung", [r for r in rows if r["lyric"] not in ("AP", "SP") and not r["lyric"].startswith("+")]),
    ]:
        if not sel:
            continue
        d = np.array([r["dev"] for r in sel])
        print(
            "  %-7s n=%3d  median %+6.1f  p05 %+7.1f p95 %+7.1f  |d|>50c %3d  >100c %3d  >200c %3d"
            % (name, len(sel), np.median(d), np.percentile(d, 5), np.percentile(d, 95),
               (np.abs(d) > 50).sum(), (np.abs(d) > 100).sum(), (np.abs(d) > 200).sum())
        )

    # ---- 3. detail for the worst sung notes
    sung = [r for r in rows if r["lyric"] not in ("AP", "SP")]
    sung.sort(key=lambda r: -abs(r["dev"]))
    print("\nworst 15 non-AP notes:")
    for r in sung[:15]:
        print(
            "  part %7d i%2d %-2s tone %2d dur %4d nf %2d  pred %7.1f  dev %+7.1f"
            % (r["part"], r["i"], r["lyric"], r["tone"], r["dur"], r["nf"], r["pred"], r["dev"])
        )

    # ---- 4. one bad phrase in full detail
    target = sung[0]["part"]
    ph = [p for p in aut["phrases"] if p["part_position"] == target][0]
    part = parts[target]
    print("\n=== detail part %d (phrase %d)" % (target, ph["position"]))
    notes = part["notes"]
    print("  notes: pos dur tone lyric")
    for i, n in enumerate(notes):
        print("    %2d %6d %5d %3d %s" % (i, n["position"], n["duration"], n["tone"], n["lyric"]))
    ticks = np.asarray(ph["ticks"])
    tones = np.asarray(ph["tones"]) * 100.0
    print("  prediction: ticks[0]=%d tones[0]=%.1f  ticks[-1]=%d tones[-1]=%.1f  n=%d"
          % (ticks[0], tones[0], ticks[-1], tones[-1], len(ticks)))
    for t, c in list(zip(ticks, tones))[:12]:
        print("    tick %6d  %7.1f c" % (t, c))
    print("    ...")
    for t, c in list(zip(ticks, tones))[-8:]:
        print("    tick %6d  %7.1f c" % (t, c))


if __name__ == "__main__":
    main()
