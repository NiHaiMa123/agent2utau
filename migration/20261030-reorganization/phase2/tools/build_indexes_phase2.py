"""P1-C + P1-D：session 分类与索引、manifest 补证、歌曲 README 重写、交付索引建立。

分类依据（全部来自本机实际内容，不靠目录名猜）：
  production  run 内有 compiled*/delivery/ 目录（产出过可交付物）
  revision    run 内是 before/candidate/inputs/native（对既有工程的局部改版，无整曲编译）
  legacy      其余（只有观察/审计/反馈记录）
manifest-only 的 session 不搬文件（其正文被知识包按路径+SHA 绑定），
只在 manifest 里补回真实产物指针并标 legacy/reference-only。
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
SONG_CN = {"nianlun": "年轮", "yuai": "雨爱", "lastpage": "最后一页", "huahai": "花海"}
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

# ---- 本机 run 结构 ----
run_info = {}
for top in ("production", "experiments", "research", "review"):
    d = ROOT / "runs" / top
    if not d.exists():
        continue
    for c in sorted(d.iterdir()):
        if not c.is_dir():
            continue
        names = {x.name for x in c.iterdir()}
        has_compiled = any(n.startswith("compiled") for n in names) or "delivery" in names
        has_edit = bool(names & {"inputs", "native", "final-native", "initial-native",
                                 "actual-inputs", "candidate-native"})
        has_ustx = any(x.suffix.lower() == ".ustx" for x in c.rglob("*.ustx"))
        wavs = [x for x in c.rglob("*") if x.suffix.lower() in (".wav", ".mp3")]
        run_info[c.name] = dict(path=f"runs/{top}/{c.name}", has_compiled=has_compiled,
                                has_edit=has_edit, has_ustx=has_ustx, wavs=len(wavs),
                                nfiles=sum(1 for x in c.rglob("*") if x.is_file()))

# ---- 正文引用 run 的文件 ----
ref_by_run = defaultdict(set)
for p in git("ls-files").split("\n"):
    if not p or not p.endswith((".md", ".json", ".py")):
        continue
    try:
        t = (ROOT / p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for m in set(RUN_RE.findall(t)):
        ref_by_run[m.replace("\\", "/").split("/")[-1]].add(p)

rows = []
for d, fs in sorted(per.items()):
    song = d.split("/")[1]
    sid = d.split("/")[-1]
    run = sid.split("__")[-1]
    other = [f for f in fs if f != "manifest.json"]
    info = run_info.get(run)
    if info and info["has_compiled"]:
        kind = "production"
    elif info and info["has_edit"]:
        kind = "revision"
    else:
        kind = "legacy"
    arts = sorted(a for a in ref_by_run.get(run, set())
                  if a.startswith("songs/") or a.startswith("docs/"))
    rows.append(dict(session=d, song=song, sid=sid, run=run, kind=kind,
                     files=len(other), info=info, artifacts=arts))

from collections import Counter
print("session kinds:", Counter(r["kind"] for r in rows))

# ---- 1) 给 manifest-only 的 session 补证 ----
updated = 0
for r in rows:
    mp = ROOT / r["session"] / "manifest.json"
    if not mp.exists():
        continue
    man = json.loads(mp.read_text(encoding="utf-8"))
    man["session_kind"] = r["kind"]
    if r["info"]:
        man["original_paths"] = [r["info"]["path"]]
        man["local_run_files"] = r["info"]["nfiles"]
    if r["artifacts"]:
        man["artifacts"] = sorted(set(man.get("artifacts", [])) | set(r["artifacts"]))
        man["related_reports"] = sorted(set(man.get("related_reports", []))
                                        | {a for a in r["artifacts"] if a.endswith(".md")})
    if r["kind"] != "production" and not r["files"]:
        man["status"] = "legacy_reference_only"
        man["note"] = ("本 session 无独立脚本/报告产物；其真实记录因被 docs/knowledge 知识包"
                       "按路径+SHA 绑定而保留在 docs/reports/ 下（见 artifacts）。"
                       "按整理计划不强行搬动，只做索引标注。")
    elif r["kind"] == "revision":
        man["note"] = "本次制作中的局部改版（revision），证据与产物见 artifacts/original_paths。"
    mp.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    updated += 1
print("manifests enriched:", updated)

# ---- 2) 交付索引（releases） ----
def delivery_items(song):
    items = []
    for r in rows:
        if r["song"] != song or not r["info"]:
            continue
        base = ROOT / r["info"]["path"]
        for sub in ("delivery",):
            d = base / sub
            if not d.exists():
                continue
            for f in sorted(d.iterdir()):
                if f.is_file():
                    items.append(dict(run=r["run"], file=f"{r['info']['path']}/{sub}/{f.name}",
                                      kind=f.suffix.lstrip(".").lower(),
                                      size=f.stat().st_size))
    # 整曲渲染（compiled 下的成品）
    for r in rows:
        if r["song"] != song or not r["info"]:
            continue
        base = ROOT / r["info"]["path"]
        for sub in sorted(x.name for x in base.iterdir() if x.is_dir() and x.name.startswith("compiled")):
            d = base / sub
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix.lower() in (".wav", ".mp3", ".ustx"):
                    items.append(dict(run=r["run"], file=f"{r['info']['path']}/{sub}/{f.name}",
                                      kind=f.suffix.lstrip(".").lower(), size=f.stat().st_size))
    return items


ACCEPT = {
    "nianlun": "无已确认的整曲交付：v1/v2 被用户明确否决（“完全不行”）；2026-10-30 的 v3 等待用户试听。",
    "yuai": "仅第三/四句共同上下文被用户确认（2026-10-18 “好像好了”，范围限第三/四句局部），不是整曲接受。",
    "lastpage": "存在整曲授权/接受记录（20261013 own-J-acceptance-and-whole-song-authorization）；具体版本以本地 delivery 为准。",
    "huahai": "暂无已确认正式交付。",
}
for song in ("nianlun", "yuai", "lastpage", "huahai"):
    items = delivery_items(song)
    lines = [f"# {SONG_CN[song]}（{song}）交付索引", "",
             "**这里只索引，不搬运。** 音频、USTX、模型等大文件仍在本机被 .gitignore 排除的目录里，",
             "不随 Git 发布；下表给出本机相对路径与现状。没有用户试听确认的版本不写成正式交付。", "",
             f"## 确认状态", "", ACCEPT[song], ""]
    if items:
        lines += ["## 本机候选交付物（按 run 分组）", "",
                  "| run | 本机路径 | 类型 | 字节 | 确认状态 |", "|---|---|---|---|---|"]
        for it in items:
            lines.append(f"| {it['run']} | `{it['file']}` | {it['kind']} | {it['size']} | 未逐条确认 |")
    else:
        lines += ["## 本机候选交付物", "", "本机未发现该歌的 delivery/ 或 compiled 成品目录。", ""]
    lines += ["", "## 相关 session", "",
              "- 见上级 `songs/<song>/README.md` 的分类索引。", ""]
    d = ROOT / "songs" / song / "releases"
    d.mkdir(parents=True, exist_ok=True)
    (d / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"releases/{song}: {len(items)} items")

json.dump(rows, open(OUT / "session-classification.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
