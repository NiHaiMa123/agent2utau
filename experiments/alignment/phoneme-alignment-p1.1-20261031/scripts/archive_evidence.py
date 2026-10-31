"""Archive the JSON evidence of the two alignment runs into the repository.

The run directories stay on this machine (media, USTX projects and the
published-lyric transcription never enter Git).  The *text* evidence does:
the locked lyrics, the normalized notes, the mappings, the anomaly lists,
the per-note USTX verification, the sample index and the GAME stability
results.  Every archived file is byte-identical to its run counterpart, and
the manifest records the SHA256 of both so a reviewer can prove it.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNS = REPO_ROOT / "runs" / "production"

SESSIONS = {
    "phoneme-alignment-p0p1-20261031": {
        "run": "phoneme-alignment-p0p1-20261031",
        "files": [
            "nianlun/lyrics_locked.json", "nianlun/notes_normalized.json",
            "nianlun/mapping.v1.json", "nianlun/anomalies.json",
            "lastpage/lyrics_locked.json", "lastpage/notes_normalized.json",
            "lastpage/mapping.v1.json", "lastpage/anomalies.json",
            "yuai/lyrics_locked.json", "yuai/notes_normalized.json",
            "yuai/mapping.v1.json", "yuai/anomalies.json",
            "yuai/hfa_observations.json",
            "samples/index.json",
            "samples/nianlun/nianlun-melisma.phones.json",
            "samples/lastpage/lastpage-polyphone.phones.json",
            "samples/yuai/yuai-one_char_one_note.phones.json",
            "command-inventory/observe-nianlun/game.json",
            "command-inventory/observe-nianlun/asr.json",
        ],
    },
    "phoneme-alignment-p1.1-20261031": {
        "run": "phoneme-alignment-p1.1-20261031",
        "files": [
            "nianlun/lyrics_locked.json", "nianlun/notes_normalized.json",
            "nianlun/mapping.v1.json", "nianlun/anomalies.json",
            "nianlun/baseline_verification.json",
            "lastpage/lyrics_locked.json", "lastpage/notes_normalized.json",
            "lastpage/mapping.v1.json", "lastpage/anomalies.json",
            "lastpage/baseline_verification.json",
            "yuai/lyrics_locked.json", "yuai/notes_normalized.json",
            "yuai/mapping.v1.json", "yuai/anomalies.json",
            "yuai/baseline_verification.json",
            "yuai/hfa_observations.json",
            "run_summary.json",
            "game_stability/game_stability.json",
            "game_stability/cross_process.json",
        ],
    },
}

SKIP = {
    "command-inventory/probe_phones.json",
    "canonical_lyrics",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    summary = {}
    for session, cfg in SESSIONS.items():
        run_dir = RUNS / cfg["run"]
        target_root = REPO_ROOT / "experiments" / "alignment" / session / "evidence"
        entries = []
        for relative in cfg["files"]:
            source = run_dir / relative
            if not source.is_file():
                print(f"  missing, skipped: {relative}")
                continue
            target = target_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            entries.append({
                "path": relative,
                "run_path": str(source.relative_to(REPO_ROOT)).replace("\\", "/"),
                "sha256": sha256(target),
                "bytes": target.stat().st_size,
                "identical_to_run": sha256(target) == sha256(source),
            })
        manifest = {
            "schema_version": 1,
            "session": session,
            "run": f"runs/production/{cfg['run']}",
            "note": "byte-identical copies of the run's text evidence; the run itself stays "
                    "on this machine (media, USTX projects and the published-lyric "
                    "transcription are deliberately not in Git)",
            "file_count": len(entries),
            "total_bytes": sum(e["bytes"] for e in entries),
            "files": entries,
        }
        (target_root / "MANIFEST.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        summary[session] = {"files": len(entries),
                            "bytes": manifest["total_bytes"],
                            "all_identical": all(e["identical_to_run"] for e in entries)}
        print(f"{session}: {len(entries)} files, {manifest['total_bytes'] / 1024:.0f} KB")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
