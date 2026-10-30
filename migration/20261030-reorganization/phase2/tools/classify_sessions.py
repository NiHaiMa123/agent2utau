"""P1-C：按本地 run 的实际结构给 59 个 session 分类（主制作 / 局部修订与试验 / 历史记录），
并为 manifest-only 的 session 补回它们真实产物的指针（内容证据：正文引用该 run-id）。
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
RUN_RE = re.compile(r"runs[/\\](?:production|experiments|research|review)[/\\][A-Za-z0-9_\-]+")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


tracked = [l for l in git("ls-files", "songs").split("\n") if l]
per = defaultdict(list)
for p in tracked:
    parts = p.split("/")
    if len(parts) >= 4 and parts[2] == "sessions":
        per["/".join(parts[:4])].append("/".join(parts[4:]))

# 本机 run 目录结构
run_dirs = {}
for top in ("production", "experiments", "research", "review"):
    d = ROOT / "runs" / top
    if not d.exists():
        continue
    for c in sorted(d.iterdir()):
        if not c.is_dir():
            continue
        names = {x.name for x in c.iterdir()}
        has_project = any(x.endswith(".ustx") for x in names) or "compiled" in names or "design" in names
        nfiles = sum(1 for x in c.rglob("*") if x.is_file())
        run_dirs[f"runs/{top}/{c.name}"] = dict(
            has_project=has_project, nfiles=nfiles, top=top,
            has_render=any(x.suffix.lower() in (".wav", ".mp3") for x in c.rglob("*")))

# 正文里引用了哪些 run
ref_by_run = defaultdict(set)
for p in git("ls-files").split("\n"):
    if not p or not p.endswith((".md", ".json", ".py")):
        continue
    try:
        t = (ROOT / p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for m in set(RUN_RE.findall(t)):
        ref_by_run[m.replace("\\", "/")].add(p)

rows = []
for d, fs in sorted(per.items()):
    song, sid = d.split("/")[1], d.split("/")[-1]
    run = sid.split("__")[-1]
    other = [f for f in fs if f != "manifest.json"]
    local = run_dirs.get(f"runs/production/{run}")
    if local is None:
        for k, v in run_dirs.items():
            if k.endswith("/" + run):
                local = v
                break
    # 分类
    if other and local and local["has_project"]:
        kind = "production"
    elif other:
        kind = "revision"
    elif local and local["has_project"]:
        kind = "production"
    else:
        kind = "legacy"
    # 真实产物指针（内容证据）
    arts = set()
    for k, v in ref_by_run.items():
        if k.endswith("/" + run):
            arts |= v
    rows.append(dict(session=d, song=song, run=run, kind=kind, files=len(other),
                     local_run=(f"runs/production/{run}" if f"runs/production/{run}" in run_dirs else None),
                     local_nfiles=(local["nfiles"] if local else 0),
                     local_has_project=(local["has_project"] if local else False),
                     artifacts=sorted(a for a in arts if a.startswith("songs/") or a.startswith("docs/"))))
from collections import Counter
print(Counter(r["kind"] for r in rows))
for r in rows:
    if r["kind"] != "production":
        print(f"  {r['kind']:10s} {r['run']:52s} files={r['files']:3d} local={r['local_nfiles']}")
json.dump(rows, open(OUT / "session-classification.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("rows:", len(rows))
