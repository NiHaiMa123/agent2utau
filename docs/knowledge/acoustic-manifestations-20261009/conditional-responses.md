# 表2现行确认：2C

14条记录复核完成，确认范围与缺口见[2C逐行报告](table2-record-confirmation.md)和[JSON](table2-record-confirmation.json)。输入/预测数学核查与历史声学/用户反馈分层；没有新模型、PCM测量或试听。以下2B及更早说明保留原时态。

# 表2现行结构：schema 3（2B）

14条记录保留原值，新增record_v3。比较、逻辑版本/文件标签、基底/增量/最终输入/PCM、反馈组与时态分开。 [字段说明](table2-fields.md)、[迁移](table2-schema-migration.json)、[2B报告](table2-schema-review.md)、[原字节快照](history/pre-table2-2b-20261010/snapshot-manifest.json)。2C未执行。

| 记录 | 主比较ID | 状态来源/反馈边界 |
|---|---|---|
| RESP-001 | RESP-001:B-A | FB:RESP-001 |
| RESP-002 | RESP-002:B-A | FB:RESP-002 |
| RESP-003 | RESP-003:C-B | fresh/B标签对应新C；旧B复用；A基底不是B |
| RESP-004 | RESP-004:B-A | FB:RESP-004 |
| RESP-005 | RESP-005:B-A | FB:BREC-cohort |
| RESP-006 | RESP-006:B-A | FB:BREC-cohort |
| RESP-007 | RESP-007:B-A | FB:BREC-cohort |
| RESP-008 | RESP-008:B-A | FB:BREC-cohort |
| RESP-009 | RESP-009:B-A | FB:BREC-cohort |
| RESP-010 | RESP-010:B-A | FB:BREC-cohort |
| OBS-001 | OBS-001:word247-word112 | FB:OBS-001 |
| OBS-002 | OBS-002:accepted_C-original_A | C-B局部反馈借用，不是C-A试听 |
| AUD-001 | AUD-001:HFA_observation-native_g_uo | 技术审计，无听觉效果比较 |
| AUD-002 | AUD-002:SHFC_400c_intended-SHFC_4c_rejected | 技术审计，无听觉效果比较 |

## 原阶段叙述（数值与时态保留，现行结构以上方为准）

# 第二层：条件—干预—实际响应—听觉结果

更新：2026-10-10（F正式引用迁移；表2专项尚未执行）。[第一层总表](README.md)继续负责“表现是什么、有哪些控制入口”；本表负责“在什么条件下，怎样改，实际发生了什么，用户是否认可”。同一参数允许同时存在正例、无效例与副作用。它是已有证据的整理，本次没有新增音频、改工程或修改通用Skill。

## 为什么另建表

第一层一行对应一个表现或控制入口；第二层一行对应一次**有输入/输出绑定的条件干预**。一个SHFC入口已有抱、果、进入时序等不同结果，把它们压进原表的一格会丢失条件和反例。两表现以CTRL控制导航、ACO/EVT/PER/META分层实体及EVID项目证据关联；RESP/OBS/AUD编号保持。旧维度候选去向与legacy引用见文末迁移表及id-migration.json，不表示每个展开实体已被观测。

当前整理了**10条条件干预记录（5个实验设计）、2组观察关联、2项技术审计，48类控制的覆盖/缺口**。六个BREC条件属于同一次实验设计；同一抱原A/C也不算两个独立受试者。结果为1条局部接受、1条有益但有副作用、1条无改善且有副作用、7条未感知区别。全来自同一声库/曲目，尚无留出条件或跨曲泛化验证。这已经补齐第二层的记录结构及现有证据，不能据此称为完整有效的控制规律库。

## 每条记录必须分开的内容

| 字段 | 应保存什么 | 防止什么误判 |
|---|---|---|
| 条件 | 声库/模型/speaker、音素/语言、邻字/乐句、note与实际F0、原生时钟、基底预测+人工状态、source unknown | 同一个字或MIDI相同便认为条件完全相同 |
| 目标表现 | 第一层原子ID、用户原话、音乐动作目的及待验证假设 | “更实”直接等同真实声带机理或formant |
| 干预 | 原值/增量/单位、函数族、绝对支撑、进入/平台/退出、音素相对锚点、合法范围 | 只记录峰值；-4c与-4半音混用 |
| 冻结与重算 | 保持哪些人工输入、允许哪些预测下游变化、实际native输入、种子、DYN/增益 | 只改一个UI通道就声称只改变一个声学机制 |
| 技术状态 | 输入隔离、原版/重复精确、实际成声/交付PCM和SHA、测量窗及单位 | 把错误编码、旧缓存或数学预期当已执行实验 |
| 响应 | 字头/核/尾/邻字的电平、谱、双F0及可比帧数；未测项unknown | 只看整字均值，漏掉接口/频带副作用 |
| 听觉 | 原话、比较对象与音频SHA、可感知差别/有益/副作用/局部接受分列 | 测量响应直接升级为自然度成功；“可以”补成所有细项全通过 |
| 使用边界 | 反例、采用/拒绝、因果范围、剂量/迁移未验证项 | 把单点145ms或单剂量无效写成通用规则 |

## 受控条件响应表

以下为易读摘要。完整原生秒数、元音时长、核/入口/尾部基底实际发声状态、输入/交付SHA及已测双F0/分带数据见[结构化表](conditional-responses.json)；便于筛选的主要字段见[CSV](conditional-responses.csv)。基底数值是模型状态，不是PCM dB、人体张力或天然真假声判定。RESP-003的对照是已有SHFC B，基底字段保留原v02参照并明确标注；B/C的下游状态与窗口响应单列，未提取的比较状态不补造。

