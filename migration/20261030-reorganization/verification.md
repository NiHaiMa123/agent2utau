# 2026-10-30 项目无损分类整理 — 验收记录

依据：`PROJECT_REORGANIZATION_PLAN_20261030.md`（拉自 origin/main，提交 34061cd）。
分支：`chore/reorganize-20261030`（从 `codex/source-function-cleanup` 的 34061cd 开出，**未推送**）。

---

## 一、总体结果

| 项 | 整理前 | 整理后 |
|---|---|---|
| Git 跟踪文件 | 1440 | **1568**（635 个换位 + 128 个新增，0 丢失） |
| `scratch/` 下跟踪文件 | 378 | 7（均为无法确证归属者，按计划保留原址） |
| `docs/reports/` 下跟踪文件 | 323 | 244（其余按归属归入 songs/，部分因知识契约保留原位） |
| 歌曲 session（带 manifest） | — | **59** |
| 受保护字节（research/baishuo 三份作者原件 + ZIP） | — | SHA 逐一核对，**未变** |

**零丢失核对**：以 `git ls-tree HEAD` 的 1440 个原文件逐个比对，新索引中无任何文件缺少去处（`old files without a new home: 0`）。
**残留旧路径引用**：全仓扫描已移动的旧路径字符串与相对链接，**0 处**指向不存在的旧位置。

---

## 二、分类依据（不靠文件名猜）

每个文件按 **正文证据** 判定：先扫正文里出现的 `runs/<类别>/<run-id>` 路径，与本机 `runs/` 实有目录对照，
得到歌曲与 session；无 run 引用时用报告目录（`docs/reports/<song>/`）与正文歌词/关键词；
仍不明的登记 `uncertain-items.tsv`，**不猜、不动**。

- 雨爱 = `yuai-*`；最后一页 = `zuihouyiye-*` 与 `lastpage-*`（两者是同一首歌的不同 run 前缀，已按 run 名区分并统一到 `lastpage`）。
- 年轮 = `nianlun-*`；白烁类研究留在 `research/`（字节保护，不移动）。

---

## 三、新结构与 session 清单

```
songs/<song>/README.md          中文歌名 + 制作时间线 + 全历史 session 索引
songs/<song>/assets/            歌词与来源信息（非媒体）
songs/<song>/sessions/<日期>__<模型>__<run-id>/
        manifest.json  scripts/  reports/  feedback/  workspace/(被忽略)
songs/<song>/reports/legacy/    无法定位到具体 session 的历史报告
songs/<song>/releases/          明确选出的交付版索引/音频/USTX
experiments/<类别>/             alignment pitch phonation evaluation misc …
benchmarks/model-comparisons/20261030-lyrics-alignment/
migration/20261030-reorganization/  本次整理的盘点表、映射表与验收记录
```

session 数：年轮 4、雨爱 32、最后一页 23（花海目录已建，当前无历史内容）。
每个 session 都有 `manifest.json`，至少含：`song_id / run_id / produced_date / produced_time /
primary_model / models / model_evidence / status / listening_status / original_paths / artifacts /
related_reports`。

### 年轮的四个 session

| session | 日期 | 内容 |
|---|---|---|
| `20261028__unknown-model__nianlun-from-scratch-20261028` | 2026-10-28 | v1 首版重制的脚本、逐句审查与产物 |
| `20261028__unknown-model__nianlun-from-scratch-v2-20261028` | 2026-10-28 | v2 重制的脚本、计划、复检记录 |
| `20261029__unknown-model__nianlun-v3-20261029` | 2026-10-29 | 早期 v3 尝试的 v3_stage*/v1*-v25* 脚本与日志（202 个文件） |
| `20261030__unknown-model__nianlun-from-scratch-v3-20261030` | 2026-10-30 | 本轮 v3：照源直描重制，含脚本、报告与验证数据 |

模型归属一律 `unknown-model`：历史脚本由谁写成没有原始日志或 manifest 佐证，按计划不按「谁写的」推定。

---

## 四、实际移动与 deferred

**已移动（tracked，`git mv`，635 个）**：脚本进 `sessions/*/scripts/`，报告/小件进 `sessions/*/reports/`；
通用研究进 `experiments/<类别>/`；无法定位 session 的报告进 `songs/<song>/reports/legacy/`。

- 移动前后 SHA 逐个记录在 `relocation-map.tsv`（`sha_before` / `sha_after` / `references_checked` / `status`）。
- 其中 58 个文件因引用改写内容变了（相对链接重算 + 根相对路径串替换），其余 577 个字节一致。

**deferred（本机大目录，不强搬）**：`runs/`（225 个目录、约 72GB）、`demo/`、`projects/`、`data/`、`models/`、
`external/`、`bridge/`。原因：run 内脚本与 manifest 含硬编码绝对路径、OpenUtau 工程与缓存有引用关系、
部分目录正被工具链使用；按计划「未验证兼容之前继续留原址，建索引和迁移映射」。它们已在
`inventory-before.tsv` 里逐目录登记（文件数、总字节、歌曲归属、风险=deferred），并在各 session 的
`manifest.json` 的 `original_paths` 里指向原址。

