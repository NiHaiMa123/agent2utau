---
name: singing-expression-editor
description: 根据原曲GAME旋律、逐帧F0、歌词与音素上下文判断演唱动作，由Agent选择函数并独立设计整曲音高及发声控制，编译原生工程与试听音频。用于重画曲线、改善平直字腹、长音细节和声线连续性；参考工程用于研究条件规律。
---

# 从原曲条件到自行画线

Agent判断什么情况需要什么动作，并选择函数、锚点、参数和衔接。函数执行决定，不替Agent挑作者路线。默认工作流是 **观察原曲 → 判断音乐与音素条件 → 设计函数 → 检查完整最终线 → 原生渲染**。研究作者工程可以归纳处理与反例；生成时不读取作者曲线数组、局部控制点或profile来构造目标，也不把原曲F0平滑缩幅后当作设计。

## 输入与研究资源

从当前项目根读取AGENTS.md、用户最新范围及已选声库／移调／声线。绑定录音、歌词、GAME、逐帧F0及未知掩码、目标原生音素时钟、软件／模型与工程哈希。

GAME提供音符事件的开始、时长和音高估计，不能冒称字内逐帧F0。细部观测使用有来源的逐帧检测器结果；辅音、分离残留、八度冲突及unknown单列，检测不到周期不能自动取消主动周期选择。旋律身份、源事实与艺术选择分别记录。

研究资源索引位于项目 `research/singing-expression-examples/source-condition-resource-index.json`，仅在授权的研究或失败分析时读取其中作者资源。学习步骤见[原曲／作者资源研究](references/reference-imitation-calibration.md)。索引缺失时定位授权的原始工程、GAME和F0，不使用别的歌曲或旧候选曲线补齐。具体曲名、歌词、时码、样本和参数保存在项目研究档案，Skill仅保存条件、处理、反例和通用接口。

新分离遵守[原曲分离](references/source-separation.md)；冻结研究的旧模型结果按其真实来源保留，不改名成新推理。时钟对齐不等于逐字对应已核实；未知不能升级为可训练或风格真值。

## 判断、设计与检查

开始画线前读[条件到函数](references/source-condition-to-function.md)。为完整乐句确认各字主音、字内音乐换音、落拍、前后音程、实际声母／元音、可用主体、下一字或停顿；看原曲动作落在哪里及其可靠程度。段落、时长或“克制／推进”等标签只是上下文，不能直接索引某条曲线。

对每个元音及其延续音乐阶段，明确入口、到达、维持／回收／展开、准备／退出的顺序。选择或拒绝有限回收、中心走势、重复浅波、持续周期、台阶连接和发声变化，并说明一个合理备选为何不选。平稳可以是选择，必须说明该段为何要收住；不能用空动作、默认平台或少量非零点填满未判断区域。

逐段写出当前条件、所选函数、实际支撑、节点／斜率或深度／Hz／相位、预期局部运动和不确定性。参数来自本段设计；研究区间只是起步依据，不搬运某个原例的整串峰谷。具体数值候选见[条件配方](references/conditional-drawing-recipes.md)，阶段选择见[动作选择](references/new-song-action-selection.md)。不要把所有长音加同形颤音，也不要把短字一律压平。

`scripts/design_functions.py`可确定性采样独立设计的中心、有限回收和变深变速周期，并核对调用者声明的局部范围。它不读F0／参考数组，不判断音乐好坏，不写USTX。计划格式与原生转写边界见[条件到函数](references/source-condition-to-function.md)。需要非对称峰谷等其它函数时使用实际支持接口或补接口，不静默换成此辅助工具的有限函数。

按[连续线与边界](references/continuous-contour-and-scale.md)检查全部音乐边界及AP/SP两侧：note pitch、before-PITD、PITD和最终绝对线分别核对。反向大偏差抵消硬基底即使当前帧通过也可能有点间尖峰；原生读回、实际显示路径和相位变化探针分别检查，不能把对自己目标误差小当作无尖角。

按[整句尺度](references/phrase-scale-contour-study.md)在统一秒／半音比例检查整首最终线，并查看浅／明显／平稳反例的细图。字头大滑音或尾部准备不能替主体内部运动背书；局部预期应限定在动作真实发生的区域。整体覆盖、周期数、C1和样本相等只证明各自技术事项。

## 专项路由

