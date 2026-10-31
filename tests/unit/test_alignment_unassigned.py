"""Every unassigned voiced note must have a documented destination (P1.2-D)."""

from agent2utau.alignment import Observation
from agent2utau.alignment.unassigned import (
    find_unassigned_voiced_notes,
    unassigned_candidates,
)


def raw(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


class Note:
    def __init__(self, index, start, dur, tone=60.0, voiced=True):
        self.index = index
        self.note_id = f"n{index + 1:04d}"
        self.start = start
        self.end = start + dur
        self.dur = dur
        self.tone = tone
        self.voiced = voiced

    @property
    def rest(self):
        return not self.voiced


class Syllable:
    def __init__(self, syllable_id, text, line_index=0):
        self.syllable_id = syllable_id
        self.text = text
        self.line_index = line_index


def test_a_note_with_vocal_evidence_is_not_called_a_false_positive():
    """Vocal evidence plus no adjacency: the note needs alignment, not deletion."""
    notes = [Note(0, 0.0, 0.5), Note(1, 0.7, 0.2)]
    syllables = [Syllable("s0001", "年")]
    observation = Observation("年", 0.7, 0.9, "hfa", level="exact_text")
    rows = find_unassigned_voiced_notes(notes, {"n0001": "s0001"}, syllables, [observation])
    assert [r["note_id"] for r in rows] == ["n0002"]
    assert rows[0]["classification"] == "needs_alignment"
    assert rows[0]["reason_code"] == "vocal_evidence_without_owner"


def test_a_short_note_without_vocal_evidence_may_be_a_false_positive():
    notes = [Note(0, 0.0, 0.5), Note(1, 0.7, 0.08)]
    syllables = [Syllable("s0001", "年")]
    rows = find_unassigned_voiced_notes(notes, {"n0001": "s0001"}, syllables, [])
    assert rows[0]["classification"] == "probable_false_positive"
    assert rows[0]["reason_code"] == "no_vocal_evidence_short_note"
    assert rows[0]["vocal_evidence"] == []


def test_a_note_next_to_a_syllable_note_is_a_melisma_candidate():
    notes = [Note(0, 0.0, 0.5), Note(1, 0.5, 0.3)]
    syllables = [Syllable("s0001", "年")]
    rows = find_unassigned_voiced_notes(notes, {"n0001": "s0001"}, syllables, [])
    assert rows[0]["classification"] == "candidate_melisma"
    assert rows[0]["neighbour_syllable"]["syllable_id"] == "s0001"


def test_an_unassigned_note_next_to_a_rest_is_marked_as_rest_or_nonlead():
    notes = [Note(0, 0.0, 0.5, voiced=False), Note(1, 0.5, 0.3)]
    syllables = [Syllable("s0001", "年")]
    rows = find_unassigned_voiced_notes(notes, {}, syllables, [])
    assert rows[0]["classification"] == "rest_or_nonlead"
    assert rows[0]["previous_note"]["rest"] is True


def test_candidates_state_their_effect_and_authorization():
    notes = [Note(0, 0.0, 0.5), Note(1, 0.7, 0.3)]
    syllables = [Syllable("s0001", "年")]
    rows = find_unassigned_voiced_notes(notes, {"n0001": "s0001"}, syllables, [])
    options = {c["option"]: c for c in unassigned_candidates(rows[0], notes[0])}
    assert options["merge_into_syllable"]["requires_authorization"] is True
    assert options["close_gap"]["requires_authorization"] is True
    assert options["repeat_character"]["status"] == "forbidden_without_human"


def test_every_record_is_unreviewed_until_a_human_looks_at_it():
    notes = [Note(0, 0.0, 0.5), Note(1, 0.5, 0.3)]
    syllables = [Syllable("s0001", "年")]
    rows = find_unassigned_voiced_notes(notes, {"n0001": "s0001"}, syllables, [])
    assert rows[0]["reviewed"] is False
