# 表1实体、字段与标注规范：阶段A

日期：2026-10-09。性质：本项目的工程描述提案；定义的文献有效性与测量可行性待B/D确认。本文不宣称有限维度能穷尽全部唱法、听感或波形，也不把候选结构当成检测器。

## 1. 范围与实体

对象是合成人声及其制作输入、输出和混音呈现的可追溯描述。声源/滤波、生理机制、模型条件、音乐动作和听感分别记录。音乐身份、歌词、动作目的和好坏评价属于上下文，不从信号标量自动反推。

| 实体类型／命名空间 | 保存什么 | 不能混入什么 |
|---|---|---|
| acoustic_observation／ACO | 明确方法下的信号量或估计特征，例如输出F0、振幅、谐波幅度、谱分布 | 输入VOIC数值、未经测量的舌位、听者的自然度判断 |
| temporal_event_or_relation／EVT | 一个或多个观测随时间的过程、锚点先后、跨phone/字/句关系 | 把所有衔接压成一个好坏标量，或从平滑直接推出自然 |
| perceptual_description／PER | 听者原话、比较方向、上下文、评价方式及其允许的多条分解 | 自动命名声区、生理诊断，或把相同RMS当作相同听感 |
| model_or_edit_control／CTRL | 已确认工程入口、单位、引擎读取条件和作用阶段 | 与对应输出观测一对一等同 |
| context_or_format／META | 声道、采样格式、源材料、歌词/音素/音符身份、音乐参照及监听环境 | 当作新的演唱声学原子 |
| hypothesis／HYP | 候选机制、因果路径、生理或音乐解释、未排除项 | 与实际测量或用户标签同列当已确认事实 |

ACO允许标量、向量或有明确定义的特征组。一个组中可单独查询的属性需要字段，不必为了“原子数”拆成无限多行。EVT显式引用ACO轨迹/事件及其时钟；PER可以对应多组ACO/EVT，不能要求唯一逆映射。HYP必须链接证据和反例，且默认未证实。

## 2. 保留、拆分、合并标准

1. 不同观测对象、证据角色或独立时间支持应拆开；L1信号电平与听感响度是必拆实例。
2. 同一对象的方向、强度、速率、持续时间优先作为属性；“大/小”“快/慢”“有意/异常”不是独立原子。
3. 对象耦合不能作为合并理由；两个指标相关也不能视为同义。重复应由对象与定义相同判定。
4. 时间过程可独立标注，但需要注明它是基础量的轨迹或多量关系，不能虚称与基础量数学独立。
5. 可测输出与潜在机制分开。未完成反滤波时保留输出谐波/谱包络；未排除混音或源谱时不命名声道共振漂移。
6. 同词多义保留多个候选分解；未知不能自动归“正常”、用0代替，或塞进“其它”后宣布覆盖。
7. 旧ID固定旧语义。A的拆分只写候选迁移，F应用时才能创建新的正式行；旧实验链接不因迁移而增加观察事实。

## 3. 正式维度与事件的必需字段

| 字段 | 规则 |
|---|---|
| id、entity_type、name、definition_version | 类型与命名空间对应；版本变更不能静默改变旧ID语义 |
| operational_definition、include、exclude | 定义观测对象与边界；包含同义词不能代替定义 |
| observations、method_id、units | 每个代理写实际算法与量纲；无法可靠估计的量标方法候选 |
| time_support、window、hop、clock | 区间、阶段、窗/hop明确；source/score/native/PCM/播放秒轴分开 |
| reference、reference_uncertainty | 音准、时间差、谱差等相对量必须有参照，参照未知则不输出伪精确误差 |
| related_ids、relation_type | 区分同对象属性、耦合、时间依赖、多义候选；不能只写“相关” |
| candidate_controls、control_path_status | 只是可能入口索引；当前读取、支持与听感方向需分别验证 |
| evidence_refs、claim_role、scope | 声学文献、源码、实际输入、输出测量、听觉、工程提案逐说法引用 |
| confirmation_status、unknown_rule | 各层独立状态；不允许“一项通过”覆盖全部层 |

事件实例另需`record_id、material_sha、word/phone/note_identity、comparison_id、purpose、raw_feedback、feedback_scope、candidate_explanations、not_excluded`。原子定义表不保存每个歌词字的完整输入数组，运行材料留在绑定run。

## 4. 证据分层与状态

证据角色并列而非单一高低排名：工程定义提案、原始研究、固定源码、本机配置、实际native输入、PCM测量、听者反馈、跨条件/留出验证。源码可以确认读取公式而不能确认好听；听者可以确认偏假而不能确认F1移动；native输入固定而PCM估计不同也需要分别保存。

独立状态栏：`definition_checked、source_checked、current_engine_support、code_path_checked、measurement_defined、measurement_validated、description_coverage_checked、auditory_label_status`。允许checked/partial/pending/not_supported/not_applicable/unknown，并附原因。本阶段的structural_proposal_only不等于声学定义已通过。

来源ID为SRC:01等，源码机制CODE:01等，实验索引EVID:01等，控制CTRL:C01等；维度ACO:S1不会与原文献S1混淆。旧ID解释依据字段类型或声明表，不对正文所有S1字符串做全局替换。

## 5. 缺口与覆盖的判定

B已复核周期级振幅扰动（shimmer候选ACO:L5）、感知音高（候选PER:P1）与语音可懂度的组件区别。复音/拍频仍需区分独立多F0、次谐波与AM；重音、跨句身份及哭笑等仍有操作/感知缺口。它们不能只凭直觉并入“噪声”或“自然”；D/E记录新增/复用/不在声学层范围的理由，F才正式迁移。

E案例分development与复查集合。进入映射前冻结清单、来源和角色；已有歌曲反馈是回归，不称留出。覆盖计数分结构能记录、观测可复算、真实标签可用三种，不能汇成“百分百好坏可描述”。未知与不适用均不计为检测通过。

## 6. 本阶段文件

[逐行审查](table1-review.md)、[完整审查CSV](table1-row-review.csv)、[结构JSON](table1-row-review.json)和[候选迁移](id-migration.json)由显式研究构建器生成；[构建器说明](../../../research/table1-confirmation/README.md)。B的[31行定义审查](core-definition-review.json)、[30组听感词审查](composite-review.json)及[来源](claim-evidence.json)保留确认缺口。原清单暂不改，具体读取路径、观测与独立覆盖待C–E，不能从文件齐全宣称已验证。
