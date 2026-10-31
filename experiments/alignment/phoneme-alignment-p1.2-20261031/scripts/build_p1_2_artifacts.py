"""P1.2 regression run: the same frozen observations, the fixed pipeline.

The inputs are copied (by SHA256) from the P1.1 run, never regenerated.  The
run writes the new artifacts and a per-syllable comparison against the P1.1
mapping, so the effect of the P1.2 changes is visible note by note instead of
being summarised as "coverage went up".
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent2utau.alignment import sha256_file  # noqa: E402
from agent2utau.alignment.pipeline import run_alignment, write_json  # noqa: E402
from agent2utau.alignment.status import exit_code  # noqa: E402

RUN_ID = "phoneme-alignment-p1.2-20261031"
BASE_RUN = "phoneme-alignment-p1.1-20261031"
RUN_DIR = REPO_ROOT / "runs" / "production" / RUN_ID
EVIDENCE = REPO_ROOT / "experiments" / "alignment" / BASE_RUN / "evidence"

SONGS = {
    "nianlun": {
        "title": "年轮",
        "game": "runs/production/nianlun-from-scratch-20261028/observation/game.json",
        "hfa": "runs/production/nianlun-from-scratch-20261028/hfa/hfa_summary.json",
    },
    "lastpage": {
        "title": "最后一页",
        "game": "runs/production/zuihouyiye-from-scratch-20261027/observation/game.json",
        "hfa": "runs/production/zuihouyiye-from-scratch-20261027/hfa/hfa_summary.json",
        "asr": "runs/lastpage_fresh_source_20261007/fresh_asr.json",
    },
    "yuai": {
        "title": "雨爱",
        "game": "runs/production/yuai-from-source-20261014/inputs/game.json",
        # 雨爱's HFA observation is token-only; the P1.1 run already joined it
        # with the locked lyrics into a normalized observation file
        "hfa_from_p1_1_run": "hfa_observations.json",
    },
}


def compare_with_p1_1(song_id: str, mapping: dict) -> dict:
    """Per-syllable comparison with the archived P1.1 mapping."""
    reference_path = EVIDENCE / song_id / "mapping.v1.json"
    if not reference_path.is_file():
        return {"reference": None, "note": "no archived P1.1 mapping to compare with"}
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    before = {row["syllable_id"]: row for row in reference["mapping"]}
    after = {row["syllable_id"]: row for row in mapping["mapping"]}
    changed = []
    for syllable_id in sorted(set(before) | set(after)):
        old = before.get(syllable_id, {})
        new = after.get(syllable_id, {})
        old_notes = list(old.get("note_ids") or [])
        new_notes = list(new.get("note_ids") or [])
        if old_notes == new_notes and old.get("status") == new.get("status"):
            continue
        changed.append({
            "syllable_id": syllable_id,
            "text": new.get("text", old.get("text")),
            "before_status": old.get("status"),
            "after_status": new.get("status"),
            "before_note_ids": old_notes,
            "after_note_ids": new_notes,
        })
    return {
        "reference": str(reference_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "reference_sha256": sha256_file(reference_path),
        "changed_syllable_count": len(changed),
        "changed": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at", default="2026-10-31T09:30:00+08:00")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    states = []
    worst = "valid"
    for song_id, cfg in SONGS.items():
        song_dir = RUN_DIR / song_id
        song_dir.mkdir(parents=True, exist_ok=True)
        source_dir = REPO_ROOT / "runs" / "production" / BASE_RUN / song_id
        frozen = {}
        for name in ("lyrics_locked.json", "hfa_observations.json"):
            source = source_dir / name
            if not source.is_file():
                continue
            target = song_dir / name
            shutil.copyfile(source, target)
            frozen[name] = {
                "source": str(source.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(target),
            }
        game_path = REPO_ROOT / cfg["game"]
        frozen["game.json"] = {"path": cfg["game"], "sha256": sha256_file(game_path)}
        if cfg.get("hfa_from_p1_1_run"):
            source = source_dir / cfg["hfa_from_p1_1_run"]
            shutil.copyfile(source, song_dir / cfg["hfa_from_p1_1_run"])
            hfa_path = song_dir / cfg["hfa_from_p1_1_run"]
            frozen["hfa_observations.json"] = {
                "source": str(source.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(hfa_path),
            }
        else:
            hfa_path = REPO_ROOT / cfg["hfa"]
            frozen["hfa"] = {"path": cfg["hfa"], "sha256": sha256_file(hfa_path)}
        asr_path = None
        if cfg.get("asr"):
            asr_path = REPO_ROOT / cfg["asr"]
            frozen["asr"] = {"path": cfg["asr"], "sha256": sha256_file(asr_path)}

        report = run_alignment(
            song_dir / "lyrics_locked.json", game_path, song_dir,
            hfa_path=hfa_path,
            asr_path=asr_path,
            song_id=song_id,
            baseline_ustx=song_dir / "baseline.ustx",
            baseline_name=f"{song_id}_baseline_p1_2",
        )
        mapping = json.loads((song_dir / "mapping.v1.json").read_text(encoding="utf-8"))
        comparison = compare_with_p1_1(song_id, mapping)
        write_json(song_dir / "comparison_with_p1_1.json", comparison)

        unassigned = json.loads(
            (song_dir / "unassigned_voiced_notes.json").read_text(encoding="utf-8"))
        verification = report.get("baseline_verification") or {}
        states.append({
            "song_id": song_id,
            "title": cfg["title"],
            "status": report["status"],
            "coverage": report["coverage"],
            "window_count": report["window_count"],
            "candidate_count": report["candidate_count"],
            "unresolved_syllable_ids": report["unresolved_syllable_ids"],
            "unresolved_note_ids": report["unresolved_note_ids"],
            "unassigned_voiced_notes": unassigned["count"],
            "unassigned_classification_counts": unassigned["classification_counts"],
            "unassigned_note_ids": [row["note_id"] for row in unassigned["notes"]],
            "ustx_one_to_one": verification.get("one_to_one"),
            "ustx_missing_note_ids": verification.get("missing_note_ids"),
            "ustx_shifted_note_ids": verification.get("shifted_note_ids"),
            "ustx_duration_changed_note_ids": verification.get("duration_changed_note_ids"),
            "window_decisions": {
                decision: sum(1 for w in mapping["windows"] if w["decision"] == decision)
                for decision in sorted({w["decision"] for w in mapping["windows"]})
            },
            "anchor_distribution": {
                key: sum(1 for row in mapping["mapping"]
                         if f"{row['evidence'].get('anchor_source')}.{row['evidence'].get('anchor_level')}" == key)
                for key in sorted({f"{row['evidence'].get('anchor_source')}.{row['evidence'].get('anchor_level')}"
                                   for row in mapping["mapping"]})
            },
            "changed_syllables_vs_p1_1": comparison.get("changed_syllable_count"),
            "hard_problems": report["hard_problems"],
            "frozen_inputs": frozen,
            "files": {k: str(v) for k, v in report["files"].items()},
        })
        if report["status"] == "invalid":
            worst = "invalid"
        elif report["status"] == "incomplete" and worst != "invalid":
            worst = "incomplete"

    summary = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "baseline_run": BASE_RUN,
        "created_at": args.created_at,
        "policy": "the P1.1 observation set is frozen by SHA256 and reused; no GAME, HFA or "
                  "lyrics input is regenerated inside this run",
        "batch_status": worst,
        "songs": states,
    }
    write_json(RUN_DIR / "run_summary.json", summary)
    code = exit_code(worst, allow_incomplete=args.allow_incomplete)
    print(json.dumps({
        "batch_status": worst,
        "exit_code": code,
        "songs": [{
            "song_id": s["song_id"],
            "status": s["status"],
            "mapped": s["coverage"]["syllable_mapped"],
            "unresolved": s["coverage"]["syllable_unresolved"],
            "unassigned_notes": s["unassigned_voiced_notes"],
            "changed_vs_p1_1": s["changed_syllables_vs_p1_1"],
            "ustx_one_to_one": s["ustx_one_to_one"],
            "windows": s["window_decisions"],
        } for s in states],
    }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
