"""The local gate: real context, fail-closed verification, shared pending list.

P1.2.1-A  the context of a segment is the real neighbouring syllable
P1.2.1-B  a missing / incomplete / duplicated verification record blocks
P1.2.1-C  the pending decisions come from one explicit list and fail closed
P1.2.1-D  a USTX verification failure feeds back into the song status
"""

from agent2utau.alignment.gate import BLOCKED, RELEASED, evaluate_segment, summarize_gate
from agent2utau.alignment.pending import (
    KIND_NOTE,
    KIND_SYLLABLE,
    STATUS_PENDING,
    PendingDecision,
    PendingDecisionError,
    load_pending_decisions,
)


def rows(*items):
    return {row["syllable_id"]: row for row in items}


def row(syllable_id, text, status="mapped", note_ids=None, line_index=0, review=False):
    return {
        "syllable_id": syllable_id,
        "text": text,
        "status": status,
        "note_ids": note_ids or [],
        "line_index": line_index,
        "review_required": review,
    }


def verification(note_id, *, present=True, start=0, duration=480, tone=60, lyric="年",
                 expected_start=None, actual_start=None, expected_duration=None,
                 expected_tone=None, expected_lyric=None, **extra):
    record = {
        "note_id": note_id,
        "present": present,
        "expected_start_tick": start if expected_start is None else expected_start,
        "actual_start_tick": start if actual_start is None else actual_start,
        "expected_duration_tick": duration if expected_duration is None else expected_duration,
        "actual_duration_tick": duration,
        "expected_tone": tone if expected_tone is None else expected_tone,
        "actual_tone": tone,
        "expected_lyric": lyric if expected_lyric is None else expected_lyric,
        "actual_lyric": lyric,
        "part_index": 0,
        "note_index": 0,
    }
    record.update(extra)
    return record


def note_index(*items):
    return {n["note_id"]: n for n in items}


def call(**overrides):
    """A clean segment: two syllables, one neighbour, complete verification."""
    arguments = {
        "segment_id": "demo-normal",
        "song_id": "demo",
        "scenario": "one_char_one_note",
        "target_syllable_ids": ["s0002", "s0003"],
        "text": "年轮",
        "ordered_syllable_ids": ["s0001", "s0002", "s0003", "s0004"],
        "mapping_rows": rows(
            row("s0001", "上", note_ids=["n0001"]),
            row("s0002", "年", note_ids=["n0002"]),
            row("s0003", "轮", note_ids=["n0003"]),
            row("s0004", "下", note_ids=["n0004"]),
        ),
        "unassigned_notes": [],
        "verification_notes": [verification("n0001"), verification("n0002"),
                               verification("n0003"), verification("n0004")],
        "verification_global": {"one_to_one": True},
        "note_index": note_index(
            {"note_id": "n0001", "start": 0.0, "end": 0.5},
            {"note_id": "n0002", "start": 0.5, "end": 1.0},
            {"note_id": "n0003", "start": 1.0, "end": 1.5},
            {"note_id": "n0004", "start": 1.5, "end": 2.0},
        ),
        "pending_decisions": [],
        "pending_sha256": "a" * 64,
        "start_s": 0.5,
        "end_s": 1.5,
    }
    arguments.update(overrides)
    return evaluate_segment(**arguments)


# --- A: the context is the real neighbour -------------------------------------

def test_the_context_is_the_real_neighbour_not_the_segment_edge():
    segment = call()
    assert segment["target_syllable_ids"] == ["s0002", "s0003"]
    assert segment["context_syllable_ids"] == ["s0001", "s0004"]
    assert segment["context_detail"]["left"] == "s0001"
    assert segment["context_detail"]["right"] == "s0004"
    assert segment["local_gate"] == RELEASED


def test_a_resolved_neighbour_does_not_block():
    segment = call()
    assert not any(b["code"].startswith("context_") for b in segment["blockers"])


