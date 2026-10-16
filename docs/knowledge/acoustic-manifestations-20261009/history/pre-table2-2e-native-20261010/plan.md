# 表1完善与确认计划

更新：2026-10-10。状态：A–F在固定范围内完成并保留确认缺口。F正式登记49个分层记录实体、30组组合词、48导航组/352具体项，另留复音/拍频开放候选；14条第二层引用已迁移，40份迁移前文件原字节保留。全部measurement_validated仍false，不宣称检测性能、通用调参规律或自然度通过。

当前续项：关联表2专项2A来源/版本绑定审计已完成，状态source_binding_audit_complete_with_explicit_gaps；2B记录schema修订已完成，状态schema_revised_with_explicit_gaps，2C记录复核已完成，2D缺口与有限协议冻结已完成，2E研究接口/独立检查器准备完成，真实执行/试听尚未进行。现行表2schema 3新增结构，原字段保持；F和2A冻结版本及原审计输出保留，不改写旧审查时态。

用户目标：优先完善并确认表1，为后续Codex判断演唱表现和选择控制建立可靠的描述基础。表1指[第一层总表](docs/knowledge/acoustic-manifestations-20261009/README.md)及其原子维度、组合听感、OpenUtau控制三份清单；[第二层](docs/knowledge/acoustic-manifestations-20261009/conditional-responses.md)提供已有实验的交叉核对，本轮不继续扩大调参实验。

本文件是根目录唯一当前执行计划，由Codex维护阶段状态和结论。旧独立评价计划已由本计划替换，其实现及实验结果以`docs`中的报告为历史证据；旧报告中的“下一步”不作为当前任务入口。

关联专项计划：[表2完善与确认](plan-table2.md)。该计划区分现有记录审计与条件响应知识验证，当前完成2A–2C记录确认及2D有限协议冻结，2E准备完成而真实渲染/试听尚未执行，2F及以后未执行；新的因果验证仍依赖相关表1定义、控制路径、观测方法与冻结协议，不因记录绑定通过而自动开展。

2B状态schema_revised_with_explicit_gaps：26份现行文档/脚本先冻结；14记录新增17比较/6反馈组，schema 3分清逻辑版本、文件槽位、预测/人工增量/最终输入/PCM及历史状态/后续反馈。旧JSON恢复等式、CSV旧列/14行结构CSV及Markdown原主体、52来源元数据/67保护输入SHA通过。见[2B报告](docs/knowledge/acoustic-manifestations-20261009/table2-schema-review.md)、[字段说明](docs/knowledge/acoustic-manifestations-20261009/table2-fields.md)与[本轮审计](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2b-audit.json)。2B完成时2C–2H未执行；现行2C收口结果另列，新因果试听仍在2D冻结设计后的2E阶段。

2B本地验证：88项pytest及工作树门禁通过（音频载荷0、三作者工程/五ZIP成员、102处Skill链接）；旧记录精确恢复与4历史写入口拒绝覆盖通过。6份生成产物重复构建精确，连同2份字段/报告文档共8产物SHA绑定；既有冻结拒绝覆盖。日志与测试临时目录在本批新ignored run，旧run不改。

2C状态record_review_complete_with_explicit_gaps：14记录复核完成，60份输入/预测NPZ只读、129实际读取绑定文件保持，823指标标量字段与原JSON/报告匹配。原生/fresh输入算术、支撑、通道、SHFC路径及重复输入/预测重查；20版本最终三通道由独立验证器重建检查。36项限定确认/24部分/56unknown逐项列明，不是新实验或普遍规律；旧2B与更旧记录可精确恢复。新模型/原生执行、PCM/mel/检测器数组读取、声学复测/试听均0，全部measurement_validated仍false。见[2C逐行报告](docs/knowledge/acoustic-manifestations-20261009/table2-record-confirmation.md)、[JSON](docs/knowledge/acoustic-manifestations-20261009/table2-record-confirmation.json)与[审计](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2c-audit.json)。此为2C完成时状态；后续2D进度另列，新因果试听在2E。

