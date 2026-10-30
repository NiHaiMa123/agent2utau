"""P0-A 执行：把 SHA 锁定/历史快照的 5 个文件恢复到第一轮前（34061cd）的精确字节。"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
sys.stdout.reconfigure(encoding="utf-8")
BASE = "34061cd"
rows = json.loads((OUT / "knowledge-diff-raw.json").read_text(encoding="utf-8"))
restore = [r for r in rows if r["sha_locked_by"] or r["is_history_snapshot"]]
print("to restore:", len(restore))
for r in restore:
    p = r["path"]
    before = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE}:{p}"],
                            capture_output=True).stdout
    old_sha = hashlib.sha256(before).hexdigest()
    cp = subprocess.run(["git", "-C", str(ROOT), "checkout", BASE, "--", p],
                        capture_output=True, text=True)
    now = (ROOT / p).read_bytes()
    now_sha = hashlib.sha256(now).hexdigest()
    ok = now_sha == old_sha
    print(f"  {'OK ' if ok else 'FAIL'} {p}  {old_sha[:12]} -> {now_sha[:12]}"
          f"{'  (' + cp.stderr.strip()[:60] + ')' if cp.stderr.strip() else ''}")
    r["restored"] = ok
    r["final_sha"] = now_sha
    r["decision"] = ("恢复第一轮前精确字节：被 SHA 锁定/历史快照，路径改写属第一轮副作用，"
                     "按计划不重写历史快照")
json.dump(rows, open(OUT / "knowledge-diff-raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("restored:", sum(1 for r in rows if r.get("restored")), "/", len(restore))
