"""Six deferred mappings authored after the 36-case main checkpoint."""
from stage_e_mapping_data import GAPS

RECHECK = '''
M10|EVT:P3 ACO:P4 EVT:T1|快速两目标交替，局部note身份及极短支持|周期候选只表示运动；缺转音目标序列/尺度规则，不能自动叫vibrato|ORNAMENT|partial_structure
M12|ACO:P1 PER:P1 EVT:T1|同Hz与不同调式/和声/调律参照|Hz能记录但音乐身份/调律误差需显式参照，固定12TET不能包办|REFERENCE|partial_structure
L04|PER:L1 PER:S1|同一呈现、多听者/多情绪评分，不混成共识|现有PER可存原话但缺评分者/任务/多标签schema；不能把评分差视为检测失败|EMOTION|partial_structure
L05|ACO:R5 ACO:P1 PER:P1 CAND:MULTI_F0|低持续音和被增强谐波的旋律关系|独立多F0仅是排除候选；感知多个音高与单周期源谐波旋律关系缺具体协议|OVERTONE|partial_structure
L07|EVT:S6 EVT:T3 EVT:T9|持续元音内部gap、清辅音/休止与检测冲突|结构能保存原因unknown；pulse方法未在歌唱上验证|MEASUREMENT|representable_with_scope
A04|ACO:P1 ACO:T2 META:X5|三作者不同谱面tone范围，AP/SP/续音另标|input tone统计非实际F0；低/高以各工程范围记，不推人体声区/质量|AUTHOR|representable_with_scope
'''
EXTRA_GAPS = {
 'ORNAMENT':'需要显式目标音序列/音乐身份、时长尺度和短段拒绝规则；不是把EVT:P3多次复制就证明完整表达。',
 'REFERENCE':'调式/和声/调律参照与音乐身份需独立schema；同一F0不代表相同音准意义，尚无标签/验证。',
 'OVERTONE':'需表达谐波序号与被听到旋律的关系；CAND:MULTI_F0不适合作默认声源分类，单基频多听觉音高协议尚缺。',
}

def recheck_mappings():
    rows=[]
    for line in RECHECK.strip().splitlines():
        code,entities,relation,why,gap,status=line.split('|')
        rows.append(dict(case_id='CASE:E'+code,candidate_entity_refs=entities.split(),temporal_or_context_relation=relation,
            mapping_reason=why,gap_code=gap,unexpressed_or_unknown=(EXTRA_GAPS|GAPS)[gap],structure_status=status,
            new_dimension_decision='no_new_atomic_ID; extend explicit target/reference/task relation in F' if status=='partial_structure' else
                'reuse candidate entities; retain measurement/audio unknown',
            reliable_measurement_for_case_conclusion=False,auditory_label_added=False))
    assert len(rows)==6
    return rows
