"""Hard constraints for the alignment artifacts.

The validator is the gate the pipeline must pass before any Agent decision or
native write-back is allowed.  It never repairs anything: it reports problems
so a wrong mapping fails loudly instead of being counted as a success.
"""

from __future__ import annotations

from typing import Sequence

from .lyrics import Syllable
from .notes import NoteEvent

SCHEMA_VERSION = 1


def validate_locked_lyrics(doc: dict) -> list[str]:
    """Check a locked-lyric document (ids, order, occurrence counters)."""
    problems: list[str] = []
    syllables = doc.get("syllables")
    if not isinstance(syllables, list) or not syllables:
        return ["locked lyrics: no syllables"]
    if doc.get("syllable_count") != len(syllables):
        problems.append("locked lyrics: syllable_count does not match the syllable list")
    seen_ids: set[str] = set()
    counts: dict[str, int] = {}
    for index, row in enumerate(syllables):
        sid = row.get("syllable_id")
        if sid != f"s{index + 1:04d}":
            problems.append(f"locked lyrics: syllable {index} has id {sid!r}, expected s{index + 1:04d}")
        if sid in seen_ids:
            problems.append(f"locked lyrics: duplicate syllable id {sid}")
        seen_ids.add(sid)
        text = row.get("text")
        counts[text] = counts.get(text, 0) + 1
        if row.get("occurrence") != counts[text]:
            problems.append(f"locked lyrics: {sid} occurrence {row.get('occurrence')} != {counts[text]}")
    for row in syllables:
        total = counts.get(row.get("text"), 0)
        if bool(row.get("repeated")) != (total > 1):
            problems.append(f"locked lyrics: {row.get('syllable_id')} repeated flag disagrees with the text count")
    return problems


def validate_mapping(
    mapping: dict,
    syllables: Sequence[Syllable],
    notes: Sequence[NoteEvent],
) -> list[str]:
    """Check the mapping against every hard constraint of plan.md P1."""
    problems: list[str] = []
    by_id = {n.note_id: n for n in notes}
    order = {n.note_id: n.index for n in notes}
    rows = mapping.get("mapping") or []
    if len(rows) != len(syllables):
        problems.append(f"mapping: {len(rows)} rows for {len(syllables)} syllables")

    expected_ids = [s.syllable_id for s in syllables]
    seen: list[str] = []
    used_notes: dict[str, str] = {}
    last_note_index = -1
    for row in rows:
        sid = row.get("syllable_id")
        seen.append(sid)
        status = row.get("status")
        note_ids = row.get("note_ids") or []
        if status == "mapped":
            if not note_ids:
                problems.append(f"mapping: {sid} is mapped without notes")
                continue
            if row.get("reason_code") is None:
                problems.append(f"mapping: {sid} has no reason_code")
            indices = []
            for note_id in note_ids:
                if note_id not in by_id:
                    problems.append(f"mapping: {sid} references unknown note {note_id}")
                    continue
                if by_id[note_id].rest:
                    problems.append(f"mapping: {sid} takes rest note {note_id}")
                if note_id in used_notes:
                    problems.append(f"mapping: note {note_id} is used by {used_notes[note_id]} and {sid}")
                used_notes[note_id] = sid
                indices.append(order[note_id])
            if indices and indices != list(range(indices[0], indices[0] + len(indices))):
                problems.append(f"mapping: {sid} owns non-consecutive notes {note_ids}")
            if indices and indices[0] <= last_note_index:
                problems.append(f"mapping: {sid} is not monotone in the note order")
            if indices:
                last_note_index = indices[-1]
            for note_id in note_ids:
                if by_id[note_id].duration_tick <= 0:
                    problems.append(f"mapping: {sid} owns note {note_id} with a non-positive duration")
        elif status == "unresolved":
            if note_ids:
                problems.append(f"mapping: {sid} is unresolved but owns notes")
            if not row.get("reason_code"):
                problems.append(f"mapping: {sid} is unresolved without a reason_code")
        else:
            problems.append(f"mapping: {sid} has unknown status {status!r}")

    if seen != expected_ids:
        missing = [s for s in expected_ids if s not in seen]
        extra = [s for s in seen if s not in expected_ids]
        if missing:
            problems.append(f"mapping: {len(missing)} syllables have no row ({missing[:5]})")
        if extra:
            problems.append(f"mapping: {len(extra)} rows use unknown syllable ids ({extra[:5]})")

    coverage = mapping.get("coverage") or {}
    mapped = sum(1 for row in rows if row.get("status") == "mapped")
    unresolved = sum(1 for row in rows if row.get("status") == "unresolved")
    if coverage.get("syllable_total") != len(syllables):
        problems.append("mapping: coverage.syllable_total disagrees with the syllable list")
    if coverage.get("syllable_mapped") != mapped:
        problems.append("mapping: coverage.syllable_mapped disagrees with the rows")
    if coverage.get("syllable_unresolved") != unresolved:
        problems.append("mapping: coverage.syllable_unresolved disagrees with the rows")
    if coverage.get("syllable_mapped", 0) + coverage.get("syllable_unresolved", 0) != len(syllables):
        problems.append("mapping: mapped and unresolved syllables do not add up to the total")

    unresolved_ids = {row.get("syllable_id") for row in mapping.get("unresolved") or []}
    if unresolved_ids != {row.get("syllable_id") for row in rows if row.get("status") == "unresolved"}:
        problems.append("mapping: the unresolved list does not match the unresolved rows")

    seen_candidates: set[str] = set()
    for candidate in mapping.get("candidates") or []:
        cid = candidate.get("candidate_id")
        if cid in seen_candidates:
            problems.append(f"mapping: duplicate candidate_id {cid}")
        seen_candidates.add(cid)
        for sid, note_ids in (candidate.get("assignment") or {}).items():
            if sid not in set(expected_ids):
                problems.append(f"mapping: candidate {cid} uses unknown syllable {sid}")
            for note_id in note_ids:
                if note_id not in by_id:
                    problems.append(f"mapping: candidate {cid} uses unknown note {note_id}")
    return problems


def validate_ustx_rows(rows: Sequence[dict]) -> list[str]:
    """Check the USTX note rows derived from a mapping.

    ``+`` blocks must touch the note they continue, and no two notes may
    overlap - both are hard errors in the USTX builder.
    """
    problems: list[str] = []
    ordered = sorted(rows, key=lambda r: r["start"])
    for left, right in zip(ordered, ordered[1:]):
        if right["lyric"] == "+" and right["start"] > left["end"] + 1e-6:
            problems.append(f"ustx: extender {right['note_id']} does not touch {left['note_id']}")
        if right["start"] < left["end"] - 1e-6:
            problems.append(f"ustx: {left['note_id']} and {right['note_id']} overlap")
    for row in ordered:
        if row["end"] - row["start"] <= 0:
            problems.append(f"ustx: {row['note_id']} has a non-positive duration")
    return problems
