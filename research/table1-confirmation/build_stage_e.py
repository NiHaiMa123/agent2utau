"""Map a frozen checklist in two phases. Never reads/writes audio or curves."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from frozen_inputs import refuse_after_formal_migration

from stage_e_mapping_data import main_mappings

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'docs/knowledge/acoustic-manifestations-20261009'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def encoded(v):return json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict)) else str(v)

def checked_inputs():
    proof=load(HERE/'stage_e_freeze_binding.json')
    assert proof['frozen_before_mapping']
    for path,hash_ in [(proof['path'],proof['sha256']),(proof['checkpoint_path'],proof['checkpoint_sha256']),
        (proof['definition_baseline']['path'],proof['definition_baseline']['sha256']),
        (proof['checklist_authoring_source']['path'],proof['checklist_authoring_source']['sha256'])]:
        assert sha(ROOT/path)==hash_,f'Frozen input changed: {path}'
    frozen=load(ROOT/proof['path'])
    assert frozen==load(ROOT/proof['checkpoint_path']) and len(frozen['rows'])==42
    for r in frozen['input_bindings']:assert sha(ROOT/r['path'])==r['sha256'],r['path']
    d=load(OUT/'measurement-protocols.json')
    assert d['status']=='protocol_review_complete_with_explicit_gaps'
    return proof,frozen,d

def main():
    refuse_after_formal_migration()
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['main','final'],required=True)
    ap.add_argument('--run',type=Path,required=True);args=ap.parse_args()
    run=args.run.resolve();assert run.is_relative_to(ROOT/'runs/research')
    proof,frozen,d=checked_inputs()
    checkpoint=run/'observations/main-mapping-checkpoint.json'
    main_rows=main_mappings();main_ids={r['id'] for r in frozen['rows'] if r['review_partition']=='main_mapping'}
    assert {r['case_id'] for r in main_rows}==main_ids
    main_sha=sha(HERE/'stage_e_mapping_data.py')
    if args.phase=='main':
        assert not checkpoint.exists() and not (OUT/'description-coverage.json').exists()
        checkpoint.write_text(json.dumps(dict(phase='main',case_count=36,frozen_checklist_sha256=proof['sha256'],
            mapping_source_sha256=main_sha,rows=main_rows,no_new_audio_or_labels=True),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(status='main_mapping_checkpointed',cases=36,sha256=sha(checkpoint))))
        return
    prior=load(checkpoint)
    assert prior['rows']==main_rows and prior['mapping_source_sha256']==main_sha
    assert prior['frozen_checklist_sha256']==proof['sha256']
    from stage_e_recheck_data import recheck_mappings
    extra=recheck_mappings()
    assert {r['case_id'] for r in extra}=={r['id'] for r in frozen['rows'] if r['review_partition']=='deferred_mapping_recheck'}
    assert len(extra)==6
    mapping={r['case_id']:r for r in main_rows+extra};by_entity={r['candidate_entity_id']:r for r in d['rows']}
    old=load(OUT/'conditional-responses.json')
    records={r['id']:r for group in ['responses','observations','audits'] for r in old[group]}
    correction_path=ROOT/'runs/lastpage_guo_positive_comparison_20261008/feedback.json'
    corrected=load(correction_path);assert corrected['word295_unknown_retained'] is True
    correction=dict(case_id='CASE:EU17',frozen_evidence_key='word-282-at-224.132s',corrected_identity='word295',
        path=correction_path.relative_to(ROOT).as_posix(),sha256=sha(correction_path),
        anchor='word295_unknown_retained=true',label_remains='unknown',frozen_checklist_rewritten=False)
    rows=[]
    for case in frozen['rows']:
        m=mapping[case['id']]
        assert set(m['candidate_entity_refs'])<=set(by_entity)
        record=records.get(case['evidence_key'])
        row=dict(**case,**m,protocol_refs=[by_entity[k]['id'] for k in m['candidate_entity_refs']],
            legacy_dimension_refs=sorted({v for k in m['candidate_entity_refs'] for v in by_entity[k]['legacy_ids']}),
            user_label_available=case['label_text']!='unknown',
            auditory_label_status='existing_label_scope_only' if case['label_text']!='unknown' else 'unknown',
            independent_audio_holdout=False,
            existing_numeric_evidence='prior_input_or_proxy_records_only' if case['origin']=='existing_user_evidence' else 'none_imported',
            historical_record_id=record['id'] if record else '',
            historical_audio_hash_refs=record.get('bindings',{}).get('delivered_audio',{}) if record else {},
            audio_hash_check_scope='prior stored bindings copied; no waveform rehash or playback in E',
            pending_audio_needs='existing feedback retained; new causal listening requires later frozen table2 design; no audio generation in E',
            formal_entity_migration=False,description_coverage_checked='reviewed_with_explicit_gaps')
        # Feedback from readable reports; do not decode/repair old mojibake JSON.
        if row['user_label_available'] and row['label_kind']=='verbatim':
            report=(ROOT/case['source_refs'][0]).read_text(encoding='utf-8')
            assert row['label_text'] in report,case['id']
        if row['case_id']=='CASE:EU17':row['identity_erratum']=correction
        rows.append(row)
    counters=dict(case_count=42,main_mapping=36,deferred_recheck=6,
        by_origin=dict(Counter(r['origin'] for r in rows)),by_role=dict(Counter(r['role'] for r in rows)),
        by_structure_status=dict(Counter(r['structure_status'] for r in rows)),
        existing_user_label_rows=sum(r['user_label_available'] for r in rows),
        reliable_measurement_for_case_conclusion=sum(r['reliable_measurement_for_case_conclusion'] for r in rows),
        independently_held_out_audio_cases=0,new_auditory_labels=0,
        distinct_candidate_entities_linked=len({v for r in rows for v in r['candidate_entity_refs']}))
    assert counters['existing_user_label_rows']==16 and counters['reliable_measurement_for_case_conclusion']==0
    uncovered=[dict(candidate_entity_id=k,name=v['name'],protocol_ref=v['id'],coverage_status='no_case_in_frozen_checklist')
               for k,v in by_entity.items() if k not in {x for r in rows for x in r['candidate_entity_refs']}]
    assert len(uncovered)==16
    strata=[
        dict(axis='稳定/变化',case_refs=['CASE:EM01','CASE:EM04','CASE:EM11'],scope='unrecorded_music_questions; no new audio truth'),
        dict(axis='有意/异常',case_refs=['CASE:EM09','CASE:EU08'],scope='intentional question versus existing reported side effect; not acoustically matched'),
        dict(axis='字头/腹/尾',case_refs=['CASE:EU08','CASE:EM01','CASE:EM03'],scope='onset label plus body/tail questions; tail labels still unknown'),
        dict(axis='低/高音',case_refs=['CASE:EL05','CASE:EA04'],scope='published task/input-score range only; no local low/high audio validation'),
        dict(axis='不同元音/辅音',case_refs=['CASE:EU01','CASE:EU02','CASE:EU03','CASE:EM08'],scope='uo/ao/ir and g/b/zh classes; no full Mandarin inventory validation'),
        dict(axis='同字跨上下文',case_refs=['CASE:EU05','CASE:EU09','CASE:EA02'],scope='existing relational feedback and author structure; not isolated causes'),
        dict(axis='同电平异谱',case_refs=['CASE:EU10'],scope='near whole-vowel RMS with spectral/local-level differences; exact equal-level isolated waveform case absent'),
        dict(axis='纯人声/混音',case_refs=['CASE:EU07','CASE:EU10','CASE:EU11'],scope='stored delivery bindings/context; no paired vocal/mix-specific listening labels or new file checks'),
        dict(axis='单点/乐句衔接',case_refs=['CASE:EU08','CASE:EM02','CASE:EM08'],scope='single-point existing label plus phrase questions; phrase quality still unknown'),
    ]
    gaps=[dict(code=code,case_refs=[r['case_id'] for r in rows if r['gap_code']==code],
        status='explicit_gap_or_scope_limit',text=next(r['unexpressed_or_unknown'] for r in rows if r['gap_code']==code))
        for code in sorted({r['gap_code'] for r in rows})]
    payload=dict(schema_version=1,date='2026-10-10',stage='E',status='coverage_review_complete_with_explicit_gaps',
        checklist_binding=proof,main_mapping_checkpoint=dict(path=checkpoint.relative_to(ROOT).as_posix(),sha256=sha(checkpoint)),
        rows=rows,counts=counters,gaps=gaps,identity_errata=[correction],
        uncovered_candidate_entities=uncovered,sampling_axes=strata,
        source_quality_gap=frozen['table2_text_quality'],sources=frozen['sources'],
        sampling_limit=frozen['sampling_limit'],recheck_scope=frozen['recheck_scope'],
        statistical_or_universal_completeness_validated=False,all_descriptions_fully_expressible=False,
        all_measurement_methods_validated=False,no_new_audio_or_synthesis=True,no_new_auditory_labels=True,
        no_project_skill_or_production_change=True,formal_ids_migrated=False,stage_F='not_executed')
    (OUT/'description-coverage.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'description-coverage.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=list(dict.fromkeys(k for r in rows for k in r))
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerows({k:encoded(r[k]) if k in r else '' for k in fields} for r in rows)
    report=['# 表1描述覆盖审查：阶段E','','2026-10-10。**E为coverage_review_complete_with_explicit_gaps**。先冻结42项，再完成36项主映射，最后复查6项；原表/ID尚未正式迁移，F未执行。没有新音频、模型执行、作者数组复用或Agent试听。','',
        '独立清单见[冻结JSON](coverage-checklist.json)，逐项映射见[CSV](description-coverage.csv)/[JSON](description-coverage.json)。清单来自用户原证据、音乐任务、原始研究和作者输入结构，未使用B的自拟反例，也不是31个词各举一例。','',
        '## 取样与角色','','18项已有反馈/未知边界、12项未录制音乐任务、8项外部研究/方法条件、4项作者结构。U18的313字只算一个未知总体边界；6个BREC条件共用一个反馈原话。三份原始研究提供任务范围，没有导入/播放它们的录音；同论文拆成几个问题不增加独立实验数。','',
        '6项复查为M10、M12、L04、L05、L07、A04。这是冻结后延迟映射的过程复查，Agent先前已见A–D，不能叫盲法、全新音频留出集或泛化通过；数量不按映射结果增删。主映射checkpoint及SHA在新ignored研究run。','',
        '## 分开报告的结果','','| 项目 | 数量/含义 |','|---|---|',
        f'| 可按现有候选结构记录 | {counters["by_structure_status"].get("representable_with_scope",0)}项；限清单指定对象与范围 |',
        f'| 结构只能部分表达 | {counters["by_structure_status"].get("partial_structure",0)}项；明确列出上下文/关系/任务缺口 |',
        '| 有既有用户标签 | 16行；不是16个独立反馈实验，也不全为正常/异常标签 |',
        '| 有完整可靠测量支撑该案例结论 | 0项本轮可宣布通过；历史输入/PCM代理的具体事实继续有效，不能升级为破音/实感等测量真值 |',
        f'| 链接候选实体 | {counters["distinct_candidate_entities_linked"]}/50；未链接项仍是未覆盖，不能因清单全映射声称维度穷尽 |',
        '| 新标签/新音频/独立音频留出 | 均0 |','',
        '取样轴逐项见JSON。稳定/变化、有意/异常、字头/腹/尾、低/高、不同元音/辅音、同字跨上下文、单点/乐句均有问题/例的来源，来源角色仍分开。U10只是整元音RMS接近且局部电平/谱不同，严格等电平隔离波形缺；纯人声/混音仅已有交付绑定，不是分别听觉验收。不能把问题清单的存在当成实际歌唱案例全部齐备。','',
        '未被清单链接的16个候选实体：'+', '.join(r['candidate_entity_id'] for r in uncovered)+'。它们保持未覆盖，而非按相邻案例代填通过。','',
        '## 已发现的具体缺口','','音乐目的与层级：整句重音/动机、调式和和声参照、快速转音的目标身份需要具体schema和操作规则；通用context字段可保存文字但不能宣称完整表达。情绪及听者差异：多标签情绪、同一音频不同听者策略和评价对象缺明确任务记录。发声角色：演唱者自反馈遮蔽不能与听者混音掩蔽共用一个解释。双音/泛音：被增强谐波的第二听觉音高与多个独立F0的源数不能混为一类。F应补上下文/关系字段并保留开放候选，不为达到100%把它们塞入其它/残差。','',
        '真实音频测量缺口保留：高F0共振、pulse jitter/shimmer、辅音/双元音内部动作、跨字/句连接、声断与响度/空间。结构能够保存unknown，不意味着检测器已经可靠或已有标签覆盖所有维度。','',
        '## 标签与来源纠错','','原5个位置标签及接受抱C不扩展为整曲；可以不补成完全无破音，都一样不补成三处均正常，全部没区别只否定该剂量/条件的可感知差别。果反馈的好像和响度下降位置未知保留。313字不是正常样本，作者+、AP/SP、note时长及音区不是声音质量标签。','',
        '冻结U17误写word-282；原反馈JSON明确word295_unknown_retained=true，本次增补word295身份勘误及SHA。冻结清单原字节不改、仍42项、标签仍unknown。表2conditional-responses.json的部分文字已有乱码；不自动改旧表/记录，E的反馈词从可读原报告核查，数值ID/已存音频SHA独立引用。F正式整合前必须公开或纠正派生文字，不能把乱码再当原话。','',
        '## 逐项映射','','| 案例 | 角色/分区 | 候选对象 | 结构状态 | 缺口 |','|---|---|---|---|']
    for r in rows:report.append(f'| {r["case_id"]} {r["description"]} | {r["role"]}/{r["review_partition"]} | {", ".join(r["candidate_entity_refs"])} | {r["structure_status"]} | {r["gap_code"]} |')
    report+=['','## 研究来源与适用范围','']
    for source in frozen['sources']:report.append(f'- [{source["id"]} {source["title"]}]({source["url"]})：{source["locator"]}；{source["read_status"]}；{source["scope"]}。')
    report+=['','下一步F整合正式修订、ID迁移及第一/第二层引用，保留原证据/SHA和上述缺口。测量与描述覆盖不代替听者，新因果试听按后续表2冻结方案推进。[当前计划](../../../plan.md)、[执行审计](table1-execution-audit.json)。','']
    (OUT/'table1-coverage-review.md').write_text('\n'.join(report),encoding='utf-8')
    print(json.dumps(dict(status=payload['status'],**counters)))

if __name__=='__main__':main()
