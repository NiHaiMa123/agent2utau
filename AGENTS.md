# agent2utau 当前工作约定

## Codex与当前计划

- 2026-10-16当前流程更新 `phrase_by_phrase_skill_workflow_updated`：按用户要求改为一个完整音乐句观察/逐字构思/前置意图/画线/原生与主体及跨字图审/成声检查做完，再推进下一句；保存逐句进度，试听状态独立，不逐句等人工批准。整曲最终只组装已审阅目标；独立入口/主体/退出主张拆检，不让一个入口代表全句。7份Skill资源更新并同步安装，40文件一致/124引用/结构核查通过；当前工具仍无逐句先后自动门禁。雨爱工程、音频、旧锁与receipt保持，本轮不继续歌曲。见[逐句流程更新](docs/reports/production/skill-phrase-workflow-20261016.md)。单Agent、CI仅手动。下一制作任务按新流程逐句执行，旧通过不倒填。

- 2026-10-16续项完成：状态 `yuai_G_whole_candidate_delivered_pending_listening_with_process_gap`。Skill已补直接检索表1/表2与后续阴性/反馈、词/核映射，39份安装一致、117链接及9本机测试通过。当前源独立G方向全曲53句/371元音/382阶段，61组原生成声与两阶段实际输入核对、371/371实际图审完成，新260.48秒纯人声及v03候选工程已交付。技术完成；s13冻结到达检查失败保留，严格流程false，末将/虹深回探及2:46短吸偏低电平列试听重点，整曲听感unknown。只取公开经验，无作者/历史制作载荷，未启用CI，单Agent。见[整曲候选报告](docs/reports/yuai/source-intent-G-whole-candidate-20261016.md)。下一步接本版整曲反馈，不自动扫参。

- 2026-10-16本轮续项：已把表1/表2检索直接写入Skill主入口，补检索覆盖/后续反馈/阴性和副作用、知识与历史制作载荷边界，以及源词/辅音/元音核映射检查；39份Skill文件安装一致、117引用与9项本机知识契约测试通过。门禁仍不自动证明检全/应用正确；见[Skill更新](docs/reports/production/skill-knowledge-entry-20261016.md)。当前继续雨爱G方向的整曲候选：53句新意图已前置冻结、371元音/382音乐阶段的当前谱面与原生核对已完成，完整成声/整曲听感尚未通过。保留原锁与失败记录，禁止作者/历史制作载荷，单Agent、CI仅手动。

- 2026-10-16当前状态 `yuai_source_intent_G_relative_preference_whole_song_pending`：原曲独立重制首代表组B/C被否定（发声与音乐均有问题）；本轮发现并修正词起点误作元音起点，第二代表组39字核起点最大差0.520ms。新D/E/F/G完成原生输入隔离和39/39实际图审，技术通过；用户原话“g相对最好，还有之前不是研究过虚实吗？研究了很久的”。G仅相对组合偏好，独立因素与整曲未通过。已纠正知识接入过窄：沿用Skill/表2的条件经验和阴性证据，继续禁读作者/历史制作曲线、工程、音频，不搬旧参数。新当前反馈公开入表，整曲知识包单独生成；原意图锁/知识包不刷新，旧Skill/歌曲不改。下一步按新源元音时钟、逐句前置意图展开整曲候选，其他条件标外推；见[本轮记录](docs/reports/yuai/source-intent-pilots-20261016.md)。单Agent、CI仅手动。

- 后续知识接入已补齐J系列：单通道阴性、入口音乐阶段的局部接受、虚实/发力/磨砂/增益分离及整曲输出包络复核。仅取公开反馈/方法元数据，不读旧工程/音频/数组，不搬旧剂量；新整曲上下文逐ID绑定，旧上下文保持。见[经验接入纠正](docs/reports/yuai/learned-conditions-carryover-20261016.md)。

