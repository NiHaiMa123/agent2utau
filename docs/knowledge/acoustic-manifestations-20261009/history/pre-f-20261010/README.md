# 演唱声学表现、OpenUtau控制与当前响应证据

研究日期：2026-10-09。范围：完整演唱描述框架、OpenUtau可调输入的分层清单、当前YousaV1.65c及《最后一页》受控/观察证据。只读研究，没有新合成、改USTX、修改Skill或追加单点候选。Agent没有有效听音工具，本报告的听觉结论只引用用户反馈。

**确认计划正在执行：** [阶段A结构审查](table1-review.md)覆盖原31行、提出47个分层实体；[字段规范](table1-schema.md)区分实体类型。[阶段B](table1-source-review.md)核对30条说法/25来源，完成[31行定义](core-definition-review.csv)及[30组听感词](composite-review.csv)审查，保留缺口。[阶段C](table1-control-review.md)固定范围审查完成：[352条具体项](control-details.csv)，前320个ID保持，覆盖48组；[31节点](graph-node-review.json)、导出/播放/pan law、[23项本机矩阵](local-capability-review.json)及[103偏好字段/8嵌套属性](editor-preferences-review.json)等。本机缺失、未读消费者/非默认执行/插件/设备仍unknown。[阶段D](table1-measurement-review.md)已有[50协议](measurement-protocols.json)覆盖A47及3个B候选；10组数组检查通过只限明列范围，全部测量方法及真实音频检测性能未验证通过。机制与测量均不能代替试听；[阶段E](table1-coverage-review.md)冻结[42项清单](coverage-checklist.json)后完成[36主映射/6过程复查](description-coverage.json)，34项结构可记录、8部分表达；16标签行/0完整测量结论分栏，链接34候选/16未覆盖。下一步F正式整合及引用/ID迁移，尚未执行。原清单暂不改，[候选ID迁移](id-migration.json)未应用。状态见[计划](../../../plan.md)，绑定见[审计](table1-execution-audit.json)。

<!-- SECOND-LAYER-INDEX -->

**第二层已单独整理：** [条件—干预—响应—听觉结果](conditional-responses.md)，含10条条件干预、2组关联、2项技术审计与48类控制覆盖/缺口。原表保留索引职责；局部接受、无效和副作用并存，不自动生成调参配方。

<!-- /SECOND-LAYER-INDEX -->


## 1. 怎样满足“原子化”与整曲覆盖

不能把“撕裂、饱满、假音、自然”硬设成互斥原子。它们重叠、多义，同一词可以来自不同声学路径；同一原子在不同歌词、音区、风格里可以好听或难听。本表采用**31项可操作描述维度 + 30项组合词映射 + 48类控制/编辑/配置入口**。这是本项目提出的工程描述框架，**不是已经验证完备或互相正交的科学标准，也不宣称31项足以无损重建波形**。

整首歌按时间写出这些维度的连续值与事件，再记录它们在音素→字/音符→乐句→全曲上的关系。pitch、周期性、谐波谱、噪声、声道滤波、振幅/时钟、瞬态、空间/混音共同构成声学描述。任意新增听感词先映射到这些域的一个或多个事件，不因它不是旧词表中的词就无法记录。可附任意谱/波形残差、阶段/上下文、听者原话和unknown，不能为强求有限词表而把未知硬塞成“正常”。

