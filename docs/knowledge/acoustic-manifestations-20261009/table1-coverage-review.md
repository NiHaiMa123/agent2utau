# 表1描述覆盖审查：阶段E

2026-10-10。**E为coverage_review_complete_with_explicit_gaps**。先冻结42项，再完成36项主映射，最后复查6项；原表/ID尚未正式迁移，F未执行。没有新音频、模型执行、作者数组复用或Agent试听。

独立清单见[冻结JSON](coverage-checklist.json)，逐项映射见[CSV](description-coverage.csv)/[JSON](description-coverage.json)。清单来自用户原证据、音乐任务、原始研究和作者输入结构，未使用B的自拟反例，也不是31个词各举一例。

## 取样与角色

18项已有反馈/未知边界、12项未录制音乐任务、8项外部研究/方法条件、4项作者结构。U18的313字只算一个未知总体边界；6个BREC条件共用一个反馈原话。三份原始研究提供任务范围，没有导入/播放它们的录音；同论文拆成几个问题不增加独立实验数。

6项复查为M10、M12、L04、L05、L07、A04。这是冻结后延迟映射的过程复查，Agent先前已见A–D，不能叫盲法、全新音频留出集或泛化通过；数量不按映射结果增删。主映射checkpoint及SHA在新ignored研究run。

## 分开报告的结果

| 项目 | 数量/含义 |
|---|---|
| 可按现有候选结构记录 | 34项；限清单指定对象与范围 |
| 结构只能部分表达 | 8项；明确列出上下文/关系/任务缺口 |
| 有既有用户标签 | 16行；不是16个独立反馈实验，也不全为正常/异常标签 |
| 有完整可靠测量支撑该案例结论 | 0项本轮可宣布通过；历史输入/PCM代理的具体事实继续有效，不能升级为破音/实感等测量真值 |
| 链接候选实体 | 34/50；未链接项仍是未覆盖，不能因清单全映射声称维度穷尽 |
| 新标签/新音频/独立音频留出 | 均0 |

取样轴逐项见JSON。稳定/变化、有意/异常、字头/腹/尾、低/高、不同元音/辅音、同字跨上下文、单点/乐句均有问题/例的来源，来源角色仍分开。U10只是整元音RMS接近且局部电平/谱不同，严格等电平隔离波形缺；纯人声/混音仅已有交付绑定，不是分别听觉验收。不能把问题清单的存在当成实际歌唱案例全部齐备。

未被清单链接的16个候选实体：ACO:P5, ACO:S1, ACO:S2, ACO:S3, ACO:S4, ACO:S5, ACO:R2, ACO:R4, ACO:R6, ACO:X4, ACO:X6, EVT:S4, EVT:T8, PER:R4, PER:X2, PER:X4。它们保持未覆盖，而非按相邻案例代填通过。

## 已发现的具体缺口

音乐目的与层级：整句重音/动机、调式和和声参照、快速转音的目标身份需要具体schema和操作规则；通用context字段可保存文字但不能宣称完整表达。情绪及听者差异：多标签情绪、同一音频不同听者策略和评价对象缺明确任务记录。发声角色：演唱者自反馈遮蔽不能与听者混音掩蔽共用一个解释。双音/泛音：被增强谐波的第二听觉音高与多个独立F0的源数不能混为一类。F应补上下文/关系字段并保留开放候选，不为达到100%把它们塞入其它/残差。

真实音频测量缺口保留：高F0共振、pulse jitter/shimmer、辅音/双元音内部动作、跨字/句连接、声断与响度/空间。结构能够保存unknown，不意味着检测器已经可靠或已有标签覆盖所有维度。

## 标签与来源纠错

原5个位置标签及接受抱C不扩展为整曲；可以不补成完全无破音，都一样不补成三处均正常，全部没区别只否定该剂量/条件的可感知差别。果反馈的好像和响度下降位置未知保留。313字不是正常样本，作者+、AP/SP、note时长及音区不是声音质量标签。

