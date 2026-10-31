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
    report["ledger"] = build_ledger(segments)
    return report


def build_ledger(segments: Sequence[dict]) -> list[dict]:
    """Sidecar ledger of every note the builder wrote.

    The USTX does not keep note ids, so the identity is rebuilt from the
    construction order: part ``i`` holds segment ``i`` and its notes in the
    order the builder writes them.  The ledger records what each note must
    look like - absolute start tick, end tick, duration, tone, lyric - and
    flags the builder's authorised +/-1 tick touch-up separately, so an
    adjustment is visible instead of silently accepted.
    """
    ledger: list[dict] = []
    for part_index, segment in enumerate(segments):
        anchor = sec_to_tick(segment["part_start_sec"])
        entries: list[dict] = []
        for note_index, note in enumerate(segment["notes"]):
            start_tick = sec_to_tick(note["start"])
            end_tick = sec_to_tick(note["end"])
            position = start_tick - anchor
            entries.append({
                "part_index": part_index,
                "note_index": note_index,
                "note_id": note.get("note_id"),
                "syllable_id": note.get("syllable_id"),
                "lyric": note["lyric"],
                "tone": to_ustx_tone(note["tone"]),
                "source_tone": round(float(note["tone"]), 4),
                "start_s": round(note["start"], 6),
                "end_s": round(note["end"], 6),
                "absolute_start_tick": start_tick,
                "absolute_end_tick": end_tick,
                "position": position,
                "duration": max(1, end_tick - start_tick),
                "adjusted_by_builder": False,
            })
        for left, right in zip(entries, entries[1:]):
            gap = right["position"] - left["position"] - left["duration"]
            if abs(gap) <= 1:
                left["duration"] = right["position"] - left["position"]
                left["adjusted_by_builder"] = True
                left["builder_adjustment_tick"] = int(gap)
        ledger.append({"part_index": part_index, "notes": entries})
    return ledger


def verify_ustx_notes(
    ustx_path: str | Path,
    ledger: Sequence[dict],
    *,
    allowed_tick_deviation: int = 1,
) -> dict:
    """Compare the written USTX with the ledger, note by note.

    The comparison is by position (part, note index), so two identical ``+``
    blocks cannot be swapped unnoticed.  Absolute ticks come from
    ``voice_parts[].position + notes[].position``.
    """
    project = yaml.safe_load(Path(ustx_path).read_text(encoding="utf-8"))
    parts = project.get("voice_parts", [])
    rows: list[dict] = []
    shifted: list[str] = []
    duration_changed: list[str] = []
    retuned: list[str] = []
    lyric_mismatch: list[str] = []
    missing: list[str] = []
    extra = 0
    adjustments: list[dict] = []
    illegal_extenders: list[str] = []
    monotonicity_errors: list[str] = []

    for part in ledger:
        part_index = part["part_index"]
        actual_notes = parts[part_index]["notes"] if part_index < len(parts) else []
        part_position = parts[part_index]["position"] if part_index < len(parts) else 0
        if len(actual_notes) > len(part["notes"]):
            extra += len(actual_notes) - len(part["notes"])
        previous_lyric = None
        for index, want in enumerate(part["notes"]):
            got = actual_notes[index] if index < len(actual_notes) else None
            expected_start = want["absolute_start_tick"]
            expected_duration = want["duration"]
            row = {
                "note_id": want["note_id"],
                "syllable_id": want["syllable_id"],
                "part_index": part_index,
                "note_index": index,
                "expected_lyric": want["lyric"],
                "expected_tone": want["tone"],
                "expected_start_tick": expected_start,
                "expected_duration_tick": expected_duration,
                "adjusted_by_builder": want["adjusted_by_builder"],
            }
            if got is None:
                missing.append(want["note_id"])
                row.update({"present": False, "actual_start_tick": None, "actual_duration_tick": None,
                            "actual_tone": None, "actual_lyric": None})
                rows.append(row)
                previous_lyric = want["lyric"]
                continue
            actual_start = int(part_position) + int(got["position"])
            actual_duration = int(got["duration"])
            row.update({
                "present": True,
                "actual_start_tick": actual_start,
                "actual_duration_tick": actual_duration,
                "actual_tone": got["tone"],
                "actual_lyric": got["lyric"],
            })
            deviation = actual_start - expected_start
            row["start_deviation_tick"] = deviation
            if abs(deviation) > allowed_tick_deviation:
                shifted.append(want["note_id"])
            if actual_duration != expected_duration:
                duration_changed.append(want["note_id"])
            if got["tone"] != want["tone"]:
                retuned.append(want["note_id"])
            if got["lyric"] != want["lyric"]:
                lyric_mismatch.append(want["note_id"])
            if want["adjusted_by_builder"]:
                adjustments.append({
                    "note_id": want["note_id"],
                    "tick": want.get("builder_adjustment_tick"),
                    "detail": "the builder closed a one-tick gap between two notes",
                })
            if want["lyric"] == "+" and index == 0:
                # a '+' that opens a part has no owner: the Core rejects it
                # ("Unrecognized phoneme \"+\"", the part gets no phrase).
                # A '+' after another '+' is legal and continues the syllable.
                illegal_extenders.append(want["note_id"])
            previous_lyric = got["lyric"]
            rows.append(row)
        for left, right in zip(actual_notes, actual_notes[1:]):
            if int(right["position"]) < int(left["position"]):
                monotonicity_errors.append(f"part {part_index}")

    return {
        "ustx": str(ustx_path),
        "expected_note_count": sum(len(part["notes"]) for part in ledger),
        "actual_note_count": sum(len(p["notes"]) for p in parts),
        "one_to_one": (not missing and extra == 0 and not shifted and not duration_changed
                       and not retuned and not lyric_mismatch and not illegal_extenders
                       and not monotonicity_errors),
        "missing_note_ids": missing,
        "extra_note_count": extra,
        "shifted_note_ids": shifted,
        "duration_changed_note_ids": duration_changed,
        "retuned_note_ids": retuned,
        "lyric_mismatch_note_ids": lyric_mismatch,
        "illegal_extender_note_ids": illegal_extenders,
        "monotonicity_errors": monotonicity_errors,
        "builder_adjustments": adjustments,
        "notes": rows,
    }