| 记录 | 条件/原标签 | 元音/谱面音区 | 剂量/比较 | 时间形状 | 实际响应摘要 | 用户结果 |
|---|---|---|---|---|---|---|
| RESP-001 | 3:04 抱，偏假/顶 | zh/ao/MIDI71 | 取消TENC +14；模型峰值-.7；24帧 | 有限偏移支撑183.821458–184.113s | ao RMS +0.1905dB | 没听出区别，不采用 |
| RESP-002 | 3:04 抱，偏假/顶 | zh/ao/MIDI71 | SHFC -400c（-4半音）；24帧 | 入口55ms，元音后10ms开始；出口55ms | ao RMS -.1132dB；入口F0最大差44.50/40.38c | 更实＋字头破音，不采用 |
| RESP-003 | 3:04 抱，偏假/顶 | zh/ao/MIDI71 | SHFC同-400c平台/退出；C对旧B | 55→145ms，起点提前90ms至元音前80ms；到达不变 | 入口谱相邻差 .666→.589；b RMS -5.3255dB；ao -.2958dB（C-B） | 局部“可以”，保留C |
| RESP-004 | 1:27 果，偏假/顶 | zh/uo/MIDI64 | SHFC -200c（-2半音） | 入口160ms，元音前80ms开始；出口70ms | uo RMS +.0901dB；2–5k约-4.032dB；接口30ms最低约-4.200dB | 无改善＋响度下降，不采用 |
| RESP-005 | 1:27 果，偏假/顶 | zh/uo/MIDI64 | 额外BREC -10；模型峰值约-1.2 | Q5，入口80ms/出口70ms，原生5tick；基底UI [0] | 元音RMS +0.0181dB；30ms最低 -0.0231dB；去电平mel差 0.062595 | 没听出区别，不采用 |
| RESP-006 | 1:33 之，偏实 | zh/ir/MIDI66 | 额外BREC -10；模型峰值约-1.2 | Q5，入口80ms/出口70ms，原生5tick；基底UI [0] | 元音RMS +0.0273dB；30ms最低 -0.0481dB；去电平mel差 0.075994 | 没听出区别，不采用 |
| RESP-007 | 2:56 只，偏实 | zh/ir/MIDI69 | 额外BREC -10；模型峰值约-1.2 | Q5，入口80ms/出口70ms，原生5tick；基底UI [0] | 元音RMS -0.0232dB；30ms最低 -0.0727dB；去电平mel差 0.035790 | 没听出区别，不采用 |
| RESP-008 | 3:04 抱，偏假/顶 | zh/ao/MIDI71 | 额外BREC -10；模型峰值约-1.2 | Q5，入口80ms/出口70ms，原生5tick；基底UI [-3, -2, -1, 0] | 元音RMS +0.0200dB；30ms最低 -0.0140dB；去电平mel差 0.037742 | 没听出区别，不采用 |
| RESP-009 | 3:17 果，局部可用 | zh/uo/MIDI64 | 额外BREC -10；模型峰值约-1.2 | Q5，入口80ms/出口70ms，原生5tick；基底UI [0] | 元音RMS +0.0064dB；30ms最低 -0.0269dB；去电平mel差 0.051873 | 没听出区别，不采用 |
| RESP-010 | 3:04 抱C，局部可用 | zh/ao/MIDI71 | 额外BREC -10；模型峰值约-1.2 | Q5，入口80ms/出口70ms，原生5tick；基底UI [-3, -2, -1, 0] | 元音RMS -0.0108dB；30ms最低 -0.0597dB；去电平mel差 0.038619 | 没听出区别，不采用 |

全部原生DYN/固定增益按原实验检查。SHFC重新计算完整variance/acoustic上下文，可能同时改变气声、有声、张力预测及邻字；vocoder目标F0输入保持不等于实测PCM F0精确保持。BREC六组只改变breathiness人工输入，新预测保持相同；A及重复精确。本表引用旧封存核查结果，本次没有重新合成或重新测音频。

RESP-003的C-B谱/电平与A-C F0不能混为同一比较。旧B明确复用封存波形，新原A/重复/C已在当时完整渲染。其入口时长和提前准备共同改变，只能支持这组时间几何可用，不能分别证明145ms或前80ms是病因修法。b电平约-5.33dB只是测量，用户没有单独判其咬字失败，也没有明确说完全无破音。

RESP-004果的元音平均电平略升，2–5kHz和邻字接口降低；用户仍听到响度下降。带能量/短窗是解释线索，没有验证感知响度模型，不能否认听感或靠增益掩盖。RESP-005～010的“全部没区别”是六组分开试听的回报；既否定本剂量可感知收益，也不补造“六组所有细分副作用都通过”。

## 关联线索单列

| 记录 | 比较条件 | 核20–80%实际模型状态差 | 可以得到什么 | 不能得到什么 |
|---|---|---|---|---|
| OBS-001 | 问题果1:27与可用果3:17，同uo/E4但时长/前后字/上下文不同 | 可用-问题：VOIC +1.6140、BREC -.9680、TENC +.3527；目标音高约-.8003c | 同元音/近音高仍能有不同听感；值得描述入口状态 | VOIC提高或BREC降低各自导致可用；通用通过阈值 |
| OBS-002 | 问题抱原A与可用抱C，同字上下文但SHFC进入条件变化 | C-A：VOIC -.9145、BREC -5.8843、TENC +1.0628；核条件pitch -400c、vocoder目标0c | 反驳把“更实”统一规定为VOIC必须增加、TENC必须减少 | 降VOIC/加TENC各自是修法；BREC变化独立造成收益 |