2C本地验证：88项pytest及工作树门禁通过（音频载荷0、三作者工程/五ZIP成员、102处Skill链接），26快照/52来源/67保护输入SHA、CSV/JSON/Markdown及旧2B精确恢复通过；9份生成产物重复构建精确，既有冻结与2B写入口拒绝覆盖。日志/TEMP/TMP在本批新ignored run，旧运行及审计不改。

2D状态gap_review_and_protocol_frozen_with_explicit_gaps：352 PARAM/48导航组与49正式表现实体/1开放候选逐项覆盖；14旧记录直接引用10个PARAM，其中3个有干预记录。冻结一个SHFC直接声学条件/预测组三通道分离协议：抱225与偏实只214，A/S/D/P四路径、各同输入两次，共计划16套波形/10组主对照，实际0套。D/P为研究反事实，现接口不支持，需先实现研究runner/独立检查器；不作USTX新旋钮或单通道病因。两个条件不是留出，相关测量仍未完整验证；果SHFC/BREC加量停止、接受抱C与旧阴性/unknown保留。23份更新前文档/脚本原字节冻结，现行2C产物及原审计不变。见[2D报告](docs/knowledge/acoustic-manifestations-20261009/table2-protocol-review.md)、[覆盖矩阵](docs/knowledge/acoustic-manifestations-20261009/table2-validation-gaps.json)、[有限协议](docs/knowledge/acoustic-manifestations-20261009/validation-protocols/shfc-path-separation-v1.md)与[审计](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2d-audit.json)。下一步2E先实现研究路径接口及独立检查器，绑定当前runtime/实际采样与隔离；本轮不渲染、不改歌曲/音频/Skill。新音频执行须按明确授权范围，人工试听在新对照技术核查通过后；2F留出/2G整句全曲/2H尚未执行。

2D本地验证：88项pytest、工作树门禁（399文件、音频载荷0、三作者工程/五ZIP成员、102处Skill链接）通过；352/50条JSON与CSV、表1引用、路径矩阵及有限预算独立核对。三种错误设计（扩大预算/伪称留出/把D当原生）拒绝；6产物重复构建精确，既有基线/协议封存及改剂量写入拒绝，23快照/67保护输入SHA保持。测试/TEMP/TMP和失败草稿在本批新ignored run。

2E准备状态research_interface_prepared_with_explicit_execution_gaps：冻结协议下的A/S/D/P研究组装、独立重建/裁剪/重复检查器、有限批接口及惰性ONNX后端已实现，40项合成契约测试通过。当前47项安装资源按已绑定登记表/配置实际路径重哈希均精确；不将字节一致当模型/分支/两阶段speaker执行通过。24份更新前文档/源码冻结，79生产/桥接/Skill/发布工程与67保护输入保持。真实native身份/5tick Q5采样、模型/声码器执行、PCM/DYN/增益及人工试听未执行；2E整体未完成，实际新波形/新反馈/通用规律均0。见[2E准备报告](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-preparation.md)、[JSON](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-preparation.json)与[审计](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-prep-audit.json)。下一步仍为2E：核查实际native身份/完整音素时钟/5tick Q5采样和后端接入依赖；新音频仅在明确执行范围内生成，并在技术门槛通过后人工试听。当前不改歌曲/音频/Skill，不启用自动CI；2F–2H未执行。

2E准备本地验证：128项pytest通过（88既有+40研究接口契约），本机工作树门禁通过（437文件、音频载荷0、三作者工程/五ZIP成员、102处Skill链接）。24快照、79生产/桥接/Skill/工程及67保护输入SHA保持，47安装资源当前字节一致；2产物重复构建精确、既有冻结及旧2D审计写入拒绝。测试/TEMP/TMP在独立新runs/test-results；原音频/旧run不写入，真实模型/原生/新音频/新试听均未执行。

## 当前执行进度

由当前Codex单个Agent执行。2026-10-10当前状态：

