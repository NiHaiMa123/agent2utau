"""Build Stage B reviews with explicit source and measurement gaps.

Authored paraphrases from inspected primary/official sources; no web fetching,
new synthesis, inferred audio labels, baseline edits or control recipes.
"""
import csv
import json
from pathlib import Path
from frozen_inputs import refuse_after_formal_migration
from stage_b_review_data import parse_core, parse_composites

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'

# id|source id|title|author/year|URL|location|support|scope|limitation|legacy dims|read level
DATA = '''
CLAIM:001|SRC:12|Voice 2. Jitter|Paul Boersma / Praat manual|https://praat.org/manual/Voice_2__Jitter.html|Jitter(local)与首段|local jitter比较相邻周期时长，通常在长持续元音测量|周期可定位的持续语音段；官方算法文档|不把帧级F0残差或歌曲任意段落的波动当生理jitter；不移植临床阈值|P5|official_method_checked
CLAIM:002|SRC:13|Voice 3. Shimmer|Paul Boersma / Praat manual|https://praat.org/manual/Voice_3__Shimmer.html|Shimmer(local)与首段|local shimmer比较相邻周期幅度，需周期级振幅信息|长持续元音；官方定义|30/50ms包络AM不是相邻周期幅度扰动；新增ACO:L5候选，检测未实现|L3;L4|official_method_checked
CLAIM:003|SRC:14|PointProcess: Get jitter (local)...|Praat manual，页面2022|https://praat.org/manual/PointProcess__Get_jitter__local____.html|Algorithm及Period floor/ceiling/Maximum period factor|local jitter以相邻有效周期时长绝对差均值除以有效周期均值，且排除不合法间隔/配对|给定PointProcess与筛选设置|未通过周期定位验证就不报告数值；筛选后分子/分母有效集合须按算法实现|P5|official_method_checked
CLAIM:004|SRC:15|Voice 4. Additive noise|Paul Boersma / Praat manual，页面2002|https://praat.org/manual/Voice_4__Additive_noise.html|正文首段|把SNR作为HNR的解释限定在可假设周期性的信号，例如持续元音|周期信号加噪框架|不能把摩擦音、强不规则段或所有CPP代理读作真实漏气比例|S1;S3;S4|official_method_checked
CLAIM:005|SRC:16|Sound: To Formant (burg)...|Praat manual，页面2020|https://praat.org/manual/Sound__To_Formant__burg____.html|Settings/Window length与Algorithm|参数Window length为有效窗长；0.025s设置对应实际0.050s高斯窗，formant ceiling/阶数/预加重影响估计|该具体Praat Burg实现|不能将任意程序25ms窗与此设置视作同窗；LPC结果不是自动真实声道真值|R1;R2;R3|official_method_checked
CLAIM:006|SRC:09|Dark tone quality and vocal tract shaping in soprano song production: Insights from real-time MRI|Elisabeth Lynn, Shrikanth S Narayanan, Adam C Lammert；2021；DOI10.1121/10.0005109|https://pmc.ncbi.nlm.nih.gov/articles/PMC8273971/|§2.2.1|文章明确高F0歌声的LPC共振估计可能偏向邻近谐波|四位专业女高音；研究主要比较整段均值|均值减弱误差的讨论依赖误差分布假设，不能保证本曲短字F1/F2准确；原SRC09标题需在F改为真实论文标题|R1;R2;R3|fulltext_section_checked
CLAIM:007|SRC:09|Dark tone quality and vocal tract shaping in soprano song production: Insights from real-time MRI|Elisabeth Lynn et al.；2021；DOI10.1121/10.0005109|https://pmc.ncbi.nlm.nih.gov/articles/PMC8273971/|§2.1.1与Discussion|相同暗色目标下个体声道变化存在差异，研究未做显式感知验收|四位女高音MRI姿态及歌唱条件|不能从本曲顶/后缩主观标签反推喉位、舌位；更不能推导GENC/SHFC剂量|R1;R3;R4|fulltext_section_checked
CLAIM:008|SRC:01|Validating a psychoacoustic model of voice quality|Jody Kreiman, Yoonjeong Lee, Marc Garellek, Robin Samlan, Bruce R Gerratt；2021；DOI10.1121/10.0003331|https://pubmed.ncbi.nlm.nih.gov/33514179/|Abstract实验1/2|联合模型用谐波/非谐波源、声道传递、F0与振幅重建声质；摘要报告200份voice token实验|声质分析合成研究；本次仅复核摘要，全文遇到访问验证|不证明本项目31或47实体足以覆盖整曲音乐/审美，也不证明相同输入会有相同感知|S1;S2;S3;R1;L1|abstract_checked_fulltext_pending
CLAIM:009|SRC:17|Sound: Get root-mean-square...|Praat manual|https://praat.org/manual/Sound__Get_root-mean-square___.html|Mathematical definition|RMS是指定时间区间平方均值的平方根；Praat声压单位与数字PCM需分清|幅度量定义|未校准PCM不能报Pa或绝对SPL；本项目dBFS的归一化参考要在D另定|L1;L2|official_method_checked
CLAIM:010|SRC:18|Sound: Get intensity (dB)|Praat manual|https://praat.org/manual/Sound__Get_intensity__dB_.html|Algorithm|声压强度dB以20微帕为声压参照，与数字满刻度参照不同|空气声压且输入有物理校准|不能将任意wav的dBFS直接说成dB SPL或感知响度|L1|official_method_checked
CLAIM:011|SRC:02|Modeling the voice source in terms of spectral slopes|Marc Garellek, Robin Samlan, Bruce R Gerratt, Jody Kreiman；2016；DOI10.1121/1.4944474|https://pages.ucsd.edu/~mgarellek/files/Garellek_etal_2016_JASA.pdf|§II.A.1/2|四段源谱参数H1-H2、H2-H4、H4-近2kHz、近2k-近5kHz是谐波幅度差，需明确频点|实验1为144份样本/136人，1秒a元音，20kHz录音|幅度差dB不自动等于dB/oct斜率；分段方案不证明所有维度完全独立|S2;R2|fulltext_methods_checked
CLAIM:012|SRC:02|Modeling the voice source in terms of spectral slopes|Garellek et al.；2016；DOI10.1121/1.4944474|https://pages.ucsd.edu/~mgarellek/files/Garellek_etal_2016_JASA.pdf|§II.A.2与Discussion|先逆滤波选代表周期再重复20脉冲，并用分析合成调整源/滤波，避免直接用未校正输出谱代替源谱|该研究的声源估计和合成流程|不是本项目已实现的算法；高F0、噪声及声道影响仍需单独验证|S2;R1;R2|fulltext_methods_checked
CLAIM:013|SRC:03|Perceptual interaction of the harmonic source and noise in voice|Jody Kreiman, Bruce R Gerratt；2012；DOI10.1121/1.3665997|https://pmc.ncbi.nlm.nih.gov/articles/PMC3283904/|§II.A/II.B与Discussion|噪声和谐波谱的感知敏感度相互影响，不能用单一噪声能量替代听感|实验1：82位听者，两种a合成声F0为126/192Hz，四种谐波斜率和噪声条件|分析合成任务不是Yousa；BREC-10不等于本研究NHR变化，未获区别的原因不能据此确诊|S2;S3;S4|fulltext_methods_results_checked
CLAIM:014|SRC:06|Acoustic characteristics of rough voice: subharmonics|K Omori, H Kojima, R Kakani, D H Slavit, S M Blaugrund；1997；DOI10.1016/s0892-1997(97)80022-7|https://pubmed.ncbi.nlm.nih.gov/9075175/|Abstract|389份病理声样本中20份有次谐波且都被判断粗糙，其中8份jitter和/或shimmer正常|临床样本的声学/感知关联；本次读取主站索引摘要，直开失败|8份不代表两指标均正常；不将20/389作歌声普遍发生率；不是合成模型病理诊断|P5;S5|primary_abstract_search_checked_fulltext_pending
CLAIM:015|SRC:04|The effects of physiological adjustments on the perceptual and acoustical characteristics of vibrato as a model of vocal tremor|Rosemary A Lester-Smith, Brad H Story；2016；DOI10.1121/1.4967454|https://pubmed.ncbi.nlm.nih.gov/27908094/|Abstract|相同调制问题的颤抖感还受声质/元音等条件影响，女声pressed条件被评为更摇晃|20位健康成人听者的配对比较，歌手颤音作为颤抖模型|20是听者而非歌手数；不据此定义病理颤抖或本曲P4好坏阈值；本次仅摘要|P4;L3;S2|abstract_checked_fulltext_pending
CLAIM:016|SRC:05|Vocal tract resonances in singing: variation with laryngeal mechanism for male operatic singers in chest and falsetto registers|Nathalie Henrich Bernardoni, John Smith, Joe Wolfe；2014；DOI10.1121/1.4836255|https://pubmed.ncbi.nlm.nih.gov/24437789/|Abstract|同音高/元音的M2相较M1接触商通常低0.27，R1/R2通常低65/90Hz，个体策略不同|7位男性歌剧歌手；唇端宽带激励测共振，EGG测接触商|0.27不是相对27%；生理测量不能从神经音频/VOIC推得；无统一SHFC方向/剂量|S1;R1;R3|abstract_checked_fulltext_pending
CLAIM:017|SRC:07|Extreme Vocal Effects Distortion, Growl, Grunt, Rattle, and Creaking as Measured by Electroglottography and Acoustics in 32 Healthy Professional Singers|Mathias Aaen, Julian McGlashan, Noor Christoph, Cathrine Sadolin；2021在线/2024卷期；DOI10.1016/j.jvoice.2021.11.010|https://pubmed.ncbi.nlm.nih.gov/34972633/|Abstract|不同极端声效有不同声学响应，多数条件Qx/Fx不显著变化，不能把所有粗糙归为同一机制|32位职业歌手/歌唱教师，持续元音四种模式加或不加效果|不推断本曲健康/病理或生理动作；本机TENC不等于人体声效控制，只有摘要级复核|S2;S3;S5;S6|abstract_checked_fulltext_pending
CLAIM:018|SRC:08|Voice acoustics: an introduction|Joe Wolfe, Maëva Garnier, John Smith；UNSW作者实验室说明，含2009/2020内容|https://www.phys.unsw.edu.au/jw/voice.html|Pitch与source/filter说明|周期基频与听者感知音高是不同对象，缺基频时谐波组织仍可提供音高线索|作者实验室的基础声学解释，不是新的受试实验|不能把一个F0估计当全部音高感；复音多F0及音乐目标判断另需协议|P1;P2;P3|author_lab_explanation_checked
CLAIM:019|SRC:08|Voice acoustics: an introduction|Wolfe, Garnier, Smith；UNSW作者实验室说明|https://www.phys.unsw.edu.au/jw/voice.html|Speech sounds与Nasalisation|元音滤波、辅音噪声/事件和口鼻耦合需区别；口鼻通道可带来共振及反共振|基础源/滤波及发音机制解释|不提供中文词表时长阈值、鼻化检测器或本模型生理标签|S4;R4;T3;T4;T5;T6;T7|author_lab_explanation_checked
CLAIM:020|SRC:22|Formant: what is a formant?|Joe Wolfe / UNSW作者实验室|https://www.phys.unsw.edu.au/jw/formant.html|正文三种用法与harmonics示例|输出谱包络峰、声道共振与模型极点常同称formant，频率并非总重合|术语和声学对象的作者说明|应报告实际估计的对象；LPC峰线不能证明口腔姿态，更不能统一估计所有高F0元音|R1;R2;R3;R4|author_lab_explanation_checked
CLAIM:021|SRC:21|Voice 1. Voice breaks|Praat manual|https://praat.org/manual/Voice_1__Voice_breaks.html|Number/Degree of voice breaks|官方voice breaks基于超过1.25/pitch floor的周期间隔；unvoiced比例另依阈值|特定Praat测量定义与参数|无周期辅音/停顿及定位失败不能自动归异常；不搬临床阈值至整曲|S6|official_method_checked
CLAIM:022|SRC:19|ISO 532-2:2017 Acoustics — Methods for calculating loudness — Part 2: Moore-Glasberg method|ISO；2017|https://www.iso.org/obp/ui?_escaped_fragment_=iso%3Astd%3Aiso%3A532%3A-2%3Aed-1%3Av1%3Aen|公开Scope与§3.15–3.18|响度是知觉量，声压、频谱/带宽和时长等条件影响它；phon与sone不同|本部分针对平稳声音、规定听觉/聆听条件|只读公开范围/定义，未读取付费算法；未校准wav不能直接当绝对sone真值|L1|official_scope_definitions_checked_algorithm_pending
CLAIM:023|SRC:20|ISO 532-3:2023 Acoustics — Methods for calculating loudness — Part 3: Moore-Glasberg-Schlittenlacher method|ISO；2023|https://www.iso.org/standard/69856.html|公开Abstract|此方法覆盖平稳与时变声音，但给超过5秒时变声一个总体响度值在其范围外|官方公开方法适用范围|只读摘要而非完整算法；这不是说所有节目整曲响度方法均无效|L1;L2|official_scope_only_algorithm_pending
CLAIM:024|SRC:23|Characterization of Source-Filter Interactions in Vocal Vibrato Using A Neck-Surface Vibration Sensor: A Pilot Study|Rosemary A Lester-Smith, Elaina Derrick, Charles R Larson；2021在线/2024卷期；DOI10.1016/j.jvoice.2021.08.004|https://pmc.ncbi.nlm.nih.gov/articles/PMC8995401/|Abstract/Introduction与Discussion|F0调制中的谐波与共振关系可改变输出AM，不能只从DYN解释全部包络|9位古典歌手的颤音源/滤波研究|物理/人体研究为机制候选，不证明当前神经声码器AM的唯一病因|P4;L3;S2;R1|fulltext_methods_results_checked
CLAIM:025|SRC:23|Characterization of Source-Filter Interactions in Vocal Vibrato Using A Neck-Surface Vibration Sensor: A Pilot Study|Lester-Smith, Derrick, Larson；DOI10.1016/j.jvoice.2021.08.004|https://pmc.ncbi.nlm.nih.gov/articles/PMC8995401/|Methods/Results|119有效试次中F0调制平均约4.8Hz；AM速率约6.4Hz颈表/8.4Hz麦克风，两种观测不相同|9人、5元音、3次5秒，共135试次；12削波/4外来声被排除|平均不是普遍理想速率；该文幅度深度(max-min)/(max+min)不能混成其它百分比定义|P4;L2;L3|fulltext_methods_results_checked
CLAIM:026|SRC:24|Some Effects of Context On Voice Onset Time in English Stops|Leigh Lisker, Arthur S Abramson；1967；DOI10.1177/002383096701000101|https://journals.sagepub.com/doi/10.1177/002383096701000101|出版社Abstract|VOT描述塞音释放到准周期起声的间隔，重音/语境影响它|英语塞音的原始语音实验；仅摘要读取|不能扩为所有音素/中文普遍理想时长；VEL的值不是VOT|T1;T2;T3;T4;T5|publisher_abstract_checked_fulltext_pending
CLAIM:027|SRC:25|Masking Effects in the Perception of Multiple Simultaneous Talkers in Normal-Hearing and Cochlear Implant Listeners|Biao Chen et al.；2020；DOI10.1177/2331216520916106|https://pmc.ncbi.nlm.nih.gov/articles/PMC7180303/|Abstract/Introduction|目标辨认依竞争声包络空隙和声线差异等条件，不能仅用总电平解释可懂度|10位正常听力/12位人工耳蜗成人，多说话者普通话任务|语音竞争不是乐器伴奏；不提供当前歌唱遮蔽阈值或ASR真值|X3;T3|fulltext_abstract_intro_checked
CLAIM:028|SRC:26|ISO 3382-1:2009 Acoustics — Measurement of room acoustic parameters — Part 1: Performance spaces|ISO；2009|https://www.iso.org/standard/40979.html|公开Abstract|表演空间的混响/相关房间参数有规定测量方法，包括数字脉冲响应技术|房间声学测量适用范围|本次未读取详细算法；未知歌曲混音的盲RT估计、远近/宽度听觉不能据此标已验证|X4|official_scope_only_algorithm_pending
CLAIM:029|SRC:27|ITU-R BS.1770-5 Algorithms to measure audio programme loudness and true-peak audio level|ITU-R；2023-11|https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf|Annex 1及recommendations Note 1|节目响度方法含K加权/通道均方/加权求和；400ms块75%重叠，-70LKFS及相对-10dB两道门限|该标准的节目响度估计，不是局部元音听感直接真值|受听者、材料/聆听条件影响；未校准当前实现，也未将LKFS当phon/sone|L1;X3|official_algorithm_sections_checked
CLAIM:030|SRC:27|ITU-R BS.1770-5 Algorithms to measure audio programme loudness and true-peak audio level|ITU-R；2023-11|https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf|Annex 2 §1/3|true peak为连续重建波形峰值，可能超过最大采样值；标准示例48kHz采用4倍过采样及低通|线性PCM的峰值测量指导|不把任意4倍插值都当合规；未满幅样本不排除间采样峰或前级失真，更非破音病因证明|X1;L4;X2;X5|official_algorithm_sections_checked
'''