- 最新状态 `musical_sequence_review_implemented_quality_unverified`（2026-10-15）：用户明确授权更改执行顺序、评价区分能力和Skill。已实现数值计划创建前冻结原曲/乐句意图、当前实际线与快速连接/浅偏差消融比较、按归一化结构复审及独立音乐critique；技术执行、Agent声明、发声试听证据和最终听感分列。contract v2接入编译/交付，旧收据不升级。Skill已修正VOIC范围冲突并同步安装，208项本机测试通过。当前雨爱v02只读回归技术仍通过/图审371，因无真实新前置意图及声线校准，新流程不通过，音乐质量未验证；全1425节点零斜率及6组重复结构触发复审，不自动否定有理由的hold。原工程/音频/作者原件/旧报告收据保持，新推理/音频0；没有重新制作歌曲或新听觉结论。见[整改实现报告](docs/reports/production/musical-sequence-review-20261015.md)。下一步按新顺序形成当前原曲的代表性设计与早期试听，未经新任务不批量重渲染；单Agent/CI仅手动。

- 此前状态 `yuai_v02_two_pass_failure_analysis_complete`（2026-10-15）：用户对v02回报“太虚、还是平”，仅授权先不看参考分析、冻结首轮，再只读白烁工程重新分析并提Skill整改；未授权本轮改工程/音频/Skill或重做v03。已完成[两轮分析](docs/reports/yuai/v02-two-pass-failure-analysis-20261015.md)与负面反馈追加，首轮SHA保持；42当前工程/音频/Skill保护文件和白烁雨爱原件SHA保持，新模型推理/新音频0。定位本轮小幅归中语法、统一快速到达、源动作推断缺失与choice_review循环论证；参考还显示跨字准备/分段到达、不同声线及和声层。缺失旧yousaV1.56与历史声音，不把书面控制当历史音频或直接复制。现有Skill已有正确要求却未落实，并有VOIC上限说明冲突；只提交整改提案，不自动实施。两个听觉目标未达成；太虚单一病因unknown，迁移unverified。单Agent、CI未运行。下列状态保留此前阶段时态。

- 当前状态 `yuai_newskill_v02_delivered_pending_listening`（2026-10-15）：用户授权按新Skill重制雨爱且禁止白烁/历史制作数据。仅沿用原曲/分离/GAME及原曲观测，重新校词、新HFA、谱面、音高函数和发声包络；新446音符/49乐句/371元音/771必要阶段执行复检通过。实际逐字图审发现跨音符首段遗漏后作第1轮音乐修订，29段补入检查、12长段新增动作；371/371完整局部审阅，126物理页中26本轮首版图像/数据精确复用、100最终页实际打开。新完整工程 `projects/latest/yuai_newskill_source_only_v02.ustx` 与新260.48秒纯人声/伴奏试听交付，49组两阶段Normal/三通道实际输入及双F0代理核对；196本机测试通过，Skill38文件未改、安装相同。禁读边界下仅执行当前任务范围门禁，未打开作者包作完整仓库门禁。听感/自然度/新曲迁移仍unknown或unverified，无新人工反馈、无通用规律；不把执行完成当音乐通过。详见[重制报告](docs/reports/yuai/new-skill-source-only-v02-20261015.md)。下一步接本v02反馈，不自动沿用旧成功参数；单Agent、CI仅手动。下列状态保留此前阶段时态。

- 当前状态 `execution_review_implemented_transfer_unverified`（2026-10-15）：按用户授权的 [Skill复检要求](docs/skill-execution-review-requirements.md)实现原生身份清单、前向账本、共享复检、逐字图册/实际审阅覆盖及编译/渲染/直接脚本交付入口。194项本机测试通过；新构造三元音探针经实际Core转写/3图实际审阅完成过程复检，听感未验证；旧雨爱371组/374图只读回归，缺前向账本不通过、实际只打开3图，正式覆盖0/371。Skill按本轮授权更新并同步安装副本；歌曲工程/既有音频不改，未合成新歌，无新听觉标签。未有已授权未见曲，迁移仍unverified；不自动重渲染雨爱或恢复旧实验。当前入口与边界见[完成报告](docs/skill-execution-review-results.md)。下条是此前音乐否决状态，继续保留；单Agent、CI仅手动。