共同BREC下降曾构成假设，随后六条件BREC -10均无感知区别。保留这个阴性证据，不能把先前关联继续写成已验证规律。后续如检验其它剂量或条件，必须登记为新假设；本次不自动追加实验。

AUD-001记录g→uo词表/语言正确及入口约+.303ms差，缺明显大错位证据；这不证明发音自然。AUD-002记录SHFC单位和原生5tick编码拒绝/修正过程；正确执行也不证明自然度。审计与听觉响应分别保存。

## 当前覆盖与下一步缺口

每个控制都有一行[覆盖/缺口表](response-coverage.csv)。三个直接模型通道TENC、SHFC、BREC有局部受控听觉记录；CTRL:C47只有SHFC进入几何、BREC时序/编码这部分，不能把整类图形/函数功能算成已验证。VOIC只有关联。DYN的数学增益路径已明确，但缺音乐强弱/感知响度验收。当前禁用ENE/falsetto与其它引擎/上游功能，先确认支持再谈响应，不能为了填空把所有UI入口轮流扫描。

| 缺口 | 要补的内容 | 有效完成标准 |
|---|---|---|
| 可感知正例与副作用边界 | 保留抱C唯一局部接受，分开实感、字头、音准、响度、邻字；精确匹配当前实验基底 | 能指出适用条件与失败边界；不补造现有反馈缺失标签 |
| 时间几何 | 入口时长、提前准备、音高到达/元音边界的作用分离 | 各自真实输入隔离并听觉判断；145ms不直接成为默认 |
| 发声状态因果 | 独立VOIC、其它TENC/BREC条件；把预测基底与人工增量分开 | 有对照、可感知结果及反例；不从相关性直接决定调节方向 |
| 元音/音区/剂量迁移 | 不同元音/音区/邻字和剂量响应的有效区域、无效区及副作用 | 未参加规则设计的留出条件仍可用；跨曲/声库结果另外建版本 |
| 发音/共振与破音分类 | 可靠谱包络/声源/transition观察及听者可标注定义，高F0保留不可靠估计 | 实际验证指标能区分所研究现象；不能直接拿LPC或单频带当嘴型真值 |
| 乐句与整曲关系 | 同一局部动作在前后承接、强弱弧线和伴奏中的收益/代价 | 整句及全曲听觉验收、原有可用处保护；不能靠单点通过宣称整曲完成 |

这是一份按证据缺口排出的研究顺序，不是自动实验队列。新实验应先有明确目的、一个主干预与反例保护，再固定计划、原生隔离、完整依赖重算、同条件交付与听觉反馈；不能用参数扫描选一个机器分数最好者恢复已撤出的路线。

## Agent如何读取第二层

先根据原曲、当前音素时钟和音乐目的判断动作，再查询相同声库/模型/音素/音区/阶段/基底及上下文的记录；匹配项用于提出或拒绝有边界的选择。近似条件仅作假设来源，缺数据返回unknown。纯关联不提供方向配方，阴性结果限定原剂量/条件；局部接受不直接迁移函数节点、作者曲线或全局默认。全曲函数仍由Agent独立设计，按现有流程编译与核查。

记录状态分别为：输入核查、声学响应、用户结果、副作用、全曲验收、泛化验证、是否可进入Skill。它们不是可相互替代的等级。当前全部泛化未验证、没有新通用Skill规则；“更实但破音”有可感知响应却被拒绝，“没区别”有真实输入变化却没有感知收益。

## 文件与来源

提供本说明、条件响应CSV/JSON、48类覆盖CSV、[来源审计](response-source-audit.json)。每条受控记录关联原报告、控制/表现ID、实验组及原工程/交付音频SHA；结构化文件只保存条件、聚合数据和绑定，不携带音频、模型或作者数组。来源审计重新哈希所引用JSON/报告；原报告和封存run保持不动。来源历史字段中的listening_pending或perceived_improvement=false是测量当时状态，最终听觉状态以随后绑定的用户反馈为准。

## F类型引用迁移

仅引用结构变更，原值/反馈/工程与音频SHA保持。原版字节见[迁移前快照清单](history/pre-f-20261010/snapshot-manifest.json)；[ID迁移](id-migration.json)保存旧ID及候选去向。E关于乱码的判断为工具显示编码误判，原UTF-8文字正确，未转码；U17 word295身份勘误仍有效，见[纠错](source-quality-correction.json)。

