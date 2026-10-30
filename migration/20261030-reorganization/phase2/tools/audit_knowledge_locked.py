"""P0-A 续：判定 17 个文件里哪些被 SHA 锁定（必须恢复原字节）、哪些是历史快照、哪些是可保留的活动索引。"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
sys.stdout.reconfigure(encoding="utf-8")
BASE = "34061cd"


def git_text(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True).stdout.decode("utf-8", "replace")


def sha(b):
    return hashlib.sha256(b).hexdigest()


rows = json.loads((OUT / "knowledge-diff-raw.json").read_text(encoding="utf-8"))

# 1) 全仓（Git 端）搜索这 17 个文件旧 SHA，看是否被按 SHA 绑定
tracked = [l for l in git_text("ls-files").split("\n") if l]
blobs = {}
for p in tracked:
    if not p.endswith((".md", ".json", ".py", ".txt", ".yaml", ".yml")):
        continue
    blobs[p] = git_text("show", f"HEAD:{p}")

locked = {}
for r in rows:
    hits = []
    for p, t in blobs.items():
        if p == r["path"]:
            continue
        if r["old_sha"] in t:
            hits.append(p)
    locked[r["path"]] = hits

for r in rows:
    r["sha_locked_by"] = locked[r["path"]]
    r["is_history_snapshot"] = "/history/" in r["path"]
    print(f"{'LOCKED' if r['sha_locked_by'] else '-     '} "
          f"{'HIST ' if r['is_history_snapshot'] else '     '} {r['path']}"
          f"{'  <- ' + ', '.join(r['sha_locked_by'][:3]) if r['sha_locked_by'] else ''}")

json.dump(rows, open(OUT / "knowledge-diff-raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nlocked count:", sum(1 for r in rows if r["sha_locked_by"]),
      "| history snapshots:", sum(1 for r in rows if r["is_history_snapshot"]))