- 当前状态yuai_musical_design_rejected_process_audit_complete：2026-10-15用户整体否定独立雨爱v01质量并指出音高主体近乎平直；代码审计确认311非句尾单元被4/9c固定分派（carry实际2.2c）、280有限回收/19周期及75无组件，0–1600c主体期待允许平直通过。“逐字记录”不构成逐字音乐设计充分的证明。原技术核验保留，音乐设计未通过；冻结本轮脚本作为失败实现记录，下一步先整改源动作判断与主体局部验收/有限代表组试听，不直接批量重渲染。原工程/音频/Skill保持，本轮新模型/音频0；单Agent/CI仅手动。 见[反馈与流程审计](docs/reports/yuai/design-process-rejection-20261015.md)。

- 2E技术交付封存时状态technical_execution_complete_pending_human_listening：用户明确授权冻结批次，两条件新A/S原生4组导出及抱32帧/只33帧5tick采样通过；8次新variance、16套固定种子acoustic/vocoder波形，另4套原生缓存技术波形单列。四路径/重复/两阶段speaker/原生DYN/固定1.5与0.7/PCM24独立检查通过，两个新A及新抱S分别与历史A/C的fresh输入、预测、raw PCM精确。53窗口与16次双F0观测只作有限代理，只的焦点早于波形起点，按协议保留整句并标未完整。72份分开上下文/焦点/两顺序对照衍生PCM待人工试听，154项本机测试通过；20快照/79生产与Skill及工程/67保护输入/1079旧封存路径/567当前歌曲run/47安装SHA保持。新反馈0、通用规律0，全部measurement_validated仍false；2E整体待听觉确认，2F–2H未执行。原歌曲、既有音频和Skill不改，单Agent、CI仅手动，下一步只接本批试听反馈，不自动扩展。报告：[2E实际执行](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution.md)。以下长段保留各阶段历史范围；最新边界以本文件顶部当前反馈条及根目录plan为准。

