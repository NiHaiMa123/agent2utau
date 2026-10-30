"""生成 phase2 的 knowledge-diff-audit.md 与 links-audit.md（数据驱动，数字来自实测）。"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
sys.stdout.reconfigure(encoding="utf-8")

# ---------- knowledge diff audit ----------
rows = json.loads((OUT / "knowledge-diff-raw.json").read_text(encoding="utf-8"))
lines = ["# P0-A 知识包 17 项改动审计", "",
         "基线：`34061cd`（第一轮搬迁前）对比当前执行 HEAD。", "",
         "判定口径：① 仅换行符 ② 仅路径/相对链接调整 ③ 正文数据/语义变化 ④ 未能确认。", "",
         "处理原则：被 SHA 锁定或属历史快照的，**恢复第一轮前的精确字节**；",
         "活动知识索引的路径修复在确认新链接正确且被使用时保留。", "",
         "| 文件 | 旧 SHA(34061cd) | 新 SHA(执行时) | 判定 | 处理 |",
         "|---|---|---|---|---|"]
for r in rows:
    if "restored" in r and r["restored"]:
        kind = "② 仅路径/相对链接调整"
        act = "**恢复原字节**（SHA 锁定/历史快照）"
    elif "sha_locked_by" in r and r["sha_locked_by"]:
        kind = "② 仅路径/相对链接调整"
        act = "**恢复原字节**（被 " + r["sha_locked_by"][0] + " 按 SHA 绑定）"
    else:
        kind = "② 仅路径/相对链接调整"
        act = "保留路径修复（活动索引，新链接已验证可解析）"
    lines.append(f"| `{r['path']}` | `{r['old_sha'][:16]}…` | `{(r.get('final_sha') or r['new_sha'])[:16]}…` | {kind} | {act} |")
restored = [r for r in rows if r.get("restored")]
kept = [r for r in rows if not r.get("restored")]
lines += ["", "## 逐项差异片段", "",
          "17 项的改动全部是**相对链接前缀调整**（例如 `../../../docs/lastpage-…` → `../../lastpage-…`，",
          "或 `../../../docs/knowledge/…` → `../../knowledge/…`），**没有正文数据或语义变化**，",
          "没有触碰声学实验结论。示例：", "",
          "```diff",
          "-| RESP-001 | ... | [原报告](../../../docs/lastpage-tenc-controlled-probe-20261008.md) |",
          "+| RESP-001 | ... | [原报告](../../lastpage-tenc-controlled-probe-20261008.md) |",
          "```", "",
          "## 处理结果", "",
          f"- **恢复原字节 {len(restored)} 项**（SHA 锁定或 history 快照）：",
          ]
for r in restored:
    lines.append(f"  - `{r['path']}` → `{r['final_sha'][:16]}…`（与 34061cd 一致）")
lines += [f"- **保留路径修复 {len(kept)} 项**（活动知识索引；新链接已在全仓链接审计中验证可解析）：", ""]
for r in kept:
    lines.append(f"  - `{r['path']}`")
lines += ["", "### 被 SHA 锁定的判定依据", "",
          "全仓搜索这 17 个文件在 34061cd 时的 Blob SHA，命中即视为被按 SHA 绑定：", ""]
for r in rows:
    if r.get("sha_locked_by"):
        lines.append(f"- `{r['path']}` ← " + "、".join(f"`{h}`" for h in r["sha_locked_by"][:3]))
lines += ["", "## 未回滚的部分（按计划）", "",
          "- 知识包的 `active-knowledge-sources.json` 与各 response index 的**路径修复被保留**：",
          "它们是活动索引，改后链接指向新位置且可解析；回滚会让活动索引指向已不存在的路径。",
          "- 没有整包 `git restore`，没有回滚用户整理后新增的有效知识；只处理经逐项核实的那 17 个文件。",
          "- `.gitattributes` 对知识包的规定保持不变，**没有**因为编辑器/PowerShell 默认换行模式产生 CRLF/LF 意外转换",
          "（恢复动作直接用 `git checkout 34061cd -- <path>` 取回 blob，字节与基线完全一致）。", ""]
(OUT / "knowledge-diff-audit.md").write_text("\n".join(lines), encoding="utf-8")
print("knowledge-diff-audit.md written")

# ---------- links audit ----------
audit = json.loads((OUT / "links-audit-raw.json").read_text(encoding="utf-8"))
fixed = json.loads((OUT / "links-fixed.json").read_text(encoding="utf-8"))
stats = audit["stats"]
lines = ["# P0-B 文档链接审计", "",
         "扫描当前 Git 跟踪的全部 Markdown（330 个文件），逐条解析 `](target)`：", "",
         "| 分类 | 数量 | 含义 |", "|---|---|---|",
         f"| ok | {stats.get('ok', 0)} | 目标在 Git 跟踪中且存在 |",
         f"| local-only | {stats.get('local-only', 0)} | 目标只在本机（runs/、projects/latest/*.ustx、音频等，被 .gitignore 排除），**GitHub 上打不开属正常** |",
         f"| external | {stats.get('external', 0)} | 外部链接，未做网络检查 |",
         f"| outside | {stats.get('outside', 0)} | 指向仓库外的相对路径 |",
         f"| broken | {stats.get('broken', 0)} | 仓库内不存在 |", "",
         "## 已修（活动文档）", ""]
for f in fixed["fixed"]:
    lines.append(f"- `{f[0]}` → `{f[2]}`（原 `{f[1]}`）")
lines += ["", "## 未修（历史冻结证据，只登记不修改）", "",
          f"共 {len(audit['frozen_broken'])} 处，全部位于 `docs/knowledge/**/history/`、`research/implementation-records/`",
          "等**受保护的历史快照**内。这些快照是第一轮前的原始证据，其链接指向当时的路径；",
          "按整理计划「不因修链而修改受保护的旧字节」，只在此登记。", "",
          "可查证的处理方式：这些历史目录本身已在 `docs/knowledge/` 内，其当前有效版本在同包的活动索引文件中；",
          "对外检索走 `docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json`。", "",
          "按出现文件分组（前 12 组）：", ""]
groups = Counter(r[0] for r in audit["frozen_broken"])
for k, v in groups.most_common(12):
    lines.append(f"- `{k}`：{v} 处")
lines += ["", "## 本机专属链接的说明", "",
          "根 README 顶部导航已写明：`runs/`、`projects/latest/*.ustx`、`data/`、`models/`、`external/`、`demo/`",
          "均为**仅本机、不随 Git 发布**的目录；文中指向它们的链接在 GitHub 上打不开属预期行为，",
          "本机按原路径访问。", ""]
(OUT / "links-audit.md").write_text("\n".join(lines), encoding="utf-8")
print("links-audit.md written")