| 阶段 | 实际状态 | 结果与边界 |
|---|---|---|
| A | 结构审查完成 | 原31行逐项记录对象、混合问题、去向/理由、范围、单位/时钟、unknown和后续核查；提出47个分层实体引用，不是47个已验证检测器。见[逐行报告](docs/knowledge/acoustic-manifestations-20261009/table1-review.md)、[字段规范](docs/knowledge/acoustic-manifestations-20261009/table1-schema.md)、[CSV](docs/knowledge/acoustic-manifestations-20261009/table1-row-review.csv)。 |
| B | 逐项审查完成，确认有缺口 | 31行定义和30组组合词均有范围、候选分解/反例、证据状态或具体缺口；累计核对30条说法/25个来源页面。来源只支持组件事实，不证明中文词唯一病因或全部测量可用。摘要/范围级别、工程定义、待补资料与未验证映射明确保留。见[来源与逐项报告](docs/knowledge/acoustic-manifestations-20261009/table1-source-review.md)、[定义审查](docs/knowledge/acoustic-manifestations-20261009/core-definition-review.csv)、[听感词审查](docs/knowledge/acoustic-manifestations-20261009/composite-review.csv)与[逐说法记录](docs/knowledge/acoustic-manifestations-20261009/claim-evidence.json)。 |
| C | 固定范围审查完成，确认有缺口 | 48导航组已有352条字段/执行项（184+136+32，前320个ID保持），当前路线130、其它引擎39、上游/本机版本差异146、编辑元数据37，均非有效艺术旋钮计数。原44+25源码重查，编辑续审21份含4重复/17新来源，共86份唯一冻结来源；六资源与Core/App绑定不变。31节点、导出/播放/pan law及23项本机静态能力另列；新增103偏好字段/8嵌套属性分类及预设/网格实际写入、扩展接口范围。本机graph/masked、FX独立开关/WrapLive缺失，MergePhrasesSec/ReduceAnimations声明字段本机缺失；未读消费者/非默认执行/设备呈现保留unknown。见[控制报告](docs/knowledge/acoustic-manifestations-20261009/table1-control-review.md)、[CSV](docs/knowledge/acoustic-manifestations-20261009/control-details.csv)、[偏好审查](docs/knowledge/acoustic-manifestations-20261009/editor-preferences-review.json)、[节点](docs/knowledge/acoustic-manifestations-20261009/graph-node-review.json)和[本机矩阵](docs/knowledge/acoustic-manifestations-20261009/local-capability-review.json)。 |
| D | 协议审查完成，验证有缺口 | 原31行/A的47候选实体全部关联协议，另列B的shimmer、感知音高与复音/拍频，共50条。对象、输入、时钟/窗口、方法、单位、质量掩码、拒绝条件与来源/实现/验证分栏；11份生产/契约源码加1份研究验证器SHA绑定，10项组件来源另读。10组已知数组检查通过仅限明列数学/组件范围；全部measurement_validated仍false，真实音频估计性能及复杂方法未验证。见[协议报告](docs/knowledge/acoustic-manifestations-20261009/table1-measurement-review.md)、[CSV](docs/knowledge/acoustic-manifestations-20261009/measurement-protocols.csv)、[JSON](docs/knowledge/acoustic-manifestations-20261009/measurement-protocols.json)与[组件来源](docs/knowledge/acoustic-manifestations-20261009/measurement-source-review.json)。 |
| E | 覆盖审查完成，确认有缺口 | 42项清单在映射前冻结：18已有反馈/未知边界、12未录制音乐任务、8研究/方法条件、4作者结构；36主映射后复查6项，仅过程分区，非独立音频留出。34项限定结构可记录、8项部分表达；有已有用户标签16行（六BREC共一条原话），完整可靠测量结论0，链接34/50候选、16未覆盖。乐句/重音、转音/和声参照、情绪/听者任务及谐波旋律关系等缺口明确。冻结U17的word282误写由既有反馈纠正为word295，冻结原字节/分母/unknown保留；E关于派生文字乱码的判断由F纠正为工具显示编码误判，原记录不改。见[覆盖报告](docs/knowledge/acoustic-manifestations-20261009/table1-coverage-review.md)、[冻结清单](docs/knowledge/acoustic-manifestations-20261009/coverage-checklist.json)、[CSV](docs/knowledge/acoustic-manifestations-20261009/description-coverage.csv)与[JSON](docs/knowledge/acoustic-manifestations-20261009/description-coverage.json)。 |
| F | 正式整合完成，确认有缺口 | 49个分层记录实体（24 ACO、15 EVT、9 PER、1 META），1开放候选；31旧描述ID去向、30 DESC、48 CTRL/352 PARAM、来源/项目证据命名空间明确，14条RESP/OBS/AUD引用同步，原数值/状态/反馈及证据SHA保持。8组上下文/任务字段已定义，E的8部分项仍未补齐；16实体未覆盖、全部measurement_validated仍false。40份迁移前原字节/SHA保留，现行构建器与审计分开核对历史和当前版本。见[正式整合报告](docs/knowledge/acoustic-manifestations-20261009/table1-consolidation-review.md)、[ID迁移](docs/knowledge/acoustic-manifestations-20261009/id-migration.json)、[上下文字段](docs/knowledge/acoustic-manifestations-20261009/context-schema.json)与[纠错记录](docs/knowledge/acoustic-manifestations-20261009/source-quality-correction.json)。 |

