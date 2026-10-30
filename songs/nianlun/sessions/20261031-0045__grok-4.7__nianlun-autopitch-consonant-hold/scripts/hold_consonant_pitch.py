"""Hold the current note across the next syllable's early consonant.

DiffSinger's pitch model starts the next note while that note's initial is
still inside the current note (ph_dur). The vowel stays on pitch. This script
replaces only those lead frames, then bakes PITD with the same index formula
as scratch/render_nianlun_func_dspitch.py. Notes, lyrics and phoneme times
are not changed.

Run from the repo root:
  .venv\\Scripts\\python.exe songs/nianlun/sessions/20261031-0045__grok-4.7__nianlun-autopitch-consonant-hold/scripts/hold_consonant_pitch.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
SRC = REPO / "runs" / "nianlun_functional_20260929" / "nianlun_functional.ustx"
AUTO = REPO / "scratch" / "nianlun_func_autopitch.json"
PITCH = REPO / "scratch" / "nianlun_func_pitch.json"
PHONES = REPO / "scratch" / "nianlun_func_phones.json"
RUN = REPO / "runs" / "experiments" / "nianlun-autopitch-consonant-hold-20261031"
TICK_S = 60.0 / (120.0 * 480.0)
REST = {"AP", "SP"}


def ms_of(part_pos, phrase_pos, tick):
    return (phrase_pos + float(tick)) * TICK_S * 1000.0


def load():
    auto = json.loads(AUTO.read_text(encoding="utf-8"))
    base = json.loads(PITCH.read_text(encoding="utf-8"))
    phones = json.loads(PHONES.read_text(encoding="utf-8"))
    proj = yaml.safe_load(SRC.read_text(encoding="utf-8"))
    return auto, base, phones, proj


def samples_for(auto, part_pos):
    rows = []
    for pi, ph in enumerate(auto["phrases"]):
        if ph["part_position"] != part_pos:
            continue
        for i, (tick, tone) in enumerate(zip(ph["ticks"], ph["tones"])):
            rows.append({
                "phrase": pi,
                "i": i,
                "ms": ms_of(part_pos, ph["position"], tick),
                "tone": float(tone),
            })
    rows.sort(key=lambda r: (r["ms"], r["phrase"], r["i"]))
    return rows


def first_phones(part):
    found = {}
    for ph in part["phrases"]:
        for p in ph["phones"]:
            for idx in p["owner_note_indices"]:
                prev = found.get(idx)
                if prev is None or p["start_ms"] < prev[0]:
                    found[idx] = (p["start_ms"], p["phoneme"])
    return found


def apply_holds(notes, found, times, tones):
    """Return held tones (MIDI semitones) and a list of windows."""
    out = tones.copy()
    windows = []
    claimed = np.zeros(len(tones), dtype=bool)
    for b in notes:
        info = found.get(b["note_index"])
        if info is None or str(b["lyric"]) in REST:
            continue
        cons, phoneme = info
        if cons >= b["start_ms"] - 5.0:
            continue
        covered = [
            n for n in notes
            if n["end_ms"] > cons + 0.5 and n["start_ms"] < b["start_ms"] - 0.5
            and str(n["lyric"]) not in REST
        ]
        covered.sort(key=lambda n: n["start_ms"])
        for k, n in enumerate(covered):
            is_last = k == len(covered) - 1
            seg1 = min(b["start_ms"], n["end_ms"])
            dur = n["end_ms"] - n["start_ms"]
            if cons >= n["start_ms"] - 0.5:
                guard = min(40.0, 0.30 * dur)
                guard_t = n["start_ms"] + guard
                own = float(n["tone"])
                # The dive often starts before the consonant label. Freeze from
                # the last frame that is still within 60c of this note, instead
                # of freezing a pitch that has already left.
                on_note = (times >= guard_t) & (times < cons) & (np.abs(tones - own) <= 0.60)
                if np.any(on_note):
                    last = int(np.flatnonzero(on_note)[-1])
                    win0 = float(times[last])
                    hold = float(tones[last])
                    source = "model-before-consonant"
                else:
                    win0 = max(guard_t, cons - 20.0)
                    hold = own
                    source = "score-tone"
            else:
                # The next initial covers this whole note, so the model never
                # established the note. Keep the score tone.
                win0 = n["start_ms"]
                hold = float(n["tone"])
                source = "score-tone"
            if win0 >= seg1 - 5.0:
                continue
            ramp = 0.0
            dest = hold
            if is_last:
                ramp = min(40.0, max(0.0, (seg1 - win0) * 0.45))
                j = int(np.searchsorted(times, seg1, side="left"))
                dest = float(tones[j]) if j < len(tones) else hold
            m = (times >= win0) & (times < seg1) & ~claimed
            if not np.any(m):
                continue
            claimed[m] = True
            if ramp <= 1.0:
                out[m] = hold
            else:
                ramp_at = seg1 - ramp
                rel = times[m]
                held = rel < ramp_at
                idx = np.flatnonzero(m)
                out[idx[held]] = hold
                gliding = ~held
                if np.any(gliding):
                    u = (rel[gliding] - ramp_at) / ramp
                    out[idx[gliding]] = hold + u * (dest - hold)
            windows.append({
                "lyric": str(n["lyric"]),
                "next": str(b["lyric"]),
                "phoneme": phoneme,
                "win0": win0,
                "seg1": seg1,
                "hold": hold,
                "dest": dest,
                "ramp_ms": ramp,
                "source": source,
                "leap_c": (b["tone"] - n["tone"]) * 100.0,
            })
    return out, windows, claimed


def region_errors(notes, found, times, tones):
    before, during = [], []
    for i, a in enumerate(notes):
        if i + 1 >= len(notes):
            break
        b = notes[i + 1]
        if str(a["lyric"]) in REST or str(b["lyric"]) in REST or b["lyric"] == "+":
            continue
        info = found.get(b["note_index"])
        if info is None:
            continue
        cons = info[0]
        leap = (b["tone"] - a["tone"]) * 100.0
        if abs(leap) < 300 or cons >= b["start_ms"] - 5:
            continue
        own = a["tone"] * 100.0
        pre = (times >= a["start_ms"] + 40.0) & (times < cons)
        mid = (times >= cons) & (times < b["start_ms"])
        if pre.sum() >= 2:
            before.append(float(np.median(np.abs(tones[pre] * 100.0 - own))))
        if mid.sum() >= 1:
            during.append(float(np.median(np.abs(tones[mid] * 100.0 - own))))
    return np.asarray(before), np.asarray(during)


def write_pitd(proj, auto, base_doc, new_tone_by_phrase):
    total = 0
    for part in proj["voice_parts"]:
        pos = part["position"]
        base_by_pos = {
            b["position"]: np.asarray(b["before_pitd_cents"], dtype=np.float64)
            for b in base_doc["phrases"] if b["part_position"] == pos
        }
        xs, ys = [], []
        for pi, o in enumerate(auto["phrases"]):
            if o["part_position"] != pos:
                continue
            base = base_by_pos.get(o["position"])
            if base is None or len(base) == 0:
                continue
            tones = new_tone_by_phrase[pi]
            for t, tone in zip(o["ticks"], tones):
                x = int(round(o["position"] - pos + t))
                pidx = int((t + 0) // 5)
                pidx = max(0, min(len(base) - 1, pidx))
                y = int(round(float(tone) * 100.0 - base[pidx]))
                xs.append(x)
                ys.append(max(-1200, min(1200, y)))
        pairs = sorted(dict(zip(xs, ys)).items())
        curves = [c for c in part.get("curves", []) if c.get("abbr") != "pitd"]
        curves.append({"abbr": "pitd", "xs": [p[0] for p in pairs], "ys": [p[1] for p in pairs]})
        part["curves"] = curves
        total += len(pairs)
    return total


def main():
    auto, base, phones, proj = load()
    part = phones["parts"][0]
    if len(phones["parts"]) != 1 or len(proj["voice_parts"]) != 1:
        raise SystemExit("expected one voice part")
    if len(part["notes"]) != len(proj["voice_parts"][0]["notes"]):
        raise SystemExit("phone notes and ustx notes differ")
    notes = part["notes"]
    part_pos = proj["voice_parts"][0]["position"]
    rows = samples_for(auto, part_pos)
    times = np.asarray([r["ms"] for r in rows])
    original = np.asarray([r["tone"] for r in rows])
    found = first_phones(part)
    held, windows, claimed = apply_holds(notes, found, times, original)

    b0, d0 = region_errors(notes, found, times, original)
    b1, d1 = region_errors(notes, found, times, held)
    changed = np.abs(held - original) > 1e-4
    flat = []
    for w in windows:
        host = [n for n in notes if n["start_ms"] - 1 <= w["win0"] < n["end_ms"] + 1]
        if not host:
            continue
        own = host[0]["tone"] * 100.0
        ramp_at = w["seg1"] - w["ramp_ms"]
        flat_m = (times >= w["win0"]) & (times < ramp_at)
        if flat_m.sum():
            flat.append(float(np.median(np.abs(held[flat_m] * 100.0 - own))))
    flat = np.asarray(flat)

    def brief(name, arr):
        print(f"  {name}: n={len(arr)} med {np.median(arr):.0f}c p90 {np.percentile(arr, 90):.0f}c >80c {(arr > 80).sum()}")

    print(f"windows {len(windows)}  frames changed {int(changed.sum())}/{len(held)}")
    print("before consonant, |pitch-own|  (3st+ leaps)")
    brief("model", b0)
    brief("held ", b1)
    print("during next initial, still inside this note (includes the ending ramp)")
    brief("model", d0)
    brief("held ", d1)
    print("flat hold only, before the 40ms ramp into the next note")
    brief("held ", flat)
    print(f"  fully-covered notes snapped to score tone: {sum(1 for w in windows if w['source']=='score-tone')}")

    # 成 around 20.4s
    print("成→指")
    for w in windows:
        if w["lyric"] == "成" and w["next"] == "指" and 20000 < w["win0"] < 22000:
            print(f"  hold {w['hold']*100:.0f}c -> dest {w['dest']*100:.0f}c  "
                  f"{w['win0']:.0f}-{w['seg1']:.0f} ramp {w['ramp_ms']:.0f}ms  {w['source']}")
    print("  ms  model  held  phone")
    spans = []
    for ph in part["phrases"]:
        for p in ph["phones"]:
            if 20400 <= p["end_ms"] and p["start_ms"] <= 21050:
                spans.append(p)
    for t, a, h in zip(times, original, held):
        if 20680 <= t <= 20940 and int(t) % 22 < 12:
            owner = "?"
            for p in spans:
                if p["start_ms"] <= t < p["end_ms"]:
                    owner = f"{p['phoneme']} {p['owner_note_indices']}"
                    break
            print(f"  {t:8.0f}  {a*100:7.0f}  {h*100:7.0f}  {owner}")

    # write tones back per phrase, in original phrase order
    by_phrase = {pi: np.array(ph["tones"], dtype=np.float64) for pi, ph in enumerate(auto["phrases"])}
    for r, tone in zip(rows, held):
        by_phrase[r["phrase"]][r["i"]] = tone

    RUN.mkdir(parents=True, exist_ok=True)
    dst = RUN / "nianlun_functional_held.ustx"
    shutil.copy2(SRC, dst)
    out_proj = yaml.safe_load(dst.read_text(encoding="utf-8"))
    if "name" in out_proj:
        out_proj["name"] = "nianlun_functional_held"
    total = write_pitd(out_proj, auto, base, by_phrase)
    dst.write_text(yaml.safe_dump(out_proj, allow_unicode=True, sort_keys=False,
                                  default_flow_style=False, width=10_000), encoding="utf-8")
    stats = {
        "windows": len(windows),
        "frames_changed": int(changed.sum()),
        "frames": int(len(held)),
        "pitd_points": total,
        "before_model_median_c": float(np.median(b0)),
        "before_held_median_c": float(np.median(b1)),
        "during_model_median_c": float(np.median(d0)),
        "during_held_median_c": float(np.median(d1)),
        "during_model_p90_c": float(np.percentile(d0, 90)),
        "during_held_p90_c": float(np.percentile(d1, 90)),
        "during_model_over_80": int((d0 > 80).sum()),
        "during_held_over_80": int((d1 > 80).sum()),
        "flat_held_median_c": float(np.median(flat)),
        "flat_held_p90_c": float(np.percentile(flat, 90)),
        "flat_held_over_80": int((flat > 80).sum()),
        "score_tone_snaps": int(sum(1 for w in windows if w["source"] == "score-tone")),
        "ustx": str(dst),
    }
    (RUN / "hold_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
