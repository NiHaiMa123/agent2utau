"""Source observations -> auditable evidence and an input manifest.

Observations are *evidence*, never truth:

* ASR gives rough character times and a guessed text; it may not change a
  locked character.
* HFA gives the original singer's syllable observation; it is a time
  observation, not the synthesiser's phoneme clock.
* GAME gives note events; it is not a lyric boundary.

The manifest binds every input by SHA256, states the clock origin and the
model hashes, so a later run can prove it used the same bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import difflib
import hashlib
import json
from pathlib import Path
from typing import Sequence

from .lyrics import Syllable

SCHEMA_VERSION = 1


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class Observation:
    """One observed character with a time window and a match level."""

    text: str
    start: float
    end: float
    source: str
    detail: str = ""
    method: str = "sequence"
    """How the observation was tied to its syllable: ``sequence`` (text
    alignment), ``residual`` (second pass on the leftovers), ``positional``
    (same index) or ``token`` (the source provided the token id itself)."""

    level: str = "exact_text"
    """``exact_token`` | ``exact_text`` | ``residual_text`` | ``positional`` |
    ``missing``.  Only the exact levels may be trusted like a ground truth."""

    match_span: tuple[int, int] | None = None
    """Range in the observation sequence that was matched."""

    same_line: bool | None = None
    """Whether the observation provably belongs to the same lyric line."""

    def as_dict(self) -> dict:
        return asdict(self)


#: How much a match level may pull the mapping.  Weak evidence must never
#: push a syllable far away from where the singer actually put it.
LEVEL_WEIGHTS = {
    "exact_token": 1.0,
    "exact_text": 1.0,
    "residual_text": 0.35,
    "positional": 0.25,
    "missing": 0.0,
}

#: A weak observation that would move a syllable further than this is not
#: allowed to drive the assignment at all.
WEAK_MAX_DISPLACEMENT_S = 0.5


def load_asr_observations(path: str | Path) -> list[Observation]:
    """Read an ASR observation into per-character windows."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: list[Observation] = []
    for seg in doc.get("segments", []):
        for ch in seg.get("chars", []):
            out.append(Observation(
                text=str(ch.get("char", "")),
                start=float(ch["start"]),
                end=float(ch["end"]),
                source="asr",
                detail=f"seg@{seg.get('start')}",
            ))
    return out