| 记录 | 旧维度ID | 分层实体引用候选 | 来源 |
|---|---|---|---|
| RESP-001 | S1, S2, R3 | ACO:S1, ACO:S2, EVT:R3, PER:S1 | [原报告](../../lastpage-tenc-controlled-probe-20261008.md) |
| RESP-002 | S1, S2, S6, R3, T4 | ACO:S1, ACO:S2, EVT:R3, EVT:S6, EVT:T4, PER:S1 | [原报告](../../lastpage-shfc-controlled-probe-20261008.md) |
| RESP-003 | S6, R3, T3, T4, L4 | ACO:L5, EVT:L4, EVT:R3, EVT:S6, EVT:T3, EVT:T4, PER:T3 | [原报告](../../lastpage-shfc-onset-probe-20261008.md) |
| RESP-004 | S1, S2, R3, L1, L2, T3, T5 | ACO:L1, ACO:S1, ACO:S2, EVT:L2, EVT:R3, EVT:T3, EVT:T5, PER:L1, PER:S1, PER:T3 | [原报告](../../lastpage-guo-register-probe-20261008.md) |
| RESP-005 | S1, S3, R3, L1, L2 | ACO:L1, ACO:S1, ACO:S3, EVT:L2, EVT:R3, PER:L1, PER:S1 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |
| RESP-006 | S1, S3, R3, L1, L2 | ACO:L1, ACO:S1, ACO:S3, EVT:L2, EVT:R3, PER:L1, PER:S1 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |
| RESP-007 | S1, S3, R3, L1, L2 | ACO:L1, ACO:S1, ACO:S3, EVT:L2, EVT:R3, PER:L1, PER:S1 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |
| RESP-008 | S1, S3, R3, L1, L2 | ACO:L1, ACO:S1, ACO:S3, EVT:L2, EVT:R3, PER:L1, PER:S1 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |
| RESP-009 | S1, S3, R3, L1, L2 | ACO:L1, ACO:S1, ACO:S3, EVT:L2, EVT:R3, PER:L1, PER:S1 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |
| RESP-010 | S1, S3, R3, L1, L2 | ACO:L1, ACO:S1, ACO:S3, EVT:L2, EVT:R3, PER:L1, PER:S1 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |
| OBS-001 | S1, S2, S3, R3, T4 | ACO:S1, ACO:S2, ACO:S3, EVT:R3, EVT:T4, PER:S1 | [原报告](../../lastpage-guo-positive-comparison-20261008.md) |
| OBS-002 | S1, S2, S3, R3 | ACO:S1, ACO:S2, ACO:S3, EVT:R3, PER:S1 | [原报告](../../lastpage-cross-condition-study-20261008.md) |
| AUD-001 | T1, T2, T3, T5, R1, R3 | ACO:R1, ACO:T2, EVT:R3, EVT:T1, EVT:T3, EVT:T5, PER:T3 | [原报告](../../lastpage-guo-phoneme-audit-20261008.md) |
| AUD-002 | T4, R3 | EVT:R3, EVT:T4 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |


## 虚实机制测试样本（2026-10-17）

新增方法记录`METHOD:PHONATION-BENCHMARK-20261017`，见[有限工程测试与待试听样本](../../reports/production/phonation-benchmark-20261017.md)。324数学信号与84孤立元音仅支持所列工程性质，听觉标签0；v2撤下合并虚实分、分轴报告并收紧动态质量掩码。25组原始/21组RMS匹配开发对照已绑定，待后续标签核验，不以旋钮作实感真值、不填补连唱参考、不升级旧measurement_validated或宣布第三句修复。


## 单音不可辨反馈与整句粗区分（2026-10-17）

用户回报单音基本听不出，要求完整句和先拉大区别。追加`AUD:PHONATION-ISOLATED-SAMPLES-INSUFFICIENT-20261017`，原25/21包暂不作下一步问卷；不倒填84条逐项阴性。`METHOD:PHONATION-SENTENCE-COARSE-20261017`交付同一完整句3个宽组合候选，主入口先听A/C两端、整句固定RMS匹配；实际输入隔离/保护/成声核查通过，可辨/虚实排序仍待听。见[完整记录](../../reports/production/phonation-sentence-coarse-20261017.md)。宽组合不作为独立通道病因/歌曲接受/通用剂量，原measurement_validated保持。


## 整句端点相对标签与B定位（2026-10-17）

`AUD:PHONATION-SENTENCE-A-MORE-VIRTUAL-20261017`记录原话“a更虚”，仅同句RMS匹配A/C的相对虚实方向，不推断C偏好/绝对合适/气声量或全部元音标签。旧pending及报告保持，另存1轴部分标签。`METHOD:PHONATION-SENTENCE-MIDPOINT-COMPARISON-20261017`交付已核查B/C整句PCM的B→C对照，无新模型或工程；B位置、可辨与偏好待听。见[记录](../../reports/production/phonation-sentence-midpoint-comparison-20261017.md)。旧measurement_validated及全曲/迁移状态不升级。


## 相对虚实与额外发声特征分列（2026-10-17）

`AUD:PHONATION-SENTENCE-BC-VIRTUALITY-C-VOICE-20261017`记录“b更虚，但是c感觉像是压低声音唱的”；B/C相对方向与C该听感分开，未获自然实声/偏好或病因标签。`RESP:PHONATION-SENTENCE-C-D-BREC-ISOLATION-20261017`新增D，仅撤回C的BREC负包络、保留VOIC与其它输入；主C→D整句RMS匹配，虚实和该听感变化待听。见[完整记录](../../reports/production/phonation-sentence-brec-isolation-20261017.md)。不从共享C端点推断A/B排序，原measurement_validated与歌曲状态保持。


## C/D两维权衡与单项中间E（2026-10-17）

`AUD:PHONATION-SENTENCE-D-LESS-LOWERED-MORE-VIRTUAL-20261017`记录“减轻，但是更虚”：D相对C的压低声音唱感觉减轻、同时更虚，不宣称偏好/接受或唯一病因。`RESP:PHONATION-SENTENCE-BREC-MIDPOINT-E-20261017`固定VOIC等，仅取C/D间BREC−40的E；D→E整句等RMS对照待听。节点取半不等于采样精确半量，首轮断言失败与未独立重建BREC的缺口保留；实际逐帧处于两端间、其它输入/边界通过。见[记录](../../reports/production/phonation-sentence-brec-midpoint-20261017.md)。不新增通用剂量或升级旧measurement_validated。


