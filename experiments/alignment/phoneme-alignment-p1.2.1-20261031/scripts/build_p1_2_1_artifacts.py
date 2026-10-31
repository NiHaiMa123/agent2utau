"""P1.2.1: re-run the frozen songs with the hardened status rules.

The inputs are the P1.2 frozen observations; GAME, HFA, lyrics, mappings,
the rounding study and the unassigned-note classification are not touched.
The run proves two things: the mapping is unchanged, and the verification
failure now reaches the song state.
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

RUN_ID = "phoneme-alignment-p1.2.1-20261031"
BASE_RUN = "phoneme-alignment-p1.2-20261031"
RUN_DIR = REPO_ROOT / "runs" / "production" / RUN_ID

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
        "hfa_from_base_run": "hfa_observations.json",
        "asr": None,
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--created-at", default="2026-10-31T09:40:00+08:00")
    args = parser.parse_args()
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    states = []
    worst = "valid"
    for song_id, cfg in SONGS.items():
        song_dir = RUN_DIR / song_id
        song_dir.mkdir(parents=True, exist_ok=True)
        base_dir = REPO_ROOT / "runs" / "production" / BASE_RUN / song_id
        frozen = {}
        shutil.copyfile(base_dir / "lyrics_locked.json", song_dir / "lyrics_locked.json")
        frozen["lyrics_locked.json"] = {
            "source": str((base_dir / "lyrics_locked.json").relative_to(REPO_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(song_dir / "lyrics_locked.json"),
        }
        if cfg.get("hfa_from_base_run"):
            name = cfg["hfa_from_base_run"]
            shutil.copyfile(base_dir / name, song_dir / name)
            hfa_path = song_dir / name
            frozen[name] = {
                "source": str((base_dir / name).relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(hfa_path),
            }
        else:
            hfa_path = REPO_ROOT / cfg["hfa"]
            frozen["hfa"] = {"path": cfg["hfa"], "sha256": sha256_file(hfa_path)}
        game_path = REPO_ROOT / cfg["game"]
        frozen["game.json"] = {"path": cfg["game"], "sha256": sha256_file(game_path)}
        asr_path = None
        if cfg.get("asr"):
            asr_path = REPO_ROOT / cfg["asr"]
            frozen["asr"] = {"path": cfg["asr"], "sha256": sha256_file(asr_path)}

        report = run_alignment(
            song_dir / "lyrics_locked.json", game_path, song_dir,
            hfa_path=hfa_path, asr_path=asr_path, song_id=song_id,
            baseline_ustx=song_dir / "baseline.ustx",
            baseline_name=f"{song_id}_baseline_p1_2_1",
        )
        base_mapping = json.loads((base_dir / "mapping.v1.json").read_text(encoding="utf-8"))
        new_mapping = json.loads((song_dir / "mapping.v1.json").read_text(encoding="utf-8"))
        base_pairs = {r["syllable_id"]: r["note_ids"] for r in base_mapping["mapping"]}
        new_pairs = {r["syllable_id"]: r["note_ids"] for r in new_mapping["mapping"]}
        changed = [sid for sid in sorted(set(base_pairs) | set(new_pairs))
                   if base_pairs.get(sid) != new_pairs.get(sid)]

        states.append({
            "song_id": song_id,
            "title": cfg["title"],
            "status": report["status"],
            "coverage": report["coverage"],
            "verification_passed": report["verification_passed"],
            "verification_identity": report["verification_identity"],
            "unresolved_syllable_ids": report["unresolved_syllable_ids"],
            "unassigned_voiced_notes": report["unassigned_voiced_notes"],
            "mapping_changed_vs_p1_2": changed,
            "hard_problems": report["hard_problems"],
            "frozen_inputs": frozen,
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
        "policy": "the P1.2 frozen observations are reused unchanged; only the status rules and "
                  "the local gate were hardened",
        "batch_status": worst,
        "songs": states,
    }
    write_json(RUN_DIR / "run_summary.json", summary)
    code = exit_code(worst)
    print(json.dumps({
        "batch_status": worst,
        "exit_code": code,
        "songs": [{
            "song_id": s["song_id"],
            "status": s["status"],
            "verification_passed": s["verification_passed"],
            "mapped": s["coverage"]["syllable_mapped"],
            "unresolved": s["coverage"]["syllable_unresolved"],
            "mapping_changed_vs_p1_2": len(s["mapping_changed_vs_p1_2"]),
            "hard_problems": s["hard_problems"][:3],
        } for s in states],
    }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