def load_hfa_observations(path: str | Path) -> list[Observation]:
    """Read HFA observations into per-syllable windows.

    Three shapes are supported:

    * ``hfa_summary.json`` - ``{"phrases": [{"words": [{"mark", "start_s",
      "end_s", "hanzi"}]}]}`` (nianlun, lastpage);
    * ``observations.json`` - the normalized form written by the song
      scripts: ``{"observations": [{"text", "start", "end", ...}]}``;
    * ``HFA.json`` - ``{"words": [{"token", "start", "end"}]}`` (yuai); the
      text is not carried here, so the caller must join it by token.
    """
    path = Path(path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: list[Observation] = []
    if isinstance(doc, dict) and "phrases" in doc:
        for phrase in doc.get("phrases", []):
            for word in phrase.get("words", []):
                mark = str(word.get("mark", ""))
                if mark in ("SP", "AP", "EP", "sil", ""):
                    continue
                hanzi = str(word.get("hanzi", ""))
                if not hanzi:
                    continue
                out.append(Observation(
                    text=hanzi,
                    start=float(word["start_s"]),
                    end=float(word["end_s"]),
                    source="hfa",
                    detail=f"{phrase.get('phrase_id')}:{mark}",
                ))
        return out
    if isinstance(doc, dict) and "observations" in doc:
        for row in doc.get("observations", []):
            out.append(Observation(
                text=str(row.get("text", "")),
                start=float(row["start"]),
                end=float(row["end"]),
                source=str(row.get("source", "hfa")),
                detail=str(row.get("detail", "")),
                method=str(row.get("method", "sequence")),
            ))
        return out
    if isinstance(doc, dict) and "words" in doc:
        for word in doc.get("words", []):
            out.append(Observation(
                text="",
                start=float(word["start"]),
                end=float(word["end"]),
                source="hfa",
                detail=str(word.get("token", "")),
            ))
        return out
    raise ValueError(f"Unsupported HFA observation shape: {path}")


def match_observations(
    observations: Sequence[Observation],
    syllables: Sequence[Syllable],
    *,
    allow_positional_fallback: bool = True,
) -> tuple[dict[str, Observation], list[dict]]:
    """Match observed characters onto locked syllables by sequence alignment.

    Returns (syllable_id -> observation, report).  Every match carries a
    level:

    * ``exact_token`` - the source provided the token and the text is equal,
    * ``exact_text``  - the text alignment matched,
    * ``residual_text`` - matched in a second pass over the leftovers,
    * ``positional``  - paired by index, text may differ (weak),
    * ``missing``     - no observation at all.

    A syllable without a match simply has no observation; it is never given a
    guessed time.  When the observation count equals the syllable count, the
    remaining syllables are paired with the remaining observations *in order* -
    an absolute index would drift as soon as one pair was consumed by the
    sequence matcher.  Such pairs stay weak and are reported as such.
    """
    obs_text = [o.text for o in observations]
    syl_text = [s.text for s in syllables]
    matcher = difflib.SequenceMatcher(a=obs_text, b=syl_text, autojunk=False)
    matched: dict[str, Observation] = {}
    report: list[dict] = []
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            observation = observations[block.a + k]
            syllable = syllables[block.b + k]
            level = "exact_token" if observation.method == "token" else "exact_text"
            matched[syllable.syllable_id] = Observation(
                text=observation.text,
                start=observation.start,
                end=observation.end,
                source=observation.source,
                detail=observation.detail,
                method=observation.method,
                level=level,
                match_span=(block.a + k, block.a + k),
                same_line=observation.same_line,
            )
    used = {id(o) for o in observations if any(
        o.text == m.text and o.start == m.start and o.end == m.end for m in matched.values())}
    for syllable in syllables:
        if syllable.syllable_id not in matched:
            report.append({
                "kind": "observation_missing",
                "level": "missing",
                "syllable_id": syllable.syllable_id,
                "text": syllable.text,
                "line_index": syllable.line_index,
            })
    unmatched_syllables = [s for s in syllables if s.syllable_id not in matched]
    unused_observations = [o for o in observations if id(o) not in used]
    if allow_positional_fallback and unmatched_syllables and unused_observations:
        # The remaining syllables are paired with the remaining observations
        # *in order* - an absolute index would drift as soon as one pair was
        # consumed by the sequence matcher.
        if len(unmatched_syllables) == len(unused_observations):
            for syllable, observation in zip(unmatched_syllables, unused_observations):
                matched[syllable.syllable_id] = Observation(
                    text=observation.text,
                    start=observation.start,
                    end=observation.end,
                    source=observation.source,
                    detail=observation.detail,
                    method="positional",
                    level="positional",
                    match_span=None,
                    same_line=observation.same_line,
                )
                used.add(id(observation))
                report.append({
                    "kind": "observation_positional_fallback",
                    "level": "positional",
                    "syllable_id": syllable.syllable_id,
                    "text": syllable.text,
                    "observed_text": observation.text,
                })
        else:
            second = difflib.SequenceMatcher(
                a=[o.text for o in unused_observations],
                b=[s.text for s in unmatched_syllables], autojunk=False)
            for block in second.get_matching_blocks():
                for k in range(block.size):
                    observation = unused_observations[block.a + k]
                    syllable = unmatched_syllables[block.b + k]
                    matched[syllable.syllable_id] = Observation(
                        text=observation.text,
                        start=observation.start,
                        end=observation.end,
                        source=observation.source,
                        detail=observation.detail,
                        method="residual",
                        level="residual_text",
                        match_span=(block.a + k, block.a + k),
                        same_line=observation.same_line,
                    )
                    used.add(id(observation))
                    report.append({
                        "kind": "observation_residual_match",
                        "level": "residual_text",
                        "syllable_id": syllable.syllable_id,
                        "text": syllable.text,
                        "observed_text": observation.text,
                    })
    for observation in observations:
        if id(observation) not in used:
            report.append({
                "kind": "observation_unused",
                "level": "missing",
                "text": observation.text,
                "start_s": round(observation.start, 4),
                "source": observation.source,
            })
    return matched, report


def build_observations_manifest(
    *,
    song_id: str,
    run_id: str,
    created_at: str,
    clock: dict,
    inputs: dict,
    models: dict,
    environment: dict,
    extra: dict | None = None,
) -> dict:
    """Build the P0 observations manifest."""
    doc = {
        "schema_version": SCHEMA_VERSION,
        "song_id": song_id,
        "run_id": run_id,
        "created_at": created_at,
        "clock": clock,
        "inputs": inputs,
        "models": models,
        "environment": environment,
    }
    if extra:
        doc.update(extra)
    return doc


def file_entry(path: str | Path, *, role: str, sha256: str | None = None) -> dict:
    """One input binding: path, role and content hash."""
    p = Path(path)
    return {
        "path": str(p),
        "role": role,
        "exists": p.is_file(),
        "sha256": sha256 or (sha256_file(p) if p.is_file() else None),
        "bytes": p.stat().st_size if p.is_file() else None,
    }