六份原表/第二层历史基线SHA通过迁移前快照核对；F时文件另按F产物SHA核对；现行表2schema 3按2B产物SHA核对，F/2A旧版本从显式快照追溯。A旧提案读错atoms字段，实际字段为atomic_ids，14条空关联原先被误判有效；F已补齐真实引用并公开纠错。展开后的实体链接是结构候选，不表示这些对象均被测到。第二层去除新增迁移字段并还原legacy引用后，与迁移前JSON精确相等；原数值、状态、原话、工程/音频SHA保持。阶段记录见[执行审计](docs/knowledge/acoustic-manifestations-20261009/table1-execution-audit.json)。

D本地验证记录见执行审计：本批88项pytest与工作树门禁通过（音频载荷0、三作者工程/五ZIP成员、102处Skill链接），使用新workspace TEMP/TMP及pytest目录并绑定日志；旧失败/重试记录保留。新增协议CSV/JSON一致、源码/观测SHA及10组数组记录核对；67份保护输入SHA保持。反相数组相关首次精确-1断言因浮点误差拒绝，研究检查改用1e-12容差后通过；失败/重试保留，不修改生产算法。CI仅workflow_dispatch；未改歌曲、音频、Skill或安装。

E本地验证见执行审计：88项pytest、工作树门禁及67保护输入SHA通过；冻结清单/两阶段checkpoint/作者原件/历史报告与身份勘误均绑定，CSV/JSON一致。未读写音频、加载模型或改歌曲/Skill；CI仅手动。历史输入/PCM代理继续有效，但0项完整测量结论指本轮不能确认破音/实感等真值，不否定已核查数学量。

F本地验证：88项pytest与工作树门禁通过（音频载荷0、三作者工程/五ZIP成员、102处Skill链接），67份保护输入及40份迁移前SHA保持；176处文档链接、当前CSV/JSON、ID/来源与第二层原记录等式通过。6个A–E构建入口均拒绝覆盖、知识文件字节保持；现行15文件重复构建字节精确一致。验证日志在新ignored runs/research/table1-f-consolidation-20261010，使用新TEMP/TMP及pytest目录。首次guard核查子进程输出按Windows默认编码导致捕获解码失败；显式UTF-8捕获后通过，失败说明保留，未绕过guard或改生产代码。

F已完成正式整合。原JSON严格UTF-8解析且SHA与基线一致，1174字符串无替换字符/Latin1异常，10条反馈逐项与可读报告/CSV对应；E所称乱码是工具输出显示误判，没有对正确原文转码。E冻结原字节与U17 word295勘误保留。C未确认本机能力、D复杂测量、E历史上下文缺口继续unknown。

关联[表2专项计划](plan-table2.md)的2A已完成：先冻结17份F后现行文档，逐条核对10干预/2关联/2技术记录的原报告/输入/工程/反馈及交付SHA。原36来源保持，补列既有反馈/审计来源后52份来源文件核对通过；五设计896条封存文件声明、1079个唯一仓库路径与67保护输入SHA通过。音频/数组只流式计算字节SHA，未解码、复测F0、加载模型或试听。见[2A报告](docs/knowledge/acoustic-manifestations-20261009/table2-review.md)、[比较绑定](docs/knowledge/acoustic-manifestations-20261009/comparison-bindings.json)、[差异](docs/knowledge/acoustic-manifestations-20261009/table2-record-differences.json)与[2A执行审计](docs/knowledge/acoustic-manifestations-20261009/table2-execution-audit.json)。

