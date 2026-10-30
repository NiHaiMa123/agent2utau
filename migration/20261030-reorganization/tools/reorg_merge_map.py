"""把最后一批移动记录合并回总映射，并重出 relocation-map.tsv。"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
MIG = ROOT / "migration" / "20261030-reorganization"
WS = ROOT / ("songs/nianlun/sessions/20261030__unknown-model__"
             "nianlun-from-scratch-v3-20261030/workspace")
sys.stdout.reconfigure(encoding="utf-8")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    f = ROOT / p
    return hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else ""


moves = json.loads((WS / "reorg_moves.json").read_text(encoding="utf-8"))
moves = moves["moves"] if isinstance(moves, dict) and "moves" in moves else moves
final = json.loads((WS / "reorg_final_moves.json").read_text(encoding="utf-8"))
for m in final["moved"]:
    moves[m["old_path"]] = m["new_path"]
# 已回退到原位的，不再算作移动
for k, v in list(moves.items()):
    if k == v:
        moves.pop(k)
json.dump(moves, open(WS / "reorg_moves.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

changed = set(json.loads((WS / "reorg_exec.json").read_text(encoding="utf-8"))["changed"])
rows = []
for old, new in sorted(moves.items()):
    if old == new:
        continue
    before = git("show", f"HEAD:{old}")
    sha_before = sha_bytes(before.encode("utf-8", "surrogateescape")) if before else ""
    rows.append(dict(old_path=old, new_path=new, action="git-mv",
                     reason="按正文 run 引用与报告目录归属归入对应歌曲的 session",
                     sha_before=sha_before, sha_after=sha_file(new),
                     references_checked=("path-string+relative-link rewritten" if old in changed
                                         else "no reference"),
                     status="moved"))
with open(MIG / "relocation-map.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\tnew_path\taction\treason\tsha_before\tsha_after\treferences_checked\tstatus\n")
    for r in rows:
        f.write("\t".join(r[k] for k in ("old_path", "new_path", "action", "reason", "sha_before",
                                         "sha_after", "references_checked", "status")) + "\n")
ident = sum(1 for r in rows if r["references_checked"].startswith("path-string"))
print("relocation rows:", len(rows), "| 自身内容改写:", ident, "| 字节一致:", len(rows) - ident)