- 本项目后续由Codex处理；开始工作先读本文件、根目录`plan.md`和`README.md`，结合用户最新范围确定当前步骤。
- 制作/研究计划执行前必须按[知识接入](docs/guides/knowledge-use-in-production.md)生成SHA绑定knowledge_context和逐ID决策；compile-functions只接schema2，研究runner调用同一门禁。新增技术/反馈记录先追加公开报告，再更新active-knowledge-sources显式来源，旧记录/receipt不刷新；没有匹配证据须明确unknown/外推。
- 由当前Codex单个Agent执行，不启动子Agent、多Agent协作或委派到其他对话。只有用户之后明确改变此约定才调整。
- 测试与仓库门禁在本机执行；GitHub的CI工作流关闭自动运行，本地配置仅保留手动触发。不要自动启用远端CI或增加push、pull_request、schedule触发，以免再次产生运行通知邮件。
- 根目录`plan.md`是唯一当前执行计划，表1固定范围整合已完成并保留确认缺口，当前继续关联表2专项的有限条件知识验证准备。A提出47个分层实体；B完成31行定义/30组组合词审查，累计30条说法/25来源并保留缺口。C固定范围审查完成，状态reviewed_with_explicit_gaps：352条具体项覆盖48导航组，前320个ID保持；31节点、导出/播放/pan law、23项本机静态能力及103偏好字段/8嵌套属性、预设/网格写入与扩展接口范围已列。本机graph/masked、FX独立开关/WrapLive及MergePhrasesSec/ReduceAnimations声明字段缺失；MixFxApplyOnExportMixdown未被已核查出口读取。D状态protocol_review_complete_with_explicit_gaps：50协议覆盖A47及3个B候选，10组数组仅验证列明数学/组件范围，11源码/契约加1研究验证器SHA绑定；全部measurement_validated仍false。E状态coverage_review_complete_with_explicit_gaps：42项先冻结再36主映射/6过程复查，34结构可记录/8部分，16已有标签行、0完整测量结论；34候选被链接/16未覆盖。F状态consolidated_with_explicit_gaps：49个正式分层记录实体（24 ACO/15 EVT/9 PER/1 META）、1复音/拍频开放候选、30 DESC、48 CTRL/352 PARAM，31旧描述ID去向和14条RESP/OBS/AUD引用已迁移，原数值/状态/反馈/证据SHA精确保持。40份迁移前文件原字节/SHA保存，8组上下文/任务字段已定义但E的8部分项仍部分。表2专项2A状态source_binding_audit_complete_with_explicit_gaps：17份现行文档先冻结，14记录/52来源/五设计896封存文件声明/1079唯一仓库路径与67保护输入SHA通过。原表2/F产物及原报告/工程/Skill/旧run不改，音频/数组只流式核对字节SHA，未解码、复测、试听或执行模型。C-B/A-C角色、有效_grid5路径、TENC58混合依赖与其它47项范围、索引缺列/原话末尾句号/反馈元数据unknown及本次附加文件名勘误共7项明确。2B状态schema_revised_with_explicit_gaps：26份现行文档/脚本先冻结，14记录新增record_v3/17比较/6反馈组，原数值/状态/反馈/SHA与表1引用保持；深度恢复旧JSON、旧CSV等式与Markdown主体通过。抱C的本轮fresh/B映射逻辑C，旧B在上轮SHFC，原脚本SHA明确；当前runtime/指标复测/新听觉均未执行。2C状态record_review_complete_with_explicit_gaps：14记录复核完成，60份输入/预测NPZ只读、129实际读取绑定文件保持，823指标标量字段与原JSON/报告匹配。原生/fresh输入算术、支撑、通道、SHFC路径及重复输入/预测重查；20版本最终三通道由独立验证器重建检查。36项限定确认/24部分/56unknown逐项列明，不是新实验或普遍规律；旧2B与更旧记录可精确恢复。新模型/原生执行、PCM/mel/检测器数组读取、声学复测/试听均0，全部measurement_validated仍false。2D状态gap_review_and_protocol_frozen_with_explicit_gaps：352 PARAM/48导航组与49正式表现实体/1开放候选逐项覆盖；14旧记录直接引用10个PARAM，其中3个有干预记录。冻结一个SHFC直接声学条件/预测组三通道分离协议：抱225与偏实只214，A/S/D/P四路径、各同输入两次，共计划16套波形/10组主对照，实际0套。D/P为研究反事实，现接口不支持，需先实现研究runner/独立检查器；不作USTX新旋钮或单通道病因。两个条件不是留出，相关测量仍未完整验证；果SHFC/BREC加量停止、接受抱C与旧阴性/unknown保留。23份更新前文档/脚本原字节冻结，现行2C产物及原审计不变。2E准备状态research_interface_prepared_with_explicit_execution_gaps：冻结协议下的A/S/D/P研究组装、独立重建/裁剪/重复检查器、有限批接口及惰性ONNX后端已实现，40项合成契约测试通过。当前47项安装资源按已绑定登记表/配置实际路径重哈希均精确；不将字节一致当模型/分支/两阶段speaker执行通过。24份更新前文档/源码冻结，79生产/桥接/Skill/发布工程与67保护输入保持。真实native身份/5tick Q5采样、模型/声码器执行、PCM/DYN/增益及人工试听未执行；2E整体未完成，实际新波形/新反馈/通用规律均0。2E历史native身份/完整时钟、5tick设计重建及静态后端核查已完成：20快照，41实际音素/421与594帧，抱采样与旧C精确、只计划33帧待新S导出，六组speaker/47资源SHA/三模型声明核对；bool/float32时基/scalar feed修正，variance double*0.01再float32顺序失败纠正，55研究契约测试通过。见docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-native-check.md。下一步有限执行前置项及明确授权的新批次，当前不改歌曲/音频/Skill；新原生导出/模型执行/新波形/反馈均0，2E真实执行/试听及2F–2H未执行。E不是独立音频留出；U17冻结word282误写已增补word295勘误，原冻结文本/unknown保留。F已纠正E的工具显示编码误判：原JSON严格UTF-8且SHA一致、1174字符串无替换/Latin1异常，10条反馈与原报告/CSV对应，未对正确原文转码；E冻结原记录保留。A旧提案读错atoms字段而生成14空关联，F按实际atomic_ids补齐，新增关联仍为结构候选非测量真值。44+25+17共86份唯一固定源码/六资源与Core/App绑定不等于全部非默认执行或模型验证；未读消费者/插件/真实设备增益unknown。C/D不替代试听；E核查已有反馈，新因果试听按表2后续冻结设计推进。B反例不是新音频或E独立覆盖，原清单/ID版本已正式迁移并保留legacy字段/原字节快照，局部证据不代表通用调参规律通过。
- 由Codex更新`plan.md`进度、报告引用及`README.md`当前状态。用户授权的`plan-table2.md`是根目录关联的专项计划，已完成2A–2C记录确认与2D有限协议冻结，2E冻结实际渲染/技术交付已完成、本批人声控制路径结果与原反馈已整理并保留缺口；用户已停止后续BGM关系复核；仍由根目录plan总入口维护，不自动扩大新因果实验。旧计划已被替换，`docs`中的评价与实验报告保留作为历史证据，其中旧“下一步”不覆盖当前计划；不另建重复的活动计划。
- 当前根目录保留`README.md`、`AGENTS.md`、`plan.md`及用户授权的`plan-table2.md`，分别作为项目入口、Codex工作约定、当前计划及后续专项计划。根目录入口整理不改变歌曲工程、Skill或封存实验；后续按实际任务与已有授权推进。

