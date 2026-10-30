"""GAME note events -> stable note ids and single-grid tick normalization.

GAME emits *note events* (time, tone, voiced), not lyric boundaries and not
frame F0.  Every event keeps its original index so the observation can be
re-read without ambiguity.  Ticks use the same fixed 120 BPM / 480 resolution
grid as ``openutau/build.py`` so the normalized clock and the built USTX never
disagree; boundaries are quantized once on the global grid (never start and
duration separately) so rounding cannot create overlaps.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Sequence

from ..openutau.build import BPM_FIXED, RESOLUTION, sec_to_tick


@dataclass(frozen=True)
class NoteEvent:
    """One GAME note event with its stable id and quantized clock."""

    note_id: str
    index: int
    start: float
    dur: float
    tone: float
    voiced: bool
    end: float
    start_tick: int
    end_tick: int
    duration_tick: int

    @property
    def rest(self) -> bool:
        return not self.voiced

    def as_dict(self) -> dict:
        d = asdict(self)
        d["rest"] = self.rest
        return d


def load_game_notes(path: str | Path) -> list[NoteEvent]:
    """Read a GAME observation (``{"notes": [...]}``) into note events."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    raw = doc.get("notes") if isinstance(doc, dict) else doc
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"No GAME notes in {path}")
    return normalize_notes(raw)


def normalize_notes(raw: Sequence[dict]) -> list[NoteEvent]:
    """Attach ids and one-grid ticks to raw GAME events."""
    notes: list[NoteEvent] = []
    for index, row in enumerate(raw):
        start = float(row["start"])
        dur = float(row["dur"])
        end = start + dur
        start_tick = int(sec_to_tick(start))
        end_tick = int(sec_to_tick(end))
        notes.append(
            NoteEvent(
                note_id=f"n{index + 1:04d}",
                index=index,
                start=start,
                dur=dur,
                tone=float(row["tone"]),
                voiced=bool(row.get("voiced", True)),
                end=end,
                start_tick=start_tick,
                end_tick=end_tick,
                duration_tick=end_tick - start_tick,
            )
        )
    return notes


def note_anomalies(notes: Sequence[NoteEvent]) -> list[dict]:
    """Clock anomalies, split by severity.

    * ``non_positive_duration`` (hard) - a note that rounds to zero or fewer
      ticks; such a note cannot exist in a score.
    * ``overlap`` (hard) - two consecutive notes that share ticks.
    * ``gap`` (info) - a hole in the covered timeline.  A silence between two
      sung notes is normal in a recording, so it is reported, never blocked.

    The quantized clock, the original clock and the USTX read-back all use the
    same criterion: gaps and overlaps are measured on quantized boundaries.
    """
    problems: list[dict] = []
    for i, note in enumerate(notes):
        if note.duration_tick <= 0:
            problems.append({
                "kind": "non_positive_duration",
                "severity": "hard",
                "note_id": note.note_id,
                "index": note.index,
                "start_s": round(note.start, 4),
                "dur_s": round(note.dur, 4),
                "duration_tick": note.duration_tick,
            })
        if i + 1 < len(notes):
            nxt = notes[i + 1]
            if nxt.start_tick < note.end_tick:
                problems.append({
                    "kind": "overlap",
                    "severity": "hard",
                    "note_id": note.note_id,
                    "next_note_id": nxt.note_id,
                    "overlap_tick": note.end_tick - nxt.start_tick,
                })
            elif nxt.start_tick > note.end_tick:
                problems.append({
                    "kind": "gap",
                    "severity": "info",
                    "note_id": note.note_id,
                    "next_note_id": nxt.note_id,
                    "gap_tick": nxt.start_tick - note.end_tick,
                    "gap_s": round((nxt.start_tick - note.end_tick) * 60.0 / (BPM_FIXED * RESOLUTION), 4),
                })
    return problems


def build_notes_document(
    song_id: str,
    notes: Sequence[NoteEvent],
    *,
    source: str,
    source_sha256: str,
    clock: dict,
    extra: dict | None = None,
) -> dict:
    """Build the on-disk normalized-notes document (the P0 deliverable)."""
    problems = note_anomalies(notes)
    doc = {
        "schema_version": 1,
        "song_id": song_id,
        "source": source,
        "source_sha256": source_sha256,
        "semantics": "GAME note events (time, tone, voiced); not lyric boundaries, not frame F0",
        "clock": clock,
        "note_count": len(notes),
        "voiced_count": sum(1 for n in notes if n.voiced),
        "rest_count": sum(1 for n in notes if n.rest),
        "notes": [n.as_dict() for n in notes],
        "anomalies": problems,
    }
    if extra:
        doc.update(extra)
    return doc
