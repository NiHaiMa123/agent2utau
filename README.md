# agent2utau

2026-10-17当前制作 `yuai_phrase_handdraw_source_only_paused_by_user_after_s14`：使用新Skill逐句重制雨爱，按用户“做完这句先暂停，我看下效果”完成s14后暂停。s01–s14共133元音的画线/实际图审/成声及输入核验完成，s15及后续未启动，整曲53句尚未完成。现按用户澄清补交[从第一句开始的前十四句连续试听及预览工程](docs/reports/yuai/phrase-handdraw-first14-preview-20261017.md)，制作继续暂停；严格缺口、失败修订、时钟不确定与试听入口见[本轮制作记录](docs/reports/yuai/phrase-handdraw-source-only-20261017.md)。禁止作者/历史制作载荷，仅沿用原曲侧观测及公开条件经验；Skill40资源与既有v03工程SHA保持。单Agent、CI未运行，听感均待确认；等待用户反馈/恢复指示。

2026-10-16 雨爱 source-only 最新 Skill 重制 `yuai_source_only_latest_skill_delivered_pending_listening`：按用户边界只用源 FLAC、分离人声、GAME 音符事件与双 F0 观测，不用历史制作 run/白烁文件，按最新逐句流程重制整曲。54 段/137 原生乐句/405 音符、361 元音；逐句冻结意图（计划前）→ 函数设计 → 编译读回 ≤0.49996c → 逐字图审 357/361。前向账本 361 决策（hold185/center109/oscillation40/finite_return27），发声路径与结构提示如实记录。新 260.5s 人声+伴奏候选已交付。技术/agent_attested；4 个 10ms 微元音单元未通过保留，技术完成false，整曲听感unknown。单Agent、CI仅手动。见[报告](docs/reports/yuai/source-only-latest-skill-20261016.md)。下一步接本版试听反馈，不自动扫参。

2026-10-16当前流程更新 `phrase_by_phrase_skill_workflow_updated`：按用户要求改为一个完整音乐句观察/逐字构思/前置意图/画线/原生与主体及跨字图审/成声检查做完，再推进下一句；保存逐句进度，试听状态独立，不逐句等人工批准。整曲最终只组装已审阅目标；独立入口/主体/退出主张拆检，不让一个入口代表全句。7份Skill资源更新并同步安装，40文件一致/124引用/结构核查通过；当前工具仍无逐句先后自动门禁。雨爱工程、音频、旧锁与receipt保持，本轮不继续歌曲。见[逐句流程更新](docs/reports/production/skill-phrase-workflow-20261016.md)。单Agent、CI仅手动。下一制作任务按新流程逐句执行，旧通过不倒填。


2026-10-16续项完成：状态 `yuai_G_whole_candidate_delivered_pending_listening_with_process_gap`。Skill已补直接检索表1/表2与后续阴性/反馈、词/核映射，39份安装一致、117链接及9本机测试通过。当前源独立G方向全曲53句/371元音/382阶段，61组原生成声与两阶段实际输入核对、371/371实际图审完成，新260.48秒纯人声及v03候选工程已交付。技术完成；s13冻结到达检查失败保留，严格流程false，末将/虹深回探及2:46短吸偏低电平列试听重点，整曲听感unknown。只取公开经验，无作者/历史制作载荷，未启用CI，单Agent。见[整曲候选报告](docs/reports/yuai/source-intent-G-whole-candidate-20261016.md)。下一步接本版整曲反馈，不自动扫参。

2026-10-16本轮续项：已把表1/表2检索直接写入Skill主入口，补检索覆盖/后续反馈/阴性和副作用、知识与历史制作载荷边界，以及源词/辅音/元音核映射检查；39份Skill文件安装一致、117引用与9项本机知识契约测试通过。门禁仍不自动证明检全/应用正确；见[Skill更新](docs/reports/production/skill-knowledge-entry-20261016.md)。当前继续雨爱G方向的整曲候选：53句新意图已前置冻结、371元音/382音乐阶段的当前谱面与原生核对已完成，完整成声/整曲听感尚未通过。保留原锁与失败记录，禁止作者/历史制作载荷，单Agent、CI仅手动。

