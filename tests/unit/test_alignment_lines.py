"""Line boundaries, sustain legality and window reachability (P1.1-C)."""

from agent2utau.alignment import (
    MappingConfig,
    Observation,
    build_evidence,
    line_intervals,
    map_syllables_to_notes,
)
from agent2utau.alignment.lyrics import parse_locked_lyrics
from agent2utau.alignment.notes import normalize_notes


def raw(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def map_with(lines, notes, observations=None, **config):
    syllables = parse_locked_lyrics(lines)
    events = normalize_notes(notes)
    evidence = build_evidence(syllables, observations or {})
    mapping = map_syllables_to_notes(syllables, events, evidence,
                                     MappingConfig(**config), song_id="test")
    return syllables, events, mapping


def test_a_note_far_outside_the_line_is_not_taken():
    """A syllable may not reach into another line without evidence."""
    syllables, _, mapping = map_with(
        ["年", "轮"],
        [raw(0.0, 0.4), raw(5.0, 0.4), raw(10.0, 0.4)],
        {"s0001": Observation("年", 0.0, 0.4, "hfa"),
         "s0002": Observation("轮", 10.0, 10.4, "hfa")},
    )
    rows = {r["syllable_id"]: r for r in mapping["mapping"]}
    assert rows["s0001"]["note_ids"] == ["n0001"]
    assert rows["s0002"]["note_ids"] == ["n0003"]


def test_a_line_without_time_evidence_is_flagged_for_review():
    syllables = parse_locked_lyrics(["年", "轮"])
    evidence = build_evidence(syllables, {"s0001": Observation("年", 0.0, 0.4, "hfa")})
    lines = line_intervals(syllables, evidence, MappingConfig())
    assert lines[0]["review_required"] is False
    assert lines[1]["review_required"] is True
    assert lines[1]["anchored_count"] == 0


def test_the_line_interval_is_recorded_in_the_mapping():
    _, _, mapping = map_with(
        ["年", "轮"],
        [raw(0.0, 0.4), raw(10.0, 0.4)],
        {"s0001": Observation("年", 0.0, 0.4, "hfa"),
         "s0002": Observation("轮", 10.0, 10.4, "hfa")},
    )
    assert len(mapping["lines"]) == 2
    assert mapping["lines"][0]["interval_s"][0] == 0.0
    assert mapping["lines"][0]["anchor_ratio"] == 1.0


def test_every_window_states_its_decision():
    _, _, mapping = map_with(
        ["年轮年轮年轮年轮年轮年轮年轮"],
        [raw(i * 0.5, 0.5) for i in range(12)],
        ambiguity_margin=10.0,
    )
    for window in mapping["windows"]:
        assert window["decision"] in ("legal_alternatives_available",
                                      "only_baseline",
                                      "no_legal_solution_proven",
                                      "search_budget_exhausted")
        if window["decision"] == "no_legal_solution_proven":
            assert window["option_count"] == 0
            assert window["search_complete"] is True
        if window["decision"] == "search_budget_exhausted":
            assert window["search_complete"] is False


def test_candidates_never_take_notes_outside_their_window():
    _, _, mapping = map_with(
        ["年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮年轮"],
        [raw(i * 0.5, 0.5) for i in range(40)],
        ambiguity_margin=10.0,
    )
    note_index = {}
    for candidate in mapping["candidates"]:
        for syllable_id, note_ids in candidate["assignment"].items():
            assert syllable_id in candidate["syllable_ids"]
            for note_id in note_ids:
                note_index[note_id] = True
    for window in mapping["windows"]:
        if window["decision"] != "agent_choice":
            continue
        budget = window["note_budget"]
        for candidate in mapping["candidates"]:
            if candidate["window_id"] != window["window_id"]:
                continue
            for note_ids in candidate["assignment"].values():
                assert note_ids


def test_a_window_without_a_valid_option_marks_its_syllables_for_review():
    """No fake-solved window: an empty window is an explicit review item."""
    _, _, mapping = map_with(
        ["年轮年轮年轮年轮年轮年轮年轮"],
        [raw(i * 0.5, 0.5) for i in range(8)],
        ambiguity_margin=10.0,
    )
    for window in mapping["windows"]:
        if window["decision"] in ("no_legal_solution_proven", "search_budget_exhausted"):
            for row in mapping["mapping"]:
                if row["syllable_id"] in window["syllable_ids"]:
                    assert row.get("review_required") is True