def test_an_unresolved_neighbour_blocks_the_segment():
    mapping = rows(
        row("s0001", "上", note_ids=["n0001"]),
        row("s0002", "年", note_ids=["n0002"]),
        row("s0003", "轮", note_ids=["n0003"]),
        row("s0004", "下", note_ids=["n0004"]),
    )
    mapping["s0001"]["status"] = "unresolved"
    mapping["s0001"]["note_ids"] = []
    segment = call(mapping_rows=mapping,
                   verification_notes=[verification("n0002"), verification("n0003")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "context_unresolved_syllable" and b["syllable_id"] == "s0001"
               for b in segment["blockers"])


def test_a_neighbour_under_review_blocks_the_segment():
    mapping = rows(
        row("s0001", "上", note_ids=["n0001"], review=True),
        row("s0002", "年", note_ids=["n0002"]),
        row("s0003", "轮", note_ids=["n0003"]),
        row("s0004", "下", note_ids=["n0004"]),
    )
    segment = call(mapping_rows=mapping,
                   verification_notes=[verification("n0002"), verification("n0003")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "context_review_required_syllable" for b in segment["blockers"])


def test_a_song_boundary_has_no_neighbour_on_that_side():
    segment = call(
        target_syllable_ids=["s0001", "s0002"],
        ordered_syllable_ids=["s0001", "s0002", "s0003", "s0004"],
        verification_notes=[verification("n0001"), verification("n0002"),
                            verification("n0003")],
    )
    assert segment["context_detail"]["left"] is None
    assert segment["context_syllable_ids"] == ["s0003"]
    assert segment["context_detail"]["at_song_boundary"] is True
    assert segment["local_gate"] == RELEASED


# --- B: the verification must be complete --------------------------------------

def test_no_verification_records_block():
    segment = call(verification_notes=[])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_missing" for b in segment["blockers"])
    assert segment["verification_complete"] is False


def test_a_missing_note_blocks():
    segment = call(verification_notes=[verification("n0002")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_missing" and b["note_id"] == "n0003"
               for b in segment["blockers"])


def test_present_false_blocks():
    segment = call(verification_notes=[
        verification("n0002", present=False), verification("n0003")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_note_absent" for b in segment["blockers"])


def test_a_record_without_the_required_fields_blocks():
    incomplete = verification("n0002")
    del incomplete["actual_tone"]
    segment = call(verification_notes=[incomplete, verification("n0003")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_incomplete_record" for b in segment["blockers"])


def test_two_records_for_one_note_block():
    segment = call(verification_notes=[
        verification("n0002"), verification("n0002"), verification("n0003")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_duplicate" for b in segment["blockers"])


def test_a_wrong_lyric_blocks():
    segment = call(verification_notes=[
        verification("n0002", actual_lyric="错"), verification("n0003")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_lyric_mismatch" for b in segment["blockers"])


def test_a_global_one_to_one_failure_blocks():
    segment = call(verification_global={"one_to_one": False})
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_failed" for b in segment["blockers"])


def test_a_tick_mismatch_blocks():
    segment = call(verification_notes=[
        verification("n0002", expected_start=0, actual_start=480),
        verification("n0003")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_start_mismatch" for b in segment["blockers"])


def test_a_complete_legal_segment_is_still_released():
    segment = call()
    assert segment["local_gate"] == RELEASED
    assert segment["verification_complete"] is True
    assert segment["release_evidence"]["verified_note_count"] == 4


# --- C: one shared pending list ------------------------------------------------

def pending_note(note_id, song_id="demo"):
    return PendingDecision(decision_id=f"{song_id}:{note_id}", song_id=song_id,
                           kind=KIND_NOTE, target_id=note_id, status=STATUS_PENDING,
                           reason="open")


def pending_syllable(syllable_id, song_id="demo"):
    return PendingDecision(decision_id=f"{song_id}:{syllable_id}", song_id=song_id,
                           kind=KIND_SYLLABLE, target_id=syllable_id,
                           status=STATUS_PENDING, reason="open")


def test_a_pending_note_blocks_the_segment():
    segment = call(pending_decisions=[pending_note("n0002")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "pending_note_decision" for b in segment["blockers"])


def test_a_pending_syllable_blocks_the_segment():
    segment = call(pending_decisions=[pending_syllable("s0002")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "pending_syllable_decision" for b in segment["blockers"])


def test_a_pending_syllable_blocks_through_the_context():
    segment = call(pending_decisions=[pending_syllable("s0001")])
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "pending_syllable_decision" for b in segment["blockers"])


def test_a_missing_pending_list_fails_closed():
    segment = call(pending_error="pending decisions file not found", pending_sha256=None)
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "pending_list_unavailable" for b in segment["blockers"])


def test_a_pending_list_without_a_hash_fails_closed():
    segment = call(pending_sha256=None)
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "pending_list_missing_hash" for b in segment["blockers"])


def test_an_explicitly_authorized_empty_list_is_accepted():
    segment = call(pending_decisions=[], pending_sha256="b" * 64)
    assert segment["local_gate"] == RELEASED


def test_the_loader_refuses_a_missing_file(tmp_path):
    with pytest.raises(PendingDecisionError):
        load_pending_decisions(tmp_path / "missing.json")


def test_the_loader_refuses_a_mismatched_frozen_input(tmp_path):
    path = tmp_path / "pending.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "frozen_input_sha256": "a" * 64,
        "decisions": [],
    }), encoding="utf-8")
    with pytest.raises(PendingDecisionError):
        load_pending_decisions(path, require_input_sha256="b" * 64)


def test_the_loader_accepts_an_authorized_empty_list(tmp_path):
    path = tmp_path / "pending.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "frozen_input_sha256": "a" * 64,
        "authorized_by": "user",
        "decided_at": "2026-10-31",
        "decisions": [],
    }), encoding="utf-8")
    decisions, sha = load_pending_decisions(path, require_input_sha256="a" * 64)
    assert decisions == []
    assert len(sha) == 64


def test_the_summary_counts_both_states():
    summary = summarize_gate([
        {"local_gate": RELEASED, "blockers": []},
        {"local_gate": BLOCKED, "blockers": [{"code": "unresolved_syllable"}]},
    ])
    assert summary["segment_count"] == 2
    assert summary["ready_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["blocker_counts"] == {"unresolved_syllable": 1}


import json  # noqa: E402  (used by the loader tests)

import pytest  # noqa: E402