**保留原位（字节保护 / 契约依赖）**：
- `docs/knowledge/**`（377 个文件）：字节恢复到 HEAD，不改一字；
- 被知识包按路径+SHA 引用的公开文档（如 `docs/reports/yuai/*-feedback-*.json`、各类 `-index.json`）：
  必须留在 `docs/reports/` 下，否则 `src/agent2utau/knowledge.py` 的公开文档契约会拒绝加载
  （这正是首轮 16 个测试失败的原因，已定位并回退）。这些文档在 `songs/<song>/README.md`
  的「因知识契约保留原位的文档」一节被索引引用。
- `research/baishuo/**`（作者原件 + ZIP + manifest）、`docs/lastpage-*-20261008.md`、`*.ustx` 工程。

**未确定归属（uncertain-items.tsv，7 个，保留原址）**：`scratch/` 下正文与目录都无法确证歌曲归属的
多音字/编译试验脚本与 JSON（`check_polyphones.py`、`read_test_polyphones.py`、`check_phones_structure.py`、
`test_compile_phrase0*.py`、`test_polyphones.json`、`test_modified_phones.json`）。按计划不猜测归属。

---

## 五、验证命令与退出码

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python -m pytest -q` | **264 passed**（11.1s） | 0 |
| `python tools/repository/check_repository.py --worktree` | `{"audio_payloads":0,"author_projects":3,"zip_members":5,"skill_links":129,"checks":"passed","worktree_files":1568}` | 0 |
| `git diff --cached --check` | 无空白错误 | 0 |
| `git status --short` | 519 重命名 / 129 新增 / 129 修改 / 1 记录为删除但实为换位（`docs/reports/lastpage/author-interaction-feedback-20261012-comparisons.csv` → `songs/lastpage/.../reports/`，内容未丢） | — |

首轮 pytest 曾 16 项失败，全部指向 `knowledge.py` 的「公开文档必须在 docs/reports 或 docs/knowledge 下」
契约；已按计划把被引用的文档移回原位并恢复 `docs/knowledge` 原始字节，随后 264 项全绿。
未运行远端 CI（`ci.yml` 仅 workflow_dispatch 手动）。

---

## 六、.gitignore 调整

新增（均为新增目录的产物隔离，不放宽既有屏蔽）：

```
songs/*/sessions/*/workspace/     # session 的原始 run 数据
songs/*/releases/*.wav            # 交付音频（全局 *.wav 之外的显式声明）
benchmarks/**/local/              # benchmark 本地原始结果
experiments/**/workspace/  experiments/**/outputs/
```

全局音频（`*.wav` 等）、模型（`*.onnx` 等）与 `*.ustx` 屏蔽保持不变；作者原件例外
`!research/baishuo/projects/*.ustx` 保持不变（门禁核对 3 份作者工程 SHA 未变）。

---

## 七、残留旧路径的兼容方式

- 脚本内的绝对路径（`E:\project\agent2utau\...`）不变：文件换位不影响其运行对象。
- 少数脚本用 `scratch/xxx` 相对路径引用同批文件，已随移动改写为新路径（`relocation-map.tsv` 的
  `references_checked=path-string+relative-link rewritten` 标记了这 58 个文件）。
- 历史脚本按计划**不重跑、不改算法**；需要复现旧流程时，从 `songs/<song>/sessions/<session>/scripts/`
  取脚本，其对应的原始 run 仍在 `runs/` 原址（见 `manifest.json` 的 `original_paths`）。

---

## 八、提交与后续

- 分支 `chore/reorganize-20261030`，本地提交 `2b0ecf6`（Reorganize project into songs/experiments/benchmarks with lossless migration），
  工作树干净；**未推送**（按计划，未经明确要求不推送、不改写历史）。上游基线为 `34061cd`。
- 迁移工具与盘点数据留在 `migration/20261030-reorganization/`（`tools/` 为本次整理脚本，
  `inventory-before.tsv` / `relocation-map.tsv` / `uncertain-items.tsv` 为三张表，
  `verification_data.json` 为机器核对结果）。
- 本轮 v3 制作（2026-10-30 的年轮重制）也随之归入
  `songs/nianlun/sessions/20261030__unknown-model__nianlun-from-scratch-v3-20261030/`；
  它的原始 run 数据仍在 `runs/production/nianlun-from-scratch-v3-20261030/`（被忽略，未搬动）。
- 后续可选：待确认后把 `runs/production/nianlun-*` 等安全目录迁入对应 session 的 `workspace/`，
  并为仍留原址的目录加 NTFS junction（不提交 junction、不制造循环链接）。
