# agent2utau

由Codex根据原曲观测和`singing-expression-editor` Skill判断演唱动作，独立设计音高与发声函数，编译OpenUtau工程，再检查实际输入和试听结果。原曲GAME、双F0、ASR、HFA提供观测；具体音乐身份、音素时钟、函数及未知范围由Codex判断。

## 目录与文件边界

生产、测试、研究和执行产物分开。完整的各环节、文件类型及存放规则见[目录规范](docs/guides/repository-layout.md)，迁移与验证见[整理记录](docs/reports/maintenance/directory-reorganization-20261009.md)。

```text
src/agent2utau/                      通用生产与独立评价代码
  audio/                            解码、分离、固定增益混音
  analysis/、transcription/          GAME/F0/歌词等原曲观测
  expression/                       显式表达函数与控制
  openutau/、resources/              原生适配、配置与资源检查
  evaluation/                       实际工程的只读评价
bridge/OuBridge/                     原生C#桥接源码
skills/singing-expression-editor/   Codex通用制作Skill及数学工具
tests/                              自动测试，独立于生产包
  unit/                             局部计算和边界
  contracts/                        编译/评价/隔离接口，原生依赖模拟
  skills/                           Skill函数与显示约束
tools/repository/                   仓库门禁和研究原件打包
configs/、schemas/                  通用配置、模板与数据契约
research/                           只读作者资料与历史实现记录
docs/knowledge/                     表1/表2、CSV/JSON知识及来源审计
docs/guides/、docs/reports/          方法规范与新的可读报告
projects/latest/                    指定保留/发布的USTX
runs/、data/、models/、external/     本机产物、输入、模型与依赖，Git忽略
```

[测试说明](tests/README.md)、[研究资料说明](research/README.md)、[文档索引](docs/README.md)、[维护工具](tools/README.md)、[工程管理](projects/README.md)分别说明用途。现有封存run、历史原始报告、Skill、三份发布USTX及作者原包保留；历史脚本搬迁只改变位置，原字节与SHA保留，旧路径由显式迁移记录追溯。

