"""The local gate: which short segments may enter the P2 pilot.

P1.2.1 hardens the P1.2 gate:

* the *context* of a segment is the **real neighbouring syllable** in the
  stable lyric order - not the first and last syllable inside the segment;
* a segment is only released when every target note and every context note
  has **exactly one complete** USTX verification record that agrees with the
  ledger (missing, duplicated, incomplete or mismatching records block);
* the pending decisions are passed in explicitly from one versioned file; a
  missing or mismatched list fails closed for production release.

A released segment is *not* a statement about the whole song: the songs stay
``incomplete`` as long as any open item exists.
"""

from __future__ import annotations

from typing import Sequence

from .pending import STATUS_PENDING, PendingDecision

RELEASED = "ready_for_p2_native_baseline"
BLOCKED = "blocked"

#: fields a verification record must carry to be usable
REQUIRED_VERIFICATION_FIELDS = (
    "note_id",
    "present",
    "expected_start_tick",
    "actual_start_tick",
    "expected_duration_tick",
    "actual_duration_tick",
    "expected_tone",
    "actual_tone",
    "expected_lyric",
    "actual_lyric",
)

#: how far the written note may sit from the ledger (the builder is allowed
#: to close a one-tick gap)
ALLOWED_TICK_DEVIATION = 1

#: global items that do not block a segment but must be written down
GLOBAL_PENDING = [
    "the MIDI rounding of the GAME tone (truncate vs round) is still open; the "
    "segment's tick and identity gate hold, but a note's tone may move by one "
    "semitone when the decision is made",
    "the line breaks follow the recording, not the release edition",
]


def _context_of(target: Sequence[str], ordered: Sequence[str]) -> tuple[list[str], dict]:
    """The real neighbours of the target in the stable lyric order."""
    index = {sid: i for i, sid in enumerate(ordered)}
    if not target:
        return [], {}
    positions = [index[s] for s in target if s in index]
    if not positions:
        return [], {}
    first, last = min(positions), max(positions)
    left = ordered[first - 1] if first > 0 else None
    right = ordered[last + 1] if last + 1 < len(ordered) else None
    context = [sid for sid in (left, right) if sid]
    return context, {"left": left, "right": right, "at_song_boundary": left is None or right is None}


def _check_verification(
    required_notes: Sequence[str],
    verification_notes: Sequence[dict],
    verification_global: dict,
) -> tuple[list[dict], bool]:
    """Every required note needs exactly one complete, matching record."""
    blockers: list[dict] = []
    by_id: dict[str, list[dict]] = {}
    for record in verification_notes:
        by_id.setdefault(record.get("note_id"), []).append(record)

    for note_id in required_notes:
        records = by_id.get(note_id, [])
        if not records:
            blockers.append({"code": "verification_missing", "note_id": note_id,
                             "detail": "no USTX verification record for this note"})
            continue
        if len(records) > 1:
            blockers.append({"code": "verification_duplicate", "note_id": note_id,
                             "detail": f"{len(records)} verification records for one note"})
            continue
        record = records[0]
        missing = [f for f in REQUIRED_VERIFICATION_FIELDS if f not in record]
        if missing:
            blockers.append({"code": "verification_incomplete_record", "note_id": note_id,
                             "detail": f"missing fields: {', '.join(missing)}"})
            continue
        if not record.get("present"):
            blockers.append({"code": "verification_note_absent", "note_id": note_id,
                             "detail": "the note is not present in the written USTX"})
            continue
        deviation = record["actual_start_tick"] - record["expected_start_tick"]
        if abs(deviation) > ALLOWED_TICK_DEVIATION:
            blockers.append({"code": "verification_start_mismatch", "note_id": note_id,
                             "deviation_tick": deviation,
                             "detail": "the written note does not sit on the expected tick"})
        if record["actual_duration_tick"] != record["expected_duration_tick"]:
            blockers.append({"code": "verification_duration_mismatch", "note_id": note_id,
                             "detail": "the written duration differs from the ledger"})
        if record["actual_tone"] != record["expected_tone"]:
            blockers.append({"code": "verification_tone_mismatch", "note_id": note_id,
                             "detail": "the written tone differs from the ledger"})
        if record["actual_lyric"] != record["expected_lyric"]:
            blockers.append({"code": "verification_lyric_mismatch", "note_id": note_id,
                             "detail": "the written lyric differs from the ledger"})

    if verification_global and verification_global.get("one_to_one") is False:
        blockers.append({"code": "verification_failed",
                         "detail": "the whole-project verification is not one_to_one"})
    return blockers, not blockers


