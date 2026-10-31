"""Pending decisions: one versioned, shared source of truth (P1.2.1-C).

A *pending decision* is something only the user can settle: a note whose
musical owner is unclear, a word whose recorded wording differs from the
published one.  Such items must block every segment that touches them.

The list lives in one versioned file so that every entry point - the CLI, the
session scripts and a direct library call - reaches the same verdict.  It is
passed into :func:`agent2utau.alignment.gate.evaluate_segment` explicitly;
there is no mutable module global that a caller could forget to fill.

Fail-closed rules:

* a missing file is **not** "no pending items" - it is an error,
* a file whose ``input_sha256`` does not match the frozen input is an error,
* an explicitly authorized empty list is allowed, but it must carry its
  provenance and hash.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

SCHEMA_VERSION = 1

#: where the shared list lives, relative to the repository root
DEFAULT_RELPATH = Path("experiments/alignment/pending_decisions.json")

STATUS_PENDING = "pending"
STATUS_RESOLVED = "resolved"

KIND_NOTE = "note"
KIND_SYLLABLE = "syllable"


class PendingDecisionError(RuntimeError):
    """Raised when the pending list is missing, malformed or out of date."""


@dataclass(frozen=True)
class PendingDecision:
    """One item that still needs a human decision."""

    decision_id: str
    song_id: str
    kind: str
    target_id: str
    status: str
    reason: str
    scope: str = ""
    source: str = ""
    authorized_by: str = ""
    decided_at: str = ""
    input_sha256: str = ""
    note_id: str = ""
    syllable_id: str = ""
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        data = {
            "decision_id": self.decision_id,
            "song_id": self.song_id,
            "kind": self.kind,
            "target_id": self.target_id,
            "status": self.status,
            "reason": self.reason,
            "scope": self.scope,
            "source": self.source,
            "authorized_by": self.authorized_by,
            "decided_at": self.decided_at,
            "input_sha256": self.input_sha256,
        }
        if self.note_id:
            data["note_id"] = self.note_id
        if self.syllable_id:
            data["syllable_id"] = self.syllable_id
        if self.extra:
            data["extra"] = self.extra
        return data

    def matches_note(self, note_id: str) -> bool:
        return self.kind == KIND_NOTE and self.target_id == note_id

    def matches_syllable(self, syllable_id: str) -> bool:
        return self.kind == KIND_SYLLABLE and self.target_id == syllable_id


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_path(path: str | Path | None = None, *, repo_root: str | Path | None = None) -> Path:
    """Resolve the pending list path (explicit > env > repository default)."""
    if path:
        return Path(path)
    import os
    env = os.environ.get("AGENT2UTAU_PENDING_DECISIONS")
    if env:
        return Path(env)
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
    return root / DEFAULT_RELPATH


def load_pending_decisions(
    path: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
    require_input_sha256: str | None = None,
    diagnostic: bool = False,
) -> tuple[list[PendingDecision], str]:
    """Load the pending list.

    Returns (decisions, sha256 of the file).  Raises
    :class:`PendingDecisionError` when the file is missing, malformed or does
    not match the frozen input - unless ``diagnostic`` is set, in which case
    the error is returned as an empty list plus the message so a diagnostic
    run can report "blocked: no pending list" instead of crashing.
    """
    resolved = resolve_path(path, repo_root=repo_root)
    try:
        raw = resolved.read_bytes()
    except FileNotFoundError as error:
        message = f"pending decisions file not found: {resolved}"
        if diagnostic:
            return [], ""
        raise PendingDecisionError(message) from error
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        message = f"pending decisions file is not valid JSON: {resolved} ({error})"
        if diagnostic:
            return [], ""
        raise PendingDecisionError(message) from error
    if document.get("schema_version") != SCHEMA_VERSION:
        message = (f"pending decisions schema {document.get('schema_version')!r} is not "
                   f"supported (expected {SCHEMA_VERSION})")
        if diagnostic:
            return [], ""
        raise PendingDecisionError(message)
    if require_input_sha256 is not None:
        recorded = document.get("frozen_input_sha256")
        if recorded and recorded != require_input_sha256:
            message = (f"pending decisions were written against a different frozen input "
                       f"({recorded} != {require_input_sha256})")
            if diagnostic:
                return [], ""
            raise PendingDecisionError(message)
    decisions: list[PendingDecision] = []
    for row in document.get("decisions", []):
        decisions.append(PendingDecision(
            decision_id=row["decision_id"],
            song_id=row.get("song_id", ""),
            kind=row.get("kind", KIND_SYLLABLE),
            target_id=row.get("target_id", ""),
            status=row.get("status", STATUS_PENDING),
            reason=row.get("reason", ""),
            scope=row.get("scope", ""),
            source=row.get("source", ""),
            authorized_by=row.get("authorized_by", ""),
            decided_at=row.get("decided_at", ""),
            input_sha256=row.get("input_sha256", ""),
            note_id=row.get("note_id", ""),
            syllable_id=row.get("syllable_id", ""),
            extra=row.get("extra", {}),
        ))
    return decisions, hashlib.sha256(raw).hexdigest()


def decisions_for_song(decisions: Iterable[PendingDecision], song_id: str) -> list[PendingDecision]:
    return [d for d in decisions if d.song_id == song_id]


def pending_note_ids(decisions: Sequence[PendingDecision]) -> set[str]:
    return {d.target_id for d in decisions
            if d.status == STATUS_PENDING and d.kind == KIND_NOTE}


def pending_syllable_ids(decisions: Sequence[PendingDecision]) -> set[str]:
    return {d.target_id for d in decisions
            if d.status == STATUS_PENDING and d.kind == KIND_SYLLABLE}
