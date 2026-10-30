"""The baseline must not drop an illegal extender silently (P1.1-B)."""

from pathlib import Path

import pytest

from agent2utau.alignment import MappingConfig, build_evidence, map_syllables_to_notes
from agent2utau.alignment.baseline import (
    MAX_EXTENDER_GAP_TICKS,
    build_baseline_ustx,
    rows_to_segments,
    verify_ustx_notes,
)
from agent2utau.alignment.candidates import mapping_to_ustx_rows
from agent2utau.alignment.lyrics import parse_locked_lyrics
from agent2utau.alignment.notes import normalize_notes


def raw(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def build_rows(lines, notes):
    syllables = parse_locked_lyrics(lines)
    events = normalize_notes(notes)
    evidence = build_evidence(syllables)
    mapping = map_syllables_to_notes(syllables, events, evidence,
                                     MappingConfig(), song_id="test")
    return mapping_to_ustx_rows(mapping, events), mapping


def test_an_extender_across_a_gap_is_reported_not_dropped():
    rows, mapping = build_rows(["声"], [raw(0.0, 0.63), raw(0.79, 0.19)])
    segments, unresolved, candidates = rows_to_segments(rows)
    assert len(unresolved) == 1
    assert unresolved[0]["reason_code"] == "extender_not_touching"
    assert unresolved[0]["gap_tick"] > MAX_EXTENDER_GAP_TICKS
    assert unresolved[0]["note_id"] == "n0002"
    # the note is still part of the mapping
    assert mapping["mapping"][0]["note_ids"] == ["n0001", "n0002"]
    # and it is not silently missing from the report
    assert candidates


def test_the_candidates_state_their_effect_and_need_authorization():
    rows, _ = build_rows(["声"], [raw(0.0, 0.63), raw(0.79, 0.19)])
    _, _, candidates = rows_to_segments(rows)
    options = {c["option"]: c for c in candidates}
    assert set(options) == {"close_gap", "merge_into_character",
                             "split_new_part", "repeat_character"}
    assert options["close_gap"]["requires_authorization"] is True
    assert options["merge_into_character"]["changes"] == ["note_count", "note_tone"]
    assert options["split_new_part"]["status"] == "illegal_by_core"
    assert options["repeat_character"]["status"] == "forbidden_without_human"


def test_a_touching_extender_is_written_to_the_project():
    rows, _ = build_rows(["声"], [raw(0.0, 0.63), raw(0.63, 0.19)])
    segments, unresolved, _ = rows_to_segments(rows)
    assert unresolved == []
    assert len(segments[0]["notes"]) == 2


def test_the_ustx_verification_lists_the_missing_note(tmp_path):
    rows, _ = build_rows(["声"], [raw(0.0, 0.63), raw(0.79, 0.19)])
    report = build_baseline_ustx(rows, tmp_path / "baseline.ustx", name="probe")
    assert report["unresolved_note_ids"] == ["n0002"]
    assert report["notes"] == 1
    verification = verify_ustx_notes(tmp_path / "baseline.ustx", rows)
    assert verification["missing_note_ids"] == ["n0002"]
    assert verification["one_to_one"] is False
    assert verification["extra_note_count"] == 0


def test_a_clean_baseline_verifies_one_to_one(tmp_path):
    rows, _ = build_rows(["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5)])
    build_baseline_ustx(rows, tmp_path / "baseline.ustx", name="probe")
    verification = verify_ustx_notes(tmp_path / "baseline.ustx", rows)
    assert verification["one_to_one"] is True
    assert verification["missing_note_ids"] == []
    assert verification["retuned_note_ids"] == []
