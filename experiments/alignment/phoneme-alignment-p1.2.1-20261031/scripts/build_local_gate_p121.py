"""P1.2.1-E: recompute the 16 segments with the hardened gate.

The P1.2 segment list (ids and target syllables) is read as-is; only the
verdict may change.  The pending decisions come from the single versioned
file and are passed explicitly; a missing or mismatched list fails closed.

Nothing here regenerates GAME, HFA, lyrics, mappings or the rounding study.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent2utau.alignment import sha256_file  # noqa: E402
from agent2utau.alignment.gate import evaluate_segment, summarize_gate  # noqa: E402
from agent2utau.alignment.pending import (  # noqa: E402
    PendingDecisionError,
    load_pending_decisions,
)
from agent2utau.alignment.pipeline import write_json  # noqa: E402

RUN_ID = "phoneme-alignment-p1.2.1-20261031"
BASE_RUN = "phoneme-alignment-p1.2-20261031"
RUN_DIR = REPO_ROOT / "runs" / "production" / RUN_ID
P12_RUN = REPO_ROOT / "runs" / "production" / BASE_RUN
PENDING_FILE = REPO_ROOT / "experiments" / "alignment" / "pending_decisions.json"

SONGS = ["nianlun", "lastpage", "yuai"]


def load_song(song_id: str) -> dict:
    song_dir = P12_RUN / song_id
    return {
        "mapping": json.loads((song_dir / "mapping.v1.json").read_text(encoding="utf-8")),
        "unassigned": json.loads(
            (song_dir / "unassigned_voiced_notes.json").read_text(encoding="utf-8")),
        "verification": json.loads(
            (song_dir / "baseline_verification.json").read_text(encoding="utf-8")),
        "lyrics": json.loads((song_dir / "lyrics_locked.json").read_text(encoding="utf-8")),
        "notes": json.loads((song_dir / "notes_normalized.json").read_text(encoding="utf-8")),
        "dir": song_dir,
    }


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    try:
        decisions, pending_sha = load_pending_decisions(PENDING_FILE, repo_root=REPO_ROOT)
        pending_error = None
    except PendingDecisionError as error:
        decisions, pending_sha = [], None
        pending_error = str(error)

    old_gate = json.loads((P12_RUN / "local_gate.json").read_text(encoding="utf-8"))
    old_by_id = {s["segment_id"]: s for s in old_gate["segments"]}

    segments: list[dict] = []
    for old in old_gate["segments"]:
        song_id = old["song_id"]
        data = load_song(song_id)
        mapping_rows = {row["syllable_id"]: row for row in data["mapping"]["mapping"]}
        ordered = [row["syllable_id"] for row in data["mapping"]["mapping"]]
        note_index = {n["note_id"]: n for n in data["notes"]["notes"]}
        target = list(old["syllable_ids"])
        note_ids = [nid for sid in target for nid in (mapping_rows.get(sid, {}).get("note_ids") or [])]
        times = [note_index[nid] for nid in note_ids if nid in note_index]
        start = min((n["start"] for n in times), default=0.0)
        end = max((n["end"] for n in times), default=0.0)
        verification_identity = {
            "ustx_sha256": sha256_file(data["dir"] / "baseline.ustx"),
            "lyrics_sha256": sha256_file(data["dir"] / "lyrics_locked.json"),
            "notes_sha256": sha256_file(data["dir"] / "notes_normalized.json"),
        }
        segment = evaluate_segment(
            segment_id=old["segment_id"],
            song_id=song_id,
            scenario=old["scenario"],
            target_syllable_ids=target,
            text=old["text"],
            ordered_syllable_ids=ordered,
            mapping_rows=mapping_rows,
            unassigned_notes=data["unassigned"]["notes"],
            verification_notes=data["verification"]["notes"],
            verification_global=data["verification"],
            verification_identity=verification_identity,
            expected_verification_identity=verification_identity,
            note_index=note_index,
            pending_decisions=decisions,
            pending_sha256=pending_sha,
            pending_error=pending_error,
            production_mode=True,
            start_s=start,
            end_s=end,
        )
        previous = old_by_id.get(old["segment_id"], {})
        segment["p1_2_gate"] = previous.get("local_gate")
        segment["gate_changed"] = previous.get("local_gate") != segment["local_gate"]
        segments.append(segment)

    index = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "baseline_run": BASE_RUN,
        "note": "local release only - the songs themselves stay incomplete; the P1.2 segment "
                "ids and target syllables are unchanged, only the verdict may change",
        **summarize_gate(segments),
        "p1_2_ready_count": old_gate["ready_count"],
        "p1_2_blocked_count": old_gate["blocked_count"],
        "changed_segments": [s["segment_id"] for s in segments if s["gate_changed"]],
        "pending_decisions_path": str(PENDING_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
        "pending_decisions_sha256": pending_sha,
        "pending_decisions_error": pending_error,
        "pending_decision_ids": [d.decision_id for d in decisions],
        "verification_note": "pure YAML ledger check against the written project; this is NOT "
                             "a native OpenUtau phoneme export",
        "native_phoneme_export": False,
        "segments": segments,
    }
    write_json(RUN_DIR / "local_gate.json", index)
    print(json.dumps({
        "segments": index["segment_count"],
        "ready": index["ready_count"],
        "blocked": index["blocked_count"],
        "p1_2_ready": index["p1_2_ready_count"],
        "changed": index["changed_segments"],
        "blocker_counts": index["blocker_counts"],
        "pending_error": pending_error,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
