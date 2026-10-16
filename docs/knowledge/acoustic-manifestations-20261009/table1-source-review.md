# 表1文献和听感词核对：阶段B

日期：2026-10-09。31行核心定义及30组听感词已逐项审查；累计核对30条说法/25个来源页面。状态为reviewed_with_explicit_gaps，不是全部事实、测量或听觉确认通过。源码控制路径在C，观测验证在D，独立覆盖在E。

资料只用原始研究、官方方法/范围文档及作者实验室解释，证据角色逐条记录。部分全文访问验证或付费，保留摘要/公开范围级别；不绕过访问限制。Praat shimmer仅复核Voice 3定义，未声称全部细节实现已核查。

| 说法ID | 已核对说法 | 来源与位置 | 不能推出什么 |
|---|---|---|---|
| CLAIM:001 | local jitter比较相邻周期时长，通常在长持续元音测量 | [Voice 2. Jitter](https://praat.org/manual/Voice_2__Jitter.html)，Jitter(local)与首段；official_method_checked | 不把帧级F0残差或歌曲任意段落的波动当生理jitter；不移植临床阈值 |
| CLAIM:002 | local shimmer比较相邻周期幅度，需周期级振幅信息 | [Voice 3. Shimmer](https://praat.org/manual/Voice_3__Shimmer.html)，Shimmer(local)与首段；official_method_checked | 30/50ms包络AM不是相邻周期幅度扰动；新增ACO:L5候选，检测未实现 |
| CLAIM:003 | local jitter以相邻有效周期时长绝对差均值除以有效周期均值，且排除不合法间隔/配对 | [PointProcess: Get jitter (local)...](https://praat.org/manual/PointProcess__Get_jitter__local____.html)，Algorithm及Period floor/ceiling/Maximum period factor；official_method_checked | 未通过周期定位验证就不报告数值；筛选后分子/分母有效集合须按算法实现 |
| CLAIM:004 | 把SNR作为HNR的解释限定在可假设周期性的信号，例如持续元音 | [Voice 4. Additive noise](https://praat.org/manual/Voice_4__Additive_noise.html)，正文首段；official_method_checked | 不能把摩擦音、强不规则段或所有CPP代理读作真实漏气比例 |
| CLAIM:005 | 参数Window length为有效窗长；0.025s设置对应实际0.050s高斯窗，formant ceiling/阶数/预加重影响估计 | [Sound: To Formant (burg)...](https://praat.org/manual/Sound__To_Formant__burg____.html)，Settings/Window length与Algorithm；official_method_checked | 不能将任意程序25ms窗与此设置视作同窗；LPC结果不是自动真实声道真值 |
| CLAIM:006 | 文章明确高F0歌声的LPC共振估计可能偏向邻近谐波 | [Dark tone quality and vocal tract shaping in soprano song production: Insights from real-time MRI](https://pmc.ncbi.nlm.nih.gov/articles/PMC8273971/)，§2.2.1；fulltext_section_checked | 均值减弱误差的讨论依赖误差分布假设，不能保证本曲短字F1/F2准确；原SRC09标题需在F改为真实论文标题 |
| CLAIM:007 | 相同暗色目标下个体声道变化存在差异，研究未做显式感知验收 | [Dark tone quality and vocal tract shaping in soprano song production: Insights from real-time MRI](https://pmc.ncbi.nlm.nih.gov/articles/PMC8273971/)，§2.1.1与Discussion；fulltext_section_checked | 不能从本曲顶/后缩主观标签反推喉位、舌位；更不能推导GENC/SHFC剂量 |
| CLAIM:008 | 联合模型用谐波/非谐波源、声道传递、F0与振幅重建声质；摘要报告200份voice token实验 | [Validating a psychoacoustic model of voice quality](https://pubmed.ncbi.nlm.nih.gov/33514179/)，Abstract实验1/2；abstract_checked_fulltext_pending | 不证明本项目31或47实体足以覆盖整曲音乐/审美，也不证明相同输入会有相同感知 |
| CLAIM:009 | RMS是指定时间区间平方均值的平方根；Praat声压单位与数字PCM需分清 | [Sound: Get root-mean-square...](https://praat.org/manual/Sound__Get_root-mean-square___.html)，Mathematical definition；official_method_checked | 未校准PCM不能报Pa或绝对SPL；本项目dBFS的归一化参考要在D另定 |
| CLAIM:010 | 声压强度dB以20微帕为声压参照，与数字满刻度参照不同 | [Sound: Get intensity (dB)](https://praat.org/manual/Sound__Get_intensity__dB_.html)，Algorithm；official_method_checked | 不能将任意wav的dBFS直接说成dB SPL或感知响度 |
| CLAIM:011 | 四段源谱参数H1-H2、H2-H4、H4-近2kHz、近2k-近5kHz是谐波幅度差，需明确频点 | [Modeling the voice source in terms of spectral slopes](https://pages.ucsd.edu/~mgarellek/files/Garellek_etal_2016_JASA.pdf)，§II.A.1/2；fulltext_methods_checked | 幅度差dB不自动等于dB/oct斜率；分段方案不证明所有维度完全独立 |
| CLAIM:012 | 先逆滤波选代表周期再重复20脉冲，并用分析合成调整源/滤波，避免直接用未校正输出谱代替源谱 | [Modeling the voice source in terms of spectral slopes](https://pages.ucsd.edu/~mgarellek/files/Garellek_etal_2016_JASA.pdf)，§II.A.2与Discussion；fulltext_methods_checked | 不是本项目已实现的算法；高F0、噪声及声道影响仍需单独验证 |
| CLAIM:013 | 噪声和谐波谱的感知敏感度相互影响，不能用单一噪声能量替代听感 | [Perceptual interaction of the harmonic source and noise in voice](https://pmc.ncbi.nlm.nih.gov/articles/PMC3283904/)，§II.A/II.B与Discussion；fulltext_methods_results_checked | 分析合成任务不是Yousa；BREC-10不等于本研究NHR变化，未获区别的原因不能据此确诊 |
| CLAIM:014 | 389份病理声样本中20份有次谐波且都被判断粗糙，其中8份jitter和/或shimmer正常 | [Acoustic characteristics of rough voice: subharmonics](https://pubmed.ncbi.nlm.nih.gov/9075175/)，Abstract；primary_abstract_search_checked_fulltext_pending | 8份不代表两指标均正常；不将20/389作歌声普遍发生率；不是合成模型病理诊断 |
| CLAIM:015 | 相同调制问题的颤抖感还受声质/元音等条件影响，女声pressed条件被评为更摇晃 | [The effects of physiological adjustments on the perceptual and acoustical characteristics of vibrato as a model of vocal tremor](https://pubmed.ncbi.nlm.nih.gov/27908094/)，Abstract；abstract_checked_fulltext_pending | 20是听者而非歌手数；不据此定义病理颤抖或本曲P4好坏阈值；本次仅摘要 |
| CLAIM:016 | 同音高/元音的M2相较M1接触商通常低0.27，R1/R2通常低65/90Hz，个体策略不同 | [Vocal tract resonances in singing: variation with laryngeal mechanism for male operatic singers in chest and falsetto registers](https://pubmed.ncbi.nlm.nih.gov/24437789/)，Abstract；abstract_checked_fulltext_pending | 0.27不是相对27%；生理测量不能从神经音频/VOIC推得；无统一SHFC方向/剂量 |
| CLAIM:017 | 不同极端声效有不同声学响应，多数条件Qx/Fx不显著变化，不能把所有粗糙归为同一机制 | [Extreme Vocal Effects Distortion, Growl, Grunt, Rattle, and Creaking as Measured by Electroglottography and Acoustics in 32 Healthy Professional Singers](https://pubmed.ncbi.nlm.nih.gov/34972633/)，Abstract；abstract_checked_fulltext_pending | 不推断本曲健康/病理或生理动作；本机TENC不等于人体声效控制，只有摘要级复核 |
| CLAIM:018 | 周期基频与听者感知音高是不同对象，缺基频时谐波组织仍可提供音高线索 | [Voice acoustics: an introduction](https://www.phys.unsw.edu.au/jw/voice.html)，Pitch与source/filter说明；author_lab_explanation_checked | 不能把一个F0估计当全部音高感；复音多F0及音乐目标判断另需协议 |
| CLAIM:019 | 元音滤波、辅音噪声/事件和口鼻耦合需区别；口鼻通道可带来共振及反共振 | [Voice acoustics: an introduction](https://www.phys.unsw.edu.au/jw/voice.html)，Speech sounds与Nasalisation；author_lab_explanation_checked | 不提供中文词表时长阈值、鼻化检测器或本模型生理标签 |
| CLAIM:020 | 输出谱包络峰、声道共振与模型极点常同称formant，频率并非总重合 | [Formant: what is a formant?](https://www.phys.unsw.edu.au/jw/formant.html)，正文三种用法与harmonics示例；author_lab_explanation_checked | 应报告实际估计的对象；LPC峰线不能证明口腔姿态，更不能统一估计所有高F0元音 |
| CLAIM:021 | 官方voice breaks基于超过1.25/pitch floor的周期间隔；unvoiced比例另依阈值 | [Voice 1. Voice breaks](https://praat.org/manual/Voice_1__Voice_breaks.html)，Number/Degree of voice breaks；official_method_checked | 无周期辅音/停顿及定位失败不能自动归异常；不搬临床阈值至整曲 |
| CLAIM:022 | 响度是知觉量，声压、频谱/带宽和时长等条件影响它；phon与sone不同 | [ISO 532-2:2017 Acoustics — Methods for calculating loudness — Part 2: Moore-Glasberg method](https://www.iso.org/obp/ui?_escaped_fragment_=iso%3Astd%3Aiso%3A532%3A-2%3Aed-1%3Av1%3Aen)，公开Scope与§3.15–3.18；official_scope_definitions_checked_algorithm_pending | 只读公开范围/定义，未读取付费算法；未校准wav不能直接当绝对sone真值 |
| CLAIM:023 | 此方法覆盖平稳与时变声音，但给超过5秒时变声一个总体响度值在其范围外 | [ISO 532-3:2023 Acoustics — Methods for calculating loudness — Part 3: Moore-Glasberg-Schlittenlacher method](https://www.iso.org/standard/69856.html)，公开Abstract；official_scope_only_algorithm_pending | 只读摘要而非完整算法；这不是说所有节目整曲响度方法均无效 |
| CLAIM:024 | F0调制中的谐波与共振关系可改变输出AM，不能只从DYN解释全部包络 | [Characterization of Source-Filter Interactions in Vocal Vibrato Using A Neck-Surface Vibration Sensor: A Pilot Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8995401/)，Abstract/Introduction与Discussion；fulltext_methods_results_checked | 物理/人体研究为机制候选，不证明当前神经声码器AM的唯一病因 |
| CLAIM:025 | 119有效试次中F0调制平均约4.8Hz；AM速率约6.4Hz颈表/8.4Hz麦克风，两种观测不相同 | [Characterization of Source-Filter Interactions in Vocal Vibrato Using A Neck-Surface Vibration Sensor: A Pilot Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8995401/)，Methods/Results；fulltext_methods_results_checked | 平均不是普遍理想速率；该文幅度深度(max-min)/(max+min)不能混成其它百分比定义 |
| CLAIM:026 | VOT描述塞音释放到准周期起声的间隔，重音/语境影响它 | [Some Effects of Context On Voice Onset Time in English Stops](https://journals.sagepub.com/doi/10.1177/002383096701000101)，出版社Abstract；publisher_abstract_checked_fulltext_pending | 不能扩为所有音素/中文普遍理想时长；VEL的值不是VOT |
| CLAIM:027 | 目标辨认依竞争声包络空隙和声线差异等条件，不能仅用总电平解释可懂度 | [Masking Effects in the Perception of Multiple Simultaneous Talkers in Normal-Hearing and Cochlear Implant Listeners](https://pmc.ncbi.nlm.nih.gov/articles/PMC7180303/)，Abstract/Introduction；fulltext_abstract_intro_checked | 语音竞争不是乐器伴奏；不提供当前歌唱遮蔽阈值或ASR真值 |
| CLAIM:028 | 表演空间的混响/相关房间参数有规定测量方法，包括数字脉冲响应技术 | [ISO 3382-1:2009 Acoustics — Measurement of room acoustic parameters — Part 1: Performance spaces](https://www.iso.org/standard/40979.html)，公开Abstract；official_scope_only_algorithm_pending | 本次未读取详细算法；未知歌曲混音的盲RT估计、远近/宽度听觉不能据此标已验证 |
| CLAIM:029 | 节目响度方法含K加权/通道均方/加权求和；400ms块75%重叠，-70LKFS及相对-10dB两道门限 | [ITU-R BS.1770-5 Algorithms to measure audio programme loudness and true-peak audio level](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf)，Annex 1及recommendations Note 1；official_algorithm_sections_checked | 受听者、材料/聆听条件影响；未校准当前实现，也未将LKFS当phon/sone |
| CLAIM:030 | true peak为连续重建波形峰值，可能超过最大采样值；标准示例48kHz采用4倍过采样及低通 | [ITU-R BS.1770-5 Algorithms to measure audio programme loudness and true-peak audio level](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf)，Annex 2 §1/3；official_algorithm_sections_checked | 不把任意4倍插值都当合规；未满幅样本不排除间采样峰或前级失真，更非破音病因证明 |

## 已发现需修订的地方

1. 周期级振幅扰动shimmer不应由原L3慢包络AM代替。新增ACO:L5候选供B/D确认；它尚未写入原表或A阶段47实体清单，阶段差异显式保留。
2. 原SRC09用了用途概括作标题，真实论文标题应在F替换。原链接所述LPC限制存在于§2.2.1，但其研究目标与样本应写清，不把它当专门验证本项目检测器的论文。
3. formant分析的“25ms窗”需要区分有效窗与实际支持；后续D协议必须写算法和完整参数，不能只报一个窗长。
4. 电平、SPL、节目响度、特定响度模型与用户强弱标签独立记录。已补定义及适用范围，但没有执行响度模型或获得当前听觉真值。
5. 原研究数字区分分母/单位：20位是颤抖研究听者；粗糙研究8份是jitter和/或shimmer正常；接触商差0.27是绝对差；32位声效论文区分在线2021与卷期2024。源谱研究144样本/136人与声源逆滤波路径明确。
6. 输出谱峰、声道共振与模型极点分栏；声门源谱和输出谱分栏。跨元音/音区原始FFT变化不能单独证明口型或真实声区。

## 31行定义审查

完整字段见[CSV](core-definition-review.csv)与[JSON](core-definition-review.json)。工程定义已有明确审查结论，但仍需操作协议，不能把挂上文献等同于方法已验证。

| 旧维度 | 工作定义 | 证据状态 | 具体缺口 |
|---|---|---|---|
| P1 | 周期信号的基频及相对音乐目标的差；另存感知音高 | partial_component_support；CLAIM:018 | 估计器质量掩码、音乐目标身份及PER:P1需D/E确认 |
| P2 | 在明确时间尺度分离的F0中心走势 | engineering_definition_proposal；CLAIM:018 | 截止频率、边界与未知段方法待D |
| P3 | 两个有身份音乐目标之间的F0连接及到达时序 | engineering_definition_proposal；CLAIM:018 | 音乐身份与允许连接范围需人工上下文；D/E待验 |
| P4 | 可定位周期/准周期的F0调制，记录速率、深度、相位和包络 | research_scope_checked；CLAIM:015;CLAIM:025 | 速率/深度算法、非平稳周期及跨通道时序待D |
| P5 | 扣除声明中心/调制模型后的帧级F0残差；周期jitter独立记录 | partial_component_support；CLAIM:001;CLAIM:003 | 循环定位及残差分解两套协议待D |
| L1 | 数字电平、校准声压级、响度模型输出与主观强弱分别记录 | source_distinctions_checked；CLAIM:009;CLAIM:010;CLAIM:022;CLAIM:023;CLAIM:029 | 回放校准、局部窗口和本机实现合规待D |
| L2 | 明确频带/窗/参考的幅度或电平包络随时间变化 | partial_component_support；CLAIM:009;CLAIM:025 | 归一、窗长、相位延迟及乐句事件定义待D |
| L3 | 包络的周期/准周期调制；记录频率、幅度及跨F0关系 | source_distinctions_checked；CLAIM:002;CLAIM:025 | AM去趋势/倍频、shimmer周期方法待D；ACO:L5为新增候选 |
| L4 | 局部短时幅度/频带能量突变及发生阶段 | partial_component_support；CLAIM:009;CLAIM:026;CLAIM:030 | 瞬态窗、变化阈值及候选原因排除待D/E |
| S1 | 周期成分/噪声的可定义声学指标；支撑感另存感知 | source_distinctions_checked；CLAIM:004;CLAIM:008;CLAIM:016 | HNR/CPP算法和有效域待D；支撑感不能给单阈值 |
| S2 | 声明取样/校正条件的谐波幅度或分段声源谱形 | source_distinctions_checked；CLAIM:011;CLAIM:012 | 逆滤波可靠性、高F0与跨元音校正待D |
| S3 | 明确分离模型下周期与非周期成分的相对量 | source_distinctions_checked；CLAIM:004;CLAIM:013 | 噪声提取与有效段验证待D |
| S4 | 非周期部分的频谱与时间结构，保留来源未明 | partial_component_support；CLAIM:013;CLAIM:019 | 非周期分解、频带和类型归属待D/E |
| S5 | 与主周期关系明确的次谐波/多周期组织 | research_scope_checked；CLAIM:014;CLAIM:017 | 检测器、复音排除及subharmonic比例协议待D |
| S6 | 声学周期支撑中断/再起事件；破音词另存候选 | source_distinctions_checked；CLAIM:021;CLAIM:017 | 官方voice breaks测量不等于本曲有效检测器 |
| R1 | 分别记录实际声道共振、输出谱包络峰和模型极点的频率 | source_distinctions_checked；CLAIM:005;CLAIM:006;CLAIM:020 | 高F0可识别性、峰/极点跟踪及无生理真值限制待D |
| R2 | 共振/模型极点带宽与谱谷/反共振分别记录 | partial_component_support；CLAIM:005;CLAIM:011;CLAIM:020 | 带宽与零点估计独立定义，鼻通道证据待D |
| R3 | 同身份元音/过渡阶段内的谱包络、峰或极点时间连续性 | engineering_relation_with_source_limits；CLAIM:006;CLAIM:007;CLAIM:020 | 对象追踪、匹配及同声线条件待D/E；无自动异常阈值 |
| R4 | 鼻化候选谱结构与鼻/堵感知分栏 | partial_component_support；CLAIM:019;CLAIM:020 | 鼻声知觉与生理推断需独立证据；本模型暂无验证 |
| T1 | 声学事件相对于显式音乐/词/音素参考的时差 | engineering_clock_definition；CLAIM:026 | 参考身份、offset、时钟转换与误差需D/C |
| T2 | 明确边界之间的音符/音素/元音核持续时间 | engineering_clock_definition；CLAIM:026 | 边界检测及延音/跨note计数待D |
| T3 | 声母爆破/摩擦/有声段及对比线索；咬字清晰度另存 | partial_component_support；CLAIM:019;CLAIM:026;CLAIM:027 | 中文音素条件与感知识别任务待D/E |
| T4 | 声母释放、周期声/噪声与元音包络建立的先后及间隔 | source_distinctions_checked；CLAIM:026;CLAIM:019 | 中文声母与非塞音入口协议待D；无通用理想ms |
| T5 | 相邻音素声学特征的过渡时间及连续/重叠关系 | engineering_relation_with_source_limits；CLAIM:019;CLAIM:020;CLAIM:026 | 自然协同发音与异常漂移的对照待D/E |
| T6 | 持续发声结束/再起及包络释放；词尾音素独立 | engineering_relation_with_source_limits；CLAIM:019;CLAIM:009 | 释放事件时刻及尾音身份待D/E |
| T7 | 非唱呼吸噪声与静音/低能量间隔分别记录 | engineering_event_definition；CLAIM:019 | 呼吸来源/边界与休止定义待D/E |
| X1 | 数字样本过载/非线性与其他失真分栏，查sample peak及true peak | partial_component_support；CLAIM:030 | true-peak实现/滤波验证及非线性归因待D/C |
| X2 | 波形边界不连续、重复结构、谱异常等现象分开记录 | engineering_artifact_candidates；CLAIM:008;CLAIM:030 | 伪影类型定义/来源归因与重现证据待D/E |
| X3 | 声部电平比例与目标识别受遮蔽的感知结果分栏 | partial_component_support；CLAIM:027;CLAIM:029 | 当前歌曲混音的频带/时间/听者协议待D/E |
| X4 | 通道相位/相关、混响响应与远近/宽度感知分栏 | scope_only_partial；CLAIM:028;CLAIM:029 | 已知IR与盲估计分开，空间听觉/算法资料仍缺 |
| X5 | 采样率、位深、编码/带限是格式/处理上下文；声学后果另记 | engineering_metadata_definition；CLAIM:030;CLAIM:011 | 量化/混叠/编解码方法资料仍缺；需C/D核对 |

## 30组组合听感逐项审查

下面多义分解、近义区别及反例均为Codex显式工程提案。来源只支持相关组件区别，**不验证中文词之间等价或其唯一病因**。反例是思考例，不是新音频/用户标签，也不是E的独立覆盖测试。

可比较结构化[CSV](composite-review.csv)与[JSON](composite-review.json)：还含两条候选路径、所需观测、说法引用与未验证状态。

| ID／原词组 | 近义／歧义区别 | 候选路径A；B | 假设反例 |
|---|---|---|---|
| DESC:01 撕裂、嘶吼 | 撕裂与嘶吼不完全同义；强度和粗糙形态分开 | S5多周期/次谐波与S3噪声组合；S6中断或X1失真伴L4突变 | 大声清亮可无粗糙；有意粗糙也可低电平 |
| DESC:02 沙哑、颗粒、毛糙 | 沙哑、颗粒、毛糙的尺度及噪声/脉冲感可能不同 | S3/S4非周期噪声；S5次谐波或P5周期扰动，另排X2 | jitter/shimmer正常仍可粗糙；摩擦辅音不等于元音沙哑 |
| DESC:03 破音、炸一下 | 破音/炸一下是事件标签，不能预判类型 | S6失声/再起或P1/P3骤变；L4瞬态、X1过载或X2边界伪影 | 元音后自然爆破可能有突峰但不破音；无削波也未排除破音 |
| DESC:04 颤抖、摇晃 | 颤抖、摇晃、颤音分开意图与可闻维度 | P4/P5频率调制；L3或R3/S2谱形调制及相互作用 | F0相同调制也可能有不同摇晃感；规律颤音可为所需 |
| DESC:05 饱满、有芯、厚实 | 饱满、厚实、有芯分别可能指低频量感/集中/稳态 | S1/S2周期与谐波组织，R1/R2谱包络；L1/L2或X3/X4呈现变化 | 提高整体增益未必更实；低音多也未必有芯 |
| DESC:06 薄、虚、空、飘 | 薄、虚、空、飘不强制互为同义 | S2/S3谱及噪声比例候选；L2主体短缺或X3掩蔽/X4空间 | 轻薄可有意而稳定；气声不必空或小声 |
| DESC:07 假音感、头声感 | 假音感、头声感是听感/唱法词，不直接标M2 | S1/S2/S3联合声质变化；R1/R3谱包络与音区/上下文变化 | 高音或气声单独都不证明假声；同F0可有声质差 |
| DESC:08 实声感、胸声感 | 实声感、胸声感不是接触商或VOIC名称的别名 | S1/S2周期谐波组织；R1/R2与L2主体/X3突出感 | 增大VOIC数值不保证胸声感；更响不必胸声 |
| DESC:09 混声、换声顺畅 | 混声是唱法解释；顺畅是关系判断 | P3/T5平滑目标与时序；S1/S2/R3/L2在过渡中保持或有意改变 | F0连续仍可换声色；声色变化也可有意顺畅 |
| DESC:10 挤、紧、顶、喊 | 挤、紧、顶、喊可指声质/用力感/音区或响度 | S2/R1/R3谱形及P1音区组合；L1/L4强弱或T4入口带来的感受 | 响不等于挤；同音高局部顶感不能证明舌根后缩 |
| DESC:11 气声、耳语、漏气 | 气声与耳语不同，漏气是生理措辞需保留假设 | S3/S4元音非周期量及频谱；S1周期下降/消失与T4噪声先行 | 清辅音高频噪声不是漏气；BREC减小未必可闻 |
| DESC:12 明亮、尖、刺 | 明亮、尖、刺的喜好/刺激感不同 | S2/R1/R2高频与包络变化；L1强度、X3遮蔽或X1瞬态失真 | 谱重心高的低音量声不必刺；明亮可柔和 |
| DESC:13 暗、柔、闷、蒙 | 暗、柔、闷、蒙含音色与清晰度不同轴 | S2/R1/R2谱形变化；T3线索受损或X3掩蔽/X4混响 | 暗可清楚；柔可明亮；低通不是唯一暗色原因 |
| DESC:14 鼻、堵、鼻腔色彩 | 鼻色与鼻堵感分开；堵还可能是闷或挤 | R4口鼻耦合候选峰/谷结构；R1/R2/S2普通谱色变化或T3线索弱 | 某频带突出不唯一证明鼻化；鼻音辅音可完全正常 |
| DESC:15 口型不稳、舌根后缩感 | 口型不稳/舌根后缩是知觉比喻与原因假设分开 | R3同元音谱包络/峰变化；S2/S3发声变化或T5过渡/估计失败 | 高F0的LPC跳峰可能无真实口型变化；双元音本有运动 |
| DESC:16 突然像换了人 | 像换了人是身份连续性标签，不能直接认speaker改动 | S2/R1/R3跨字谱及音区变化；X4空间或T5切换/模型speaker条件候选 | speaker字段相同也可能色变；字段改变未必可闻换人 |
| DESC:17 硬起、爆字头 | 硬起与爆字头可能是有意发音/重音或异常突峰 | T4有声/噪声/辅音事件关系；L4突峰、X1过载/X2拼接 | 爆破辅音强不必硬声门起音；硬起不必过载 |
| DESC:18 软起、虚起、气起 | 软起、气起、虚起不是同一个时间参数 | L2缓起与T4起点组织；S3/S4噪声领先或S1弱周期 | 包络缓起也能实；气声入口可很短很明确 |
| DESC:19 咬字清楚、含糊、吞字 | 含糊、吞字、咬字弱可能是不同识别失误 | T3/T2声母或元音线索/核不足；X3掩蔽或T5过渡影响可懂度 | 辅音能量更多不保证识别更准；原生音素正确也不保证清晰 |
| DESC:20 连贯、粘、断、磕绊 | 连贯、粘、断、磕绊区分有意连断与异常 | T5/T1间隔、重叠及边界事件；P3/R3/L2连续性或X2拼接 | 句末有意断开不等于磕绊；过分连可糊词 |
| DESC:21 滑、拐、跳得太高 | 滑、拐、跳跃是动作；太高是相对目标判断 | P3/P1音乐身份及连接路径；T1/T2过快到达或声质过渡引起跳感 | 大音程可以自然；浅滑音也可能拖错拍 |
| DESC:22 直、平、机械、僵硬 | 直、平是形状，机械/僵硬是音乐判断 | P2/P4较少变化与L2稳定；T1/T5阶段重复或S2/R3过度一致候选 | 稳定直音可符合音乐目的；加入颤音不保证自然 |
| DESC:23 稳、松弛、自然 | 稳、松弛、自然属于不同条件的评价词 | P1/T1符合目标且S/R连续候选；有意变化的P4/L2/T5也可获自然感 | 低残差不保证自然；有意粗糙/抖动也可能合适 |
| DESC:24 无力、漏底、支撑不住 | 无力、漏底、支撑不住不直接等于气声多 | L2元音主体包络不足候选；S1/S2/R3变化或X3掩蔽 | 降低气声未必更有力；弱声可以完整稳定 |
| DESC:25 渐强、蓄力、爆发、回收 | 渐强、蓄力、爆发、回收区分强弱轨迹与意图 | L2/L4振幅阶段组织；S2/S3/P2/R3联合变化候选 | 电平不变也可有推进感；增益上升未必蓄力 |
| DESC:26 抢、赶、拖、松紧不对 | 抢、赶、拖是相对节奏/歌词身份；松紧可含感觉 | T1音乐/词边界时差及T2核分配；P3到达或T4/T5线索建立造成时间感 | 所有note落拍也可能字腹太快；提前音节可为有意切分 |
| DESC:27 哭腔、哽咽、泣音 | 哭腔、哽咽、泣音的具体声学指向待标签 | P3/P4/S6断续或调制候选；S3/T4/R3声质/入口变化候选 | 下滑或断声单独不保证哭感；哭感不必破音 |
| DESC:28 笑感、甜、冷、温暖、情绪充足 | 笑、甜、冷、温暖、情绪足分别存标签 | R1/S2/T3音色/发音候选；P2/P4/L2/T1表达组织候选 | 亮声不必甜；暗声不必温暖；同声学可因歌词变感受 |
| DESC:29 近、贴耳、远、空灵 | 近、贴耳、远、空灵区分空间与声质 | X4直达/反射、通道关系候选；S3/R1/L1气声/谱/呈现强度候选 | 纯干声也可空灵；加混响不保证远或好听 |
| DESC:30 好听、难听、像不像原唱 | 好听、难听、像原唱是审美/身份/目标不同任务 | 多维声学与音乐组织的描述；听者、原唱、歌词和风格情境评价 | 技术完全跟随也未必好听；偏离原唱可有意且好听 |

## 待确认的遗漏与范围

- 周期幅度扰动shimmer：候选ACO:L5；保留在B差异中，未修改A的47实体或原清单。D先明确循环定位适用域。
- 感知音高：候选PER:P1，不用物理F0代替。复音/拍频需区分同源次谐波、多个独立F0、AM及感知融合；是否新增实体待D/E，不把所有拍频塞入P4。
- 哭笑/情绪、身份与审美：保留独立标签/上下文，不伪造声学标量或唯一调参配方。专门知觉资料仍缺。
- 房间测量、通道关系、远近/宽度听感，以及数字编码/混叠/金属伪影的详细方法仍有缺口；已读标准范围不能代替算法验证。
- 工程定义的趋势、连接、连续性与阶段时钟需D落实协议，E检查它们有无吞掉独立现象。

原SRC01–09研究/实验室来源均已在上表核对到明确读取级别；SRC10/SRC11是OpenUtau支持/Expressions文档，软件机制核查留在C，不用它们证明声学或听感。原来源标题/元数据正式更正留在F，原知识表字节保留。

本阶段逐项审查已完成并携带以上缺口继续[阶段C](../../../plan.md)：展开具体控制字段及本机/上游支持。C不依赖这些词已有唯一病因；资料缺口留在后续确认清单，不升级状态。原六份清单/第二层、Skill、工程和历史证据不改。

逐说法记录见[CSV](claim-evidence.csv)和[JSON](claim-evidence.json)，文件/保护绑定见[执行审计](table1-execution-audit.json)。