2A公开7项差异/缺口：C-B与A-C比较角色、BREC有效_grid5版本、逐设计runtime范围、旧36来源索引缺列、BREC原话末尾句号、反馈时间/监听条件unknown及本次附加候选文件名纠正。TENC是58项混合依赖，只有6项与共享47项同名同SHA，另41项未在TENC该清单列出；其余四设计的历史47项相同。没有把当前外部模型/安装或新执行补成已验证。一个附加预设native_isolation.json不存在，实际guo相关来源按封存manifest绑定preservation_check.json，冻结原误写保留，不视为原实验丢失。

2A本地验证：新TEMP/TMP与pytest目录下88项测试通过，工作树门禁通过（音频载荷0、三作者工程/五ZIP成员、102处Skill链接），当前CSV/JSON一致、引用及快照/来源/67保护输入SHA检查通过；5份新审计产物重复构建字节精确相同。日志与逐文件字节检查在新ignored runs/research/table2-2a-record-audit-20261010，未改旧日志或完成清单。

下一工作仍为2E：实际native身份/完整时钟/5tick Q5采样与真实后端接入核查。新音频仅按明确执行范围生成，人工试听在技术核查后；研究接口准备不等于实际输入、模型或听觉验收。

试听衔接：C确认输入机制，不能确认可感知差别、改善或自然度；D定义测量也不能代替听觉结论。E回到已有问题/可用/无差别反馈核查描述覆盖，未听案例保留unknown。新的因果对照与人工试听按后续plan-table2.md的2E–2G冻结设计推进，不在本轮擅自生成音频。

B遗留确认项继续保留：摘要级全文及完整ISO算法未读、中文/非塞音入口、哭笑情绪、空间知觉、数字编码/伪影类型资料不足；趋势/连续性等工程定义待操作验证。30组映射和反例是显式假设，不是新音频标签或E独立覆盖样本。A47及B的shimmer/感知音高已正式登记，复音/拍频仍开放；旧ID含义由legacy字段与迁移前快照追溯。B“逐项审查完成”与“所有定义已证实”独立，后者未通过。

## 1. 要确认什么

最终交付应能回答：

1. 一段歌声发生了什么变化，应该用哪些维度、时间关系和听感词描述？
2. 每个维度具体指什么，和相邻维度有什么区别，什么情况下无法可靠观测？
3. OpenUtau的哪个具体入口有实际读取路径，改变的是音高、时钟、模型条件、波形增益还是后处理？
4. 相关说法来自声学研究、源码、实际输入检查还是用户试听？能确认到哪一层？
5. 当前框架还遗漏什么、哪些项需要拆分或合并、哪些机制不能用本机声库实现？

“表1确认”分为**定义与结构确认、软件机制确认、观测方法确认、样本描述覆盖检查**。它不自动包含调节方向/剂量有效、自然度改善或跨曲泛化；这些属于第二层及后续音乐决策、制作和验收。

不以“31项不增不减”作为目标，也不承诺有限简化指标能够无损描述所有波形或包办审美。目标是：明确研究范围，在范围内形成可追溯、可扩展的记录方法，并公开发现的遗漏和不确定项。

## 2. 当前基线与重点风险

计划编写时基线有31项描述维度、30组组合词、48类控制入口、9项项目证据、44份固定上游源码文件；默认表达名27个已被入口分组覆盖。F现行结构为49个分层记录实体、1开放候选，30组组合词、48导航组/352具体项及86份固定源码来源。这些数字**不是完整性或声学有效性的验收结果**；下列风险和基线保留计划编写时语境，现行状态以上方进度表为准。

