"""P1.1 regression run: fixed inputs, new outputs, aggregated status.

The P0/P1 run is the frozen baseline: its lyrics, GAME and HFA observations
are copied (by SHA256, never regenerated) into the new run directory, the
fixes are produced there, and the old assets are left untouched.

The batch aggregates the per-song states and returns a real exit code:
0 when every song is valid, 3 when a song is incomplete (unless
``--allow-incomplete``), 2 when a song is invalid.
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
from agent2utau.alignment.status import (  # noqa: E402
    EXIT_INCOMPLETE,
    EXIT_INVALID,
    EXIT_VALID,
    classify,
    exit_code,
)

RUN_ID = "phoneme-alignment-p1.1-20261031"
BASE_RUN = "phoneme-alignment-p0p1-20261031"
RUN_DIR = REPO_ROOT / "runs" / "production" / RUN_ID

#: frozen inputs: the P0/P1 run's artifacts are the only source
SONGS = {
    "nianlun": {
        "title": "年轮",
        "game": "runs/production/nianlun-from-scratch-20261028/observation/game.json",
        "hfa": "runs/production/nianlun-from-scratch-20261028/hfa/hfa_summary.json",
        "asr": None,
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
        "hfa": None,
        "asr": None,
    },
}


def freeze(song_id: str, cfg: dict) -> dict:
    """Copy the locked lyrics and the normalised HFA into the new run."""
    song_dir = RUN_DIR / song_id
    song_dir.mkdir(parents=True, exist_ok=True)
    source_dir = REPO_ROOT / "runs" / "production" / BASE_RUN / song_id
    frozen = {}
    lyrics_source = source_dir / "lyrics_locked.json"
    target = song_dir / "lyrics_locked.json"
    shutil.copyfile(lyrics_source, target)
    frozen["lyrics_locked"] = {
        "source": str(lyrics_source.relative_to(REPO_ROOT)).replace("\\", "/"),
        "path": str(target.relative_to(REPO_ROOT)).replace("\\", "/"),
        "sha256": sha256_file(target),
    }
    hfa_source = source_dir / "hfa_observations.json"
    if hfa_source.is_file():
        target = song_dir / "hfa_observations.json"
        shutil.copyfile(hfa_source, target)
        frozen["hfa_observations"] = {
            "source": str(hfa_source.relative_to(REPO_ROOT)).replace("\\", "/"),
            "path": str(target.relative_to(REPO_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(target),
        }
    else:
        frozen["hfa_observations"] = None
    for key in ("game", "hfa", "asr"):
        value = cfg.get(key)
        if value:
            path = REPO_ROOT / value
            frozen[key] = {"path": value, "sha256": sha256_file(path) if path.is_file() else None}
        else:
            frozen[key] = None
    return frozen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at", default="2026-10-31T03:30:00+08:00")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="Diagnostics only: do not fail the batch on incomplete songs")
    args = parser.parse_args()
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    states = []
    worst = "valid"
    for song_id, cfg in SONGS.items():
        frozen = freeze(song_id, cfg)
        hfa_path = RUN_DIR / song_id / "hfa_observations.json"
        report = run_alignment(
            RUN_DIR / song_id / "lyrics_locked.json",
            REPO_ROOT / cfg["game"],
            RUN_DIR / song_id,
            hfa_path=hfa_path if hfa_path.is_file() else (REPO_ROOT / cfg["hfa"] if cfg.get("hfa") else None),
            asr_path=(REPO_ROOT / cfg["asr"]) if cfg.get("asr") else None,
            song_id=song_id,
            baseline_ustx=RUN_DIR / song_id / "baseline.ustx",
            baseline_name=f"{song_id}_baseline_p1_1",
        )
        states.append({
            "song_id": song_id,
            "title": cfg["title"],
            "status": report["status"],
            "coverage": report["coverage"],
            "window_count": report["window_count"],
            "candidate_count": report["candidate_count"],
            "unresolved_syllable_ids": report["unresolved_syllable_ids"],
            "unresolved_note_ids": report["unresolved_note_ids"],
            "hard_problems": report["hard_problems"],
            "baseline_notes": (report.get("baseline") or {}).get("notes"),
            "baseline_unresolved_note_ids": (report.get("baseline") or {}).get("unresolved_note_ids"),
            "ustx_one_to_one": (report.get("baseline_verification") or {}).get("one_to_one"),
            "ustx_missing_note_ids": (report.get("baseline_verification") or {}).get("missing_note_ids"),
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
        "policy": "the P0/P1 observation set is frozen by SHA256 and reused; no GAME, HFA or "
                  "lyrics input is regenerated inside this run",
        "batch_status": worst,
        "songs": states,
    }
    write_json(RUN_DIR / "run_summary.json", summary)
    code = exit_code(worst, allow_incomplete=args.allow_incomplete)
    print(json.dumps({"batch_status": worst, "exit_code": code,
                      "songs": [{"song_id": s["song_id"], "status": s["status"],
                                 "mapped": s["coverage"]["syllable_mapped"],
                                 "unresolved": s["coverage"]["syllable_unresolved"],
                                 "unresolved_notes": s["unresolved_note_ids"],
                                 "ustx_one_to_one": s["ustx_one_to_one"]}
                                for s in states]}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
