"""The USTX verification must catch real damage (P1.2-C).

Every case below damages a written project in one specific way and asserts
that the verification reports it.  A verification that only counts notes and
compares lyrics would pass all of them.
"""

from pathlib import Path

import pytest
import yaml

from agent2utau.alignment import MappingConfig, build_evidence, map_syllables_to_notes
from agent2utau.alignment.baseline import build_baseline_ustx, verify_ustx_notes
from agent2utau.alignment.candidates import mapping_to_ustx_rows
from agent2utau.alignment.lyrics import parse_locked_lyrics
from agent2utau.alignment.notes import normalize_notes


def raw(start, dur, tone=60.0, voiced=True):
    return {"start": start, "dur": dur, "tone": tone, "voiced": voiced}


def build(tmp_path: Path):
    syllables = parse_locked_lyrics(["年轮", "年轮"])
    events = normalize_notes([raw(0.0, 0.5), raw(0.5, 0.5), raw(1.0, 0.5), raw(1.5, 0.5)])
    evidence = build_evidence(syllables)
    mapping = map_syllables_to_notes(syllables, events, evidence, MappingConfig(), song_id="test")
    rows = mapping_to_ustx_rows(mapping, events)
    path = tmp_path / "baseline.ustx"
    report = build_baseline_ustx(rows, path, name="probe")
    return path, report["ledger"]


def rewrite(path: Path, mutate) -> None:
    project = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(project)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(project, f, allow_unicode=True, sort_keys=False, width=10 ** 6)


def test_a_clean_project_verifies(tmp_path):
    path, ledger = build(tmp_path)
    verification = verify_ustx_notes(path, ledger)
    assert verification["one_to_one"] is True
    assert verification["shifted_note_ids"] == []
    assert verification["duration_changed_note_ids"] == []


def test_a_note_shifted_by_one_beat_is_caught(tmp_path):
    path, ledger = build(tmp_path)

    def mutate(project):
        project["voice_parts"][0]["notes"][1]["position"] += 480

    rewrite(path, mutate)
    verification = verify_ustx_notes(path, ledger)
    assert verification["one_to_one"] is False
    assert verification["shifted_note_ids"]


def test_a_changed_duration_is_caught(tmp_path):
    path, ledger = build(tmp_path)

    def mutate(project):
        project["voice_parts"][0]["notes"][1]["duration"] += 120

    rewrite(path, mutate)
    verification = verify_ustx_notes(path, ledger)
    assert verification["one_to_one"] is False
    assert verification["duration_changed_note_ids"]


def test_a_shifted_part_is_caught(tmp_path):
    path, ledger = build(tmp_path)

    def mutate(project):
        project["voice_parts"][0]["position"] += 480

    rewrite(path, mutate)
    verification = verify_ustx_notes(path, ledger)
    assert verification["one_to_one"] is False
    assert verification["shifted_note_ids"]


def test_two_identical_extenders_swapped_are_caught(tmp_path):
    """Text matching alone cannot see this; the positions do."""
    syllables = parse_locked_lyrics(["声"])
    events = normalize_notes([raw(0.0, 0.5), raw(0.5, 0.5), raw(1.0, 0.5)])
    evidence = build_evidence(syllables)
    mapping = map_syllables_to_notes(syllables, events, evidence, MappingConfig(), song_id="test")
    rows = mapping_to_ustx_rows(mapping, events)
    path = tmp_path / "baseline.ustx"
    report = build_baseline_ustx(rows, path, name="probe")

    def mutate(project):
        notes = project["voice_parts"][0]["notes"]
        notes[1]["position"], notes[2]["position"] = notes[2]["position"], notes[1]["position"]

    rewrite(path, mutate)
    verification = verify_ustx_notes(path, report["ledger"])
    assert verification["one_to_one"] is False
    assert verification["shifted_note_ids"]


def test_a_duplicated_lyric_is_caught(tmp_path):
    path, ledger = build(tmp_path)

    def mutate(project):
        project["voice_parts"][0]["notes"][1]["lyric"] = project["voice_parts"][0]["notes"][0]["lyric"]

    rewrite(path, mutate)
    verification = verify_ustx_notes(path, ledger)
    assert verification["one_to_one"] is False
    assert verification["lyric_mismatch_note_ids"]


def test_a_missing_note_is_caught(tmp_path):
    path, ledger = build(tmp_path)

    def mutate(project):
        project["voice_parts"][0]["notes"].pop(1)

    rewrite(path, mutate)
    verification = verify_ustx_notes(path, ledger)
    assert verification["one_to_one"] is False
    assert verification["missing_note_ids"]
