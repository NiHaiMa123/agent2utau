# 表1观测协议审查：阶段D

2026-10-09。**D为protocol_review_complete_with_explicit_gaps**：原31行/A的47候选实体全部关联协议，另列B的shimmer、感知音高、复音/拍频3项，共50条。协议定义完成不等于所有检测器实现或真实歌唱测量通过；E/F未执行，原清单/ID不迁移。

完整字段见[CSV](measurement-protocols.csv)/[JSON](measurement-protocols.json)，方法来源见[组件来源](measurement-source-review.json)。每项包括对象、输入、阶段/时钟、窗口/hop、公式、单位、质量掩码、参照/不确定性、拒绝条件、实现/验证范围及尚缺证据。所有新窗口/门限均标候选，代码已有常量另列，不设通用好坏阈值。

## 本轮做了什么

- 只读核查11份生产/契约源码，另绑定1份研究数组验证器；源码SHA/行号明确。未修改生产代码、工程、Skill、安装或音频，未运行模型/原生导出。
- 阅读10项官方/作者实验室组件来源（另2页交叉读）；B文献的摘要/范围级缺口原样保持，没有凭D协议填写升级成全文/已验证。
- 运行10组已知数值数组检查，记录真值/实际值/版本/范围；没有生成或播放WAV，数组不是自然度正反例。88项仓库测试与保护绑定由执行审计另记。

## 现有实现的关键边界

| 实现 | 实际量与限制 |
|---|---|
| features.shape_features | 显式输入曲线OLS与极值候选；8样本/150ms/gap40ms、3–12Hz/6c是代码候选常量。峰谷幅度不等于±depth，残差仍含周期。未连接PCM或voiced mask自动验真。 |
| FCPE/RMVPE | 各自原生hop/UV语义、重采样、mono均值需绑定；双估计一致不等于独立真值。本轮不加载权重，未验证真实输出准确率。 |
| onsets.frame_rms | forward窗从frame时间开始，非中心窗；尾部截短并分母改实际样本数。D新矩形中心窗协议若采用需另外实现与验证。 |
| wavcheck.analyze_wav | 先LR算术均值；voiced_fraction是20ms不重叠窗RMS>-50dBFS比例。支持1/2/4字节整数解析，不支持PCM24；>=0.999只近满幅告警，非true peak/声断检测。 |
| controlled_probe.spectral_response | 原生log-mel的每帧bin共同偏移去除；不是PCM/dBFS、formant校正或听觉改善。当前adapter布局限制继续保留。 |
| independent.validate_native / TempoMap | 输入SHA/几何/单位与score时钟契约；native phone时钟不是HFA或实际爆破/元音声学边界。 |

实现引用和哈希见JSON；本轮只记录限制，不把文档更名当作生产修复。

## 复杂方法的拒绝条件

