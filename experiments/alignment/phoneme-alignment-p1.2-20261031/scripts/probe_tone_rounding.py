"""P1.2-E: is the MIDI rounding of the GAME tone truncate or round?

The production builder truncates the fractional MIDI value of a GAME event
(``int(tone)``); the older song scripts rounded.  The two rules disagree on
about 46 % of the voiced notes, which is a lot - but "they differ" is not
evidence that either one is right.

This script measures which rule agrees with the *original* recording:

* the frozen GAME notes give the fractional MIDI value per event,
* the FCPE / RMVPE F0 curves of the same vocals give the sung pitch,
* for every voiced note the F0 inside its window is converted to MIDI and
  compared with both rules.

Only the base pitch is checked - no vibrato, no note curve.  Where the two
F0 trackers disagree with each other or with GAME by an octave, the note is
counted as *uncertain* instead of being counted for one side.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

RUN_ID = "phoneme-alignment-p1.2-20261031"
OUT_DIR = REPO_ROOT / "runs" / "production" / RUN_ID / "tone_rounding"

SONGS = {
    "nianlun": {
        "game": "runs/production/nianlun-from-scratch-20261028/observation/game.json",
        "f0": {
            "fcpe": "runs/production/nianlun-from-scratch-20261028/observation/fcpe.npz",
            "rmvpe": "runs/production/nianlun-from-scratch-20261028/observation/rmvpe.npz",
        },
    },
    "lastpage": {
        "game": "runs/production/zuihouyiye-from-scratch-20261027/observation/game.json",
        "f0": {
            "fcpe": "runs/lastpage_fresh_source_20261007/fcpe.npz",
            "rmvpe": "runs/lastpage_fresh_source_20261007/rmvpe.npz",
        },
    },
    "yuai": {
        "game": "runs/production/yuai-from-source-20261014/inputs/game.json",
        "f0": {
            "fcpe": "runs/production/yuai-from-source-20261014/observations/FCPE.npz",
            "rmvpe": "runs/production/yuai-from-source-20261014/observations/RMVPE.npz",
        },
    },
}

#: A note is only used as evidence when the trackers are within this many
#: semitones of each other and of the GAME value.
TOLERANCE_SEMITONES = 0.6
OCTAVE_SEMITONES = 6.0


def hz_to_midi(hz: np.ndarray) -> np.ndarray:
    return 69.0 + 12.0 * np.log2(hz / 440.0)


def load_f0(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.load(path)
    return data["times"], data["f0_hz"], data["voiced"]


def note_midi_from_f0(times, f0, voiced, start, end) -> tuple[float | None, int]:
    """Median MIDI of the voiced frames inside the note window."""
    mask = (times >= start) & (times <= end) & voiced & (f0 > 0)
    if not mask.any():
        return None, 0
    values = hz_to_midi(f0[mask])
    return float(np.median(values)), int(mask.sum())


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261031)
    report: dict = {
        "schema_version": 1,
        "question": "truncate or round: which agrees with the original recording?",
        "method": "GAME fractional MIDI vs FCPE/RMVPE F0 inside the same note window; "
                  "base pitch only, no vibrato",
        "songs": {},
    }
    totals = {"notes": 0, "rules_differ": 0, "truncate_closer": 0, "round_closer": 0,
              "tie": 0, "uncertain": 0, "octave_conflicts": 0, "f0_disagree": 0}

    for song_id, cfg in SONGS.items():
        raw = json.loads((REPO_ROOT / cfg["game"]).read_text(encoding="utf-8"))
        notes = raw["notes"] if isinstance(raw, dict) else raw
        trackers = {name: load_f0(REPO_ROOT / path) for name, path in cfg["f0"].items()}
        rows = []
        for index, note in enumerate(notes):
            if not note.get("voiced", True):
                continue
            game_tone = float(note["tone"])
            truncated = int(game_tone)
            rounded = int(round(game_tone))
            per_tracker = {}
            for name, (times, f0, voiced) in trackers.items():
                midi, frames = note_midi_from_f0(times, f0, voiced,
                                                float(note["start"]),
                                                float(note["start"]) + float(note["dur"]))
                per_tracker[name] = {"midi": midi, "frames": frames}
            rows.append({
                "index": index,
                "game_tone": game_tone,
                "fractional_part": game_tone - math.floor(game_tone),
                "truncate": truncated,
                "round": rounded,
                "rules_differ": truncated != rounded,
                "trackers": per_tracker,
            })

        for row in rows:
            totals["notes"] += 1
            if row["rules_differ"]:
                totals["rules_differ"] += 1
            values = {name: data["midi"] for name, data in row["trackers"].items()
                      if data["midi"] is not None}
            if len(values) < 2:
                row["verdict"] = "uncertain"
                row["reason"] = "only one F0 tracker has frames in this window"
                totals["uncertain"] += 1
                continue
            fcpe, rmvpe = values.get("fcpe"), values.get("rmvpe")
            if fcpe is None or rmvpe is None:
                row["verdict"] = "uncertain"
                row["reason"] = "a tracker has no frames in this window"
                totals["uncertain"] += 1
                continue
            if abs(fcpe - rmvpe) > TOLERANCE_SEMITONES:
                row["verdict"] = "uncertain"
                row["reason"] = "the two trackers disagree by more than the tolerance"
                totals["f0_disagree"] += 1
                totals["uncertain"] += 1
                continue
            reference = (fcpe + rmvpe) / 2.0
            if abs(reference - row["game_tone"]) > OCTAVE_SEMITONES:
                row["verdict"] = "uncertain"
                row["reason"] = "the F0 is an octave away from the GAME value"
                totals["octave_conflicts"] += 1
                totals["uncertain"] += 1
                continue
            error_truncate = abs(reference - row["truncate"])
            error_round = abs(reference - row["round"])
            if error_truncate < error_round - 1e-9:
                row["verdict"] = "truncate_closer"
                totals["truncate_closer"] += 1
            elif error_round < error_truncate - 1e-9:
                row["verdict"] = "round_closer"
                totals["round_closer"] += 1
            else:
                row["verdict"] = "tie"
                totals["tie"] += 1

        differing = [row for row in rows if row["rules_differ"]]
        sample = rng.sample(differing, min(12, len(differing))) if differing else []
        fractions = np.array([row["fractional_part"] for row in rows]) if rows else np.array([])
        report["songs"][song_id] = {
            "voiced_note_count": len(rows),
            "rules_differ_count": len(differing),
            "rules_differ_ratio": round(len(differing) / max(1, len(rows)), 4),
            "fractional_part_histogram": {
                "below_0.1": int((fractions < 0.1).sum()) if len(fractions) else 0,
                "0.1_to_0.4": int(((fractions >= 0.1) & (fractions < 0.4)).sum()) if len(fractions) else 0,
                "0.4_to_0.6": int(((fractions >= 0.4) & (fractions < 0.6)).sum()) if len(fractions) else 0,
                "0.6_to_0.9": int(((fractions >= 0.6) & (fractions < 0.9)).sum()) if len(fractions) else 0,
                "above_0.9": int((fractions >= 0.9).sum()) if len(fractions) else 0,
            },
            "verdict_counts": {
                name: sum(1 for row in rows if row["verdict"] == name)
                for name in ("truncate_closer", "round_closer", "tie", "uncertain")
            },
            "sample_of_differing_notes": [{
                "index": row["index"],
                "game_tone": round(row["game_tone"], 4),
                "truncate": row["truncate"],
                "round": row["round"],
                "f0_midi_fcpe": row["trackers"]["fcpe"]["midi"],
                "f0_midi_rmvpe": row["trackers"]["rmvpe"]["midi"],
                "verdict": row["verdict"],
            } for row in sample],
        }
        print(f"{song_id}: {len(rows)} voiced notes, {len(differing)} rules differ, "
              f"{report['songs'][song_id]['verdict_counts']}")

    decided = totals["truncate_closer"] + totals["round_closer"] + totals["tie"]
    if totals["round_closer"] > totals["truncate_closer"] * 1.2 and decided > 0:
        recommendation = "round_is_better_supported"
    elif totals["truncate_closer"] > totals["round_closer"] * 1.2:
        recommendation = "truncate_is_better_supported"
    else:
        recommendation = "undetermined"
    report["totals"] = totals
    report["recommendation"] = {
        "conclusion": recommendation,
        "decided_notes": decided,
        "uncertain_notes": totals["uncertain"],
        "note": "the F0 trackers are a reference, not a ground truth; where they disagree with "
                "each other or with GAME the note is counted as uncertain, and the production "
                "rule is not changed by this script",
    }
    (OUT_DIR / "tone_rounding.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"totals": totals, "recommendation": recommendation}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
