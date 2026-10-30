"""P0-A：逐项审计 docs/knowledge 的 17 个改动文件。

对每个文件给出：旧 SHA（34061cd）、新 SHA（当前 HEAD）、差异类别
  ① 仅换行符  ② 仅路径/相对链接调整  ③ 正文数据/语义变化  ④ 未能确认
并附差异片段（前后各若干行）。
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
OUT.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BASE = "34061cd"


def git(*a):
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True)
    return r.stdout


def sha(b):
    return hashlib.sha256(b).hexdigest()


changed = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", BASE, "HEAD", "--",
                           "docs/knowledge/"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.split("\n")
changed = [c for c in changed if c.strip()]
print("changed knowledge files:", len(changed))

PATH_RE = re.compile(r"(?:docs/reports|scratch|docs|research|songs)/[A-Za-z0-9_\-./]+")
rows = []
for p in changed:
    old = git("show", f"{BASE}:{p}")
    new = git("show", f"HEAD:{p}")
    old_t = old.decode("utf-8", "replace")
    new_t = new.decode("utf-8", "replace")
    old_nl = old_t.replace("\r\n", "\n")
    new_nl = new_t.replace("\r\n", "\n")
    if old == new:
        kind, detail = "④ 未能确认", "字节完全相同"
    elif old_nl == new_nl:
        kind, detail = "① 仅换行符", f"CRLF/LF 差异；归一化后完全相同（{len(old)} vs {len(new)} 字节）"
    else:
        o = PATH_RE.sub("<P>", old_nl)
        n = PATH_RE.sub("<P>", new_nl)
        if o == n:
            kind = "② 仅路径/相对链接调整"
            diffs = []
            ol, nl = old_nl.split("\n"), new_nl.split("\n")
            for i in range(min(len(ol), len(nl))):
                if ol[i] != nl[i]:
                    diffs.append((i + 1, ol[i].strip(), nl[i].strip()))
            detail = f"{len(diffs)} 行仅路径不同"
            rows.append(dict(path=p, old_sha=sha(old), new_sha=sha(new), kind=kind,
                             detail=detail, diffs=diffs[:6]))
            continue
        kind = "③ 正文数据/语义变化"
        diffs = []
        ol, nl = old_nl.split("\n"), new_nl.split("\n")
        import difflib
        for line in list(difflib.unified_diff(ol, nl, lineterm="", n=1))[:24]:
            diffs.append(line)
        detail = f"{len(ol)} 行 -> {len(nl)} 行；正文存在非路径差异"
        rows.append(dict(path=p, old_sha=sha(old), new_sha=sha(new), kind=kind,
                         detail=detail, diffs=diffs))
        continue
    rows.append(dict(path=p, old_sha=sha(old), new_sha=sha(new), kind=kind, detail=detail, diffs=[]))

for r in rows:
    print(f"{r['kind']:22s} {r['path']}")

# 历史快照判定：history/ 下的快照与被引用的 SHA 基线应恢复原字节
frozen = [r for r in rows if "/history/" in r["path"]]
print("\nfrozen(history) files:", len(frozen))
json.dump(rows, open(OUT / "knowledge-diff-raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
