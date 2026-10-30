"""Pick the P0 small samples and cut them into tiny baseline projects.

plan.md P0 asks for at least ten small windows that cover the hard cases:
one character per note, melisma, repeated characters, an early attack, a
short vowel, a rest before the character, a line boundary and a polyphonic
character.  Every sample is cut from the *mapping* that was just produced, so
a sample can be handed to the native phonemizer without guessing anything.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent2utau.alignment import load_locked_lyrics, load_game_notes, sha256_file  # noqa: E402
from agent2utau.alignment.baseline import build_baseline_ustx  # noqa: E402
from agent2utau.alignment.pipeline import write_json  # noqa: E402

RUN_ID = "phoneme-alignment-p0p1-20261031"
RUN_DIR = REPO_ROOT / "runs" / "production" / RUN_ID

SCENARIOS = [
    "one_char_one_note",
    "melisma",
    "repeated_char",
    "early_attack",
    "short_vowel",
    "rest_before",
    "line_boundary",
    "polyphone",
]

SONG_ORDER = ["nianlun", "lastpage", "yuai"]


def load_song(song_id: str):
    song_dir = RUN_DIR / song_id
    mapping = json.loads((song_dir / "mapping.v1.json").read_text(encoding="utf-8"))
    notes = json.loads((song_dir / "notes_normalized.json").read_text(encoding="utf-8"))
    lyrics, lyrics_doc = load_locked_lyrics(song_dir / "lyrics_locked.json")
    return song_dir, mapping, notes, lyrics, lyrics_doc


def hfa_marks(song_dir: Path) -> dict[str, set]:
    """Pinyin marks the original singer used, per character (HFA evidence)."""
    manifest = json.loads((song_dir / "observations_manifest.json").read_text(encoding="utf-8"))
    path = REPO_ROOT / manifest["inputs"]["hfa"]["path"]
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    marks: dict[str, set] = {}
    for phrase in doc.get("phrases", []):
        for word in phrase.get("words", []):
            hanzi = word.get("hanzi")
            if hanzi:
                marks.setdefault(hanzi, set()).add(str(word.get("mark", "")))
    return marks


def detect(song_id: str):
    """Find one witness per scenario for one song."""
    song_dir, mapping, notes_doc, lyrics, lyrics_doc = load_song(song_id)
    note_rows = {n["note_id"]: n for n in notes_doc["notes"]}
    order = {n["note_id"]: n["index"] for n in notes_doc["notes"]}
    rows = mapping["mapping"]
    syllables = {s.syllable_id: s for s in lyrics}

    counts: dict[str, int] = {}
    for s in lyrics:
        counts[s.text] = counts.get(s.text, 0) + 1

    # polyphonic characters: one character, several pinyin marks (locked lyrics
    # and the original singing both count)
    polyphones: dict[str, set] = {}
    for line in lyrics_doc.get("line_meta", []):
        for text, pinyin in zip(line.get("hanzi", ""), str(line.get("pinyin", "")).split()):
            polyphones.setdefault(text, set()).add(pinyin)
    for text, marks in hfa_marks(song_dir).items():
        polyphones.setdefault(text, set()).update(marks)
    polyphonic = {text for text, marks in polyphones.items() if len(marks) > 1}

    witnesses: dict[str, dict] = {}
    chosen_index: list[int] = []

    def offer(scenario: str, row: dict, index: int, extra: dict | None = None):
        if scenario in witnesses:
            return
        # spread the samples: prefer a witness far from the ones already taken
        if any(abs(index - other) < 8 for other in chosen_index):
            return
        note_ids = row.get("note_ids") or []
        entry = {
            "scenario": scenario,
            "syllable_id": row["syllable_id"],
            "text": row["text"],
            "line_index": row["line_index"],
            "note_ids": note_ids,
        }
        if extra:
            entry.update(extra)
        witnesses[scenario] = entry
        chosen_index.append(index)

    for index, row in enumerate(rows):
        if row["status"] != "mapped":
            continue
        note_ids = row["note_ids"]
        anchor = row.get("evidence", {}).get("anchor_s")
        duration = row.get("evidence", {}).get("expected_dur_s")
        if len(note_ids) == 1:
            offer("one_char_one_note", row, index)
        if len(note_ids) > 1:
            offer("melisma", row, index, {"sustain_note_ids": row.get("sustain_note_ids", [])})
        if counts.get(row["text"], 0) > 1:
            offer("repeated_char", row, index, {"occurrences_in_song": counts[row["text"]]})
        if row["text"] in polyphonic:
            offer("polyphone", row, index, {"pinyin_marks": sorted(polyphones[row["text"]])})
        first_in_line = next((s.syllable_id for s in lyrics if s.line_index == row["line_index"]), "")
        if row["syllable_id"] == first_in_line:
            offer("line_boundary", row, index)
        if anchor is not None and note_ids:
            first = note_rows[note_ids[0]]
            if first["start"] - anchor >= 0.08:
                offer("early_attack", row, index, {
                    "anchor_s": anchor,
                    "note_start_s": first["start"],
                    "lead_s": round(first["start"] - anchor, 4),
                })
        if duration is not None and 0.08 <= duration <= 0.25:
            offer("short_vowel", row, index, {"observed_dur_s": duration})
        if note_ids:
            first = note_rows[note_ids[0]]
            if first["index"] > 0:
                previous = notes_doc["notes"][first["index"] - 1]
                if previous["rest"]:
                    offer("rest_before", row, index, {"previous_note_id": previous["note_id"]})
    return song_dir, rows, witnesses, note_rows, order


def cut_samples(song_id: str, rows, witnesses, note_rows, order):
    """Cut a small window around every witness and build a tiny project."""
    by_id = {r["syllable_id"]: r for r in rows}
    index_of = {r["syllable_id"]: i for i, r in enumerate(rows)}
    samples = []
    for scenario, witness in witnesses.items():
        anchor_index = index_of[witness["syllable_id"]]
        start = max(0, anchor_index - 2)
        end = min(len(rows) - 1, anchor_index + 2)
        window = [r for r in rows[start:end + 1] if r["status"] == "mapped"]
        if not window:
            continue
        notes: list[dict] = []
        for row in window:
            for position, note_id in enumerate(row["note_ids"]):
                note = note_rows[note_id]
                notes.append({
                    "note_id": note_id,
                    "syllable_id": row["syllable_id"],
                    "lyric": row["text"] if position == 0 else "+",
                    "start": note["start"],
                    "end": note["end"],
                    "dur": note["dur"],
                    "tone": note["tone"],
                    "line_index": row["line_index"],
                })
        notes.sort(key=lambda n: (n["start"], n["note_id"]))
        sample_id = f"{song_id}-{scenario}"
        samples.append({
            "sample_id": sample_id,
            "song_id": song_id,
            "scenario": scenario,
            "witness_syllable_id": witness["syllable_id"],
            "witness_text": witness["text"],
            "syllable_ids": [r["syllable_id"] for r in window],
            "text": "".join(r["text"] for r in window),
            "note_ids": [n["note_id"] for n in notes],
            "start_s": notes[0]["start"],
            "end_s": notes[-1]["end"],
            "note_count": len(notes),
            "detail": {k: v for k, v in witness.items()
                       if k not in ("scenario", "syllable_id", "text", "line_index", "note_ids")},
            "_notes": notes,
        })
    return samples


def main() -> int:
    index = []
    written = []
    for song_id in SONG_ORDER:
        song_dir, rows, witnesses, note_rows, order = detect(song_id)
        samples = cut_samples(song_id, rows, witnesses, note_rows, order)
        for sample in samples:
            notes = sample.pop("_notes")
            out_dir = RUN_DIR / "samples" / song_id
            out_dir.mkdir(parents=True, exist_ok=True)
            ustx = out_dir / f"{sample['sample_id']}.ustx"
            report = build_baseline_ustx(
                notes, ustx, name=sample["sample_id"],
            )
            sample["baseline_ustx"] = str(ustx.relative_to(REPO_ROOT))
            sample["baseline_sha256"] = sha256_file(ustx)
            sample["parts"] = report["parts"]
            sample["notes"] = report["notes"]
            sample["sustain_notes"] = report["sustain_notes"]
            sample["anomalies"] = report["anomalies"]
            written.append(sample)
        index.append({"song_id": song_id, "sample_count": len(samples),
                      "sample_ids": [s["sample_id"] for s in samples]})

    summary = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "scenarios": SCENARIOS,
        "per_song": index,
        "samples": written,
        "covered_scenarios": sorted({s["scenario"] for s in written}),
        "sample_count": len(written),
    }
    write_json(RUN_DIR / "samples" / "index.json", summary)
    print(json.dumps({"sample_count": summary["sample_count"],
                      "covered_scenarios": summary["covered_scenarios"],
                      "per_song": index}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
