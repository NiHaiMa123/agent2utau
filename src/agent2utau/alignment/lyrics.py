"""Locked lyric text -> stable syllable ids.

The locked lyric is the only authority for *which* character is sung; ASR is a
rough hint and may never silently change a character.  Syllable ids are assigned
by occurrence order over the whole song, so a repeated character still owns a
unique, stable id (``s0001``, ``s0002`` ...).

Line structure is preserved: a line is one sung phrase and therefore also the
unit that must not be crossed when notes are assigned (see
``docs/guides/repository-layout.md`` and the mapping hard constraints in
``plan.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Iterable, Sequence

SCHEMA_VERSION = 1

#: Punctuation and whitespace are never sung; they only delimit phrases.
NON_SUNG = set("，。！？；、,.!?;:…—－·「」『』（）()《》〈〉“”\"' \t\r\n")

#: Latin/digit runs are kept as a single syllable: the phonemizer decides how
#: to pronounce them, the alignment layer only needs a stable unit.
def _is_cjk(ch: str) -> bool:
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


@dataclass(frozen=True)
class Syllable:
    """One sung character (or latin/digit run) with a song-wide stable id."""

    syllable_id: str
    index: int
    text: str
    line_index: int
    char_index: int
    occurrence: int
    repeated: bool

    def as_dict(self) -> dict:
        return asdict(self)


def split_line(text: str) -> list[tuple[str, int]]:
    """Split one lyric line into (syllable_text, char_index) pairs."""
    out: list[tuple[str, int]] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in NON_SUNG:
            i += 1
            continue
        if _is_cjk(ch):
            out.append((ch, i))
            i += 1
            continue
        j = i
        while j < len(text) and text[j] not in NON_SUNG and not _is_cjk(text[j]):
            j += 1
        out.append((text[i:j], i))
        i = j
    return out


def parse_locked_lyrics(lines: Sequence[str]) -> list[Syllable]:
    """Assign song-wide syllable ids to the locked lyric lines."""
    counts: dict[str, int] = {}
    parsed: list[tuple[str, int, int, str]] = []
    for line_index, line in enumerate(lines):
        for text, char_index in split_line(line):
            counts[text] = counts.get(text, 0) + 1
            parsed.append((text, line_index, char_index, counts[text]))
    repeated = {text: n > 1 for text, n in counts.items()}
    return [
        Syllable(
            syllable_id=f"s{index + 1:04d}",
            index=index,
            text=text,
            line_index=line_index,
            char_index=char_index,
            occurrence=occurrence,
            repeated=repeated[text],
        )
        for index, (text, line_index, char_index, occurrence) in enumerate(parsed)
    ]


def load_locked_lyrics(path: str | Path) -> tuple[list[Syllable], dict]:
    """Read a locked-lyric document and return (syllables, document).

    Expected document shape::

        {"schema_version": 1, "song_id": "...", "verification": "user-confirmed",
         "lines": [{"line": 0, "text": "..."}, ...]}
    """
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported locked lyric schema: {doc.get('schema_version')}")
    raw_lines = doc.get("lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        raise ValueError("Locked lyric document needs a non-empty 'lines' list")
    texts: list[str] = []
    for row in raw_lines:
        texts.append(row["text"] if isinstance(row, dict) else str(row))
    return parse_locked_lyrics(texts), doc


def build_locked_lyrics_document(
    song_id: str,
    lines: Sequence[str],
    *,
    verification: str,
    source: str,
    extra: dict | None = None,
) -> dict:
    """Build the on-disk locked-lyric document (the P0 deliverable)."""
    syllables = parse_locked_lyrics(lines)
    doc = {
        "schema_version": SCHEMA_VERSION,
        "song_id": song_id,
        "verification": verification,
        "source": source,
        "line_count": len(lines),
        "syllable_count": len(syllables),
        "lines": [{"line": i, "text": t} for i, t in enumerate(lines)],
        "syllables": [s.as_dict() for s in syllables],
    }
    if extra:
        doc.update(extra)
    return doc


def syllable_lines(syllables: Iterable[Syllable]) -> dict[int, list[Syllable]]:
    """Group syllables by their lyric line."""
    out: dict[int, list[Syllable]] = {}
    for s in syllables:
        out.setdefault(s.line_index, []).append(s)
    return out