- 节奏、长字太急、后字提前：先读[唱字时长](references/rhythm-and-syllable-duration.md)，HFA是观测，不能决定音乐字界。
- 呼吸／停顿与原生分句：[AP/SP](references/ap-sp-placement.md)。明确非唱支撑，不把载频跳变算作唱音运动。
- 连续唱太久、缺少补气或承载长字仍显怪：[气口预算与承载元音](references/breath-budget-and-carried-nucleus.md)。全曲记录连续负担、语义边界和可用准备；主动腾出气口，区分真正转音与不必要的连续大回转。
- 换气像单独插入、与唱句脱节：按[AP/SP](references/ap-sp-placement.md)区分宽候选、真实吸气与准备下字，检查共同上下文和波形余量。
- 缺少pitch外控制、长音发声不变：[多通道与长音](references/joint-phonation-and-sustain.md)。TENC／BREC／VOIC／DYN分别设计或有理由保持，pitch里的文字不自动执行控制。
- 强调、虚实／音量／声线问题：[强调](references/accent-selection.md)、[声线](references/voice-baseline-and-stability.md)、[参数](references/parameters.md)。当前曲的已选声线不是跨曲默认值，不自动逐字归一化。
- 突然小声、同词前后落差或高音尖紧：[实际包络与舒适度](references/loudness-and-high-note-comfort.md)。检查整曲真实元音输出，分开发声阶段与有限增益，并让工程和音频采用同一原生包络。
- 响度忽大忽小、相同控制仍有落差或怀疑音高影响：[音高、预测发声与响度](references/pitch-phonation-and-loudness.md)。先选整句强弱意图，核对当前预测、工程声明范围和两条音高依赖，再设计有限补偿；改变条件后重新预测，不靠换随机种子或压平音高修音量。
- 字内漏声、短字主体被收尾吞掉：[元音核与局部释放](references/nucleus-envelope-and-release.md)。核对原始声／最终声、短窗持续低谷及改气口后的必要元音；隔离试验后再选有限恢复函数，复核整曲反例。
- 相邻字句气实交替奇怪：[虚实连续性](references/phonation-continuity.md)。先选整句走向，再查未加人工事件的实际预测基底；原生分句不决定表达，有限补偿不抹平音素细节。
- 转音保守、发音怪或支撑乏力：[转音与支撑推断](references/expressive-turn-and-support.md)。区分音乐音程、较大装饰与微周期；查动作顺序和真实音素，分离音高与发声因素。
- 低转高大跳生硬、不顺畅：[上行音程衔接](references/upward-interval-connections.md)。分开连续推进、下方承接与短促到达，检查速度、主音到达和旧字腹叠加；完整列出全曲相关连接。
- 英文塌陷、长音顶不住、高音细紧或稍虚而需饱满：[元音支撑与语言](references/vowel-support-and-language.md)。区分元音核与辅音下探，连贯处理词内音节，分别设计声线、支撑与气声。
- 细小回收、非对称与周期退出：[细部](references/microexpression-and-acoustics.md)、[局部周期](references/local-cycle-design.md)。物理Hz积分相位，深度退出独立，不拖长最后半波。
- 继续研究处理与反例：[参考条件](references/baishuo-drawing-method.md)。作者书面控制不证明历史声音或真实意图。

## 执行与交付

整曲任务按[整曲执行](references/whole-song-redraw.md)为全部音符、延续音、前导／尾帧与非唱边界生成显式目标。音乐身份改变须在授权范围内记录原目标、新目标和原因；不得改源掩码或把主动装饰冒称源事实修正。只做局部任务时按[pilot](references/pilot-execution.md)声明范围。

接入前读[实际工具](references/project-tools.md)及[上下文接口](references/context-execution.md)。旧歌曲生成器、参考路线挑选器、简单模板没有因Skill更新自动变成新方法；先确认实际消费了哪些函数与参数，unsupported不算执行。清除旧曲线不等于新函数已经覆盖所有边界。

按[计划与评估](references/planning-and-evaluation.md)记录planned／compiled／native_checked／rendered／checked。音高、音素或speaker条件改变后重新计算两阶段依赖；绑定新工程、波形拼接、全曲增益、哈希、无削波及实际F0。声音好坏与技术跟随分开。没有音频感知工具时明确没有听过；可交付初版，但不宣布自然度解决。

能力范围见[能力考核](references/grounding-and-competence.md)。已研究曲的改版、函数测试或文字解释不证明未见曲能力；不自动恢复暂停goal或提高冻结数据训练资格。
