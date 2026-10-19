---
name: singing-expression-editor
description: 根据原曲GAME旋律、逐帧F0、歌词与音素上下文，由Agent逐句构思、画线、原生复查及成声，完成一句再做下一句，最后组装整曲。用于重画音高与发声控制、改善平直字腹、长音细节和声线连续性；参考工程用于研究条件规律。
---

# 从原曲条件到自行画线

Agent负责演唱判断，工具负责执行和发现矛盾。制作按[一句完成再画下一句](references/phrase-by-phrase-workflow.md)推进：**通览整曲与列句 → 当前句源观察及呼吸/计算上下文选择 → 逐字构思与冻结意图 → 只画当前句 → 原生落线、完整字腹/跨字复查与成声 → 保存本句进度 → 下一句 → 整曲组装复核**。未完成当前句复核，不先给后句分配数值函数或平台。先决定怎样唱，再选函数；不能先画全曲快速到主音的平台，再集中补小鼓包。研究参考可归纳条件和反例；生成不读取作者数组、局部节点或profile构造目标，也不把原曲F0平滑缩幅当设计。

## 输入与研究资源

从当前项目根读取AGENTS.md、用户最新范围及已选声库／移调／声线。绑定录音、歌词、GAME、逐帧F0及未知掩码、目标原生音素时钟、软件／模型与工程哈希。

制作或修订前，先按[设计前知识接入](references/knowledge-before-design.md)检索表1机制和表2相关正例、阴性、副作用及最新反馈，记录检索范围、条件匹配和采用／拒绝／外推理由，再冻结音乐意图。不能只取参数定义、只看早期摘要，或把来源绑定通过当成相关经验已检全。“不读取历史制作数据”时仍按用户范围使用已整理的方法与条件结论，隔离旧工程、曲线、音频和数组，不搬旧剂量；若用户连知识结论也禁用则遵从并记录缺口。

GAME提供音符事件的开始、时长和音高估计，不能冒称字内逐帧F0。细部观测使用有来源的逐帧检测器结果；辅音、分离残留、八度冲突及unknown单列，检测不到周期不能自动取消主动周期选择。旋律身份、源事实与艺术选择分别记录。

研究资源索引位于项目 `research/singing-expression-examples/source-condition-resource-index.json`，仅在授权的研究或失败分析时读取其中作者资源。学习步骤见[原曲／作者资源研究](references/reference-imitation-calibration.md)。索引缺失时定位授权的原始工程、GAME和F0，不使用别的歌曲或旧候选曲线补齐。具体曲名、歌词、时码、样本和参数保存在项目研究档案，Skill仅保存条件、处理、反例和通用接口。

新分离遵守[原曲分离](references/source-separation.md)；冻结研究的旧模型结果按其真实来源保留，不改名成新推理。时钟对齐不等于逐字对应已核实；未知不能升级为可训练或风格真值。

## 判断、设计与检查

开始制作读[条件到函数](references/source-condition-to-function.md)、[转音与支撑](references/expressive-turn-and-support.md)及[声线基底](references/voice-baseline-and-stability.md)。先展开连续原曲F0和歌词/音素上下文，辨认主音、到达/回探/再到达、展开和下一字准备；统计概述不替代完整过程，辅音低F0和共同误检仍可unknown。“克制/推进”、时长、段落只提供上下文，不直接派发动作。

在当前句数值函数计划创建前，按[执行契约](references/production-execution-review.md)保存本句意图：绑定源观察及窗口，分开事实、解释、主动选择，说明每个独立过程与合理备选的不同后果，再冻结intent lock。入口、主体与退出分别判断/检查，一个入口通过不能代表整句字腹有发展。未知观察允许明确艺术外推，不冒称已观察到。意图覆盖本句每个真实元音及跨字关系；函数与幅度期待随后编写，不从已生成曲线倒填意图。

对每个元音及其延续音乐阶段，明确入口、到达、维持／回收／展开、准备／退出的顺序。选择或拒绝有限回收、中心走势、重复浅波、持续周期、台阶连接和发声变化，并说明一个合理备选为何不选。平稳可以是选择，必须说明该段为何要收住；不能用空动作、默认平台或少量非零点填满未判断区域。

