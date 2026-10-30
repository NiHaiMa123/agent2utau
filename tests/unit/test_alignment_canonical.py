"""Published lyrics vs. the recording's own phrasing."""

from agent2utau.alignment.canonical import apply_canonical


def test_a_wrong_character_is_listed_for_review_and_not_applied():
    """The published wording is a candidate, not a fact about the recording."""
    corrected, report = apply_canonical(["是有缘却无份"], ["是有缘却无分"])
    assert corrected == ["是有缘却无份"]
    assert len(report.substitutions) == 1
    assert report.substitutions[0]["from"] == "份"
    assert report.substitutions[0]["to"] == "分"
    assert report.substitutions[0]["status"] == "pending_review"
    assert report.substitutions[0]["requires_review"] is True


def test_an_approved_substitution_can_be_applied_explicitly():
    corrected, report = apply_canonical(["是有缘却无份"], ["是有缘却无分"], apply=True)
    assert corrected == ["是有缘却无分"]
    assert report.substitutions[0]["status"] == "applied"


def test_an_unchanged_song_reports_no_substitution():
    corrected, report = apply_canonical(["雨停滞天空之间"], ["雨停滞天空之间"])
    assert corrected == ["雨停滞天空之间"]
    assert report.substitutions == []
    assert report.aligned_equal == report.canonical_characters


def test_a_repeated_line_keeps_its_repeated_form():
    corrected, report = apply_canonical(
        ["可惜从没人陪我演这剧本", "可惜从没人陪我演这剧本"],
        ["可惜从没人陪我演这剧本"])
    assert corrected == ["可惜从没人陪我演这剧本", "可惜从没人陪我演这剧本"]
    assert report.substitutions == []
    assert report.recording_only


def test_a_latin_run_keeps_the_recorded_syllables():
    """The published spelling must not override how many syllables were sung."""
    corrected, report = apply_canonical(["我爱上给我勇气的 Rainie Love"], ["我爱上给我勇气的 Rainie Love"])
    assert corrected == ["我爱上给我勇气的 Rainie Love"]
    assert report.substitutions == []
    assert report.latin_from_recording


def test_a_latin_difference_does_not_touch_the_sung_syllables():
    """Recording "Rai nie Love" (3 sung syllables) vs published "Rainie Love"."""
    corrected, report = apply_canonical(["Rai nie Love"], ["Rainie Love"])
    assert corrected == ["Rai nie Love"]
    assert report.substitutions == []
    assert len(report.latin_from_recording) == 10


def test_published_lines_the_singer_never_sang_are_reported():
    corrected, report = apply_canonical(["是树根"], ["是树根", "春去秋来的茂盛"])
    assert corrected == ["是树根"]
    assert report.canonical_only
