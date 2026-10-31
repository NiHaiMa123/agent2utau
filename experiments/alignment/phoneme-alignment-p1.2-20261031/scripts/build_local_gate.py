"""P1.2-F: build the local gate list for the P2 pilot.

The gate rules live in ``agent2utau.alignment.gate`` so they can be tested;
this script only gathers the evidence and writes the list.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent2utau.alignment import sha256_file  # noqa: E402
from agent2utau.alignment.canonical import apply_canonical  # noqa: E402
from agent2utau.alignment.gate import (  # noqa: E402
    PENDING_LYRIC_DECISIONS,
    PENDING_NOTE_DECISIONS,
    evaluate_segment,
    summarize_gate,
)
from agent2utau.alignment.pipeline import write_json  # noqa: E402

RUN_ID = "phoneme-alignment-p1.2-20261031"
RUN_DIR = REPO_ROOT / "runs" / "production" / RUN_ID
P01_EVIDENCE = (REPO_ROOT / "experiments" / "alignment" /
                "phoneme-alignment-p0p1-20261031" / "evidence")

SONGS = ["nianlun", "lastpage", "yuai"]

PENDING_NOTE_DECISIONS["lastpage"] = {
    "n0060": "the note between 声 and 淹: GAME split the consonant of 淹 into its own "
             "event; merging, moving or dropping it is still open",
}
PENDING_LYRIC_DECISIONS["nianlun"] = (
    "two characters differ between the published lyric and the recorded wording "
    "(份 / 分); the locked text keeps the recorded wording until a human decides")


def load(song_id: str) -> dict:
    song_dir = RUN_DIR / song_id
    return {
        "mapping": json.loads((song_dir / "mapping.v1.json").read_text(encoding="utf-8")),
        "unassigned": json.loads(
            (song_dir / "unassigned_voiced_notes.json").read_text(encoding="utf-8")),
        "verification": json.loads(
            (song_dir / "baseline_verification.json").read_text(encoding="utf-8")),
        "lyrics": json.loads((song_dir / "lyrics_locked.json").read_text(encoding="utf-8")),
        "notes": json.loads((song_dir / "notes_normalized.json").read_text(encoding="utf-8")),
        "dir": song_dir,
    }


def pending_lyric_syllables(song_id: str, lyrics: dict) -> list[str]:
    """Syllables whose text is still under review."""
    canonical_path = RUN_DIR / "canonical_lyrics" / f"{song_id}.json"
    if not canonical_path.is_file():
        return []
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    lines = lyrics["lines"]
    _corrected, report = apply_canonical([row["text"] for row in lines],
                                         canonical["lines"], apply=False)
    if not report.substitutions:
        return []
    positions_by_unit: dict[int, set[int]] = {}
    for substitution in report.substitutions:
        positions_by_unit.setdefault(substitution["unit_index"], set()).add(
            substitution["position"])
    affected: list[str] = []
    index = 0
    for unit_index, row in enumerate(lines):
        for position in range(len(row["text"])):
            if position in positions_by_unit.get(unit_index, set()):
                affected.append(f"s{index + 1:04d}")
            index += 1
    return affected


def evaluate_song(song_id: str, data: dict, segments: list[dict]) -> list[dict]:
    mapping_rows = {row["syllable_id"]: row for row in data["mapping"]["mapping"]}
    note_index = {n["note_id"]: n for n in data["notes"]["notes"]}
    pending = pending_lyric_syllables(song_id, data["lyrics"])
    out = []
    for segment in segments:
        syllable_ids = segment["syllable_ids"]
        note_ids = [nid for sid in syllable_ids
                    for nid in (mapping_rows.get(sid, {}).get("note_ids") or [])]
        times = [note_index[nid] for nid in note_ids if nid in note_index]
        start = min((n["start"] for n in times), default=0.0)
        end = max((n["end"] for n in times), default=0.0)
        out.append(evaluate_segment(
            segment_id=segment["segment_id"],
            song_id=song_id,
            scenario=segment["scenario"],
            syllable_ids=syllable_ids,
            text=segment["text"],
            mapping_rows=mapping_rows,
            unassigned_notes=data["unassigned"]["notes"],
            verification_notes=data["verification"]["notes"],
            note_index=note_index,
            pending_lyric_syllables=pending,
            start_s=start,
            end_s=end,
        ))
    return out


def main() -> int:
    samples_index = json.loads((P01_EVIDENCE / "samples" / "index.json").read_text(encoding="utf-8"))
    by_song_scenario: dict[tuple[str, str], list[dict]] = {}
    for sample in samples_index["samples"]:
        song_id = sample["sample_id"].split("-")[0]
        by_song_scenario.setdefault((song_id, sample["scenario"]), []).append(sample)
    scenarios = sorted({scenario for _song, scenario in by_song_scenario})
    per_song = {song_id: 0 for song_id in SONGS}
    used = {key: 0 for key in by_song_scenario}
    picked = []
    # two rounds keep the set diverse and land inside the planned 10-20
    for _round in range(2):
        for scenario in scenarios:
            candidates = [song for song in SONGS if (song, scenario) in by_song_scenario]
            if not candidates:
                continue
            song = min(candidates, key=lambda s: (per_song[s], s))
            options = by_song_scenario[(song, scenario)]
            if used[(song, scenario)] >= len(options):
                continue
            picked.append(options[used[(song, scenario)]])
            used[(song, scenario)] += 1
            per_song[song] += 1

    segments: list[dict] = []
    for song_id in SONGS:
        data = load(song_id)
        song_picked = [s for s in picked if s["sample_id"].startswith(song_id + "-")]
        segments += evaluate_song(song_id, data, [{
            "segment_id": s["sample_id"],
            "scenario": s["scenario"],
            "syllable_ids": s["syllable_ids"],
            "text": s["text"],
        } for s in song_picked])

    # a segment that deliberately covers an open decision
    data = load("lastpage")
    mapping_rows = {row["syllable_id"]: row for row in data["mapping"]["mapping"]}
    target = next(sid for sid, row in mapping_rows.items() if row["text"] == "淹")
    index = int(target[1:])
    syllable_ids = [f"s{n:04d}" for n in range(index - 2, index + 3)]
    syllable_ids = [s for s in syllable_ids if s in mapping_rows]
    segments += evaluate_song("lastpage", data, [{
        "segment_id": "lastpage-pending-n0060",
        "scenario": "pending_note_decision",
        "syllable_ids": syllable_ids,
        "text": "".join(mapping_rows[s]["text"] for s in syllable_ids),
    }])

    index = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "note": "local release only - the songs themselves stay incomplete",
        **summarize_gate(segments),
        "inputs": {
            song_id: {
                "mapping_sha256": sha256_file(RUN_DIR / song_id / "mapping.v1.json"),
                "lyrics_sha256": sha256_file(RUN_DIR / song_id / "lyrics_locked.json"),
                "notes_sha256": sha256_file(RUN_DIR / song_id / "notes_normalized.json"),
                "verification_sha256": sha256_file(RUN_DIR / song_id / "baseline_verification.json"),
            } for song_id in SONGS
        },
        "segments": segments,
    }
    write_json(RUN_DIR / "local_gate.json", index)
    print(json.dumps({
        "segments": index["segment_count"],
        "ready": index["ready_count"],
        "blocked": index["blocked_count"],
        "blocker_counts": index["blocker_counts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
