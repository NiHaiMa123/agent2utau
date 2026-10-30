"""Canonical (published) lyrics vs. the recording's own phrasing.

The published lyric is the authority for *which characters are sung*; the
recording is the authority for *how they are phrased and repeated*.  This
module aligns the two with a global edit-distance alignment so that

* a character the singer got wrong can be corrected to the published text,
* a line the singer repeated keeps its repeated form, and
* a published line the singer never sang is reported instead of invented.

The alignment is deterministic: no sampling, no model.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import difflib
from typing import Sequence

SCHEMA_VERSION = 1

MATCH_COST = 0
SUBSTITUTION_COST = 1
GAP_COST = 1


@dataclass(frozen=True)
class Character:
    """One character of a lyric sequence with its position in the source."""

    text: str
    unit_index: int
    """Index of the line/phrase this character belongs to."""

    position_in_unit: int
    """Index of the character inside the original line string."""

    alignable: bool = True
    """CJK characters are aligned against each other; latin runs are not.

    A latin word is written as one word but sung as several syllables
    ("Rainie" = "Rai" + "nie").  Only the recording knows how many syllables
    were actually sung, so the published spelling must not override it.
    """


@dataclass
class AlignmentReport:
    """What the canonical text changed (or did not change) in the recording."""

    schema_version: int
    canonical_characters: int
    recording_characters: int
    aligned_equal: int
    substitutions: list[dict]
    recording_only: list[dict]
    canonical_only: list[dict]
    latin_from_recording: list[dict]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["schema_version"] = SCHEMA_VERSION
        return data


def _characters(lines: Sequence[str]) -> list[Character]:
    out: list[Character] = []
    for unit_index, line in enumerate(lines):
        for position, ch in enumerate(line):
            if ch.isspace():
                continue
            alignable = "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"
            out.append(Character(text=ch, unit_index=unit_index,
                                 position_in_unit=position, alignable=alignable))
    return out


def align_sequences(canonical: Sequence[Character], recording: Sequence[Character]) -> list[tuple[int, int]]:
    """Global alignment (Needleman-Wunsch) as pairs of (canonical, recording).

    Only *alignable* characters take part; latin runs are kept out of the
    alignment because their syllable count belongs to the recording.
    """
    pairs: list[tuple[int, int]] = []
    canonical_index = [i for i, c in enumerate(canonical) if c.alignable]
    recording_index = [i for i, c in enumerate(recording) if c.alignable]
    a = [canonical[i].text for i in canonical_index]
    b = [recording[i].text for i in recording_index]
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i * GAP_COST
    for j in range(1, m + 1):
        dp[0][j] = j * GAP_COST
    for i in range(1, n + 1):
        row, previous = dp[i], dp[i - 1]
        for j in range(1, m + 1):
            same = a[i - 1] == b[j - 1]
            diagonal = previous[j - 1] + (MATCH_COST if same else SUBSTITUTION_COST)
            row[j] = min(diagonal, previous[j] + GAP_COST, row[j - 1] + GAP_COST)
    i, j = n, m
    matched: list[tuple[int, int]] = []
    while i > 0 and j > 0:
        same = a[i - 1] == b[j - 1]
        if dp[i][j] == dp[i - 1][j - 1] + (MATCH_COST if same else SUBSTITUTION_COST):
            matched.append((canonical_index[i - 1], recording_index[j - 1]))
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + GAP_COST:
            i -= 1
        else:
            j -= 1
    matched.reverse()
    pairs.extend(matched)
    return pairs


def apply_canonical(
    recording_lines: Sequence[str],
    canonical_lines: Sequence[str],
    *,
    apply: bool = False,
) -> tuple[list[str], AlignmentReport]:
    """Compare the recorded text with the published text.

    ``apply`` defaults to **False**: the published lyric is a candidate
    source, not a fact about the recording.  The report then lists the
    characters that differ as *pending review* and the recorded text is left
    untouched - swapping a word for the internet's wording without checking
    the recording would replace a fact with a guess.
    """
    canonical = _characters(canonical_lines)
    recording = _characters(recording_lines)
    pairs = align_sequences(canonical, recording)

    corrected = [list(line) for line in recording_lines]
    substitutions: list[dict] = []
    equal = 0
    matched_recording: set[int] = set()
    for canonical_index, recording_index in pairs:
        matched_recording.add(recording_index)
        canonical_char = canonical[canonical_index]
        recording_char = recording[recording_index]
        if canonical_char.text == recording_char.text:
            equal += 1
            continue
        unit = recording_char.unit_index
        position = recording_char.position_in_unit
        original = corrected[unit][position]
        if apply:
            corrected[unit][position] = canonical_char.text
        substitutions.append({
            "unit_index": unit,
            "position": position,
            "from": original,
            "to": canonical_char.text,
            "canonical_line_index": canonical_char.unit_index,
            "status": "applied" if apply else "pending_review",
            "requires_review": not apply,
            "detail": "published wording differs from the recorded wording; a human must "
                      "confirm which one was sung before it replaces the locked text",
        })

    recording_only: list[dict] = []
    latin_from_recording: list[dict] = []
    for index, char in enumerate(recording):
        if index in matched_recording:
            continue
        if char.alignable:
            recording_only.append({
                "unit_index": char.unit_index,
                "position": char.position_in_unit,
                "text": char.text,
            })
        else:
            latin_from_recording.append({
                "unit_index": char.unit_index,
                "position": char.position_in_unit,
                "text": char.text,
            })

    canonical_only: list[dict] = []
    matched_canonical = {c for c, _ in pairs}
    for index, char in enumerate(canonical):
        if index in matched_canonical or not char.alignable:
            continue
        canonical_only.append({
            "canonical_line_index": char.unit_index,
            "position": char.position_in_unit,
            "text": char.text,
        })

    report = AlignmentReport(
        schema_version=SCHEMA_VERSION,
        canonical_characters=len(canonical),
        recording_characters=len(recording),
        aligned_equal=equal,
        substitutions=substitutions,
        recording_only=recording_only,
        canonical_only=canonical_only,
        latin_from_recording=latin_from_recording,
    )
    return ["".join(line) for line in corrected], report


def similarity(left: str, right: str) -> float:
    """Character-level similarity of two texts (for reporting only)."""
    matcher = difflib.SequenceMatcher(a=left, b=right, autojunk=False)
    return matcher.ratio()
