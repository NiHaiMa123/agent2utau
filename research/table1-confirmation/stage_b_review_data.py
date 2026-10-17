"""Authored definition and descriptor reviews; hypotheses, not audio labels.

Source claims support component distinctions. None establishes these Chinese
descriptor decompositions as a validated taxonomy or an engine control recipe.
"""

# old dimension | working definition | boundary | claim IDs (without prefix)
# | evidence status | remaining gap
CORE = '''
P1|周期信号的基频及相对音乐目标的差；另存感知音高|无周期不补F0；感知音高不等于物理基频|018|partial_component_support|估计器质量掩码、音乐目标身份及PER:P1需D/E确认
P2|在明确时间尺度分离的F0中心走势|趋势与颤音分离依滤波/模型选择，不是天然唯一分解|018|engineering_definition_proposal|截止频率、边界与未知段方法待D
P3|两个有身份音乐目标之间的F0连接及到达时序|转音、换音、八度误检与音符基底跳变分开|018|engineering_definition_proposal|音乐身份与允许连接范围需人工上下文；D/E待验
P4|可定位周期/准周期的F0调制，记录速率、深度、相位和包络|快慢调制不是好坏；F0颤音不包办AM及谱形颤动|015;025|research_scope_checked|速率/深度算法、非平稳周期及跨通道时序待D
P5|扣除声明中心/调制模型后的帧级F0残差；周期jitter独立记录|残差不是jitter；octave error不是生理不规则|001;003|partial_component_support|循环定位及残差分解两套协议待D
L1|数字电平、校准声压级、响度模型输出与主观强弱分别记录|RMS/dBFS、dB SPL、LKFS、phon/sone不可互换|009;010;022;023;029|source_distinctions_checked|回放校准、局部窗口和本机实现合规待D
L2|明确频带/窗/参考的幅度或电平包络随时间变化|元音发声包络不等于混音总包络；渐强意图另记|009;025|partial_component_support|归一、窗长、相位延迟及乐句事件定义待D
L3|包络的周期/准周期调制；记录频率、幅度及跨F0关系|AM不等于周期shimmer；FM经源滤波也可能出现AM|002;025|source_distinctions_checked|AM去趋势/倍频、shimmer周期方法待D；ACO:L5为新增候选
L4|局部短时幅度/频带能量突变及发生阶段|自然爆破、瞬态噪声、增益跳变、削波均可能，但原因另判|009;026;030|partial_component_support|瞬态窗、变化阈值及候选原因排除待D/E
S1|周期成分/噪声的可定义声学指标；支撑感另存感知|模型VOIC、HNR、接触商和实感不同|004;008;016|source_distinctions_checked|HNR/CPP算法和有效域待D；支撑感不能给单阈值
S2|声明取样/校正条件的谐波幅度或分段声源谱形|原始输出谱受声道/噪声影响，不直接等于声门源谱|011;012|source_distinctions_checked|逆滤波可靠性、高F0与跨元音校正待D
S3|明确分离模型下周期与非周期成分的相对量|神经breathiness feature不是输出NHR；辅音噪声不算元音漏气真值|004;013|source_distinctions_checked|噪声提取与有效段验证待D
S4|非周期部分的频谱与时间结构，保留来源未明|气声、摩擦音和分离残留不能只靠高频能量区分|013;019|partial_component_support|非周期分解、频带和类型归属待D/E
S5|与主周期关系明确的次谐波/多周期组织|多个歌手或伴奏的独立F0不是同源次谐波；粗糙感另存|014;017|research_scope_checked|检测器、复音排除及subharmonic比例协议待D
S6|声学周期支撑中断/再起事件；破音词另存候选|清辅音/停顿、检测失败和主动不规则不自动异常|021;017|source_distinctions_checked|官方voice breaks测量不等于本曲有效检测器
R1|分别记录实际声道共振、输出谱包络峰和模型极点的频率|三种对象可能偏离；不能用LPC直接证实舌根/喉位|005;006;020|source_distinctions_checked|高F0可识别性、峰/极点跟踪及无生理真值限制待D
R2|共振/模型极点带宽与谱谷/反共振分别记录|峰宽不等于谷深；原始谱变化也可能来自声源|005;011;020|partial_component_support|带宽与零点估计独立定义，鼻通道证据待D
R3|同身份元音/过渡阶段内的谱包络、峰或极点时间连续性|自然双元音/协同发音不等于漂移；峰跳也可能估计失败|006;007;020|engineering_relation_with_source_limits|对象追踪、匹配及同声线条件待D/E；无自动异常阈值
R4|鼻化候选谱结构与鼻/堵感知分栏|口鼻耦合可有共振及反共振；单个鼻峰不唯一诊断|019;020|partial_component_support|鼻声知觉与生理推断需独立证据；本模型暂无验证
T1|声学事件相对于显式音乐/词/音素参考的时差|ASR/HFA/谱面不是彼此真值；发声起点与note onset不同|026|engineering_clock_definition|参考身份、offset、时钟转换与误差需D/C
T2|明确边界之间的音符/音素/元音核持续时间|音符长不保证元音核长；模型时长不等于实际声学边界|026|engineering_clock_definition|边界检测及延音/跨note计数待D
T3|声母爆破/摩擦/有声段及对比线索；咬字清晰度另存|辅音能量大不一定更清楚；声学时序不等于识字率|019;026;027|partial_component_support|中文音素条件与感知识别任务待D/E
T4|声母释放、周期声/噪声与元音包络建立的先后及间隔|VOT适用塞音的特定事件；不能统称所有起声协调|026;019|source_distinctions_checked|中文声母与非塞音入口协议待D；无通用理想ms
T5|相邻音素声学特征的过渡时间及连续/重叠关系|断连感可来自音高、周期、包络或剪辑；不是只看音素边界|019;020;026|engineering_relation_with_source_limits|自然协同发音与异常漂移的对照待D/E
T6|持续发声结束/再起及包络释放；词尾音素独立|自然收声、辅音尾与拼接突然截断不同|019;009|engineering_relation_with_source_limits|释放事件时刻及尾音身份待D/E
T7|非唱呼吸噪声与静音/低能量间隔分别记录|AP/SP工程符号不证明真实呼吸；无波形也不证明无准备动作|019|engineering_event_definition|呼吸来源/边界与休止定义待D/E
X1|数字样本过载/非线性与其他失真分栏，查sample peak及true peak|没有满幅样本不排除间采样峰、前级失真或字头破音感|030|partial_component_support|true-peak实现/滤波验证及非线性归因待D/C
X2|波形边界不连续、重复结构、谱异常等现象分开记录|听感电子/金属感不自动证明缓存、拼接或模型故障|008;030|engineering_artifact_candidates|伪影类型定义/来源归因与重现证据待D/E
X3|声部电平比例与目标识别受遮蔽的感知结果分栏|同RMS不等于同可懂度；多说话者实验不直接给伴奏阈值|027;029|partial_component_support|当前歌曲混音的频带/时间/听者协议待D/E
X4|通道相位/相关、混响响应与远近/宽度感知分栏|单声道电平不够解释空间；房间RT方法不自动适用未知合成混音|028;029|scope_only_partial|已知IR与盲估计分开，空间听觉/算法资料仍缺
X5|采样率、位深、编码/带限是格式/处理上下文；声学后果另记|格式标签不是听感好坏维度；缺频也可能来自源/滤波|030;011|engineering_metadata_definition|量化/混叠/编解码方法资料仍缺；需C/D核对
'''