新任务按用途放`runs/production/<run-id>`、`runs/experiments/<run-id>`、`runs/research/<run-id>`等新目录。观测、工作谱面、设计、编译、原生输入/渲染、混音、评价、交付和反馈按[阶段规范](docs/guides/repository-layout.md#3-本机运行目录与阶段文件)分别保存。该规范由Codex选择具体`--out`实现，不表示CLI新增了自动编排；旧封存目录不重排。

## 当前任务与入口

当前**表1 A–F已按固定范围整合完成，确认缺口保留；表2已完成2A–2C记录确认，缺口保留**。现行清单登记49个分层记录实体、1个开放候选、30组听感词与48导航组/352具体项；14条第二层记录已迁移引用，40份迁移前文件原字节保留。D的50协议全部measurement_validated仍false；E的42项审查仍为34可记录/8部分，16标签行不等于独立试验。2A冻结17份现行文档，核对14条记录、52来源、五设计896条封存文件声明及67保护输入SHA；2B先冻结26份文档/脚本，14记录新增17比较/6反馈组，原字段及原实验保持；现行schema 3，旧F/2A审计保留历史范围。2C复核14记录的输入声明、历史指标与反馈，60输入/预测数组只读、823处指标字段来源对应；条件知识尚未确认。下一步2D缺口与有限协议冻结，尚未执行，不自动进入新合成或试听。

| 入口 | 用途与当前状态 |
|---|---|
| [plan.md](plan.md) | 唯一当前执行计划：A–F整合完成；关联表2已完成2A–2C、下一步2D，缺口保留 |
| [表1正式整合](docs/knowledge/acoustic-manifestations-20261009/table1-consolidation-review.md) | 49个分层实体、引用/ID迁移、上下文字段与纠错；记录结构不等于检测器 |
| [表1逐行审查](docs/knowledge/acoustic-manifestations-20261009/table1-review.md) | A当时的原31行拆分/迁移提案；正式去向与历史快照见F |
| [表1来源与听感词审查](docs/knowledge/acoustic-manifestations-20261009/table1-source-review.md) | 30条说法、31行定义、30组多义拆解与假设反例；逐项保留缺口，不宣称全部验证 |
| [表1具体控制审查](docs/knowledge/acoustic-manifestations-20261009/table1-control-review.md) | 352条具体项、偏好/预设/网格与扩展范围；本机缺失/未执行独立记录，机制核查不等于听感验证 |
| [偏好逐字段审查](docs/knowledge/acoustic-manifestations-20261009/editor-preferences-review.json) | 103字段/8嵌套属性；声明、固定源码引用、本机成员存在与live未知分栏 |
| [表1观测协议审查](docs/knowledge/acoustic-manifestations-20261009/table1-measurement-review.md) | 50条协议覆盖A47实体及3个B候选；10组数组只验证明列范围，未验证真实音频检测性能或自然度 |
| [表1描述覆盖审查](docs/knowledge/acoustic-manifestations-20261009/table1-coverage-review.md) | 42项冻结清单，34可记录/8部分；16候选未覆盖，反馈/音乐提问/研究任务/作者结构分别计数 |
| [表2专项计划](plan-table2.md) | 2A–2C记录确认完成且有缺口，2D–2H尚未执行；新因果试听按后续冻结范围 |
| [表2记录审计](docs/knowledge/acoustic-manifestations-20261009/table2-review.md) | 14记录的来源/比较/版本、有效_grid5路径与实际用户绑定交付；7差异/缺口，非新效果验证 |
| [表2结构修订](docs/knowledge/acoustic-manifestations-20261009/table2-schema-review.md) | schema 3、17比较/6反馈组、精确恢复迁移；2C复核结果另见逐行确认 |
| [表2逐行确认](docs/knowledge/acoustic-manifestations-20261009/table2-record-confirmation.md) | 14记录，输入数学重查/历史指标/反馈范围分开；36限定确认/24部分/56unknown，非通用规律 |
| [AGENTS.md](AGENTS.md) | Codex工作约定、来源边界、已有用户反馈及Git要求 |
| [表1：表现与控制清单](docs/knowledge/acoustic-manifestations-20261009/README.md) | 正式记录结构：49分层实体/1开放候选、30组组合听感、48导航组/352具体项；确认与验证缺口独立列明 |
| [表2：条件响应证据](docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md) | 已整理10条条件干预（5个实验设计）、2组观察关联、2项技术审计；有效、无效与副作用分别记录 |
| [控制覆盖与缺口](docs/knowledge/acoustic-manifestations-20261009/response-coverage.csv) | 逐类列出已有证据和待验证项，尚无跨曲泛化验证 |
| [Skill](skills/singing-expression-editor/SKILL.md) | 独立表达判断、函数设计与制作检查要求 |
| [执行流程](docs/workflow.md) | 环境、CLI、编译格式、原生依赖重算和验收边界 |
| [独立评价v0](docs/evaluation-v0.md) | 已有只读评价接口，读取显式输入与SHA绑定，不读取制作预期作真值 |

项目后续由当前Codex单个Agent处理，不启动多Agent或委派其他对话。进度写入根目录`plan.md`，README保持当前状态。旧独立评价计划已替换；`docs`中的既有评价、审查和实验报告保留为历史证据，其旧“下一步”不作为当前任务入口。

表1框架不等于已验证的异常检测器；测量响应不等于可感知改善。C机制核查与D测量协议均不能代替试听，E核对已有反馈，新的因果试听按表2后续冻结设计推进。已有证据尚不足以形成通用音色、口型或真假声配方。本轮没有生成新音频、修改Skill或发布歌曲工程。

F纠正两项旧判断：A因读错字段生成14条空关联，已补齐实际引用；E所称表2文字乱码实为工具显示编码误判，原UTF-8中文和反馈正确，未转码。原审查记录保留，见[纠错与原话绑定](docs/knowledge/acoustic-manifestations-20261009/source-quality-correction.json)及F报告。U17的word295身份勘误仍有效，unknown不变。

2A确认抱C的主试听对照为旧B，原A/F0参照分别保留；BREC有效工程/输入位于cohort明确的_grid5目录，旧1tick草稿继续封存。TENC的58项混合依赖与其它47项清单范围不同，当前外部模型/安装未重查。音频与数组仅核对字节SHA，未解码、声学复测或重听；记录绑定通过不代表隔离/指标/听感全部确认。F产物中的表2未执行是F完成时状态，当前以本入口和计划为准。

## 当前歌曲与试听结论

仓库保留三份最新发布USTX：

| 歌曲 | 工程 |
|---|---|
| 花海 | [huahai_plus4_smooth.ustx](projects/latest/huahai_plus4_smooth.ustx) |
| 最后一页 | [lastpage_loudness_v02.ustx](projects/latest/lastpage_loudness_v02.ustx) |
| 雨爱 | [yuai_skill_v17.ustx](projects/latest/yuai_skill_v17.ustx) |

这些是保留工程，不代表整曲演唱质量已验收。《最后一页》的已知结果：

- 1:27“果”、3:04“抱”有偏假/顶的反馈；1:33、2:56偏实。3:17“果”获局部可用反馈。
- 取消“抱”的TENC偏移没有听出区别；SHFC -400c初版更实但出现字头破音，未采用。调整进入时间后的“抱C”获局部“可以”，只保留该局部接受，尚未写入仓库发布工程。
- “果”SHFC -200c没有改善且引入响度下降，未采用；六条件BREC -10分开试听均“全部没区别”，均未采用。

完整条件、原话、数据与输入/交付SHA见[表2](docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md)及其原报告。Agent没有有效听音工具，听觉结论来自用户反馈；RMS、频谱变化、F0输入保持或技术检查不能代替听觉验收。

## 制作与评价流程

原曲观测 → Codex判断音乐与音素条件 → 选择动作及函数参数 → 显式全曲计划 → 原生编译与读回 → 当前依赖渲染 → 固定增益混音 → 独立检查与试听反馈。

改变音高、音素、声线或分句后，重建相关预测和实际输入，检查两阶段speaker、预测与人工发声控制、原生DYN、拼接及固定增益。保留source unknown。研究工程可用于学习条件和反例；独立制作不读取作者曲线数组、profile或旧曲参数来构造目标。

`src/agent2utau/workflow.py`提供原曲观测及显式函数编译，`bridge/OuBridge`使用实际OpenUtau Core导出与渲染；它们不替Codex选择动作。`research/implementation-records/lastpage-20261007/`中的脚本是已完成歌曲的实现记录，不能直接换曲名或常量作为新曲模板。旧cover、自动修复、候选搜索和参考曲线复制路线已撤出。

## 环境与命令

需要Python 3.11+及本机OpenUtau、声库/模型、ffmpeg、原曲观测和HFA依赖。仓库不携带模型；按[执行流程](docs/workflow.md)配置机器差异，`configs/local.yaml`不进入Git。

```powershell
python -m pip install -e .
agent2utau doctor
```

制作命令示例，使用本次任务的新目录及实际准备好的工程/计划：

```powershell
agent2utau observe-source "<原曲路径>" --out runs/new-source
agent2utau export-phonemes --project runs/new-score.ustx --out runs/phones.json
agent2utau export-pitch --project runs/new-score.ustx --out runs/pitch.json
agent2utau compile-functions --plan runs/functions.json --out runs/compiled
agent2utau render-project --project runs/compiled/project.ustx --out runs/native.wav --mixdown
```

上面是CLI参数格式示例，正式任务采用前述角色/阶段目录并按实际位置填写计划相对路径。观测不会自动生成歌词谱面或表达线，`new-score.ustx`和`functions.json`需先由Codex根据任务准备。独立只读评价入口为`python -m agent2utau.evaluation`，输入、SHA绑定和输出要求见[评价文档](docs/evaluation-v0.md)。

## 研究资料与文件管理

白烁三份原件《花海+4》《雨爱》《最后一页》及ZIP保持只读，见[资料说明](research/baishuo/README.md)和[SHA清单](research/baishuo/manifest.json)。工程结构和书面控制不证明未听过的声学标签，研究授权不等于曲线复制授权。

Git保留代码、Skill、文档、USTX及只含允许成员的作者工程包；不提交音频、模型、缓存、run产物、本机归档或绝对路径配置。已有本机音频和实验产物继续保留。旧路线清理见[记录](docs/repository-cleanup.md)，既有Git历史不改写。

代码检查在本机使用`python -m pytest -q`；当前工作树检查使用`python tools/repository/check_repository.py --worktree`，正式发布使用不带`--worktree`的索引文件检查，核对媒体排除、Skill引用、作者工程SHA和ZIP成员。检查通过只证明相应技术事项，不等于演唱自然度通过。

GitHub Actions的CI已停用，停止推送后自动运行及其失败通知邮件。本地`.github/workflows/ci.yml`仅保留`workflow_dispatch`手动入口，不随push、pull request或定时任务运行。后续测试由当前Codex在本机执行；如需恢复远端CI，先由用户明确授权。
