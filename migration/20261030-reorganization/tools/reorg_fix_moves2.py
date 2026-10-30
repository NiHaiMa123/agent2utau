"""处理剩余同名撞车：先把被放错名字的文件移到正确名字，再放真正的同名文件。"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")
_data = json.loads((ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_moves.json").read_text(encoding="utf-8"))
MOVES = _data["moves"] if isinstance(_data, dict) and "moves" in _data else _data
exec_res = json.loads((ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_exec.json").read_text(encoding="utf-8"))
fails = [f for f in exec_res["failed"] if f[2] == "target exists"]

# 当前索引里，落在撞车目标路径上的到底是谁
status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "-z"],
                        capture_output=True, text=True, encoding="utf-8").stdout
renames = {}
for entry in status.split("\0"):
    if not entry:
        continue
    if " -> " in entry:
        left, right = entry.split(" -> ", 1)
        renames[right.strip()] = left.strip()

for old, bad_new, _ in fails:
    session_dir = os.path.dirname(os.path.dirname(bad_new))
    ext = Path(old).suffix.lower()
    sub = "scripts" if ext in (".py", ".ps1", ".sh") else "reports"
    new = f"{session_dir}/{sub}/{Path(old).name}"
    # 谁占着 new
    occupant_origin = renames.get(new)
    if occupant_origin and occupant_origin != old:
        ext2 = Path(occupant_origin).suffix.lower()
        sub2 = "scripts" if ext2 in (".py", ".ps1", ".sh") else "reports"
        occupant_new = f"{session_dir}/{sub2}/{Path(occupant_origin).name}"
        r = subprocess.run(["git", "-C", str(ROOT), "mv", new, occupant_new],
                           capture_output=True, text=True)
        print("  displaced:", new, "->", occupant_new, r.returncode)
        if r.returncode == 0:
            MOVES[occupant_origin] = occupant_new
    r = subprocess.run(["git", "-C", str(ROOT), "mv", old, new], capture_output=True, text=True)
    print("  moved:", old, "->", new, r.returncode, r.stderr.strip()[:80])
    if r.returncode == 0:
        MOVES[old] = new
json.dump(MOVES, open(ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_moves.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("moves total:", len(MOVES))
