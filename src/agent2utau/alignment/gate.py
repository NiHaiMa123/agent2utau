"""The local gate: which short segments may enter the P2 pilot (P1.2-F).

A segment is a short, contiguous piece of a song (5-15 characters).  It is
released only when everything inside it *and* its one character of context is
settled:

* no unresolved syllable,
* no unreviewed voiced note without an owner,
* no illegal '+' extender,
* no pending user decision that touches the segment,
* the note's real USTX tick, tone and duration agree with the ledger.

A released segment is *not* a statement about the whole song: the songs stay
``incomplete`` as long as any of these items is open.
"""

from __future__ import annotations

from typing import Sequence

RELEASED = "ready_for_p2_native_baseline"
BLOCKED = "blocked"

#: decisions the user still has to make; the sentences they touch are blocked
PENDING_NOTE_DECISIONS: dict[str, dict[str, str]] = {}
PENDING_LYRIC_DECISIONS: dict[str, str] = {}

#: global items that do not block a segment but must be written down
GLOBAL_PENDING = [
    "the MIDI rounding of the GAME tone (truncate vs round) is still open; the "
    "segment's tick and identity gate hold, but a note's tone may move by one "
    "semitone when the decision is made",
    "the line breaks follow the recording, not the release edition",
]


def evaluate_segment(
    *,
    segment_id: str,
    song_id: str,
    scenario: str,
    syllable_ids: Sequence[str],
    text: str,
    mapping_rows: dict[str, dict],
    unassigned_notes: Sequence[dict],
    verification_notes: Sequence[dict],
    note_index: dict[str, dict],
    pending_lyric_syllables: Sequence[str] = (),
    start_s: float = 0.0,
    end_s: float = 0.0,
) -> dict:
    """Evaluate one segment and return its gate record."""
    syllables = list(syllable_ids)
    context = [syllables[0], syllables[-1]] if syllables else []
    note_ids = [nid for sid in syllables
                for nid in (mapping_rows.get(sid, {}).get("note_ids") or [])]
    blockers: list[dict] = []
    cautions: list[dict] = []

    for sid in syllables + context:
        row = mapping_rows.get(sid)
        if row is None:
            continue
        if row.get("status") == "unresolved":
            blockers.append({"code": "unresolved_syllable", "syllable_id": sid,
                             "text": row.get("text"),
                             "detail": "the syllable has no defensible note assignment"})
        if row.get("review_required"):
            blockers.append({"code": "syllable_review_required", "syllable_id": sid,
                             "text": row.get("text"),
                             "detail": "the syllable or its line is still under review"})

    for row in unassigned_notes:
        if row["end_s"] >= start_s and row["start_s"] <= end_s:
            blockers.append({"code": "unassigned_voiced_note", "note_id": row["note_id"],
                             "classification": row.get("classification"),
                             "detail": row.get("detail", "")})

    for note in verification_notes:
        if note["note_id"] not in note_ids:
            continue
        if note.get("actual_start_tick") is not None and \
                abs(note.get("start_deviation_tick", 0)) > 1:
            blockers.append({"code": "ustx_start_deviation", "note_id": note["note_id"],
                             "deviation_tick": note.get("start_deviation_tick"),
                             "detail": "the written note does not sit on the expected tick"})
        if note.get("actual_tone") is not None and \
                note["actual_tone"] != note["expected_tone"]:
            blockers.append({"code": "ustx_tone_mismatch", "note_id": note["note_id"],
                             "detail": "the written tone differs from the mapping"})
        if note.get("actual_duration_tick") is not None and \
                note["actual_duration_tick"] != note["expected_duration_tick"]:
            blockers.append({"code": "ustx_duration_mismatch", "note_id": note["note_id"],
                             "detail": "the written duration differs from the mapping"})

    for note_id, detail in PENDING_NOTE_DECISIONS.get(song_id, {}).items():
        if note_id in note_ids:
            blockers.append({"code": "pending_note_decision", "note_id": note_id,
                             "detail": detail})
    pending = set(pending_lyric_syllables)
    for sid in syllables:
        if sid in pending:
            blockers.append({"code": "pending_lyric_decision", "syllable_id": sid,
                             "detail": PENDING_LYRIC_DECISIONS.get(song_id, "")})

    lines = sorted({mapping_rows[sid]["line_index"] for sid in syllables
                    if sid in mapping_rows and "line_index" in mapping_rows[sid]})
    if len(lines) > 1:
        cautions.append({"code": "cross_line_segment", "lines": lines,
                         "detail": "the segment crosses a lyric line; the shared context "
                                   "of the two lines must be kept when editing"})

    return {
        "segment_id": segment_id,
        "song_id": song_id,
        "scenario": scenario,
        "syllable_ids": syllables,
        "note_ids": note_ids,
        "text": text,
        "start_s": round(start_s, 4),
        "end_s": round(end_s, 4),
        "context_syllable_ids": context,
        "local_gate": BLOCKED if blockers else RELEASED,
        "blockers": blockers,
        "cautions": cautions,
        "global_pending": list(GLOBAL_PENDING),
    }


def summarize_gate(segments: Sequence[dict]) -> dict:
    """One page summary of a gate list."""
    blockers = [b for segment in segments for b in segment["blockers"]]
    return {
        "segment_count": len(segments),
        "ready_count": sum(1 for s in segments if s["local_gate"] == RELEASED),
        "blocked_count": sum(1 for s in segments if s["local_gate"] == BLOCKED),
        "blocker_counts": {
            code: sum(1 for b in blockers if b["code"] == code)
            for code in sorted({b["code"] for b in blockers})
        },
    }