| 当前待审问题 | 为什么需要处理 | 本轮处理方式 |
|---|---|---|
| “原子”未有统一拆分标准 | 维度可耦合，部分行同时包含测量、听感、成因或动作关系 | 先制定字段与拆分规则，再逐行保留/拆分/合并/移入组合层 |
| L1同时列电平和感知响度 | 两者单位、观测与解释不同；已有果实验说明平均电平不能代替听感 | 优先审查是否拆成独立字段或维度，明确各自成立范围 |
| 有声支撑、共鸣位置、起声协调等含多义描述 | 模型voicing、听感“实”与生理机制不能等同；动作时序也不等同单帧特征 | 区分声学观察、感知标签、模型条件、时序关系和生理解释 |
| 48类入口仍是汇总分组 | 一类可能包含多个参数、旗标、上下文或多个引擎；表达名覆盖不足以证明全部入口完整 | 新建可逐项追溯的具体参数清单，保留48类作为导航 |
| 上游支持与本机支持不同 | 已检查的官方提交不能自动代表本机Core或声库模型 | 本机版本/配置/读取路径与上游功能分栏，差异项保留unknown |
| 测量建议不等于有效检测器 | LPC、jitter、HNR等有条件限制；当前没有可靠嘴型/真假声/破音自动真值 | 每项写适用条件、失败条件和当前验证状态 |
| 来源ID与维度ID可同名 | 例如S1既可能指声源维度，也可能指文献；字符串检索会混淆 | 来源和维度使用独立命名空间/类型字段；记录旧ID迁移关系 |
| 总览混入具体剂量结果 | 来源层级不清时，会将局部实验误读成通用控制关系 | 表1保留机制和证据索引，完整条件响应留在第二层 |

### 基线绑定

计划编写时四个核心文件SHA256如下，原字节由F迁移前快照保留。现行版本已因正式结构迁移变更，SHA见table1-consolidation.json与执行审计；不得拿旧SHA覆盖现行文件，也不改写此历史基线。

| 文件 | SHA256 |
|---|---|
| atomic-manifestations.csv | `6a243754bc4d7f1c0aeca0a87486dc86b7cd88cbd5ea518c52f35b38f9c3d9d4` |
| composite-descriptors.csv | `202c7c56d3c50013906305b3c9b448dfbda42bd38ed15ea1d5707ffc09d01fc9` |
| openutau-controls.csv | `63cdc16fa0e2bd55719a48e58ed292bd2e6b16761055eb376f95e4ddf57e03e3` |
| knowledge-table.json | `c998b5ea4b39648a5703c5818455140d7dc932cbb40095199b5a7ca9739d0962` |

## 3. 执行顺序与每阶段验收

| 阶段 | 工作 | 产出 | 阶段验收 |
|---|---|---|---|
| A／P0 | 明确表1范围、实体类型、拆分标准和证据等级；审计原31行的混合/重叠/空缺 | 字段定义、逐行审查单、拟议拆并清单 | 原31行全部有去向与理由；不能为满足原子数而保留模糊项 |
| B／P0 | 逐项复核声学定义、组合听感词和实际测量限制；核对原始研究与适用范围 | 修订表现表、听感映射、逐说法来源记录 | 每个核心定义/机制主张有准确来源或标为工程提案；每个组合词允许多条解释与unknown |
| C／P0 | 从UI/USTX/表达/音符/音素/声线/配置/渲染/组装/混音/导出逐层枚举具体参数，核对实际读取路径 | 具体控制清单、引擎支持矩阵、路径/单位审计 | 每个入口分组有具体项；每个具体项有支持状态、类型、单位/范围、读取路径或明确未确认原因 |
| D／P1 | 为修订维度补齐观测定义、窗口/单位、边界情况；按需要用已知信号核查数学指标 | 观测协议、指标验证记录、限制清单 | 可测项有可复算定义；不支持可靠检测的项明确待验证，不能伪称已经实现 |
| E／P1 | 用独立准备的表现清单和现有绑定案例检查描述覆盖，检查漏项、多义词和跨字关系 | 覆盖矩阵、未覆盖/歧义案例、修订理由 | 每个审查案例能给出描述或明确缺口；不能把所有新现象随意塞进宽泛维度后宣布覆盖 |
| F／P0发布门槛 | 汇总A–E结论，更新第一层文件、关联第二层并审计引用/数值/哈希/ID | 表1新版、确认报告、迁移记录、待验证清单 | 无悬空引用、无未经证实的调节配方、来源层级清晰；所有未完成确认项单列 |