## D/E整体近似与有声支撑因素F（2026-10-17）

`AUD:PHONATION-SENTENCE-DE-OVERALL-SIMILAR-20261017`记录“差不多”，整体近似而非六轴分别等价；E实际BREC响应已只读确认，不由数值差反驳反馈。停止本句BREC加密，`RESP:PHONATION-SENTENCE-VOIC-ISOLATION-F-20261017`固定C负BREC只撤回VOIC，补同句工程2×2缺格，C→F等整句RMS试听待评，不推因果/交互或最优参数。见[记录](../../reports/production/phonation-sentence-voic-isolation-20261017.md)。旧measurement_validated及歌曲保持。


## 第一测试句汇总与另一句前向检查（2026-10-17）

`AUD:PHONATION-SENTENCE-CF-LESS-LOWERED-C-FIRMER-20261017`记录“减轻，c更实”：F该听感减轻、C更实；同句撤回两项控制均伴随两维权衡，不推唯一病因/交互或未听排序，停止该句新增点。`RESP:PHONATION-SECOND-CONTEXT-GHI-20261017`换“窗外的天气”，新生成G/H/I，预先冻结G/H和G/I相对方向后验证；当前均待听，5/6元音可靠、短u unknown，输入/时钟/PCM通过，不算独立盲听/新歌迁移。见[记录](../../reports/production/phonation-second-context-20261017.md)。旧measurement_validated及歌曲保持。


## 换句偏好、暗/清亮与虚实锚点（2026-10-17）

`AUD:PHONATION-SECOND-CONTEXT-HI-SIMILAR-PREFERRED-G-20261017`记录H≈I且各自好于G；`AUD:PHONATION-SECOND-CONTEXT-G-DARK-CLARIFIED-20261017`追加G暗、像压低声音、不够清亮。两条压低感预期获问答上下文支持（非逐对独立重评），两条虚实预期unknown。`METHOD:PHONATION-SECOND-CONTEXT-PREFERENCE-REVIEW-20261017`检索四条已有虚实锚点，保留C副作用；不由清亮或偏好补虚实排序，不重复要求定义。见[复核](../../reports/production/phonation-second-context-preference-review-20261017.md)。歌曲/音频/旧收据保持，未新增样本，measurement_validated保持。


## 已有标签开发考核与声色混杂（2026-10-17）

`METHOD:PHONATION-EXISTING-LABEL-AUDIT-20261017`重测已有9版PCM/F0精确复现；四组虚实标签两轴汇总方向吻合，但共用较实且压低感的C，仅一个听觉标注句上下文，不报听觉准确率或声色分离。D/E整体近似仍有指标差，等组分SNR滤波也改变代理，不能据数值宣布可辨或定统一阈值。新增共同主体配对API不输出虚实分。见[考核](../../reports/production/phonation-existing-label-audit-20261017.md)。歌曲/音频保持，旧measurement_validated不升级。


## 非C证据检索与一组已有PCM试听（2026-10-17）

`METHOD:PHONATION-NONC-EVIDENCE-AND-LISTENING-20261017`检索96份活动公开JSON，73字段命中不计独立样本。J实而非旧前顶及更实却尖挤的经验保留，不读取历史制作载荷；现无完整约束当前非C虚实/暗清亮两轴的标签。只拼已有D→F整句PCM，不加增益/效果或新合成；两轴待听，不能从共享C补排序。见[记录](../../reports/production/phonation-nonC-evidence-and-listening-20261017.md)。Skill与雨爱保持，旧状态不升级。


## 非C直接反馈：F更实、D暗、偏好F（2026-10-17）

`AUD:PHONATION-NONC-DF-F-FIRMER-D-DARK-20261017`保存“f更实”“D暗。F好很多”，同一试听事件两条消息；F相对更实、D更暗、整体偏好F，非绝对采用或压低感完全消失。原两项虚实代理方向相符，谱倾斜直接明暗排序却与反馈相反；不翻符号/拟合权重。见[记录](../../reports/production/phonation-nonC-df-feedback-20261017.md)。新增非C交叉关系仍只一个标注句上下文，跨句刻度未通过；旧文件与雨爱保持。


## 真实前三句覆盖与F连续诊断（2026-10-17）

`METHOD:PHONATION-CONTINUOUS-ANCHOR-COVERAGE-20261017`按原v2重测精确复现。第三句同句D/F可比8/8，但跨前两句参考仅了/e、泣/i共2/8，不能合并覆盖；两轴相对F方向不一致，不据小差判虚实相同。只用已有F音频一次固定RMS匹配接入原前三句作诊断，前两句PCM精确、工程不改；连续一致性待听，F局部偏好不自动带入。见[记录](../../reports/production/phonation-continuous-anchor-coverage-20261017.md)。


## F接入真实连续语境的正例（2026-10-17）

`AUD:PHONATION-CONTEXT-F-BASICALLY-CONSISTENT-20261017`记录“后面的更好，基本一致”：指后面的F接入诊断，第三句与原前两句虚实基本一致。确认这份连续PCM/固定第三句增益的组合，非逐元音同等级、F单因素病因或现有USTX已修复。见[正例记录](../../reports/production/phonation-context-F-confirmed-20261017.md)。作为后续评价器正例复核来源；覆盖与通用刻度不自动升级，原pending和工程保持。


## 雨爱第四句新Skill候选（2026-10-17）

