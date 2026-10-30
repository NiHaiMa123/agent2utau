# agent2utau 项目整理要求（第二轮收尾版 · 2026-10-30）

> **执行对象：MiniMax Agent。此文件已取代第一次“从零整理目录”的要求，按本版执行。**
>
> 核心目标：**少折腾历史，修复整理遗留问题，让歌曲制作、测试、实验、交付文件真正容易找到。**
>
> **用户最新决定：过去哪个 AI 制作了哪一版，不用追溯。所有历史会话的 unknown-model 原样接受；不要批量查询历史对话、Git 提交作者、工具日志来猜历史模型。** 从本轮要求生效后的**新制作**起，才严格记录日期、执行 AI 模型、版本和结果。
>
> **数据安全底线：不删除旧文件，不覆盖历史成果，不重新制歌，不调音高/声线，不删除失败的候选、被否决的反馈或原始实验记录。** 若无法保证无损和引用兼容，就保留原位置并建立索引。完成具体整理任务即可，不能因追求目录“绝对整洁”而无限重构。

## 0. 当前真实基线与边界（避免重复第一轮）

第一轮已有大规模整理，**不要再次批量执行旧迁移脚本**，也不要根据旧版计划中“scratch/ 378 个文件”重新移动一次。

2026-10-30 已核对 GitHub main HEAD：**7dcd9cd9780fb80d846baf01693e7cc18380d8b8**，Git tree 为 **1563 个跟踪文件**（不是旧验收文件声称的 1568）。主要现状：

| 项目 | 现状 |
| --- | --- |
| songs/ | 已有年轮、雨爱、最后一页、花海四个歌曲目录 |
| sessions/ | 年轮 4、雨爱 32、最后一页 23，共 59 个历史 session |
| scratch/ | 仅余 7 个无法确认归属的条目 |
| docs/knowledge/ | 377 个文件；相对第一轮前的 34061cd 基线有 17 个 Blob SHA 改变 |
| benchmarks/ | 已有 model-comparisons/20261030-lyrics-alignment 基本说明 |
| experiments/ | 已有 alignment、pitch、phonation、evaluation 等类别 |
| tests/ | 原 unit、contracts、skills 仍存在 |
| 本机大文件 | runs、demo、projects 等被 Git 忽略，第一轮 deferred；**这一轮不强制物理搬迁** |

原第一轮验收报告在 migration/20261030-reorganization/verification.md；旧文件移动映射在同目录 relocation-map.tsv。**两者保留作历史证据，不要覆盖/假装当时验收数据正确；新一轮报告独立保存。**

执行之前先读：README.md、AGENTS.md、docs/guides/repository-layout.md、docs/README.md、docs/workflow.md、第一轮 verification.md、当前 .gitignore、tools/repository/check_repository.py，以及真正涉及到的歌曲 README/manifest。

## 1. 本次必须做的事（按优先级）

### P0-A：复核知识包 17 个文件的改动，修复“声称未改字节”与实际不符

独立比较 34061cd（第一轮搬迁前）与**执行时当前 HEAD** 的 docs/knowledge/。上一轮核查发现 17 个旧文件 Blob SHA 改变；至少包括：

- docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md
- 同知识包 history/pre-table2-2a、2b、2c、2d 下的 conditional-responses.md 历史快照
- table2-DYN、TENC、entry-pitch、layering、texture-listening 等交付/反馈索引，以及 existing-listening-queue

**处理方法：**

1. 列出确切 17 项（如果当前 HEAD 又有新变更，以新 diff 为准），逐项判定：①仅换行符，②仅路径/相对链接调整，③正文数据/语义变化，④未能确认。提供旧 SHA、新 SHA、差异片段和处理结论。
2. history 快照、固定 SHA 的基线数据及保护文件：**原则上恢复第一轮前的精确内容（包括换行字节）**，不能因为修链把历史快照改成新版本。若该快照原本就有失效相对链接，记录为历史缺陷或从外部索引提供访问方式，不能重写历史。
3. 其他活动知识索引：仅在确认它们不属于 SHA 锁定的原始证据、且新链接确实正确并被使用时保留路径修复；否则恢复原始内容，并在独立可编辑的导航页维护指向新位置的链接。
4. **不能整包 git restore，不能回滚用户整理后新增的有效知识**。只处理经过比对核实的具体文件。若关联 docs/knowledge 的 manifest、knowledge.py 契约涉及路径/SHA，检查其完整性；修改路径必须有对应校验。
5. 注意 .gitattributes 规定知识包保字节：不要因为 PowerShell/编辑器默认换行模式导致 CRLF/LF 意外转换。
6. 更新新的审计报告，客观写明“哪些文件恢复原 SHA、哪些经授权保留调整”，不能再笼统写全部未修改。

