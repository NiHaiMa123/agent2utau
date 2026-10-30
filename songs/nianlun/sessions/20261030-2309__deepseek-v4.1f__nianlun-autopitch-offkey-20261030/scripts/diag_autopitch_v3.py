"""Diagnose why the v3 auto-pitch (DiffSinger dspitch) render sounds off-key.

Reads the 2026-10-30 22:26-22:43 rebuild artifacts and reports, per note:
  - predicted (dspitch) pitch vs score nominal tone
  - how the pitd curve written into final.ustx maps back onto baseline pitch
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
AUT = REPO / "scratch" / "nianlun_v3_rebuild" / "autopitch.json"
BASE = REPO / "scratch" / "nianlun_v3_rebuild" / "baseline_no_pitch_no_dyn.ustx"
PITCH = REPO / "scratch" / "nianlun_v3_rebuild" / "baseline_pitch.json"
FINAL = REPO / "scratch" / "nianlun_v3_rebuild_audio" / "final.ustx"
TICK_MS = 60000.0 / (120.0 * 480.0)


def load():
    aut = json.loads(AUT.read_text(encoding="utf-8"))
    pit = json.loads(PITCH.read_text(encoding="utf-8"))
    base = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    final = yaml.safe_load(FINAL.read_text(encoding="utf-8"))
    return aut, pit, base, final


def note_table(aut, base):
    parts = {p["position"]: p for p in base["voice_parts"]}
    rows = []
    for ph in aut["phrases"]:
        part = parts[ph["part_position"]]
        notes = part["notes"]
        nt = np.array([ph["part_position"] + n["position"] for n in notes])
        ne = np.array([ph["part_position"] + n["position"] + n["duration"] for n in notes])
        tone = np.array([n["tone"] for n in notes], dtype=float)
        lyr = [n["lyric"] for n in notes]
        ticks = np.asarray(ph["ticks"]) + ph["position"]
        tones = np.asarray(ph["tones"]) * 100.0
        for i in range(len(notes)):
            m = (ticks >= nt[i]) & (ticks < ne[i])
            if m.sum() < 3:
                continue
            rows.append(
                dict(
                    part=ph["part_position"],
                    phrase=ph["position"],
                    note=i,
                    lyric=lyr[i],
                    tone=tone[i],
                    pred=float(np.median(tones[m])),
                    dev=float(np.median(tones[m]) - tone[i] * 100.0),
                    n=int(m.sum()),
                    t0=float(nt[i]),
                    t1=float(ne[i]),
                )
            )
    return rows


def main():
    aut, pit, base, final = load()
    rows = note_table(aut, base)
    dev = np.array([r["dev"] for r in rows])
    print(f"notes with prediction: {len(rows)}")
    print(
        "dev pred-nominal (cents): median %.1f mean %.1f p05 %.1f p95 %.1f min %.1f max %.1f"
        % (np.median(dev), dev.mean(), np.percentile(dev, 5), np.percentile(dev, 95), dev.min(), dev.max())
    )
    print(
        "|dev|>100c %d  >300c %d  >600c %d"
        % ((abs(dev) > 100).sum(), (abs(dev) > 300).sum(), (abs(dev) > 600).sum())
    )
    rows.sort(key=lambda r: -abs(r["dev"]))
    print("\nworst 25 notes:")
    for r in rows[:25]:
        print(
            "  %-3s tone %3d pred %7.1f dev %+7.1f (%d smp) part %d note %d"
            % (r["lyric"], r["tone"], r["pred"], r["dev"], r["n"], r["part"], r["note"])
        )

    # ---- how pitd was written and what it reconstructs to
    base_by_pos = {}
    for b in pit["phrases"]:
        base_by_pos.setdefault(b["part_position"], {})[b["position"]] = np.asarray(
            b["before_pitd_cents"], dtype=np.float64
        )
    final_parts = {p["position"]: p for p in final["voice_parts"]}
    off_by_key = {(p["part_position"], p["position"]): p for p in aut["phrases"]}

    errs = []
    for pi, part in enumerate(final["voice_parts"]):
        pos = part["position"]
        cur = [c for c in part.get("curves", []) if c.get("abbr") == "pitd"]
        if not cur:
            continue
        xs = np.asarray(cur[0]["xs"])
        ys = np.asarray(cur[0]["ys"], dtype=float)
        for (ppos, phpos), off in off_by_key.items():
            if ppos != pos:
                continue
            base = base_by_pos.get(pos, {}).get(phpos)
            if base is None:
                continue
            leading = 0
            t = np.asarray(off["ticks"])
            tone = np.asarray(off["tones"]) * 100.0
            pidx = np.clip(((t + leading) // 5).astype(int), 0, len(base) - 1)
            y_ref = np.round(tone - base[pidx])
            x_ref = phpos - pos + t
            # compare to what the writer actually stored inside this x range
            m = (xs >= x_ref.min()) & (xs <= x_ref.max())
            if m.sum() < 3:
                continue
            y_have = np.interp(x_ref, xs, ys)
            errs.append(np.abs(y_have - y_ref))
    if errs:
        e = np.concatenate(errs)
        print(
            "\npitd curve vs official formula (cents): median %.2f p95 %.2f max %.2f  (n=%d)"
            % (np.median(e), np.percentile(e, 95), e.max(), len(e))
        )


if __name__ == "__main__":
    main()
