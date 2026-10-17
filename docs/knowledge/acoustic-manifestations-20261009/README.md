# 表1：演唱表现记录、控制导航与既有响应证据

当前状态yuai_musical_design_rejected_process_audit_complete：2026-10-15用户整体否定独立雨爱v01质量并指出音高主体近乎平直；代码审计确认311非句尾单元被4/9c固定分派（carry实际2.2c）、280有限回收/19周期及75无组件，0–1600c主体期待允许平直通过。“逐字记录”不构成逐字音乐设计充分的证明。原技术核验保留，音乐设计未通过；冻结本轮脚本作为失败实现记录，下一步先整改源动作判断与主体局部验收/有限代表组试听，不直接批量重渲染。原工程/音频/Skill保持，本轮新模型/音频0；单Agent/CI仅手动。 见[反馈与流程审计](../../reports/yuai/design-process-rejection-20261015.md)。

2E技术交付封存时状态technical_execution_complete_pending_human_listening：用户明确授权冻结批次，两条件新A/S原生4组导出及抱32帧/只33帧5tick采样通过；8次新variance、16套固定种子acoustic/vocoder波形，另4套原生缓存技术波形单列。四路径/重复/两阶段speaker/原生DYN/固定1.5与0.7/PCM24独立检查通过，两个新A及新抱S分别与历史A/C的fresh输入、预测、raw PCM精确。53窗口与16次双F0观测只作有限代理，只的焦点早于波形起点，按协议保留整句并标未完整。72份分开上下文/焦点/两顺序对照衍生PCM待人工试听，154项本机测试通过；20快照/79生产与Skill及工程/67保护输入/1079旧封存路径/567当前歌曲run/47安装SHA保持。新反馈0、通用规律0，全部measurement_validated仍false；2E整体待听觉确认，2F–2H未执行。原歌曲、既有音频和Skill不改，单Agent、CI仅手动，下一步只接本批试听反馈，不自动扩展。见[实际执行报告](table2-stage-2e-execution.md)、[JSON](table2-stage-2e-execution.json)与[审计](table2-stage-2e-execution-audit.json)。

以下准备/静态/早期阶段叙述保留当时状态，不覆盖新批次。


当前2E历史实际输入/完整时钟、5tick采样重建及静态接入核查已完成，整体2E仍未完成。见[输入与静态核查](table2-stage-2e-native-check.md)：41实际音素/421与594帧，抱整数曲线及两路径采样与旧C精确，只的33帧为计划/IL重建；六组两阶段speaker、47资源SHA及三模型声明通过。55研究契约测试通过，无新原生导出/推理/音频/反馈。下一步有限执行前置项及明确授权的新批次；通过技术检查后人工试听。以下保留此前阶段范围。

当前2E研究接口准备已完成，整体2E未完成。[准备报告](table2-stage-2e-preparation.md)、[JSON](table2-stage-2e-preparation.json)及[审计](table2-stage-2e-prep-audit.json)为当前续项。A/S/D/P组装、独立检查器及有限批/惰性后端代码通过40项合成契约测试；47当前资源SHA精确，未运行真实模型、原生导出或音频。下一步实际native身份/5tick采样和后端接入核查，人工试听仍待新对照通过技术检查；原2D协议/审计及2C记录保持。

当前2D缺口审查及有限协议已冻结。[2D报告](table2-protocol-review.md)、[协议](validation-protocols/shfc-path-separation-v1.md)为当前续项：352 PARAM/49正式表现及1开放候选，单个SHFC路径分离设计、2条件/4路径/各两次，计划16套新波形，实际0套。D/P需要新研究接口，先实现独立检查器，不写生产原生工程。人工试听仍须在新对照技术核查通过后进行。2C文档/原审计原字节保持；2C写入口已guard，快照保留原脚本，以下各阶段叙述保留当时范围。

更新：2026-10-10。A–F本轮固定范围审查与正式整合已完成，状态consolidated_with_explicit_gaps。49个正式分层记录实体、30组多义听感词、48导航组及352具体参数/字段；复音/拍频另列1开放候选。所有测量方法、通用调参方向/剂量及自然度均未获全面验证。Agent没有试听，新音频/歌曲/Skill/安装未改。

现行机器入口为[knowledge-table.json](knowledge-table.json)，实体/组合词/导航CSV与它一致；[F报告](table1-consolidation-review.md)、[ID迁移](id-migration.json)、[上下文/任务字段](context-schema.json)说明正式范围。原31项/旧ID/旧来源及迁移前全部40文件原字节见[快照清单](history/pre-f-20261010/snapshot-manifest.json)。A–E报告保留阶段时态，以本入口和根目录计划为当前状态。

表2在2B阶段完成来源绑定与结构修订，schema 3；当前2C结果见下文。见[2B报告](table2-schema-review.md)、[字段说明](table2-fields.md)、[完整14行结构CSV](table2-record-structure.csv)、[迁移](table2-schema-migration.json)和[本轮审计](table2-stage-2b-audit.json)。旧F/2A产物为冻结时证据，现行3份表2及本入口已有新版本；原字段/报告/工程/Skill/旧run保留。26份更新前文档/脚本见[2B快照](history/pre-table2-2b-20261010/snapshot-manifest.json)，历史写入口有防覆盖guard。此为2B完成时状态，现行2C已收口，不自动进入新合成/试听。

当前表2已完成2A–2C记录确认并保留缺口，见[2C逐行报告](table2-record-confirmation.md)、[JSON/已确认及未知列表](table2-record-confirmation.json)、[CSV](table2-record-confirmation.csv)、[迁移](table2-confirmation-migration.json)与[审计](table2-stage-2c-audit.json)。14记录，60输入/预测数组只读数学重查；历史指标/反馈不升级为新测量或通用规律。上方2B及原F叙述保留阶段范围，旧原字节见[2C快照](history/pre-table2-2c-20261010/snapshot-manifest.json)。现行schema 3仅追加确认引用，原2B可精确恢复；下一步2D未执行，试听在2E。

新增当前关联入口：[表2补充统一索引](table2-supplement-index-20261012.md)、[结构JSON](table2-supplement-index-20261012.json)、[表1反馈案例CSV](table2-supplement-index-20261012-table1-cases.csv)。旧14主表保留；近8响应技术交付/追加反馈分别绑定，不推成通用规律。

制作使用[当前表2索引](table2-texture-listening-index-20261013.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近12系列/37行追加用户撤回衔接的更正，当前复用A/C质感试听待评；旧字段/SHA/阴性保持。

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
