"""盘点：把本机工作树（tracked / 非忽略新文件 / ignored 大文件）分类，为迁移映射做准备。

只读，不移动任何东西。输出到 migration/20261030-reorganization/。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")

SONG_PATTERNS = [
    ("nianlun", ["年轮", "nianlun"]),
    ("yuai", ["雨爱", "yuai"]),
    ("lastpage", ["最后一页", "lastpage", "最后一頁"]),
    ("huahai", ["花海", "huahai"]),
]
RUN_PATTERNS = [
    r"nianlun-from-scratch-v3-20261030",
    r"nianlun-from-scratch-v2-20261028",
    r"nianlun-from-scratch-20261028",
    r"nianlun-lingyuan",
]


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


tracked = [l for l in git("ls-files", "-z").split("\0") if l]
ignored = [l for l in git("ls-files", "-z", "--others", "--ignored", "--exclude-standard").split("\0") if l]
untracked = [l for l in git("ls-files", "-z", "--others", "--exclude-standard").split("\0") if l]


def guess_song(text):
    low = text.lower()
    for song, keys in SONG_PATTERNS:
        for k in keys:
            if k in text or k in low:
                return song
    return ""


def guess_run(text):
    for p in RUN_PATTERNS:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return ""


def head(path, n=6000):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")[:n]
    except Exception:
        return ""


rows = []
for p in tracked:
    full = ROOT / p
    size = full.stat().st_size if full.exists() else 0
    txt = head(full) if size and size < 2_000_000 else ""
    song = guess_song(txt) if p.startswith(("scratch/", "docs/reports/")) else ""
    rows.append(dict(old_path=p, tracked="yes", size=size, song=song))

# 本机 ignored 的大目录（只列顶层，不逐文件哈希）
for top in ("runs", "demo", "projects", "data", "models", "external", "bridge"):
    d = ROOT / top
    if not d.exists():
        continue
    for child in sorted(d.iterdir()):
        if not child.is_dir():
            continue
        n = sum(1 for _ in child.rglob("*") if _.is_file())
        rows.append(dict(old_path=f"{top}/{child.name}/", tracked="ignored_dir", size=n,
                         song="", note="本机 ignored 目录，逐文件统计见下"))

print("tracked:", len(tracked), "ignored entries:", len(ignored), "untracked:", len(untracked))
from collections import Counter
c = Counter()
for r in rows:
    parts = r["old_path"].split("/")
    key = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
    c[key] += 1
for k, v in sorted(c.items()):
    print(f"{v:5d}  {k}")
json.dump(dict(tracked=tracked, ignored=ignored, untracked=untracked),
          open(ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_survey.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
