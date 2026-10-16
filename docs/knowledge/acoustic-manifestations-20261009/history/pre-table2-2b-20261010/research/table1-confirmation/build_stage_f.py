"""Canonical document builder from SHA-bound A–E reviews and pre-F bytes.

Only schema/reference migration; no audio, models, songs or Skill execution.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from frozen_inputs import original_path
from stage_f_context_data import context_fields, families

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'docs/knowledge/acoustic-manifestations-20261009'
DATE='2026-10-10'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def old(name):return original_path(OUT/name)
def read_csv(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_json(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def write_csv(name,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerows({k:json.dumps(r[k],ensure_ascii=False,sort_keys=True) if isinstance(r.get(k),(list,dict)) else str(r[k]) if k in r else '' for k in fields} for r in rows)

def all_strings(v):
    if isinstance(v,str):yield v
    elif isinstance(v,list):
        for x in v:yield from all_strings(x)
    elif isinstance(v,dict):
        for x in v.values():yield from all_strings(x)

def main():
    baseline=load(HERE/'stage_f_baseline_binding.json')
    assert sha(ROOT/baseline['manifest_path'])==baseline['manifest_sha256']
    for r in baseline['files']:assert sha(ROOT/r['snapshot_path'])==r['sha256']
    a=load(old('table1-row-review.json'));b=load(old('core-definition-review.json'))
    c=load(old('control-details.json'));d=load(old('measurement-protocols.json'));e=load(old('description-coverage.json'))
    assert c['counts']['parameters']==352 and len(d['rows'])==50 and e['counts']['case_count']==42
    before=load(old('knowledge-table.json'));proposal=load(old('id-migration.json'))
    ledger=load(old('conditional-responses.json'))
    dimension={r['legacy_id']:list(r['proposed_ids']) for r in a['rows']}
    dimension['P1'].append('PER:P1');dimension['L3'].append('ACO:L5');dimension['L4'].append('ACO:L5')
    lookup={r['candidate_entity_id']:r for r in d['rows']}
    formal_ids=set(lookup)-{'CAND:MULTI_F0'};assert len(formal_ids)==49
    definitions={r['legacy_id']:r for r in b['rows']}
    entities=[]
    for key,r in lookup.items():
        if key not in formal_ids:continue
        linked=[v for v in e['rows'] if key in v['candidate_entity_refs']]
        row=dict(id=key,name=r['name'],entity_type=key.split(':')[0],legacy_ids=r['legacy_ids'],
            operation_definition=r['observation_object'],input_requirements=r['input_requirements'],
            includes=r['method_or_formula'],excludes=r['unknown_or_refusal'],units=r['units'],clock=r['stage_and_clock'],
            window_and_support=r['window_hop_and_support'],quality_mask=r['quality_mask'],unknown_rule=r['unknown_or_refusal'],
            measurement_protocol_ref=r['id'],source_refs=sorted(set(r['source_refs']+r['inherited_B_component_refs'])),
            legacy_definition_review_refs=r['legacy_ids'],control_family_navigation_refs=families(r['legacy_ids']),
            control_relation_status='navigation_only; not a causal or dose rule; see each PARAM condition/scope',
            definition_checked='reviewed_with_explicit_gaps',source_checked='component_read_levels_retained; no full-method upgrade',
            current_engine_support='not_a_control_entity; parameter support separately scoped',
            code_path_checked=r['implementation_status'],measurement_defined=r['measurement_defined'],measurement_validated=False,
            technical_validation_refs=r['technical_validation_refs'],technical_validation_scope=r['technical_validation_scope'],
            description_coverage_checked='limited_case_mapping_with_gaps' if linked else 'no_case_in_frozen_E_checklist',
            description_case_refs=[v['case_id'] for v in linked],
            auditory_label_status='existing_PER_labels_only; no atom truth/new labels' if key.startswith('PER:') and any(v['user_label_available'] for v in linked) else 'unknown_or_not_a_direct_listener_label',
            required_followup=r['remaining_gap'],formal_registration='registered_record_entity_not_validated_detector')
        assert all(ref.startswith('CTRL:C') for ref in row['control_family_navigation_refs'])
        entities.append(row)
    composites=[]
    for r in load(old('composite-review.json'))['rows']:
        paths={}
        for field in ['candidate_path_A','candidate_path_B']:
            legacy=sorted(set(re.findall(r'(?<![A-Z0-9])(?:P[1-5]|L[1-4]|S[1-6]|R[1-4]|T[1-7]|X[1-5])(?![0-9])',r[field])))
            paths[field+'_refs']={lid:dimension[lid] for lid in legacy}
        composites.append(dict(**r,**paths,legacy_text_namespace='dimension IDs in candidate_path text retained with explicit structured migration',
            formal_registration='descriptor_with_nonexclusive_hypothesis_paths',definition_checked='reviewed_with_explicit_gaps',
            description_coverage_checked='hypothetical_paths_not_independent_E_cases'))
    controls=[]
    for r in read_csv(old('openutau-controls.csv')):
        parameters=[v for v in c['rows'] if v['group_id']==r['id']]
        controls.append(dict(id='CTRL:'+r['id'],legacy_group_id=r['id'],control=r['control'],
            parameter_refs=[v['id'] for v in parameters],parameter_count=len(parameters),
            scope_counts=dict(Counter(v['scope'] for v in parameters)),
            current_engine_support='per_PARAM_conditions; group presence not proof of installed support',
            code_path_checked='frozen_source_review_with_local_gaps',definition_checked='navigation_group_defined',
            response_ids=[x for x in r.get('response_ids','').split(';') if x],
            observation_ids=[x for x in r.get('observation_ids','').split(';') if x],audit_ids=[x for x in r.get('audit_ids','').split(';') if x],
            source_ref='control-details.json',limitation='352 fields include editor metadata, other engines and unsupported upstream paths; no validated dose/auditory direction'))
    assert len(controls)==48 and sum(r['parameter_count'] for r in controls)==352
    ns={k:dict(v) for k,v in proposal['namespaces'].items()}
    ns['dimension']={lid:dict(legacy='legacy_dimension:'+lid,targets=refs,status='applied_schema_split_not_new_observation') for lid,refs in dimension.items()}
    # Preserve old record semantics and values. Canonical reference arrays are
    # schema candidates; no added occurrence, measurement or listening fact.
    linked=[]
    for group in ['responses','observations','audits']:
        for r in ledger[group]:
            legacy=list(r['atomic_ids']);legacy_controls=list(r['control_ids']);legacy_evidence=list(r['evidence_ids'])
            assert legacy and set(legacy)<=set(dimension)
            refs={lid:dimension[lid] for lid in legacy}
            r['legacy_atomic_ids']=legacy;r['atomic_ids']=sorted({v for ids in refs.values() for v in ids})
            r['entity_reference_candidates']=refs
            r['legacy_control_ids']=legacy_controls;r['control_ids']=[ns['control_family'][v] for v in legacy_controls]
            r['legacy_evidence_ids']=legacy_evidence;r['evidence_ids']=[ns['project_evidence'][v] for v in legacy_evidence]
            r['reference_role']='schema_translation_candidates; not assertion each entity was observed or validated'
            linked.append(dict(record_id=r['id'],legacy_atomic_ids=legacy,canonical_reference_candidates=refs,
                canonical_entity_refs=r['atomic_ids'],reference_role=r['reference_role']))
    assert len(linked)==14 and all(v['legacy_atomic_ids'] for v in linked)
    for r in ledger['coverage']:
        r['legacy_control_id']=r['control_id'];r['control_id']='CTRL:'+r['control_id']
    ledger['schema_version']=2
    ledger['formal_reference_migration']=dict(date=DATE,source_sha256=sha(old('conditional-responses.json')),
        evidence_values_and_feedback_unchanged=True,old_ids_preserved_in_legacy_fields=True,no_new_causal_validation=True)
    csv_rows=read_csv(old('conditional-responses.csv'))
    for row,rec in zip(csv_rows,ledger['responses']):
        assert row['id']==rec['id']
        row['legacy_atoms']=row['atoms'];row['atoms']=';'.join(rec['atomic_ids'])
        row['legacy_controls']=row['controls'];row['controls']=';'.join(rec['control_ids'])
        row['reference_role']=rec['reference_role']
    evidence=[dict(**r,legacy_id=r['id']) for r in before['evidence']]
    for r in evidence:r['id']=ns['project_evidence'][r['legacy_id']]
    sources=[dict(**r,legacy_id=r['id']) for r in before['primary_sources']]
    for r in sources:r['id']=ns['source'][r['legacy_id']]
    mechanisms=[dict(**r,legacy_id=r['id']) for r in before['mechanisms']]
    for r in mechanisms:
        r['id']=ns['code_mechanism'][r['legacy_id']]
        r['status']='legacy_mechanism_summary; current_parameter_formula_and_scope_in_C'
    contexts=context_fields()
    quality_strings=list(all_strings(load(old('conditional-responses.json'))))
    assert not any('\ufffd' in s or any(128<=ord(ch)<256 for ch in s) for s in quality_strings)
    original_responses=load(old('conditional-responses.json'))['responses']
    feedback_checks=[]
    for r,row in zip(original_responses,read_csv(old('conditional-responses.csv'))):
        assert r['user_feedback']['verbatim'].rstrip('。')==row['feedback'].rstrip('。')
        report=ROOT/r['report'];assert report.exists()
        terms=r['user_feedback']['verbatim'].rstrip('。').split('；')
        assert all(term in report.read_text(encoding='utf-8') for term in terms)
        feedback_checks.append(dict(record_id=r['id'],verbatim=r['user_feedback']['verbatim'],report=r['report'],sha256=sha(report)))
    correction=dict(date=DATE,status='E_mojibake_claim_corrected; no_file_text_corruption_found',
        inspected_original_sha256=sha(old('conditional-responses.json')),utf8_strict=True,string_values_inspected=len(quality_strings),
        replacement_character_count=0,latin1_nonascii_string_count=0,feedback_report_csv_checks=feedback_checks,
        reason='E tool-output encoding displayed correct Chinese incorrectly; earlier file-corruption claim was not supported by the actual UTF-8 bytes.',
        original_feedback_text_changed=False,E_frozen_claim_retained_in_history=True,
        word295_identity_erratum_still_valid=e['identity_errata'])
    migration=dict(schema_version=2,date=DATE,status='applied_schema_migration_with_explicit_gaps',
        old_id_semantics_preserved=True,baseline_binding='stage_f_baseline_binding.json',namespaces=ns,
        second_layer_links=linked,formal_entity_ids=sorted(formal_ids),
        open_candidates=[dict(id='CAND:MULTI_F0',protocol_ref='MEAS:D50',status='open_not_promoted_to_formal_atomic_entity',
            reason='Independent source count, subharmonics/AM and enhanced harmonic melody remain distinct/unknown; CTX:SOURCE_RELATION records hypotheses')],
        original_proposal_issue='A read atoms instead of atomic_ids; original14 candidate mappings were empty. Actual14 references translated here; historical proposal retained.',
        rule='Typed references and split candidates only; no upgrade of measured/label/causal facts')
    package=dict(schema_version=2,date=DATE,status='formal_record_schema_reviewed_with_explicit_gaps',
        entities=entities,composite_descriptors=composites,controls=controls,context_schema=contexts,
        evidence=evidence,mechanisms=mechanisms,primary_sources=sources,
        original_legacy_registry=dict(path='history/pre-f-20261010/knowledge-table.json',sha256=sha(old('knowledge-table.json'))),
        parameter_catalog=dict(path='control-details.json',count=352,parameter_IDs_preserved=True),
        observation_protocols=dict(path='measurement-protocols.json',formal_entity_protocols=49,open_candidate_protocols=1,all_measurement_validated=False),
        description_coverage=dict(path='description-coverage.json',original_E_counts=e['counts'],uncovered_formal_entities=e['uncovered_candidate_entities']),
        migration='id-migration.json',open_candidates=migration['open_candidates'],source_quality_correction='source-quality-correction.json',
        quality_requires_context_and_listening=True,agent_audio_perception=False,no_new_synthesis=True,
        unknown_preserved=True,second_layer=dict(report='conditional-responses.md',ledger='conditional-responses.json',coverage='response-coverage.csv',no_new_synthesis=True))
    write_csv('atomic-manifestations.csv',entities);write_csv('composite-descriptors.csv',composites);write_csv('openutau-controls.csv',controls)
    write_csv('current-evidence.csv',evidence);write_json('knowledge-table.json',package);write_json('id-migration.json',migration)
    write_json('conditional-responses.json',ledger);write_csv('conditional-responses.csv',csv_rows);write_csv('response-coverage.csv',ledger['coverage'])
    write_json('context-schema.json',dict(date=DATE,rows=contexts,measurement_or_causal_rules=False,unfilled_historical_fields_remain_unknown=True))
    write_json('source-quality-correction.json',correction)
    entry=['# 表1：演唱表现记录、控制导航与既有响应证据','',
        '更新：2026-10-10。A–F本轮固定范围审查与正式整合已完成，状态consolidated_with_explicit_gaps。49个正式分层记录实体、30组多义听感词、48导航组及352具体参数/字段；复音/拍频另列1开放候选。所有测量方法、通用调参方向/剂量及自然度均未获全面验证。Agent没有试听，新音频/歌曲/Skill/安装未改。','',
        '现行机器入口为[knowledge-table.json](knowledge-table.json)，实体/组合词/导航CSV与它一致；[F报告](table1-consolidation-review.md)、[ID迁移](id-migration.json)、[上下文/任务字段](context-schema.json)说明正式范围。原31项/旧ID/旧来源及迁移前全部40文件原字节见[快照清单](history/pre-f-20261010/snapshot-manifest.json)。A–E报告保留阶段时态，以本入口和根目录计划为当前状态。','',
        '## 现行目录','','| 文件 | 范围与边界 |','|---|---|',
        '| [实体](atomic-manifestations.csv) | 24 ACO、15 EVT、9 PER、1 META。信号、时序、听感和元数据分层，不是49个声学标量/检测器 |',
        '| [多义听感词](composite-descriptors.csv) | 30组DESC，两条候选分解及反例；非已验证中文同义/病因映射 |',
        '| [控制导航](openutau-controls.csv) / [具体项](control-details.json) | 48 CTRL组→352 PARAM；当前/其它引擎/上游缺失/编辑数据分栏，组存在不等于本机生效 |',
        '| [观测协议](measurement-protocols.json) | 49实体协议+1开放候选；10组有限数学检查，不等于真实PCM估计性能通过 |',
        '| [描述覆盖](description-coverage.json) / [冻结问题](coverage-checklist.json) | 42问题、34可记录/8部分、16标签行/0完整测量结论；过程复查非音频留出，16正式实体未覆盖 |',
        '| [既有响应](conditional-responses.md) / [JSON](conditional-responses.json) / [CSV](conditional-responses.csv) | 10干预、2关联、2技术审计；14记录类型引用已迁移，原值/反馈/SHA保持 |',
        '| [控制响应覆盖](response-coverage.csv) / [项目证据](current-evidence.csv) | CTRL/EVID引用；有效/无效/副作用范围分开，不产通用配方 |',
        '| [来源与定义](table1-source-review.md) / [逐说法](claim-evidence.json) | 30说法/25来源，B原阅读层级与摘要/范围缺口保持 |',
        '| [本机能力](local-capability-review.json) / [偏好](editor-preferences-review.json) / [节点](graph-node-review.json) | 离线PE/固定源码路径；未读live值、模型/设备未执行 |',
        '| [纠错](source-quality-correction.json) / [审计](table1-execution-audit.json) | E乱码为输出编码误判；原JSON正确，word295身份勘误保留；原基线和现行版本分别校验 |','',
        '## 表1能确认什么','','定义、代码路径、输入/输出观测、描述覆盖和听觉标签分别记录。49项只是实体登记：ACO保存声明方法下的量，EVT保存支持与关系，PER保存原话/呈现/范围，META及CTX保存身份/音乐目标/监听/任务。没有证据的值保持unknown；信号平滑、相同RMS或固定vocoder输入都不能替代声线/发音/自然度验收。','',
        '控制导航只帮助查找实际PARAM字段，不承诺“哪个参数越大越好”。当前剂量的没区别不证明整个通道无效，局部可以不推广整曲，模型VOIC/BREC/TENC/SHFC不是人体量或听感的唯一解释。','',
        '## 仍需确认的范围','','C：未读消费者、非默认执行、开放插件与本机版本差异；86冻结来源/六资源绑定不证明所有能力可用。D：真实F0、高F0共振、pulse jitter/shimmer、声源分解、语言边界、复杂响度/空间的方法性能。E：8部分表达项新增任务/关系字段仍缺实际标注，16实体未覆盖，严格等电平异谱和纯人声/混音成对听觉验证仍缺。B：摘要/范围来源与30组假设映射不升级。','',
        '原5位置标签及抱C局部接受保留，313字unknown不变。没有新的听觉标签、跨曲/留出验证或通用真假声/口型配方。后续按[表2专项计划](../../../plan-table2.md)先审计记录，再冻结新因果设计及人工试听；尚未执行。','',
        '## 重建与历史入口','','现行重建使用research/table1-confirmation/build_stage_f.py；A–E构建器正式迁移后拒绝覆盖，原始资料从明确SHA快照读取。原上游源码、作者工程、发布工程、Skill及封存run不改。[研究构建说明](../../../research/table1-confirmation/README.md)、[当前计划](../../../plan.md)、[项目约定](../../../AGENTS.md)。','']
    (OUT/'README.md').write_text('\n'.join(entry),encoding='utf-8')
    report=['# 表1正式整合与引用迁移：阶段F','',
        '2026-10-10。**F为consolidated_with_explicit_gaps**：正式登记49个分层记录实体（24 ACO、15 EVT、9 PER、1 META），30组听感词及48导航组/352具体项，另保留复音/拍频1个开放候选。这是可追溯记录结构，全部measurement_validated仍false，不是完整检测器、通用调参规律或自然度验收。','',
        '现行[JSON总表](knowledge-table.json)、[实体CSV](atomic-manifestations.csv)、[组合词CSV](composite-descriptors.csv)、[控制导航CSV](openutau-controls.csv)、[上下文/任务字段](context-schema.json)与[ID迁移](id-migration.json)。原40文件按原字节存于[迁移前快照清单](history/pre-f-20261010/snapshot-manifest.json)，snapshot链接按原路径解释；A–E报告为当时证据，不覆盖现行状态。','',
        '## 迁移范围','','- 31个旧描述ID有明确分层去向；增加周期shimmer/感知音高，复音/拍频保持开放，不强制变成第50个正式实体。旧含义存legacy字段/快照，旧S1来源与声学对象使用独立命名空间。',
        '- 30组词使用DESC、48组用CTRL、源码摘要用CODE、项目证据用EVID、旧来源用SRC；CLAIM/DSRC/ESRC来源的原阅读层级保留，PARAM/MEAS/CASE ID保持。',
        '- 14条RESP/OBS/AUD现在从实际atomic_ids读取，逐个旧ID保留候选去向。A旧提案误读atoms而生成14条空关联，本次公开纠正。展开后的引用仅结构翻译，不称各声学/感知对象均被测到。',
        '- 第二层原数值、干预、状态、原话、报告/工程/音频SHA及runtime绑定精确保持；只迁移类型明确的引用并附legacy字段。没有重查波形、模型或新因果试验。','',
        '## E缺口如何处理','','8组上下文/任务字段记录层级/重音、调律参照、装饰目标序列、参与/目标角色、多标签情绪、谐波/感知音高关系及取样范围。字段定义完成不代表历史材料已补齐，更不让E的8部分表达项自动变为通过。E42案例、34可记录/8部分、16标签行/0完整测量结论不变；16个正式实体未被该清单覆盖。','',
        'C的未读消费者/非默认分支/开放插件与本机缺失保持；D的真实F0/共振、pulse/声源分解、边界与响度/空间验证缺口保持；B摘要/范围级资料和30组多义映射仍不能升级为全部证实。','',
        '## 公开纠错','','E所称表2派生文字乱码为工具输出编码误判。原JSON严格UTF-8解析，SHA与基线一致；1174字符串无U+FFFD/Latin1异常，10条原话与可读报告/CSV逐项对应。没有把正确原文做猜测性转码，见[纠错与报告绑定](source-quality-correction.json)。E冻结记录原字节保留，当前入口以此纠错为准。U17冻结word282误写→word295勘误仍有效，听感unknown不变。','',
        '## 重建与验收边界','','现行文件由research/table1-confirmation/build_stage_f.py从明确SHA绑定的迁移前资料/A–E产物生成；A–E构建器在正式迁移后拒绝覆盖。执行审计分别核对原历史基线、当前CSV/JSON、ID/来源、第二层去除迁移字段后的原记录等式及67份保护输入；不通过更新哈希绕过历史证据。','',
        '表1本轮按当前固定范围收口并交付缺口清单，不以未知迫使合成或试听。后续表2专项计划尚未执行；先做已授权记录审计，新的因果设计/人工试听按其冻结步骤开展。歌曲、音频、Skill、模型/安装不变，远端CI仍仅手动。[当前计划](../../../plan.md)、[执行审计](table1-execution-audit.json)。','']
    (OUT/'table1-consolidation-review.md').write_text('\n'.join(report),encoding='utf-8')
    # Retain the original readable conditions, timing, measured responses and
    # qualifications; the reference migration must not remove those summaries.
    readable=old('conditional-responses.md').read_text(encoding='utf-8')
    readable=readable.replace('日期：2026-10-09。','更新：2026-10-10（F正式引用迁移；表2专项尚未执行）。',1)
    old_link_text='两表以C控制ID、P/L/S/R/T/X表现ID、E原证据ID关联；第二层再使用RESP/OBS/AUD独立编号。原表只增加关联索引，原编号保留。'
    assert old_link_text in readable
    readable=readable.replace(old_link_text,'两表现以CTRL控制导航、ACO/EVT/PER/META分层实体及EVID项目证据关联；RESP/OBS/AUD编号保持。旧维度候选去向与legacy引用见文末迁移表及id-migration.json，不表示每个展开实体已被观测。')
    readable=readable.replace('C47只有','CTRL:C47只有')
    readable+='\n## F类型引用迁移\n\n仅引用结构变更，原值/反馈/工程与音频SHA保持。原版字节见[迁移前快照清单](history/pre-f-20261010/snapshot-manifest.json)；[ID迁移](id-migration.json)保存旧ID及候选去向。E关于乱码的判断为工具显示编码误判，原UTF-8文字正确，未转码；U17 word295身份勘误仍有效，见[纠错](source-quality-correction.json)。\n\n'
    readable+='| 记录 | 旧维度ID | 分层实体引用候选 | 来源 |\n|---|---|---|---|\n'
    for rec in ledger['responses']+ledger['observations']+ledger['audits']:
        readable+=f'| {rec["id"]} | {", ".join(rec["legacy_atomic_ids"])} | {", ".join(rec["atomic_ids"])} | [原报告](../../../{rec["report"]}) |\n'
    (OUT/'conditional-responses.md').write_text(readable,encoding='utf-8')
    consolidation=dict(schema_version=1,date=DATE,stage='F',status='consolidated_with_explicit_gaps',formal_entities=49,
        entity_types=dict(Counter(r['entity_type'] for r in entities)),open_candidates=1,descriptors=30,control_groups=48,parameters=352,context_groups=8,
        migrated_records=14,all_historical_values_and_feedback_preserved=True,baseline_manifest=baseline,
        A_empty_mapping_issue_corrected=True,E_encoding_claim_corrected=True,
        all_measurement_validated=False,universal_completeness_validated=False,no_new_auditory_labels=True,no_new_synthesis=True,
        no_project_skill_audio_production_or_installation_change=True,table2_special_plan_status='not_executed',
        artifacts=[dict(path=(OUT/n).relative_to(ROOT).as_posix(),sha256=sha(OUT/n)) for n in [
            'atomic-manifestations.csv','composite-descriptors.csv','openutau-controls.csv','current-evidence.csv','knowledge-table.json',
            'id-migration.json','conditional-responses.json','conditional-responses.csv','conditional-responses.md','response-coverage.csv',
            'context-schema.json','source-quality-correction.json','table1-consolidation-review.md','README.md']])
    write_json('table1-consolidation.json',consolidation)
    print(json.dumps(dict(status=consolidation['status'],entities=49,open_candidates=1,parameters=352,records=14)))

if __name__=='__main__':main()
