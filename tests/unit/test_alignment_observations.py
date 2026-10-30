"""Observation match levels and weak evidence (P1.1-D)."""

from agent2utau.alignment import Observation, build_evidence, match_observations
from agent2utau.alignment.lyrics import parse_locked_lyrics
from agent2utau.alignment.observations import LEVEL_WEIGHTS


def obs(text, start, end, source="hfa", method="sequence", level="exact_text", detail=""):
    return Observation(text=text, start=start, end=end, source=source,
                       detail=detail, method=method, level=level)


def test_an_identical_text_is_matched_exactly():
    syllables = parse_locked_lyrics(["年轮"])
    matched, report = match_observations([obs("年", 1.0, 1.4), obs("轮", 1.4, 1.9)], syllables)
    assert set(matched) == {"s0001", "s0002"}
    assert matched["s0001"].level == "exact_text"
    assert report == []


def test_a_token_joined_observation_is_exact_token():
    syllables = parse_locked_lyrics(["年轮"])
    matched, _ = match_observations(
        [obs("年", 1.0, 1.4, method="token", level="exact_token", detail="w0000"),
         obs("轮", 1.4, 1.9, method="token", level="exact_token", detail="w0001")],
        syllables)
    assert matched["s0001"].level == "exact_token"


def test_a_positional_fallback_is_reported_as_weak():
    syllables = parse_locked_lyrics(["年轮"])
    matched, report = match_observations([obs("X", 1.0, 1.4), obs("轮", 1.4, 1.9)], syllables)
    kinds = {row["kind"] for row in report}
    assert "observation_positional_fallback" in kinds
    assert matched["s0001"].level == "positional"
    assert matched["s0001"].method == "positional"


def test_a_residual_match_is_reported_as_residual_text():
    """The first pass aligns greedily; leftovers are matched in a second pass."""
    syllables = parse_locked_lyrics(["年轮"])
    matched, report = match_observations(
        [obs("甲", 1.0, 1.2), obs("轮", 1.2, 1.6),
         obs("乙", 1.6, 1.8), obs("年", 1.8, 2.2)], syllables)
    levels = {row.get("level") for row in report}
    assert "residual_text" in levels
    assert any(m.level == "residual_text" for m in matched.values())


def test_matched_observations_are_not_reported_as_unused():
    """Regression: the fallback used to leave 'used' out of sync."""
    syllables = parse_locked_lyrics(["年轮"])
    _, report = match_observations([obs("X", 1.0, 1.4), obs("轮", 1.4, 1.9)], syllables)
    unused = [row for row in report if row["kind"] == "observation_unused"]
    assert unused == []


def test_weak_evidence_may_not_drive_a_large_displacement():
    """A weak observation must not pull a syllable far from the singer."""
    weak = build_evidence(
        parse_locked_lyrics(["年"]),
        {"s0001": obs("年", 1.0, 1.4, method="positional", level="positional")})
    strong = build_evidence(
        parse_locked_lyrics(["年"]),
        {"s0001": obs("年", 1.0, 1.4, level="exact_text")})
    assert weak["s0001"].anchor_weight < strong["s0001"].anchor_weight
    assert LEVEL_WEIGHTS["positional"] < LEVEL_WEIGHTS["exact_text"]


def test_a_missing_observation_leaves_the_syllable_without_an_anchor():
    syllables = parse_locked_lyrics(["年轮"])
    matched, report = match_observations([obs("年", 1.0, 1.4)], syllables)
    evidence = build_evidence(syllables, matched)
    assert evidence["s0001"].anchor_s == 1.0
    assert evidence["s0002"].anchor_s is None
    assert evidence["s0002"].anchor_level == "missing"
    assert any(row["kind"] == "observation_missing" for row in report)
