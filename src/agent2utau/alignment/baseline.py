"""Baseline USTX from a chosen mapping - no manual PITD, no manual voicing.

The baseline exists so P2 can ask the *current* voicebank for its own phoneme
clock.  It therefore contains only:

* one note per mapped syllable (character) plus ``+`` sustain blocks for the
  melisma notes of the same syllable,
* the default pitch curve and the default voicebank controls.

Nothing here changes pitch, voicing or mix.

**Illegal extends are never dropped silently.**  An extender that does not
touch its character cannot be represented: OpenUtau's Core reports
``Unrecognized phoneme "+"`` and leaves the note out of the phrase (verified
with the real Core, see
``experiments/alignment/phoneme-alignment-p0p1-20261031/scripts/probe_extender_gap.py``).
Such a note is reported as an unresolved note with its id, syllable, tone and
clock, together with a small set of code-generated candidates - each of them
stating its effect and whether it needs authorization.  A baseline with such
a note is ``incomplete`` and must not enter P2 as a finished baseline.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Sequence

import yaml

from ..openutau.build import RESOLUTION, BPM_FIXED, build_project, sec_to_tick, to_ustx_tone

#: An extender must touch the note it continues.  One tick of slack is the
#: quantization itself; anything larger is a real gap in the recording.
MAX_EXTENDER_GAP_TICKS = 1


def tick_to_sec(ticks: int) -> float:
    return ticks * 60.0 / (BPM_FIXED * RESOLUTION)


def _gap_ticks(left_end: float, right_start: float) -> int:
    return int(sec_to_tick(right_start)) - int(sec_to_tick(left_end))


def extender_candidates(
    *,
    note_id: str,
    syllable_id: str,
    text: str,
    tone: float,
    previous_note_id: str,
    previous_end: float,
    gap_s: float,
    next_start: float,
    next_end: float,
) -> list[dict]:
    """Code-generated options for an extender that does not touch its note.

    No option is applied automatically: the first two change the song clock
    or the note count, the third is rejected by the Core, the fourth would
    repeat a sung character.
    """
    return [
        {
            "candidate_id": f"baseline:{note_id}:close_gap",
            "option": "close_gap",
            "effect": f"move {note_id} earlier by {round(gap_s, 4)} s so it touches {previous_note_id}",
            "changes": ["note_start"],
            "requires_authorization": True,
            "status": "candidate",
        },
        {
            "candidate_id": f"baseline:{note_id}:merge_into_character",
            "option": "merge_into_character",
            "effect": f"replace {previous_note_id}+{note_id} with one note of {round(next_end - previous_end, 4)} s",
            "changes": ["note_count", "note_tone"],
            "requires_authorization": True,
            "status": "candidate",
        },
        {
            "candidate_id": f"baseline:{note_id}:split_new_part",
            "option": "split_new_part",
            "effect": f"let {note_id} open a new voice part",
            "changes": ["part_layout"],
            "requires_authorization": False,
            "status": "illegal_by_core",
            "evidence": "OpenUtau Core: a part whose first note is '+' has no owner "
                        "(probe: split_part_starting_with_plus)",
        },
        {
            "candidate_id": f"baseline:{note_id}:repeat_character",
            "option": "repeat_character",
            "effect": f"write '{text}' again for {note_id}",
            "changes": ["lyrics"],
            "requires_authorization": True,
            "status": "forbidden_without_human",
            "evidence": "repeats a sung character; never applied automatically",
        },
    ]


def rows_to_segments(rows: Sequence[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Group mapped notes into one part per lyric line.

    ``rows`` are per-note rows (see ``candidates.mapping_to_ustx_rows``).
    Returns (segments, unresolved_notes, candidates).  ``unresolved_notes``
    describes the notes that could not be represented legally; ``candidates``
    are the limited options for each of them.
    """
    unresolved_notes: list[dict] = []
    candidates: list[dict] = []
    by_line: dict[int, list[dict]] = {}
    for row in rows:
        by_line.setdefault(row["line_index"], []).append(row)

    segments: list[dict] = []
    for line_index in sorted(by_line):
        line_rows = sorted(by_line[line_index], key=lambda r: (r["start"], r["note_id"]))
        kept: list[dict] = []
        for row in line_rows:
            if row["lyric"] == "+" and kept:
                gap = row["start"] - kept[-1]["end"]
                gap_ticks = _gap_ticks(kept[-1]["end"], row["start"])
                if gap_ticks > MAX_EXTENDER_GAP_TICKS:
                    previous = kept[-1]
                    unresolved_notes.append({
                        "note_id": row["note_id"],
                        "syllable_id": row["syllable_id"],
                        "text": row.get("syllable_text", ""),
                        "tone": round(row["tone"], 4),
                        "start_s": round(row["start"], 4),
                        "end_s": round(row["end"], 4),
                        "gap_s": round(gap, 4),
                        "gap_tick": gap_ticks,
                        "previous_note_id": previous["note_id"],
                        "reason_code": "extender_not_touching",
                        "detail": "a '+' block may not cross a real gap; OpenUtau Core reports "
                                  "Unrecognized phoneme \"+\" and leaves the note out of the phrase",
                    })
                    candidates.extend(extender_candidates(
                        note_id=row["note_id"],
                        syllable_id=row["syllable_id"],
                        text=row.get("syllable_text", ""),
                        tone=row["tone"],
                        previous_note_id=previous["note_id"],
                        previous_end=previous["end"],
                        gap_s=gap,
                        next_start=row["start"],
                        next_end=row["end"],
                    ))
                    continue
            kept.append(row)
        if not kept:
            continue
        segments.append({
            "notes": kept,
            "start_sec": kept[0]["start"],
            "part_start_sec": kept[0]["start"],
            "line_index": line_index,
            "note_count": len(kept),
            "last_end": kept[-1]["end"],
        })
    return segments, unresolved_notes, candidates


