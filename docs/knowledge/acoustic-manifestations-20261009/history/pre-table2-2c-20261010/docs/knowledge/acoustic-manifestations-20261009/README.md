# 表1：演唱表现记录、控制导航与既有响应证据

更新：2026-10-10。A–F本轮固定范围审查与正式整合已完成，状态consolidated_with_explicit_gaps。49个正式分层记录实体、30组多义听感词、48导航组及352具体参数/字段；复音/拍频另列1开放候选。所有测量方法、通用调参方向/剂量及自然度均未获全面验证。Agent没有试听，新音频/歌曲/Skill/安装未改。

现行机器入口为[knowledge-table.json](knowledge-table.json)，实体/组合词/导航CSV与它一致；[F报告](table1-consolidation-review.md)、[ID迁移](id-migration.json)、[上下文/任务字段](context-schema.json)说明正式范围。原31项/旧ID/旧来源及迁移前全部40文件原字节见[快照清单](history/pre-f-20261010/snapshot-manifest.json)。A–E报告保留阶段时态，以本入口和根目录计划为当前状态。

表2当前完成2A来源绑定与2B结构修订，schema 3。见[2B报告](table2-schema-review.md)、[字段说明](table2-fields.md)、[完整14行结构CSV](table2-record-structure.csv)、[迁移](table2-schema-migration.json)和[本轮审计](table2-stage-2b-audit.json)。旧F/2A产物为冻结时证据，现行3份表2及本入口已有新版本；原字段/报告/工程/Skill/旧run保留。26份更新前文档/脚本见[2B快照](history/pre-table2-2b-20261010/snapshot-manifest.json)，历史写入口有防覆盖guard。下一步2C未执行，不自动进入新合成/试听。

## 现行目录

| 文件 | 范围与边界 |
|---|---|
| [实体](atomic-manifestations.csv) | 24 ACO、15 EVT、9 PER、1 META。信号、时序、听感和元数据分层，不是49个声学标量/检测器 |
| [多义听感词](composite-descriptors.csv) | 30组DESC，两条候选分解及反例；非已验证中文同义/病因映射 |
| [控制导航](openutau-controls.csv) / [具体项](control-details.json) | 48 CTRL组→352 PARAM；当前/其它引擎/上游缺失/编辑数据分栏，组存在不等于本机生效 |
| [观测协议](measurement-protocols.json) | 49实体协议+1开放候选；10组有限数学检查，不等于真实PCM估计性能通过 |
| [描述覆盖](description-coverage.json) / [冻结问题](coverage-checklist.json) | 42问题、34可记录/8部分、16标签行/0完整测量结论；过程复查非音频留出，16正式实体未覆盖 |
| [既有响应](conditional-responses.md) / [JSON](conditional-responses.json) / [CSV](conditional-responses.csv) | 10干预、2关联、2技术审计；14记录类型引用已迁移，原值/反馈/SHA保持 |
| [控制响应覆盖](response-coverage.csv) / [项目证据](current-evidence.csv) | CTRL/EVID引用；有效/无效/副作用范围分开，不产通用配方 |
| [来源与定义](table1-source-review.md) / [逐说法](claim-evidence.json) | 30说法/25来源，B原阅读层级与摘要/范围缺口保持 |
| [本机能力](local-capability-review.json) / [偏好](editor-preferences-review.json) / [节点](graph-node-review.json) | 离线PE/固定源码路径；未读live值、模型/设备未执行 |
| [纠错](source-quality-correction.json) / [审计](table1-execution-audit.json) | E乱码为输出编码误判；原JSON正确，word295身份勘误保留；原基线和现行版本分别校验 |

## 表1能确认什么

定义、代码路径、输入/输出观测、描述覆盖和听觉标签分别记录。49项只是实体登记：ACO保存声明方法下的量，EVT保存支持与关系，PER保存原话/呈现/范围，META及CTX保存身份/音乐目标/监听/任务。没有证据的值保持unknown；信号平滑、相同RMS或固定vocoder输入都不能替代声线/发音/自然度验收。

控制导航只帮助查找实际PARAM字段，不承诺“哪个参数越大越好”。当前剂量的没区别不证明整个通道无效，局部可以不推广整曲，模型VOIC/BREC/TENC/SHFC不是人体量或听感的唯一解释。

## 仍需确认的范围

C：未读消费者、非默认执行、开放插件与本机版本差异；86冻结来源/六资源绑定不证明所有能力可用。D：真实F0、高F0共振、pulse jitter/shimmer、声源分解、语言边界、复杂响度/空间的方法性能。E：8部分表达项新增任务/关系字段仍缺实际标注，16实体未覆盖，严格等电平异谱和纯人声/混音成对听觉验证仍缺。B：摘要/范围来源与30组假设映射不升级。

原5位置标签及抱C局部接受保留，313字unknown不变。没有新的听觉标签、跨曲/留出验证或通用真假声/口型配方。后续按[表2专项计划](../../../plan-table2.md)先审计记录，再冻结新因果设计及人工试听；尚未执行。

## 重建与历史入口

现行重建使用research/table1-confirmation/build_stage_f.py；A–E构建器正式迁移后拒绝覆盖，原始资料从明确SHA快照读取。原上游源码、作者工程、发布工程、Skill及封存run不改。[研究构建说明](../../../research/table1-confirmation/README.md)、[当前计划](../../../plan.md)、[项目约定](../../../AGENTS.md)。
