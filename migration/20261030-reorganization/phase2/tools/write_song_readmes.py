"""P1-C/D：重写各歌曲 README（按主制作/局部修订/历史记录/交付四类），并建 songs/README.md 总入口。"""
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
sys.stdout.reconfigure(encoding="utf-8")
SONG_CN = {"nianlun": "年轮", "yuai": "雨爱", "lastpage": "最后一页", "huahai": "花海"}
KIND_TITLE = {"production": "主制作（Production Session）",
              "revision": "局部修订与试验（Revision / Experiment）",
              "legacy": "历史记录（Legacy Record）"}
NOTE = {
    "production": "一次完整制作/重做某歌的 run；有本地 compiled/delivery 产物。",
    "revision": "同次制作中的局部改版、试听候选、参数修正或对照试验。",
    "legacy": "只有报告/审计/反馈记录，没有独立脚本产物；多因被知识包按路径+SHA 绑定而保留原位。",
}


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


rows = json.loads((OUT / "session-classification.json").read_text(encoding="utf-8"))
tracked = set(l for l in git("ls-files").split("\n") if l)
by_song = defaultdict(list)
for r in rows:
    by_song[r["song"]].append(r)
for song in by_song:
    by_song[song].sort(key=lambda r: (r["kind"] != "production", r["sid"]))

for song, rs in sorted(by_song.items()):
    lines = [f"# {SONG_CN[song]}（{song}）制作索引", "",
             "按「主制作 / 局部修订与试验 / 历史记录 / 交付」四类索引；",
             "每个 session 目录含 `manifest.json`（song_id、run_id、日期、模型归属证据、状态、听感状态、",
             "本机原始 run 路径、产物清单），`scripts/`、`reports/`、`feedback/` 可跟踪，`workspace/` 被忽略。",
             "模型归属只按原始日志/manifest 判定，没有证据的一律 `unknown-model`——**这不是缺陷，是不猜**。",
             "历史 session 的目录名保持原样，不追溯重命名。", ""]
    for kind in ("production", "revision", "legacy"):
        group = [r for r in rs if r["kind"] == kind]
        if not group:
            continue
        lines += [f"## {KIND_TITLE[kind]}", "", NOTE[kind], "",
                  "| session | 日期 | 模型 | 本机 run 目录 | run 文件数 | session 内归档文件 |",
                  "|---|---|---|---|---|---|"]
        for r in group:
            date = r["sid"].split("__")[0]
            local = (r["info"] or {}).get("path", "—")
            lines.append(f"| [`{r['sid']}`]({r['sid']}/) | {date} | unknown-model | `{local}` | "
                         f"{(r['info'] or {}).get('nfiles', 0)} | {r['files']} |")
        lines.append("")
    lines += ["## 交付索引", "",
              "见 [`releases/README.md`](releases/README.md)：本机候选交付物与逐条确认状态。",
              "**没有用户试听确认的版本不算正式交付**；大文件仍在本机被忽略的目录里，不随 Git 发布。", ""]
    kept = [p for p in tracked if p.startswith(f"docs/reports/{song}/")]
    if kept:
        lines += ["## 因知识契约保留原位的文档", "",
                  "下列文档被 `docs/knowledge` 知识包按路径+SHA 引用，属字节保护范围，",
                  "按整理计划保留在 `docs/reports/` 原位（不搬进 songs/）：", ""]
        lines += [f"- `{p}`" for p in sorted(kept)]
        lines.append("")
    lines += ["## 全局未归属条目", "",
              "有 7 个 scratch 条目无法从正文与目录确证歌曲归属，统一登记在",
              "[`migration/20261030-reorganization/uncertain-items.tsv`](../../../migration/20261030-reorganization/uncertain-items.tsv)，",
              "**不在每首歌重复列出**，以免暗示它们属于本歌。", ""]
    (ROOT / "songs" / song / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print("README:", song, len(rs), "sessions")

# ---- songs/README.md 总入口 ----
top = ["# songs/ — 歌曲制作总入口", "",
       "每首歌有完整制作索引与交付索引；新制作的 session 与交付物命名规则见",
       "[docs/guides/repository-layout.md](../docs/guides/repository-layout.md)。", "",
       "| 歌曲 | 目录 | 制作 session | 主制作 | 局部修订/试验 | 历史记录 | 本机候选交付物 | 用户确认状态 |",
       "|---|---|---|---|---|---|---|---|"]
ACCEPT = {
    "nianlun": "无已确认整曲交付（v1/v2 被否决；2026-10-30 的 v3 待试听）",
    "yuai": "仅第三/四句局部被确认，非整曲",
    "lastpage": "有整曲授权记录（20261013），版本以本机 delivery 为准",
    "huahai": "暂无已确认交付",
}
for song in ("nianlun", "yuai", "lastpage", "huahai"):
    rs = by_song.get(song, [])
    c = Counter(r["kind"] for r in rs)
    rel = ROOT / "songs" / song / "releases" / "README.md"
    n_items = rel.read_text(encoding="utf-8").count("| `runs/") if rel.exists() else 0
    top.append(f"| {SONG_CN[song]} | [`{song}/`]({song}/) | {len(rs)} | {c['production']} | "
               f"{c['revision']} | {c['legacy']} | {n_items} | {ACCEPT[song]} |")
top += ["", "## 目录约定", "",
        "- `sessions/<日期>__<模型>__<run-id>/`：一次制作；`manifest.json` 是它的索引。",
        "- `reports/legacy/`：无法定位到具体 session 的历史报告。",
        "- `releases/`：交付索引（只索引，不搬动大文件）。",
        "- `workspace/`：本机原始 run 数据，被 .gitignore 排除。", ""]
(ROOT / "songs" / "README.md").write_text("\n".join(top), encoding="utf-8")
print("songs/README.md written")