**验收：历史冻结字节恢复一致，活跃知识库能通过原有契约测试，引用关系可检验，不修改声学实验结论。**

### P0-B：修复真正失效的 Git 文档路径

从当前跟踪文件生成 Markdown 链接/相对路径校验清单，区分：

- **Git 跟踪目标**：仓库中应该存在却被搬走，必须修复到新路径。
- **本机 ignored 目标**：例如 runs/...、projects/latest/*.ustx、音频；不要自动当成丢失，文档标注“仅本机存在/不随 Git 发布”，必要时给出 run 的 manifest 索引。
- **外部链接**：不做无关的互联网检查。
- **历史快照/冻结证据中的旧链接**：只登记，不以修复链接为由修改受保护的旧字节。

已确定至少一处：AGENTS.md 仍引用 docs/reports/nianlun/nianlun-from-scratch-v3-20261030.md 旧路径；应核实新位置后精确更正。

README.md 里指向 projects/README.md 和 projects/latest/*.ustx 的链接在 GitHub 上打不开，**这些工程原本是本机 ignored 文件**；应在入口文字说明“仅本机”或改为有效的歌曲 releases 索引，不强制上传 USTX。

当前根 README 长期把大量按日期记载的制作日志平铺在入口。**仅做轻量入口优化**：在顶部添加简洁的“歌曲制作 / 基准测试 / 实验 / 通用代码 / 文档”导航；历史日志信息保持可追溯，不要顺手删减或改写内容。必要时再把完整历史放独立 history 文档，但本次优先最小改动，不要因为美化 README 破坏其既有链接和旧引用。

**验收：所有应当可在 GitHub 打开的活动链接可解析；本机专属文件和历史快照例外明确分类。对仍未解决的链接列清单，不虚报为零。**

### P1-C：处理 Session 空壳/过度拆分，但不强制合并全部历史

实际 Git 端统计：59 个 sessions 中**23 个只有 manifest.json**；**54 个没有 scripts/**。没有脚本不代表空壳，很多是报告或用户反馈的记录，不能依照文件个数一刀切。

定义：

1. **Production Session（完整制作）**：一次真正创建或重做某歌的工程/run；其内可以有多个 v1、v2、v20 等迭代版本。
2. **Revision（同次制作中的改版）**：同一个真实 run 的调参、声学修正、试听反馈、单句修改；应在 Production Session 的 revisions/ 或 reports/feedback 下索引，而不是凭“每个日期+反馈”强建制作 Session。
3. **Experiment（方法实验）**：跨歌曲可复用或有明确对照协议的研究，归 experiments/；歌曲专属的小测试归其制作 Session 内的 experiments/ 或 revisions/。
4. **Legacy record（历史资料）**：只有报告/manifest、没有证据证明属于哪个主 run 的，可保留在 songs/<song>/reports/legacy 或旧 Session；**不必为了凑整洁强行推断归属**。

**重点是准确索引，而不是追求把 59 改成一个漂亮数字。**

- 遍历 23 个 manifest-only 的原始信息；如果已能从引用、run-id、报告直接确认它只是同一次制作的一个 Revision，可以统一到其主 Session 的 revisions/<revision-id>/。
- **原 manifest 必须完整留存**，例如迁移为 revisions/<revision-id>/legacy-manifest.json，并在新的索引映射记录原路径。源文件可以 git mv，绝不直接删除或只保留提炼后的摘要。
- 如果判断不出主 Session、需要挪动大批受 SHA 保护文件、或者迁移容易打断知识库，**保持原目录原文件，只将它标记为 legacy/reference-only**。这也是验收合格。
- 不批量给过去版本回填制作模型，不重命名所有历史 unknown-model 目录；历史名字存在不是问题。
- 每首歌 README 用更清晰的分类展示“主制作 / 局部修订与试验 / 历史记录 / 用户确认的交付”，并列出真正可定位的原始 run。不得把技术测试通过写成用户听感 accepted。
- 解决歌曲 README 中反复复制同一组 7 个 scratch 未归属文件的问题：这些全局未归属项应只在 migration/uncertain-items.tsv 或公共索引中说明；不要在每首歌都列一遍暗示属于该歌曲。

### P1-D：真正建立交付索引，而不搬动旧音频工程

目前 Git 中 songs/*/releases/ 下没有实际文件。由于全局 *.ustx、音频被忽略，**空目录本身不意味着错；问题在于用户找不到现有交付。**