2026-10-16当前状态 `yuai_source_intent_G_relative_preference_whole_song_pending`：原曲独立重制首代表组B/C被否定（发声与音乐均有问题）；本轮发现并修正词起点误作元音起点，第二代表组39字核起点最大差0.520ms。新D/E/F/G完成原生输入隔离和39/39实际图审，技术通过；用户原话“g相对最好，还有之前不是研究过虚实吗？研究了很久的”。G仅相对组合偏好，独立因素与整曲未通过。已纠正知识接入过窄：沿用Skill/表2的条件经验和阴性证据，继续禁读作者/历史制作曲线、工程、音频，不搬旧参数。新当前反馈公开入表，整曲知识包单独生成；原意图锁/知识包不刷新，旧Skill/歌曲不改。下一步按新源元音时钟、逐句前置意图展开整曲候选，其他条件标外推；见[本轮记录](docs/reports/yuai/source-intent-pilots-20261016.md)。单Agent、CI仅手动。

后续知识接入已补齐J系列：单通道阴性、入口音乐阶段的局部接受、虚实/发力/磨砂/增益分离及整曲输出包络复核。仅取公开反馈/方法元数据，不读旧工程/音频/数组，不搬旧剂量；新整曲上下文逐ID绑定，旧上下文保持。见[经验接入纠正](docs/reports/yuai/learned-conditions-carryover-20261016.md)。

由Codex根据原曲观测和`singing-expression-editor` Skill判断演唱动作，独立设计音高与发声函数，编译OpenUtau工程，再检查实际输入和试听结果。原曲GAME、双F0、ASR、HFA提供观测；具体音乐身份、音素时钟、函数及未知范围由Codex判断。

制作前执行[表1/表2知识接入](docs/guides/knowledge-use-in-production.md)：显式检索并记录条件/采用或拒绝理由，compile-functions schema2执行前校验；Skill保持方法层。

最新（2026-10-15）：已按用户授权完成执行顺序、评价和Skill整改，见[实现报告](docs/reports/production/musical-sequence-review-20261015.md)。音乐意图须在数值计划之前冻结；新评价检验实际动作能否排除快速连接/浅偏差消融，归一化结构提示重复，并分开技术执行、Agent声明、发声试听证据和最终听感。contract v2接入编译/交付，旧收据不升级；安装Skill已同步，208项本机测试通过。雨爱v02只读回归仍技术通过/371图审，但新流程未完成、音乐质量未验证。歌曲、音频和旧证据不改，没有新推理/渲染。[此前两轮失败分析](docs/reports/yuai/v02-two-pass-failure-analysis-20261015.md)保留；太虚的单一病因及新曲迁移仍unknown/unverified。下段保留v02交付时态。

当前状态 `yuai_newskill_v02_delivered_pending_listening`：按用户要求使用新Skill，仅依据原曲及其观测重制雨爱，未读取白烁或历史制作谱面/曲线/控制/音频。新工程49乐句、371元音、771阶段执行复检和371/371局部图审完成；图审发现跨音符前段遗漏后完成第1轮音乐修订。完整工程与260.48秒人声/伴奏试听已交付，196项本机测试通过，Skill保持。听感、音乐质量和未见曲迁移仍待验，见[重制报告](docs/reports/yuai/new-skill-source-only-v02-20261015.md)。此前[复检接入结果](docs/skill-execution-review-results.md)、旧雨爱否决及专项实验均保留原范围。

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

当前状态yuai_musical_design_rejected_process_audit_complete：2026-10-15用户整体否定独立雨爱v01质量并指出音高主体近乎平直；代码审计确认311非句尾单元被4/9c固定分派（carry实际2.2c）、280有限回收/19周期及75无组件，0–1600c主体期待允许平直通过。“逐字记录”不构成逐字音乐设计充分的证明。原技术核验保留，音乐设计未通过；冻结本轮脚本作为失败实现记录，下一步先整改源动作判断与主体局部验收/有限代表组试听，不直接批量重渲染。原工程/音频/Skill保持，本轮新模型/音频0；单Agent/CI仅手动。 见[反馈与流程审计](docs/reports/yuai/design-process-rejection-20261015.md)。

