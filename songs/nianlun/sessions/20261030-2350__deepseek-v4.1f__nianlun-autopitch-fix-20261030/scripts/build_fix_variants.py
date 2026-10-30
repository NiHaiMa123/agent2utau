"""Build the auto-pitch fix variants for 骞磋疆 v3, without touching the source.

Fix 1 (+merge)  Merge '+' extension blocks back into their parent syllable.
                The score's declared melody then matches the sung melody, and the
                predictor is not asked to sing an invented leap on a fragment.
Fix 2 (+merge + shortinherit)
                Additionally absorb notes shorter than one predictor frame budget
                into a neighbour, so no note is left with too few frames.

Outputs go to runs/experiments/nianlun-autopitch-fix-20261030/ (Git-ignored).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[5]  # scripts -> session -> sessions -> nianlun -> songs -> repo
SRC = REPO / "scratch/nianlun_v3_rebuild/baseline_no_pitch_no_dyn.ustx"
OUT = REPO / "runs/experiments/nianlun-autopitch-fix-20261030"
TICK_MS = 60000.0 / (120.0 * 480.0)
SHORT_MS = 150.0          # below this a note has too few predictor frames


def dump(doc, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False,
                                   default_flow_style=False, width=10_000),
                    encoding="utf-8")


def is_plus(n):
    return str(n["lyric"]).startswith("+")


def is_rest(n):
    return str(n["lyric"]) in ("SP", "AP")


def merge_plus(doc, log):
    """Fold each '+' block into the note it extends (same syllable)."""
    merged = 0
    for vp in doc["voice_parts"]:
        keep = []
        for n in vp["notes"]:
            if is_plus(n) and keep and not is_rest(n):
                prev = keep[-1]
                if not is_rest(prev):
                    # extend the parent to cover the '+': same start, longer duration
                    prev["duration"] = int(n["position"]) + int(n["duration"]) - int(prev["position"])
                    merged += 1
                    log.append(dict(part=vp["position"], note=int(n["position"]),
                                    tone_parent=int(prev["tone"]), tone_plus=int(n["tone"]),
                                    dur_plus=int(n["duration"])))
                    continue
            keep.append(n)
        vp["notes"] = keep
    return merged


def absorb_short(doc, log, min_ms=SHORT_MS, rounds=4):
    """Extend short sung notes by taking time from the next note (or the previous)."""
    fixed = 0
    for _ in range(rounds):
        changed = False
        for vp in doc["voice_parts"]:
            ns = vp["notes"]
            i = 0
            while i < len(ns) - 1:
                n = ns[i]
                if is_rest(n) or is_plus(n):
                    i += 1
                    continue
                if n["duration"] * TICK_MS >= min_ms:
                    i += 1
                    continue
                nxt = ns[i + 1]
                need = int(round(min_ms / TICK_MS)) - int(n["duration"])
                avail = int(nxt["duration"]) - int(round(min_ms / TICK_MS))
                if is_rest(nxt) and avail <= 0:
                    i += 1
                    continue
                take = min(need, max(0, avail))
                if take <= 0:
                    i += 1
                    continue
                n["duration"] = int(n["duration"]) + take
                nxt["position"] = int(nxt["position"]) + take
                nxt["duration"] = int(nxt["duration"]) - take
                log.append(dict(part=vp["position"], note=int(n["position"]),
                                lyric=str(n["lyric"]), before_ms=round(n["duration"] * TICK_MS),
                                took=take))
                fixed += 1
                changed = True
                i += 1
            # drop zero-length notes
            vp["notes"] = [x for x in vp["notes"] if int(x["duration"]) > 0]
        if not changed:
            break
    return fixed


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = yaml.safe_load(SRC.read_text(encoding="utf-8"))

    for tag, do_short in (("B_plusmerge", False), ("C_plusmerge_short", True)):
        doc = yaml.safe_load(SRC.read_text(encoding="utf-8"))
        log = []
        m = merge_plus(doc, log)
        s = absorb_short(doc, log) if do_short else 0
        tot = sum(len(vp["notes"]) for vp in doc["voice_parts"])
        plus = sum(1 for vp in doc["voice_parts"] for n in vp["notes"] if is_plus(n))
        durs = [n["duration"] * TICK_MS for vp in doc["voice_parts"] for n in vp["notes"]
                if not is_rest(n)]
        plus_durs = [n["duration"] * TICK_MS for vp in doc["voice_parts"]
                     for n in vp["notes"] if is_plus(n)]
        dump(doc, OUT / f"{tag}.ustx")
        (OUT / f"{tag}_log.json").write_text(
            json.dumps(dict(merged=m, short_fixed=s, notes=tot, plus_left=plus,
                            min_dur_ms=round(min(durs)) if durs else None,
                            min_plus_dur_ms=round(min(plus_durs)) if plus_durs else None,
                            edits=log[:2000]),
                       ensure_ascii=False, indent=1), encoding="utf-8")
        print("%-20s merged=%d short_fixed=%d notes=%d plus_left=%d min_dur=%.0fms"
              % (tag, m, s, tot, plus, min(durs) if durs else -1))


if __name__ == "__main__":
    main()
