"""One reproducible alignment run: locked lyrics + GAME -> P0/P1 artifacts.

The pipeline writes the four P0/P1 documents, validates them against the hard
constraints and refuses to report success when a constraint is violated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from .baseline import build_baseline_ustx
from .candidates import MappingConfig, build_evidence, map_syllables_to_notes, mapping_to_ustx_notes
from .lyrics import load_locked_lyrics
from .notes import build_notes_document, load_game_notes, note_anomalies
from .observations import load_asr_observations, load_hfa_observations, match_observations, sha256_file
from .validator import validate_locked_lyrics, validate_mapping, validate_ustx_rows


def write_json(path: str | Path, value) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return str(path)


def run_alignment(
    lyrics_path: str | Path,
    game_path: str | Path,
    out_dir: str | Path,
    *,
    hfa_path: str | Path | None = None,
    asr_path: str | Path | None = None,
    song_id: str = "",
    config: MappingConfig | None = None,
    baseline_ustx: str | Path | None = None,
    baseline_name: str | None = None,
) -> dict:
    """Run P0/P1 for one song and write the artifacts into ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lyrics_path = Path(lyrics_path)
    game_path = Path(game_path)

    syllables, lyrics_doc = load_locked_lyrics(lyrics_path)
    song_id = song_id or lyrics_doc.get("song_id") or "song"
    lyrics_problems = validate_locked_lyrics(lyrics_doc)

    notes = load_game_notes(game_path)
    clock = {
        "origin": "source_t0",
        "bpm": 120.0,
        "resolution": 480,
        "tick_rate_per_s": 960.0,
        "note": "fixed 120 BPM / 480 resolution, same grid as openutau/build.py",
    }

    hfa_obs, asr_obs = {}, {}
    observation_report: list[dict] = []
    if hfa_path:
        hfa_list = load_hfa_observations(hfa_path)
        hfa_obs, report = match_observations(hfa_list, syllables)
        observation_report += report
    if asr_path:
        asr_list = load_asr_observations(asr_path)
        asr_obs, report = match_observations(asr_list, syllables)
        observation_report += report

    evidence = build_evidence(syllables, hfa_obs, asr_obs)
    mapping = map_syllables_to_notes(syllables, notes, evidence, config, song_id=song_id)
    mapping["inputs"] = {
        "lyrics": {"path": str(lyrics_path), "sha256": sha256_file(lyrics_path)},
        "game": {"path": str(game_path), "sha256": sha256_file(game_path)},
        "hfa": {"path": str(hfa_path), "sha256": sha256_file(hfa_path)} if hfa_path else None,
        "asr": {"path": str(asr_path), "sha256": sha256_file(asr_path)} if asr_path else None,
    }
    mapping["clock"] = clock

    rows = mapping_to_ustx_notes(mapping, notes)
    for row in rows:
        syllable = next(s for s in syllables if s.syllable_id == row["syllable_id"])
        row["line_index"] = syllable.line_index
    row_problems = validate_ustx_rows(rows)
    mapping_problems = validate_mapping(mapping, syllables, notes)
    clock_problems = note_anomalies(notes)

    problems = lyrics_problems + mapping_problems + row_problems
    baseline_report = None
    if baseline_ustx:
        baseline_report = build_baseline_ustx(
            rows, baseline_ustx, name=baseline_name or f"{song_id}_baseline")
        problems += [f"baseline: {a}" for a in baseline_report["anomalies"]]

    notes_doc = build_notes_document(
        song_id, notes,
        source=str(game_path), source_sha256=sha256_file(game_path), clock=clock)
    lyrics_out = dict(lyrics_doc)
    lyrics_out["source_sha256"] = sha256_file(lyrics_path)

    written = {
        "lyrics_locked": write_json(out_dir / "lyrics_locked.json", lyrics_out),
        "notes_normalized": write_json(out_dir / "notes_normalized.json", notes_doc),
        "mapping": write_json(out_dir / "mapping.v1.json", mapping),
        "anomalies": write_json(out_dir / "anomalies.json", {
            "song_id": song_id,
            "clock_anomalies": clock_problems,
            "observation_anomalies": observation_report,
            "mapping_problems": mapping_problems,
            "ustx_problems": row_problems,
            "lyrics_problems": lyrics_problems,
            "baseline_anomalies": (baseline_report or {}).get("anomalies", []),
        }),
    }
    if baseline_report:
        written["baseline_ustx"] = baseline_report["project"]

    return {
        "status": "completed" if not problems else "completed_with_problems",
        "song_id": song_id,
        "syllable_count": len(syllables),
        "note_count": len(notes),
        "voiced_note_count": sum(1 for n in notes if n.voiced),
        "coverage": mapping["coverage"],
        "window_count": len(mapping["windows"]),
        "candidate_count": len(mapping["candidates"]),
        "baseline": baseline_report,
        "problems": problems,
        "files": written,
    }