先画中心的离开、承接/回探、主音到达和持续走势，再选有限运动、周期或保持。真正停留/极值可用零导数，连续推进的途中节点保留速度。明显装饰与微周期分别给预算；不要把所有转音缩成±几十音分，也不强制每字深颤。参数依据须说明当前观察怎样约束位置、幅度和时序；“我选了X，所以拒绝替代X”不能作为依据。数值候选见[条件配方](references/conditional-drawing-recipes.md)，不按区间或作者实例查表。

先在覆盖不同音乐/音素条件的完整上下文校准发声基底及处理策略，再展开整曲。校准前按[AP/SP](references/ap-sp-placement.md)核定实际原生分句、静顿/呼吸及padding，按[声线基底](references/voice-baseline-and-stability.md)确认实际加载与试听条件；同一轨道或音乐句不保证模型共用上下文。相同声线、默认控制或非零人工增量均不证明实感合适。准备有区分力的少量对照并尽早提供试听；无听感证据时标为未校准。用户要求完整候选仍按范围交付，不增加许可等待，不把候选或代理指标当实感解决。

`scripts/design_functions.py`可确定性采样独立设计的中心、有限回收和变深变速周期，并核对调用者声明的局部范围。它不读F0／参考数组，不判断音乐好坏，不写USTX。计划格式与原生转写边界见[条件到函数](references/source-condition-to-function.md)。需要非对称峰谷等其它函数时使用实际支持接口或补接口，不静默换成此辅助工具的有限函数。

按[连续线与边界](references/continuous-contour-and-scale.md)检查全部音乐边界及AP/SP两侧：note pitch、before-PITD、PITD和最终绝对线分别核对。反向大偏差抵消硬基底即使当前帧通过也可能有点间尖峰；原生读回、实际显示路径和相位变化探针分别检查，不能把对自己目标误差小当作无尖角。

每句落线后立即按[整句尺度](references/phrase-scale-contour-study.md)和[逐元音执行复检](references/production-execution-review.md)查看本句每个真实元音的完整局部视图及相邻关系，修订本句的明确缺失后再进入下一句；整曲组装后另作总览和跨句复核。统一秒／半音比例，长字以连续重叠页覆盖；代表细图不能代替全部字。生成图册不计已审阅，逐项绑定实际视图访问证据、具体观察、保留或修改理由与版本 SHA，不以整句评语重复填充所有字。字头大滑音或尾部准备不能替主体内部运动背书；局部期待绑定事前实际阶段。整体覆盖、周期数、C1和样本相等只证明各自技术事项。

音乐复审同时检查跨字到达路线和真正字腹。声称明显回探/延迟到达/展开的处理，应能否决“快速连接+浅小起伏”的诊断对照；若对照也满足同样理由，重查意图和评价。平稳反例可明确允许相似。检查实际结构是否仍为统一短连接、归中鼓包、全零途中斜率或近似百分比分派；换ID、手写不同数字不解除复审。自动对照能否定几何主张，不能自动判好听；最终仍须Agent具体批评和听觉证据。

## 专项路由

