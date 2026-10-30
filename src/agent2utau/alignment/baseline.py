"""Baseline USTX from a chosen mapping - no manual PITD, no manual voicing.

The baseline exists so P2 can ask the *current* voicebank for its own phoneme
clock.  It therefore contains only:

* one note per mapped syllable (character) plus ``+`` sustain blocks for the
  melisma notes of the same syllable,
* the default pitch curve and the default voicebank controls.

Nothing here changes pitch, voicing or mix; a sustain note that is separated
from its syllable by a gap is dropped (and reported) because a ``+`` block may
not cross an illegal gap.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ..openutau.build import build_project


def rows_to_segments(rows: Sequence[dict]) -> tuple[list[dict], list[dict]]:
    """Group mapping rows into one part per lyric line.

    Returns (segments, anomalies).  Segments are ready for
    ``openutau.build.build_project``.
    """
    anomalies: list[dict] = []
    by_line: dict[int, list[dict]] = {}
    for row in rows:
        by_line.setdefault(row["line_index"], []).append(row)

    segments: list[dict] = []
    for line_index in sorted(by_line):
        line_rows = sorted(by_line[line_index], key=lambda r: r["start"])
        notes: list[dict] = []
        previous_end: float | None = None
        for row in line_rows:
            notes.append({
                "start": row["start"],
                "end": row["end"],
                "dur": row["dur"],
                "tone": int(round(row["tone"])),
                "lyric": row["lyric"],
                "note_id": row["note_id"],
                "syllable_id": row["syllable_id"],
            })
            previous_end = row["end"]
        # a sustain block must touch the note it continues
        kept: list[dict] = []
        for index, note in enumerate(notes):
            if note["lyric"] == "+" and kept:
                gap = note["start"] - kept[-1]["end"]
                if gap > 1e-6:
                    anomalies.append({
                        "kind": "sustain_note_dropped_gap",
                        "note_id": note["note_id"],
                        "syllable_id": note["syllable_id"],
                        "gap_s": round(gap, 4),
                        "detail": "a '+' block may not cross a gap; the note stays in notes_normalized.json",
                    })
                    continue
            kept.append(note)
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
    return segments, anomalies


def build_baseline_ustx(
    rows: Sequence[dict],
    out_ustx: str | Path,
    *,
    name: str,
    template: str | Path | None = None,
) -> dict:
    """Write the baseline USTX and report what it contains."""
    segments, anomalies = rows_to_segments(rows)
    if not segments:
        raise ValueError("No segments to build")
    out = Path(out_ustx)
    build_project(name, segments, out, template=Path(template) if template else None)
    return {
        "project": str(out),
        "parts": len(segments),
        "notes": sum(len(s["notes"]) for s in segments),
        "sustain_notes": sum(1 for s in segments for n in s["notes"] if n["lyric"] == "+"),
        "anomalies": anomalies,
    }