- 给 songs/ 增加总入口 README.md，链接四首歌的 README、当前版本状态及对应的交付索引。
- 给各歌曲 releases/ 建立可跟踪的 README.md 或 manifest.json，包含：歌曲、run-id、明确交付版本、**现有**文件名/相对本机路径、文件类型、确认状态、有没有用户试听反馈、是否仅本机可见。
- 从已有报告、原始 run manifest、现存文件目录中确认版本；没有证据就标 unknown/未确认，**绝对不要把所有写着 FINAL 的 v20/v23 自动选为正式最佳版本**。
- 音频、USTX、模型仍放原本被忽略的本机目录。**这轮先索引，不要求移动几十 GB 文件，也不创建 junction，不复制相同音频多份。**
- releases/ 索引里不得放无意义的空记录占位；如果某首歌尚未交付就写“暂无已确认正式交付，候选见 sessions/”。

### P1-E：落实“未来”文件命名规则，历史不追溯

**用户最新要求：历史 AI 模型不用管。**

- 旧目录的 unknown-model、旧文件名、旧 manifest.models=[] 均**原样接受**，不要补模型、不翻历史日志、不按 Git 作者瞎猜；旧版日期也无需重新归因。
- **从新建任务开始**：每首歌制作统一落在 songs/<song>/sessions/<YYYYMMDD-HHMM>__<model-slug>__<run-id>/（运行原始数据也可以继续物理写 ignored runs/，但 session 要有索引/manifest）。
- 新交付物格式：<song>__<YYYYMMDD-HHMM>__<model-slug>__<version>__<role>.<ext>。model-slug 示例 gpt-6.1-sol、gemini-4、minimax-m3.1f、deepseek-v4.1f、gemini-3.8-flash。时间是该次制作产生时间（当地时间），不能拿推送时间冒充。
- manifest 记录 song_id、run_id、started_at/produced_at（含时区）、primary_model、models_with_roles（多模型时）、version、original_run_path、output_artifacts、status、listening_status、related_reports。**仅新任务强制记录完整；历史不迁就新 schema 重建。**
- 自动生成脚本/模板可以提供轻量实现，但必须优先保留当前 CLI、Skill 和 Windows/OpenUtau 的兼容性；禁止本轮为了新命名重写整个生产流水线。
- 如果本轮只整理、不制作新歌，不创建伪造的新制作 Session。

### P2-F：明确 tests、experiments、benchmarks 之间的边界

- tests/unit、tests/contracts、tests/skills 保留；只有具备受控输入、断言、可重复 pass/fail 的测试才放 tests/，不可把 production evaluation 代码挪出 src/agent2utau/evaluation。
- 第一轮未确定的 7 个 scratch 文件先看正文：若为通用音素/编译诊断，可归 experiments/alignment/ 或 experiments/diagnostics/；若依赖特定历史歌曲，保留原址/索引。**不能只看 test_ 前缀就迁到 pytest**。
- experiments/ 的 README 应列目前已有的真实实验入口以及用途，避免全部只是空目录说明；但是**不要为填充数量而复制数据或搬动受保护的研究项目**。
- benchmarks/model-comparisons/20261030-lyrics-alignment 保留为已有五模型主观对照记录，暂不追溯旧测试哪个 AI 产生哪版工程，**不填假的误差、成本或成功率**。
- 为以后跨模型测试定义统一 protocol（输入 SHA、任务范围、模型配置/思考档位、工具权限、预算、输出路径、时间轴误差口径、音频盲评/人工反馈）。如果没有新测试数据，只提供模板即可，**不自动开始模型测试**。

### P2-G：统一真正的目录说明，避免双规范冲突

目前 docs/guides/repository-layout.md 还是 2026-10-09 的旧约定，强调 runs/production、projects/latest 等，却没有明确 songs/、experiments/、benchmarks/ 的新入口。

- 以**当前真实实现**更新该规范，明确：
  - 生产通用内核仍在 src、bridge、skills；
  - 可提交的歌曲制作脚本/报告/索引在 songs/；
  - 大型音频、USTX、模型和原始 run 可继续本机 ignored 旧路径；
  - 自动测试在 tests/，方法实验在 experiments/，跨模型比较在 benchmarks/；
  - 受保护 research/baishuo、docs/knowledge、被知识契约绑定的 docs/reports 不受“按歌曲集中”的粗暴移动规则约束。
- README、docs/README、各歌曲索引跟随这一份规范；历史计划和历史验收报告保留作为时间点记录。
- 将本文件定位为**一次性第二轮收尾任务书**，后续常规制作以 docs/guides/repository-layout.md 作为长期规范。

