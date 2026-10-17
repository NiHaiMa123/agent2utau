"""Explicit mappings for the 36 main questions; no deferred recheck here."""
# code | candidate entities | time/context relation | reason | gap code
MAIN = '''
U01|PER:S1 ACO:P1 ACO:R5 EVT:T4|g→uo入口/核；与U05跨上下文|保留偏假/前顶原话，音区/元音相近不消除上下文混杂|MEASUREMENT
U02|PER:S1 ACO:P1 ACO:R5 EVT:T4|b→ao入口/核；与U06同上下文干预|问题词与SHFC模型条件/生理声区分开|MEASUREMENT
U03|PER:S1 ACO:T2 EVT:T3|ir/F#4，字内阶段|偏实是相对听感，不能填所有指标正常|LABEL_SCOPE
U04|PER:S1 ACO:T2 EVT:T3|ir/A4；与U03跨音区|不同音区的偏实标签不建立统一阈值|LABEL_SCOPE
U05|PER:S1 EVT:T5 ACO:P1 ACO:R5|同字果，1:27/3:17/3:44三段|中间局部可用不是声学因果或邻字验收|LABEL_SCOPE
U06|PER:S1 PER:X1 EVT:T4 EVT:T5 ACO:R5|55→145ms条件进入；核平台/退出保留|只记录可以，字头/字腹/完全无破音均未细标|LABEL_SCOPE
U07|PER:S1 ACO:R5|同上下文TENC取消A/B|数值谱响应与没区别允许同时记录|PROXY
U08|PER:S1 PER:X1 EVT:T4 EVT:S6 ACO:X1 ACO:R5|抱字头与字腹分开，B/A比较|更实与破音可并存，满幅阴性不能反驳标签|MEASUREMENT
U09|PER:S1 EVT:T5 ACO:P1|三处原抱相似性，非正常/异常对照|都一样只为关系标签，不给另外两处正常/异常|LABEL_SCOPE
U10|PER:S1 PER:T3 PER:L1 EVT:T3 EVT:L4 ACO:R5|果及后这、比较对象明确而响度位置未定|整元音RMS近似不能否认听感下降；好像不删去|MEASUREMENT
U11|PER:S1 ACO:R5|问题果BREC A/B，同组剂量|一个共同反馈关联六条件；本剂量无感知区别|PROXY
U12|PER:S1 ACO:R5|偏实之BREC A/B，同组剂量|既有偏实与新无区别是不同标签任务|PROXY
U13|PER:S1 ACO:R5|偏实只BREC A/B，同组剂量|不把无区别改成全部自然或绝无副作用|PROXY
U14|PER:S1 ACO:R5|问题抱BREC A/B，同组剂量|问题原标签未因新无区别被抹掉|PROXY
U15|PER:S1 ACO:R5|可用果BREC A/B，同组剂量|原局部可用保留，不推广BREC方向|PROXY
U16|PER:S1 ACO:R5|接受抱C再加BREC，与原抱分开|变体身份及交付SHA区别于原版对照|PROXY
U17|PER:S1 ACO:P1 EVT:T5|3:44果第三段，无用户质量标签|预测接近不补正常；冻结word号需核对，暂只用绑定报告时位|IDENTITY
U18|PER:S1 ACO:T2|313未知字集合，尚未逐字入覆盖|未知集合可记但不能代表313个独立映射或正常样本|POPULATION
M01|ACO:P1 EVT:P2 ACO:P4|长稳态核、音乐目标为直音|缺颤音不等于异常；意图在上下文而非声学值|INTENT
M02|EVT:L2 EVT:T1 ACO:L1 PER:L1|乐句级重音/强弱及回落|电平轨迹可记，句层重音/语义身份需具体关系字段|PHRASE
M03|EVT:T6 ACO:X2 ACO:X7|周期/电平收束、拼接和尾混响分别计时|弱尾、硬切和reverb代理不能互相替换|MEASUREMENT
M04|EVT:P3 ACO:P1 EVT:T1|起始/目标音、到达/保持|参考明确才能描述上滑与过冲，不默认异常|INTENT
M05|EVT:P3 EVT:T6 EVT:T5|尾滑源/目的及后字时钟|下滑与收尾组织可组合，目标可能不唯一|INTENT
M06|EVT:P3 EVT:T4 EVT:T1|入口倚音后到正音|迟到是否错误需锚点/目的，不从F0独判|INTENT
M07|ACO:T2 EVT:P3 EVT:T5|一音节/元音核对应多note|输入note数量不能变成多段词识别真值|LANGUAGE
M08|EVT:T3 EVT:T5 EVT:R3|元音/辅音跨界与句内承接|正常协同发音与异常断层的区分需标签|LANGUAGE
M09|EVT:T9 EVT:S6 EVT:T6|合法休止/断唱意图和周期中断|不能把所有gap当破音|INTENT
M11|ACO:P4 ACO:L3 EVT:P2 EVT:T4 EVT:T6|周期入口/核/退出与AM/谱关系|动态调制能分量记录，检测短支持/变速未验证|MEASUREMENT
L01|ACO:P1 EVT:P3 ACO:T2 EVT:T9|三和弦、连/断、快/慢任务身份|外部人体任务提供取样条件，不充当本机成功样本|EXTERNAL
L02|ACO:X3 PER:X3 ACO:P1|演唱者反馈遮蔽与听者呈现任务分栏|掩蔽源/对象/任务的角色缺具体元数据，不套神经模型|TASK_ROLE
L03|ACO:P4 EVT:L2 ACO:R5 ACO:T2|同乐句不同情绪、听者评价与动作目的|情绪原话可存；无正式情绪任务字段或可靠声学逆映射|EMOTION
L06|ACO:R1 ACO:R5 ACO:P1|高F0元音，共振解释与输出谱区别|能表达共振unknown，不用谱峰补造F1|MEASUREMENT
L08|ACO:S7 ACO:L5 ACO:P4 ACO:L3|周期级与帧/包络级，稳态/运动分层|尺度拆分避免残差冒称jitter；pulse未测|MEASUREMENT
A01|ACO:T2 EVT:P3 EVT:T5|作者note21+及前后note输入连接|只读字段支持一字多音输入结构，不证明实际连贯|AUTHOR
A02|ACO:T2 EVT:T1 EVT:T5|雨爱de跨tone/duration，保留note身份|同syllable不同条件可记录，未听不能叫可用/问题|AUTHOR
A03|EVT:T7 EVT:T9 META:X5|作者AP/SP、part与note空隙|元数据只能证符号/间隙，不推实际呼吸与静音|AUTHOR
'''

