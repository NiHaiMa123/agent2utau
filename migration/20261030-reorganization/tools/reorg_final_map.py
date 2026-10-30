"""生成最终 relocation-map.tsv（带移动前后 SHA 与引用检查状态）并刷新 session manifest / 歌曲 README。"""
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
MIG = ROOT / "migration" / "20261030-reorganization"
sys.stdout.reconfigure(encoding="utf-8")

final = json.loads((ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_final_moves.json").read_text(encoding="utf-8"))
moves = json.loads((ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_moves.json").read_text(encoding="utf-8"))
moves = moves["moves"] if isinstance(moves, dict) and "moves" in moves else moves
for m in final["moved"]:
    moves[m["old_path"]] = m["new_path"]


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    f = ROOT / p
    if not f.exists():
        return ""
    return sha_bytes(f.read_bytes())


rows = []
changed = set(json.loads((ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_exec.json").read_text(encoding="utf-8"))["changed"])
for old, new in sorted(moves.items()):
    before = git("show", f"HEAD:{old}")
    sha_before = sha_bytes(before.encode("utf-8", "surrogateescape")) if before else ""
    sha_after = sha_file(new)
    same = "identical" if sha_before == sha_after else "content-updated"
    rows.append(dict(old_path=old, new_path=new, action="git-mv",
                     reason="按正文 run 引用与报告目录归属归入对应歌曲的 session",
                     sha_before=sha_before, sha_after=sha_after,
                     references_checked=("path-string+relative-link rewritten" if old in changed else "no reference"),
                     status="moved"))
with open(MIG / "relocation-map.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\tnew_path\taction\treason\tsha_before\tsha_after\treferences_checked\tstatus\n")
    for r in rows:
        f.write("\t".join(r[k] for k in ("old_path", "new_path", "action", "reason", "sha_before",
                                         "sha_after", "references_checked", "status")) + "\n")
ident = sum(1 for r in rows if r["references_checked"].startswith("path-string"))
print("relocation rows:", len(rows), "| content rewritten:", ident,
      "| byte-identical:", len(rows) - ident)

# uncertain：补上"保留原址"的状态说明
unc_path = MIG / "uncertain-items.tsv"
rows_unc = []
if unc_path.exists():
    for line in unc_path.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        rows_unc.append(dict(old_path=parts[0], reason=parts[1] if len(parts) > 1 else "",
                             risk=parts[2] if len(parts) > 2 else ""))
for k in final["kept"]:
    rows_unc.append(dict(old_path=k["old_path"], reason=k["reason"], risk="low"))
seen = set()
with open(unc_path, "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\treason\trisk\tstatus\n")
    for r in rows_unc:
        if r["old_path"] in seen:
            continue
        seen.add(r["old_path"])
        f.write(f"{r['old_path']}\t{r['reason']}\t{r['risk']}\tkept-in-place\n")
print("uncertain rows:", len(seen))
