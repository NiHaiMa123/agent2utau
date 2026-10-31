"""End-to-end CLI contract: the JSON state and the process exit code (P1.1-A).

Five injected faults are exercised through the real command line: a negative
length note, an overlap, a dropped character, an unresolved character and an
illegal extender.  The test reads the JSON state *and* the shell exit code.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def write_lyrics(path: Path, lines: list[str]) -> Path:
    from agent2utau.alignment import build_locked_lyrics_document
    doc = build_locked_lyrics_document("probe", lines, verification="test", source="test")
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return path


def write_game(path: Path, notes: list[dict]) -> Path:
    path.write_text(json.dumps({"notes": notes}, ensure_ascii=False), encoding="utf-8")
    return path


def note(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def run_cli(lyrics: Path, game: Path, out: Path, *extra: str) -> tuple[int, dict]:
    command = [sys.executable, "-m", "agent2utau.cli", "align-lyrics",
               "--lyrics", str(lyrics), "--game", str(game), "--out", str(out), *extra]
    completed = subprocess.run(command, capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               cwd=str(REPO_ROOT))
    payload = {}
    for line in reversed(completed.stdout.splitlines()):
        if line.startswith("{"):
            payload = json.loads(line)
            break
    return completed.returncode, payload


def write_hfa(path: Path, observations: list[dict]) -> Path:
    path.write_text(json.dumps({"schema_version": 1, "observations": observations},
                               ensure_ascii=False), encoding="utf-8")
    return path


def test_a_clean_run_exits_zero(tmp_path):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮"])
    game = write_game(tmp_path / "game.json", [note(0.0, 0.5), note(0.5, 0.5)])
    hfa = write_hfa(tmp_path / "hfa.json", [
        {"text": "年", "start": 0.0, "end": 0.5, "source": "hfa", "detail": "p00:年"},
        {"text": "轮", "start": 0.5, "end": 1.0, "source": "hfa", "detail": "p00:轮"},
    ])
    code, payload = run_cli(lyrics, game, tmp_path / "out", "--hfa", str(hfa))
    assert code == 0
    assert payload["status"] == "valid"


def test_a_line_without_any_time_evidence_is_incomplete(tmp_path):
    """No observation means the musical boundary is not established."""
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮"])
    game = write_game(tmp_path / "game.json", [note(0.0, 0.5), note(0.5, 0.5)])
    code, payload = run_cli(lyrics, game, tmp_path / "out")
    assert code == 3
    assert payload["status"] == "incomplete"


def test_a_negative_length_note_is_invalid_and_exits_non_zero(tmp_path):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮"])
    game = write_game(tmp_path / "game.json", [note(0.0, -0.2), note(0.5, 0.5)])
    code, payload = run_cli(lyrics, game, tmp_path / "out")
    assert code == 2
    assert payload["status"] == "invalid"


def test_an_overlap_is_invalid_and_exits_non_zero(tmp_path):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮"])
    game = write_game(tmp_path / "game.json", [note(0.0, 0.6), note(0.4, 0.4)])
    code, payload = run_cli(lyrics, game, tmp_path / "out")
    assert code == 2
    assert payload["status"] == "invalid"


def test_a_dropped_character_is_incomplete_and_exits_non_zero(tmp_path):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮年"])
    game = write_game(tmp_path / "game.json", [note(0.0, 0.5), note(0.5, 0.5)])
    code, payload = run_cli(lyrics, game, tmp_path / "out")
    assert code == 3
    assert payload["status"] == "incomplete"
    assert payload["unresolved_syllable_ids"]


def test_an_unresolved_character_is_incomplete(tmp_path):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮"])
    game = write_game(tmp_path / "game.json", [note(0.0, 0.5)])
    code, payload = run_cli(lyrics, game, tmp_path / "out")
    assert code == 3
    assert payload["status"] == "incomplete"


def test_an_illegal_extender_is_incomplete_and_is_not_dropped_silently(tmp_path):
    """The gapped note cannot be assigned, so it must be registered, not lost."""
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["声"])
    game = write_game(tmp_path / "game.json", [note(0.0, 0.63), note(0.79, 0.19)])
    hfa = write_hfa(tmp_path / "hfa.json", [
        {"text": "声", "start": 0.0, "end": 0.63, "source": "hfa", "detail": "p00:声"},
    ])
    code, payload = run_cli(lyrics, game, tmp_path / "out", "--hfa", str(hfa),
                            "--baseline", str(tmp_path / "baseline.ustx"))
    assert code == 3
    assert payload["status"] == "incomplete"
    assert payload["unassigned_voiced_notes"] == ["n0002"]
    registered = json.loads((tmp_path / "out" / "unassigned_voiced_notes.json").read_text(encoding="utf-8"))
    assert registered["count"] == 1
    row = registered["notes"][0]
    assert row["note_id"] == "n0002"
    assert row["classification"]
    assert row["reason_code"]
    assert row["candidates"]


def test_diagnostics_may_be_requested_explicitly(tmp_path):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮年"])
    game = write_game(tmp_path / "game.json", [note(0.0, 0.5), note(0.5, 0.5)])
    code, payload = run_cli(lyrics, game, tmp_path / "out", "--allow-incomplete")
    assert code == 0
    assert payload["status"] == "incomplete"


def test_a_diagnostic_run_is_never_valid(tmp_path):
    lyrics = write_lyrics(tmp_path / "lyrics.json", ["年轮"])
    game = write_game(tmp_path / "game.json", [note(0.0, 0.5), note(0.5, 0.5)])
    code, payload = run_cli(lyrics, game, tmp_path / "out", "--diagnostic-only")
    assert code == 3
    assert payload["status"] == "incomplete"