`RESP:YUAI-S04-SKILL-REDRAW-CANDIDATE-20261017`在同一USTX只重制第四句，27阶段/80节点/9元音图审与当前预测后有限控制；完整工程原生区外20短句/263音素/138音符及参考原字节保持。技术true，首“不”普通连接的消融区分缺口及本句发声待听保留，流程false；前三句F正例不倒填。见[本轮记录](../../reports/yuai/fourth-phrase-redraw-20261017.md)。


## 第四句局部接受；第三句F落回工程（2026-10-17）

`AUD:YUAI-S03-CURRENT-PROJECT-AIRY-S04-OK-20261017`记录第四句“没问题”、第三句在OpenUtau工程“更虚、气声更多”。此前F连续音频基本一致的反馈保留，工程此前未写F。`RESP:YUAI-S03-F-NATIVE-WRITEBACK-20261017`仅第三句VOIC/BREC采用本次自身F和原生DYN43对应已听整句电平，两阶段输入精确于F，前两句/第四句PCM保持；新工程听感待确认，0.019dB量化及小尾差保留。见[写回记录](../../reports/yuai/third-phrase-F-native-writeback-20261017.md)。非通用参数、非全曲验收，旧流程缺口保留。


## 第三句F原生写回仍未接受；只读白烁比较（2026-10-17）

`AUD:YUAI-S03-F-NATIVE-STILL-UNSATISFACTORY-20261017`保留“还是不行”，旧F连续正例不抹除。`RESP:YUAI-S03-AUTHOR-READONLY-COMPARISON-20261017`对照31字：作者主唱前四句稳定VOIC114/BREC0/cl0559，第三句后半有另行高和声；当前第三句独立F组合，与第一句同/i/同68的最终voicing低约9.17特征单位而breathiness也更低。是当前实现线索，非输出dB/因果或通用处方；末“泣”书面时长少约0.68秒，音高动作位置不同。旧库/原声缺失，未复制作者值或生成新候选，歌曲/音频/Skill保持。见[对比记录](../../reports/yuai/third-phrase-author-comparison-20261017.md)。


## 第三句核心支撑/气声表面P、Q（2026-10-18）

`RESP:YUAI-S03-CORE-SURFACE-PQ-20261018`冻结两条当前主唱完整句对照：现版→P仅恢复有限元音VOIC，P→Q仅撤回强减BREC，pitch/phones/speaker/DYN保持，前两句及第四句PCM精确。原生路径/三通道/两阶段与两组8/8共同可靠字腹声学观测完成，听觉实感/暗压低感/连续性pending；主试听现版→P，单次整句电平匹配及原始同增益版均绑定。当前工程/Skill不改，非通用剂量或听感通过。见[本轮记录](../../reports/yuai/third-phrase-core-surface-contrasts-20261018.md)。


## P初步改善后原位供查看（2026-10-18）

`AUD:YUAI-S03-P-TENTATIVE-BETTER-VIEW-REQUEST-20261018`记录“好像好点，你改下项目，我看下”，不补虚实/明暗/最终接受。`RESP:YUAI-S03-P-NATIVE-WRITEBACK-20261018`仅第三句VOIC写P并将已听整体电平落实原生DYN5；模型输入精确于P，前两句/第四句PCM保持，与已听匹配版RMS差约−0.04007dB，新工程待查看。Q不采用，Skill不改；见[写回记录](../../reports/yuai/third-phrase-P-native-writeback-20261018.md)。


## P仍有问题后的全面参数/当前参考纠正（2026-10-18）

`AUD:YUAI-S03-P-STILL-PROBLEM-FULL-AUDIT-20261018`保留“还是有问题”及旧初步改善。`RESP:YUAI-FIRST4-FULL-PARAMETER-AUDIT-20261018`逐项36表达/154机制字段及前四句31字，只读当前换库参考、原件与播放链：当前保存我们静音/白烁主唱开启且+4.83dB/和声静音；当前参考两阶段41Bright+59Classic，我们主要65Normal+35Classic且第二句Normal100。b为既有c目录junction。当前P“泣”与“气”最终voicing差+0.43，旧F低9.17不再适用；7对3原生模型上下文跨音乐句不同。参考精确预测缓存缺失保持unknown，不新预测/音频，不复制数组或改工程/Skill；见[全面报告](../../reports/yuai/first4-full-parameter-audit-20261018.md)。这些是执行条件与旧解释纠正，不是唯一声学病因/通用剂量或听觉接受。


## 第三句帧声线R与保存播放选择（2026-10-18）

`RESP:YUAI-S03-FRAME-VOICE-R-20261018`只将同一工程两处mute修正为我们的主唱开启、参考主唱/和声静音，其它字节保持。新R仅研究第三句Bright41/Classic59帧混合，CLR/时长speaker、22pitch/263音素、138音符、人工发声/DYN和模型分组保持；两阶段speaker及新预测核实，邻句输入与PCM精确。R原始RMS高1.66862dB，另提供一次整句匹配0.82521847的连续对照，两版双F0共同8/8主体。听觉/采用pending，R未写工作工程，不据数值判实感或复原作者历史声。见[记录](../../reports/yuai/third-phrase-frame-voice-contrast-20261018.md)。


## 在同一工程查看R（2026-10-18）

`AUD:YUAI-SAME-PROJECT-REVIEW-WORKFLOW-20261018`明确后续修订直接落实同一USTX供OpenUtau查看，不是R接受。`RESP:YUAI-S03-R-NATIVE-WRITEBACK-20261018`第三句写入R帧声线cl01/cl05并用原生DYN−12落实已交付整句匹配电平；输入/预测精确于R、邻句PCM保持，新声与匹配R RMS差-0.0316103dB，听感pending。全部pitch/phone/音符/其它发声及参考保持，Skill不改。见[写回记录](../../reports/yuai/third-phrase-R-native-writeback-20261018.md)。