# row | near terms / ambiguity | candidate A | candidate B | hypothetical
# counterexample | observations needed | claim IDs (component support only)
COMPOSITES = '''
1|撕裂与嘶吼不完全同义；强度和粗糙形态分开|S5多周期/次谐波与S3噪声组合|S6中断或X1失真伴L4突变|大声清亮可无粗糙；有意粗糙也可低电平|周期组织、噪声、峰/过载、阶段及意图标签|014;017;030
2|沙哑、颗粒、毛糙的尺度及噪声/脉冲感可能不同|S3/S4非周期噪声|S5次谐波或P5周期扰动，另排X2|jitter/shimmer正常仍可粗糙；摩擦辅音不等于元音沙哑|持续元音、周期可靠性、次谐波、阶段试听|001;002;014;019
3|破音/炸一下是事件标签，不能预判类型|S6失声/再起或P1/P3骤变|L4瞬态、X1过载或X2边界伪影|元音后自然爆破可能有突峰但不破音；无削波也未排除破音|字头/腹/尾、F0有效域、波形、true peak、用户标签|021;026;030
4|颤抖、摇晃、颤音分开意图与可闻维度|P4/P5频率调制|L3或R3/S2谱形调制及相互作用|F0相同调制也可能有不同摇晃感；规律颤音可为所需|F0/AM/分带调制率深度、相位与听者判断|015;025
5|饱满、厚实、有芯分别可能指低频量感/集中/稳态|S1/S2周期与谐波组织，R1/R2谱包络|L1/L2或X3/X4呈现变化|提高整体增益未必更实；低音多也未必有芯|同增益人声、分带/谱、同元音条件与独立标签|008;011;016;022
6|薄、虚、空、飘不强制互为同义|S2/S3谱及噪声比例候选|L2主体短缺或X3掩蔽/X4空间|轻薄可有意而稳定；气声不必空或小声|主体/入口/尾部分开、谱/包络、纯声与混音试听|013;022;027
7|假音感、头声感是听感/唱法词，不直接标M2|S1/S2/S3联合声质变化|R1/R3谱包络与音区/上下文变化|高音或气声单独都不证明假声；同F0可有声质差|同pitch/元音对照、周期/谱、标签；生理机制unknown|016;008;020
8|实声感、胸声感不是接触商或VOIC名称的别名|S1/S2周期谐波组织|R1/R2与L2主体/X3突出感|增大VOIC数值不保证胸声感；更响不必胸声|实际输入、同增益输出谱/包络及局部用户反馈|008;016;022
9|混声是唱法解释；顺畅是关系判断|P3/T5平滑目标与时序|S1/S2/R3/L2在过渡中保持或有意改变|F0连续仍可换声色；声色变化也可有意顺畅|过渡两侧身份、F0/谱/包络连续性、音乐意图|016;019;020
10|挤、紧、顶、喊可指声质/用力感/音区或响度|S2/R1/R3谱形及P1音区组合|L1/L4强弱或T4入口带来的感受|响不等于挤；同音高局部顶感不能证明舌根后缩|元音、音区、谱与入口阶段、原话；人体解释unknown|007;011;015;022
11|气声与耳语不同，漏气是生理措辞需保留假设|S3/S4元音非周期量及频谱|S1周期下降/消失与T4噪声先行|清辅音高频噪声不是漏气；BREC减小未必可闻|持续元音、噪声/谐波、源滤波条件与同增益标签|004;013;019
12|明亮、尖、刺的喜好/刺激感不同|S2/R1/R2高频与包络变化|L1强度、X3遮蔽或X1瞬态失真|谱重心高的低音量声不必刺；明亮可柔和|频带、增益/回放、瞬态与分开听感标签|011;020;022;030
13|暗、柔、闷、蒙含音色与清晰度不同轴|S2/R1/R2谱形变化|T3线索受损或X3掩蔽/X4混响|暗可清楚；柔可明亮；低通不是唯一暗色原因|同元音谱、辅音/混音对照及分词标签|007;011;027
14|鼻色与鼻堵感分开；堵还可能是闷或挤|R4口鼻耦合候选峰/谷结构|R1/R2/S2普通谱色变化或T3线索弱|某频带突出不唯一证明鼻化；鼻音辅音可完全正常|音素身份、谱峰谷、元音对照；生理原因unknown|019;020
15|口型不稳/舌根后缩是知觉比喻与原因假设分开|R3同元音谱包络/峰变化|S2/S3发声变化或T5过渡/估计失败|高F0的LPC跳峰可能无真实口型变化；双元音本有运动|同元音/声线/音区、输出谱、边界及用户时间点|006;007;020
16|像换了人是身份连续性标签，不能直接认speaker改动|S2/R1/R3跨字谱及音区变化|X4空间或T5切换/模型speaker条件候选|speaker字段相同也可能色变；字段改变未必可闻换人|两阶段输入及上下文、同增益谱、听者身份判断|008;016;020
17|硬起与爆字头可能是有意发音/重音或异常突峰|T4有声/噪声/辅音事件关系|L4突峰、X1过载/X2拼接|爆破辅音强不必硬声门起音；硬起不必过载|释放/周期起点、包络、峰值、相位及词身份|026;030
18|软起、气起、虚起不是同一个时间参数|L2缓起与T4起点组织|S3/S4噪声领先或S1弱周期|包络缓起也能实；气声入口可很短很明确|周期/噪声入口、元音起点、包络和听感|013;019;026
19|含糊、吞字、咬字弱可能是不同识别失误|T3/T2声母或元音线索/核不足|X3掩蔽或T5过渡影响可懂度|辅音能量更多不保证识别更准；原生音素正确也不保证清晰|词身份、实际边界、线索、纯声/混音及识别任务|019;026;027
20|连贯、粘、断、磕绊区分有意连断与异常|T5/T1间隔、重叠及边界事件|P3/R3/L2连续性或X2拼接|句末有意断开不等于磕绊；过分连可糊词|跨字时钟、F0/包络/谱与乐句目的|019;026;020
21|滑、拐、跳跃是动作；太高是相对目标判断|P3/P1音乐身份及连接路径|T1/T2过快到达或声质过渡引起跳感|大音程可以自然；浅滑音也可能拖错拍|原曲身份/unknown、目标F0、到达时刻及上下文|018;026
22|直、平是形状，机械/僵硬是音乐判断|P2/P4较少变化与L2稳定|T1/T5阶段重复或S2/R3过度一致候选|稳定直音可符合音乐目的；加入颤音不保证自然|阶段/乐句与重复动作、声学变化和意图评价|015;008
23|稳、松弛、自然属于不同条件的评价词|P1/T1符合目标且S/R连续候选|有意变化的P4/L2/T5也可获自然感|低残差不保证自然；有意粗糙/抖动也可能合适|目标、来源unknown、听者判断与多维描述；不能单阈值|008;015;017
24|无力、漏底、支撑不住不直接等于气声多|L2元音主体包络不足候选|S1/S2/R3变化或X3掩蔽|降低气声未必更有力；弱声可以完整稳定|入口/核/尾能量、谱、承载时长及上下文标签|013;022;027
25|渐强、蓄力、爆发、回收区分强弱轨迹与意图|L2/L4振幅阶段组织|S2/S3/P2/R3联合变化候选|电平不变也可有推进感；增益上升未必蓄力|包络/分带、阶段时序、乐句目的与听觉结果|009;025;022
26|抢、赶、拖是相对节奏/歌词身份；松紧可含感觉|T1音乐/词边界时差及T2核分配|P3到达或T4/T5线索建立造成时间感|所有note落拍也可能字腹太快；提前音节可为有意切分|音乐目标、元音事件与源观察，不拿HFA作裁判|026;019
27|哭腔、哽咽、泣音的具体声学指向待标签|P3/P4/S6断续或调制候选|S3/T4/R3声质/入口变化候选|下滑或断声单独不保证哭感；哭感不必破音|原话、音频身份、情境与阶段；专门知觉资料仍缺|015;019
28|笑、甜、冷、温暖、情绪足分别存标签|R1/S2/T3音色/发音候选|P2/P4/L2/T1表达组织候选|亮声不必甜；暗声不必温暖；同声学可因歌词变感受|情境/词义、回放、听者及独立情绪研究缺口|008;022
29|近、贴耳、远、空灵区分空间与声质|X4直达/反射、通道关系候选|S3/R1/L1气声/谱/呈现强度候选|纯干声也可空灵；加混响不保证远或好听|干/湿身份、IR/通道、回放与空间知觉标签|028;022
30|好听、难听、像原唱是审美/身份/目标不同任务|多维声学与音乐组织的描述|听者、原唱、歌词和风格情境评价|技术完全跟随也未必好听；偏离原唱可有意且好听|明确比较目标、听者及标签，不能用总体分数补缺|008;022
'''