def write_baseline_ustx(
    segments: Sequence[dict],
    out_ustx: str | Path,
    *,
    name: str,
    template: str | Path | None = None,
) -> dict:
    """Write the baseline USTX from prepared segments."""
    if not segments:
        raise ValueError("No segments to build")
    out = Path(out_ustx)
    build_project(name, list(segments), out, template=Path(template) if template else None)
    return {
        "project": str(out),
        "parts": len(segments),
        "notes": sum(len(s["notes"]) for s in segments),
        "sustain_notes": sum(1 for s in segments for n in s["notes"] if n["lyric"] == "+"),
    }


def build_baseline_ustx(
    rows: Sequence[dict],
    out_ustx: str | Path,
    *,
    name: str,
    template: str | Path | None = None,
) -> dict:
    """Write the baseline USTX and report what it contains."""
    segments, unresolved_notes, candidates = rows_to_segments(rows)
    report = write_baseline_ustx(segments, out_ustx, name=name, template=template)
    report["unresolved_note_ids"] = [row["note_id"] for row in unresolved_notes]
    report["unresolved_notes"] = unresolved_notes
    report["candidates"] = candidates
    report["segments"] = segments
    return report


def verify_ustx_notes(
    ustx_path: str | Path,
    rows: Sequence[dict],
    part_lines: Sequence[int] | None = None,
) -> dict:
    """Compare the mapped notes with the notes that are really in the USTX.

    The comparison is per voice part (the parts follow the lyric lines), so a
    note that could not be represented does not shift the notes behind it.
    ``part_lines`` tells which lyric line each part holds; without it the
    parts are matched to the lines by order, which only holds when every line
    produced a part.
    """
    project = yaml.safe_load(Path(ustx_path).read_text(encoding="utf-8"))
    parts = project.get("voice_parts", [])
    by_line: dict[int, list[dict]] = {}
    for row in rows:
        by_line.setdefault(row["line_index"], []).append(row)
    line_order = list(part_lines) if part_lines is not None else sorted(by_line)

    rows_out: list[dict] = []
    missing: list[str] = []
    retuned: list[str] = []
    lyric_mismatch: list[str] = []
    extra = 0
    for part_index, line_index in enumerate(line_order):
        expected = by_line.get(line_index, [])
        actual = parts[part_index]["notes"] if part_index < len(parts) else []
        matcher = difflib.SequenceMatcher(
            a=[row["lyric"] for row in expected],
            b=[note["lyric"] for note in actual], autojunk=False)
        matched_expected: set[int] = set()
        matched_actual: set[int] = set()
        for block in matcher.get_matching_blocks():
            for k in range(block.size):
                want = expected[block.a + k]
                got = actual[block.b + k]
                matched_expected.add(block.a + k)
                matched_actual.add(block.b + k)
                expected_tone = to_ustx_tone(want["tone"])
                rows_out.append({
                    "note_id": want["note_id"],
                    "syllable_id": want["syllable_id"],
                    "part": part_index,
                    "expected_lyric": want["lyric"],
                    "expected_tone": expected_tone,
                    "actual_lyric": got["lyric"],
                    "actual_tone": got["tone"],
                    "present": True,
                    "tone_matches": got["tone"] == expected_tone,
                })
                if got["tone"] != expected_tone:
                    retuned.append(want["note_id"])
        for index, want in enumerate(expected):
            if index in matched_expected:
                continue
            missing.append(want["note_id"])
            rows_out.append({
                "note_id": want["note_id"],
                "syllable_id": want["syllable_id"],
                "part": part_index,
                "expected_lyric": want["lyric"],
                "expected_tone": to_ustx_tone(want["tone"]),
                "actual_lyric": None,
                "actual_tone": None,
                "present": False,
                "tone_matches": False,
            })
        extra += len(actual) - len(matched_actual)
    return {
        "ustx": str(ustx_path),
        "expected_note_count": len(rows),
        "actual_note_count": sum(len(p["notes"]) for p in parts),
        "one_to_one": not missing and extra == 0 and not retuned and not lyric_mismatch,
        "missing_note_ids": missing,
        "extra_note_count": extra,
        "retuned_note_ids": retuned,
        "lyric_mismatch_note_ids": lyric_mismatch,
        "notes": rows_out,
    }
