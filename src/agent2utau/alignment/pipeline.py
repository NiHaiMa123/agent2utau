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

from .baseline import build_ledger, rows_to_segments, verify_ustx_notes, write_baseline_ustx
from .candidates import MappingConfig, build_evidence, map_syllables_to_notes, mapping_to_ustx_rows
from .lyrics import load_locked_lyrics
from .notes import build_notes_document, load_game_notes, note_anomalies
from .observations import (EXACT_LEVELS, confirmed_note_ids, load_asr_observations,
                          load_hfa_observations, match_observations, sha256_file)
from .status import STATUS_INVALID, STATUS_VALID, classify
from .unassigned import find_unassigned_voiced_notes, unassigned_candidates
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
    if hfa_path:
        hfa_list = load_hfa_observations(hfa_path)
        hfa_obs, report = match_observations(hfa_list, syllables, source="hfa")
        observation_report += report
    if asr_path:
        asr_list = load_asr_observations(asr_path)
        asr_obs, report = match_observations(asr_list, syllables, source="asr")
        observation_report += report

    def _tally(rows: list[dict]) -> dict:
        """Statistics per source *and* per matching stage.

        The stage is the kind of the report row, so "never matched" and
        "matched to another syllable" stay apart.  The authoritative
        distribution of the anchors that ended up in the mapping is reported
        separately (``final_anchor_distribution``).
        """
        counts: dict[str, int] = {}
        for row in rows:
            key = f"{row.get('source', 'observation')}.{row.get('kind', 'unknown')}"
            counts[key] = counts.get(key, 0) + 1
        return counts

    match_levels = _tally(observation_report)

    evidence = build_evidence(syllables, hfa_obs, asr_obs)
    trusted_pool = [o for o in list(hfa_obs.values()) + list(asr_obs.values())
                     if getattr(o, "level", "exact_text") in EXACT_LEVELS]
    confirmed = confirmed_note_ids(notes, trusted_pool)
    mapping = map_syllables_to_notes(syllables, notes, evidence, config, song_id=song_id,
                                     confirmed_note_ids=confirmed)
    mapping["inputs"] = {
        "lyrics": {"path": str(lyrics_path), "sha256": sha256_file(lyrics_path)},
        "game": {"path": str(game_path), "sha256": sha256_file(game_path)},
        "hfa": {"path": str(hfa_path), "sha256": sha256_file(hfa_path)} if hfa_path else None,
        "asr": {"path": str(asr_path), "sha256": sha256_file(asr_path)} if asr_path else None,
    }
    mapping["clock"] = clock
    mapping["observation_match_counts"] = match_levels
    mapping["observation_stage_counts"] = {
        kind: sum(1 for row in observation_report if row["kind"] == kind)
        for kind in sorted({row["kind"] for row in observation_report})
    }

    rows = mapping_to_ustx_rows(mapping, notes)
    mapping_problems = validate_mapping(mapping, syllables, notes)

    # every voiced note without an owner must have a documented destination
    owner_by_note_id = {note_id: row["syllable_id"]
                        for row in mapping["mapping"] if row["status"] == "mapped"
                        for note_id in row["note_ids"]}
    observation_pool = list(hfa_obs.values()) + list(asr_obs.values())
    unassigned = find_unassigned_voiced_notes(
        notes, owner_by_note_id, syllables, observation_pool,
        line_intervals={row["line_index"]: row for row in mapping.get("lines", [])})
    for row in unassigned:
        previous = next((n for n in sorted(notes, key=lambda n: n.index)
                          if n.index == row["index"] - 1), None)
        row["candidates"] = unassigned_candidates(row, previous)

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
        baseline_report["ledger"] = build_ledger(segments)
        verification = verify_ustx_notes(baseline_ustx, baseline_report["ledger"])
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
    anchor_distribution: dict[str, int] = {}
    for row in mapping["mapping"]:
        ev = row.get("evidence", {})
        key = f"{ev.get('anchor_source', 'none')}.{ev.get('anchor_level', 'missing')}"
        anchor_distribution[key] = anchor_distribution.get(key, 0) + 1
    status = classify(
        hard_problems=hard_problems,
        unresolved_syllables=unresolved_syllables,
        unresolved_note_ids=([row["note_id"] for row in unresolved_notes]
                             + [row["note_id"] for row in unassigned if not row["reviewed"]]),
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
        "unassigned_voiced_notes": write_json(out_dir / "unassigned_voiced_notes.json", {
            "schema_version": 1,
            "song_id": song_id,
            "count": len(unassigned),
            "classification_counts": {
                name: sum(1 for row in unassigned if row["classification"] == name)
                for name in sorted({row["classification"] for row in unassigned})
            },
            "unreviewed_count": sum(1 for row in unassigned if not row["reviewed"]),
            "notes": unassigned,
        }),
        "anomalies": write_json(out_dir / "anomalies.json", {
            "song_id": song_id,
            "clock_anomalies": clock_hard,
            "clock_info": clock_info,
            "observation_anomalies": observation_report,
            "observation_match_counts": match_levels,
            "observation_stage_counts": mapping["observation_stage_counts"],
            "final_anchor_distribution": anchor_distribution,
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
        "unassigned_voiced_notes": [row["note_id"] for row in unassigned],
        "baseline": baseline_report,
        "baseline_verification": verification,
        "hard_problems": hard_problems,
        "problems": hard_problems,
        "files": written,
    }