执行从A开始；A的定义和字段决定后再推进B/C，D/E根据修订表检查，最后F。P1不表示可以省略，只表示应在定义/入口清楚后开展。不要先采大量数据再决定每列究竟是什么。

### A：统一结构与拆分标准

每条表现维度至少包含：`ID；名称；实体类型；操作定义；包含/排除例；观测量；单位/时间尺度；相关但不同的维度；可能控制入口；证据类型与引用；确认状态；unknown规则`。

实体类型区分：

- 可测声学维度，例如F0、振幅包络、噪声/谐波、谱包络。
- 时间事件与关系，例如入口先后、转换、释放、跨音素承接。
- 感知描述，例如“假音感”“饱满”“顶”，可以由多个维度共同解释。
- 模型/编辑控制，例如VOIC、SHFC、DYN；它们是输入，不是声学表现。
- 生理或音乐解释；没有直接证据时保持假设，不能冒充测量事实。

若两项有不同观测对象、单位或时间作用，应考虑拆分；若是同一对象的不同程度/方向/时间值，优先作为同一维度的属性；若是多维组合、因果猜测或审美词，放入组合/解释层。耦合不等于重复；“不正交”本身也不构成删除理由。

原ID不静默改义。拆分/合并新增ID，旧ID标注迁移关系；第二层现有RESP/OBS/AUD关联同步校验，旧实验记录的原始内容和SHA保持。

### B：逐说法核对文献和听感词

优先复核：撕裂/粗糙/破音的区别、周期颤音与非周期抖动、饱满/实/假音感、气声与辅音摩擦、元音共振与谐波谱、响度与平均电平、发音/起声/跨音素衔接。

技术事实使用原始论文或官方资料，记录标题、作者/年份、DOI/URL、支持的具体说法、研究对象和限制。不能用“某论文讨论声质”支持整张表的完备性，也不能从人体唱法论文直接推出Yousa模型的调参方向。不确定或可能更新的事实需重新查证；确认本机机制以当前代码/配置/实际输入为主。

组合听感表补同义词、易混词、可能分解路径与反例。例如“颤抖”先区分F0、振幅、谱包络变化；“破音”保留声源中断、失真、数字伪影等候选；“假音感”不直接判人体M1/M2。无法由现有证据分解的词可保存原话并列出需要的观测，不能强行确定病因。

### C：把控制分组展开为具体参数

每个具体项至少记录：`参数ID；所属C分组；UI/USTX字段；引擎/声库/版本；有效条件；默认值/声明范围/合法范围；存储单位；原生变换公式；采样/插值/裁剪；读取者；variance/acoustic/vocoder/后处理作用阶段；需重算依赖；确认来源；状态`。

“所有可调项”拆成三种范围逐一统计：本机当前选用引擎/声库的可调项、其它已调查引擎的可调项、仅上游存在或本机尚未确认的项。显示/编辑辅助单列；若操作真正改变音符或其它输入，归入相应实际控制。48个分组数和27个默认表达名都不能代替这份具体项枚举。

优先排查：

1. PITD/音符基底/移调/颤音各字段及作用时钟；条件音高和输出目标音高分开。
2. DYN与轨道/混音增益；VOL、VEL与VELC各自引擎支持；时间包络与发声条件进入分开。
3. VOIC/BREC/TENC/SHFC/GENC/CLR及speaker，energy/falsetto启用条件，两阶段实际路径。
4. note/part/tempo、音素offset/覆盖/延音/AP/SP、phonemizer/语言/词表、上下文与分句。
5. 重采样器/旗标/oto包络、模型/声码器/步数/depth/种子、组装/导出、效果器及自定义表达。

关键单位与路径用现有原生检查记录交叉核对；必要时对显式绑定工程做最小读取/导出核查。没有读路径的UI项标“当前未生效/未确认”。不改发布USTX、不重新推理音频来填满支持矩阵。自定义旗标按已调查引擎及配置来源列出，不声称穷尽未来插件和任意第三方实现。

### D：确认“怎样观测”，不提前实现全部检测器

每项写清测量对象、输入要求、阶段/窗口、公式/估计方法、单位、质量掩码与不可判定条件。若存在实现，记录版本与实际完成的验证；只有建议时明确标“方法候选”。