## R贴耳/演唱状态否决后查看既有Q（2026-10-18）

`AUD:YUAI-S03-R-REJECTED-PROXIMITY-STATE-20261018`记录“不行”及“更贴耳，和前两句感觉不是同一个状态唱出来的”，未补虚实/暗挤标签。`RESP:YUAI-S03-Q-NATIVE-AFTER-R-REJECTION-20261018`在同一USTX撤回R声线，恢复第一句基底并落实已冻结Q：保留P有声支撑，仅第三句BREC回模型预测，原生DYN7对应已交付整句电平，新声与Q匹配版RMS差0.0283528dB。22pitch/263phone/138音符及邻句PCM保持；R→Q不是单因素，Q听觉/采用pending、上下文未改。见[记录](../../reports/yuai/third-phrase-Q-native-after-R-rejection-20261018.md)。


## Q否决后核查真实上下文链路（2026-10-18）

`AUD:YUAI-S03-Q-REJECTED-CONTEXT-QUESTION-20261018`记录Q“不行”与用户模型预测/上下文怀疑，不补Q分轴标签。`RESP:YUAI-S03-CONTEXT-ENCODER-DIAGNOSTIC-20261018`加载本机实际语言模型，当前两段缓存重现<1e−4，同输入重复精确，中心16phone/token/时长/language保持而联合静顿上下文后16/16编码变化；证明编码上下文依赖，不证明贴耳病因或音质改善。variance含随机源待后续控制，本轮variance/声学/音频0，工程/Skill保持；见[分析](../../reports/yuai/third-phrase-context-mechanism-20261018.md)。


## AP/SP与原生上下文的结构验证（2026-10-18）

`RESP:YUAI-APSP-NATIVE-CONTEXT-LINK-20261018`对齐前四句31字6处谱面空隙；参考各有AP/SP但非全部100%覆盖，我们显式0。参考分析副本只删7AP/3SP、保留EP和所有剩余音符/曲线，覆盖前四句原生段3→7（完整20→24），分组与我们7段一致；31字phone符号保持、边界最多变35.417ms。证实这些标签导致当前分组差异，不证实贴耳/状态不一致病因；新variance/声学/音频0，当前工程/Skill保持，下一有限对照按自己时钟设计，不铺满全曲。见[分析](../../reports/yuai/apsp-context-link-audit-20261018.md)。


## 前三句有限AP/SP上下文工程候选（2026-10-18）

`RESP:YUAI-FIRST3-APSP-CONTEXT-CANDIDATE-20261018`按用户请求在同一USTX前三句加入自己时间轴5AP/5SP，原生5→2，总22→19；138原音符字段和非PITD曲线节点保持，新基底重编码原绝对目标误差<.501c。phone边界最多变59.375ms，窗u55.208ms保持；范围外116音符phone/17pitch精确、第四句输入/PCM精确。新预测/两阶段speaker/三通道/输出与新双F0核查完成，原增益下RMS变化约−3.527/−0.515/+1.073dB，不作额外补偿，部分新AP/SP采原VOIC尾部。听觉及上下文病因仍待验，非严格共同噪声因果；Skill不改。见[记录](../../reports/yuai/first3-apsp-context-candidate-20261018.md)。


## GUI音色映射条件核查（2026-10-18）

`RESP:YUAI-VOICE-REMAP-DIALOG-AUDIT-20261018`记录energy(curve)→Cute参考截图及用户“我们的轨道也会弹”。本机App IL证实导入模式错误包含ene且不查空节点；当前参考ene空、cl01已存在，此截图分支预计跳过，不等于整轨Cute。当前我们磁盘无该导入候选，具体现场映射未知；CLR映射/有值导入确可能改变UI条件，旧反馈保留并标现场来源待核，不一概作废。工程/Skill/软件/音频保持；见[核查](../../reports/yuai/voice-remap-dialog-audit-20261018.md)。


## Skill回填：上下文前置与现场试听条件（2026-10-18）

`RESP:SKILL-CONTEXT-LIVE-CONDITION-UPDATE-20261018`按用户要求仅更新5份Skill文档：AP/SP/RenderPhrase在发声校准前核定；新增非唱区检查旧控制尾部；加载/音色映射区分磁盘与现场；保持自有目标重编码不冒称新画线；含糊反馈不升级因果。40资源安装精确、128引用、9项知识契约通过，6情境仅Agent手工复查，未加自动门禁/新声音或通用数值配方；127保护SHA保持。见[更新报告](../../reports/production/skill-context-and-live-condition-update-20261018.md)。


## 第四句明暗与压低感否决（2026-10-18）

`AUD:YUAI-S04-DARK-LOWERED-NOT-CLEAR-20261018`：用户指出第四句太暗、像压低声音、不够清亮，要求按新Skill重做；不补虚实/响度或病因标签，旧局部接受保留时态。见[反馈](../../reports/yuai/fourth-phrase-dark-feedback-20261018.md)。


## 第四句新上下文/清亮方向候选（2026-10-18）

`RESP:YUAI-S04-CLEAR-CONTEXT-CANDIDATE-20261018`：同一USTX第四句加入自己时钟2AP/1SP，原生2→1/全19→18；保留自有音高重编码<.501c、撤回六负BREC，原VOIC/声线/TENC/DYN保持。151notes/276phones，148原note字段、区外139旧note phone/17pitch及前三句两阶段输入/预测精确；旧/新前三句PCM微差与首轮错误相等断言保留。原增益RMS−.7741dB，无补增益；9元音图审/双F0及输入重建完成，清亮/压低感/虚实待听，不判病因。见[记录](../../reports/yuai/fourth-phrase-clear-context-candidate-20261018.md)。


