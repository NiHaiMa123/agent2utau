"""P1.2.1-D: a USTX verification failure must reach the song state.

The pipeline builds the project and verifies it; when the verification fails
the song becomes ``invalid`` (exit code 2) instead of quietly staying
``incomplete``.  A note that is *documented* as intentionally excluded (an
illegal extender) stays ``incomplete`` - an expected gap is not a defect.
"""

from pathlib import Path

import pytest

from agent2utau.alignment import build_evidence, map_syllables_to_notes
from agent2utau.alignment import pipeline as pipeline_module
from agent2utau.alignment.baseline import build_baseline_ustx, verify_ustx_notes
from agent2utau.alignment.candidates import mapping_to_ustx_rows
from agent2utau.alignment.gate import BLOCKED, evaluate_segment
from agent2utau.alignment.lyrics import parse_locked_lyrics
from agent2utau.alignment.notes import normalize_notes
from agent2utau.alignment.status import EXIT_INVALID, EXIT_INCOMPLETE


def raw(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def build_project(tmp_path: Path):
    syllables = parse_locked_lyrics(["年轮"])
    events = normalize_notes([raw(0.0, 0.5), raw(0.5, 0.5)])
    evidence = build_evidence(syllables)
    mapping = map_syllables_to_notes(syllables, events, evidence, song_id="test")
    rows = mapping_to_ustx_rows(mapping, events)
    path = tmp_path / "baseline.ustx"
    report = build_baseline_ustx(rows, path, name="test")
    return path, report


def write_lyrics(path: Path, lines):
    from agent2utau.alignment import build_locked_lyrics_document
    document = build_locked_lyrics_document("demo", lines, verification="test", source="test")
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def write_hfa(path: Path, observations):
    path.write_text(json.dumps({"schema_version": 1, "observations": observations},
                                ensure_ascii=False), encoding="utf-8")
    return path


def test_the_pipeline_reports_the_verification_identity(tmp_path):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮"])
    game = tmp_path / "game.json"
    game.write_text(json.dumps({"notes": [raw(0.0, 0.5), raw(0.5, 0.5)]}), encoding="utf-8")
    hfa = write_hfa(tmp_path / "hfa.json", [
        {"text": "年", "start": 0.0, "end": 0.5, "source": "hfa", "detail": "p00:年"},
        {"text": "轮", "start": 0.5, "end": 1.0, "source": "hfa", "detail": "p00:轮"},
    ])
    report = pipeline_module.run_alignment(
        lyrics, game, tmp_path / "out", song_id="demo", hfa_path=hfa,
        baseline_ustx=tmp_path / "out" / "baseline.ustx")
    assert report["verification_passed"] is True
    assert report["verification_identity"]["ustx_sha256"]
    assert report["status"] == "valid"


def test_a_failing_verification_makes_the_song_invalid(tmp_path, monkeypatch):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮"])
    game = tmp_path / "game.json"
    game.write_text(json.dumps({"notes": [raw(0.0, 0.5), raw(0.5, 0.5)]}), encoding="utf-8")
    real = pipeline_module.verify_ustx_notes

    def failing(ustx_path, ledger, **kwargs):
        result = real(ustx_path, ledger, **kwargs)
        result["one_to_one"] = False
        result["shifted_note_ids"] = ["n0001"]
        return result

    monkeypatch.setattr(pipeline_module, "verify_ustx_notes", failing)
    report = pipeline_module.run_alignment(
        lyrics, game, tmp_path / "out", song_id="demo",
        baseline_ustx=tmp_path / "out" / "baseline.ustx")
    assert report["status"] == "invalid"
    assert any(problem.startswith("verification:") for problem in report["hard_problems"])


def test_a_tampered_project_is_detected_by_the_gate(tmp_path):
    path, report = build_project(tmp_path)
    verification = verify_ustx_notes(path, report["ledger"])
    identity = {"ustx_sha256": "a" * 64, "lyrics_sha256": "b" * 64, "notes_sha256": "c" * 64}
    segment = evaluate_segment(
        segment_id="demo", song_id="demo", scenario="x",
        target_syllable_ids=["s0001", "s0002"], text="年轮",
        ordered_syllable_ids=["s0001", "s0002"],
        mapping_rows={
            "s0001": {"syllable_id": "s0001", "text": "年", "status": "mapped",
                       "note_ids": ["n0001"], "line_index": 0, "review_required": False},
            "s0002": {"syllable_id": "s0002", "text": "轮", "status": "mapped",
                       "note_ids": ["n0002"], "line_index": 0, "review_required": False},
        },
        unassigned_notes=[], verification_notes=verification["notes"],
        verification_global=verification, verification_identity=identity,
        expected_verification_identity={"ustx_sha256": "d" * 64},
        pending_decisions=[], pending_sha256="e" * 64,
    )
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_identity_mismatch" for b in segment["blockers"])


def test_a_missing_verification_blocks_the_segment(tmp_path):
    path, report = build_project(tmp_path)
    segment = evaluate_segment(
        segment_id="demo", song_id="demo", scenario="x",
        target_syllable_ids=["s0001"], text="年",
        ordered_syllable_ids=["s0001", "s0002"],
        mapping_rows={
            "s0001": {"syllable_id": "s0001", "text": "年", "status": "mapped",
                       "note_ids": ["n0001"], "line_index": 0, "review_required": False},
            "s0002": {"syllable_id": "s0002", "text": "轮", "status": "mapped",
                       "note_ids": ["n0002"], "line_index": 0, "review_required": False},
        },
        unassigned_notes=[], verification_notes=[],
        verification_global={"one_to_one": True},
        pending_decisions=[], pending_sha256="e" * 64,
    )
    assert segment["local_gate"] == BLOCKED
    assert any(b["code"] == "verification_missing" for b in segment["blockers"])


import json  # noqa: E402