## 2. 执行顺序与范围控制

1. **先盘点**：记录本机分支、HEAD、git status；从当前基线生成第二轮新增待办，不得复用第一轮旧扫描数据当“现在”。
2. **先修 P0**：知识包差异与活动文档失效链接。每一步进行具体 diff 和原有测试；遇到不确定的 SHA 依赖就暂缓，记录原因。
3. **再做 P1**：只合并证据明确的 Revision/空壳、更新歌曲 README、建立 releases/索引。对本机 72 GB 大目录只读核查/编制索引，不做高风险物理移动。
4. **最后 P2**：完善分类导航、未来版本的 manifest/命名模板和长期目录规范。
5. 本轮改动优先为**文档/索引/必要路径修正**。不升级包、不改核心算法、不触发 OpenUtau 渲染、DiffSinger、F0/ASR 再分析。
6. 若旧代码引用确实要修改，逐一说明原因并进行直接测试，禁止脚本扫描后全局替换所有字符串。
7. 尽量在独立 chore/reorg-phase2 分支提交；不 force push、不改 Git 历史、不清理原文件。用户之前的工作树有未提交修改时先保护，不能用覆盖式 checkout 抹掉。未经授权不主动推送执行分支。

## 3. 必须做的验收（结果必须区分“本机实测”和“Git 文件静态检查”）

建议运行：

~~~powershell
python -m pytest -q
python tools/repository/check_repository.py --worktree
git diff --check
git status --short
git ls-files | Measure-Object -Line
~~~

测试环境缺模型/依赖时明确 blocked，不可伪报 passed；若使用 TEMP/TMP 等测试临时目录，确保不会覆盖既有 production run。仓库门禁默认 indexed 模式在暂存后可另执行。

额外的独立检查：

- **第一轮结束时的 1563 个 tracked 文件**（以 7dcd9cd 为参考）必须都有当前路径或明确无损新路径映射；本次新增文档另计。旧文件的字节若改变，必须解释原因；不能用“Git 认为是 rename”代替内容校验。
- P0 知识包 17 项逐项有 diff、判定和最终 SHA，尤其历史快照应满足冻结约束。
- 核查 Git 中活动 Markdown 链接、明示 ignored 本机链接、历史冻结链接分别输出统计；不以“0 坏链接”掩盖 Git 里原本不可能打开的本机音频。
- 被知识库按路径+SHA 引用的 public report 必须保持加载契约；研究作者三份 USTX + ZIP 字节/SHA 仍然一致。
- 每个歌曲有 README + releases 交付索引；模型旧版仍 unknown 不算缺陷，未来新版本有明确模型名。
- Session 合并后的旧 manifest 原始内容能在新位置找到，不能造成用户历史数据、被否决版本或试听记录丢失。
- Git 中不得出现新的真实歌声音频、完整原始缓存、模型权重、密钥或内部环境配置；不可把 ignored 文件强制 add。
- 只有验收完实际运行才写 264 tests passed 等数值；报告不能沿用第一轮 1568 的过期计数。

## 4. 交付物与报告模板

新增第二轮验收目录（不要覆盖第一轮）：

~~~text
migration/20261030-reorganization/phase2/
    README.md
    knowledge-diff-audit.md        # 17 项与最终处理
    links-audit.md                 # Git/本机/历史分类，已修与未修
    session-consolidation.tsv     # old_path、new_path、理由、SHA、状态
    release-index-audit.md        # 交付索引和本机可用性
    verification.md               # 命令、退出码、具体验证结果
~~~

报告至少给出：

- P0/P1/P2 各项 done / deferred / blocked 及原因。
- 文件总数、移动数、修改数、历史保护 SHA、活动链接验证结果。
- 59 个历史 Session 处理前后数量（可不减少）、哪些 revision 被整理、哪些保持旧址。
- 四首歌的交付索引与各自本机工程关联（没有已确认交付就说没有）。
- 代码/知识契约/仓库门禁真实测试记录；未运行的绝不写通过。
- 分支、commit SHA、是否 push、工作树状态。

## 5. 成功标准（用来防止 MiniMax 过度工作）

**不是**：旧 unknown-model 全变成准确模型名、59 个目录强行合成 4 个、72 GB 全搬到 songs、测试工具跑出一大堆漂亮数字。

**而是**：知识库字节和引用可信，活动文档不再断链，歌曲历史容易按制作/修订/交付检索，旧文件完全保留，测试和实验分区明确，**新制作从此自动按日期 + AI 模型管理**。

完成这些后停止，不要继续为目录美观重构音频生产算法。
