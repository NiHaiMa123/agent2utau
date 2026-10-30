# agent2utau 无损分类整理计划（2026-10-30）

> 给 MiniMax Agent 执行。**本轮只整理目录、文件命名、索引和必要的引用；不删除、覆盖任何已有文件；不重制歌曲、不改算法或声学结论。** 实际操作依据用户本机工作树，不仅依据 GitHub。

## 一、现状（已读取 main 的完整树）

截至 2026-10-30，Git 跟踪 **1439** 个文件：docs/ 720、scratch/ 378、research/ 210、src/ 45、skills/ 40、tests/ 25。docs/reports/ 中：lastpage 129、yuai 121、nianlun 12、production 59、maintenance 2。

目前 tests 已有 unit/contracts/skills 三类；scratch 大部分是《年轮》的多个版本的脚本、JSON、日志，且有很多只叫 v3_、v20_ 的文件，**不能单凭文件名认定所属歌曲/模型**。

AGENTS.md 记录 2026-10-29 本机约有 runs/ 72.6 GB、external/ 1.96 GB、models/ 870 MB、bridge/ 766 MB、projects/ 114 MB、demo/ 55 MB。**这些本机 ignored 内容在 GitHub 无法直接看到，执行时必须实地盘点。**

现有规范先读：docs/guides/repository-layout.md、songs/lastpage/reports/legacy/directory-reorganization-20261009.md、docs/workflow.md、AGENTS.md、README.md、.gitignore、.gitattributes、tools/repository/check_repository.py。

