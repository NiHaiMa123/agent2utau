# 目录边界与各环节文件存放规范

更新：**2026-10-31（自动音高新路线）**。本文是**长期规范**；当前执行计划为 [根目录 plan.md](../../plan.md)。旧表1/表2及旧目录整理计划已归档到 [docs/archive/legacy-plans/](../archive/legacy-plans/)，不再执行；历史迁移的验收文件继续保留。

## 0. 一句话

生产内核仍在 `src`／`bridge`／`skills`；**可提交的歌曲制作脚本、报告与索引在 `songs/`**；大型音频、USTX 工程、模型和原始 run 仍在本机被忽略的旧路径；自动测试在 `tests/`，方法实验在 `experiments/`，跨模型比较在 `benchmarks/`。

## 1. 顶层职责

| 目录/文件 | 保存什么 | 不放什么 | Git |
|---|---|---|---|
| 根目录 README、AGENTS、plan | 当前执行入口；旧 plan-table2 和目录整理计划根路径仅用于兼容跳转 | 旧音高路线、新实验音频 | 提交 |
| src/agent2utau/ | 通用生产、原生适配与独立评价；`alignment/` 为**待新增**模块 | 歌曲脚本、作者控制数组 | 提交 |
| bridge/OuBridge/ | OpenUtau 原生桥接 C# 源码 | 歌曲输出、测试 fixture | 提交源码；bin/obj 忽略 |
| skills/singing-expression-editor/ | 通用制作 Skill、参考方法、函数工具 | 具体歌曲参数/路径配置 | 提交 |
| tests/ | unit、contracts、skills 自动测试 | 生产入口、真实录音、作者数组 | 提交 |
| tools/ | 仓库门禁等维护工具；会话脚手架 | 已完成歌曲制作脚本 | 提交 |
| configs/、schemas/ | 通用默认值、USTX 模板、可读契约 | 模型权重、机器绝对路径 | 提交（local.yaml 忽略） |
| **songs/** | **每首歌的制作索引、session 脚本/报告、交付索引** | 大音频、模型、原始 run 缓存 | 提交（workspace 忽略） |
| **experiments/** | 跨歌曲可复用或有对照协议的方法实验 | 某首歌的局部修订/试唱 | 提交 |
| **benchmarks/** | 跨模型同题对照的协议与小型结果 | 整曲大文件、原始日志 | 提交（local 忽略） |
| **migration/** | 目录迁移的盘点表、映射表、验收记录 | 生产资产 | 提交 |
| research/ | 只读作者资源、表1/表2复核、历史实现记录 | 默认生产配方、运行输出 | 提交允许的原件/文本 |
| docs/guides/ | 使用说明、**本规范**、方法文档 | 实验 PCM、模型输入数组 | 提交 |
| docs/archive/ | 废弃计划与旧 README/AGENTS 原文快照，只读 | 当前执行任务 | 提交 |
| docs/knowledge/<包名>/ | 表1/表2、CSV/JSON 知识清单与来源审计 | 未标角色的作者数组 | 提交必要文本 |
| docs/reports/<主题>/ | 公共研究、维护报告、**被知识契约绑定的公开文档** | 可直接运行的旧曲脚本 | 提交 |
| projects/latest/ | 用户指定保留/发布的 USTX | 测试谱面、音频、模型 | 仅本机 |
| runs/ | 本机 run：观测、设计、编译、渲染、评测、交付 | 当作新任务输入的缓存 | 整目录忽略 |
| data/、models/、external/、demo/、.local-archive/ | 本机资料、权重、依赖、试听、旧路线归档 | 新工作默认入口 | 整目录忽略 |

## 2. 歌曲制作：songs/ 的结构与规则

```text
songs/<song>/
  README.md                  # 中文歌名 + 主制作/局部修订/历史记录/交付 四类索引
  assets/                    # 歌词与来源信息（非媒体）
  sessions/<日期>__<模型>__<run-id>/
      manifest.json           # 该次制作的索引（见第 5 节）
      scripts/                # 本次特有代码
      reports/                # 本次制作/审查小报告
      feedback/               # 用户试听反馈及其限定范围
      workspace/              # 忽略：原始 run 数据/波形/工程
  reports/legacy/            # 无法定位到具体 session 的历史报告
  releases/README.md         # 交付索引（本机路径 + 逐条确认状态）
```

- `<song>` 用 `nianlun`／`yuai`／`lastpage`／`huahai`，README 写中文歌名。
- **session 命名**（仅新任务强制）：`<YYYYMMDD-HHMM>__<model-slug>__<run-id>`，模型 slug 取 `gpt-6.1-sol`／`gemini-4`／`minimax-m3.1f`／`deepseek-v4.1f`／`gemini-3.8-flash`。
- **交付物命名**（仅新任务强制）：`<song>__<YYYYMMDD-HHMM>__<model-slug>__<version>__<role>.<ext>`，role 取 `project`／`vocal`／`mix`／`report`。
- 历史上写 `unknown-model` 的 session **保持原样**：没有原始日志或 manifest 就不追溯模型归属，不按 Git 作者猜。
- 一次制作里的改版（调参、试听候选、单句修改）放该 session 的 `revisions/` 或 `reports/`，**不要**每个日期/每次反馈都新开一个 session。
- 跨歌曲可复用的实验归 `experiments/`；只有报告、没有脚本产出的历史资料放 `reports/legacy` 或标 `legacy/reference-only`。

## 3. 本机 run 与 session 的关系

原始 run 仍可物理写在被忽略的 `runs/production/<run-id>/`（或 `experiments/`、`research/`），此时 session 负责**索引**它：`manifest.json` 的 `original_run_path` 指向真实目录。
只有在**无引用风险**（没有硬编码绝对路径、OpenUtau 工程/缓存引用、正在使用）时才把 run 目录搬进 session 的 `workspace/`；搬动前后核对文件清单与哈希。`projects/latest`、`demo/`、`models/`、`external/`、声库安装目录不搬。

## 4. 文件类型与角色

| 类型 | 位置 |
|---|---|
| .py/.cs 通用逻辑 | src、bridge、tools；Skill 通用数学脚本仍在 Skill 目录 |
| test_*.py 及测试辅助 | tests 的相应类别；**仅当有受控输入、断言、可重复 pass/fail**；临时 probe 不因名字带 test 就进 tests |
| .yaml 通用默认/模板 | configs；绝对路径配置仅 local.yaml |
| .json/.csv 知识与规则 | docs/knowledge，必须标来源、证据层级、unknown 和版本 |
| .json 运行 state/实际输入/.npy/.npz | runs 或 session 的 workspace，不能因是文本 JSON 就提交完整 run 输出 |
| .jsonl/.log 执行与事件记录 | run 的 evaluation/feedback/logs；可读结论提取至 docs/reports 或 session/reports |
| .md 方法/计划/报告 | 根目录计划、docs/guides、docs/reports、songs/*/sessions/*/reports |
| .ustx Agent 工作/候选 | runs/ 或 session workspace；只有指定发布版进入 projects/latest 或 releases 索引 |
| .ustx 作者原件及授权 ZIP | research/baishuo，逐字节只读、SHA 核对 |
| .wav/.mp3/.flac 音频 | 本机 data/runs/demo，**所有目录均禁止上传 Git** |
| .onnx/.pt 等权重 | 本机 models/external/安装声库；不提交 |

每个文件的角色以来源/绑定为准，不能只看扩展名。**技术测试通过 ≠ 用户听感接受**；交付状态必须写明是"已确认"还是"未确认"。

## 5. manifest 字段（新任务强制；历史不追溯重建）

```json
{
  "song_id": "nianlun",
  "run_id": "<run-id>",
  "session_id": "<YYYYMMDD-HHMM>__<model-slug>__<run-id>",
  "started_at": "2026-10-30T09:00:00+08:00",
  "produced_at": "2026-10-30T13:30:00+08:00",
  "primary_model": "minimax-m3.1f",
  "models_with_roles": [{"model": "minimax-m3.1f", "role": "画线与复检"}],
  "model_evidence": ["原始执行日志路径或用户明确指定"],
  "version": "v3",
  "original_run_path": "runs/production/<run-id>",
  "output_artifacts": [{"path": "…", "kind": "ustx|wav|md", "local_only": true}],
  "status": "candidate|accepted|rejected|historical_unverified",
  "listening_status": "unknown|partial|confirmed",
  "related_reports": ["…"]
}
```

`produced_at` 用该次制作的**产生时间**（含时区），不得用推送时间冒充。多模型协作要在 `models_with_roles` 写清每人角色，未知不硬归一人。

## 6. 受保护区域（不参与"按歌曲集中"的移动规则）

- `research/baishuo/**`：作者原件、授权 ZIP、manifest，逐字节只读，SHA 核对。
- `docs/knowledge/**`：知识包快照与固定 SHA 基线。**历史快照的失效相对链接只登记、不重写**；链接修复放在可编辑的导航页。
- 被 `docs/knowledge` 知识包**按路径+SHA 绑定**的公开文档必须留在 `docs/reports/` 下，否则 `src/agent2utau/knowledge.py` 的公开文档契约拒绝加载。
- `docs/reports/<主题>/` 下被知识契约绑定的文件同理。

## 7. 测试、实验、评测的边界

- `tests/unit`、`tests/contracts`、`tests/skills` 保留；只有具备受控输入、断言、可重复 pass/fail 的脚本才进 tests。
- 生产评价实现留在 `src/agent2utau/evaluation`（供实际工程使用的通用只读功能），**不挪到 tests**。
- `experiments/` 放方法实验与对照；某首歌的局部修订留在该歌 session。
- `benchmarks/model-comparisons/<日期>-<主题>/` 放跨模型同题对照：`protocol.md`（输入 SHA、任务范围、模型配置/思考档位、工具权限、预算、输出路径、时间轴误差口径、盲评/人工反馈口径）、`results/`（小型对照记录）、`local/`（忽略的原始输出与音频）。没有新数据就只提供模板，**不填假的误差、成本或成功率**。

## 8. 其它约定（沿用）

- `docs/workflow.md`、`docs/evaluation-v0.md` 与封存历史报告保留原路径。
- `bridge/out*` 与 `bin/obj` 是 ignored 构建产物，保留已部署/绑定路径，不重新部署或搬动本机安装。
- 测试默认用 pytest `tmp_path`；需要真实路径时用全新的 `runs/test-results/<run-id>`，禁止指向已有任务/封存目录。
- 仓库发布门禁：`python tools/repository/check_repository.py --worktree`（暂存后再跑一次不带 `--worktree` 的 indexed 模式）。
