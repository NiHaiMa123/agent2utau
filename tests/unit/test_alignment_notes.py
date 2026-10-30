"""GAME note events -> stable note ids, one-grid ticks, clock anomalies."""

from agent2utau.alignment import note_anomalies, normalize_notes
from agent2utau.openutau.build import sec_to_tick


def raw(start, dur, tone, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def test_ids_follow_the_original_index():
    notes = normalize_notes([raw(0.0, 0.5, 60.0), raw(0.5, 0.5, 62.0)])
    assert [n.note_id for n in notes] == ["n0001", "n0002"]
    assert [n.index for n in notes] == [0, 1]


def test_original_values_are_preserved():
    notes = normalize_notes([raw(1.25, 0.5, 60.5, voiced=False)])
    note = notes[0]
    assert note.start == 1.25
    assert note.dur == 0.5
    assert note.tone == 60.5
    assert note.voiced is False
    assert note.rest is True
    assert note.end == 1.75


def test_ticks_use_one_grid_and_duration_is_derived_from_the_bounds():
    notes = normalize_notes([raw(1.0, 0.5, 60.0), raw(1.5, 0.5, 62.0)])
    assert notes[0].start_tick == sec_to_tick(1.0)
    assert notes[0].end_tick == sec_to_tick(1.5)
    assert notes[0].duration_tick == notes[0].end_tick - notes[0].start_tick
    assert notes[1].start_tick == notes[0].end_tick


def test_zero_length_note_is_reported():
    notes = normalize_notes([raw(1.0, 0.0, 60.0)])
    kinds = {row["kind"] for row in note_anomalies(notes)}
    assert "non_positive_duration" in kinds


def test_overlap_is_reported():
    notes = normalize_notes([raw(1.0, 0.6, 60.0), raw(1.4, 0.3, 62.0)])
    kinds = {row["kind"] for row in note_anomalies(notes)}
    assert "overlap" in kinds


def test_gap_is_reported_but_is_not_an_error():
    notes = normalize_notes([raw(1.0, 0.5, 60.0), raw(2.0, 0.5, 62.0)])
    kinds = {row["kind"] for row in note_anomalies(notes)}
    assert kinds == {"gap"}
