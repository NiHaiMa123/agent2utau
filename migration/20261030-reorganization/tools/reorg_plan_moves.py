"""生成移动映射（relocation-map）与 session 划分。

规则：
  * scratch/ 下能定位到具体 run 的脚本/小件 -> songs/<song>/sessions/<date>__<model>__<run-id>/{scripts,reports}
  * docs/reports/<song>/ 下能定位到 run 的报告 -> 同上 session 的 reports/；定位不到的 -> songs/<song>/reports/legacy/
  * docs/reports/production/ 下确属某歌制作报告的 -> 该歌 session；方法论/通用报告 -> 原地保留
  * 字节保护（research/baishuo、docs/knowledge、docs/lastpage-*-20261008.md、*.ustx）-> 原地保留，只登记索引
"""
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
MIG = ROOT / "migration" / "20261030-reorganization"
sys.stdout.reconfigure(encoding="utf-8")

RUN_RE = re.compile(r"runs[/\\][A-Za-z0-9_\-]+[/\\][A-Za-z0-9_\-]+")
PREFIX_SONG = [("nianlun", "nianlun"), ("yuai", "yuai"), ("zuihouyiye", "lastpage"),
                ("lastpage", "lastpage"), ("huahai", "huahai")]
EXPERIMENT_CATEGORY = [("phonation", "phonation"), ("alignment", "alignment"),
                       ("hfa", "alignment"), ("game", "alignment"), ("asr", "alignment"),
                       ("pitch", "pitch"), ("f0", "pitch"), ("pitd", "pitch"),
                       ("evaluation", "evaluation"), ("review", "evaluation"),
                       ("table", "research-tables"), ("baishuo", "research-baishuo"),
                       ("cover", "covers"), ("diag", "diagnostics")]


def norm(m):
    return m.replace("\\", "/").rstrip("/")


def song_of_run(name):
    for pre, sg in PREFIX_SONG:
        if name.startswith(pre):
            return sg
    return ""


def date_of_run(name):
    m = re.search(r"(20\d{6})", name)
    return m.group(1) if m else ""