技术交付封存时**表1 A–F固定范围整合完成；表2完成2A–2D及2E冻结16套实际渲染/技术交付，当时人工试听pending，确认缺口保留**。2E技术交付封存时状态technical_execution_complete_pending_human_listening：用户明确授权冻结批次，两条件新A/S原生4组导出及抱32帧/只33帧5tick采样通过；8次新variance、16套固定种子acoustic/vocoder波形，另4套原生缓存技术波形单列。四路径/重复/两阶段speaker/原生DYN/固定1.5与0.7/PCM24独立检查通过，两个新A及新抱S分别与历史A/C的fresh输入、预测、raw PCM精确。53窗口与16次双F0观测只作有限代理，只的焦点早于波形起点，按协议保留整句并标未完整。72份分开上下文/焦点/两顺序对照衍生PCM待人工试听，154项本机测试通过；20快照/79生产与Skill及工程/67保护输入/1079旧封存路径/567当前歌曲run/47安装SHA保持。新反馈0、通用规律0，全部measurement_validated仍false；2E整体待听觉确认，2F–2H未执行。原歌曲、既有音频和Skill不改，单Agent、CI仅手动，下一步只接本批试听反馈，不自动扩展。见[实际执行报告](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution.md)与[审计](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution-audit.json)。

| 入口 | 用途与当前状态 |
|---|---|
| [plan.md](plan.md) | 唯一当前执行计划：A–F整合完成；关联表2已完成2A–2D及2E实际技术交付，2E两字机制预实验保留；既有人声试听循环已收口；当前先准备最后一页逐首更新与证据回填，BGM复核停止 |
| [表1正式整合](docs/knowledge/acoustic-manifestations-20261009/table1-consolidation-review.md) | 49个分层实体、引用/ID迁移、上下文字段与纠错；记录结构不等于检测器 |
| [表1逐行审查](docs/knowledge/acoustic-manifestations-20261009/table1-review.md) | A当时的原31行拆分/迁移提案；正式去向与历史快照见F |
| [表1来源与听感词审查](docs/knowledge/acoustic-manifestations-20261009/table1-source-review.md) | 30条说法、31行定义、30组多义拆解与假设反例；逐项保留缺口，不宣称全部验证 |
| [表1具体控制审查](docs/knowledge/acoustic-manifestations-20261009/table1-control-review.md) | 352条具体项、偏好/预设/网格与扩展范围；本机缺失/未执行独立记录，机制核查不等于听感验证 |
| [偏好逐字段审查](docs/knowledge/acoustic-manifestations-20261009/editor-preferences-review.json) | 103字段/8嵌套属性；声明、固定源码引用、本机成员存在与live未知分栏 |
| [表1观测协议审查](docs/knowledge/acoustic-manifestations-20261009/table1-measurement-review.md) | 50条协议覆盖A47实体及3个B候选；10组数组只验证明列范围，未验证真实音频检测性能或自然度 |
| [表1描述覆盖审查](docs/knowledge/acoustic-manifestations-20261009/table1-coverage-review.md) | 42项冻结清单，34可记录/8部分；16候选未覆盖，反馈/音乐提问/研究任务/作者结构分别计数 |
| [表2实际执行](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-execution.md) | 8次variance/16套实验波形及72份固定增益分开试听文件；技术通过，听觉pending |
| [表2专项计划](plan-table2.md) | 2A–2C记录确认及2D协议冻结完成且有缺口，2E实际渲染/技术交付完成，2E两字机制预实验保留，当前2F采样设计准备、实际留出验证0，后续BGM关系复核取消，2F–2H未执行；新因果试听按冻结范围 |
| [表2记录审计](docs/knowledge/acoustic-manifestations-20261009/table2-review.md) | 14记录的来源/比较/版本、有效_grid5路径与实际用户绑定交付；7差异/缺口，非新效果验证 |
| [表2输入与静态核查](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-native-check.md) | 41音素完整时钟、抱采样与旧C精确、只计划采样；六组speaker/三模型声明、55契约测试；新导出/推理/PCM/试听仍待执行 |
| [表2研究接口准备](docs/knowledge/acoustic-manifestations-20261009/table2-stage-2e-preparation.md) | A/S/D/P独立数学检查；40契约测试/47资源SHA；真实模型、PCM与试听尚未执行 |
| [表2有限协议](docs/knowledge/acoustic-manifestations-20261009/table2-protocol-review.md) | 352 PARAM/50表现覆盖；一个SHFC路径分离设计，2D冻结时研究接口尚待实现；当前另见2E实际执行报告，新对照待听 |
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

表1框架不等于已验证的异常检测器；测量响应不等于可感知改善。C机制核查与D测量协议均不能代替试听，E核对已有反馈，新的因果试听按表2后续冻结设计推进。已有证据尚不足以形成通用音色、口型或真假声配方。本批按明确授权生成冻结对照且技术检查通过，原歌曲、既有音频及Skill保持。现在接人工试听；未听/无反馈保持pending，全部measurement_validated仍false。

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
