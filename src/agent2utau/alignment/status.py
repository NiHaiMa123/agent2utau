"""Machine-readable result states for the alignment pipeline.

Three states, deliberately distinct:

``valid``
    Every hard constraint passes, no syllable is unresolved, every mapped note
    exists in the built project one-to-one.
``incomplete``
    Nothing illegal happened, but something still needs a human: unresolved
    syllables, notes that cannot be represented legally, windows without a
    usable candidate.  Diagnostic artifacts may be produced, but the result
    must never be presented as a finished baseline.
``invalid``
    A semantic error: illegal note clock, illegal extender, mapping that
    breaks a hard constraint, or a native read-back that disagrees.  The
    result must block any further use.

The CLI exit code mirrors the state: valid -> 0, invalid -> 2,
incomplete -> 3 (unless the caller explicitly asks for diagnostics only).
"""

from __future__ import annotations

STATUS_VALID = "valid"
STATUS_INCOMPLETE = "incomplete"
STATUS_INVALID = "invalid"

EXIT_VALID = 0
EXIT_INVALID = 2
EXIT_INCOMPLETE = 3

EXIT_CODES = {
    STATUS_VALID: EXIT_VALID,
    STATUS_INCOMPLETE: EXIT_INCOMPLETE,
    STATUS_INVALID: EXIT_INVALID,
}


def classify(
    *,
    hard_problems: Sequence[str],
    unresolved_syllables: Sequence[str] = (),
    unresolved_note_ids: Sequence[str] = (),
    review_required: Sequence[str] = (),
    diagnostic_only: bool = False,
) -> str:
    """Classify a run into valid / incomplete / invalid."""
    if hard_problems:
        return STATUS_INVALID
    if unresolved_syllables or unresolved_note_ids or review_required:
        return STATUS_INCOMPLETE
    if diagnostic_only:
        return STATUS_INCOMPLETE
    return STATUS_VALID


def exit_code(status: str, *, allow_incomplete: bool = False) -> int:
    """Process exit code for a status.

    ``invalid`` always fails.  ``incomplete`` fails as well unless the caller
    explicitly asked for diagnostics only - a diagnostic run must never look
    like a successful production run.
    """
    if status == STATUS_INVALID:
        return EXIT_INVALID
    if status == STATUS_INCOMPLETE:
        return EXIT_VALID if allow_incomplete else EXIT_INCOMPLETE
    return EXIT_VALID