高F0时输出谐波峰、LPC pole和声道共振可能不可辨识；缺足够频率信息、参数稳定性或独立参照时只保留R5输出谱，R1/R2/R6为unknown。这是基于来源的协议限制，未建立一个自动高F0阈值。[UNSW对象区别](https://www.phys.unsw.edu.au/jw/formant.html)、[Burg参数](https://praat.org/manual/Sound__To_Formant__burg____.html)。

周期级jitter/shimmer需要可信pulse、有效周期及配对筛选，不能用10ms F0残差或30/50ms包络替代；歌唱滑音、颤音、强非周期和脉冲不稳时拒绝解释，不迁移临床阈值。[jitter算法](https://praat.org/manual/PointProcess__Get_jitter__local____.html)、[shimmer定义](https://praat.org/manual/Voice_3__Shimmer.html)。

HNR/CPPS只是声明条件下的周期性/噪声代理，不能等同模型VOIC/BREC或“实/假”；完整参数、稳定元音、辅音/泄漏与方法敏感性必须记录。[HNR参数](https://praat.org/manual/Sound__To_Harmonicity__ac____.html)、[CPPS参数](https://praat.org/manual/PowerCepstrogram__Get_CPPS___.html)。

sample peak、true peak、短窗RMS、节目响度和听者响度分别保存。ITU规定的K加权/通道功率/400ms重叠门禁及true-peak重建是方法候选，本仓库未实现/验证符合性；不据LUFS或RMS替代字头反馈。[BS.1770-5 Annex1/2](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf)。

## 数值检查与验证层级

| 检查 | 绑定对象 | 实际验证范围 |
|---|---|
| DVAL:01 | ACO:P1 | Unit conversion only; no FCPE/RMVPE execution, voiced mask accuracy or reference identity truth |
| DVAL:02 | EVT:P2, ACO:P5 | OLS straight-line primitive only; frame residual not cycle jitter or a validated nonperiodic decomposition |
| DVAL:03 | ACO:P4 | Known F0 curve values only; no extractor accuracy, fast-changing vibrato performance or perceived vibrato truth |
| DVAL:04 | ACO:P4, EVT:T5 | Input validation and explicitly supplied region masks; no real phone classification or audible boundary truth |
| DVAL:05 | ACO:R5 | Arithmetic of bound log-mel proxy only; not dBFS, formant truth, acoustic waveform level removal or improvement |
| DVAL:06 | EVT:T1, ACO:T2 | Score tempo conversion only; no PCM offset, model latency, HFA boundary or perceived timing truth |
| DVAL:07 | ACO:L1, EVT:L2, EVT:L4 | Existing frame_rms uses forward window at frame time, not centered window. Numerical levels only, no new audio; no loudness or phonation test |
| DVAL:08 | ACO:L3 | Definition algebra only; no PCM envelope extraction or general AM detector validation |
| DVAL:09 | ACO:X1, ACO:X2 | Known algebraic clip/seam only; does not execute wavcheck, prove true peak, or establish click/破音 thresholds |
| DVAL:10 | ACO:X4 | Channel/downmix identity only; no perceived spatial quality or playback device validation |

反相相关首次用精确-1断言，得到-0.9999999999999998而拒绝；研究验证器改用声明1e-12容差，精确mono消除/功率断言保留后通过。失败/重试日志在新研究run，未修改生产算法。其它数组的通过只限列出的数学/组件，不把对应完整协议measurement_validated升级为true。

## 逐项协议索引

| 协议 | 候选对象 | 窗/时钟 | 单位 | 现有实现状态 |
|---|---|
| MEAS:D01 ACO:P1 输出F0与参照偏差 | PCM周期的估计F0；工程目标单列 | 按各模型原生hop；同元音稳态区；统计覆盖率与有效样本数 | Hz/cents/有效帧比例 | selected_component_source_reviewed |
| MEAS:D02 EVT:P2 慢趋势 | 指定支持内的F0中心走势 | 现有shape_features支持>=0.15s/8样本、相邻gap<=0.04s；并非通用趋势带宽 | cents/s、cents、s | selected_component_source_reviewed |
| MEAS:D03 EVT:P3 换音事件 | 从起始中心到目的中心的轨迹及相位关系 | 整个过渡并含两侧稳定支持；hop使用F0原生值；窗口候选由事件显式给出 | cents/s、cents、ms | method_candidate_not_implemented_here |
| MEAS:D04 ACO:P4 F0周期调制 | 有声中心周围的慢周期运动 | 现有8样本/150ms/gap40ms门禁；3–12Hz/6c为代码候选范围；至少2个完整cycle | Hz、峰谷cents、相位/非对称比例 | selected_component_source_reviewed |
| MEAS:D05 ACO:P5 帧级非周期F0残差 | 声明趋势/周期模型以外的帧残差 | 与原F0相同hop；指定稳态段；分解带宽候选未冻结 | cents、cents/s | selected_component_source_reviewed |
| MEAS:D06 ACO:L1 数字电平 | 逐通道PCM幅度/功率 | 候选中心矩形30/50ms、hop10ms；半开[t-w/2,t+w/2)，取样量化规则/实际样本数需冻结；完整窗不足不补零；整段另报 | FS、dBFS、峰值 | selected_component_source_reviewed |
| MEAS:D07 EVT:L2 非周期强弱包络 | PCM短时电平走势及持续区间 | 候选30/50ms矩形窗、10ms hop；两窗并报敏感性；字头/腹/尾不混平均 | dBFS、dB/s、ms | method_candidate_not_implemented_here |
| MEAS:D08 ACO:L3 振幅周期调制 | 包络中周期性幅度变化 | 候选10ms hop包络；报告RMS窗传递效应；至少3周期且远低于包络Nyquist | Hz、调制指数、相位 | method_candidate_not_implemented_here |
| MEAS:D09 EVT:L4 瞬态电平事件 | 局部能量变化和波形接缝分别观察 | 候选边界±30ms并30/50ms电平；逐sample跳变另列 | dB、FS/sample、ms | method_candidate_not_implemented_here |
| MEAS:D10 ACO:S1 周期性声学支撑代理 | PCM可重复周期结构而非模型VOIC | 候选至少5周期并固定窗；CPP/CPPS各自分析窗/平滑参数完整记录 | HNR/CPP dB、voiced覆盖 | method_candidate_not_implemented_here |
| MEAS:D11 ACO:S2 输出谐波谱形 | 输出谐波幅度/斜率，校正声源谱另列 | 候选稳态>=5周期；Hann窗/hop显式记录；频带/谐波号固定 | dB、dB/oct | method_candidate_not_implemented_here |
| MEAS:D12 ACO:S3 非周期噪声估计 | 特定分解算法的非周期成分 | 随选HNR分析窗；跨phone不混；固定周期数/floor/门限 | dB或算法比例 | method_candidate_not_implemented_here |
| MEAS:D13 ACO:S4 噪声谱形 | 已声明噪声/残差分量的频带分布 | 候选20/40ms Hann、10ms hop；频带冻结；足够带宽 | Hz、dB或相对能量 | method_candidate_not_implemented_here |
| MEAS:D14 ACO:S5 多周期/次谐波结构 | 相对基准周期的重复组织/低阶分量 | 候选8–20周期并时频两看；频率分辨率不足不强行检峰 | Hz、周期倍数、相对dB | method_candidate_not_implemented_here |
| MEAS:D15 ACO:S7 周期级jitter | 有效相邻声周期时长扰动 | 长持续元音；按有效cycle及有效pair计数，不拿10ms F0帧作周期 | 秒、% | method_candidate_not_implemented_here |
| MEAS:D16 ACO:T2 音素时长 | 标签边界之间的持续时间，输入/声学两层 | 逐phone/元音核/韵尾半开区间；各边界uncertainty | ms、ticks、模型帧 | selected_component_source_reviewed |
| MEAS:D17 ACO:R1 声道共振位置候选 | 输出峰/模型pole/声道共振分开 | Praat候选effective25ms、实际Gaussian50ms、hop6.25ms；ceiling/poles不当通用固定 | Hz、置信区间 | method_candidate_not_implemented_here |
| MEAS:D18 ACO:R2 共振带宽候选 | 已识别共振峰的宽度 | 稳态同R1；窗分辨率和F0间距均需记录 | Hz | method_candidate_not_implemented_here |
| MEAS:D19 ACO:R4 鼻耦合相关谱线索 | 候选鼻化谱型而非鼻感 | 稳定核与鼻邻接分层；窗同R5并记录多尺度 | Hz、dB、关系标签 | method_candidate_not_implemented_here |
| MEAS:D20 ACO:R5 输出谱包络 | 输出能量形状；保留代理的算法单位 | PCM候选20/40ms Hann、10ms hop；原生mel按模型hop/frame clock，现有spectral_response选[start,end]闭区间，不静默转半开 | dB/Hz或native log-mel单位（不能混） | selected_component_source_reviewed |
| MEAS:D21 ACO:R6 反共振候选 | 可能的传递零点；输出凹陷先归R5 | 稳定段、多窗/多激励；所需带宽未冻结 | Hz、dB | method_candidate_not_implemented_here |
| MEAS:D22 ACO:X1 削波/过载观测 | 数字rails/超限与true peak分开 | 逐sample计数/连续rail长度；true peak按已验证重建器独立估计 | FS、次数、连续samples、dBTP候选 | selected_component_source_reviewed |
| MEAS:D23 ACO:X2 采样接缝观测 | PCM边界值/斜率变化 | 逐sample边界并候选±5/30ms；记录交叉淡化范围 | FS/sample、ms | method_candidate_not_implemented_here |
| MEAS:D24 ACO:X3 声部电平关系 | 同步stem的时频功率关系 | 候选30/50ms与频带，合成PCM另报交叉项 | dB、交叉功率 | method_candidate_not_implemented_here |
| MEAS:D25 ACO:X4 左右通道关系 | LR功率/互相关及mono兼容 | 候选50/200ms；逐频带/延迟范围冻结 | 相关系数、dB、ms | method_candidate_not_implemented_here |
| MEAS:D26 ACO:X6 重复纹理观测 | 跨帧/样本重复与可能的周期纹理 | 候选跨2–10个模型hop及乐句区；lag与支持显式 | lag samples/ms、相似度、重复段长度 | method_candidate_not_implemented_here |
| MEAS:D27 ACO:X7 衰减/混响关系候选 | 系统冲激响应或受限尾声衰减代理 | IR完整衰减支持；尾声窗不能把后续发声算reverb | dB/s、s | method_candidate_not_implemented_here |
| MEAS:D28 EVT:S4 噪声出现阶段 | 候选噪声/摩擦/呼吸相对phone的时位 | 字头/核/尾区间与uncertainty；20/40ms窗口边界效应 | ms、phase标签 | method_candidate_not_implemented_here |
| MEAS:D29 EVT:S6 发声中断/恢复 | 可靠周期建立/失去及上下文关系 | 内部唱区；检测hop与gap精度，排除前后静音/AP/SP | ms、次数、覆盖比例 | method_candidate_not_implemented_here |
| MEAS:D30 EVT:R3 字内谱过渡 | 输出谱轨迹或可靠共振轨迹随时间 | 整个元音含两端；声明窗/hop、延迟与平滑 | log谱单位/s、Hz/s、ms | method_candidate_not_implemented_here |
| MEAS:D31 EVT:T1 整体落点关系 | 多时钟/多种起点之间的关系 | 逐事件；边界给区间不确定性；不把相邻帧当无限精确 | ticks、ms、拍比例 | selected_component_source_reviewed |
| MEAS:D32 EVT:T3 辅音动作 | 辅音类别内的爆破/摩擦/闭塞与周期建立 | 类别对应起止；候选5–20ms短谱+上下文，不统一一个元音窗 | ms、Hz、dB | method_candidate_not_implemented_here |
| MEAS:D33 EVT:T4 起声协调关系 | 增益建立、周期建立、辅音/元音边界的相对时序 | 入口前后候选80–200ms，窗口/hop记录并给uncertainty | ms、dB/s、phase | method_candidate_not_implemented_here |
| MEAS:D34 EVT:T5 跨音素衔接关系 | 边界上的时钟/电平/音高/谱连续性分别观察 | 边界候选±30/80ms并两侧稳态；跨元音谱差不直接设阈值 | ms、cents、dB、谱单位 | selected_component_source_reviewed |
| MEAS:D35 EVT:T6 释放/收声关系 | 周期结束、电平衰减与音素尾部的相对顺序 | 声明字尾至后音段，窗延迟与混响尾分开 | ms、dB/s | method_candidate_not_implemented_here |
| MEAS:D36 EVT:T7 呼吸声事件 | 可能的吸气/呼气声音及其时位 | 整个候选呼吸区+两侧；S4短谱与局部电平 | ms、dBFS、事件标签 | method_candidate_not_implemented_here |
| MEAS:D37 EVT:T8 韵尾身份事件 | 韵尾音素存在与声学支持 | 尾部phone/音节和后字语境；不能只看整元音RMS | 类别、ms、presence/unknown | method_candidate_not_implemented_here |
| MEAS:D38 EVT:T9 间隙/静音组织 | 唱段之间空隙与音乐/语义参照 | 逐gap与句级支持；0.9s voiced_blocks门限是代码分组，不是普遍断句规则 | ms、拍比例、结构标签 | selected_component_source_reviewed |
| MEAS:D39 META:X5 格式/输出链元数据 | 编码、采样率、通道与每次变换 | 文件级/每转换节点；PCM样本时轴另记 | Hz、bit、channels、线性gain/dB | selected_component_source_reviewed |
| MEAS:D40 PER:L1 感知响度 | 听者在呈现条件下感到的大/小 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D41 PER:R4 鼻感 | 听者所说鼻/堵等标签 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D42 PER:S1 支撑/实的听感 | 有芯、偏实、偏假的主观关系 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D43 PER:T3 语音清晰/可懂度 | 听到的辅音清楚与词识别 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D44 PER:X1 破音/失真听感 | 听者报告的破/顶/裂 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D45 PER:X2 数码/拼接质地听感 | 被听到的click/机械/重复纹理 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D46 PER:X3 掩蔽/平衡听感 | 听者在mix中对目标声部可辨认与平衡的感受 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D47 PER:X4 空间/距离听感 | 听者所说近远、宽窄、空间 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D48 PER:P1 感知音高（B候选） | 听到的高低/音程身份 | 标签范围可为字头/腹/尾/词/乐句；听者约秒数保留uncertainty，不强造精确hop | 原文/有序评分/识别率（须任务定义） | listening_record_protocol_only |
| MEAS:D49 ACO:L5 周期级shimmer（B候选） | 有效相邻周期幅度扰动 | 长稳定元音周期级；不是30/50ms RMS包络 | %/dB | method_candidate_not_implemented_here |
| MEAS:D50 CAND:MULTI_F0 复音/拍频（B开放候选） | 多个独立周期源、差频包络与其它调制的区别 | 候选支持至少数个差频周期；频率近时须足够长窗，不桥过非平稳段 | Hz、源数候选、ms | method_candidate_not_implemented_here |

## 后续与人工试听

下一步E先冻结独立覆盖清单及角色，再映射这些候选；已有问题/可用/无差别反馈是回归证据，未知字/未听细分标签仍unknown。听者的原话确认感知范围，不自动确认声学病因；测量也不能代替听者。新的因果对照按后续表2的冻结设计推进，本轮不追加合成。

D确定性协议已列；高F0共振、声源分解、鼻化、次谐波/复音、真实声学边界、语言辅音、复杂响度/空间和任何真实音频检测性能仍有缺口。F前不静默迁移ID或改表2绑定。当前[计划](../../../plan.md)，检查见[执行审计](table1-execution-audit.json)。