- 节奏、长字太急、后字提前：先读[唱字时长](references/rhythm-and-syllable-duration.md)，HFA是观测，不能决定音乐字界。
- 发音不清、复合韵母含混：按[韵母内部时序](references/vowel-support-and-language.md#复合韵母的清晰度与内部时序)区分声母、介音、主元音和韵尾；合法token和正确总时长不证明内部过渡清楚。
- 呼吸／停顿与原生分句：[AP/SP](references/ap-sp-placement.md)。明确非唱支撑，不把载频跳变算作唱音运动。
- 连续唱太久、缺少补气或承载长字仍显怪：[气口预算与承载元音](references/breath-budget-and-carried-nucleus.md)。全曲记录连续负担、语义边界和可用准备；主动腾出气口，区分真正转音与不必要的连续大回转。
- 换气像单独插入、与唱句脱节：按[AP/SP](references/ap-sp-placement.md)区分宽候选、真实吸气与准备下字，检查共同上下文和波形余量。
- 缺少pitch外控制、长音发声不变：[多通道与长音](references/joint-phonation-and-sustain.md)。TENC／BREC／VOIC／DYN分别设计或有理由保持，pitch里的文字不自动执行控制。
- 强调、虚实／音量／声线问题：[强调](references/accent-selection.md)、[声线](references/voice-baseline-and-stability.md)、[参数](references/parameters.md)。当前曲的已选声线不是跨曲默认值，不自动逐字归一化。
- 突然小声、同词前后落差或高音尖紧：[实际包络与舒适度](references/loudness-and-high-note-comfort.md)。整曲声线／音高／人工发声控制改版后重查当前真实元音输出；按乐句选择承托、强字保留与回收，分开发声力度和有限输出增益，让工程和音频采用同一原生包络。
- 响度忽大忽小、相同控制仍有落差或怀疑音高影响：[音高、预测发声与响度](references/pitch-phonation-and-loudness.md)。先选整句强弱意图，核对当前预测、工程声明范围和两条音高依赖，再设计有限补偿；改变条件后重新预测，不靠换随机种子或压平音高修音量。
- 字内漏声、短字主体被收尾吞掉：[元音核与局部释放](references/nucleus-envelope-and-release.md)。核对原始声／最终声、短窗持续低谷及改气口后的必要元音；隔离试验后再选有限恢复函数，复核整曲反例。
- 相邻字句气实交替奇怪：[虚实连续性](references/phonation-continuity.md)。先选整句走向，再查未加人工事件的实际预测基底；原生分句不决定表达，有限补偿不抹平音素细节。
- 转音保守、发音怪或支撑乏力：[转音与支撑推断](references/expressive-turn-and-support.md)。区分音乐音程、较大装饰与微周期；查动作顺序和真实音素，分离音高与发声因素。
- 局部已经接受、需应用整曲，或“实、力量、磨砂填充”互相混淆：读[局部接受到整曲发声](references/local-acceptance-to-whole-song-phonation.md)。先查短音乐阶段是否遗漏，区分发声质感与波形增益；逐句说明采用、保留和外推，整曲新声音另行验收。
- 低转高大跳生硬、不顺畅：[上行音程衔接](references/upward-interval-connections.md)。分开连续推进、下方承接与短促到达，检查速度、主音到达和旧字腹叠加；完整列出全曲相关连接。
- 英文塌陷、长音顶不住、高音细紧或稍虚而需饱满：[元音支撑与语言](references/vowel-support-and-language.md)。区分元音核与辅音下探，连贯处理词内音节，分别设计声线、支撑与气声。
- 细小回收、非对称与周期退出：[细部](references/microexpression-and-acoustics.md)、[局部周期](references/local-cycle-design.md)。物理Hz积分相位，深度退出独立，不拖长最后半波。
- 继续研究处理与反例：[参考条件](references/baishuo-drawing-method.md)。作者书面控制不证明历史声音或真实意图。

## 执行与交付

先按[执行契约](references/production-execution-review.md)冻结真实元音身份及乐句意图，再创建数值计划与ledger。新制作用contract v2绑定intent lock和独立乐句critique；独立facts先于计划期待提取。技术核对、Agent审阅声明、发声校准证据与最终听觉结果分开报告，keep加文字不自动代表音乐正确。contract v1/无sidecar只支持旧技术复现和候选；旧receipt不升级为新版音乐流程通过。改输入/工程后重导出并复查依赖，缺项不包装为完成；有理由的hold合法。新曲迁移另验，已见曲回归不算迁移。

整曲任务按[整曲执行](references/whole-song-redraw.md)为全部音符、延续音、前导／尾帧与非唱边界生成显式目标。音乐身份改变须在授权范围内记录原目标、新目标和原因；不得改源掩码或把主动装饰冒称源事实修正。只做局部任务时按[pilot](references/pilot-execution.md)声明范围。

接入前读[实际工具](references/project-tools.md)及[上下文接口](references/context-execution.md)。旧歌曲生成器、参考路线挑选器、简单模板没有因Skill更新自动变成新方法；先确认实际消费了哪些函数与参数，unsupported不算执行。清除旧曲线不等于新函数已经覆盖所有边界。

按[计划与评估](references/planning-and-evaluation.md)记录planned／compiled／native_checked／rendered／checked。音高、音素或speaker条件改变后重新计算两阶段依赖；绑定新工程、波形拼接、全曲增益、哈希、无削波及实际F0。声音好坏与技术跟随分开。没有音频感知工具时明确没有听过；可交付初版，但不宣布自然度解决。

能力范围见[能力考核](references/grounding-and-competence.md)。已研究曲的改版、函数测试或文字解释不证明未见曲能力；不自动恢复暂停goal或提高冻结数据训练资格。
