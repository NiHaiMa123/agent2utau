"""刷新 song README（含因知识契约保留原位的文档清单）与 relocation-map（最终状态）。"""
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
MIG = ROOT / "migration" / "20261030-reorganization"
WS = ROOT / ("songs/nianlun/sessions/20261030__unknown-model__"
             "nianlun-from-scratch-v3-20261030/workspace")
sys.stdout.reconfigure(encoding="utf-8")
SONG_CN = {"nianlun": "年轮", "yuai": "雨爱", "lastpage": "最后一页", "huahai": "花海"}
STAGE_LOCAL = {
    "nianlun-from-scratch-20261028": "runs/production/nianlun-from-scratch-20261028",
    "nianlun-from-scratch-v2-20261028": "runs/production/nianlun-from-scratch-v2-20261028",
    "nianlun-v3-20261029": "runs/production/nianlun-v3-20261029",
    "nianlun-from-scratch-v3-20261030": "runs/production/nianlun-from-scratch-v3-20261030",
    "zuihouyiye-from-scratch-20261027": "runs/production/zuihouyiye-from-scratch-20261027",
}


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


tracked = [l for l in git("ls-files").split("\n") if l]
moves = json.loads((WS / "reorg_moves.json").read_text(encoding="utf-8"))
moves = moves["moves"] if isinstance(moves, dict) and "moves" in moves else moves
# 只保留真正换了位置��（old != new）
moves = {k: v for k, v in moves.items() if k != v}
kept_in_place = sorted({k for k in moves if k not in moves})


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    f = ROOT / p
    return sha_bytes(f.read_bytes()) if f.exists() else ""


changed = set(json.loads((WS / "reorg_exec.json").read_text(encoding="utf-8"))["changed"])
rows = []
for old, new in sorted(moves.items()):
    before = git("show", f"HEAD:{old}")
    sha_before = sha_bytes(before.encode("utf-8", "surrogateescape")) if before else ""
    sha_after = sha_file(new)
    rows.append(dict(old_path=old, new_path=new, action="git-mv",
                     reason="按正文 run 引用与报告目录归属归入对应歌曲的 session",
                     sha_before=sha_before, sha_after=sha_after,
                     references_checked=("path-string+relative-link rewritten" if old in changed
                                         else "no reference"),
                     status="moved"))
with open(MIG / "relocation-map.tsv", "w", encoding="utf-8", newline="\n") as f:
    f.write("old_path\tnew_path\taction\treason\tsha_before\tsha_after\treferences_checked\tstatus\n")
    for r in rows:
        f.write("\t".join(r[k] for k in ("old_path", "new_path", "action", "reason", "sha_before",
                                         "sha_after", "references_checked", "status")) + "\n")
ident = sum(1 for r in rows if r["references_checked"].startswith("path-string"))
print("relocation rows:", len(rows), "| 引用改写:", ident, "| 字节一致:", len(rows) - ident)

# session 视图
sessions = defaultdict(lambda: dict(song="", run="", date="", files=[]))
for p in tracked:
    m = re.match(r"songs/(nianlun|yuai|lastpage|huahai)/sessions/([^/]+)/(.+)$", p)
    if m:
        s = sessions[m.group(2)]
        s["song"], s["run"] = m.group(1), m.group(2).split("__")[-1]
        s["date"] = m.group(2).split("__")[0]
        s["files"].append(p)

# 因知识契约保留在 docs/reports 的文档（按歌曲归类）
kept_docs = defaultdict(list)
for p in tracked:
    m = re.match(r"docs/reports/(nianlun|yuai|lastpage)/(.+)$", p)
    if m:
        kept_docs[m.group(1)].append(p)

for song in ("nianlun", "yuai", "lastpage", "huahai"):
    rows_s = sorted((sid, s) for sid, s in sessions.items() if s["song"] == song)
    lines = [f"# {SONG_CN[song]}（{song}）制作索引", "",
             "本目录按「歌曲 → 日期/模型 → 制作 session → 脚本/报告/音频」组织。",
             "每个 session 的 `manifest.json` 记录制作日期、模型归属证据、状态与听感状态；",
             "`workspace/` 放本次制作的原始 run 数据（被 .gitignore 忽略；历史 run 因含",
             "硬编码绝对路径与 OpenUtau 工程引用，暂留原址，见 migration 的 deferred 清单）。", "",
             "## 制作 session", "",
             "| session | 日期 | 模型 | 状态 | 听感 | 本地 run 目录 | 归档文件数 |",
             "|---|---|---|---|---|---|---|"]
    for sid, s in rows_s:
        local = STAGE_LOCAL.get(s["run"], "")
        date = s["date"] if re.match(r"^20\d{6}$", s["date"]) else "date-unknown"
        lines.append(f"| `{sid}` | {date} | unknown-model | historical_unverified | unknown "
                     f"| {('`' + local + '`') if local else '—'} | {len(s['files'])} |")
    if kept_docs.get(song):
        lines += ["", "## 因知识契约保留原位的文档", "",
                  "下列文档被 `docs/knowledge` 的知识包按路径与 SHA 引用，属于字节保护范围，",
                  "按整理计划保留在 `docs/reports/` 原位，由本索引引用：", ""]
        for p in sorted(kept_docs[song]):
            lines.append(f"- `{p}`")
    lines += ["", "## 未确定归属（保留原址）", ""]
    unc = MIG / "uncertain-items.tsv"
    if unc.exists():
        for line in unc.read_text(encoding="utf-8").splitlines()[1:]:
            if not line.strip():
                continue
            path = line.split("\t")[0]
            if path.startswith("scratch/"):
                lines.append(f"- `{path}`（正文与目录都无法确证归属，按计划不动）")
    lines += ["", "## 其它入口", "",
              "- `assets/`：歌词与来源信息（非媒体）",
              "- `reports/legacy/`：无法定位到具体 session 的历史报告",
              "- `releases/`：明确选出的交付版索引/音频/USTX", ""]
    (ROOT / "songs" / song / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print("readme:", song, len(rows_s), "sessions,", len(kept_docs.get(song, [])), "kept docs")
print("sessions:", len(sessions))