tracked = [l for l in subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace").stdout.split("\n") if l]


def read(p):
    try:
        return (ROOT / p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def runs_in(text):
    # JSON 里的路径转义成双反斜杠，先归一
    t = text.replace("\\\\", "\\")
    return [norm(m.group(0)) for m in RUN_RE.finditer(t)]


def session_id(run_name, song):
    d = date_of_run(run_name)
    return f"{d or 'date-unknown'}__unknown-model__{run_name}"


moves = {}          # old -> new
sessions = defaultdict(lambda: dict(song="", run="", date="", files=[], local=""))
uncertainties = []

for p in tracked:
    if not (p.startswith("scratch/") or p.startswith("docs/reports/")):
        continue
    if p.endswith(".ustx") or "/baishuo/" in p:
        continue
    txt = read(p)
    counts = Counter(runs_in(txt))
    parts = p.split("/")
    path_song = ""
    if len(parts) > 2 and parts[0] == "docs" and parts[1] == "reports" and parts[2] in (
            "nianlun", "yuai", "lastpage", "huahai"):
        path_song = parts[2]
    song = path_song
    run = ""
    if counts:
        best = counts.most_common(1)[0][0]
        run = best.split("/")[-1]
        song = song_of_run(run) or song
    if not song:
        low = txt.lower()
        for s, keys in (("nianlun", ["年轮", "nianlun", "lingyuan"]),
                        ("yuai", ["雨爱", "yuai"]),
                        ("lastpage", ["最后一页", "lastpage", "zuihouyiye"]),
                        ("huahai", ["花海", "huahai"])):
            if any(k in txt or k in low for k in keys):
                song = s
                break
    # 通用研究 run（非歌曲前缀）-> experiments/
    if run and not song_of_run(run) and counts:
        cat = "misc"
        for key, c in EXPERIMENT_CATEGORY:
            if key in run:
                cat = c
                break
        sub = "scripts" if ext in (".py", ".ps1", ".sh") else "reports"
        new = f"experiments/{cat}/{sub}/{Path(p).name}"
        moves[p] = new
        sid = f"run-{run}"
        s = sessions[sid]
        s["song"], s["run"], s["date"] = "", run, date_of_run(run)
        s["files"].append(p)
        continue
    if not song:
        uncertainties.append(dict(old_path=p, reason="无法从正文或目录确定歌曲归属",
                                   risk="low" if p.startswith("scratch/") else "medium"))
        continue
    if not run:
        run = f"{song}-legacy"
    sid = session_id(run, song)
    ext = Path(p).suffix.lower()
    if p.startswith("scratch/"):
        sub = "scripts" if ext in (".py", ".ps1", ".sh") else "reports"
    else:
        sub = "reports"
    if not run.endswith("-legacy"):
        new = f"songs/{song}/sessions/{sid}/{sub}/{Path(p).name}"
    else:
        new = f"songs/{song}/reports/legacy/{Path(p).name}"
    moves[p] = new
    s = sessions[sid]
    s["song"], s["run"], s["date"] = song, run, date_of_run(run)
    s["files"].append(p)

# 保护：docs/lastpage-*-20261008.md 等字节保护文件不移动（已在上面排除规则外，显式再排除）
PROTECTED_PREFIX = ("docs/knowledge/", "research/baishuo/", "docs/reports/production/")
for p in list(moves):
    if p.startswith(PROTECTED_PREFIX):
        moves.pop(p)

# 兄弟文件继承：日志/小产物跟随同前缀脚本的 session（如 v11_compile.log <- v11_compile_plan.py）
def prefix_of(stem):
    m = re.match(r"^(v\d+[a-z]?|v3[a-z]?)", stem)
    return m.group(1) if m else ""


by_prefix = defaultdict(list)
for old, new in moves.items():
    if old.startswith("scratch/"):
        p = prefix_of(Path(old).stem)
        if p:
            by_prefix[p].append((old, new))
still_uncertain = []
for u in uncertainties:
    p = prefix_of(Path(u["old_path"]).stem)
    cands = by_prefix.get(p, [])
    if len(cands) == 1:
        old, new = cands[0]
        moves[u["old_path"]] = new
        u["reason"] = f"无独立 run 引用，但同前缀脚本 {old} 属于同一 session，按同批次归档"
        u["risk"] = "low"
        u["resolved_by"] = old
    else:
        still_uncertain.append(u)
uncertainties = still_uncertain

rows = []
for old, new in sorted(moves.items()):
    rows.append(dict(old_path=old, new_path=new, action="git-mv",
                     reason="按正文 run 引用与报告目录归属归入对应歌曲的 session",
                     sha_before="", sha_after="", references_checked="pending", status="planned"))
with open(MIG / "relocation-map.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\tnew_path\taction\treason\tsha_before\tsha_after\treferences_checked\tstatus\n")
    for r in rows:
        f.write("\t".join(r[k] for k in ("old_path", "new_path", "action", "reason", "sha_before",
                                         "sha_after", "references_checked", "status")) + "\n")
with open(MIG / "uncertain-items.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\treason\trisk\n")
    for r in uncertainties:
        f.write(f"{r['old_path']}\t{r['reason']}\t{r['risk']}\n")

print("planned moves:", len(moves))
print("by song:", Counter(v.split("/")[1] for v in moves.values()))
print("sessions:", len(sessions))
for sid, s in sorted(sessions.items()):
    print(f"  {s['song']:10s} {sid:70s} files={len(s['files'])}")
print("uncertain:", len(uncertainties))
for u in uncertainties[:25]:
    print("   ", u["old_path"])
json.dump(dict(moves=moves, sessions={k: v for k, v in sessions.items()}),
          open(ROOT / "songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/workspace" / "reorg_moves.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
