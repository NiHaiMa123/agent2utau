"""建立 songs/ experiments/ benchmarks/ 骨架，为每个 session 写 manifest，并生成歌曲 README 索引。"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
sys.stdout.reconfigure(encoding="utf-8")

SONG_CN = {"nianlun": "年轮", "yuai": "雨爱", "lastpage": "最后一页", "huahai": "花海"}
STAGE_LOCAL = {
    "nianlun-from-scratch-20261028": "runs/production/nianlun-from-scratch-20261028",
    "nianlun-from-scratch-v2-20261028": "runs/production/nianlun-from-scratch-v2-20261028",
    "nianlun-v3-20261029": "runs/production/nianlun-v3-20261029",
    "nianlun-from-scratch-v3-20261030": "runs/production/nianlun-from-scratch-v3-20261030",
    "zuihouyiye-from-scratch-20261027": "runs/production/zuihouyiye-from-scratch-20261027",
}

# 1) 骨架目录
for song in ("nianlun", "yuai", "lastpage", "huahai"):
    for sub in ("assets", "sessions", "reports", "releases"):
        (ROOT / "songs" / song / sub).mkdir(parents=True, exist_ok=True)
for cat in ("alignment", "pitch", "phonation", "evaluation", "misc", "research-tables",
            "research-baishuo", "covers", "diagnostics"):
    (ROOT / "experiments" / cat).mkdir(parents=True, exist_ok=True)
bench = ROOT / "benchmarks" / "model-comparisons" / "20261030-lyrics-alignment"
(bench / "results").mkdir(parents=True, exist_ok=True)
(bench / "local").mkdir(parents=True, exist_ok=True)

# 2) 收集已归档内容
tracked = [l for l in subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace").stdout.split("\n") if l]
sessions = defaultdict(lambda: dict(song="", run="", date="", files=[]))
for p in tracked:
    m = re.match(r"songs/(nianlun|yuai|lastpage|huahai)/sessions/([^/]+)/(.+)$", p)
    if m:
        s = sessions[m.group(2)]
        s["song"], s["run"] = m.group(1), m.group(2).split("__")[-1]
        s["date"] = m.group(2).split("__")[0]
        s["files"].append(p)

# 3) 每个 session 写 manifest
for sid, s in sorted(sessions.items()):
    run = s["run"]
    local = STAGE_LOCAL.get(run, "")
    produced_date = s["date"] if re.match(r"^20\d{6}$", s["date"]) else ""
    status = "delivered_candidate" if run == "nianlun-from-scratch-v3-20261030" else "historical_unverified"
    listening = "unknown"
    manifest = {
        "song_id": s["song"],
        "run_id": run,
        "session_id": sid,
        "produced_date": produced_date,
        "produced_time": None,
        "primary_model": "unknown-model",
        "models": [],
        "model_evidence": [],
        "status": status,
        "listening_status": listening,
        "original_paths": [local] if local else [],
        "artifacts": sorted(s["files"]),
        "related_reports": [p for p in sorted(s["files"]) if p.endswith(".md")],
        "note": ("历史 session：模型归属无原始证据，按计划记 unknown-model；"
                 "local run 目录因含硬编码绝对路径与 OpenUtau 工程引用，暂留原址（deferred）"),
    }
    d = ROOT / "songs" / s["song"] / "sessions" / sid
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for sub in ("scripts", "reports", "feedback", "workspace"):
        (d / sub).mkdir(parents=True, exist_ok=True)

# 4) 歌曲 README（时间线 + 全历史索引）
for song in ("nianlun", "yuai", "lastpage", "huahai"):
    rows = [(sid, s) for sid, s in sessions.items() if s["song"] == song]
    rows.sort()
    lines = [f"# {SONG_CN[song]}（{song}）制作索引", "",
             "本目录按「歌曲 → 日期/模型 → 制作 session → 脚本/报告/音频」组织。",
             "每个 session 的 manifest.json 记录制作日期、模型归属证据、状态与听感状态；",
             "`workspace/` 放本次制作的原始 run 数据（默认被 .gitignore 忽略，历史 run 暂留原址）。", "",
             "## 制作 session", "",
             "| session | 日期 | 模型 | 状态 | 听感 | 本地 run 目录 | 归档文件数 |",
             "|---|---|---|---|---|---|---|"]
    for sid, s in rows:
        run = s["run"]
        local = STAGE_LOCAL.get(run, "")
        date = s["date"] if re.match(r"^20\d{6}$", s["date"]) else "date-unknown"
        lines.append(f"| `{sid}` | {date} | unknown-model | historical_unverified | unknown "
                     f"| {('`' + local + '`') if local else '—'} | {len(s['files'])} |")
    lines += ["", "## 未确定归属（保留原址）", ""]
    unc = ROOT / "migration" / "20261030-reorganization" / "uncertain-items.tsv"
    if unc.exists():
        for line in unc.read_text(encoding="utf-8").splitlines()[1:]:
            if not line.strip():
                continue
            path = line.split("\t")[0]
            if song in ("nianlun", "yuai", "lastpage") and path.startswith("scratch/"):
                lines.append(f"- `{path}`（正文与目录都无法确证归属，按计划不动）")
    lines += ["", "## 其它入口", "",
              "- `assets/`：歌词与来源信息（非媒体）",
              "- `reports/legacy/`：无法定位到具体 session 的历史报告",
              "- `releases/`：明确选出的交付版索引/音频/USTX", ""]
    (ROOT / "songs" / song / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print("song readme:", song, len(rows), "sessions")
print("sessions with manifest:", len(sessions))