def evaluate_segment(
    *,
    segment_id: str,
    song_id: str,
    scenario: str,
    target_syllable_ids: Sequence[str],
    text: str,
    ordered_syllable_ids: Sequence[str],
    mapping_rows: dict[str, dict],
    unassigned_notes: Sequence[dict],
    verification_notes: Sequence[dict],
    verification_global: dict | None = None,
    verification_identity: dict | None = None,
    expected_verification_identity: dict | None = None,
    note_index: dict[str, dict] | None = None,
    pending_decisions: Sequence[PendingDecision] = (),
    pending_sha256: str | None = None,
    pending_error: str | None = None,
    production_mode: bool = True,
    start_s: float = 0.0,
    end_s: float = 0.0,
) -> dict:
    """Evaluate one segment and return its gate record."""
    target = list(target_syllable_ids)
    blockers: list[dict] = []
    cautions: list[dict] = []
    note_index = note_index or {}

    # --- pending decisions: explicit, shared, fail-closed -------------------
    if pending_error:
        blockers.append({"code": "pending_list_unavailable", "detail": pending_error})
    if production_mode and pending_sha256 is None and not pending_error:
        blockers.append({"code": "pending_list_missing_hash",
                         "detail": "the pending decision list has no hash; the release cannot "
                                   "be tied to a version"})

    context, context_info = _context_of(target, ordered_syllable_ids)
    target_notes = [nid for sid in target for nid in (mapping_rows.get(sid, {}).get("note_ids") or [])]
    context_notes = [nid for sid in context for nid in (mapping_rows.get(sid, {}).get("note_ids") or [])]

    # --- the target's own state --------------------------------------------
    for sid in target:
        row = mapping_rows.get(sid)
        if row is None:
            blockers.append({"code": "target_syllable_unknown", "syllable_id": sid,
                             "detail": "the segment references a syllable that is not in the mapping"})
            continue
        if row.get("status") == "unresolved":
            blockers.append({"code": "unresolved_syllable", "syllable_id": sid,
                             "text": row.get("text"),
                             "detail": "the syllable has no defensible note assignment"})
        if row.get("review_required"):
            blockers.append({"code": "syllable_review_required", "syllable_id": sid,
                             "text": row.get("text"),
                             "detail": "the syllable or its line is still under review"})

    # --- the real neighbours ------------------------------------------------
    context_status = {}
    for sid in context:
        row = mapping_rows.get(sid, {})
        context_status[sid] = {
            "status": row.get("status"),
            "text": row.get("text"),
            "review_required": bool(row.get("review_required")),
            "note_ids": list(row.get("note_ids") or []),
        }
        if row.get("status") == "unresolved":
            blockers.append({"code": "context_unresolved_syllable", "syllable_id": sid,
                             "text": row.get("text"),
                             "detail": "the neighbouring syllable is unresolved; the segment "
                                       "shares its phoneme context"})
        if row.get("review_required"):
            blockers.append({"code": "context_review_required_syllable", "syllable_id": sid,
                             "text": row.get("text"),
                             "detail": "the neighbouring syllable is still under review"})

    # --- notes without an owner ---------------------------------------------
    for row in unassigned_notes:
        for note_id in target_notes + context_notes:
            if row["note_id"] == note_id:
                blockers.append({"code": "unassigned_voiced_note", "note_id": row["note_id"],
                                 "classification": row.get("classification"),
                                 "detail": row.get("detail", "")})
                break
        else:
            if row["end_s"] >= start_s and row["start_s"] <= end_s:
                blockers.append({"code": "unassigned_voiced_note_in_window",
                                 "note_id": row["note_id"],
                                 "classification": row.get("classification"),
                                 "detail": row.get("detail", "")})

    # --- pending decisions ---------------------------------------------------
    for decision in pending_decisions:
        if decision.status != STATUS_PENDING or decision.song_id != song_id:
            continue
        if decision.matches_note(decision.target_id) and (
                decision.target_id in target_notes or decision.target_id in context_notes):
            blockers.append({"code": "pending_note_decision",
                             "decision_id": decision.decision_id,
                             "note_id": decision.target_id,
                             "detail": decision.reason})
        if decision.matches_syllable(decision.target_id) and (
                decision.target_id in target or decision.target_id in context):
            blockers.append({"code": "pending_syllable_decision",
                             "decision_id": decision.decision_id,
                             "syllable_id": decision.target_id,
                             "detail": decision.reason})
        # a pending note that belongs to no syllable still blocks by its window
        if decision.kind == "note" and decision.target_id not in target_notes \
                and decision.target_id not in context_notes:
            note = note_index.get(decision.target_id)
            if note and note["end"] >= start_s and note["start"] <= end_s:
                blockers.append({"code": "pending_note_in_window",
                                 "decision_id": decision.decision_id,
                                 "note_id": decision.target_id,
                                 "detail": decision.reason})

    # --- the USTX verification must be complete and match -------------------
    required_notes = list(dict.fromkeys(target_notes + context_notes))
    verification_blockers, verification_complete = _check_verification(
        required_notes, verification_notes, verification_global or {})
    blockers += verification_blockers
    if expected_verification_identity and verification_identity:
        for key in ("ustx_sha256", "lyrics_sha256", "notes_sha256"):
            expected = expected_verification_identity.get(key)
            actual = verification_identity.get(key)
            if expected and actual and expected != actual:
                blockers.append({"code": "verification_identity_mismatch", "field": key,
                                 "detail": "the verification was produced for other inputs"})

    # --- cross-line segments -------------------------------------------------
    lines = sorted({mapping_rows[sid]["line_index"] for sid in target
                    if sid in mapping_rows and "line_index" in mapping_rows[sid]})
    if len(lines) > 1:
        cautions.append({"code": "cross_line_segment", "lines": lines,
                         "detail": "the segment crosses a lyric line; the shared context "
                                   "of the two lines must be kept when editing"})

    codes = sorted({b["code"] for b in blockers})
    return {
        "segment_id": segment_id,
        "song_id": song_id,
        "scenario": scenario,
        "target_syllable_ids": target,
        "context_syllable_ids": context,
        "context_detail": {
            "left": context_info.get("left"),
            "right": context_info.get("right"),
            "at_song_boundary": context_info.get("at_song_boundary"),
            "status": context_status,
        },
        "note_ids": target_notes,
        "context_note_ids": context_notes,
        "text": text,
        "start_s": round(start_s, 4),
        "end_s": round(end_s, 4),
        "local_gate": BLOCKED if blockers else RELEASED,
        "blocked_reason": "; ".join(f"{b['code']}"
                                    + (f"({b.get('syllable_id') or b.get('note_id') or b.get('decision_id')})"
                                       if (b.get("syllable_id") or b.get("note_id") or b.get("decision_id"))
                                       else "")
                                    for b in blockers),
        "blocker_codes": codes,
        "blockers": blockers,
        "cautions": cautions,
        "verification_complete": verification_complete,
        "verification_identity": verification_identity or {},
        "pending_decisions_sha256": pending_sha256,
        "global_pending": list(GLOBAL_PENDING),
        "release_evidence": {
            "target_syllable_count": len(target),
            "target_note_count": len(target_notes),
            "context_syllable_count": len(context),
            "context_note_count": len(context_notes),
            "verified_note_count": len(required_notes),
        },
    }


def summarize_gate(segments: Sequence[dict]) -> dict:
    """One page summary of a gate list."""
    blockers = [b for segment in segments for b in segment["blockers"]]
    return {
        "segment_count": len(segments),
        "ready_count": sum(1 for s in segments if s["local_gate"] == RELEASED),
        "blocked_count": sum(1 for s in segments if s["local_gate"] == BLOCKED),
        "blocker_counts": {
            code: sum(1 for b in blockers if b["code"] == code)
            for code in sorted({b["code"] for b in blockers})
        },
    }
