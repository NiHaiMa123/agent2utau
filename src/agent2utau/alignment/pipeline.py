"""One reproducible alignment run: locked lyrics + GAME -> P0/P1 artifacts.

The pipeline writes the P0/P1 documents, validates them against the hard
constraints and reports a machine-readable state:

* ``valid``       - every hard constraint passes and nothing is pending,
* ``incomplete``  - nothing illegal happened but something still needs a
  human (unresolved syllables, notes that cannot be represented legally,
  windows without a usable candidate),
* ``invalid``     - a semantic error that must block any further use.

A diagnostic baseline may be written for an incomplete run, but it is never
presented as a finished baseline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from .baseline import rows_to_segments, verify_ustx_notes, write_baseline_ustx
from .candidates import MappingConfig, build_evidence, map_syllables_to_notes, mapping_to_ustx_rows
from .lyrics import load_locked_lyrics
from .notes import build_notes_document, load_game_notes, note_anomalies
from .observations import load_asr_observations, load_hfa_observations, match_observations, sha256_file
from .status import STATUS_INVALID, STATUS_VALID, classify
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
    diagnostic_only: bool = False,
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
    match_levels: dict[str, int] = {}
    if hfa_path:
        hfa_list = load_hfa_observations(hfa_path)
        hfa_obs, report = match_observations(hfa_list, syllables)
        observation_report += report
    if asr_path:
        asr_list = load_asr_observations(asr_path)
        asr_obs, report = match_observations(asr_list, syllables)
        observation_report += report
    for row in observation_report:
        match_levels[row["kind"]] = match_levels.get(row["kind"], 0) + 1

    evidence = build_evidence(syllables, hfa_obs, asr_obs)
    mapping = map_syllables_to_notes(syllables, notes, evidence, config, song_id=song_id)
    mapping["inputs"] = {
        "lyrics": {"path": str(lyrics_path), "sha256": sha256_file(lyrics_path)},
        "game": {"path": str(game_path), "sha256": sha256_file(game_path)},
        "hfa": {"path": str(hfa_path), "sha256": sha256_file(hfa_path)} if hfa_path else None,
        "asr": {"path": str(asr_path), "sha256": sha256_file(asr_path)} if asr_path else None,
    }
    mapping["clock"] = clock
    mapping["observation_match_counts"] = match_levels

    rows = mapping_to_ustx_rows(mapping, notes)
    mapping_problems = validate_mapping(mapping, syllables, notes)

    clock_rows = note_anomalies(notes)
    clock_hard = [r for r in clock_rows if r.get("severity") == "hard"]
    clock_info = [r for r in clock_rows if r.get("severity") != "hard"]

    segments, unresolved_notes, candidates = rows_to_segments(rows)
    kept_rows = [row for segment in segments for row in segment["notes"]]
    row_problems = validate_ustx_rows(kept_rows)

    baseline_report = None
    verification = None
    if baseline_ustx:
        baseline_report = write_baseline_ustx(
            segments, baseline_ustx, name=baseline_name or f"{song_id}_baseline")
        baseline_report["unresolved_note_ids"] = [row["note_id"] for row in unresolved_notes]
        baseline_report["unresolved_notes"] = unresolved_notes
        baseline_report["candidates"] = candidates
        verification = verify_ustx_notes(baseline_ustx, rows,
                                          part_lines=[s["line_index"] for s in segments])
        missing = set(verification["missing_note_ids"])
        reported = {row["note_id"] for row in unresolved_notes}
        if missing != reported:
            mapping_problems.append(
                "baseline: notes missing from the USTX do not match the reported illegal extends "
                f"(missing={sorted(missing)}, reported={sorted(reported)})")

    hard_problems = list(lyrics_problems) + list(mapping_problems) + list(row_problems)
    hard_problems += [f"clock: {r['kind']} {r.get('note_id', '')}".strip() for r in clock_hard]

    unresolved_syllables = [row["syllable_id"] for row in mapping["mapping"]
                            if row["status"] == "unresolved"]
    review_required = [row["syllable_id"] for row in mapping["mapping"]
                       if row.get("review_required")]
    status = classify(
        hard_problems=hard_problems,
        unresolved_syllables=unresolved_syllables,
        unresolved_note_ids=[row["note_id"] for row in unresolved_notes],
        review_required=review_required,
        diagnostic_only=diagnostic_only,
    )

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
            "clock_anomalies": clock_hard,
            "clock_info": clock_info,
            "observation_anomalies": observation_report,
            "observation_match_counts": match_levels,
            "mapping_problems": mapping_problems,
            "ustx_problems": row_problems,
            "lyrics_problems": lyrics_problems,
            "unresolved_notes": unresolved_notes,
            "baseline_candidates": candidates,
        }),
    }
    if baseline_report:
        written["baseline_ustx"] = baseline_report["project"]
    if verification:
        written["baseline_verification"] = write_json(
            out_dir / "baseline_verification.json", verification)

    return {
        "status": status,
        "song_id": song_id,
        "syllable_count": len(syllables),
        "note_count": len(notes),
        "voiced_note_count": sum(1 for n in notes if n.voiced),
        "coverage": mapping["coverage"],
        "window_count": len(mapping["windows"]),
        "candidate_count": len(mapping["candidates"]),
        "unresolved_syllable_ids": unresolved_syllables,
        "unresolved_note_ids": [row["note_id"] for row in unresolved_notes],
        "baseline": baseline_report,
        "baseline_verification": verification,
        "hard_problems": hard_problems,
        "problems": hard_problems,
        "files": written,
    }