## 目录与文件边界

- 按`docs/guides/repository-layout.md`存放文件。通用生产/只读评价在`src/agent2utau`，原生源码在`bridge/OuBridge`；测试只在`tests/unit`、`tests/contracts`、`tests/skills`，测试临时文件不写发布工程/生产run。
- 仓库维护工具在`tools/repository`；七份旧歌曲脚本在`research/implementation-records/lastpage-20261007`，保留原字节，不执行为新曲模板。历史manifest不改写，旧脚本路径核对使用显式目录迁移清单。
- 表1/表2知识包在`docs/knowledge/acoustic-manifestations-20261009`；新方法文档放`docs/guides`、新可读报告放`docs/reports/<主题>`。封存历史报告及Skill引用的稳定文档保留原路径，不改其原始证据。
- 新运行按生产/实验/研究/原生测试/构建角色在ignored `runs`创建新目录，再分观测、谱面、设计、编译、原生输入、混音、评价、交付、反馈与日志。旧封存run、作者原件/包、发布USTX和本机模型/安装不移动。
- `data`、`models`、`external`、`runs`均为本机资料/产物；不提交。移动/改名维护后检查文档、维护配置、pytest和生成脚本路径；工作树门禁为`python tools/repository/check_repository.py --worktree`，发布检查使用默认索引模式。

## 唯一制作流程

- 读 `skills/singing-expression-editor/SKILL.md` 和 `docs/workflow.md`。
- 当前原曲 GAME / 双 F0 / ASR / HFA 是观测，Agent 判断音乐身份、歌词、音素时钟和未知范围。
- 制作按Skill逐句循环：通览列句后，当前完整音乐句先观察、逐字构思、冻结意图、画线、原生/主体/跨字实际图审和成声核查，保存本句进度后才创建下一句数值计划。整曲最终组装已复核目标，不先批量派发入口/平台。试听状态另列，不要求用户逐句批准；缺真实前置意图不倒填，旧回放只作候选。
- Agent 选择函数、锚点、斜率、幅度、相位及发声过程，明确目的、备选和局部期待。
- 用显式函数计划编译全曲；原生 before-PITD 仅用于编码，不作为目标线。保留并检查 Agent 选择的 note pitch 衔接。
- 改音高、音素、声线、分句后，重建相关预测和实际输入；检查两阶段 speaker、当前张力/气声/有声基底、原生 DYN、拼接和固定增益。
- 保留 source unknown，不拿数学跟随、音量代理或图像检查宣布听觉自然度通过。没有听音工具时标明未听。

## 代码与资料

