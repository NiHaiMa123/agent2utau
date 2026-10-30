"""Deterministic syllable <-> note mapping and the P1 hard constraints."""

from agent2utau.alignment import (
    MappingConfig,
    build_evidence,
    map_syllables_to_notes,
    mapping_to_ustx_notes,
    normalize_notes,
    parse_locked_lyrics,
    validate_mapping,
    validate_ustx_rows,
)


def raw(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def map_lines(lines, notes, **kwargs):
    syllables = parse_locked_lyrics(lines)
    events = normalize_notes(notes)
    evidence = build_evidence(syllables)
    mapping = map_syllables_to_notes(
        syllables, events, evidence, MappingConfig(**kwargs), song_id="test")
    return syllables, events, mapping


def test_one_syllable_per_note_keeps_the_order():
    _, notes, mapping = map_lines(
        ["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5)])
    mapped = [row for row in mapping["mapping"] if row["status"] == "mapped"]
    assert [row["syllable_id"] for row in mapped] == ["s0001", "s0002"]
    assert [row["note_ids"] for row in mapped] == [["n0001"], ["n0002"]]
    assert validate_mapping(mapping, parse_locked_lyrics(["年轮"]), notes) == []


def test_a_trailing_note_is_kept_as_a_sustain_instead_of_being_dropped():
    _, notes, mapping = map_lines(
        ["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5), raw(1.0, 0.5)])
    mapped = {row["syllable_id"]: row for row in mapping["mapping"]}
    assert mapped["s0001"]["note_ids"] == ["n0001"]
    assert mapped["s0002"]["note_ids"][0] == "n0002"
    assert mapped["s0002"]["sustain_note_ids"] == ["n0003"]
    assert validate_mapping(mapping, parse_locked_lyrics(["年轮"]), notes) == []


def test_anchors_drive_the_assignment():
    from agent2utau.alignment import Observation

    syllables = parse_locked_lyrics(["年轮"])
    events = normalize_notes([raw(0.0, 0.5), raw(0.5, 0.5), raw(1.0, 0.5)])
    hfa = {
        "s0001": Observation("年", 0.0, 0.4, "hfa"),
        "s0002": Observation("轮", 1.0, 1.45, "hfa"),
    }
    evidence = build_evidence(syllables, hfa)
    mapping = map_syllables_to_notes(syllables, events, evidence, song_id="test")
    mapped = {row["syllable_id"]: row for row in mapping["mapping"]}
    assert mapped["s0001"]["note_ids"] == ["n0001"]
    assert mapped["s0002"]["note_ids"] == ["n0003"]
    assert mapped["s0002"]["evidence"]["anchor_source"] == "hfa"
    assert validate_mapping(mapping, syllables, events) == []


def test_a_syllable_may_own_several_consecutive_notes():
    _, notes, mapping = map_lines(["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5), raw(1.0, 0.5)])
    rows = {row["syllable_id"]: row for row in mapping["mapping"]}
    assert len(rows["s0002"]["note_ids"]) == 2
    assert rows["s0002"]["sustain_note_ids"] == rows["s0002"]["note_ids"][1:]
    assert validate_mapping(mapping, parse_locked_lyrics(["年轮"]), notes) == []


def test_rest_notes_are_never_handed_to_a_syllable():
    _, notes, mapping = map_lines(
        ["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5, voiced=False), raw(1.0, 0.5)])
    used = [nid for row in mapping["mapping"] for nid in row["note_ids"]]
    assert "n0002" not in used
    assert validate_mapping(mapping, parse_locked_lyrics(["年轮"]), notes) == []


def test_surplus_syllables_become_unresolved_and_stay_in_the_coverage():
    syllables, notes, mapping = map_lines(
        ["年轮年轮"], [raw(0.0, 0.5), raw(0.5, 0.5)])
    coverage = mapping["coverage"]
    assert coverage["syllable_total"] == 4
    assert coverage["syllable_mapped"] + coverage["syllable_unresolved"] == 4
    assert coverage["syllable_unresolved"] >= 1
    assert len(mapping["unresolved"]) == coverage["syllable_unresolved"]
    assert validate_mapping(mapping, syllables, notes) == []


def test_mapping_is_deterministic():
    _, _, first = map_lines(["年轮年"], [raw(0.0, 0.5), raw(0.5, 0.5), raw(1.0, 0.5)])
    _, _, second = map_lines(["年轮年"], [raw(0.0, 0.5), raw(0.5, 0.5), raw(1.0, 0.5)])
    assert first == second


def test_window_size_stays_between_five_and_fifteen_characters():
    _, _, mapping = map_lines(
        ["年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮"],
        [raw(i * 0.5, 0.5) for i in range(20)],
        ambiguity_margin=10.0)
    assert mapping["windows"]
    for window in mapping["windows"]:
        assert 5 <= len(window["syllable_ids"]) <= 15
        for candidate in mapping["candidates"]:
            if candidate["window_id"] == window["window_id"]:
                assert candidate["candidate_id"].startswith("map:test:")


def test_ustx_rows_keep_sustain_blocks_touching_their_note():
    _, _, mapping = map_lines(["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5)])
    rows = mapping_to_ustx_notes(mapping, normalize_notes([raw(0.0, 0.5), raw(0.5, 0.5)]))
    assert [row["lyric"] for row in rows] == ["年", "轮"]
    assert validate_ustx_rows(rows) == []


def test_validator_rejects_a_note_used_twice():
    syllables, notes, mapping = map_lines(["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5)])
    mapping["mapping"][1]["note_ids"] = ["n0001"]
    problems = validate_mapping(mapping, syllables, notes)
    assert any("used by" in problem for problem in problems)


def test_validator_rejects_a_dropped_syllable():
    syllables, notes, mapping = map_lines(["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5)])
    mapping["mapping"] = mapping["mapping"][:1]
    problems = validate_mapping(mapping, syllables, notes)
    assert any("no row" in problem for problem in problems)


def test_validator_rejects_a_rest_note_in_a_mapping():
    syllables, notes, mapping = map_lines(
        ["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5, voiced=False)])
    mapping["mapping"][0]["note_ids"] = ["n0002"]
    problems = validate_mapping(mapping, syllables, notes)
    assert any("rest note" in problem for problem in problems)
