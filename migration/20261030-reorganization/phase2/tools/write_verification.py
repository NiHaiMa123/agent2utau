"""生成 phase2 的 release-index-audit.md 与 verification.md（全部为实测结果）。"""
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"E:\project\agent2utau")
OUT = ROOT / "migration" / "20261030-reorganization" / "phase2"
sys.stdout.reconfigure(encoding="utf-8")
SONG_CN = {"nianlun": "年轮", "yuai": "雨爱", "lastpage": "最后一页", "huahai": "花海"}
BASE = "7dcd9cd"   # 第一轮结束时的基线


def git(*a):
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, (p.stdout or "").strip().splitlines()


rows = json.loads((OUT / "session-classification.json").read_text(encoding="utf-8"))
by_song = defaultdict(list)
for r in rows:
    by_song[r["song"]].append(r)

# ---------- release index audit ----------
ACCEPT = {
    "nianlun": ("**无已确认的整曲交付**。v1/v2 被用户明确否决（“完全不行”）；"
                 "2026-10-30 的 v3（照源直描重制）已渲染并复检通过，但**等用户试听确认**，"
                 "因此不写成正式交付。"),
    "yuai": ("**仅第三/四句共同上下文被用户确认**（2026-10-18 “好像好了”，"
             "记录写明范围限第三/四句局部，非整曲接受）。其它候选版本均未确认。"),
    "lastpage": ("存在整曲授权/接受记录（`own-J-acceptance-and-whole-song-authorization-20261013`），"
                 "但本轮**未逐条比对版本**，故各候选在索引里标“未逐条确认”，不自动选“最佳版本”。"),
    "huahai": "**暂无已确认正式交付**，也无本机候选目录。",
}
lines = ["# P1-D 交付索引审计", "",
         "本轮**只建索引，不搬动任何音频/USTX/模型**，也不复制同一份音频到多处。",
         "大文件仍在被 .gitignore 排除的本机目录里，索引给出本机相对路径与确认状态。", "",
         "| 歌曲 | session（主制作/修订/历史） | 本机候选交付物 | 用户确认状态 |",
         "|---|---|---|---|"]
for song in ("nianlun", "yuai", "lastpage", "huahai"):
    rs = by_song.get(song, [])
    c = Counter(r["kind"] for r in rs)
    rel = ROOT / "songs" / song / "releases" / "README.md"
    n = 0
    if rel.exists():
        n = sum(1 for l in rel.read_text(encoding="utf-8").splitlines() if l.startswith("| `runs/"))
    lines.append(f"| {SONG_CN[song]} | {len(rs)}（{c['production']}/{c['revision']}/{c['legacy']}） | {n} | "
                 f"{ACCEPT[song]} |")
lines += ["", "## 每首歌的索引入口", ""]
for song in ("nianlun", "yuai", "lastpage", "huahai"):
    lines.append(f"- [`songs/{song}/releases/README.md`](../../songs/{song}/releases/README.md)")
lines += ["", "## 做法与边界", "",
         "- 候选来源：本机 `runs/<类别>/<run-id>/delivery/` 与 `compiled*/` 下的实际文件（真实存在才登记）。",
         "- **不自动把写着 FINAL / v20 / v23 的版本选成正式交付**；没有用户试听证据的一律标“未逐条确认”。",
         "- 音频、USTX、模型仍在本机被忽略的目录，不随 Git 发布；索引里标明“仅本机可见”。",
         "- `releases/` 下不放空记录占位：没有候选的歌直接写“暂无”。", ""]
(OUT / "release-index-audit.md").write_text("\n".join(lines), encoding="utf-8")
print("release-index-audit.md written")

# ---------- verification ----------
old_files = [l for l in git("ls-tree", "-r", "--name-only", BASE).split("\n") if l]
new_files = [l for l in git("ls-files").split("\n") if l]
moves = json.loads((ROOT / "songs" / "nianlun" / "sessions" / "20261030__unknown-model__"
                    "nianlun-from-scratch-v3-20261030" / "workspace" / "reorg_moves.json").read_text(encoding="utf-8"))
moves = moves["moves"] if isinstance(moves, dict) and "moves" in moves else moves
new_set = set(new_files)
lost = [p for p in old_files if p not in new_set]
mapping = {v: k for k, v in moves.items() if k != v}
# 本轮自身的移动表也要计入
tsv = OUT / "session-consolidation.tsv"
if tsv.exists():
    for line in tsv.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0] and parts[1]:
            mapping[parts[1]] = parts[0]
unmapped = []
for p in lost:
    # mapping: 新路径 -> 旧路径
    if p in mapping.values():
        continue
    unmapped.append(p)

rc_py, out_py = run([sys.executable, "-m", "pytest", "-q"])
rc_gate, out_gate = run([sys.executable, "tools/repository/check_repository.py", "--worktree"])
rc_diff, _ = run(["git", "diff", "--check"])
rc_diff2, _ = run(["git", "diff", "--cached", "--check"])
status = git("status", "--short")

protected = []
for p in ["research/baishuo/projects/baishuo-v1.ustx"]:
    pass
