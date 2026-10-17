"""Explicit context/task fields addressing E's partial structures, not detectors."""
FIELDS = [
 ('CTX:IDENTITY','对象与层级身份','asset_sha256,version,score_note_ids,syllable_id,phone_id,language,token,source_status','音符/歌词/音素/实际声学对象不能默认一一对应','CASE:EU17'),
 ('CTX:PHRASE','乐句与重音关系','parent_id,child_ids,beat_reference,stress_span,motif_id,gesture_goal,goal_source','重音/动机/动作目的未给出时unknown，不从峰值反推音乐身份','CASE:EM02'),
 ('CTX:REFERENCE','音乐与调律参照','tonic,mode,harmonic_context,tuning_system,reference_frequency,reference_event,clock_mapping,reference_uncertainty','没有明确调律/音乐目标，不能用12TET默认判所有音准好坏','CASE:EM12'),
 ('CTX:ORNAMENT','快速目标序列与调制','target_sequence,target_identity_source,arrival_support,cycle_role,intended_or_unknown','两个音乐目标交替与一个中心周围FM分开；短支持拒绝精确周期判断','CASE:EM10'),
 ('CTX:TASK','感知任务与参与角色','task_id,observer_id,observer_role,target_role,presentation_asset_sha,order,question,scale,playback_conditions,shared_feedback_group','performer_feedback、listener_presentation与Agent观测分开；历史未记录设备/盲法等保持unknown','CASE:EL02;CASE:EL04'),
 ('CTX:EMOTION','多标签情绪与音乐目的','reported_terms,intended_terms,term_source,rating_by_observer,scale,semantic_context','声学特征不自动编码喜怒悲惧；未知/多情绪不强压唯一标签','CASE:EL03;CASE:EL04'),
 ('CTX:SOURCE_RELATION','周期源与感知音高关系','periodic_source_hypotheses,F0_tracks,harmonic_index,perceived_pitch_tracks,relationship_evidence,alternatives','被增强谐波的旋律不默认是独立第二F0；源数/生理机制可unknown','CASE:EL05'),
 ('CTX:SAMPLING','案例总体与反馈范围','sampling_frame,case_members,aggregate_or_individual,selection_rule,partition,feedback_scope,identity_errata','313未知字集合不是313个覆盖案例；共一原话不增加独立试验数','CASE:EU18'),
]

# Control-family navigation only; each concrete item retains C's condition/scope.
FAMILIES = {
 'P1':'01 02 03 14','P2':'02 03','P3':'01 02 03','P4':'04 05 06 07 08 09','P5':'02 03',
 'L1':'10 17 26 42','L2':'10 16 17 26 27','L3':'09 10','L4':'10 26 27 41',
 'S1':'11 12 13 14 18 19 20 39','S2':'13 14 15 19 20 43','S3':'11 12 31','S4':'12 23 31 43',
 'S5':'35 39','S6':'01 14 24 41 47','R1':'14 15 19 20 23 39','R2':'14 15 19 43',
 'R3':'01 14 19 20 23 24 41','R4':'15 19 23 43','T1':'22 24 25 27 28',
 'T2':'22 24 25 27 28','T3':'23 24 25 26 27 28','T4':'11 12 14 24 26 27',
 'T5':'01 11 12 14 23 24 41','T6':'10 24 26 27','T7':'22 24 41',
 'X1':'10 26 42 44 46','X2':'39 40 41 46','X3':'42 43 44 46','X4':'42 45 46',
 'X5':'39 40 45 46',
}

def context_fields():
    return [dict(id=id_,name=name,fields=fields.split(','),unknown_rule=rule,applicable_scope='all_records_when_applicable',coverage_case_refs=refs.split(';'),
        status='formal_record_schema_defined_not_measurement_or_label_validation') for id_,name,fields,rule,refs in FIELDS]

def families(legacy_ids):
    return sorted({'CTRL:C'+x for lid in legacy_ids for x in FAMILIES[lid].split()})