GAPS = {
 'MEASUREMENT': '真实PCM估计/边界/源分解缺独立真值；只可定义候选，不验证质量/病因。',
 'LABEL_SCOPE': '仅原标签范围明确，其它阶段/自然度/病因均unknown；不需新声学原子来制造正常标签。',
 'PROXY': '历史原生输入隔离与谱代理已记；可感知响应仅原剂量/条件，不能把代理数值当改善或统计等价。',
 'IDENTITY': '冻结U17误写word-282；既有原始feedback.json的word295_unknown_retained=true确认应为word295。新增勘误绑定，保留冻结文本/42项分母，听感仍unknown。',
 'POPULATION': '本项是未知总体边界，不是逐字覆盖；尚需显式case身份/取样规则，不能计313例。',
 'INTENT': '通用上下文能保存动作目的/参照，但尚无各动作操作阈值或听感标签；曲线无自动好坏。',
 'PHRASE': '缺重音、动机/句层级的具体关系/参照schema；已有字段只部分表达，F应补操作字段而非无限新增原子。',
 'LANGUAGE': '实际辅音/双元音/韵尾内部身份和边界需要语言专项；token/续音输入不是声学真值。',
 'EXTERNAL': '仅外部研究任务的描述覆盖；未导入音频/样本级数据，不能声明本机观测或跨曲验证通过。',
 'TASK_ROLE': '应显式区分performer feedback与listener presentation；缺任务角色操作字段，信号比值不能补齐。',
 'EMOTION': '应保留多标签情绪、听者评分和任务语境；已有声学指标不充分。仅通用PER/上下文字段部分记录，暂不创正式情绪维度。',
 'AUTHOR': '作者结构例仅输入事实；没有作者波形或听觉标签，不能视为完整测量或自然度覆盖。',
}

PARTIAL = {'U18','M02','L02','L03'}

def main_mappings():
    rows=[]
    for line in MAIN.strip().splitlines():
        code,entities,relation,why,gap=line.split('|')
        rows.append(dict(case_id='CASE:E'+code,candidate_entity_refs=entities.split(),
            temporal_or_context_relation=relation,mapping_reason=why,gap_code=gap,
            unexpressed_or_unknown=GAPS[gap],structure_status='partial_structure' if code in PARTIAL else 'representable_with_scope',
            new_dimension_decision='no_new_atomic_ID; extend specific context/task fields in F' if code in PARTIAL else
                'reuse candidate entities; no new atomic ID required for the stated scope',
            reliable_measurement_for_case_conclusion=False,auditory_label_added=False))
    assert len(rows)==36
    return rows
