"""Behaviour of the observation confidence, not the weight numbers (P1.2-A).

A weak observation must not drag a syllable away from the right note and must
not make unresolved more likely.  These tests therefore check the *decision*,
not the weight.
"""

from agent2utau.alignment import MappingConfig, Observation, build_evidence, map_syllables_to_notes
from agent2utau.alignment.candidates import MappingConfig as MC
from agent2utau.alignment.lyrics import parse_locked_lyrics
from agent2utau.alignment.notes import normalize_notes


def raw(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def map_with(lines, notes, observations, **config):
    syllables = parse_locked_lyrics(lines)
    events = normalize_notes(notes)
    evidence = build_evidence(syllables, observations)
    mapping = map_syllables_to_notes(syllables, events, evidence,
                                     MappingConfig(**config), song_id="test")
    return mapping


def test_an_exact_anchor_influences_the_choice():
    """A trusted observation may decide between two possible notes."""
    mapping = map_with(
        ["年", "轮"],
        [raw(0.0, 0.4), raw(0.4, 0.4), raw(5.0, 0.4), raw(5.4, 0.4)],
        {"s0001": Observation("年", 0.0, 0.4, "hfa", level="exact_text"),
         "s0002": Observation("轮", 5.0, 5.4, "hfa", level="exact_text")},
    )
    rows = {r["syllable_id"]: r for r in mapping["mapping"]}
    assert rows["s0001"]["note_ids"] == ["n0001"]
    assert rows["s0002"]["note_ids"] == ["n0003"]


def test_a_wrong_weak_anchor_does_not_drag_the_mapping():
    """A positional anchor far away must not pull the syllable to it."""
    wrong = map_with(
        ["年", "轮"],
        [raw(0.0, 0.4), raw(0.4, 0.4), raw(5.0, 0.4), raw(5.4, 0.4)],
        {"s0001": Observation("年", 0.0, 0.4, "hfa", level="exact_text"),
         "s0002": Observation("轮", 5.0, 5.4, "hfa", method="positional",
                               level="positional")},
    )
    # the weak anchor for 轮 points at 5.0 s, which is where 轮's own note is;
    # move it to the wrong place and the mapping must not follow
    dragged = map_with(
        ["年", "轮"],
        [raw(0.0, 0.4), raw(0.4, 0.4), raw(5.0, 0.4), raw(5.4, 0.4)],
        {"s0001": Observation("年", 0.0, 0.4, "hfa", level="exact_text"),
         "s0002": Observation("轮", 0.0, 0.4, "hfa", method="positional",
                               level="positional")},
    )
    exact = map_with(
        ["年", "轮"],
        [raw(0.0, 0.4), raw(0.4, 0.4), raw(5.0, 0.4), raw(5.4, 0.4)],
        {"s0001": Observation("年", 0.0, 0.4, "hfa", level="exact_text"),
         "s0002": Observation("轮", 5.0, 5.4, "hfa", level="exact_text")},
    )
    dragged_rows = {r["syllable_id"]: r for r in dragged["mapping"]}
    exact_rows = {r["syllable_id"]: r for r in exact["mapping"]}
    assert exact_rows["s0002"]["note_ids"] == ["n0003"]
    # the wrong weak anchor must not move 轮 onto the first note
    assert dragged_rows["s0002"]["note_ids"] != ["n0001"]


def test_a_weak_anchor_does_not_create_more_unresolved_than_a_trusted_one():
    notes = [raw(i * 0.5, 0.5) for i in range(8)]
    trusted = map_with(
        ["年" * 8], notes,
        {f"s{i + 1:04d}": Observation("年", i * 0.5, i * 0.5 + 0.5, "hfa", level="exact_text")
         for i in range(8)},
    )
    weak = map_with(
        ["年" * 8], notes,
        {f"s{i + 1:04d}": Observation("年", i * 0.5, i * 0.5 + 0.5, "hfa",
                                       method="positional", level="positional")
         for i in range(8)},
    )
    assert (trusted["coverage"]["syllable_unresolved"]
            <= weak["coverage"]["syllable_unresolved"])


def test_an_observation_shared_by_two_syllables_becomes_a_review_signal():
    syllables = parse_locked_lyrics(["年", "轮"])
    shared = Observation("年", 0.0, 0.4, "hfa", level="exact_text")
    evidence = build_evidence(syllables, {"s0001": shared, "s0002": shared})
    assert evidence["s0001"].trust == "conflict"
    assert evidence["s0002"].trust == "conflict"
    assert "observation_shared_with_other_syllable" in evidence["s0001"].review_signals


def test_an_observation_from_another_line_is_a_review_signal():
    syllables = parse_locked_lyrics(["年", "轮"])
    evidence = build_evidence(syllables, {
        "s0001": Observation("年", 0.0, 0.4, "hfa", level="exact_text", same_line=False),
    })
    assert evidence["s0001"].trust == "conflict"
    assert "observation_line_mismatch" in evidence["s0001"].review_signals


def test_a_weak_anchor_outside_the_trust_window_does_not_discriminate():
    """The cost of a far-away weak observation must be the same as no anchor."""
    from agent2utau.alignment.candidates import _assign_cost

    notes = normalize_notes([raw(0.0, 0.4)])
    config = MC()
    weak_far = build_evidence(parse_locked_lyrics(["年"]), {
        "s0001": Observation("年", 9.0, 9.4, "hfa", method="positional", level="positional"),
    })["s0001"]
    none = build_evidence(parse_locked_lyrics(["年"]), {})["s0001"]
    cost_far = _assign_cost(weak_far, notes, 0, 1, config, [0])
    cost_none = _assign_cost(none, notes, 0, 1, config, [0])
    assert abs(cost_far - cost_none) < 1e-9
