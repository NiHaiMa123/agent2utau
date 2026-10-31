"""The local gate decides per segment, not per song (P1.2-F)."""

from agent2utau.alignment import gate
from agent2utau.alignment.gate import BLOCKED, RELEASED, evaluate_segment, summarize_gate


def mapping_rows(*rows):
    return {row["syllable_id"]: row for row in rows}


def row(syllable_id, text, status="mapped", note_ids=None, line_index=0, review=False):
    return {
        "syllable_id": syllable_id,
        "text": text,
        "status": status,
        "note_ids": note_ids or [],
        "line_index": line_index,
        "review_required": review,
    }


def test_a_clean_segment_is_released():
    rows = mapping_rows(row("s0001", "年", note_ids=["n0001"]),
                        row("s0002", "轮", note_ids=["n0002"]))
    segment = evaluate_segment(
        segment_id="s1", song_id="demo", scenario="one_char_one_note",
        syllable_ids=["s0001", "s0002"], text="年轮",
        mapping_rows=rows, unassigned_notes=[], verification_notes=[],
        note_index={"n0001": {"start": 0.0, "end": 0.5}, "n0002": {"start": 0.5, "end": 1.0}},
        start_s=0.0, end_s=1.0)
    assert segment["local_gate"] == RELEASED
    assert segment["blockers"] == []


def test_an_unresolved_syllable_blocks_the_segment():
    rows = mapping_rows(row("s0001", "年", note_ids=["n0001"]),
                        row("s0002", "轮", status="unresolved"))
    segment = evaluate_segment(
        segment_id="s1", song_id="demo", scenario="x",
        syllable_ids=["s0001", "s0002"], text="年轮",
        mapping_rows=rows, unassigned_notes=[], verification_notes=[],
        note_index={"n0001": {"start": 0.0, "end": 0.5}}, start_s=0.0, end_s=1.0)
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "unresolved_syllable" for b in segment["blockers"])


def test_an_unassigned_voiced_note_in_the_window_blocks_the_segment():
    rows = mapping_rows(row("s0001", "年", note_ids=["n0001"]))
    unassigned = [{"note_id": "n0009", "start_s": 0.4, "end_s": 0.6,
                   "classification": "candidate_melisma", "detail": "x"}]
    segment = evaluate_segment(
        segment_id="s1", song_id="demo", scenario="x",
        syllable_ids=["s0001"], text="年",
        mapping_rows=rows, unassigned_notes=unassigned, verification_notes=[],
        note_index={"n0001": {"start": 0.0, "end": 0.5}}, start_s=0.0, end_s=0.5)
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "unassigned_voiced_note" for b in segment["blockers"])


def test_a_ustx_deviation_blocks_the_segment():
    rows = mapping_rows(row("s0001", "年", note_ids=["n0001"]))
    verification = [{"note_id": "n0001", "expected_tone": 60, "actual_tone": 60,
                     "expected_duration_tick": 480, "actual_duration_tick": 480,
                     "actual_start_tick": 1000, "start_deviation_tick": 480}]
    segment = evaluate_segment(
        segment_id="s1", song_id="demo", scenario="x",
        syllable_ids=["s0001"], text="年",
        mapping_rows=rows, unassigned_notes=[], verification_notes=verification,
        note_index={"n0001": {"start": 0.0, "end": 0.5}}, start_s=0.0, end_s=0.5)
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "ustx_start_deviation" for b in segment["blockers"])


def test_a_pending_decision_blocks_the_segment():
    rows = mapping_rows(row("s0001", "淹", note_ids=["n0001"]))
    segment = evaluate_segment(
        segment_id="s1", song_id="lastpage", scenario="x",
        syllable_ids=["s0001"], text="淹",
        mapping_rows=rows, unassigned_notes=[], verification_notes=[],
        note_index={"n0001": {"start": 0.0, "end": 0.5}}, start_s=0.0, end_s=0.5)
    assert segment["local_gate"] == RELEASED
    gate.PENDING_NOTE_DECISIONS.setdefault("lastpage", {})["n0001"] = "open decision"
    try:
        blocked = evaluate_segment(
            segment_id="s1", song_id="lastpage", scenario="x",
            syllable_ids=["s0001"], text="淹",
            mapping_rows=rows, unassigned_notes=[], verification_notes=[],
            note_index={"n0001": {"start": 0.0, "end": 0.5}}, start_s=0.0, end_s=0.5)
        assert blocked["local_gate"] == BLOCKED
        assert any(b["code"] == "pending_note_decision" for b in blocked["blockers"])
    finally:
        gate.PENDING_NOTE_DECISIONS["lastpage"].pop("n0001", None)


def test_a_segment_across_two_lines_is_released_with_a_caution():
    rows = mapping_rows(row("s0001", "年", note_ids=["n0001"], line_index=0),
                        row("s0002", "轮", note_ids=["n0002"], line_index=1))
    segment = evaluate_segment(
        segment_id="s1", song_id="demo", scenario="x",
        syllable_ids=["s0001", "s0002"], text="年轮",
        mapping_rows=rows, unassigned_notes=[], verification_notes=[],
        note_index={"n0001": {"start": 0.0, "end": 0.5}, "n0002": {"start": 0.5, "end": 1.0}},
        start_s=0.0, end_s=1.0)
    assert segment["local_gate"] == RELEASED
    assert segment["cautions"]
    assert segment["global_pending"]


def test_the_summary_counts_both_states():
    summary = summarize_gate([
        {"local_gate": RELEASED, "blockers": []},
        {"local_gate": BLOCKED, "blockers": [{"code": "unresolved_syllable"}]},
    ])
    assert summary["segment_count"] == 2
    assert summary["ready_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["blocker_counts"] == {"unresolved_syllable": 1}
