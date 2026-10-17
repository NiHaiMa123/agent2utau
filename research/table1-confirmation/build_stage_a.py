"""Build the authored Stage A structural review; no audio or production inputs.

Run from the repository root. Original inventories must match the plan baseline.
This is a research document builder, not a singing or classification pipeline.
"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from frozen_inputs import refuse_after_formal_migration

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
BASELINE = {
    'atomic-manifestations.csv': '6a243754bc4d7f1c0aeca0a87486dc86b7cd88cbd5ea518c52f35b38f9c3d9d4',
    'composite-descriptors.csv': '202c7c56d3c50013906305b3c9b448dfbda42bd38ed15ea1d5707ffc09d01fc9',
    'openutau-controls.csv': '63cdc16fa0e2bd55719a48e58ed292bd2e6b16761055eb376f95e4ddf57e03e3',
    'knowledge-table.json': 'c998b5ea4b39648a5703c5818455140d7dc932cbb40095199b5a7ca9739d0962',
    'conditional-responses.csv': '9ef9970a072490c7df4517a0a1355fae668c957361b98a753692ce5cde9abd69',
    'conditional-responses.json': '950a7c5f4f04506991988d7033b2a0105d48ee6ddc1055b86f3eef9847117821',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_csv(name):
    with (OUT / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def write_csv(name, data):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)

# Explicit decisions made for each original row. These are structural proposals,
# not literature findings, measured diagnoses, or automatically inferred classes.
# legacy|action|problem|targets|scope/definition|exclude|units/clock|related|unknown|next verification
DECISIONS = '''
P1|保留并限定对象|目标、工程输入与实测F0混在同一解释里|ACO:P1|输出可靠有声段的F0；相对明确音乐参照另记cents偏差；工程目标单独放控制实体|无声段不存在可用F0；音符基底不是输出F0|Hz、cents；输出秒轴及参考秒轴|P2/P3/P4/P5均为其时序描述|无声、检测冲突、音乐参考未定分别标unknown，禁止填0c|B核对F0定义；D冻结置信掩码与参照定义
P2|转为轨迹属性|慢趋势未规定分离尺度，可能与颤音相互吞并|EVT:P2|在声明时间窗与分解算法下描述F0中心的非周期走势；起止值、斜率和曲率为属性|不把残余周期或音符跳变自动归为漂移|cents、cents/s、秒；元音或乐句范围|依赖ACO:P1；与P4/P5分解必须同协议|无分解尺度或有效帧不足不判平直/推进|B核对趋势与调制区别；D评估分解可辨识性
P3|转为换音事件|音程、装饰目的、到达时刻与F0形状不是单一标量|EVT:P3|记录两个音乐锚点间F0轨迹及到达/过冲时刻，链接原音乐身份与元音边界|连贯/生硬是听感；滑音/倚音的音乐身份不能仅由斜率决定|cents、秒、cents/s；锚点/元音/节拍关联|P1/P2与T1/T2/T5|锚点、允许到达区或源动作不确定，保留候选而非统一斜率阈值|B查音乐/声学边界；E检查大跳、装饰与同音连字
P4|保留调制对象|周期深度、速率、相位属于一条调制过程而非四个独立表现|ACO:P4|在F0基底上记录准周期调制的频率、幅度、相位、包络与稳定程度|不以周期存在判自然；不把工程内置参数当PCM测量|Hz、cents峰幅/峰峰必须注明、rad或周期%、秒|P2/P5、L3及跨通道相位|周期数不足或趋势分解有歧义不报精确速率|B核对术语与源码定义；D验证变深变速信号
P5|拆分时间尺度|帧级F0残差与周期级jitter观测对象不同|ACO:P5;ACO:S7|P5记录指定分解后的短时F0残差；S7另记可定位周期的相邻周期时长变化|帧F0差分不可命名生理jitter；八度错误先归估计问题|P5:cents/帧秒；S7:周期时长秒及注明公式的相对值|P1/P2/P4、S5|周期定位不可信、强调制或间断段不计算S7|B核对jitter适用性；D分开帧指标与周期指标
L1|拆分并迁出感知|RMS/dBFS是信号量，感知大/小还依赖播放、谱和时间关系|ACO:L1;PER:L1|L1记录指定声道/窗口的RMS或峰值；PER记录听者的响度比较及播放/混音条件|RMS不能直接作为感知响度或饱满；LUFS代理也不能替代单字用户标签|ACO:线性振幅/dBFS/峰值；PER:原话/顺序或明确评价量表；秒窗|L2/L3/L4、R/S谱、X3/X4|播放条件未知则仅保存原话；数字静音不伪造有限dBFS值|B复核电平/响度量；D明确短窗与零值；E同电平异谱
L2|转为包络属性|强弱意图与输出包络混合，30/50ms只是当前候选窗口|EVT:L2|在声明窗口/hop下描述输出振幅包络非周期走势和低谷位置/持续时间|不包含应不应该渐弱的价值判断；不将每字平均替代接口|dBFS、dB/s、秒；字头/核/尾与乐句|L1/L3/L4、T2/T6|窗口平滑可能抹去低谷，未验证前不定异常阈值|D验证窗口与瞬态；E长音漏底/有意弱收
L3|保留并更名振幅调制|音量一词混淆输入增益、输出幅度与感知响度|ACO:L3|在指定包络上记录准周期振幅变化及其与F0调制的相位关系|输出AM存在不证明人为DYN变化；不自动判颤抖|Hz、线性调制指数或注明的dB深度、相位、秒|L1/L2、P4、R3|频带包络与全带包络可能不同；不明来源保持unknown|B核对AM与听感；D固定包络算法
L4|转为瞬态事件|短窗下降、瞬态峰值与真正波形不连续不能等同|EVT:L4|记录指定接口附近振幅包络突增/突降及支持区，注明窗长与参照|波形接缝用X2；crest factor不独立证明突变或爆音|dB差、秒、峰值/均方；接口相对时钟|L1/L2、X1/X2、T4/T5|无接口或短窗稳定性不足不判因果增益跳变|D瞬态窗口核查；E果接口与抱字头反馈
S1|拆分听感与观测|周期性、模型voicing、听感有芯/支撑与生理力量不是同一对象|ACO:S1;PER:S1|S1记录声明方法得到的周期组织/显著性指标；PER记录有芯、支撑等听感与阶段|VOIC是控制输入；CPP/HNR数值不可直接命名胸声、声门闭合或能量|方法指定的CPP/HNR/周期显著性及单位；稳定段或局部窗口|S2/S3/S5/S6、L2；PER假/实组合|噪声与非规则周期可能影响估计；单指标不决定实感|B核对声质指标；D明确算法/元音/音区限制
S2|限定为输出谐波形状|原行从原始谐波跳到经校正声源谱，逆问题未说明|ACO:S2|记录输出谐波幅度分布；反滤波/共振校正后的声源估计另设method和假设字段|不把原始H1-H2解释为独立声源开合；亮/厚移入PER组合|dB比、dB/倍频程或指定频段斜率；F0匹配窗口|R1/R2/R3、新增ACO:R5；S3|不可分离声源和滤波时只报告输出谱；高F0谐波稀疏限制|B逐说法核对校正；D禁止跨元音原始差值阈值
S3|保留估计量并限定段落|气声标签、辅音噪声、算法残差被同称噪声比例|ACO:S3|指定分解算法和频带的周期/非周期成分比例或代理|算法非周期残差不全等于漏气；CPP不直接等于物理噪声百分比|dB比或明确分解的比例；phone阶段/窗|S1/S4、X5、PER气声/沙哑|无分解真值或摩擦段不得推断人体气流|B核对噪声/听感；D声明分解假设
S4|拆分谱属性与时间位置|噪声频带和噪声发生在哪个阶段单位与对象不同|ACO:S4;EVT:S4|ACO记录已识别非周期分量的频谱分布；EVT记录其与辅音/元音/气口的支持时间|齿音不是元音气声；全信号谱质心不能直接当噪声谱质心|Hz/dB频带；时间秒和phone区间|S3、T3/T4/T7|不能可靠分离噪声时标输出频带而非噪声频带|B核对声源/摩擦区分；D时间定位协议
S5|保留结构并迁出粗糙评价|次谐波、多周期、侧带与听感粗糙不是充分必要对应|ACO:S5|描述可支持的基频分频/多周期/侧带结构与稳定时段；不同结构用属性区分|声部叠加或AM侧带不自动判次谐波；撕裂归组合听感|频率Hz、频率比、相对dB、持续秒|P5/S1/S3、L3、X2|未排除双声部、谐波误认和窗泄漏不确认结构|B核对粗糙研究；D方法候选；E有意粗糙/异常分开
S6|转为声源事件|中断可观测；声区翻转与破音病因是另一层解释|EVT:S6|在非休止目标区间记录周期组织消失/恢复及同时谱/电平变化，链接用户破音标签|AP/SP和辅音正常无声不判失声；无满幅削波不等于没有破音|秒、有效帧掩码、关联F0/谱/电平轨迹|S1、L4、P3、T4/T5、PER破音|周期估计失败与实际中断分开；本曲字头类型仍unknown|B核对中断/声区术语；E抱B及C标签范围
R1|保留估计对象并迁出生理|F1/F2是共振估计，舌根/圆唇/口腔形状不可直接反推|ACO:R1|在明确声道模型/估计法下记录共振中心与误差，无法估计时记录输出谱于R5|最大谐波不等于共振；听感口型原话保存为PER描述|Hz、估计不确定区间；phone核/动态窗|S2、R2/R3/R4/R5|高F0、谐波稀疏或模型拟合不稳不填精确F1/F2|B核对formant估计限制；D建立拒绝条件
R2|拆分带宽与凹陷|共振带宽、反共振与任意输出能量凹陷不是同一测量|ACO:R2;ACO:R6;ACO:R5|R2记录可信共振带宽；R6记录可信滤波峰零/反共振候选；只见输出峰谷写R5|单频带能量下降不直接判共振带宽或反共振|Hz带宽/位置、dB深度；估计模型/窗|R1/R3/R4、S2|声源谱不可分或零点不可靠时仅保留输出谱，不确认声道结构|B核对峰零区别；D避免LPC自动填满
R3|转为动态关系|谱包络动不等于声道共振必定漂移；双元音本就需描述变化|EVT:R3|在同音素阶段比较R1/R2或R5的时序轨迹，注明到底测到何种对象|不要求双元音静止；正常元音切换不自动判共鸣不连续|Hz/s或定义的谱距离、秒；phone核/边界|R1/R2/R5、T2/T5|仅输出谱时只称谱变化；听觉口型与机制保持分离|B校正口型描述；E同字跨上下文与双元音
R4|拆分候选谱型与鼻感|鼻化线索、鼻辅音和主观堵/鼻混合|ACO:R4;PER:R4|ACO记录指定假设下鼻化相关谱模式候选；PER保存鼻感/堵感与语音上下文|不能用单个峰或TENC变化确认鼻腔耦合；闭塞不等于鼻化|候选峰/零Hz与相对幅度、阶段；PER原话|R1/R2/R6、T3、组合鼻腔色彩|未验证鼻化检测时不确认人体机制；鼻音身份另外记录|B核对鼻化与声道资料；D方法状态待验证
T1|保留关系并明确多时钟|note/phone实际起点、原曲与拍点参照不能共用一个误差|EVT:T1|明确事件类型及独立参考时钟后记录时间差，保留映射来源与误差|音符移动不自动等于声学元音落点移动；抢拍是音乐评价|ms/拍；source、score、native、PCM分轴|T2/T4/T5/T7、P3|源字界未知或时基未绑定则不报告精确抢/拖值|D建立时基契约；E0:48这叫爱等定位原话
T2|保留并把承载意图移出|phone时长与足够/吞字评价混合|ACO:T2|为明确分段边界记录辅音/核/韵尾持续时间及比例；符号token与内部声学运动分开|uo整体token不证明内部没有过渡；拉note时长不必线性拉全部phone|ms、比例；native时钟与PCM观测分栏|T1/T3/T5/T6、R3|HFA边界有误差，未核实段落不伪造精确CV比例|B/D核对phone与音节层级；E短核/延音/韵尾
T3|拆分辅音事件与清晰度|爆破/VOT/摩擦是观测，清晰/含糊是感知且也受混音影响|EVT:T3;PER:T3|记录辅音类别对应的爆破/摩擦/送气事件及谱幅；PER记录可懂度与咬字原话|辅音电平下降不直接判咬字坏；ASR通过不等于自然|秒、VOT ms、谱/电平；类别和字位|S4、L4、T2/T4/T5、X3|无爆破锚点不测VOT；没有听者标签不判清晰|B核对语音定义；D按类别观测；E抱C邻字
T4|保留为起声关系|增益attack、辅音起点与周期声建立是不同过程|EVT:T4|分别定位噪声/辅音、周期声、F0到达、包络增长并描述先后|人工SHFC进入时间不等于输出周期声入口；硬/柔/气起标签独立|秒/ms、事件间差值；多个明确边界|S1/S3、P3、L2/L4、T3|周期/辅音锚点不可信则不判协调类型|B核对起声术语；D/E分别检查增益与条件进入
T5|转为多通道衔接关系|时间gap、声线连续与审美连贯不是一个标量|EVT:T5|两个phone间记录gap/overlap及P/L/S/R轨迹变化，说明编辑分段与实际声学边界|时间连续不推出音色连续；oto overlap不等于声学过渡长度|ms及所链接轨迹单位；pair身份/边界|P3/R3/S6/L4、T1/T2|单轨融合信号无法分离声部重叠时不报物理overlap|E检查正常元音换型与异常断层；D关系协议
T6|拆分释放关系与韵尾身份|元音收声与韵尾是否存在需要不同观察|EVT:T6;EVT:T8|T6记录周期/噪声/电平向静音释放顺序；T8记录预期韵尾身份、出现/缺失与支撑|弱声不等于韵尾丢失；音素表有韵尾不等于输出已实现|ms/秒及phone类别；核→尾→间隙|T2/T3/T5/T7、S6/L2|韵尾听感/边界未核实则保持unknown，不靠DYN补造身份|B语音核查；E弱收但保韵尾/硬切
T7|拆分呼吸事件与间隙组织|AP标记、吸气声音、静音和语义断句不是同一对象|EVT:T7;EVT:T9|T7记录可信呼吸噪声与方向未知；T9记录声学间隙/工程AP-SP和音乐断句参照|AP不保证真实吸气；SP不是失声标签；不由工程推断呼吸生理|事件秒、间隙ms、标签/目的|S4/T1/T6、L2、上下文|吸呼方向没有证据就unknown；意图单独由Agent说明|B核对呼吸术语；E静音/换气/连续负担
X1|拆分检测量与失真解释|满幅削波可查，广义非线性/破音不一定能从单个输出定位|ACO:X1;PER:X1|ACO记录采样满幅/饱和形态及已知变换的非线性残差；PER记录炸/失真原话|true peak是过载风险量，不是已发生削波证据；模型破音未必文件饱和|峰值、dBFS/dBTP、样本比例；有输入对照才记变换残差|L4/S6、X2|只有输出时非线性病因unknown；无满幅不能否定用户破音|B核对峰值标准；D已知削波测试；E抱字头
X2|拆分观测与数码成因|不连续/重复纹理可观察，称数码伪影带有实现病因推断|ACO:X2;ACO:X6;PER:X2|X2记录边界波形/差分跳变；X6记录指定时延重复/相关纹理；PER保存咔哒/金属颗粒等标签|单点差分大不一定为接缝；普通周期性不判数码重复|振幅差、相关系数、时延秒、边界位置|X1/P4/S5/T5、R5|定位到拼接器或声码器需要真实输入/实现证据，不能从听感命名病因|B/D核对伪影方法；E模型/组装/有意重复分开
X3|拆分声部关系与掩蔽感知|stem幅度可比，实际遮蔽依听觉且分带/时间条件有关|ACO:X3;PER:X3|ACO记录显式两声部的分带/时序电平关系；PER记录在指定混音/监听下是否被盖住|声部电平差不是通用可懂度阈值；分离误差不当独立真值|相对dB、频带Hz、秒；stem来源/混音增益|L1/PER:L1、T3、R5/X4|只有混音或分离质量未知时不冒充独立stem比例|B掩蔽原始资料；E纯人声/混音与同电平异谱
X4|拆分通道与空间听感|pan、互相关、混响衰减、近远感观测对象不同|ACO:X4;ACO:X7;PER:X4|X4记录声道电平/相关及已知时延；X7记录有条件可测的尾部衰减/反射；PER记录近远/湿宽原话|相关系数不独立决定宽度；尾音延长不必为混响；输出不能凭空恢复房间参数|dB差、相关、时延ms；尾部dB/s、已知IR衰减时间；PER原话|L1/X3、T6、R5|缺少干声/IR或尾部被乐器盖住，直湿比/混响参数unknown|B空间方法定义；D未知输入限制；E单声道/多轨
X5|迁出格式元数据并复用已有声学对象|频带质地、噪声底与格式标签混合并重复S4/R2|ACO:R5;ACO:S3;ACO:S4;META:X5|实际输出带宽/总谱用R5，噪声量与分布用S3/S4；格式保存采样率、编码、位深、声道和转换链|格式元数据不是一个演唱原子；44.1kHz不等于有22.05kHz有效能量|Hz/dB频谱；META采样率Hz/位深bit/编码/声道|S2/R1/R2与X1/X2|未知转换链保留unknown，编码标签不证明听感低保真|B/D核对频带与格式；E底噪/低保真标签
'''

ENTITY_TYPES = {'ACO': 'acoustic_observation', 'EVT': 'temporal_event_or_relation',
                'PER': 'perceptual_description', 'META': 'context_or_format'}

def main():
    refuse_after_formal_migration()
    for name, expected in BASELINE.items():
        actual = sha(OUT / name)
        if actual != expected:
            raise ValueError(f'Baseline changed: {name}: {actual}; review before rebuilding')
    original = read_csv('atomic-manifestations.csv')
    by_id = {r['id']: r for r in original}
    decisions = []
    for line in DECISIONS.strip().splitlines():
        old, action, problem, targets, definition, exclude, units, related, unknown, pending = line.split('|')
        ids = targets.split(';')
        decisions.append({
            'legacy_id': old, 'legacy_name': by_id[old]['dimension'], 'decision': action,
            'problem': problem, 'proposed_ids': ids, 'entity_types': [ENTITY_TYPES[i.split(':')[0]] for i in ids],
            'operational_scope_proposal': definition, 'exclude': exclude, 'units_and_clock': units,
            'related_legacy_dimensions': related, 'unknown_rule': unknown, 'required_followup': pending,
            'definition_checked': 'structural_proposal_only', 'source_checked': 'pending_stage_B',
            'current_engine_support': 'not_determined_in_stage_A', 'code_path_checked': 'pending_stage_C',
            'measurement_defined': 'scope_proposed_details_pending_D', 'measurement_validated': 'not_validated',
            'description_coverage_checked': 'pending_stage_E', 'auditory_label_status': 'no_new_labels',
            'legacy_evidence_text': by_id[old]['evidence'],
        })
    assert len(decisions) == len(original) == 31
    assert {r['legacy_id'] for r in decisions} == set(by_id)
    lookup = {r['legacy_id']: r['proposed_ids'] for r in decisions}

    # The original second layer is NOT rewritten. Produce a separate proposed
    # linkage for every declared atomic reference so its historical IDs stay valid.
    layer2 = json.loads((OUT / 'conditional-responses.json').read_text(encoding='utf-8'))
    linked = []
    for collection in ['responses', 'observations', 'audits']:
        for record in layer2[collection]:
            atoms = record.get('atomic_ids', record.get('atoms', []))
            if isinstance(atoms, str):
                atoms = atoms.split(';') if atoms else []
            assert all(a in lookup for a in atoms), (record['id'], atoms)
            linked.append({'record_id': record['id'], 'legacy_atoms': atoms,
                           'proposed_candidates': {a: lookup[a] for a in atoms},
                           'status': 'candidate_links_not_new_observations'})

    evidence = json.loads((OUT / 'knowledge-table.json').read_text(encoding='utf-8'))
    namespaces = {
        'dimension': {k: {'legacy': f'legacy_dimension:{k}', 'candidates': v} for k,v in lookup.items()},
        'source': {r['id']: f"SRC:{int(r['id'][1:]):02d}" for r in evidence['primary_sources']},
        'code_mechanism': {r['id']: f"CODE:{int(r['id'][1:]):02d}" for r in evidence['mechanisms']},
        'project_evidence': {r['id']: f"EVID:{int(r['id'][1:]):02d}" for r in evidence['evidence']},
        'control_family': {r['id']: f"CTRL:{r['id']}" for r in evidence['controls']},
    }
    migration = {'schema_version': 1, 'status': 'proposed_not_applied',
                 'old_id_semantics_preserved': True, 'baseline_sha256': BASELINE,
                 'namespaces': namespaces, 'second_layer_candidate_links': linked,
                 'rule': 'Splits are candidates, not automatic assertions that every new entity occurred in each old experiment.'}
    write_json('id-migration.json', migration)
    review = {'schema_version': 1, 'stage': 'A', 'status': 'structural_review_complete_validation_pending',
              'baseline_sha256': BASELINE, 'original_rows': len(original), 'rows': decisions,
              'proposed_entity_count': len({i for r in decisions for i in r['proposed_ids']}),
              'no_new_synthesis': True, 'no_skill_or_project_change': True}
    write_json('table1-row-review.json', review)
    flattened = [{**r, 'proposed_ids': ';'.join(r['proposed_ids']),
                  'entity_types': ';'.join(r['entity_types'])} for r in decisions]
    write_csv('table1-row-review.csv', flattened)

    lines = ['# 表1逐行结构审查：阶段A', '', '日期：2026-10-09。原31行均已审查；本文件只确认工程描述结构和拆分提案，B文献、C软件路径、D观测方法、E覆盖及F正式修订尚未完成。', '',
             '基线六份文件SHA核对通过。原三份清单、knowledge-table与第二层保持原字节，拆并尚未应用；候选实体不等于新增已验证原子。没有新听音、新合成或歌曲/Skill变更。', '',
             '结构与字段见[实体与标注规范](table1-schema.md)。完整字段见[CSV](table1-row-review.csv)和[JSON](table1-row-review.json)；旧ID及第二层候选关联见[id-migration.json](id-migration.json)。', '',
             '## 逐行决定', '', '| 原ID／名称 | 决定／候选去向 | 问题与理由 | 后续确认 |', '|---|---|---|---|']
    for r in decisions:
        lines.append(f"| {r['legacy_id']} {r['legacy_name']} | {r['decision']}：{'; '.join(r['proposed_ids'])} | {r['problem']} | {r['required_followup']} |")
    type_counts = Counter(i.split(':')[0] for i in {i for r in decisions for i in r['proposed_ids']})
    lines += ['', '## 拆并结论与尚未确认项', '',
              f"31个旧条目目前提出{review['proposed_entity_count']}个不同实体引用：" + '、'.join(f'{k} {v}' for k,v in sorted(type_counts.items())) + '。数量变化来自实体分层，并不代表科学完备性增强或检测器数量。', '',
              '- L1拆电平与感知响度；S1拆周期观测与支撑听感；T3拆辅音事件与清晰度；R4拆谱型候选与鼻感；X3/X4拆声部/通道关系与听感。',
              '- P5的帧级残差与周期级时长扰动分开。R2的带宽、反共振与输出峰谷分开；新增R5作为输出谱包络对象，由原S2/R1/R2/R3/X5交叉引用，避免强行推断声道。',
              '- T6分离释放顺序与韵尾身份；T7分离呼吸声事件与间隙组织；X2分离接缝观测、重复纹理与伪影成因；X5中的格式转入META。',
              '- P2/P3、L2/L4、S6、R3、T1/T4/T5/T6/T7是时间过程或关系，允许复用基础观测，不再强称独立声学标量。',
              '- 所有PER均保留原话和比较范围；没有用户或研究感知标签，不自动填“正常”“自然”“假音消失”。没有已验证反滤波/鼻化/声区检测时，不把候选物理解释升级为事实。', '',
              '## B–E所需补充', '',
              'B逐说法查证：F0调制与残差、周期级jitter/幅度周期变化、声源/滤波分离、粗糙/次谐波、感知响度、鼻化与高F0共振估计、辅音/起声/呼吸、空间与伪影。来源不能只指向一篇泛论。', '',
              'C继续展开原48控制分组，而非把候选实体数当控制枚举数；各参数要区分工程字段、当前引擎读取、模型支持、上游能力与外部监听。', '',
              'D必须补窗口、hop、公式、质量掩码、时基和拒绝条件；本文件的单位栏只是对象约束，不等于已完成测量协议。E独立案例清单须冻结后再映射，不能仅用这些候选名称自测覆盖。', '',
              '## 阶段A验收', '',
              '- 原31行各有问题、决定、候选去向、包含/排除范围、单位/时间轴、相关维度、unknown和后续核查项。',
              f'- 原第二层{len(linked)}条RESP/OBS/AUD记录已逐项检查其旧维度引用；另存候选关联，不改原实验记录或反馈。',
              '- 来源、维度、控制、机制与实验使用不同命名空间；迁移状态明确为proposed_not_applied。',
              '- 尚不能宣布表1已确认；正式清单更新须待B–E结论并在F统一应用。', '']
    (OUT / 'table1-review.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'stage': 'A', 'reviewed_rows': len(decisions),
                      'proposed_entities': review['proposed_entity_count'],
                      'second_layer_linkage_records': len(linked),
                      'baseline_matches': len(BASELINE), 'status': review['status']}))

if __name__ == '__main__':
    main()