**特别注意：** 当前 .gitignore 排除 /projects/、runs/、demo/、data/、models/、external/、音频、*.ustx。research/baishuo/projects/*.ustx 是特殊放行的作者原件，禁止误动。projects/latest 在 Git 中没有跟踪文件，不能因此断言本机没有。

## 二、目标结构（每首歌有自己完整的制作索引）

~~~text
agent2utau/
├── README.md / AGENTS.md / plan.md / plan-table2.md
├── PROJECT_REORGANIZATION_PLAN_20261030.md
├── src/agent2utau/                   # 通用核心代码，暂不移动
├── bridge/OuBridge/                  # 原生桥，暂不移动
├── skills/singing-expression-editor/ # 已安装 Skill，暂不移动
├── configs/ / schemas/ / tools/      # 保留原有职责
├── tests/                            # 自动执行、有断言的测试
│   ├── unit/
│   ├── contracts/
│   ├── skills/
│   └── integration/                  # 真有集成测试时再创建
├── benchmarks/                       # 多个 AI 模型同题对比
│   └── model-comparisons/
│       └── 20261030-lyrics-alignment/
│           ├── README.md / protocol.md
│           ├── results/             # 小型对照记录
│           └── local/               # 被忽略的音频/原始结果
├── experiments/                      # 技术实验（不是成品翻唱）
│   ├── alignment/                   # HFA、GAME、ASR、字时钟
│   ├── pitch/                       # F0、PITD
│   ├── phonation/                   # VOIC/BREC/TENC/声线
│   ├── evaluation/                  # 独立评价/消融
│   └── misc/
├── songs/
│   ├── nianlun/                     # 年轮
│   ├── yuai/                        # 雨爱
│   ├── lastpage/                    # 最后一页
│   └── huahai/                      # 花海
│       # 每个 songs/<song>/ 同结构：
│       ├── README.md                # 中文名、制作时间线、版本索引
│       ├── assets/                  # 歌词和来源信息（非媒体）
│       ├── sessions/
│       │   └── <日期>__<AI模型>__<run-id>/
│       │       ├── manifest.json   # 制作时间、模型、状态、来源
│       │       ├── scripts/        # 本次特有代码（可跟踪）
│       │       ├── reports/        # 本次制作/审查小报告
│       │       ├── feedback/       # 用户试听反馈及其限定范围
│       │       └── workspace/      # 忽略：原始 run 数据/波形/工程
│       ├── reports/                 # session 无法确定的旧报告
│       └── releases/                # 明确选出的交付版索引/音频/USTX
├── docs/guides/ / docs/knowledge/    # 既有方法和知识包
├── docs/reports/                    # 公共研究、受保护历史例外
├── research/                        # 作者原件、表1/表2、历史证据
├── runs/ / demo/ / projects/        # 旧本机入口，兼容完成前保留
└── migration/20261030-reorganization/
    ├── inventory-before.tsv
    ├── relocation-map.tsv
    ├── uncertain-items.tsv
    └── verification.md
~~~

分类原则：

1. **正式翻唱**：以完成《某首歌》的 USTX/音频为目标的每次制作放 songs/<song>/sessions/<run>/；同一首歌的不同模型、不同日期、不同重做版本独立，不覆盖失败版本。歌曲 README 给出全历史索引。
2. **跨模型测试**：用户使用 Sol 6.1、Gemini 4、MiniMax M3.1F、DeepSeek V4.1F、Gemini 3.8 Flash 对歌词时间轴的比较，属于 benchmarks/model-comparisons；其单个模型生成的歌曲作品仍归 songs/，benchmark 只保留引用和对照结果，不复制整曲大文件。
3. **自动测试**：带断言、可重复运行的 pytest/契约测试归 tests/。临时 probe、诊断脚本不能因文件名有 test 就认定是自动测试。
4. **实验**：HFA 对齐算法、音高算法、发声参数、评估器的通用 A/B 研究归 experiments/。但某首歌的局部修订/试唱仍归该歌对应 session 的 scripts/reports。
5. **核心/研究**：src/agent2utau/evaluation 是生产级只读评价接口，不能挪到 tests；Skill、bridge、受 SHA 保护的 research/baishuo 和 docs/knowledge 等暂保留原位。
6. **不明确**：先不动原文件，填写 uncertain-items.tsv 并在对应歌曲 README 中链接，不猜测归属。

## 三、正式制作日期和 AI 模型的文件名规范

**对用户直接打开的交付文件**（工程 USTX、成品/试听音频、对照音频、最终报告）使用：

~~~text
<song>__<YYYYMMDD-HHMM>__<model>__<version>__<role>.<ext>
~~~

示范（下列模型 unknown 为示意，**不代表已经核实创作者**）：

~~~text
nianlun__20261029-time-unknown__unknown-model__v23__mix.mp3
nianlun__20261029-time-unknown__unknown-model__v23__vocal.mp3
nianlun__20261029-time-unknown__unknown-model__v23__project.ustx
nianlun__20261029-time-unknown__unknown-model__v23__delivery.md
yuai__20261018-time-unknown__unknown-model__F__report.md
~~~

- 日期必须是**制作发生日期**，不是后续上传 Git 的日期；有执行日志用原始日志，有制作报告用报告日期。只有日期没有钟点就写 YYYYMMDD-time-unknown；无日期写 date-unknown；不可由 Git 上传时间或 checkout 的 mtime 瞎猜。
- 模型 slug 建议：gpt-6.1-sol、gemini-4、minimax-m3.1f、deepseek-v4.1f、gemini-3.8-flash。**有原始日志、manifest 或明确用户记录才标该模型**；否则 unknown-model。多模型合作须在 manifest 中标每人角色，未知不硬归一人。
- 同名加版本/唯一 run-id，不自动覆盖。Windows 路径避免非法字符与过长路径；歌曲目录统一用 nianlun、yuai、lastpage、huahai，README 写中文歌名。
- **内部机器读取的 plan.json、manifest.json、.lab、缓存、pitch.json、音素文件和历史脚本**可保留原基础文件名；通过带日期/模型的 session 文件夹和 manifest 标识，不能为了表面命名把程序路径改坏。
- 作者原始素材、白烁研究 USTX/ZIP 不重命名，也不能冒充 AI 制作。

每个 session 写 manifest.json，最少字段：

~~~json
{
  "song_id": "nianlun",
  "run_id": "nianlun-v3-20261029",
  "produced_date": "2026-10-29",
  "produced_time": null,
  "primary_model": "unknown-model",
  "models": [],
  "model_evidence": [],
  "status": "historical_unverified",
  "listening_status": "unknown",
  "original_paths": [],
  "artifacts": [],
  "related_reports": []
}
~~~

强调：不能因为历史脚本由 Codex 写成，就自动标为 GPT-6.1 Sol；技术通过不等于歌曲听感被接受。

## 四、按仓库真实文件开展分类

### 4.1 scratch/ —— 第一优先

逐一扫描 378 个**已跟踪**条目的文件正文、导入、输出目录、run-id、报告链接，再分类；另盘点 scratch/ 下被忽略的音频。

- 如 scratch/audit_nianlun_*.py、scratch/build_nianlun_*.py、scratch/v3_stage*.py、songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/v20_pitd.py、scratch/v24_asr_*.py、scratch/v25_*.py 等，应依据代码引用的实际制作 run，分别放 songs/nianlun/sessions/<run>/scripts/；小型被跟踪的 JSON/日志应留在合理的 tracked 子目录或保留 legacy，**不能因搬到 ignored 的 workspace/ 就悄悄从 Git 消失**。
- 历史脚本不改算法、不重跑。为迁移后的活动脚本修复 repo-root 或相对路径引用；历史冻结脚本记录原工作目录和 E:\project\agent2utau 等原始路径，必要时提供兼容入口。
- songs/nianlun/sessions/20261029__unknown-model__nianlun-v3-20261029/scripts/_tmp.py、songs/nianlun/reports/legacy/asr_segments.txt、scratch/raw_inv_*.json、scratch/bs_*.py 等先查实际内容；不明者登记 uncertain。根目录 pelican-bicycle.html 也先查内容，不强塞某首歌。

### 4.2 docs/reports/ —— 歌曲报告集中

- docs/reports/nianlun（12份）、yuai（121份）、lastpage（129份）分别与 songs/<song>/ 对应。能确认是哪次制作的移动到 sessions/<run>/reports；否则进入 songs/<song>/reports/legacy 或**保持原位置并通过歌曲索引引用**。
- docs/reports/production（59份）先逐个识别：通用 Skill/评价方法报告留在 docs/reports/production 或 experiments；确实是某歌的制作报告才归该歌。
- **旧路径已有相对链接、JSON 引用、SHA 记录时不能盲搬**。普通可更新文档中的路径一起更新；字节保护的历史报告、docs/knowledge、research/implementation-records、docs/lastpage-*-20261008.md 默认不移动，使用索引+relocation-map。
- 不改历史报告的自评结果、不把 pending 改成 accepted。

### 4.3 本机 runs/、demo/、projects/、音频 —— 先盘点再无损移动

- 看实际目录与 Git ignore；一个 run 是一个 session，源目录与目标目录必须有唯一映射。旧 runs/production/<run-id> 若确认歌曲归属，目标为 songs/<song>/sessions/<session>/workspace/（保留 run 内现有相对结构）；纯通用实验归 experiments，跨模型比较归 benchmarks 的 ignored local。
- 只对**无运行中占用、无断裂引用风险**的目录实施同卷文件系统移动，并在移动前后核对文件清单及内容哈希；有关联的 OpenUtau 工程、manifest 固定路径、硬编码绝对路径、既有缓存/脚本，**未验证兼容之前继续留原址**，建索引和迁移映射，标记 deferred。
- 可考虑在确有必要且验证成功时保留旧本地路径的 NTFS junction，但不得覆盖已有目录、不得制造循环链接，不提交 junction 到 Git。不要迁移正在使用的 OpenUtau/bridge 安装、external、models 或研究作者原件。
- 用户当前在 OpenUtau 打开的 USTX 不可未经验证移动。projects/latest 和 demo 的文件可先按歌建立 releases/README 的索引；确认用途与引用安全后再移动/重命名。**不需要复制整曲音频来完成分类。**
- GitHub 上没有这些大型 ignored 文件，不能在报告中假装已经处理；执行只根据实际本机清单。

### 4.4 tests/、experiments/、benchmarks/

保留现有 tests 分类；只将真正可重复自动断言的脚本归 tests。新增 benchmarks/model-comparisons/20261030-lyrics-alignment/ 作为五模型实测的结构化记录入口：已知用户主观结果“GPT-6.1 Sol 与 Gemini 4 效果还行，其余模型歌词时间有问题”；详细输入、模式、日志、误差、成本等没有证据就写 unknown，**不造分数**。

## 五、MiniMax 必须按此顺序执行

**Step 0 — 盘点/保护**

1. 获取本机 git branch、HEAD、git status；未提交改动先列出，不覆盖，最好在独立 chore/reorganize-20261030 分支操作。
2. 同时盘点 Git tracked、非忽略新文件、ignored 的 runs/demo/projects/scratch 音频等；输出 migration/.../inventory-before.tsv。字段：old_path、tracked、size、sha256（可用时）、song、run、category、date、model、evidence、risk。
3. 对每一个打算移动的文件，先输出 relocation-map.tsv：old_path、new_path、action、reason、sha_before、sha_after、references_checked、status；未知归属单列 uncertain-items.tsv。
4. 验证受保护 SHA、可用磁盘空间、目标不存在、无正在运行的文件占用。大文件完整 SHA 可只对真正要移动者计算，但不能把没核实的标为 verified。

**Step 1 — 新分类骨架和索引**

创建 songs/<song>/README、sessions、reports、releases 入口，以及 experiments/、benchmarks/ 的说明。调整 .gitignore：**新 session 的 workspace/**、benchmark local/、实验大输出应忽略；scripts/reports/feedback/manifest 应仍可跟踪；保留全局音频/模型屏蔽和白烁 USTX 例外。用 git check-ignore -v 查实。

**Step 2 — 分批移动 tracked 小文件**

从 scratch 可确认归属的脚本开始，再处理安全的歌曲报告/实验。tracked 使用 git mv，保护文件保字节、重算 SHA。每批更新可编辑 README/入口相对链接，并核查 import、脚本调用、Git index；暂不能安全移动的保持旧址+登记，不为了清空旧目录强制动它。

**Step 3 — 大文件本机分类**

为旧 runs/demo/projects 全部建立 session/版本索引；仅搬安全可迁移内容，旧依赖需要兼容则先验证或留原址。**本步骤验收重点是完整分类/可追踪/零丢失，不要求强搬全部约 72 GB**。

**Step 4 — 运行验证**

~~~powershell
python -m pytest -q
python tools/repository/check_repository.py --worktree
git diff --check
git status --short
~~~

暂存后对 Git index 再执行不带 --worktree 的仓库发布门禁。测试缺模型/环境受阻写 blocked，不能称 passed。另确认 src、Skill 链接、CLI 帮助、保留的作者 USTX 和 ZIP SHA 不变，原 1439 个跟踪文件逐个都有新路径或明确原位映射，绝不能因 .gitignore 意外失去跟踪；新增文件另外统计。

**Step 5 — 交付**

完成 migration/.../verification.md：列出旧/新文件数、按歌 session 列表、能查证的日期和模型、Git tracked 与 local ignored 区分、实际移动与 deferred 清单、受保护 SHA、所有测试的命令/退出码、残留旧路径的兼容方式、分支与 commit SHA。整理操作用独立本地提交；**未经用户明确要求不强制推送或改写历史**。

## 六、严格禁止

- 不运行 git clean、git rm、rm、Remove-Item 等清理删除操作，不覆盖同名文件，不删除任何旧实验/失败版本。
- 不重新生成歌词/音高/渲染音频，不改生产算法与音乐质量结论。
- 不碰 research/baishuo 三份作者原件、ZIP、manifest 原始字节，不破坏现有 SHA/Skill 路径契约。
- 不猜测某个历史版本由哪个 AI 生产；无法确证写 unknown-model。
- 不为追求“所有目录搬空”而破坏硬编码路径、用户当前打开的工程或历史可复现性。
- **最终目标：歌曲→日期/模型→制作 session→脚本/工程/音频/报告能找到；自动测试与研究实验有独立区域；文件零丢失。**