- CLI只有原曲观测、显式函数编译、原生导出/渲染和资源检查；旧 cover / repair / 候选搜索 / 自动参考路线已撤出。
- 独立只读评价入口为 `python -m agent2utau.evaluation`。只接显式输入和SHA绑定，不读取制作计划的expectations作真值，不自动修歌或搜索缓存；覆盖未知与听觉验收分开。
- 研究资料 `research/baishuo` 的三份原件保持只读；不能把作者数组裁剪、移调、重定时或拟合后接入独立制作。
- `research/implementation-records/lastpage-20261007/`中的脚本为最近完成歌曲的实现记录，不是新曲模板。新曲应使用通用接口与新计划；不可原样重跑已经绑定的旧目录。
- 历史路线及笔记在本机 `.local-archive/cleanup-20261008`，不自动加载、不作为默认入口。此前方案的失败与试听待验收状态不会因清理变成成功。
- 最近用户反馈定位：最后一页响度v02，1:27与3:04偏假/顶上去，1:33与2:56偏实；只完成诊断，尚未修复或听觉验收。
- 2026-10-08 用户授权的单个3:04 TENC实验已完成，见 `docs/lastpage-tenc-controlled-probe-20261008.md`。当前A与v02波形/片段PCM相同，无变化重复精确；B仅取消“抱”的有限TENC偏移，原生输入隔离通过并有小幅谱响应。75项测试通过；六份USTX/36份Skill及当前旧run绑定567文件保持原哈希。局部试听待评价，口型改善/唯一病因unknown；不自动修整曲、更新Skill或推进P2。
- 用户随后试听回报“没啥区别”：本次TENC取消未获可感知改善支持，不采用该B。只读核查当前自身状态并裁切原版约1:14/3:04/3:31同字“抱”作定位对照，PCM/增益保持，另两处听感unknown；不把数值谱变化当改善或自动加大参数。
- 同字对照用户回报“我听着都一样”：只记录未感知差别，不自动标三处均异常/正常。已核查本机GENC=0/falsetto未启用及pitch条件路径；有限SHFC保留vocoder F0为后续候选，尚未执行。报告depth误写偏好1已纠正为实际0.6，实验输入和结果未变；不据此改Skill、发布工程或恢复旧路线。
- 用户再次授权“下一步”后完成有限SHFC -400c条件隔离，见 `docs/lastpage-shfc-controlled-probe-20261008.md`。先前-4存储值只有-4c，被原生单位校验拒绝并保留；诊断B明确所选SHFC合法范围±1200后实现原定-4半音，发布工程不变。24帧条件偏移，variance只pitch变，vocoder F0/人工控制精确保持，全新variance11/acoustic101、A/重复精确、原生DYN/固定1.5/.7。双F0主体相近但局部40–45c检测差，不宣称实测F0固定或病因/自然度通过。84项测试通过，42工程/Skill、47运行依赖、旧run567与旧TENC104绑定保持；试听待评价，不自动扫参数、修整曲或改Skill。

- SHFC试听最新反馈：“更实了，但是有破音的情况”，位置明确“抱的字头”。当前B不采用；只读检查无文件满幅削波/特征裁剪，字头谱变化及上下文预测是候选线索，未证实破音病因。反馈和审计在独立新run，原封存实验不动；下一项候选只检验条件进入时间形状，保持字腹平台/退出及其他控制。本轮未生成新候选或改Skill/整曲。

- 用户授权下一步后完成单个SHFC进入时间C：55→145ms，提前元音80ms准备，-400c平台/退出原生精确。完整新variance11/acoustic101/vocoder，原A/重复精确，旧B明确封存复用；同增益B/C已交付。元音入口响应减小，但b RMS约-5.326dB、谱变化增大，咬字/破音/字腹听感均待评价，不采用为整曲修复。检查器浮点除法顺序误判1帧修正，精确等式/容差保持，失败与F0时基断言保留，85项测试通过。见docs/lastpage-shfc-onset-probe-20261008.md；不继续候选或改Skill。

- 用户对145ms条件进入B/C试听回报“可以”：记录为C在3:04“抱”的局部可用反馈，独立反馈run绑定对照/C工程/波形SHA；原72封存文件保持。未扩为1:27或整曲验收，未补造“完全无破音”等细分标签。本轮没有新合成、发布USTX或Skill变更。

- 用户授权下一步后完成1:27“果”独立SHFC -200c试验：约330Hz/uo/无人工三通道增量，160ms进入/70ms退出，已接受“抱”在完整A/B精确保留。全新variance11/acoustic101/vocoder、原A/重复/currentPCM精确，原生路径/手工控制/vocoderF0/DYN/1.5/.7通过。实际双F0主体相近，uo电平+0.09dB、g+1.69dB/后zh-1.99dB声明；听感待评价，不宣布病因或整曲修复。85测试/资源审计通过，旧567/116/72/接受反馈1及42工程Skill/47运行依赖保持。见docs/lastpage-guo-register-probe-20261008.md；不自动继续参数或改Skill。

