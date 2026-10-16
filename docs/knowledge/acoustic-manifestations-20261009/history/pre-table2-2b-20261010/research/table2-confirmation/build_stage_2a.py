"""Audit explicit historical bindings by bytes; never infer or decode audio.

Current records remain unchanged. Arrays and waveforms are streamed only for
SHA verification, and are never copied into public documents.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from stage_2a_review_data import FINDINGS, GROUPS, NOTES, RESPONSE_GROUP

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: json.dumps(r[k], ensure_ascii=False, sort_keys=True) if isinstance(r.get(k),(dict,list)) else str(r[k]) if k in r else '' for k in fields} for r in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    args = ap.parse_args()
    run = args.run.resolve()
    assert run.is_relative_to(ROOT / 'runs/research') and (run/'observations/freeze-binding.json').is_file()
    binding = load(HERE/'stage_2a_baseline_binding.json')
    assert load(run/'observations/freeze-binding.json') == binding
    assert sha(ROOT/binding['manifest_path']) == binding['manifest_sha256']
    freeze = load(ROOT/binding['manifest_path'])
    entries = {r['path']:r for r in freeze['files']}
    for ref in entries.values():
        assert sha(ROOT/ref['snapshot_path']) == ref['sha256']
        if ref['path'].startswith('docs/'):
            assert sha(ROOT/ref['path']) == ref['sha256'], 'Current post-F documents changed; new stage/version needed'
    def frozen(name):
        return ROOT/entries[(OUT/name).relative_to(ROOT).as_posix()]['snapshot_path']
    ledger = load(frozen('conditional-responses.json'))
    formal = load(frozen('table1-consolidation.json'))
    for ref in formal['artifacts']:
        assert sha(ROOT/ref['path']) == ref['sha256'], ref['path']
    sources = []
    for ref in freeze['source_files']:
        path = ROOT/ref['path']
        got = sha(path) if path.is_file() else None
        assert got == ref['sha256'], ref['path']
        sources.append(dict(**ref, hash_status='verified' if got else 'unavailable_candidate_locator',
            actual_sha256=got))
    assert all(r['hash_status']=='verified' for r in sources if r['origin']=='original_table2_source_audit')

    # Verify only files explicitly declared by each sealed manifest. No directory
    # search, cache selection, model loading, audio analysis or historical edits.
    checks = []
    memo = {}
    def check(raw, expected, base, role):
        path = Path(raw)
        if not path.is_absolute():
            path = base/path
        path = path.resolve()
        if not path.is_relative_to(ROOT):
            return dict(role=role, path='external-resource/'+path.name, expected_sha256=expected,
                status='historical_binding_only_external_not_reopened')
        name = path.relative_to(ROOT).as_posix()
        if name not in memo:
            memo[name] = sha(path) if path.is_file() else None
        got = memo[name]
        status = 'verified' if got == expected else 'unavailable' if got is None else 'mismatch'
        result = dict(role=role, path=name, expected_sha256=expected, actual_sha256=got, status=status)
        checks.append(result)
        return result
    sealed = {}
    for group, spec in GROUPS.items():
        base = ROOT/spec['run']
        manifest_path = base/'completion_manifest.json'
        manifest = load(manifest_path)
        files = manifest.get('files',manifest.get('files_sha256'))
        assert isinstance(files,dict)
        records = [check(raw,expected,base,group+':sealed_manifest') for raw,expected in files.items()]
        assert all(r['status'] == 'verified' for r in records), (group,[r for r in records if r['status']!='verified'])
        sealed[group] = dict(manifest=manifest_path.relative_to(ROOT).as_posix(), sha256=sha(manifest_path),
            declared_files=len(files), verified_files=len(records), current_hashes_verified=True,
            scope='Only declared sealed files; does not certify runtime execution or method accuracy', records=records)
    # Correct the pre-audit optional locator without altering frozen bytes.
    correction_path = ROOT/'runs/lastpage_guo_register_probe_20261008/preservation_check.json'
    correction_check = next(r for r in sealed['GUO']['records'] if r['path']==correction_path.relative_to(ROOT).as_posix())
    sources.append(dict(path=correction_check['path'],sha256=correction_check['expected_sha256'],actual_sha256=correction_check['actual_sha256'],
        available_at_freeze=True,origin='sealed_GUO_manifest_locator_correction',hash_status='verified'))
    source_lookup = {r['path']:r for r in sources}
    def source_ref(name):
        ref = source_lookup[name]
        assert ref['hash_status']=='verified',name
        return dict(path=name,sha256=ref['sha256'])
    # Historical runtime registries are compared with the shared table by
    # normalized identity, not reopened or asserted to represent today's install.
    shared = ledger['runtime_hash_bindings']
    runtime_rows = []
    for group,spec in GROUPS.items():
        name = spec['run']+'/'+spec['runtime']
        registry = load(ROOT/name)
        normalized = {}
        for raw,digest in registry.items():
            path = Path(raw)
            if path.is_relative_to(ROOT):
                key = path.relative_to(ROOT).as_posix()
            else:
                # The historical registries use one explicit OpenUtau install root.
                install_root = Path(next(k for k in registry if Path(k).name=='OpenUtau.Core.dll')).parent
                assert path.is_relative_to(install_root),raw
                key = 'external-resource/OpenUtau/'+path.relative_to(install_root).as_posix()
            normalized[key] = digest
        common = set(normalized)&set(shared)
        runtime_rows.append(dict(group=group,source=source_ref(name),declared_entries=len(normalized),
            shared_identical=sorted(k for k in common if normalized[k]==shared[k]),
            shared_different=[dict(resource=k,experiment_sha256=normalized[k],shared_sha256=shared[k]) for k in sorted(common) if normalized[k]!=shared[k]],
            only_experiment=[dict(resource=k,sha256=normalized[k]) for k in sorted(set(normalized)-set(shared))],
            only_shared=sorted(set(shared)-set(normalized)),current_external_files_rehashed=False,current_execution_verified=False))
    cohort = load(ROOT/GROUPS['BREC']['run']/'cohort.json')
    feedback_group = load(ROOT/GROUPS['BREC']['feedback'])
    cases = {r['id']:r for r in cohort['cases']}
    feedback_cases = {r['id']:r for r in feedback_group['conditions']}
    rows = []
    for record in ledger['responses']:
        rid = record['id']; group = RESPONSE_GROUP[rid]; spec = GROUPS[group]; base = ROOT/spec['run']
        feedback = load(ROOT/spec['feedback'])
        project_checks = []
        if group == 'BREC':
            case = cases[record['condition']['id']]
            assert case['relative_dir'].endswith('_grid5')
            for variant in ['A','B']:
                assert case[variant+'_sha256']==record['bindings']['project_'+variant]
                project_checks.append(check(case[variant+'_path'],case[variant+'_sha256'],base,'project_'+variant))
            variant_base = base/case['relative_dir']
            feedback_audio = feedback_cases[case['id']]['audio']
            listener_checks = [check(v['path'],v['sha256'],base,'listener_'+k) for k,v in feedback_audio.items()]
            assert feedback_audio['A']['sha256']==record['bindings']['delivered_audio']['A']['sha256']
            assert feedback_audio['B']['sha256']==record['bindings']['delivered_audio']['B']['sha256']
            verbatim = feedback['user_verbatim']; feedback_shared='BREC-six-conditions-one-summary-feedback'
        else:
            for field,name in spec['projects'].items():
                project_checks.append(check(name,record['bindings'][field],ROOT,field))
            variant_base = base
            listener_checks = [check(spec['listener'],feedback['comparison_sha256'],base,'actual_listener_comparison')]
            assert record['bindings']['delivered_audio'][spec['run']+'/'+spec['listener']] == feedback['comparison_sha256']
            verbatim = feedback['user_verbatim']; feedback_shared='not_a_shared_cohort_summary'
            if group=='SHFC':
                assert verbatim+'；'+feedback['location_user_verbatim'][-1]==record['user_feedback']['verbatim']
            else:
                assert verbatim==record['user_feedback']['verbatim']
        assert verbatim.rstrip('。')==record['user_feedback']['verbatim'].split('；')[0].rstrip('。')
        report_text=(ROOT/record['report']).read_text(encoding='utf-8')
        assert verbatim.rstrip('。') in report_text
        # Trace all deliveries preserved by the table, including ancillary files
        # that were not the user's actually bound comparison.
        deliveries = record['bindings']['delivered_audio']
        delivered = []
        for key,value in deliveries.items():
            delivered.append(check(value['path'],value['sha256'],ROOT,'retained_delivery_'+key) if isinstance(value,dict)
                else check(key,value,ROOT,'retained_delivery'))
        prefix = variant_base.relative_to(ROOT).as_posix()+'/'
        artifacts = [r for r in sealed[group]['records'] if r['path'].startswith(prefix) and
            any(token in r['path'][len(prefix):] for token in ['native_A/','native_B/','native_C/','fresh/']) and
            Path(r['path']).suffix in {'.json','.npz','.wav'} and 'rejected_' not in r['path']]
        assert artifacts and all(v['status']=='verified' for v in artifacts+project_checks+listener_checks+delivered)
        row = dict(record_id=rid,record_type='response',report=source_ref(record['report']),
            comparison_direction=spec['direction'],legacy_comparison_text=record['comparison_direction'],
            reference_variant=spec['reference'],intervention_variant=spec['intervention'],
            project_bindings=project_checks,actual_listener_bindings=listener_checks,retained_delivery_bindings=delivered,
            native_and_fresh_artifact_bindings=artifacts,experiment_manifest_ref=sealed[group]['manifest'],
            runtime_source_ref=source_ref(spec['run']+'/'+spec['runtime']),runtime_currently_revalidated=False,
            feedback_source=source_ref(spec['feedback']),feedback_original_text=verbatim,
            ledger_feedback_text=record['user_feedback']['verbatim'],feedback_shared_group=feedback_shared,
            feedback_submission_timestamp='unknown',listening_device_and_blinding='unknown',
            historical_machine_pending_flags='retained_as_execution_time_state; later_bound_feedback_separate',
            binding_status='verified_declared_files_and_source_links_not_new_execution',
            conclusion_status=record['status'],unknowns=['fine_grained_side_effects_if_unreported','whole_song_acceptance','held_out_generalization','causal_mediator'],
            note=NOTES.get(rid,NOTES['BREC']))
        rows.append(row)
    # Observational and technical records keep different provenance roles.
    related = {
        'OBS-001':['runs/lastpage_guo_positive_comparison_20261008/comparison.json','runs/lastpage_guo_positive_comparison_20261008/feedback.json','runs/lastpage_guo_phoneme_audit_20261008/comparison.json'],
        'OBS-002':['runs/lastpage_cross_condition_study_20261008/study.json','runs/lastpage_shfc_onset_feedback_20261008/feedback.json'],
        'AUD-001':['runs/lastpage_guo_phoneme_audit_20261008/audit.json','runs/lastpage_guo_phoneme_audit_20261008/comparison.json'],
        'AUD-002':['runs/lastpage_shfc_probe_20261008/intervention.json','runs/lastpage_brec_cohort_probe_20261008/cohort.json'],
    }
    for record in ledger['observations']+ledger['audits']:
        rid=record['id']; artifact_checks=[]; external_count=0
        for name in related[rid]:
            data=load(ROOT/name)
            for raw,expected in data.get('bindings',{}).items():
                value=check(raw,expected,ROOT,'related_'+rid)
                if value['status']=='historical_binding_only_external_not_reopened':external_count+=1
                else:artifact_checks.append(value)
        rows.append(dict(record_id=rid,record_type='observation' if rid.startswith('OBS') else 'technical_audit',
            report=source_ref(record['report']),comparison_direction=record.get('comparison_direction','not_an_effect_comparison'),
            related_sources=[source_ref(name) for name in related[rid]],artifact_bindings=artifact_checks,
            unavailable_or_mismatch=[r for r in artifact_checks if r['status']!='verified'],external_declared_not_reopened=external_count,
            binding_status='reviewed_with_explicit_scope_not_new_effect_validation',new_causal_or_listener_evidence=False,
            note=NOTES[rid]))
    assert len(rows)==14
    # Feedback and identity binding for the observed middle guo clip.
    guo_feedback=load(ROOT/'runs/lastpage_guo_positive_comparison_20261008/feedback.json')
    guo_clips=load(ROOT/'runs/lastpage_guo_phoneme_audit_20261008/comparison.json')
    assert guo_feedback['word295_unknown_retained'] and guo_feedback['accepted_clip']['word']==247
    clip_path=ROOT/'runs/lastpage_guo_phoneme_audit_20261008/guo_original_2.wav'
    guo_listener=[check(clip_path,guo_feedback['accepted_clip']['file_sha256'],ROOT,'OBS-001:accepted_middle_clip'),
        check(ROOT/'runs/lastpage_guo_phoneme_audit_20261008/three_guo_original_vocal.wav',guo_feedback['playlist_sha256'],ROOT,'OBS-001:original_playlist')]
    assert guo_clips['playlist_sha256']==guo_feedback['playlist_sha256'] and all(r['status']=='verified' for r in guo_listener)
    rows[10]['actual_listener_bindings']=guo_listener
    rows[10]['feedback_original_text']=guo_feedback['user_text']
    protected=load(ROOT/'research/table1-confirmation/protected-inputs.json')
    protected_checks=[check(r['path'],r['sha256'],ROOT,'repository_protected') for r in protected['files']]
    assert len(protected_checks)==67 and all(r['status']=='verified' for r in protected_checks)
    # A second uncached hash pass protects against changes during this audit.
    assert all((sha(ROOT/name) if (ROOT/name).is_file() else None)==value for name,value in memo.items())
    for ref in sources:
        if ref['sha256'] is not None:assert sha(ROOT/ref['path'])==ref['sha256']
    write_json(run/'observations/artifact-checks.json',dict(checks=checks,unique_reopened_repository_paths=len(memo),second_uncached_pass_exact=True,
        audio_bytes_hashed_only=True,audio_decoded_or_remeasured=False,model_execution=False))
    public_sealed=[{k:v for k,v in s.items() if k!='records'}|dict(group=g) for g,s in sealed.items()]
    result=dict(date='2026-10-10',stage='2A',status='source_binding_audit_complete_with_explicit_gaps',
        frozen_baseline=binding,rows=rows,runtime_registry_comparisons=runtime_rows,sealed_manifests=public_sealed,
        source_bindings=sources,findings=FINDINGS,original_record_files_unchanged=True,
        original_36_sources_verified=True,audio_hashed_only_not_decoded_or_listened=True,
        no_new_synthesis_or_knowledge_rule=True,no_original_report_project_skill_change=True,
        counts=dict(records=14,responses=10,observations=2,technical_audits=2,experiment_designs=5,
            frozen_documents=len(entries),frozen_source_candidates=52,source_candidates_verified=sum(r['hash_status']=='verified' for r in sources),
            misnamed_optional_locator=1,sealed_files_verified=sum(s['verified_files'] for s in sealed.values()),
            unique_repository_paths_rehashed=len(memo),protected_inputs=67,findings=len(FINDINGS)),
        remaining_stage_status={'2B':'not_executed','2C':'not_executed','2D_to_2H':'not_executed'},
        limitations=['SHA equality identifies bytes, not successful inference or auditory improvement.',
            'Runtime metadata checked per design; actual current external runtime/model resources not reopened.',
            '2A links sources and valid versions; mathematical/isolation/metric reconfirmation belongs to 2C.',
            'Fine listener tasks/timestamp/device/blinding remain unknown; no new feedback requested.'])
    write_json(OUT/'comparison-bindings.json',result)
    write_csv(OUT/'comparison-bindings.csv',rows)
    write_json(OUT/'table2-record-differences.json',dict(date='2026-10-10',rows=FINDINGS,original_records_unchanged=True))
    write_csv(OUT/'table2-record-differences.csv',FINDINGS)
    lines=['# 表2来源与版本绑定审计：2A','',
        '2026-10-10。2A为source_binding_audit_complete_with_explicit_gaps。冻结F后的17份现行文档，逐条审计10干预/2关联/2技术记录。只确认来源/版本/文件绑定，2B字段修订和2C隔离/指标结论复核尚未执行。未生成或解码音频、运行模型、改歌曲/Skill、申请新试听或启用远端CI。既有音频/数组只读取字节计算SHA，不作新的声学测量。','',
        '[完整绑定JSON](comparison-bindings.json)、[CSV](comparison-bindings.csv)、[差异JSON](table2-record-differences.json)、[差异CSV](table2-record-differences.csv)和[原字节快照清单](history/pre-table2-2a-20261010/snapshot-manifest.json)。原表2CSV/JSON/Markdown、F产物与原报告未改；原SHA和此版SHA分开保存。当前执行状态以[根目录计划](../../../plan.md)为准，F产物里的表2未执行为F完成时状态。','',
        '## 已核对的范围','',
        f'原36来源均保持SHA，补列实际反馈/音素/接受与运行清单来源。五份封存manifest共{result["counts"]["sealed_files_verified"]}条文件声明逐一字节核对；67份保护输入保持。完整SHA检查和第二次无缓存复核在本批ignored run，公开文件只含有限路径/绑定摘要，不复制数组/波形。SHA一致不代表重新推理、重新解码PCM、复测F0或人工重听。','',
        '| 记录 | 比较/来源角色 | 核对结果与边界 |','|---|---|---|']
    for row in rows:
        note=row['note'].replace('|','/').replace('\n',' ')
        lines.append(f'| {row["record_id"]} | {row["comparison_direction"]} | {note} |')
    lines+=['','## 版本与原话差异','']
    for item in FINDINGS:
        lines.append(f'- {item["id"]}：{item["finding"]} {item["action"]}')
    lines+=['','## 逐实验runtime范围','','| 设计 | 历史清单项数 | 与共享清单相同 | 共有但值不同 | 仅本设计 | 共享中未在本设计列出 |','|---|---:|---:|---:|---:|---:|']
    for row in runtime_rows:
        lines.append(f'| {row["group"]} | {row["declared_entries"]} | {len(row["shared_identical"])} | {len(row["shared_different"])} | {len(row["only_experiment"])} | {len(row["only_shared"])} |')
    lines+=['','上述清单SHA/交集只确认历史记录。TENC包含工程/Skill/当时源码等混合依赖，范围与其余47项不同；共享组名不能抹去诊断桥/资源范围差异。本轮没有重新哈希当前外部模型/安装或执行设备，因此不将缺列补成相同、不将旧源码路径当作现行执行证明。','',
        '旧pending/自然度未验收标志保留原时间角色，后续用户反馈保持优先范围；六条件BREC共一次汇总回报。抱C局部可用、果SHFC否决、TENC与BREC无感知改善结论保持；word295、313未知字、细分副作用与整曲/泛化状态不升级。','',
        '下一步2B修订比较/版本/基底/下游与反馈状态字段，再由2C逐项复核隔离声明、指标来源及结论范围。新的因果试听须经2D冻结且进入2E执行范围，本轮不自动开展。[专项计划](../../../plan-table2.md)、[研究构建说明](../../../research/table2-confirmation/README.md)。','']
    (OUT/'table2-review.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(status=result['status'],counts=result['counts'])))


if __name__ == '__main__':
    main()
