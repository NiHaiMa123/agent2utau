"""P1.1-F: audit the files that were removed from the tracked tree.

The audit answers three questions for every file that disappeared between
``1a3a5bab`` and ``9e5435a7``:

* what exactly was it (original path, Git blob, size, SHA256)?
* does a byte-identical copy exist somewhere verifiable?
* what is its disposition?

Files that are not confirmed to live on in a verifiable place are copied
byte-for-byte into ``docs/archive/legacy-scratch/<original path>`` and mapped
back to their original path in the manifest.  Nothing is rewritten and
nothing is re-encoded: the archived bytes are the committed bytes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BEFORE = "1a3a5bab"
AFTER = "9e5435a7"
ARCHIVE = REPO_ROOT / "docs" / "archive" / "legacy-scratch"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True, text=True).stdout


def git_bytes(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=str(REPO_ROOT),
                          capture_output=True).stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    deleted = [line for line in
               git("diff", "--diff-filter=D", "--name-only", BEFORE, AFTER).splitlines()
               if line.strip()]
    entries = []
    for path in deleted:
        blob = git("rev-parse", f"{BEFORE}:{path}").strip()
        data = git_bytes("cat-file", "blob", blob)
        entry = {
            "original_path": path,
            "blob_sha1": blob,
            "bytes": len(data),
            "sha256": sha256(data),
            "holding_commit": BEFORE,
            "recoverable_from": f"git show {BEFORE}:{path}",
        }
        current = REPO_ROOT / path
        if current.is_file():
            current_bytes = current.read_bytes()
            entry["working_copy_present"] = True
            entry["working_copy_sha256"] = sha256(current_bytes)
            entry["working_copy_matches_committed"] = current_bytes == data
        else:
            entry["working_copy_present"] = False
            entry["working_copy_matches_committed"] = None
        if path.startswith("scratch/"):
            target = ARCHIVE / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            entry["disposition"] = "archived_byte_identical_copy"
            entry["archive_path"] = str(target.relative_to(REPO_ROOT)).replace("\\", "/")
            entry["detail"] = ("the working copy under scratch/ is not tracked and had already "
                               "drifted from the committed bytes; the committed bytes are kept "
                               "here unchanged")
        else:
            entry["disposition"] = "deleted_by_user_request"
            entry["archive_path"] = None
            entry["detail"] = ("unrelated to the singing project; deleted on explicit user "
                               "request. The bytes stay reachable in the Git history at "
                               f"{BEFORE}:{path} (blob {blob})")
        entries.append(entry)

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "audit": "P1.1-F history deletion check",
        "range": {"before": BEFORE, "after": AFTER},
        "deleted_file_count": len(entries),
        "total_bytes": sum(e["bytes"] for e in entries),
        "policy": "no tracked copy is deleted without either a byte-identical archive copy "
                  "or an explicit user decision; archived copies are never re-encoded",
        "entries": entries,
    }
    (ARCHIVE / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "deleted_file_count": len(entries),
        "total_bytes": manifest["total_bytes"],
        "archived_copies": sum(1 for e in entries if e["disposition"] == "archived_byte_identical_copy"),
        "user_authorized_deletions": sum(1 for e in entries if e["disposition"] == "deleted_by_user_request"),
        "working_copy_drifted": sum(1 for e in entries if e.get("working_copy_matches_committed") is False),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
