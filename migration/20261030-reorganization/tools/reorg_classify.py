"""按文件正文判定归属（歌曲 / run / 日期），输出迁移映射候选。

原则：只看正文里出现的 run 路径、歌曲关键词、报告标题，不靠文件名猜。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")

SONG_KEYS = {
    "nianlun": ["年轮", "nianlun", "lingyuan"],
    "yuai": ["雨爱", "yuai"],
    "lastpage": ["最后一页", "lastpage", "最后一頁"],
    "huahai": ["花海", "huahai"],
}
RUN_RE = re.compile(r"runs[/\\][A-Za-z0-9_\-./\\ ]*")
DATE_RE = re.compile(r"(20\d{6})")


def read(p, limit=200000):
    try:
        return (ROOT / p).read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def classify(path):
    txt = read(path)
    low = txt.lower()
    song = ""
    for s, keys in SONG_KEYS.items():
        if any(k in txt or k in low for k in keys):
            song = s
            break
    runs = sorted({m.group(0).strip().replace("\\", "/").rstrip(".") for m in RUN_RE.finditer(txt)})
    runs = [r for r in runs if len(r) > 6][:6]
    dates = sorted({m.group(1) for m in DATE_RE.finditer(txt)})
    return song, runs, dates[:6]


rows = []
for p in read_tracked if False else []:
    pass

import subprocess
tracked = [l for l in subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace").stdout.split("\n") if l]
out = []
for p in tracked:
    if not (p.startswith("scratch/") or p.startswith("docs/reports/") or p.startswith("docs/") and "lastpage" in p):
        continue
    song, runs, dates = classify(p)
    out.append(dict(path=p, song=song, runs=runs, dates=dates))
(ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_classify.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

from collections import Counter
print("classified:", len(out), Counter(r["song"] or "unknown" for r in out))
print("--- runs mentioned ---")
c = Counter()
for r in out:
    for run in r["runs"]:
        c[run] += 1
for k, v in c.most_common(40):
    print(f"{v:4d}  {k}")
print("--- unknown song samples ---")
for r in out:
    if not r["song"]:
        print("   ", r["path"], r["dates"][:2])
