"""The pending decision list is shared, versioned and fail-closed (P1.2.1-C).

The same file must give the same verdict whether the gate is called from the
session script, from the CLI or directly from library code.
"""

from pathlib import Path

import json
import pytest

from agent2utau.alignment.gate import BLOCKED, RELEASED, evaluate_segment
from agent2utau.alignment.pending import (
    PendingDecisionError,
    decisions_for_song,
    load_pending_decisions,
    pending_note_ids,
    pending_syllable_ids,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PENDING_FILE = REPO_ROOT / "experiments" / "alignment" / "pending_decisions.json"


def mapping(*items):
    return {row["syllable_id"]: row for row in items}


def row(syllable_id, text, note_ids=None, line_index=0, status="mapped", review=False):
    return {
        "syllable_id": syllable_id,
        "text": text,
        "status": status,
        "note_ids": note_ids or [],
        "line_index": line_index,
        "review_required": review,
    }


def verification(note_id, lyric="年"):
    return {
        "note_id": note_id,
        "present": True,
        "expected_start_tick": 0,
        "actual_start_tick": 0,
        "expected_duration_tick": 480,
        "actual_duration_tick": 480,
        "expected_tone": 60,
        "actual_tone": 60,
        "expected_lyric": lyric,
        "actual_lyric": lyric,
        "part_index": 0,
        "note_index": 0,
    }


def gate_for(song_id, target, notes, decisions, pending_sha="a" * 64, **overrides):
    arguments = {
        "segment_id": "demo",
        "song_id": song_id,
        "scenario": "x",
        "target_syllable_ids": target,
        "text": "demo",
        "ordered_syllable_ids": [s for s, _t, _n in notes],
        "mapping_rows": mapping(*[row(s, t, note_ids=n) for s, t, n in notes]),
        "unassigned_notes": [],
        "verification_notes": [verification(n[0]) for _s, _t, n in notes],
        "verification_global": {"one_to_one": True},
        "pending_decisions": decisions,
        "pending_sha256": pending_sha,
        "start_s": 0.0,
        "end_s": 10.0,
    }
    arguments.update(overrides)
    return evaluate_segment(**arguments)


def test_the_committed_list_loads_and_is_versioned():
    decisions, sha = load_pending_decisions(PENDING_FILE, repo_root=REPO_ROOT)
    assert sha and len(sha) == 64
    assert decisions, "the shared list must not be empty"
    assert {d.decision_id for d in decisions} >= {
        "lastpage:n0060", "nianlun:s0059", "nianlun:s0203"}


def test_the_committed_list_names_the_real_ids():
    decisions, _sha = load_pending_decisions(PENDING_FILE, repo_root=REPO_ROOT)
    assert pending_note_ids(decisions) == {"n0060"}
    assert pending_syllable_ids(decisions) == {"s0059", "s0203"}
    lastpage = decisions_for_song(decisions, "lastpage")
    assert [d.decision_id for d in lastpage] == ["lastpage:n0060"]
    for decision in decisions:
        assert decision.reason
        assert decision.source
        assert decision.input_sha256


def test_n0060_blocks_a_segment_that_touches_it():
    decisions, sha = load_pending_decisions(PENDING_FILE, repo_root=REPO_ROOT)
    notes = [("s0049", "声", ["n0059"]), ("s0050", "淹", ["n0060"])]
    segment = gate_for("lastpage", ["s0049", "s0050"], notes,
                       [d for d in decisions if d.song_id == "lastpage"], sha)
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "pending_note_decision" for b in segment["blockers"])


def test_the_pending_lyric_syllables_block_their_segment():
    decisions, sha = load_pending_decisions(PENDING_FILE, repo_root=REPO_ROOT)
    notes = [("s0059", "分", ["n0100"]), ("s0060", "轮", ["n0101"])]
    segment = gate_for("nianlun", ["s0059", "s0060"], notes,
                       [d for d in decisions if d.song_id == "nianlun"], sha)
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "pending_syllable_decision" for b in segment["blockers"])


def test_an_unrelated_segment_is_not_blocked_by_the_list():
    decisions, sha = load_pending_decisions(PENDING_FILE, repo_root=REPO_ROOT)
    notes = [("s0001", "圆", ["n0002"]), ("s0002", "圈", ["n0003"])]
    segment = gate_for("nianlun", ["s0001", "s0002"], notes,
                       [d for d in decisions if d.song_id == "nianlun"], sha)
    assert segment["local_gate"] == RELEASED
    assert segment["pending_decisions_sha256"] == sha


def test_a_missing_list_fails_closed_in_every_entry_point(tmp_path):
    with pytest.raises(PendingDecisionError):
        load_pending_decisions(tmp_path / "nothing.json", repo_root=REPO_ROOT)
    segment = gate_for("nianlun", ["s0001"], [("s0001", "圆", ["n0002"])], [],
                       pending_sha256=None,
                       pending_error="pending decisions file not found")
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "pending_list_unavailable" for b in segment["blockers"])


def test_a_list_written_for_other_inputs_is_refused(tmp_path):
    path = tmp_path / "pending.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "frozen_input_sha256": "a" * 64,
        "decisions": [],
    }), encoding="utf-8")
    with pytest.raises(PendingDecisionError):
        load_pending_decisions(path, require_input_sha256="b" * 64)