def main():
    refuse_after_formal_migration()
    claims = []
    keys = ['id', 'source_id', 'source_title', 'authors_year', 'url', 'locator',
            'supported_claim', 'study_scope', 'limitations', 'legacy_dimensions', 'read_status']
    for line in DATA.strip().splitlines():
        r = dict(zip(keys, line.split('|'), strict=True))
        role = 'primary_research_or_official_method'
        if r['read_status'].startswith('author_lab'):
            role = 'primary_author_lab_explanation_not_original_experiment'
        r.update({'evidence_role': role,
                  'current_engine_effect': 'not_established_by_this_source',
                  'measurement_validated_here': False, 'checked_date': '2026-10-09'})
        claims.append(r)
    assert len({r['id'] for r in claims}) == len(claims)
    def write_pair(stem, rows, metadata):
        with (OUT / (stem + '.csv')).open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows({k: ';'.join(v) if isinstance(v, list) else v for k,v in r.items()} for r in rows)
        (OUT / (stem + '.json')).write_text(json.dumps(dict(metadata, rows=rows),
            ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    with (OUT / 'composite-descriptors.csv').open(encoding='utf-8-sig', newline='') as f:
        original = list(csv.DictReader(f))
    core = parse_core()
    composites = parse_composites(original)
    assert len(core) == 31 and len(composites) == len(original) == 30
    valid = {r['id'] for r in claims}
    assert all(set(r['claim_refs']) <= valid for r in core + composites)
    common = dict(schema_version=1, stage='B', status='reviewed_with_explicit_gaps',
                  no_new_synthesis=True, scientific_completeness_validated=False)
    write_pair('core-definition-review', core, common)
    write_pair('composite-review', composites, common)
    # Keep the existing claims key for downstream readers; pairs share the
    # same row serialization but this ledger has an established field name.
    write_pair('claim-evidence', claims, common)
    (OUT / 'claim-evidence.json').write_text(json.dumps({
        **common,
        'claims': claims, 'all_core_definitions_checked': False,
        'all_core_definitions_reviewed': True, 'all_composite_descriptors_reviewed': True,
        'all_composite_descriptors_checked': False,
        'core_rows': 31, 'composite_groups': 30,
        'open_items': ['摘要级论文全文、完整ISO算法未读取的缺口保留',
                       '中文音素/非塞音入口、哭笑情绪、空间知觉、数字量化/混叠及伪影类型资料待补',
                       '动态趋势、连续性等工程操作定义仍需D/E检验',
                       'shimmer/感知音高/复音拍频候选需D/E决定去向，F正式迁移',
                       '具体控制C、观测D、独立覆盖E及正式修订F']},
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 表1文献和听感词核对：阶段B', '',
             f'日期：2026-10-09。31行核心定义及30组听感词已逐项审查；累计核对{len(claims)}条说法/{len({r["url"] for r in claims})}个来源页面。状态为reviewed_with_explicit_gaps，不是全部事实、测量或听觉确认通过。源码控制路径在C，观测验证在D，独立覆盖在E。', '',
             '资料只用原始研究、官方方法/范围文档及作者实验室解释，证据角色逐条记录。部分全文访问验证或付费，保留摘要/公开范围级别；不绕过访问限制。Praat shimmer仅复核Voice 3定义，未声称全部细节实现已核查。', '',
             '| 说法ID | 已核对说法 | 来源与位置 | 不能推出什么 |', '|---|---|---|---|']
    for r in claims:
        lines.append(f"| {r['id']} | {r['supported_claim']} | [{r['source_title']}]({r['url']})，{r['locator']}；{r['read_status']} | {r['limitations']} |")
    lines += ['', '## 已发现需修订的地方', '',
              '1. 周期级振幅扰动shimmer不应由原L3慢包络AM代替。新增ACO:L5候选供B/D确认；它尚未写入原表或A阶段47实体清单，阶段差异显式保留。',
              '2. 原SRC09用了用途概括作标题，真实论文标题应在F替换。原链接所述LPC限制存在于§2.2.1，但其研究目标与样本应写清，不把它当专门验证本项目检测器的论文。',
              '3. formant分析的“25ms窗”需要区分有效窗与实际支持；后续D协议必须写算法和完整参数，不能只报一个窗长。',
              '4. 电平、SPL、节目响度、特定响度模型与用户强弱标签独立记录。已补定义及适用范围，但没有执行响度模型或获得当前听觉真值。',
              '5. 原研究数字区分分母/单位：20位是颤抖研究听者；粗糙研究8份是jitter和/或shimmer正常；接触商差0.27是绝对差；32位声效论文区分在线2021与卷期2024。源谱研究144样本/136人与声源逆滤波路径明确。',
              '6. 输出谱峰、声道共振与模型极点分栏；声门源谱和输出谱分栏。跨元音/音区原始FFT变化不能单独证明口型或真实声区。', '',
              '## 31行定义审查', '',
              '完整字段见[CSV](core-definition-review.csv)与[JSON](core-definition-review.json)。工程定义已有明确审查结论，但仍需操作协议，不能把挂上文献等同于方法已验证。', '',
              '| 旧维度 | 工作定义 | 证据状态 | 具体缺口 |', '|---|---|---|---|']
    for r in core:
        lines.append(f"| {r['legacy_id']} | {r['working_definition']} | {r['source_review_status']}；{';'.join(r['claim_refs'])} | {r['remaining_gap']} |")
    lines += ['', '## 30组组合听感逐项审查', '',
              '下面多义分解、近义区别及反例均为Codex显式工程提案。来源只支持相关组件区别，**不验证中文词之间等价或其唯一病因**。反例是思考例，不是新音频/用户标签，也不是E的独立覆盖测试。', '',
              '可比较结构化[CSV](composite-review.csv)与[JSON](composite-review.json)：还含两条候选路径、所需观测、说法引用与未验证状态。', '',
              '| ID／原词组 | 近义／歧义区别 | 候选路径A；B | 假设反例 |', '|---|---|---|---|']
    for r in composites:
        lines.append(f"| {r['id']} {r['descriptor']} | {r['ambiguity']} | {r['candidate_path_A']}；{r['candidate_path_B']} | {r['counterexample']} |")
    lines += ['', '## 待确认的遗漏与范围', '',
              '- 周期幅度扰动shimmer：候选ACO:L5；保留在B差异中，未修改A的47实体或原清单。D先明确循环定位适用域。',
              '- 感知音高：候选PER:P1，不用物理F0代替。复音/拍频需区分同源次谐波、多个独立F0、AM及感知融合；是否新增实体待D/E，不把所有拍频塞入P4。',
              '- 哭笑/情绪、身份与审美：保留独立标签/上下文，不伪造声学标量或唯一调参配方。专门知觉资料仍缺。',
              '- 房间测量、通道关系、远近/宽度听感，以及数字编码/混叠/金属伪影的详细方法仍有缺口；已读标准范围不能代替算法验证。',
              '- 工程定义的趋势、连接、连续性与阶段时钟需D落实协议，E检查它们有无吞掉独立现象。', '',
              '原SRC01–09研究/实验室来源均已在上表核对到明确读取级别；SRC10/SRC11是OpenUtau支持/Expressions文档，软件机制核查留在C，不用它们证明声学或听感。原来源标题/元数据正式更正留在F，原知识表字节保留。', '',
              '本阶段逐项审查已完成并携带以上缺口继续[阶段C](../../../plan.md)：展开具体控制字段及本机/上游支持。C不依赖这些词已有唯一病因；资料缺口留在后续确认清单，不升级状态。原六份清单/第二层、Skill、工程和历史证据不改。', '',
              '逐说法记录见[CSV](claim-evidence.csv)和[JSON](claim-evidence.json)，文件/保护绑定见[执行审计](table1-execution-audit.json)。', '']
    (OUT / 'table1-source-review.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'stage': 'B', 'claims': len(claims),
                      'distinct_pages': len({r['url'] for r in claims}),
                      'core_rows': len(core), 'composite_groups': len(composites),
                      'status': 'reviewed_with_explicit_gaps'}))

if __name__ == '__main__':
    main()
