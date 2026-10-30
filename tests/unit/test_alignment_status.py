"""Result states and exit codes (P1.1-A)."""

from agent2utau.alignment.status import (
    EXIT_INCOMPLETE,
    EXIT_INVALID,
    EXIT_VALID,
    STATUS_INCOMPLETE,
    STATUS_INVALID,
    STATUS_VALID,
    classify,
    exit_code,
)


def test_a_clean_run_is_valid():
    status = classify(hard_problems=[], unresolved_syllables=[],
                      unresolved_note_ids=[], review_required=[])
    assert status == STATUS_VALID
    assert exit_code(status) == EXIT_VALID


def test_unresolved_syllables_make_the_run_incomplete():
    status = classify(hard_problems=[], unresolved_syllables=["s0007"],
                      unresolved_note_ids=[], review_required=[])
    assert status == STATUS_INCOMPLETE
    assert exit_code(status) == EXIT_INCOMPLETE


def test_an_unresolved_note_also_makes_the_run_incomplete():
    status = classify(hard_problems=[], unresolved_syllables=[],
                      unresolved_note_ids=["n0060"], review_required=[])
    assert status == STATUS_INCOMPLETE


def test_review_required_items_make_the_run_incomplete():
    status = classify(hard_problems=[], unresolved_syllables=[],
                      unresolved_note_ids=[], review_required=["s0012"])
    assert status == STATUS_INCOMPLETE


def test_a_hard_problem_makes_the_run_invalid():
    status = classify(hard_problems=["clock: overlap n0003"], unresolved_syllables=[],
                      unresolved_note_ids=[], review_required=[])
    assert status == STATUS_INVALID
    assert exit_code(status) == EXIT_INVALID


def test_invalid_wins_over_incomplete():
    status = classify(hard_problems=["clock: overlap"], unresolved_syllables=["s0001"],
                      unresolved_note_ids=["n0001"], review_required=["s0002"])
    assert status == STATUS_INVALID


def test_a_diagnostic_run_is_never_valid():
    status = classify(hard_problems=[], unresolved_syllables=[], unresolved_note_ids=[],
                      review_required=[], diagnostic_only=True)
    assert status == STATUS_INCOMPLETE


def test_incomplete_only_passes_when_diagnostics_are_requested():
    assert exit_code(STATUS_INCOMPLETE) == EXIT_INCOMPLETE
    assert exit_code(STATUS_INCOMPLETE, allow_incomplete=True) == EXIT_VALID
    assert exit_code(STATUS_INVALID, allow_incomplete=True) == EXIT_INVALID