def parse_core():
    keys = ['legacy_id', 'working_definition', 'boundary', 'claim_refs',
            'source_review_status', 'remaining_gap']
    rows = []
    for line in CORE.strip().splitlines():
        r = dict(zip(keys, line.split('|'), strict=True))
        r['claim_refs'] = ['CLAIM:' + n.zfill(3) for n in r['claim_refs'].split(';')]
        r.update(definition_reviewed=True, measurement_validated=False,
                 current_engine_effect='not_established',
                 status='reviewed_with_explicit_gaps')
        rows.append(r)
    return rows


def parse_composites(original):
    keys = ['legacy_row', 'ambiguity', 'candidate_path_A', 'candidate_path_B',
            'counterexample', 'needed_observations', 'claim_refs']
    rows = []
    for line in COMPOSITES.strip().splitlines():
        r = dict(zip(keys, line.split('|'), strict=True))
        row = int(r['legacy_row'])
        r['legacy_row'] = row
        r['id'] = f'DESC:{row:02}'
        r['descriptor'] = original[row - 1]['descriptor']
        r['claim_refs'] = ['CLAIM:' + n.zfill(3) for n in r['claim_refs'].split(';')]
        r.update(mapping_role='authored_hypothesis_component_sources_only',
                 counterexample_role='hypothetical_not_new_audio_or_coverage_test',
                 synonym_equivalence_validated=False, measurement_validated=False,
                 auditory_label_status='no_new_labels', status='reviewed_with_explicit_gaps')
        rows.append(r)
    return rows
