"""The baseline must not drop an illegal extender silently (P1.1-B, P1.2-B/D).

Since P1.2 the illegal extender is refused one level earlier: the mapping
itself may not give a syllable a note that is separated by a real gap, so the
note ends up as an *unassigned voiced note* with a documented destination
(P1.2-D).  The baseline keeps its own safety net for mappings that were
built elsewhere.
"""

from pathlib import Path

from agent2utau.alignment import MappingConfig, build_evidence, map_syllables_to_notes
from agent2utau.alignment.baseline import (
    MAX_EXTENDER_GAP_TICKS,
    build_baseline_ustx,
    rows_to_segments,
    verify_ustx_notes,
)
from agent2utau.alignment.candidates import mapping_to_ustx_rows
from agent2utau.alignment.lyrics import parse_locked_lyrics
from agent2utau.alignment.notes import normalize_notes
from agent2utau.alignment.unassigned import (
    find_unassigned_voiced_notes,
    unassigned_candidates,
)


def raw(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def build_rows(lines, notes, anchors=None):
    syllables = parse_locked_lyrics(lines)
    events = normalize_notes(notes)
    observations = {}
    if anchors:
        from agent2utau.alignment import Observation
        for index, (text, start, end) in enumerate(anchors):
            observations[f"s{index + 1:04d}"] = Observation(text, start, end, "hfa")
    evidence = build_evidence(syllables, observations)
    mapping = map_syllables_to_notes(syllables, events, evidence,
                                     MappingConfig(), song_id="test")
    return syllables, events, mapping, mapping_to_ustx_rows(mapping, events)


def test_a_gapped_note_cannot_be_given_to_a_syllable():
    """The gap makes the assignment illegal, so the note stays unassigned."""
    syllables, events, mapping, rows = build_rows(
        ["声"], [raw(0.0, 0.63), raw(0.79, 0.19)], anchors=[("声", 0.0, 0.63)])
    row = mapping["mapping"][0]
    assert row["note_ids"] == ["n0001"], "the gapped note must not be assigned"
    owner = {nid: r["syllable_id"] for r in mapping["mapping"]
             for nid in r["note_ids"]}
    unassigned = find_unassigned_voiced_notes(events, owner, syllables, [])
    assert [r["note_id"] for r in unassigned] == ["n0002"]
    assert unassigned[0]["classification"] in ("candidate_melisma", "needs_alignment",
                                               "probable_false_positive")


def test_an_unassigned_note_gets_limited_candidates():
    syllables, events, mapping, rows = build_rows(
        ["声"], [raw(0.0, 0.63), raw(0.79, 0.19)], anchors=[("声", 0.0, 0.63)])
    owner = {nid: r["syllable_id"] for r in mapping["mapping"]
             for nid in r["note_ids"]}
    unassigned = find_unassigned_voiced_notes(events, owner, syllables, [])
    previous = events[0]
    options = {c["option"]: c for c in unassigned_candidates(unassigned[0], previous)}
    assert "merge_into_syllable" in options
    assert options["merge_into_syllable"]["requires_authorization"] is True
    assert options["repeat_character"]["status"] == "forbidden_without_human"


def test_the_baseline_safety_net_still_reports_an_illegal_extend():
    """A mapping that contains one must not lose it quietly."""
    rows = [{
        "note_id": "n0001", "syllable_id": "s0001", "syllable_text": "声",
        "lyric": "声", "start": 0.0, "end": 0.63, "dur": 0.63, "tone": 60.0,
        "line_index": 0, "is_sustain": False,
    }, {
        "note_id": "n0002", "syllable_id": "s0001", "syllable_text": "声",
        "lyric": "+", "start": 0.79, "end": 0.98, "dur": 0.19, "tone": 60.0,
        "line_index": 0, "is_sustain": True,
    }]
    segments, unresolved, candidates = rows_to_segments(rows)
    assert len(unresolved) == 1
    assert unresolved[0]["reason_code"] == "extender_not_touching"
    assert unresolved[0]["gap_tick"] > MAX_EXTENDER_GAP_TICKS
    options = {c["option"]: c for c in candidates}
    assert set(options) == {"close_gap", "merge_into_character",
                             "split_new_part", "repeat_character"}
    assert options["split_new_part"]["status"] == "illegal_by_core"
    assert options["repeat_character"]["status"] == "forbidden_without_human"


def test_a_touching_extender_is_written_to_the_project():
    rows, _ = build_rows(["声"], [raw(0.0, 0.63), raw(0.63, 0.19)])[3], None
    segments, unresolved, _ = rows_to_segments(rows)
    assert unresolved == []
    assert len(segments[0]["notes"]) == 2


def test_the_ustx_verification_matches_the_mapped_notes(tmp_path):
    rows = build_rows(["年轮"], [raw(0.0, 0.5), raw(0.5, 0.5)])[3]
    report = build_baseline_ustx(rows, tmp_path / "baseline.ustx", name="probe")
    verification = verify_ustx_notes(tmp_path / "baseline.ustx", report["ledger"])
    assert verification["one_to_one"] is True
    assert verification["missing_note_ids"] == []
    assert verification["retuned_note_ids"] == []
    assert verification["shifted_note_ids"] == []
    assert verification["duration_changed_note_ids"] == []