## “了”后颤抖喘气声（2026-10-18）

`AUD:YUAI-S03-LE-POST-BREATH-TREMBLE-20261018`：第三句“了”后有颤抖喘气声；对应已知AP28.20–28.522917秒但病因未确认，未补其它维度标签，第四句候选待评不变。见[反馈](../../reports/yuai/third-phrase-le-breath-feedback-20261018.md)。


## “了”后AP局部音量候选（2026-10-18）

`RESP:YUAI-S03-LE-BREATH-ENVELOPE-CANDIDATE-20261018`同一USTX仅DYN在AP28.20–28.522917秒内部有限衰减，保留了尾和下一雨字头/151notes/18原生pitch-phone以及前四句两阶段输入、预测、speaker；完整AP实测约−24.00dB，平台−24.16369dB，事前±.15dB精度失败保留，无改剂量/放宽。非AP PCM微差另列；未判颤抖病因或声音修复，听觉pending，不作为所有呼吸默认配方。见[记录](../../reports/yuai/third-phrase-le-breath-envelope-candidate-20261018.md)。


## 下雨了三字偏虚（2026-10-18）

`AUD:YUAI-S03-XIAYULE-AIRY-20261018`用户反馈这三字有点虚；上一轮仅AP音量，唱字输入未改，不据先后推断病因，亦不补其它维度或接受。见[反馈](../../reports/yuai/third-phrase-xiayule-airy-feedback-20261018.md)。


## 下雨了三元音BREC有限候选（2026-10-18）

`RESP:YUAI-S03-XIAYULE-BREC-CANDIDATE-20261018`同一USTX仅ia/v/e元音内部BREC有限下调，保留已有VOIC和声线/TENC/DYN/AP气口；新增元音外0帧、模型裁剪0、151note/18原生pitch-phone精确，前两句及第四句输入/PCM精确。RMS约−.164/+.044/+.066dB，无补音量；新双F0与实际图审完成，不判更实/更清亮或唯一病因。听感pending，变暗/压低副作用待听。见[记录](../../reports/yuai/third-phrase-xiayule-brec-candidate-20261018.md)。


## 三元音BREC候选否决/白烁研究授权（2026-10-18）

`AUD:YUAI-XIAYULE-BREC-REJECTED-AUTHOR-REVIEW-20261018`：用户“不行，你看下白烁的这句”，当前候选未接受；不补其它轴，研究授权不等于逐点复制。见[反馈](../../reports/yuai/third-phrase-xiayule-brec-rejected-20261018.md)。


## 下雨了白烁定点复核（2026-10-18）

`RESP:YUAI-XIAYULE-AUTHOR-FOCUSED-RECHECK-20261018`重查当前未改参考语义/运行时后复用完整原生：参考三字VOIC114/BREC0，实际Bright41+Classic59，自己已有更强局部VOIC/负BREC；参考预测段还含后句看不清，我们仅第三句。了元音477.1/596.9ms，中间半段范围135/68.9c，不代表颤音标准或实感分。上轮BREC候选否决，停止加码；下步应独立查自身上下文/声线，再看了承载，不能复制数组。参考预测/PCM未知，新模型/音频0、工程/Skill保持。见[报告](../../reports/yuai/xiayule-author-focused-recheck-20261018.md)。


## 自身第三/四句联合上下文候选（2026-10-18）

`RESP:YUAI-S03S04-JOINT-CONTEXT-CANDIDATE-20261018`仅在自己31.9–32.5秒间隙加1SP，第三/四句共同预测，2→1/全18→17；151原note及非PITD曲线精确，自有目标重编码<.501c，区外16pitch/127旧note phone保持。两句phone最多变12.5ms，新17元音图审/双F0及输入重建完成，前两句输入/PCM精确；第三/四句RMS约−.322/+1.697dB，无补增益。非参考精确边界/曲线复刻，非严格同噪因果；听感pending，不自动声线/剂量加码。见[记录](../../reports/yuai/third-fourth-joint-context-candidate-20261018.md)。


## 第三/四句共同上下文局部接受（2026-10-18）

`AUD:YUAI-S03S04-JOINT-CONTEXT-LOCAL-ACCEPTED-20261018`用户“可以了，然后看下需不需要返回去修改skill”，即时回复当前同一USTX共同上下文候选，记录局部完整组合接受；非逐元音/分轴或整曲接受、不证明联合分段唯一病因/通用规律。旧BREC否决及原收据保持，来源按紧邻交付绑定。见[接受记录](../../reports/yuai/third-fourth-joint-context-accepted-20261018.md)。


## Skill窄范围回填：完整预测段与联合检查（2026-10-18）

`RESP:SKILL-JOINT-CONTEXT-LOCAL-ACCEPTANCE-UPDATE-20261018`按最新局部组合接受，仅改AP/SP、逐句流程、虚实连续性三页：列全部前后唱字/token/边界，不以段数当等价；VOIC/BREC否决后条件回查；联合重算复查实际受影响邻句，接受不反推单参数有效或通用连接方式。40安装精确、129引用、9本机知识契约通过，手工情境非独立前测，无新自动门禁/模型/音频，歌曲SHA保持。见[更新记录](../../reports/production/skill-joint-context-accepted-update-20261018.md)。