**可闭合的是记录格式和声学域，不是有限形容词全集或审美判断。** 如需波形级完备，必须保留实际多声道波形/充分的时频信息，不能用31个简化指标取代；如需“好听/难听”，还要音乐身份、歌词/语义、风格、动作目的、结构组织、伴奏遮蔽及听者评价。原子描述≠病因，模型条件≠人体量，原始RMS≠感知响度，F0正确≠发音自然。[声质联合模型](https://pubmed.ncbi.nlm.nih.gov/33514179/)支持这种分层思路，但该研究的200个voice token并不是本曲、全曲音乐或所有唱法的完备性验证。

质量不强制给每个原子一个“越大越好”的方向：粗糙可以有意，气声可以贴耳，直音可以稳定，颤音可以自然也可以晃，弱收尾可以合理也可以漏底。每个事件额外记录：目的、局部期待、听觉标签、适用条件、证据类型、不确定范围。

## 2. 原子表现表

P=音高，L=强弱/振幅，S=声源/噪声，R=共振/谱包络，T=音素/动作时序，X=失真/混音/空间。这里的“原子”指可以分别标注和调查的操作维度；其代理指标与控制可能耦合。测量一栏是建议的观测方式，**不是已经实现/验证的异常检测器**；听觉未标注时保留unknown。

| ID | 原子维度 | 可描述的表现 | 声学观测/限制 | 可能影响的入口 | 如何影响/不可混同 | 当前证据 |
|---|---|---|---|---|---|---|
| P1 | 音高中心 | 准、偏高、偏低、八度错误 | 可靠有声段F0相对音乐目标的cents误差；保留无声/估计冲突 | note tone、tuning、pitch点、PITD；条件pitch与输出pitch分开 | PITD增加100c使目标线升1半音；实际PCM需复测，不能修口型冒充修音准 | M1；没有全曲听觉验收 |
| P2 | 音高慢趋势 | 平直、推进、回落、越唱越高/低 | 元音内非周期中心走势、c/s及持续时间 | pitch点/PITD的锚点、斜率、支撑 | 慢趋势不是颤音；改变F0也会改变预测发声与谱，响度方向未定 | M1、M8；源观测unknown保留 |
| P3 | 换音轨迹 | 滑音、倚音、上挑、下滑、连贯/突跳 | 起止音程、到达时刻、过冲、斜率、加速度、与元音起点关系 | note衔接、pitch插值形状/PITD、音素时钟 | 同一音程可以快/慢到达；数学连续不保证音色和发声连续 | M1、M8；未有统一自然斜率 |
| P4 | 音高周期调制 | 直音、颤音、摇晃、音高颤抖 | 调制频率Hz、深度c、规则性、相位、进入/退出 | vibrato length/period/depth/in/out/shift/drift，或函数PITD | 周期200ms=5Hz；depth25c为正弦峰幅，峰峰50c；越深不等于越好 | M2；文献S4；未验证本曲颤抖病因 |
| P5 | 音高非周期扰动 | 抖动、游移、短促音高裂点 | 去趋势/周期后的短时F0残差；稳定周期段才考虑jitter | 局部pitch/PITD、音素与模型条件；无独立真实jitter旋钮 | 无声段、颤音、倍频误检不可算生理jitter；随机加噪不能自动得到自然 | S1、S3；当前未测可靠jitter |
| L1 | 总电平与感知响度 | 大、小、压过/被伴奏盖住 | RMS/dBFS、短时响度、频谱、同播放条件；二者不可混用 | DYN、track volume、VOL(支持引擎)、发声条件、伴奏平衡 | DYN纯乘法可确定电平；模型参数同时改谱，RMS相近仍可能听弱 | M3、E4 |
| L2 | 非周期强弱包络 | 渐强、渐弱、长音漏底、忽大忽小 | 30/50ms RMS包络、低谷深度/长度、字头/腹/尾分区 | DYN函数/控制时间、ATK/DEC/包络(采样引擎)、VOIC等间接路径 | 保留有目的的强弱；整字平均掩盖接口低谷，不能逐字归一 | M3、E4、E5 |
| L3 | 音量周期调制 | 音量颤抖、脉冲、呼吸感、抽动 | 振幅调制频率/深度、与F0调制相位、频带包络 | DYN、vibrato vol_link(版本支持)、模型发声曲线间接影响 | 音高颤音经过谱/共振变化也会形成AM；不是看到抖就加减PITD | M2、S4；当前没有单因素听觉规律 |
| L4 | 瞬态电平不连续 | 突然爆一下、塌一下、字头/尾断层 | 增益跳变、峰值、接口短窗、crest factor | DYN节点与坡度、拼接、ATK/DEC、混音、模型上下文 | 缓变增益可避开人工跳变；模型谱/源突变不能只靠DYN解决 | M3、E3、E4 |
| S1 | 周期声源与有声支撑 | 有芯、漏声、无芯、清声/弱周期声 | 周期/噪声分解、CPP、HNR、谐波幅度；依赖元音与音区 | VOIC、BREC、音高/SHFC、speaker、模型；ENE仅启用时 | VOIC正增量提高模型voicing条件，不保证更响/更实；假音仍可以有明确周期 | M4、E6、S1、S5 |
| S2 | 谐波谱形 | 明亮/暗、厚/薄、锐/柔、金属感 | 经共振影响校正的H1-H2、分段谱斜率、谐波分布 | TENC、GENC、SHFC、speaker、F0、模型；EQ后处理改输出谱 | 高频增加常使更亮，也可能尖；不存在TENC数值直接等于饱满度 | M4、M5、E1-E4、S2 |
| S3 | 非周期噪声比例 | 气声、沙声、漏气、干净/浑浊 | 分频带噪声/谐波关系、CPP/HNR；区分辅音摩擦和元音气声 | BREC、VOIC、speaker、模型/声码器；BRE旗标仅对应引擎 | BREC负增量降低模型breathiness输入；本轮-10六组无可感知改变 | M4、E7、S3 |
| S4 | 噪声频谱与位置 | 气流、嘶、刺耳齿音、低频风噪 | 噪声频带/持续区、谱质心、辅音/元音分类 | 音素选择/长度、BREC、声库、LPF/旗标(采样引擎)、EQ | 摩擦音不是气声异常；提高/降低总气声未必改变目标频带 | S1、S3；无本曲已验收修法 |
| S5 | 次谐波与多周期结构 | 粗糙、颗粒、嘶吼、双音、撕裂的一类 | F0/2、F0/3等结构、侧带、多周期、谱与听感联合 | 声库/模型可表达能力、GRWC/Hifisampler仅对应引擎、发声条件候选 | TENC不是可靠growl开关；粗糙也可为有意唱法；当前未证实次谐波 | S6、S7；当前引擎无已验证独立粗糙度控制 |
| S6 | 发声中断与恢复 | 破音、断声、失声、声区突然翻转的一类 | 有声连续性、短时F0/谱/电平突变及恢复时钟 | F0与条件进入、SHFC、音素边界、speaker、模型 | 输出不满幅仍可听到破音；SHFC抱B有字头破音反馈，C只获局部可用 | E2、E3；破音具体声学种类unknown |
| R1 | 元音共振位置 | 开/闭、前/后、圆唇、口型变窄、元音偏移 | F1/F2/F3及带宽与谱包络；高F0需防LPC锁谐波 | 音素/语言/字典、GENC、SHFC、speaker、模型、F0间接 | 正常元音变更应变化；GENC非独立F1/F2/舌位控制；不能由主观口型倒推生理位置 | M5、E8、S8、S9 |
| R2 | 共振宽度与峰谷形状 | 集中/散、尖/闷、某频带凹陷 | 共振带宽、谱峰/谷、分带能量，避免把谐波峰当共振峰 | 音素、声线/模型、GENC、发声状态；EQ只改输出 | 能量谱形与声道滤波不完全可分；单个频带下降不证明formant漂移 | E4、S1、S8 |
| R3 | 共振过渡与字内稳定 | 口型漂移、共鸣断层、变嘴型、元音渐变 | 同元音核的谱包络运动；CV/VC、双元音轨迹/持续时间 | 音素时钟/序列、上下文、speaker变化、SHFC/GENC时间形状 | ao/uo等自带运动不能强求静止；控制平台相同也可能因上下文预测变声 | E3、E8、M8；未独立测F1/F2漂移 |
| R4 | 鼻腔耦合相关谱形 | 鼻音、鼻腔色彩、闭塞/闷的一类 | 鼻化峰/反共振、带宽、口/鼻音上下文；避免单峰判鼻化 | 鼻音音素与时序、speaker、TENC/模型候选；无鼻腔独立旋钮 | n/m/ng需要正常鼻音；TENC改变不等于确定降低鼻化 | S8、官方DiffSinger说明；本曲因果unknown |
| T1 | 整体发声落点 | 抢拍、拖拍、字头太早/晚 | 音符、辅音、元音开始与节拍/原曲各自偏差 | note/part position、tempos、音素offset、字头提前量 | 移音符改变时钟和上下文；小对齐误差不等于可听问题或歌唱身份错误 | M7、E8 |
| T2 | 音素承载时长 | 吞字、拖字、元音不够、声母过长 | 辅音/元音/韵尾时长ms、比例；保留双元音内部运动 | note duration、延音+、音素边界、duration模型、VEL仅有读取路径时 | 延长元音改变模型帧数/相邻承接；当前g→uo无大错位证据，不盲拆uo | M7、E8 |
| T3 | 辅音动作与清晰度 | 咬字清晰/含糊、硬/软、齿音重、爆破弱 | 爆破/摩擦瞬态、VOT/送气、频谱和辅音相对元音电平 | phonetic hint/override、字典/phonemizer、音素时长、声库、包络/VEL支持路径 | 模型条件可间接改字头；抱C b电平约降5.326dB，但不等于用户判咬字坏 | E3、E8、S8 |
| T4 | 起声协调 | 气起、硬起、柔起、卡字头 | 辅音/呼气/周期声建立顺序、起声时间和谱电平运动 | AP/音素、pitch到达、发声/SHFC函数进入、采样包络 | 音量attack、辅音长度与发声条件进入是不同路径；145ms不推广成通用值 | E2、E3、M7 |
| T5 | 跨音素衔接 | 连唱、断唱、粘字、换元音突变 | 音素间gap/overlap、谱/F0/电平连续性、上下文一致 | phonemes/offset/延音、分句、声线、各曲线时间；oto overlap仅采样库 | 词表正确不能保证过渡自然；模型完整句重算可能影响邻字 | E4、E8、M7、M8 |
| T6 | 收声与韵尾 | 自然收束、硬切、拖尾、尾字漏声、韵尾丢失 | 元音→韵尾→静音时钟、能量与周期声释放 | note/phoneme末端、SP/AP、pitch/发声/DYN退出、DEC/释放时间支持路径 | 只拉低增益可丢韵尾；持续有声和气尾需分别描述 | M3、M7；本曲未有因果验收 |
| T7 | 呼吸与静音组织 | 换气、喘、气口短/长、断句不对 | AP/SP/空隙长度、呼气噪声电平、与下一元音位置 | AP/SP、note/part间距、词/句划分、DYN、模型上下文 | AP不等于静音；SP不是任意漏声标签；呼吸位置属于音乐意图 | M7、M8；按当前原曲独立判断 |
| X1 | 非线性失真 | 削波、炸、过载、破音的一类 | 满幅平台/削波比例、谐波扩展、true peak、失真残差 | DYN/track/VOL增益、叠加、压缩/限制路径、PCM格式 | 降低增益可防后级过载；不能修合成前声源异常；当前破音无文件满幅削波 | E2、E3；未检验全部播放设备 |
| X2 | 数码/拼接伪影 | 咔哒、毛刺、金属颗粒、重复纹理、边界接缝 | 波形/导数不连续、异常时频结构、重复/相位、边界残差 | 分句/重叠组装、声码器/重采样、steps/depth、缓存/导出完整性 | 变化可能来自模型或组装；steps增多不保证更自然；不能把画线检查当听音 | M8；未有通用伪影阈值 |
| X3 | 遮蔽与声部平衡 | 埋在人群/伴奏、突出、字被盖住 | 人声/伴奏分带与时序关系、混音/纯人声两种试听 | track volume、伴奏音量/位置、pan、EQ、编配/导入轨道 | 同人声在不同伴奏可清楚/不清楚；固定增益比较仍保留真实遮蔽 | M9；本轮固定1.5/.7 |
| X4 | 空间与相位关系 | 近/远、干/湿、空/贴、宽/窄、重影 | 直达/混响比例、尾长、pre-delay、声道互相关/相位 | pan、多轨叠加、混响(版本支持)、导入音频、声道/导出 | 空间能改变清晰/饱满感觉但不直接改合成音素；本轮未用效果器 | M9；当前安装效果器能力未验证 |
| X5 | 频带与录制/导出质地 | 闷、亮、低保真、底噪、失去空气感 | 频带范围、噪声底、采样率/位深/编码、EQ响应 | 声库/声码器匹配、LPF/引擎旗标、EQ、导出格式、导入音频 | 本模型mel 40-16000Hz与输出44100Hz不是同一种频带声明；格式不能恢复缺失发音信息 | M8、M9；未听验收 |

## 3. 用户听感词怎样分解

下面是组合词的解释入口，不是看到一个词就自动写参数的处方。“假音/头声/胸声/混声”记录感知标签；对神经合成输出不能依据听感或model tensor断言人体M1/M2生理机制。[同音符实声/假声研究](https://pubmed.ncbi.nlm.nih.gov/24437789/)显示声源与共振可同时不同，且个体策略不统一。[粗糙唱法研究](https://pubmed.ncbi.nlm.nih.gov/34972633/)也说明粗糙并非只能靠F0或响度描述。

| 听感/表现 | 原子组合/关系 | 解释与边界 |
|---|---|---|
| 撕裂、嘶吼 | S5+S3+S2，或S6/X1 | 先区分有意粗糙唱法、发声失稳、数码过载；TENC不是通用撕裂度 |
| 沙哑、颗粒、毛糙 | S3+S5+P5，可能X2 | 非周期噪声、多周期可分别或共同出现；不能用jitter单指标包办 |
| 破音、炸一下 | S6/P1/P3、L4、X1/X2的不同组合 | 当前抱B只有字头破音反馈，具体类型尚未归类 |
| 颤抖、摇晃 | P4/P5、L3、R3、S1变化 | 记录是哪条维度、频率/深度/规则性；颤音与抖动质量依上下文 |
| 饱满、有芯、厚实 | S1+S2+R1/R2+L1/L2；混音还有X3/X4 | 可在不增大RMS时变实，也可变响却仍薄；不设统一能量阈值 |
| 薄、虚、空、飘 | S1/S2/S3+R1/R2+L2，可能X3/X4 | 薄可能是有意声色，也可能支撑缺失或被伴奏遮蔽 |
| 假音感、头声感 | S1/S2/S3+R1/R3的联合听感与音区上下文 | 音频和模型输入不能证明人体M1/M2；假音不等于气声或小声 |
| 实声感、胸声感 | S1/S2+R1/R2+起声/承载方式 | 当前抱C更实并获局部可用；没有统一提高VOIC规则 |
| 混声、换声顺畅 | 跨P/S/R维度的协调变化+T5 | 混声不是单个声学原子或确定模型开关 |
| 挤、紧、顶、喊 | S2+R1/R2/R4+L1+T4，可伴S6 | 主观顶不等于喉位真实上升；TENC升降与听感方向依条件 |
| 气声、耳语、漏气 | S3/S4+S1+T4/T6 | 耳语缺乏周期声，气声可保留周期；BREC模型条件不能代替声源分析 |
| 明亮、尖、刺 | S2+R2/S4+X5 | 区分谐波亮度与噪声齿音；亮度不自带好坏 |
| 暗、柔、闷、蒙 | S2+R1/R2+X5/X3 | 暗柔可有意；闷也可为混音遮蔽；GENC并非统一亮度旋钮 |
| 鼻、堵、鼻腔色彩 | R4+R1/R2+音素上下文 | 正常鼻辅音与不需要的元音鼻化分开 |
| 口型不稳、舌根后缩感 | R1/R3+S2+T5+声线条件变化 | 当前为听感描述，无独立声道/formant漂移测量或生理结论 |
| 突然像换了人 | P/S/R的跨字一致性+speaker条件+X4 | 先看实际两阶段embedding，不用suffix或单字CLR推断整句 |
| 硬起、爆字头 | T4+T3+L4+S2/S6 | 可有意重音，也可出现突变；不同控制attack不混同 |
| 软起、虚起、气起 | T4+S1/S3+L2 | 有目的的起声与元音到位不足分开 |
| 咬字清楚、含糊、吞字 | T2/T3/T5+R1+X3 | 词表正确和ASR可懂度不能单独宣布自然 |
| 连贯、粘、断、磕绊 | T5+P3+R3+L4+S6 | 时间/F0连续只是部分条件，不能直接判声线连续 |
| 滑、拐、跳得太高 | P3+T1/T2+R3/S6 | 先判断音乐音程与动作；不靠统一平滑掩盖错音 |
| 直、平、机械、僵硬 | P2/P4+L2+R3+T1/T4/T6与跨句组织 | 所有字重复同动作可能机械；添加随机波浪不等于自然 |
| 稳、松弛、自然 | P/L/S/R/T的情境一致与合理变化 | 不是方差越小越好；本模型尚无全曲自然度自动判定 |
| 无力、漏底、支撑不住 | S1+L2+S2+T2/T6+X3 | 先分声源与输出包络；不能小声就加VOIC |
| 渐强、蓄力、爆发、回收 | P2+L2+S2/S3+T4/T6的阶段组织 | 强弱、音高、张力不必同步增大 |
| 抢、赶、拖、松紧不对 | T1/T2/T7加乐句节奏组织 | 对齐原曲、节拍及演唱意图三者关系；不是看单字起点 |
| 哭腔、哽咽、泣音 | P2/P3+S6/S3+T4/T6及语义组织 | 可作组合标签，不能伪造一个哭腔数值开关 |
| 笑感、甜、冷、温暖、情绪充足 | P/L/S/R/T+歌词/音乐与听者解释 | 语义与风格标签需上下文和听觉评价；没有声学一对一逆映射 |
| 近、贴耳、远、空灵 | X4+S3+L1+X3 | 空间与发声可共同造成；不要将混响效果说成口型修复 |
| 好听、难听、像不像原唱 | 全部原子时序+旋律/歌词/风格/混音/听者偏好 | 是整合评价，不能作为一个原子或由单个特征阈值决定 |

## 4. OpenUtau所有可调入口的清单与边界

“所有东西”按**会影响声音/模型输入/音乐时钟/呈现，或控制可用性**盘点。纯窗口颜色/缩放、快捷键等没有直接DSP作用；它们列在C48，不能包装成声学控制。撤销、量化、复制、移调、预设、生成pitch等操作最终仍写入本表某类输入，不算新的生理维度。

分清三层：(a)已核对本机实际渲染路径；(b)当前官方固定提交有的功能；(c)第三方renderer/resampler/phonemizer开放扩展。官方上游固定提交见下面来源，**不是本机Core的字节等同证明**。新上游图、masked曲线、growl、内置混音等在本机未核对的能力明确标为未确认，不能作为现有可用旋钮。外部插件/引擎可以定义任意数量的参数，软件的全部未来/第三方参数名称不可能有限穷举；其入口属于C30/C36/C38/C39，必须按实际插件再登记名称、单位、读取路径和响应，而不是漏项装作完备。

本机事实：Yousa支持key_shift/speed/breathiness/voicing/tension；energy/falsetto未启用。实际新variance与acoustic均Normal75/Classic25；GENC=0、velocity=1。本曲发布SHFC声明±12c（不是±12半音），受控诊断另行明确±1200c。本次只记录这个单位/范围差异，没有改发布工程。PEXP虽有pitch模型支持，现行制作仍由Agent自主函数画线。模型质量/随机设置是执行条件，不作不断扫参的演唱路线。[官方DiffSinger支持说明](https://github.com/openutau/OpenUtau/wiki/DiffSinger-support)明确多项需要声库/声码器支持。

| ID | 可调入口 | 主要影响 | 支持范围/本机状态 | 单位/换算 | 如何作用 | 证据索引 | 已知边界 |
|---|---|---|---|---|---|---|---|
| C01 | 音符中心 tone、tuning、全曲移调 | 音高/音乐内容 | 通用音符；实际读取依引擎 | tone半音，tuning cents；+4key通常需明确为+4半音 | 改变中心/模型音区和部分音素条件；不是仅改变PITD | M1、M8 | 当前流程保留Agent选择note衔接；暂无统一移调自然阈值 |
| C02 | 音符 pitch 点X/Y、插值形状、snap_first | P2/P3 | 通用音高基底 | X相对音符ms，Y为0.1半音；l/i/o/io，sp见新上游 | 锚点与插值改变到达、斜率、过冲；snap_first接前音，PITD还会叠加 | M1、M2 | 旧基底不能当最终目标；未验证本机sp新功能 |
| C03 | PITD | P1-P5；间接S/L/R | 当前DiffSinger支持 | cents；当前声明±1200 | 叠加在before-PITD，+100目标升半音；进入variance/acoustic/vocoder | M1、M8 | 目标F0保持不代表输出F0、谱、电平精确保持 |
| C04 | vibrato length | P4 | 当前结构存在；生产函数可另实现 | 音符时长百分比 | 决定周期段从何处开始；更大值覆盖更早 | M2 | 不是深度参数；当前发布许多length=0 |
| C05 | vibrato period | P4 | 当前结构存在 | ms；公式Hz=1000/period | 更短周期更快；200ms=5Hz、125ms=8Hz为算术例子 | M2 | 不把示例当推荐范围 |
| C06 | vibrato depth | P4 | 当前结构存在 | cents峰幅 | 25c为±25c，峰峰50c；更大范围不保证动听 | M2 | 需扣除与人工PITD的重复周期 |
| C07 | vibrato in/out | P4进入/退出 | 当前结构存在 | 颤音区时长百分比 | 调整周期幅度包络；不是移动整字时钟 | M2 | 过短/过长的听觉效果依音素/乐句 |
| C08 | vibrato shift/drift | P4相位/中心 | 当前结构存在 | shift周期%；drift深度相关偏移 | shift移动相位；drift移动周期中心，不能代替慢走势计划 | M2 | 无当前听觉单因素验证 |
| C09 | vibrato vol_link | L3与P4耦合 | 新上游明确支持；本机功能未审定 | ±100 | 0不联动，正负改变AM相位；上游100可到0.2～1.2倍振幅 | M2 | 不是每个版本都可用；不应用于当前探针 |
| C10 | DYN | L1-L4、T6/X1 | 当前支持，已核对原生乘法 | 节点×0.1dB；当前-240～120，默认0 | 10→+1dB×1.1220；30→+3dB×1.4125；最低声明值特殊为0振幅；5tick后振幅插值 | M3 | 这是输出增益，不直接修有声/元音；比较保持原生DYN |
| C11 | VOIC | S1，联动谱/电平 | Yousa启用；本曲合法范围自定义0～200 | 零增量100；Δ=(值-100)×12/100；最终clip[-96,0] | 110→预测上加1.2模型特征；不是+1.2dB；改变声学voicing输入 | M4、E6 | 统一更高更实有反例；当前未做独立VOIC声学改善验收 |
| C12 | BREC | S3/S4；间接S/R/L | Yousa启用 | 默认0；Δ=值×12/100；clip[-96,0] | -10→约-1.2模型特征；改变声学breathiness输入，不改变variance预测条件 | M4、E7 | 六条件均无可感知差别，不采纳该剂量；不证明整个通道无效 |
| C13 | TENC | S2及发声质地 | Yousa启用 | 默认0；Δ=值/20；clip[-10,10] | +20→+1模型特征；改变声学tension输入；亮/紧/鼻等响应依模型 | M4、E1、E6 | 取消+14即-0.7特征，抱无感知改善；非挤压/撕裂度一对一旋钮 |
| C14 | SHFC | 模型音区条件及预测、S/R/L/T | 当前pitch-controllable vocoder支持 | cents；原发布声明±12，诊断明确±1200 | -400c使variance pitch-4st、acoustic F0×0.7937005；vocoder目标F0保持；下游三预测会改变 | M5、E2-E4 | 抱局部正向但字头风险；果-200c无改善且响度下降；不作整曲规则 |
| C15 | GENC | 谱/共振相关条件R/S | Yousa use_key_shift_embed=true；当前基底0 | 曲线±100；本机augmentation range[-5,+5] | 本机gender输入由范围换算，-100→+2.4，+100→-2.4模型输入；不是F1/F2直接Hz设定 | M5 | 官方通用描述的±12半音不能冒称本机实际共振峰位移；尚无本机试听因果数据 |
| C16 | VELC | 元音动作速度条件T/R | Yousa use_speed_embed=true；当前实际1 | 默认100；2^((值-100)/100) | 0→0.5、100→1、200→2的speed输入；与VEL声母伸缩分开 | M6 | 这是声学速度条件，不保证音素边界按比例改；本曲未受控验证 |
| C17 | ENE | 能量/发声条件 | 引擎建议项；本机use_energy_embed/predict_energy=false | 默认0；Δ=值×12/100（启用路径） | 需要模型和预测共同支持才进声学输入 | M4 | 当前不生效，不是本曲响度修法 |
| C18 | falsetto embedding / prediction | 潜在发声条件 | 本机use_falsetto_embed/predict_falsetto=false | 无已确认当前可用独立假音表达缩写/控制路径 | 配置字段存在不等于可直接打开已训练能力或界面有旋钮 | 本机配置审计 | 当前没有假音开关；不得把SHFC效果当开启falsetto |
| C19 | CLR、speaker/subbank | 声线/音区/音素基底 | 当前支持；按音素index与名称映射 | CLR options含空默认；索引与clNN不同 | 改变音素suffix/默认声线，影响duration及模型speaker；只设index0不保证后续同色 | M7、M8 | 不能从Bright suffix推断实际两阶段embedding |
| C20 | cl01…clNN声线曲线 | 声线渐变与多阶段条件 | 当前五色Bright/Cute/Normal/Whisper/Classic | 0～100，名称/索引绑定实际库 | 权重总和>100%归一；不足部分回填该帧默认声线；全零不静音 | M7、M8 | 本轮两阶段Normal75/Classic25固定；无统一混合自然比例 |
| C21 | PEXP、生成/重生成pitch、retake | 预测音高表达P | 本机pitch模型use_expr=true，人工画线流程不依赖它 | 默认100；模型expr=clip(值/100,0,1) | 只在pitch预测路径调表达，人工完整目标不因改PEXP自动更新 | M6 | 算法预测是模型建议，不恢复自动修复/候选搜索制作路线 |
| C22 | 音符/part position、duration、tempos | T1/T2/T7和音乐组织 | 当前支持 | ticks→TempoMap ms；BPM改变换算 | 移动/拉伸影响音素时钟与完整预测；480PPQ下5tick在120BPM约5.208ms | M7、M8 | 拍号、key标记与网格本身不等于自动移调或改声 |
| C23 | 歌词、语言、多音字、phonetic hint、phoneme override | T3/R1/可懂度 | 当前Chinese phonemizer、字典/词表支持 | phoneme字符串、language id、按index改写 | 改变元音/辅音身份及条件；语言ID不能随便换；uo为整体token仍可输出内部运动 | M7、E8 | g/uo映射正确不证明咬字自然；不可盲拆uo |
| C24 | 音素offset/时长、延音+、AP/SP、分组/分句 | T1-T7及上下文 | 当前支持；部分符号需phonemizer验证 | offset ticks；持续音组/原生ms时钟 | 改变CV/VC承接、元音承载、呼吸/静音与整句预测；+避免重复声母 | M7、M8 | 时钟等于意图输入，非实际声学对齐真值；current未知保留 |
| C25 | VEL声母速度 | 采样伸缩/音素器属性 | 通用默认项；本次核对的DiffSingerBase未读consonantStretchRatio | 0～200默认100；属性比2^(1-VEL/100) | VEL200提示0.5倍固定区、VEL0提示2倍；生效须音素器/采样器读取 | UNote源码、M7 | 不能当当前Yousa已验证g/uo时长旋钮；与VELC不同 |
| C26 | VOL/ATK/DEC | 采样音量与包络L/T | Classic支持；DiffSinger不支持音素包络 | VOL0～200/100，ATK0～200/100，DEC0～100/0 | 调整采样phoneme整体/开始/结束包络；不进入本机DiffSinger声学feed | M10 | 有同名工程字段不等于当前响度生效 |
| C27 | preutterDelta、overlapDelta、attackTimeDelta、releaseTimeDelta | 采样提前/交叉淡化/包络时间 | 主要采样声库；DiffSinger supportsPhonemeEnvelope=false | 相对oto/包络时间，ms字段 | 改变采样固定区与相邻淡化/起落；不等于直接改本机模型音素时长 | M10 | 本机音素offset另行处理；不得混用oto与HFA时钟 |
| C28 | oto Offset/Consonant/Cutoff/Preutter/Overlap、alias、frq | 样本选择/伸缩/拼接/源F0 | 采样声库编辑与配置 | ms、别名、原始音频频率分析 | 切选录音区、固定/拉伸区、提前与交叉淡化、源pitch；可影响咬字/接缝/粗糙 | M10 | 改库可影响多曲；不用于当前DiffSinger模型phonemes作为oto修复 |
| C29 | ALT、SHFT | 替代alias/音区样本条件 | Classic及对应音素器；VOICEVOX/ENUNU也有自己的路径 | ALT0～16；SHFT默认±36半音 | ALT选替代录音；SHFT选音区/查询条件，不等于SHFC连续cents或全曲移调 | M10、M11 | 不同引擎同名意义不同，当前DiffSinger renderer未列SHFT |
| C30 | ENG、renderer、resampler、wavtool | 整条声学实现路径 | 各引擎/采样库 | 枚举/文件/引擎版本 | 更换算法/模型/拼接器改变支持项、谱、F0、噪声、缓存；ENG主要Classic逐音素选择 | M10、M11 | 不是新引擎调过的值可照搬DiffSinger |
| C31 | GEN(g)、BRE(B)、LPF(H)、NORM(P) | 采样flag谱/噪声/滤波/自动增益 | 取决于resampler；DiffSinger不读取这些flags | 默认GEN±100、BRE/LPF/NORM0～100；NORM86 | g/B/H/P是协议名，具体换算和方向由resampler实现；P会破坏固定增益可比性 | M10 | 本曲不用NORM归一；GEN≠GENC，BRE≠BREC |
| C32 | MOD、MOD+ | 保留采样原始音高起伏P | Classic/Worldline读取路径 | 0～100默认0 | MOD传给采样器；MOD+从frq保留伸缩后的录音音高细节并叠入目标 | M10 | 不是颤音深度；当前DiffSinger没这些源录音通道 |
| C33 | DIR | 绕过某些采样处理/使用引擎原pitch | Classic/Worldline及VOICEVOX的不同分支 | off/on | Classic取直接录音分支；VOICEVOX的首phone direct切换原引擎F0与人工F0 | M10、M11 | 不能作跨引擎统一“自然开关” |
| C34 | CLRY、XSY | 第二样本声线与交叉合成 | 新上游Classic/Worldline支持；本机未审定 | 第二声色枚举，XSY0～100 | 准备两种oto/声线后混合，具体实现可能波形/特征层；可生相位/声色过渡 | M10 | 不是当前DiffSinger clNN；未做当前因果验收 |
| C35 | GRWC、Hifisampler粗糙效果 | S5、S2/X2 | 新上游Hifisampler；当前DiffSinger不支持 | GRWC0～100 | 此实现对默认400Hz以上频段做80Hz方波音高调制、强度映射最大100c并能量匹配 | M12 | 人工粗糙效果不等于生理吼腔，也不是抱字头破音已知病因 |
| C36 | 自定义flags与表达声明、默认值、范围、类型、track覆盖 | 控制通道的可用性/剂量 | 开放扩展，需引擎实现 | Numerical/Options/Curve/MaskedCurve；min/max/default、flag | 声明只定义合法输入；实际支持/范围裁剪/模型clip需分别核查；新增任意名字不会自动进模型 | M13 | OPE在本地模板存在但当前DiffSinger无读取证据；其它扩展按能力清单登记 |
| C37 | VOICEVOX VOLC、SMOC、REPM、style | 引擎专用电平/预测pitch/音素替换 | 官方VOICEVOX renderer，当前不使用 | VOLC0～200/100；SMOC0～10；REPM建议项被注释 | VOLC乘引擎volume；SMOC用于LoadRenderedPitch平滑宽度；REPM路径须读版本/配置，不能当完整可用滑块 | M11 | 不移植给Yousa；同名CLR选VOICEVOX style |
| C38 | ENUNU styles/custom expressions、Vogen/Worldline声学控制 | 引擎专用发声/模型风格 | 非当前路线 | ENUNU由config extensions.styles定义；Worldline归一条件 | Worldline当前将TENC/BREC/GENC映射0.5+0.005x、VOIC0.01x，和DiffSinger预测增量不同 | M11 | 支持列表只说明可接收，不证明所有声库响应/听觉方向 |
| C39 | 声库、speaker embeddings、duration/pitch/variance/acoustic模型、vocoder、字典/subbank配置 | 所有声学能力与条件依赖 | 本机已哈希绑定；换资源需验证匹配 | 模型/词表/语言/频率/ mel/hop/augmentation/enable字段 | 这些限定可实现声色/音区/发音、预测与声码器；配置开关不能创造未训练能力 | M8 | 当前有声/气声/张力启用，energy/falsetto关闭 |
| C40 | DiffSinger steps/depth、pitch/variance步骤、speedup、随机输入/seed | 推理轨迹/质量/重复性 | 当前模型连续加速/variable-depth；seed在诊断接口控制 | 当前acoustic20/depth0.6，variance/acoustic种子11/101 | 不同采样设置可能改谱/细节/电平；更多步骤不是更好听保证；种子不是常规演唱旋钮 | M8 | 冻结用于公平对比，不能挑更响seed伪装规律 |
| C41 | 完整短语上下文、AP/SP、合并/拆分、padding、渲染缓存 | 边界与完整新预测 | 通用依赖；新上游有merge/local-patch偏好 | 本机head/tail各8帧、hop512/44100约11.610ms | 改pitch/phones/speaker/分句需重建对应预测；旧cached export≠新成声state；有padding overlap还需组装 | M8、E9 | 缓存是执行状态不是艺术强弱旋钮；不清空封存或恢复旧路线 |
| C42 | track volume、pan、mute/solo、导入伴奏位置/音量、多轨 | L/X与可听内容 | 当前支持，具体pan law依实现 | track gain dB、pan位置、开关、time | 正gain放大电平，声像/多轨改变平衡遮蔽/相位；静音只影响呈现 | M9 | 本次试验固定vocal1.5(+3.522dB)/backing.7(-3.098dB) |
| C43 | MixFx EQ总/模块开关、lowDb/midFreq/midDb/highDb、preset | X5及组合亮/厚/闷 | 新上游实现；当前安装未确认有该UI/路径 | dB/Hz，mid Q代码固定0.707 | 增益提高对应滤波频带；改变输出谱而非指定元音F1/F2；preset应用slider值 | M9 | 本轮没有EQ，不将其当发声修复证据 |
| C44 | MixFx压缩 threshold/ratio/makeup、preset、开关 | L1/L2、瞬态与抽动 | 新上游实现；本机未确认 | 阈值dB、比例、补偿dB；attack/release/knee代码与preset提供 | 高于阈值受比例压缩，makeup补电平；改变包络，可损失重音；attack等不都是独立UI滑块 | M9 | 本曲比较不压缩；不能直接声称能修元音共鸣 |
| C45 | MixFx混响 size/damp/wet/pre-delay、preset、开关 | X4及可懂度/距离感 | 新上游实现；本机未确认 | size/damp/wet标量、pre-delay ms；width/dry有preset内部设置 | size影响尾/空间、damp高频衰减、wet混入、pre-delay推迟湿声，dry仍按时 | M9 | 不能通过混响证明口型变自然；代码参数/界面参数分开 |
| C46 | 导出格式/采样率/位深、声道、重采样、播放/监听增益 | X1/X4/X5与听觉比较 | 依版本/导出接口/外部监听 | PCM格式、编码、声道与播放电平 | 量化/有损编码/转换可引入纹理或改变峰值；设备也改变响度谱 | M8、M9 | 本轮44.1k PCM同增益；不是OpenUtau全部播放设备能力声明 |
| C47 | 表达图、RPIT/PITO、曲线插值/函数时间形状/量化 | 已列P/L/S/R/T条件的组合/驱动 | 新上游有graph/masked curves；本机本流程用显式Agent函数 | RPIT/PITO绝对MIDI×100，graph算术/LFO/smooth/slew/随机/锚点 | 图是驱动已有参数的工具，不是新增生理变量；必须核对最终pitch/控制与合法范围 | M13、E3、E9 | 不恢复自动修复；新上游图能力与当前函数编译流程分开 |
| C48 | key/拍号、snap/grid、预设、显示、轨名/颜色、UI偏好 | 编辑/组织与工作可靠性 | 通用及版本差异 | 标签/网格/预设/开关 | key标记本身不移调；网格影响后续编辑落点，预设填控制值；颜色/缩放等无直接DSP因果 | UProject/UNote/Preferences源码 | 纯显示项纳入排除清单，不假称声学因素 |

### 4.1 不应混为同一件事的参数

- **PITD / SHFC / GENC / SHFT**：目标音高偏移 / 模型条件音区 / key-shift相关谱条件 / alias或特定引擎音区选择。不是四种写法的同一个移调。
- **DYN / VOIC / ENE / VOL**：后级增益 / 声学voicing条件 / 模型能量条件（当前关闭）/ 采样或特定引擎音量。不是四个等价响度旋钮。
- **VEL / VELC / phoneme offset**：声母伸缩提示或采样速度 / speed embedding / 音素边界时钟。某音素器不读取VEL提示时，它不能充当本机音素时长控制。
- **CLR / clNN / CLRY+XSY**：音素默认声色 / 帧级speaker混合 / 特定采样引擎第二样本交叉合成。名称索引、阶段和作用范围不同。
- **模型falsetto字段 / 主观假音感 / SHFC响应**：未启用能力 / 用户听感 / 当前可执行条件干预。不能互相代替。
- **TENC / 撕裂 / 紧张 / 鼻音**：模型tension输入可以影响若干质地，不能由参数名称宣称单独控制所有粗糙、挤压或鼻化。

### 4.2 本机已确认的数值路径

`TENC_final = clip(pred_tension + TENC / 20, -10, 10)`。

`BREC_final = clip(pred_breathiness + BREC * 12 / 100, -96, 0)`。

`VOIC_final = clip(pred_voicing + (VOIC - 100) * 12 / 100, -96, 0)`。

上式表示模型输入，不是输出dB/鼻化百分比/声带闭合商。独立检查须保留native float32运算顺序；除以20不能为了逐位精确擅自换乘0.05。零人工增量仍保留当前预测，所以同VOIC=100的两个元音/音区可能完全不同。自定义范围、原生加载合法范围、控制采样、最终feature clip四层都要核查。

`variance_pitch = target_pitch_semitones + SHFC_cents / 100`；本机pitch-controllable分支`acoustic_F0 = vocoder_target_F0 × 2^(SHFC_cents/1200)`。-400c倍率约0.7937005；这固定了声码器目标输入，**不固定实测PCM F0或发声状态**。SHFC还经variance改变voicing/breathiness/tension，并可影响邻字。当前尚未隔离“声学条件直接路径”与“预测发声下游路径”的各自听觉贡献。[上游renderer](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs)仅作源码机制核对，本机feed及封存对照才证明本次执行。

`DYN_gain = 10^((value×0.1)/20)`（最低声明值例外为0）。DYN+30对应+3dB电平，不是更实或感知响两倍。原生先5tick采样，之后输出振幅域逐样本插值；本机44.1k/512模型帧约11.610ms，不能把任意密度工程点当一对一模型帧控制。

本机GENC输入映射：augmentation[-5,+5]，负侧`-x×12/5/100`、正侧`-x×12/5/100`，所以-100→+2.4、+100→-2.4的`gender`张量值。这个算术**没有证明F1/F2整体移了2.4半音，更没有证明舌位移动**；官方通用声色说明不能替代实际模型响应。

## 5. 已探索证据：正向、无区别和副作用都保留

证据分为：**机制**（实际输入/官方代码）、**响应**（受控波形/特征变化）、**听觉反馈**（绑定具体音频）、**观察相关**（上下文不同）、**待验证**。不能合并为“已掌握通用调法”。当前原版318字仅5字有局部听感标签，另有接受抱C变体；313字仍unknown，不能统计为正常样本、泛化成功或检测器真阴性。

| ID | 探索/变化 | 适用条件/固定项 | 数据支持 | 用户听觉反馈 | 能支持什么/不能支持什么 | 原报告 |
|---|---|---|---|---|---|---|
| E1 | 取消抱的TENC+14 | 3:04 ao/B4，固定同噪声、其他人工控制与增益 | 24模型帧，峰值张力差-0.7；A/重复PCM精确 | 用户“没啥区别” | 该次取消未获可感知改善；不证明TENC所有剂量无效 | [原报告](../../lastpage-tenc-controlled-probe-20261008.md) |
| E2 | 抱SHFC -400c，55ms进入 | 3:04 ao/B4，vocoder目标F0保持，允许完整新预测 | 条件音高-4st；三个预测同时响应；无满幅/特征裁剪；ao局部双F0检测差约40～45c | “更实了，但是有破音”，明确抱字头 | 有局部实感响应和副作用；不能归因单个预测通道、不能断定真实声区/formant | [原报告](../../lastpage-shfc-controlled-probe-20261008.md) |
| E3 | 抱SHFC入口55→145ms，起点提前到元音前80ms | 同字腹-400c平台/退出精确保留；起点相对旧B前移90ms；时间几何一次干预 | 最快条件变化12644→5082c/s；ao前65ms谱形相邻差RMS .666→.589；b RMS -5.326dB，ao -0.296dB | 用户“可以” | C局部可用；不是字头完全无破音/咬字全通过的标签；时长与提前准备不能分开归因 | [原报告](../../lastpage-shfc-onset-probe-20261008.md) |
| E4 | 果SHFC -200c | 1:27 uo/E4；160ms进入70ms退出、固定原音符/人工控制/增益 | uo RMS+0.0901dB；0～500Hz+1.296、500～2k -1.959、2～5k -4.032、>5k -2.955dB；30ms接口最低-4.200dB | 果没区别；这咬字好像没区别；响度下降 | 该B否决；总RMS不能代替听觉响度；分带/短窗为线索非精确感知真值 | [原报告](../../lastpage-guo-register-probe-20261008.md) |
| E5 | 同字果1:27 vs3:17 | uo/E4，但时值/邻字/上下文不同；元音中央20～80% | 通过侧voicing+1.6140、breathiness-.9680、tension+.3527、目标F0差-.8003c；前60ms差异更大 | 1:27偏假/顶；3:17“中间这个可以” | 条件相关性，不是因果；不能拟合通用阈值 | [原报告](../../lastpage-guo-positive-comparison-20261008.md) |
| E6 | 接受抱C vs原抱A的实际发声特征 | SHFC整路径干预；元音核20～80% | voicing-.9145、breathiness-5.8843、tension+1.0628；vocoder目标F0差0 | C局部可用，原偏假/顶 | 否定普遍“更实必须voicing更高/张力更低”；不证明降低VOIC是修法 | [原报告](../../lastpage-cross-condition-study-20261008.md) |
| E7 | BREC额外-10六条件 | 2问题+4偏实/可用，Q5 80ms进入70ms退出；18套A/Arepeat/B；variance种子11/acoustic种子101（不是步数） | 只breathiness人工增量峰约-1.2；元音RMS[-.0232,+.0273]dB；双F0绝对差p50 .03～.16c，max3.20/2.44c；重复差0 | 全部分开试听“全部没区别” | 六组均不采纳；否定该剂量听觉改善，不能升格整个气声通道无效或其余维度全验收 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |
| E8 | 果g→uo词表/时序只读核查 | 当前g/uo及语言ID4；uo整体token | HFA vs native元音起点+.303ms；元音361.582→347.917ms，差-13.665ms | 1:27问题反馈仍保留 | 无明显大错位/错误词表证据；HFA不是音乐身份/实际生成发音真值 | [原报告](../../lastpage-guo-phoneme-audit-20261008.md) |
| E9 | 1tick→5tick原生控制编码核查 | 本次六条件BREC；原生先5tick再模型帧 | 1tick草稿被独立采样检查拒绝，最大特征差.072；5tick最终精确，原18套波形生成有效 | 没有为编码更正单独声称改善 | 写入曲线≠实际采样；检验原生输入再谈参数作用，不把数值精确当自然 | [原报告](../../lastpage-brec-cohort-probe-20261008.md) |

### 5.1 六组BREC的逐条件数据

额外BREC -10、同函数族；18套新波形。全部A对旧绑定波形与A重复精确，人工/模型输入隔离通过，实际不是只有文件名不同。代理指标小幅响应，用户分开听六组均没区别。这里“无感知差别”不能自动补造“所有副作用均已验收”。

| 条件 | 元音RMS B-A | 30ms最低B-A | 去每帧整体电平后log-mel差RMS | 听觉 |
|---|---:|---:|---:|---|
| 1:27 果，问题 | +0.0181dB | -0.0231dB | 0.062595 | 无区别，不采用 |
| 3:04 抱原A，问题 | +0.0200dB | -0.0140dB | 0.037742 | 无区别，不采用 |
| 3:17 果，可用 | +0.0064dB | -0.0269dB | 0.051873 | 无区别，不采用 |
| 3:04 抱C，可用 | -0.0108dB | -0.0597dB | 0.038619 | 无区别，保留原C |
| 1:33 之，偏实 | +0.0273dB | -0.0481dB | 0.075994 | 无区别，不采用 |
| 2:56 只，偏实 | -0.0232dB | -0.0727dB | 0.035790 | 无区别，不采用 |

log-mel差不是dBFS、formant漂移幅度或自然度分数。F0测量对实际交付PCM运行FCPE/RMVPE，未可比帧不补造真值；最大差3.20/2.44c，目标输入精确不变仍不能宣称实测F0完全不变。[原记录与最新否决反馈](../../lastpage-brec-cohort-probe-20261008.md#最新试听反馈)。

### 5.2 现在可以写入“影响因素知识表”的结论

1. **输出增益与发声方式需要分开。** DYN数学上有明确振幅响应；VOIC/BREC/TENC是模型条件，其电平与谱响应依pitch/音素/声线/上下文。
2. **条件音区能改变同目标音高的发声听感。** 抱SHFC有“更实”反馈，但干预影响多条下游路径，不能归为纯formant移动或气声下降。
3. **控制进入时间是独立于字腹峰值的重要设计变量。** 抱-400c平台保留，55→145ms，起点由元音后10ms移至前80ms（相对旧B提前90ms）获局部可用；同时声母电平/谱变化，未有普适时常。
4. **电平、频谱和时间窗口都影响强弱解释。** 果整段/元音平均近似不变，接口及2～5kHz下降；听觉响度反馈优先，机器均值不能否认它。
5. **已知反例必须保护。** 可用抱C的voicing更低、tension更高；取消TENC与BREC-10均无改善。统一“提高有声/降低张力/降低气声”的修法不成立。
6. **音素正确不等于发音稳定，主观口型不等于已测formant。** 当前g/uo词表/语言匹配、入口近似对齐；仍有问题反馈。共振/声源/transition贡献需要后续独立检验。

这些是当前限条件知识；没有新增通用Skill规则。GENC、VELC、独立VOIC、其它元音/音区、混音效果器和真实粗糙/颤抖分类仍缺本机受控听觉数据。不能以“官方可以调”补造本曲的方向/阈值。

## 6. 整曲怎样用这个表记录，不继续走成单点补丁

每个连续事件保存：`时间区间；word/phone/note身份；原子ID；阶段(准备/入口/核/转换/释放)；强度/速率/持续时间或unknown；音乐目的；上下文；候选控制与作用路径；实际输入SHA；声学响应；用户反馈原话/音频SHA；证据类型；未排除项`。跨字再记录连贯、身份一致、重音、强弱弧线与节奏结构。这些关系是原子在时间中的组合，不另造“自然度旋钮”。同一句可同时气声、颤音、渐弱；不能只选一个类别，也不能只贴“好听/难听”标签。

示例：当前抱B记为`ao/B4、SHFC -400c、条件入口55ms、实感增加、字头破音种类unknown`；抱C记为`同平台、145ms且提前准备80ms、局部可用、细分破音/咬字标签unknown`。果B记为`uo/E4、SHFC -200c、实感无改善、响度下降反馈、短窗/分带负响应`。它们共用同一个P/L/S/R/T/X记录格式，不能为每个字发明新的修复路线。

检测实现和自然度判定仍是独立工作：这份表没有声称新增31个有效检测器，没有把绝对音高、谱、口型、声区等直接阈值化；评价入口继续显式输入/SHA绑定、不把制作expectations作真值。当前唯有原曲观测→Agent自主动作/函数→原生编译/全依赖重算→固定增益/独立核查→听觉验收的制作流程。

## 7. 固定来源、当前资源与可追溯性

### 7.1 源码机制索引

官方源码研究快照提交：`5c3c83bbeced96718e85e4a96d127de3287cd14b`。下载保存于本机ignored研究run；只读查看，没有替换安装程序/模型。下列链接固定提交。wiki为2026-10-09读取的动态文档。上游新增能力单独标识，不把它们视作本机已确认功能。

| ID | 机制 | 解释 | 固定源码 |
|---|---|---|---|
| M1 | 目标音高与相对编码 | 最终目标=原生before-PITD+PITD；before包含note/pitch/vibrato等路径，实际按版本验证。SHFC不是该目标的普通加项。音高同时进入预测与声学，vocoder路径须独立核对。 | [OpenUtau.Core/Render/RenderPhrase.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Render/RenderPhrase.cs) |
| M2 | 音高动作与颤音结构 | 音符点X/Y单位、UVibrato周期/深度/包络/相位/中心偏移定义；新上游还有vol_link与sp。周期、幅度、时机和规则性分开。 | [OpenUtau.Core/Ustx/UNote.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UNote.cs) |
| M3 | DYN输出增益 | 5tick节点转换值×0.1dB到振幅，最低声明值为0；ApplyDynamics逐样本在振幅域插值并相乘。+6dB≈1.9953倍振幅，不等于感知响两倍。 | [OpenUtau.Core/Render/Renderers.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Render/Renderers.cs) |
| M4 | 预测发声+人工增量 | VOIC/BREC/TENC的增量先相加再裁剪。特征单位不是PCM dB或人体量。预测变更可以使相同人工控制得到不同实际输入。 | [OpenUtau.Core/DiffSinger/DiffSingerUtils.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerUtils.cs) |
| M5 | SHFC/GENC不同路径 | SHFC转variance semitones与acoustic条件F0；pitch-controllable vocoder可保留目标F0。GENC由augmentation range映射gender条件，不提供独立F1/F2。 | [OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerRenderer.cs) |
| M6 | 速度与预测pitch表达 | VELC是指数speed条件；PEXP是pitch模型expr，不是当前人工线的后处理强度。 | [OpenUtau.Core/DiffSinger/DiffSingerPitch.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerPitch.cs) |
| M7 | 音素身份/时序/声线 | phonetic hint/override、音素分组与预测时长，CLR按音素索引；clNN帧权重归一/默认回填，duration与帧阶段的speaker路径不同。 | [OpenUtau.Core/DiffSinger/DiffSingerSpeakerEmbedManager.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerSpeakerEmbedManager.cs) |
| M8 | 完整上下文与模型能力 | variance条件含pitch/phones/durations/speaker等，声学输入加发声条件，声码器由mel+F0输出。句内新预测/缓存/随机推理不能混同；本机feed由已核对bridge及封存输入支持。 | [OpenUtau.Core/DiffSinger/DiffSingerVariance.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/DiffSinger/DiffSingerVariance.cs) |
| M9 | 呈现与后处理 | 轨道平衡、EQ、压缩、混响改变最终呈现；新上游UMixFx为可选，null/disabled旁路，当前实验未启用。 | [OpenUtau.Core/Ustx/UMixFx.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UMixFx.cs) |
| M10 | Classic控制 | 采样alias、oto、frq、volume/velocity/flags/envelope；同名表达的算法意义由resampler决定。 | [OpenUtau.Core/Classic/ResamplerItem.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Classic/ResamplerItem.cs) |
| M11 | 不同renderer支持集合 | DiffSinger、Classic、Worldline、ENUNU、Vogen、VOICEVOX控制集合及建议项不同，存在任意扩展。 | [OpenUtau.Core/Render/Renderers.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Render/Renderers.cs) |
| M12 | 人工粗糙效果实现 | 新上游Hifisampler的高频方波调制粗糙效果；区别于声带生理机制和当前DiffSinger能力。 | [OpenUtau.Core/Classic/Hifisampler/HifiGrowl.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Classic/Hifisampler/HifiGrowl.cs) |
| M13 | 参数声明与驱动 | 表达min/max/default/type及track覆盖、MaskedCurve和图驱动定义输入能力；有名称不等于renderer/model读取。 | [OpenUtau.Core/Ustx/UExpression.cs](https://github.com/openutau/OpenUtau/blob/5c3c83bbeced96718e85e4a96d127de3287cd14b/OpenUtau.Core/Ustx/UExpression.cs) |

### 7.2 研究/官方文献

| ID | 原始研究/官方来源 | 使用范围 |
|---|---|---|
| S1 | [声质心理声学模型验证（2021）](https://pubmed.ncbi.nlm.nih.gov/33514179/) | 200份voice token的分析合成研究支持联合描述谐波源、非谐波源、声道滤波、F0与振幅；实验是voice token，不能直接证明整首歌审美完全可判定。 |
| S2 | [分段声源谱斜率模型（2016）](https://pmc.ncbi.nlm.nih.gov/articles/PMC4818273/) | 研究用H1-H2/H2-H4/H4-2k/2k-5k描述源谱；这些不是跨元音直接用原始FFT峰值相减的通用真值。 |
| S3 | [谐波源与噪声的感知交互（2012）](https://pmc.ncbi.nlm.nih.gov/articles/PMC3283904/) | 噪声的感知依赖谐波谱形/相对能量，反之亦然；不能假设BREC/UI变化对应固定可闻气声量。 |
| S4 | [颤音作为颤抖模型的知觉研究（2016）](https://pubmed.ncbi.nlm.nih.gov/27908094/) | 20位听者研究显示声质/元音等改变调制感受，频带振幅调制也与听觉判断相关；不能只用F0摇摆定义所有颤抖。 |
| S5 | [相同音符/元音的实声与假声共振研究（2014）](https://pubmed.ncbi.nlm.nih.gov/24437789/) | 7位男歌手同音高/元音对比中M2接触商通常少.27，R1约低65Hz/R2低90Hz；个体共振策略差异大。人体实验不等于神经歌声发生人体声区转换。 |
| S6 | [粗糙声与次谐波（1997）](https://pubmed.ncbi.nlm.nih.gov/9075175/) | 389份样本中20份有次谐波且均听觉粗糙，8份jitter和/或shimmer正常；粗糙不能只靠jitter/shimmer判。 |
| S7 | [32位歌手极端声效声学/EGG研究（2024发表）](https://pubmed.ncbi.nlm.nih.gov/34972633/) | 多种粗糙声效呈不同频带/噪声指标响应，多数条件F0/接触商未显著改变；有意粗糙不自动等于难听或错误。 |
| S8 | [UNSW研究实验室声学介绍](https://www.phys.unsw.edu.au/jw/voice.html) | 有声源、无声辅音噪声、元音声道滤波、鼻通道及源滤波交互；用于维度解释，不作为本模型生理检测。 |
| S9 | [高F0歌唱中的LPC共振估计限制（2021）](https://pmc.ncbi.nlm.nih.gov/articles/PMC8273971/) | 高F0下LPC可偏向邻近谐波；当前约330～495Hz元音不能从未验证自动F1/F2线宣称舌位漂移。 |
| S10 | [官方DiffSinger支持](https://github.com/openutau/OpenUtau/wiki/DiffSinger-support) | 区分renderer提供表达与voicebank/vocoder支持；通用说明不代替本机特定配置/实际输入。 |
| S11 | [官方Expressions (Flags)](https://github.com/openutau/OpenUtau/wiki/Expressions-%28Flags%29) | 默认表达和采样旗标用途，实际实现/范围仍需固定版本核对。 |

### 7.3 文件与数字的绑定

随附`control-inventory-audit.json`记录本机Core/config/当前发布USTX哈希、固定上游源码逐文件SHA、默认表达名与renderer支持集合及本报告/CSV哈希。原实验9份报告与封存manifest/反馈文件也做只读哈希绑定；数据是以前实际受控或观察结果，没有本次新推理。报告中通用示例的数值注明为公式算术，不能伪装新实验。因日期/版本变化，使用前以实际配置/合法范围/输入再次检查。

当前机制不包括：已验证的F1/F2漂移检测、真实M1/M2识别、破音类型检测、完整自然度自动判断、跨曲泛化阈值。作者三份只读研究原件、最新三曲工程、当前Skill及原封存试验不改；不加载本机历史归档路线。

交付：本报告、原子表现CSV、组合听感CSV、OpenUtau控制CSV、当前证据CSV、结构化知识表JSON、来源/资源审计JSON。CSV为UTF-8 BOM，适合直接用Excel查看。它们是研究文档与知识清单，不是自动改歌器或新曲模板。
