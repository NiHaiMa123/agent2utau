"""Every voiced GAME note must have a documented destination (P1.2-D).

A voiced note that no syllable owns is not automatically an error - GAME can
over-segment a fast passage - but it must never disappear quietly.  This
module gives every such note a record:

* its own clock and pitch,
* the notes and syllables around it,
* the vocal evidence (HFA / ASR) that refers to it,
* a classification and a reason code.

Classification rules use *independent* evidence only.  A note that no vocal
observation covers may be called a probable false positive; everything else
stays under review.
"""

from __future__ import annotations

from typing import Sequence

from .candidates import SyllableEvidence
from .notes import NoteEvent

#: How far a vocal observation may reach to count as evidence for a note.
EVIDENCE_WINDOW_S = 0.15


def _classify(
    note: NoteEvent,
    previous: NoteEvent | None,
    following: NoteEvent | None,
    evidence_hits: list[dict],
    neighbour_syllable: dict | None,
    line_interval: tuple[float, float] | None,
) -> tuple[str, str, str]:
    """Return (classification, reason_code, detail).

    The order follows the strength of the evidence: a structural fact (the
    note touches a rest, or it follows a syllable's note without a gap) is
    checked before a negative fact (no vocal observation covers the note).
    """
    if (previous is not None and previous.rest) or (following is not None and following.rest):
        return ("rest_or_nonlead",
                "no_vocal_evidence_next_to_rest",
                "the note touches a rest and no singing covers it")
    if neighbour_syllable is not None and previous is not None:
        gap = note.start - previous.end
        if 0 <= gap <= 0.05:
            return ("candidate_melisma",
                    "adjacent_to_syllable_note",
                    f"the note follows {previous.note_id} of syllable "
                    f"{neighbour_syllable['syllable_id']} with no gap; it may be another "
                    f"note of the same syllable and needs a decision")
    if not evidence_hits:
        if note.dur <= 0.12:
            return ("probable_false_positive",
                    "no_vocal_evidence_short_note",
                    f"no HFA/ASR observation covers this {round(note.dur, 3)} s note")
        return ("probable_false_positive",
                "no_vocal_evidence",
                "no HFA/ASR observation covers this note")
    if line_interval is not None and not (line_interval[0] - 0.6 <= note.start
                                          <= line_interval[1] + 0.6):
        return ("needs_alignment",
                "vocal_evidence_outside_own_line",
                "a vocal observation covers this note but it lies outside the line of the "
                "nearest syllable")
    return ("needs_alignment",
            "vocal_evidence_without_owner",
            "a vocal observation covers this note but no syllable owns it")


def unassigned_candidates(row: dict, previous: NoteEvent | None) -> list[dict]:
    """Limited options for an unassigned voiced note.

    None of them is applied automatically: two of them change the song
    (timing or note count) and one would change the lyrics.
    """
    options: list[dict] = []
    note_id = row["note_id"]
    neighbour = row.get("neighbour_syllable")
    if neighbour:
        options.append({
            "candidate_id": f"unassigned:{note_id}:merge_into_syllable",
            "option": "merge_into_syllable",
            "effect": f"give {note_id} to syllable {neighbour['syllable_id']} as a sustain",
            "changes": ["note_count", "syllable_length"],
            "requires_authorization": True,
            "status": "candidate",
        })
    if previous is not None and not previous.rest:
        gap = row["start_s"] - previous.end
        if gap > 0.001:
            options.append({
                "candidate_id": f"unassigned:{note_id}:close_gap",
                "option": "close_gap",
                "effect": f"move {note_id} earlier by {round(gap, 4)} s so it touches "
                          f"{previous.note_id}",
                "changes": ["note_start"],
                "requires_authorization": True,
                "status": "candidate",
            })
    options.append({
        "candidate_id": f"unassigned:{note_id}:repeat_character",
        "option": "repeat_character",
        "effect": f"write the character again for {note_id}",
        "changes": ["lyrics"],
        "requires_authorization": True,
        "status": "forbidden_without_human",
    })
    return options


def find_unassigned_voiced_notes(
    notes: Sequence[NoteEvent],
    owner_by_note_id: dict[str, str],
    syllables: Sequence,
    observations: Sequence,
    line_intervals: dict[int, dict] | None = None,
) -> list[dict]:
    """List every voiced note without an owner, with its evidence."""
    ordered = sorted(notes, key=lambda n: n.index)
    syllable_by_id = {s.syllable_id: s for s in syllables}
    rows: list[dict] = []
    for position, note in enumerate(ordered):
        if not note.voiced or note.note_id in owner_by_note_id:
            continue
        previous = ordered[position - 1] if position > 0 else None
        following = ordered[position + 1] if position + 1 < len(ordered) else None
        hits = [
            {"source": observation.source, "text": observation.text,
             "start_s": round(observation.start, 4), "end_s": round(observation.end, 4),
             "level": getattr(observation, "level", "exact_text")}
            for observation in observations
            if observation.start - EVIDENCE_WINDOW_S <= note.end
            and observation.end + EVIDENCE_WINDOW_S >= note.start
        ]
        # the syllable that owns the note before it, if any
        neighbour_syllable = None
        if previous is not None:
            owner = owner_by_note_id.get(previous.note_id)
            if owner:
                neighbour_syllable = {
                    "syllable_id": owner,
                    "text": syllable_by_id[owner].text if owner in syllable_by_id else "",
                }
        line_interval = None
        if line_intervals:
            for _line_index, line in sorted(line_intervals.items()):
                start, end = line.get("interval_s", [None, None])
                if start is not None and start - 1.5 <= note.start <= end + 1.5:
                    line_interval = (start, end)
                    break
        classification, reason_code, detail = _classify(
            note, previous, following, hits, neighbour_syllable, line_interval)
        rows.append({
            "note_id": note.note_id,
            "index": note.index,
            "start_s": round(note.start, 4),
            "end_s": round(note.end, 4),
            "dur_s": round(note.dur, 4),
            "tone": round(note.tone, 4),
            "classification": classification,
            "reason_code": reason_code,
            "detail": detail,
            "previous_note": None if previous is None else {
                "note_id": previous.note_id, "rest": previous.rest,
                "end_s": round(previous.end, 4)},
            "next_note": None if following is None else {
                "note_id": following.note_id, "rest": following.rest,
                "start_s": round(following.start, 4)},
            "neighbour_syllable": neighbour_syllable,
            "vocal_evidence": hits,
            "reviewed": False,
        })
    return rows