冻结U17误写word-282；原反馈JSON明确word295_unknown_retained=true，本次增补word295身份勘误及SHA。冻结清单原字节不改、仍42项、标签仍unknown。表2conditional-responses.json的部分文字已有乱码；不自动改旧表/记录，E的反馈词从可读原报告核查，数值ID/已存音频SHA独立引用。F正式整合前必须公开或纠正派生文字，不能把乱码再当原话。

## 逐项映射

| 案例 | 角色/分区 | 候选对象 | 结构状态 | 缺口 |
|---|---|---|---|
| CASE:EU01 1:27果原版，uo/E4，同字问题侧 | baseline_problem/main_mapping | PER:S1, ACO:P1, ACO:R5, EVT:T4 | representable_with_scope | MEASUREMENT |
| CASE:EU02 3:04抱原版，ao/B4，同字问题侧 | baseline_problem/main_mapping | PER:S1, ACO:P1, ACO:R5, EVT:T4 | representable_with_scope | MEASUREMENT |
| CASE:EU03 1:33之原版，ir/F#4，相对偏实侧 | relative_reference/main_mapping | PER:S1, ACO:T2, EVT:T3 | representable_with_scope | LABEL_SCOPE |
| CASE:EU04 2:56只原版，ir/A4，相对偏实侧 | relative_reference/main_mapping | PER:S1, ACO:T2, EVT:T3 | representable_with_scope | LABEL_SCOPE |
| CASE:EU05 约3:17果原版，相同MIDI64跨上下文 | local_usable/main_mapping | PER:S1, EVT:T5, ACO:P1, ACO:R5 | representable_with_scope | LABEL_SCOPE |
| CASE:EU06 3:04抱C，145ms进入的局部可用变体 | local_usable/main_mapping | PER:S1, PER:X1, EVT:T4, EVT:T5, ACO:R5 | representable_with_scope | LABEL_SCOPE |
| CASE:EU07 抱TENC取消，数值响应但未感知区别 | no_difference/main_mapping | PER:S1, ACO:R5 | representable_with_scope | PROXY |
| CASE:EU08 抱SHFC初B，更实且字头破音 | benefit_with_side_effect/main_mapping | PER:S1, PER:X1, EVT:T4, EVT:S6, ACO:X1, ACO:R5 | representable_with_scope | MEASUREMENT |
| CASE:EU09 约1:14/3:04/3:31原抱的相似性定位 | similarity_only/main_mapping | PER:S1, EVT:T5, ACO:P1 | representable_with_scope | LABEL_SCOPE |
| CASE:EU10 果SHFC B与邻字这：无改善且响度下降 | no_benefit_with_side_effect/main_mapping | PER:S1, PER:T3, PER:L1, EVT:T3, EVT:L4, ACO:R5 | representable_with_scope | MEASUREMENT |
| CASE:EU11 BREC -10：1:27问题果 | no_difference/main_mapping | PER:S1, ACO:R5 | representable_with_scope | PROXY |
| CASE:EU12 BREC -10：1:33偏实之 | no_difference/main_mapping | PER:S1, ACO:R5 | representable_with_scope | PROXY |
| CASE:EU13 BREC -10：2:56偏实只 | no_difference/main_mapping | PER:S1, ACO:R5 | representable_with_scope | PROXY |
| CASE:EU14 BREC -10：3:04问题抱 | no_difference/main_mapping | PER:S1, ACO:R5 | representable_with_scope | PROXY |
| CASE:EU15 BREC -10：3:17可用果 | no_difference/main_mapping | PER:S1, ACO:R5 | representable_with_scope | PROXY |
| CASE:EU16 BREC -10：已接受抱C | no_difference/main_mapping | PER:S1, ACO:R5 | representable_with_scope | PROXY |
| CASE:EU17 约3:44果，MIDI64；第三段未获标签 | unknown_control/main_mapping | PER:S1, ACO:P1, EVT:T5 | representable_with_scope | IDENTITY |
| CASE:EU18 318字中313字未获原版听感标签的集合 | unknown_population/main_mapping | PER:S1, ACO:T2 | partial_structure | POPULATION |
| CASE:EM01 长音保持直音，稳定可为有意；是否错误需音乐目标 | unrecorded_task_question/main_mapping | ACO:P1, EVT:P2, ACO:P4 | representable_with_scope | INTENT |
| CASE:EM02 一整句渐强至重音，再回落；单字平均无法保存组织 | unrecorded_task_question/main_mapping | EVT:L2, EVT:T1, ACO:L1, PER:L1 | partial_structure | PHRASE |
| CASE:EM03 弱收尾、硬切与尾混响三种候选；可听收声关系 | unrecorded_task_question/main_mapping | EVT:T6, ACO:X2, ACO:X7 | representable_with_scope | MEASUREMENT |
| CASE:EM04 上行滑音到目标，保留到达身份/参照，不把全部弯曲叫异常 | unrecorded_task_question/main_mapping | EVT:P3, ACO:P1, EVT:T1 | representable_with_scope | INTENT |
| CASE:EM05 下行滑音/尾滑，源音与目的音、字尾和后字关系 | unrecorded_task_question/main_mapping | EVT:P3, EVT:T6, EVT:T5 | representable_with_scope | INTENT |
| CASE:EM06 字头倚音/上挑后到正音，迟到可能有意 | unrecorded_task_question/main_mapping | EVT:P3, EVT:T4, EVT:T1 | representable_with_scope | INTENT |
| CASE:EM07 一字跨多音melisma；多note不能多算歌词核 | unrecorded_task_question/main_mapping | ACO:T2, EVT:P3, EVT:T5 | representable_with_scope | LANGUAGE |
| CASE:EM08 跨辅音/元音的连唱；正常换型与声线断层分开 | unrecorded_task_question/main_mapping | EVT:T3, EVT:T5, EVT:R3 | representable_with_scope | LANGUAGE |
| CASE:EM09 断唱与合法休止；中断并非必定破音 | unrecorded_task_question/main_mapping | EVT:T9, EVT:S6, EVT:T6 | representable_with_scope | INTENT |
| CASE:EM10 短时快速转音/颤音两目标交替，不能把所有周期当vibrato | unrecorded_task_question/deferred_mapping_recheck | EVT:P3, ACO:P4, EVT:T1 | partial_structure | ORNAMENT |
| CASE:EM11 颤音晚进入/退出且速率深度变化；与AM/谱变化分开 | unrecorded_task_question/main_mapping | ACO:P4, ACO:L3, EVT:P2, EVT:T4, EVT:T6 | representable_with_scope | MEASUREMENT |
| CASE:EM12 同一频率在不同调式/和声/参照下的音准意义 | unrecorded_task_question/deferred_mapping_recheck | ACO:P1, PER:P1, EVT:T1 | partial_structure | REFERENCE |
| CASE:EL01 连/断与快/慢三和弦任务；短音的测量支持区别 | external_task_scope_no_local_audio/main_mapping | ACO:P1, EVT:P3, ACO:T2, EVT:T9 | representable_with_scope | EXTERNAL |
| CASE:EL02 演唱者听觉反馈被遮蔽；与听者混音清晰度区分 | external_task_scope_no_local_audio/main_mapping | ACO:X3, PER:X3, ACO:P1 | partial_structure | TASK_ROLE |
| CASE:EL03 同一乐句中性/怒/喜/惧/悲的多标签感知任务 | external_task_scope_no_local_audio/main_mapping | ACO:P4, EVT:L2, ACO:R5, ACO:T2 | partial_structure | EMOTION |
| CASE:EL04 相同呈现的听者评分差异/多情绪并存 | external_task_scope_no_local_audio/deferred_mapping_recheck | PER:L1, PER:S1 | partial_structure | EMOTION |
| CASE:EL05 sygyt低持续音与被增强谐波旋律；双音听感未必双独立源 | external_task_scope_no_local_audio/deferred_mapping_recheck | ACO:R5, ACO:P1, PER:P1, CAND:MULTI_F0 | partial_structure | OVERTONE |
| CASE:EL06 高F0谐波稀疏时共振不可辨识的例 | external_task_scope_no_local_audio/main_mapping | ACO:R1, ACO:R5, ACO:P1 | representable_with_scope | MEASUREMENT |
| CASE:EL07 持续元音声断检测条件，正常清辅音/休止/失败的反查 | external_task_scope_no_local_audio/deferred_mapping_recheck | EVT:S6, EVT:T3, EVT:T9 | representable_with_scope | MEASUREMENT |
| CASE:EL08 滑音/强AM与pulse jitter/shimmer的尺度混淆 | external_task_scope_no_local_audio/main_mapping | ACO:S7, ACO:L5, ACO:P4, ACO:L3 | representable_with_scope | MEASUREMENT |
| CASE:EA01 花海作者note21的+续音：输入延展结构，不推听感 | read_only_structure_not_audio_label/main_mapping | ACO:T2, EVT:P3, EVT:T5 | representable_with_scope | AUTHOR |
| CASE:EA02 雨爱作者重复de，在不同tone/duration的输入上下文 | read_only_structure_not_audio_label/main_mapping | ACO:T2, EVT:T1, EVT:T5 | representable_with_scope | AUTHOR |
| CASE:EA03 作者最后一页AP/SP、note间隙及多part；结构不证明实际呼吸 | read_only_structure_not_audio_label/main_mapping | EVT:T7, EVT:T9, META:X5 | representable_with_scope | AUTHOR |
| CASE:EA04 三作者工程不同谱面音区；不是实测F0或高音质量标签 | read_only_structure_not_audio_label/deferred_mapping_recheck | ACO:P1, ACO:T2, META:X5 | representable_with_scope | AUTHOR |

