"""P0-B：全仓 Markdown 链接与仓库内路径引用审计。

分类：
  ok            目标在 Git 跟踪中且存在
  local-only    目标只在本机（被 .gitignore 排除，如 runs/、音频、USTX）
  broken        仓库内不存在
  external      外部链接（不做网络检查）
  frozen        位于受保护/历史快照文件中的坏链：只登记不修改
"""
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
sys.stdout.reconfigure(encoding="utf-8")

LINK = re.compile(r"\]\(([^)\s]+)\)")
FROZEN_HINT = ("/history/", "docs/knowledge/", "docs/implementation-records",
               "research/implementation-records", "docs/lastpage-")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


tracked = [l for l in git("ls-files").split("\n") if l]
tracked_set = set(tracked)
ignored = set(l for l in git("ls-files", "--others", "--ignored", "--exclude-standard").split("\n") if l)
mds = [p for p in tracked if p.endswith(".md")]

stats = defaultdict(int)
broken = []
local_only = []
for p in mds:
    txt = (ROOT / p).read_text(encoding="utf-8", errors="replace")
    base = os.path.dirname(p)
    for target in set(LINK.findall(txt)):
        t = target.split("#")[0].strip()
        if not t:
            continue
        if t.startswith(("http://", "https://", "mailto:", "#")):
            stats["external"] += 1
            continue
        if t.startswith("/"):
            cand = t.lstrip("/")
        elif ":" in t.split("/")[0]:
            stats["external"] += 1
            continue
        else:
            cand = os.path.normpath(os.path.join(base, t)).replace("\\", "/")
        if cand.startswith(".."):
            stats["outside"] += 1
            continue
        if cand in tracked_set:
            stats["ok"] += 1
            continue
        if (ROOT / cand).exists():
            stats["local-only"] += 1
            local_only.append((p, t, cand))
            continue
        stats["broken"] += 1
        broken.append((p, t, cand))

frozen_broken = [b for b in broken if any(h in b[0] for h in FROZEN_HINT)]
active_broken = [b for b in broken if b not in frozen_broken]
print("markdown files scanned:", len(mds))
print("stats:", dict(stats))
print("broken total:", len(broken), "| frozen/history:", len(frozen_broken),
      "| active:", len(active_broken))
print("local-only links:", len(local_only))
print("--- active broken (first 30) ---")
for b in active_broken[:30]:
    print("   ", b[0], "->", b[1])
print("--- frozen broken (first 12) ---")
for b in frozen_broken[:12]:
    print("   ", b[0], "->", b[1])

json.dump(dict(stats=dict(stats), broken=broken, active_broken=active_broken,
               frozen_broken=frozen_broken, local_only=local_only[:400]),
          open(OUT / "links-audit-raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