- 果SHFC试听被否决：“果字没啥区别，这的咬字好像也没啥区别，而且引入新的问题，响度下降”。B不采用，保留A（已接受抱C），发布工程本来未写入B。独立反馈run保留原文/对照SHA，原67封存文件保持；uo总RMS接近但2–5kHz约-4.03dB、接口30ms约-4.20dB，代理不等于用户精确位置/感知响度真值。停止果SHFC/增益补偿，下一项先只读核查g→uo时序/映射/过渡，尚未执行。无新合成/Skill变更，不否定抱的局部接受或宣布病因。

- 用户授权下一步后完成果音素只读核查：实际g/uo词表及语言ID4匹配，uo整体token；HFA观测对原生元音起点差0.303ms、时长差约14ms，无明确大错位/吞元音证据。五处自己同字时钟保留，当前生成版1:27/3:17/3:44同MIDI64原PCM三段用于标签定位，不是因果对照，另两处标签unknown。无新合成/参数/Skill/unknown改动，已接受抱保留；不直接拆uo或缩g。见docs/lastpage-guo-phoneme-audit-20261008.md。

- 用户对三处果原PCM对照回报“中间这个可以”：word247约3:17局部可用，1:27原反馈保留、3:44仍unknown。实际新成声state比较：主体音高相近，通过处voicing略高、breathiness略低，入口差更明显；仅线索，非因果。缓存导出不等于新成声的草稿被拒绝保留，567当前run文件哈希保持。无新合成/参数/Skill修改，已接受抱保留；下一项候选有限VOIC单因素支撑，尚未执行。见 docs/lastpage-guo-positive-comparison-20261008.md。

- 用户确认研究通用规律而非继续单点修复后，完成318当前字跨条件只读研究：5个原版标签+接受抱C变体，313字听感unknown保留。接受抱voicing更低、tension更高，否定统一提高VOIC/降低TENC；同元音配对breathiness降低方向一致但未隔离。冻结6条件同剂量BREC单因素检验方案（2问题+4偏实/可用），尚未渲染，不拟合阈值或扫参数。停止先前果VOIC提案；不更新Skill或改音频，接受抱保留。见 docs/lastpage-cross-condition-study-20261008.md。

- 执行冻结六条件BREC -10单因素对照，18套新variance11/acoustic101/vocoder、Normal75/Classic25；仅fresh breathiness改变，预测/其他输入/原SHFC保持，6原A与此前波形和6重复精确。原生DYN/固定1.5/.7/PCM通过，特征裁剪0；元音RMS变化约±0.03dB，双F0中位差0.03～0.16c、最大3.20/2.44c，技术响应不是口型改善。1tick编码被独立检查拒绝后改原5tick网格，原生初始化崩溃普通同输入重试成功，草稿/失败保留；88测试通过。六组同增益A/B已交付待听感，不扫参数/改Skill/发布工程，接受抱C保持。见 docs/lastpage-brec-cohort-probe-20261008.md。

- 六组分开试听后用户回报“全部没区别”：本轮BREC -10在两个问题及四个偏实/可用条件均未获得可感知差别，不采纳B，不把数值响应当改善或写入Skill，也不自动增大剂量。限于当前剂量/条件的否定证据，不宣布整个气声通道无效；原标签/接受抱C/源unknown保持。独立反馈run绑定12份A/B人声SHA，原537封存文件精确。无新合成/参数/Skill修改。见 docs/lastpage-brec-cohort-probe-20261008.md#最新试听反馈。

## Git

- 不提交音频、模型、缓存、run输出、本机归档或绝对路径配置 `configs/local.yaml`。
- 发布前运行当前测试、检查Skill引用、验证作者包SHA及ZIP成员，再审计Git索引内容。
- 不改写既有Git历史；删除旧音频跟踪只清理当前树。本机音频与已完成工程仍保留。
