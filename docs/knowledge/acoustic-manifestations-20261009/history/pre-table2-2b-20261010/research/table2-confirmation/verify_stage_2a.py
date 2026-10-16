"""Independent source/record consistency checks; no waveform decoding."""
import argparse
import ast
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'docs/knowledge/acoustic-manifestations-20261009'


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def csv_matches(path, rows):
    assert path.read_bytes().startswith(b'\xef\xbb\xbf')
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);actual=list(reader);fields=reader.fieldnames
    expected=[{k:json.dumps(r[k],ensure_ascii=False,sort_keys=True) if isinstance(r.get(k),(dict,list)) else str(r[k]) if k in r else '' for k in fields} for r in rows]
    assert actual==expected,path.name


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--local-checks',action='store_true')
    args=ap.parse_args();run=args.run.resolve()
    assert run.is_relative_to(ROOT/'runs/research')
    binding=load(HERE/'stage_2a_baseline_binding.json')
    assert sha(ROOT/binding['manifest_path'])==binding['manifest_sha256']
    freeze=load(ROOT/binding['manifest_path'])
    for r in freeze['files']:
        assert sha(ROOT/r['snapshot_path'])==r['sha256']
        if r['path'].startswith('docs/'):assert sha(ROOT/r['path'])==r['sha256']
    audited=load(OUT/'comparison-bindings.json');rows=audited['rows']
    current=load(OUT/'conditional-responses.json')
    ledger_rows=current['responses']+current['observations']+current['audits']
    assert [r['record_id'] for r in rows]==[r['id'] for r in ledger_rows]
    assert len(rows)==14 and audited['counts']['responses']==10 and audited['counts']['observations']==2 and audited['counts']['technical_audits']==2
    assert audited['status']=='source_binding_audit_complete_with_explicit_gaps'
    assert audited['original_record_files_unchanged'] and audited['no_new_synthesis_or_knowledge_rule']
    assert all(v=='not_executed' for v in audited['remaining_stage_status'].values())
    assert sum(r['declared_files'] for r in audited['sealed_manifests'])==896
    assert all(r['verified_files']==r['declared_files'] for r in audited['sealed_manifests'])
    source_table={r['path']:r for r in audited['source_bindings']}
    original=load(OUT/'response-source-audit.json')['source_files']
    assert len(original)==36
    for r in original:assert source_table[r['path']]['sha256']==sha(ROOT/r['path'])==r['sha256']
    assert sum(r['hash_status']=='verified' for r in source_table.values())==52
    for r in source_table.values():
        if r['hash_status']=='verified':assert sha(ROOT/r['path'])==r['sha256']
        else:assert r['path']=='runs/lastpage_guo_register_probe_20261008/native_isolation.json' and r['sha256'] is None and not (ROOT/r['path']).exists()
    for row,record in zip(rows,ledger_rows):
        assert row['report']['path']==record['report']
        assert sha(ROOT/row['report']['path'])==row['report']['sha256']
        if row['record_type']=='response':
            assert row['conclusion_status']==record['status']
            assert row['ledger_feedback_text']==record['user_feedback']['verbatim']
            assert row['feedback_submission_timestamp']=='unknown'
            assert row['listening_device_and_blinding']=='unknown'
            assert sha(ROOT/row['feedback_source']['path'])==row['feedback_source']['sha256']
            for item in row['project_bindings']+row['actual_listener_bindings']+row['retained_delivery_bindings']+row['native_and_fresh_artifact_bindings']:
                assert item['status']=='verified' and item['actual_sha256']==item['expected_sha256']
            assert row['native_and_fresh_artifact_bindings']
    by_id={r['record_id']:r for r in rows}
    onset=by_id['RESP-003']
    assert onset['comparison_direction']=='C-B' and 'reused waveform' in onset['reference_variant']
    assert onset['actual_listener_bindings'][0]['path'].endswith('/B_C_vocal.wav')
    guo=by_id['RESP-004']
    assert 'accepted bao C' in guo['reference_variant']
    assert guo['project_bindings'][0]['expected_sha256']==onset['project_bindings'][-1]['expected_sha256']
    brec=rows[4:10]
    assert len({r['feedback_shared_group'] for r in brec})==1
    assert len({r['feedback_source']['sha256'] for r in brec})==1
    assert all(r['feedback_original_text']=='全部没区别。' for r in brec)
    assert all('_grid5/' in item['path'] for r in brec for item in r['project_bindings']+r['native_and_fresh_artifact_bindings'])
    runtime={r['group']:r for r in audited['runtime_registry_comparisons']}
    assert runtime['TENC']['declared_entries']==58 and len(runtime['TENC']['shared_identical'])==6
    assert len(runtime['TENC']['only_shared'])==41 and not runtime['TENC']['shared_different']
    for group in ['SHFC','ONSET','GUO','BREC']:
        r=runtime[group]
        assert r['declared_entries']==47 and len(r['shared_identical'])==47 and not r['only_experiment'] and not r['only_shared'] and not r['shared_different']
    assert all(not r['current_external_files_rehashed'] and not r['current_execution_verified'] for r in runtime.values())
    checks=load(run/'observations/artifact-checks.json')
    assert checks['second_uncached_pass_exact'] and not checks['audio_decoded_or_remeasured'] and not checks['model_execution']
    unique={r['path']:r for r in checks['checks']}
    assert len(unique)==checks['unique_reopened_repository_paths']==audited['counts']['unique_repository_paths_rehashed']
    assert all(r['status']=='verified' for r in checks['checks'])
    # Recheck all declared repository paths independently of the builder's cache.
    for name,r in unique.items():assert sha(ROOT/name)==r['expected_sha256']==r['actual_sha256']
    findings=load(OUT/'table2-record-differences.json')['rows']
    assert findings==audited['findings'] and len(findings)==7
    ids={r['record_id'] for r in rows}
    assert len({r['id'] for r in findings})==7
    assert all(set(r['records'])<=ids for r in findings)
    csv_matches(OUT/'comparison-bindings.csv',rows)
    csv_matches(OUT/'table2-record-differences.csv',findings)
    protected=load(ROOT/'research/table1-confirmation/protected-inputs.json')['files']
    assert len(protected)==67 and all(sha(ROOT/r['path'])==r['sha256'] for r in protected)
    formal=load(OUT/'table1-consolidation.json')
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in formal['artifacts'])
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert ci.split('on:',1)[1].split('jobs:',1)[0].strip()=='workflow_dispatch:'
    links=0
    for p in [ROOT/'README.md',ROOT/'plan.md',ROOT/'plan-table2.md',ROOT/'AGENTS.md',HERE/'README.md',OUT/'table2-review.md']:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):continue
            assert (p.parent/target.split('#')[0]).exists(),(p,target)
            links+=1
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    artifacts=[OUT/n for n in ['comparison-bindings.json','comparison-bindings.csv','table2-record-differences.json','table2-record-differences.csv','table2-review.md']]
    artifacts+=list(HERE.glob('*.py'))+[HERE/'README.md',HERE/'stage_2a_baseline_binding.json',run/'observations/artifact-checks.json']
    artifacts+=[ROOT/name for name in ['AGENTS.md','README.md','plan.md','plan-table2.md']]
    result=dict(date='2026-10-10',stage='2A',status='passed',records=14,frozen_documents=17,source_bindings_verified=52,
        sealed_manifest_files_verified=896,unique_repository_paths_rehashed=len(unique),protected_inputs_verified=67,document_links_checked=links,
        csv_json_exact=True,current_post_F_originals_unchanged=True,no_original_experiment_report_project_skill_change=True,
        no_audio_decoding_measurement_listening_or_model_execution=True,CI_manual_only=True,
        verification_run=run.relative_to(ROOT).as_posix(),
        artifacts=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in artifacts])
    if args.local_checks:
        tests=run/'logs/pytest.txt';gate=run/'logs/worktree-check.txt'
        text=tests.read_text(encoding='utf-8-sig')
        assert re.search(r'\b88 passed\b',text) and not re.search(r'\b(?:failed|errors)\b',text)
        gate_data=load(gate)
        assert gate_data['checks']=='passed' and gate_data['audio_payloads']==0 and gate_data['author_projects']==3 and gate_data['zip_members']==5
        result['local_verification']=dict(pytest='88 passed',worktree_gate=gate_data,new_TEMP_TMP_and_pytest_directory=True,
            logs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in [tests,gate]])
        repeat_path=run/'observations/exact-rebuild.json';repeat=load(repeat_path)
        assert repeat['status']=='passed' and repeat['exact'] and repeat['count']==5
        assert all(sha(OUT/name)==digest for name,digest in repeat['artifact_sha256'].items())
        assert set(repeat['artifact_sha256'])=={'comparison-bindings.json','comparison-bindings.csv','table2-record-differences.json','table2-record-differences.csv','table2-review.md'}
        result['local_verification']['exact_rebuild']=dict(files=5,path=repeat_path.relative_to(ROOT).as_posix(),sha256=sha(repeat_path))
    (OUT/'table2-execution-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['artifacts','local_verification']}))


if __name__=='__main__':main()
