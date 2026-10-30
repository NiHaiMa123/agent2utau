"""生成迁移三表：inventory-before.tsv / relocation-map.tsv / uncertain-items.tsv。

分类依据（都来自文件正文或路径，不靠文件名猜）：
  1) 正文里出现的 run 路径 -> 本地 runs/ 目录名 -> 歌曲与 session；
  2) 正文里的歌曲关键词；
  3) docs/reports/<song>/ 的目录归属（路径即证据）。
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
MIG = ROOT / "migration" / "20261030-reorganization"
MIG.mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")

SONG_OF_PREFIX = [("nianlun", "nianlun"), ("yuai", "yuai"),
                   ("zuihouyiye", "lastpage"), ("lastpage", "lastpage"),
                   ("huahai", "huahai"), ("baishuo", "baishuo-research")]
SONG_KEYS = {"nianlun": ["年轮", "nianlun", "lingyuan"],
             "yuai": ["雨爱", "yuai"],
             "lastpage": ["最后一页", "lastpage", "zuihouyiye"],
             "huahai": ["花海", "huahai"]}

# 本地 run 目录 -> (song, run_id)
local_runs = {}
for top in ("production", "experiments", "research"):
    d = ROOT / "runs" / top
    if not d.exists():
        continue
    for c in sorted(d.iterdir()):
        if not c.is_dir():
            continue
        song = ""
        for pre, sg in SONG_OF_PREFIX:
            if c.name.startswith(pre):
                song = sg
                break
        local_runs[f"runs/{top}/{c.name}"] = (song, c.name)

RUN_RE = re.compile(r"runs[/\\](?:production|experiments|research)[/\\][A-Za-z0-9_\-]+")
DATE_RE = re.compile(r"20\d{6}")


def norm_run(m):
    return m.replace("\\", "/").rstrip("/")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(p, limit=300000):
    try:
        return (ROOT / p).read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


tracked = [l for l in subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace").stdout.split("\n") if l]
untracked = [l for l in subprocess.run(["git", "-C", str(ROOT), "ls-files", "--others",
                                       "--exclude-standard"], capture_output=True, text=True,
                                      encoding="utf-8", errors="replace").stdout.split("\n") if l]

inv_rows, rel_rows, unc_rows = [], [], []


def song_of_prefix(name):
    for pre, sg in SONG_OF_PREFIX:
        if name.startswith(pre):
            return sg
    return ""


for p in tracked:
    full = ROOT / p
    size = full.stat().st_size if full.exists() else 0
    txt = read(p) if size < 3_000_000 else ""
    runs = sorted({norm_run(m.group(0)) for m in RUN_RE.finditer(txt)})
    known = [r for r in runs if r in local_runs]
    song = ""
    run_id = ""
    date = ""
    evidence = ""
    if known:
        song = local_runs[known[0]][0]
        run_id = local_runs[known[0]][1]
        evidence = "content:" + ",".join(known[:3])
    else:
        parts = p.split("/")
        if len(parts) > 2 and parts[0] == "docs" and parts[1] == "reports" and parts[2] in ("nianlun", "yuai", "lastpage", "huahai"):
            song = parts[2]
            evidence = "path:docs/reports/" + parts[2]
        else:
            low = txt.lower()
            for s, keys in SONG_KEYS.items():
                if any(k in txt or k in low for k in keys):
                    song = s
                    evidence = "content:song-keyword"
                    break
    dates = sorted({m.group(0) for m in DATE_RE.finditer(txt)})
    if date == "" and dates:
        date = dates[-1]
    if song and not run_id:
        run_id = f"{song}-legacy"
        if not evidence:
            evidence = "path:" + "/".join(p.split("/")[:2])
    category = ("script" if p.startswith("scratch/") and p.endswith((".py", ".ps1", ".sh"))
                else "log" if p.endswith(".log") else "data" if p.endswith((".json", ".csv", ".txt"))
                else "report" if p.endswith(".md") else "other")
    risk = "low"
    if p.startswith(("research/baishuo", "docs/knowledge")) or p.endswith(".ustx"):
        risk = "protected"
    inv_rows.append(dict(old_path=p, tracked="yes", size=size,
                         sha256=sha256(full) if size and size < 5_000_000 else "",
                         song=song, run=run_id, category=category, date=date,
                         model="unknown-model", evidence=evidence, risk=risk))

# 本机 ignored 大目录：只登记，不移动
for top in ("runs", "demo", "projects", "data", "models", "external", "bridge"):
    d = ROOT / top
    if not d.exists():
        continue
    for c in sorted(d.iterdir()):
        if not c.is_dir():
            continue
        n = sum(1 for x in c.rglob("*") if x.is_file())
        sz = sum(x.stat().st_size for x in c.rglob("*") if x.is_file())
        song = song_of_prefix(c.name)
        inv_rows.append(dict(old_path=f"{top}/{c.name}/", tracked="ignored_dir", size=sz,
                             sha256="", song=song, run=c.name, category="local_run",
                             date="", model="unknown-model",
                             evidence="local-ignored-dir", risk="deferred"))

with open(MIG / "inventory-before.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\ttracked\tsize\tsha256\tsong\trun\tcategory\tdate\tmodel\tevidence\trisk\n")
    for r in inv_rows:
        f.write("\t".join(str(r[k]) for k in ("old_path", "tracked", "size", "sha256", "song", "run",
                                               "category", "date", "model", "evidence", "risk")) + "\n")
print("inventory rows:", len(inv_rows))
json.dump(dict(local_runs={k: list(v) for k, v in local_runs.items()}),
          open(ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_local_runs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