对可精确控制的数学量，按需要使用少量临时已知信号验证：F0偏移、慢趋势、周期调制、振幅调制、瞬态增益变化、已知边界、削波与拼接。区分输入真值和估计误差，不将这些信号说成真实歌唱自然度正/反例；验证用音频不进入Git。

对高F0元音共振、气声/声源分解、次谐波、真实起声和听感响度等复杂项，优先核对方法成立条件及失败案例。方法不够可靠时明确保留unknown和验证缺口，不以简单阈值补齐“已确认”。已有双F0/短窗/谱数据只能确认它们实际测到的量。

### E：检查描述覆盖，避免自证完整

先从原始研究、用户已有描述及不同类型音乐动作独立编制审查清单，再映射修订表；不能只用表内31个词各举一例。案例至少包含稳定与变化、有意与异常、字头/腹/尾、低/高音、不同元音/辅音、同一字跨上下文、同电平异谱、纯人声/混音、单点与乐句衔接。

已有问题/可用/无差别案例均入表，并显式标角色。已有调参样本用于回归，不冒充留出验证。只有已绑定、已授权的材料进入研究；作者工程只作只读结构/条件例，不能凭工程文件推断未听过的声学标签。

每个案例记录：已知标签与来源、尚未知的事实、所需原子及时间关系、为何该映射有意义、是否需新增维度、无法表达之处。覆盖统计分别报告“可以用结构记录”“有可靠测量”“有用户标签”，不能混成一个通过率。设计新描述体系时保留一部分未参与修订的清单项作复查，报告其来源和角色；数量与取样范围在执行A/B后明确冻结。

检查合并/拆分是否真的解决遗漏；出现新现象时优先解释已有维度的适用性，不能靠“其它/残差”一栏将覆盖率推到100%。若确实需开放字段，保留案例、原因和待建定义。

## 4. 状态、交付与停止条件

确认状态按独立列填写，建议：`definition_checked；source_checked；current_engine_support；code_path_checked；measurement_defined；measurement_validated；description_coverage_checked；auditory_label_status`。每列允许已确认、部分确认、未验证、不适用；“全部字段已填写”与“全部事实已验证”分开。

最终文件在现有第一层目录更新，新增：

- `table1-review.md`：逐行问题、修订、结论与未完成项。
- `control-details.csv/json`：具体控制项及读取/作用阶段。
- `claim-evidence.csv/json`：逐说法的来源与证据层级。
- `measurement-protocols.csv/json`：观测定义、适用范围与验证状态。
- `description-coverage.csv/json`：独立案例映射、遗漏/歧义与unknown。
- `id-migration.json`：拆并映射；同步第一层/第二层引用，保留实验绑定。
- 更新README、原三份清单、knowledge-table及审计哈希；生成脚本同步，避免重建覆盖修订。

停止本轮并交付确认报告的条件：

1. 原31行、30组组合词、48类入口全部审查完毕，每项有确认状态、证据或具体缺口。
2. 修订后概念层级清楚，具体参数清单与分组关联可追溯；未生效/未支持项不混入当前有效控制。
3. 单位/范围/公式/时钟等确定性说法已核对，不能确定的项标明原因。
4. 覆盖审查公开案例角色、漏项与限制；无“所有好听难听已由有限指标证明穷尽”的承诺。
5. CSV/JSON/Markdown一致，引用与ID完整，原证据/工程/Skill绑定保持，相关仓库检查通过。

遇到资料不足，只暂停依赖该证据的具体确认项并继续其它项，最终列出需要什么资料或验证。该状态不升级为已通过，也不迫使本轮开展新合成。

执行遵循[Codex项目约定](AGENTS.md)、[当前Skill](skills/singing-expression-editor/SKILL.md)和[工作流程](docs/workflow.md)的来源、unknown与独立验证约定。本计划不恢复候选搜索、自动修歌或作者曲线复制；不修改通用Skill、歌曲工程或音频，不追加第二层因果实验。执行状态以上方进度表为准；后续由当前Codex单个Agent更新进度并关联具体审查报告，不启动多Agent。