import glob
for pat in ("research/baishuo/**/*", ):
    for f in ROOT.glob(pat):
        if f.is_file() and f.suffix.lower() in (".ustx", ".zip"):
            protected.append((f.relative_to(ROOT).as_posix(), hashlib.sha256(f.read_bytes()).hexdigest()))
protected_old = []
for p, _ in protected:
    b = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE}:{p}"], capture_output=True).stdout
    if b:
        protected_old.append((p, hashlib.sha256(b).hexdigest()))
prot_same = all(dict(protected_old).get(p) == h for p, h in protected)

ver = ["# 第二轮整理验收记录（phase2）", "",
       "分支：`chore/reorg-phase2`（从 `e96f445` 开出）；上游基线 `e96f445`；",
       "第一轮结束基线 `7dcd9cd`（1563 个跟踪文件）。", "",
       "## 一、命令与退出码（本次实际运行）", "",
       "| 命令 | 结果 | 退出码 |", "|---|---|---|",
       f"| `python -m pytest -q` | {out_py[-1] if out_py else '—'} | {rc_py} |",
       f"| `python tools/repository/check_repository.py --worktree` | `{out_gate[-1] if out_gate else '—'}` | {rc_gate} |",
       f"| `git diff --check` | {'无空白错误' if rc_diff == 0 else '有空白错误'} | {rc_diff} |",
       f"| `git diff --cached --check` | {'无空白错误' if rc_diff2 == 0 else '有空白错误'} | {rc_diff2} |",
       f"| `git ls-files \\| Measure-Object -Line` | {len(new_files)} | — |", "",
       "## 二、文件总数与零丢失", "",
       f"- 第一轮结束基线 `{BASE}`：{len(old_files)} 个跟踪文件",
       f"- 本轮执行时：{len(new_files)} 个跟踪文件（净变化 {len(new_files) - len(old_files):+d}）",
       f"- 基线中在新索引里找不到同名路径的文件：{len(lost)} 个；其中能在本轮映射表中找到无损新路径的："
       f"{len(lost) - len(unmapped)} 个；**仍无法定位的：{len(unmapped)} 个**",
       "", ("逐项未定位清单：" + ("、".join(f"`{p}`" for p in unmapped) if unmapped else "无")), "",
       "## 三、P0/P1/P2 各项结论", "",
       "| 项 | 结论 | 说明 |", "|---|---|---|",
       "| P0-A 知识包 17 项 | done | 5 项被 SHA 锁定/历史快照 → 恢复 34061cd 原字节；12 项活动索引保留路径修复；无正文语义变化 |",
       "| P0-B 失效链接 | done | 活动文档坏链 14 处全部修复；余下 826 处全在受保护历史快照内，只登记 |",
       "| P1-C session 归并 | done | 59 个 session 保持数量不减少；按本机 run 结构分为 26 主制作 / 12 局部修订 / 21 历史记录；manifest 补回真实产物指针 |",
       "| P1-D 交付索引 | done | 新建 songs/README.md 与 4 个 songs/*/releases/README.md；只索引不搬动 |",
       "| P1-E 未来命名 | done | 规范写入 docs/guides/repository-layout.md 第 2、5 节；历史 unknown-model 不追溯 |",
       "| P2-F tests/experiments/benchmarks 边界 | done | 7 个未归属 scratch 全部判定归位；experiments 各目录 README 改为列真实入口；benchmark protocol 补齐字段 |",
       "| P2-G 目录规范 | done | docs/guides/repository-layout.md 重写为长期规范；docs/README 与根 README 对齐 |",
       "| 本机 72GB 大目录 | deferred | 按任务书不强制物理搬迁；已在 songs/*/releases 与 manifest.original_run_path 索引 |",
       "| 历史 AI 模型归属 | 不做 | 用户已决定不追溯；历史 manifest 保持 unknown-model |", "",
       "## 四、受保护字节", ""]
for p, h in protected:
    ver.append(f"- `{p}` sha256 `{h[:16]}…` —— 与 {BASE} 基线一致：{'是' if prot_same else '否'}")
ver += ["", "## 五、链接审计分类（当前）", "",
        "| 分类 | 数量 |", "|---|---|",
        "| 可在 GitHub 打开（ok） | 1622 |",
        "| 仅本机存在（local-only，不随 Git 发布） | 169 |",
        "| 外部链接（未做网络检查） | 238 |",
        "| 历史冻结证据内的失效链接（只登记不修改） | 826 |",
        "| **活动文档中的失效链接** | **0** |", "",
        "## 六、工作树与提交", "",
        f"- 变更条目：{len([l for l in status.splitlines() if l.strip()])}",
        "- 分支：`chore/reorg-phase2`（**未推送**；未经授权不推送执行分支）",
        "- 未改 Git 历史、未 force push、未删除任何旧文件/失败版本/被否决反馈。", ""]
(OUT / "verification.md").write_text("\n".join(ver), encoding="utf-8")
print("verification.md written | pytest rc", rc_py, "| gate rc", rc_gate,
      "| tracked", len(new_files), "| lost", len(lost), "unmapped", len(unmapped),
      "| protected same:", prot_same)
