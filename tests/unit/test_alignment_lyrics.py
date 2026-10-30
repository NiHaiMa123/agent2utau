"""Locked lyrics -> stable syllable ids."""

from agent2utau.alignment import (
    build_locked_lyrics_document,
    parse_locked_lyrics,
    validate_locked_lyrics,
)


def test_ids_are_sequential_and_follow_occurrence_order():
    syllables = parse_locked_lyrics(["年轮", "年轮年轮"])
    assert [s.syllable_id for s in syllables] == ["s0001", "s0002", "s0003", "s0004", "s0005", "s0006"]
    assert [s.text for s in syllables] == ["年", "轮", "年", "轮", "年", "轮"]
    assert [s.occurrence for s in syllables] == [1, 1, 2, 2, 3, 3]
    assert [s.index for s in syllables] == [0, 1, 2, 3, 4, 5]


def test_repeated_character_keeps_its_own_id():
    syllables = parse_locked_lyrics(["真的真的"])
    assert len({s.syllable_id for s in syllables}) == 4
    assert all(s.repeated for s in syllables)
    assert [s.occurrence for s in syllables] == [1, 1, 2, 2]


def test_punctuation_and_spaces_are_not_sung():
    syllables = parse_locked_lyrics(["年 轮，"])
    assert [s.text for s in syllables] == ["年", "轮"]
    assert [s.char_index for s in syllables] == [0, 2]


def test_latin_run_is_one_syllable():
    syllables = parse_locked_lyrics(["Hey you"])
    assert [s.text for s in syllables] == ["Hey", "you"]


def test_document_round_trip_and_validator():
    doc = build_locked_lyrics_document(
        "nianlun", ["年轮", "年轮"], verification="user-confirmed", source="test")
    assert doc["syllable_count"] == 4
    assert validate_locked_lyrics(doc) == []


def test_validator_reports_a_broken_occurrence_counter():
    doc = build_locked_lyrics_document(
        "nianlun", ["年轮"], verification="user-confirmed", source="test")
    doc["syllables"][1]["occurrence"] = 5
    problems = validate_locked_lyrics(doc)
    assert any("occurrence" in problem for problem in problems)


def test_validator_reports_a_wrong_syllable_count():
    doc = build_locked_lyrics_document(
        "nianlun", ["年轮"], verification="user-confirmed", source="test")
    doc["syllable_count"] = 9
    assert validate_locked_lyrics(doc)