## 研究来源与适用范围

- [ESRC:01 Mürbe et al. 2003, Auditory and kinesthetic feedback in singing](https://www.isca-archive.org/maveba_2003/murbe03_maveba.pdf)：printed pp183–186; methods/limitations；full_paper_text_read；28起始学生/22复查；三和弦、连/断、快/慢和反馈遮蔽；不是听者混音掩蔽模型，也不迁移人体训练因果到模型。
- [ESRC:02 Jansens, Bloothooft & de Krom 1997, Perception and acoustics of emotions in singing](https://www.isca-archive.org/eurospeech_1997/jansens97_eurospeech.pdf)：printed pp2155–2158; material, perception, regression cautions；full_paper_text_read；同一德语乐句/14专业歌手/25听者；多情绪及评分差异，只用于任务/标签边界，不套系数或中文情绪公式。
- [ESRC:03 Kob & Neuschaefer-Rube 2003, Acoustic analysis of overtone singing](https://www.isca-archive.org/maveba_2003/kob03_maveba.pdf)：printed pp187–190; introduction/methods；selected_fulltext_sections_read；一个sygyt演唱者的谱/超声/阻抗观察；不是独立双F0或所有撕裂唱法真值。
- [ESRC:04 UNSW formant/resonance/pole distinction](https://www.phys.unsw.edu.au/jw/formant.html)：high-F0 example and object distinction；component_explanation_read；作者实验室对象与可辨识性解释；非新歌唱样本。
- [ESRC:05 Praat Voice breaks](https://praat.org/manual/Voice_1__Voice_breaks.html)：continuous sustained vowel and locally unvoiced distinctions；component_method_conditions_read；持续元音方法，不把正常辅音/休止或检测失败都叫破音。
- [ESRC:06 Praat jitter/shimmer conditions](https://praat.org/manual/PointProcess__Get_jitter__local____.html)：period and pair selection; D source for shimmer separately retained；inherited_D_component_read_not_reexecuted；周期级测量条件提问，无新的录音、pulse或临床阈值。

下一步F整合正式修订、ID迁移及第一/第二层引用，保留原证据/SHA和上述缺口。测量与描述覆盖不代替听者，新因果试听按后续表2冻结方案推进。[当前计划](../../../plan.md)、[执行审计](table1-execution-audit.json)。
