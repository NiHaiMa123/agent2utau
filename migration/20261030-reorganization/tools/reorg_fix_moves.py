"""修正 9 个因同前缀继承而撞车的移动目标（应落在同 session 的正确子目录与自身文件名）。"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")
MOVES = json.loads((ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_moves.json").read_text(encoding="utf-8"))["moves"]
exec_res = json.loads((ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_exec.json").read_text(encoding="utf-8"))
fails = exec_res["failed"]

fixed = []
for old, bad_new, why in fails:
    # 从错误的同名目标推断出正确的 session 目录，再按自身扩展名决定子目录
    session_dir = os.path.dirname(os.path.dirname(bad_new))
    ext = Path(old).suffix.lower()
    sub = "scripts" if ext in (".py", ".ps1", ".sh") else "reports"
    new = f"{session_dir}/{sub}/{Path(old).name}"
    src, dst = ROOT / old, ROOT / new
    if not src.exists():
        fixed.append((old, new, "source missing"))
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        fixed.append((old, new, "target exists"))
        continue
    r = subprocess.run(["git", "-C", str(ROOT), "mv", old, new], capture_output=True, text=True)
    if r.returncode != 0:
        fixed.append((old, new, r.stderr.strip()[:120]))
    else:
        MOVES[old] = new
        fixed.append((old, new, "moved"))

for f in fixed:
    print("  ", f)
json.dump(MOVES, open(ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_moves.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("moves total:", len(MOVES))
