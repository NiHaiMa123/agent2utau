"""Independent reversible-migration and provenance checks, using metadata only."""
import argparse
import ast
import copy
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
OUTPUTS = ['conditional-responses.json', 'conditional-responses.csv', 'conditional-responses.md',
    'table2-record-schema.json', 'table2-schema-migration.json', 'table2-record-structure.csv', 'table2-fields.md', 'table2-schema-review.md']
MUTABLE = {str(OUT.relative_to(ROOT) / n).replace('\\', '/') for n in ['conditional-responses.json', 'conditional-responses.csv', 'conditional-responses.md', 'README.md']}
MUTABLE.update(['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md',
    'research/table1-confirmation/build_stage_f.py', 'research/table1-confirmation/build_audit.py',
    'research/table2-confirmation/build_stage_2a.py', 'research/table2-confirmation/verify_stage_2a.py',
    'research/table2-confirmation/README.md'])


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def read_csv(p):
    assert p.read_bytes().startswith(b'\xef\xbb\xbf')
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def check_declared_schema(value, schema):
    """Check the keywords used here; not a general JSON Schema implementation."""
    types = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'null': type(None)}
    if 'type' in schema:
        choices = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        assert any(isinstance(value, types[t]) for t in choices)
    if 'const' in schema:
        assert value == schema['const']
    if 'enum' in schema:
        assert value in schema['enum']
    if isinstance(value, dict):
        assert set(schema.get('required', [])) <= value.keys()
        for k, sub in schema.get('properties', {}).items():
            if k in value:
                check_declared_schema(value[k], sub)
    if isinstance(value, list):
        assert len(value) >= schema.get('minItems', 0)
        for item in value:
            if 'items' in schema:
                check_declared_schema(item, schema['items'])
    if isinstance(value, str):
        assert len(value) >= schema.get('minLength', 0)


def pointer(value, path):
    for k in path.strip('/').split('/'):
        value = value[int(k)] if isinstance(value, list) else value[k.replace('~1', '/').replace('~0', '~')]
    return value


def main():
    if (HERE / 'stage_2c_baseline_binding.json').exists():
        raise SystemExit('Stage 2C registered: do not rewrite the historical 2B audit with current confirmation hashes. Use verify_stage_2c.py.')
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--local-checks', action='store_true')
    args = ap.parse_args()
    run = args.run.resolve()
    assert run.is_relative_to(ROOT / 'runs/research')
    binding = load(HERE / 'stage_2b_baseline_binding.json')
    assert sha(ROOT / binding['manifest_path']) == binding['manifest_sha256']
    freeze = load(ROOT / binding['manifest_path'])
    entries = {r['path']: r for r in freeze['files']}
    for r in entries.values():
        assert sha(ROOT / r['snapshot_path']) == r['sha256']
        if r['path'] not in MUTABLE:
            assert sha(ROOT / r['path']) == r['sha256'], r['path']
    def old(name):
        return ROOT / entries[(OUT / name).relative_to(ROOT).as_posix()]['snapshot_path']
    original = load(old('conditional-responses.json'))
    current = load(OUT / 'conditional-responses.json')
    schema = load(OUT / 'table2-record-schema.json')
    assert current['schema_version'] == 3 and original['schema_version'] == 2
    rows = current['responses'] + current['observations'] + current['audits']
    prior_rows = original['responses'] + original['observations'] + original['audits']
    assert len(rows) == 14 and [r['id'] for r in rows] == [r['id'] for r in prior_rows]
    restored = copy.deepcopy(current)
    restored['schema_version'] = 2
    del restored['table2_schema_revision']
    for r in restored['responses'] + restored['observations'] + restored['audits']:
        del r['record_v3']
    assert restored == original, 'Any change to old payload blocks migration'
    # Existing numeric/feedback/status fields, F IDs and SHA bindings are all covered by equality.
    index = {r['id']: r for r in rows}
    comparisons = {}
    params = {r['id'] for r in load(OUT / 'control-details.json')['rows']}
    entities = {r['id'] for r in load(OUT / 'knowledge-table.json')['entities']}
    for r in rows:
        ext = r['record_v3']
        check_declared_schema(ext, schema)
        variant_ids = {v['variant_id'] for v in ext['variants']}
        assert len(variant_ids) == len(ext['variants'])
        for c in ext['comparisons']:
            assert c['comparison_id'] not in comparisons
            assert c['reference_variant'] in variant_ids and c['intervention_variant'] in variant_ids
            assert c['reference_variant'] != c['intervention_variant']
            comparisons[c['comparison_id']] = c
        assert ext['comparison_id'] in comparisons
        assert set(ext['table1_refs']['parameter_ids']) <= params
        assert set(ext['table1_refs']['entity_ids']) <= entities
        assert ext['condition_context']['current_runtime_revalidated'] is False
        for v in ext['variants']:
            assert v['state_origin']['newly_executed_in_2B'] is False
        for metric in ext['metric_bindings']:
            pointer(r, metric['pointer'])
            assert set(metric['comparison_ids']) <= comparisons.keys()
        assert ext['record_confirmation'].endswith('2C_not_executed')
    assert len(comparisons) == 17
    # Rejection checks: the actual schema subset rejects absent comparison/invalid type.
    valid = copy.deepcopy(rows[0]['record_v3'])
    for mutate in [lambda v: v.pop('comparison_id'), lambda v: v.update(record_kind='passed'),
                   lambda v: v['comparisons'][0].update(listener_evidence='true')]:
        invalid = copy.deepcopy(valid)
        mutate(invalid)
        try:
            check_declared_schema(invalid, schema)
        except AssertionError:
            pass
        else:
            raise AssertionError('Malformed schema specimen accepted')
    onset = index['RESP-003']['record_v3']
    assert onset['comparison_id'] == 'RESP-003:C-B'
    av, bv, cv = onset['variants']
    assert av['logical_label'] == 'A' and bv['logical_label'] == 'B' and cv['logical_label'] == 'C'
    assert '/lastpage_shfc_probe_' in bv['state_origin']['artifacts'][0]['path']
    assert '/lastpage_shfc_onset_probe_' in cv['state_origin']['artifacts'][0]['path']
    assert cv['artifact_slot'] == 'B'
    assert onset['condition_context']['baseline_state_variant'] == 'RESP-003:A'
    assert onset['condition_context']['baseline_not_comparator']
    assert not comparisons['RESP-003:C-A']['listener_evidence']
    for m in onset['metric_bindings']:
        if '/F0/' in m['pointer']:
            assert m['operation'] == 'absolute_cents_distance'
            pair = m['pointer'].split('/')[-1].split('_')
            assert m['comparison_ids'] == ['RESP-003:' + pair[1] + '-' + pair[0]]
        elif 'adjacent_frame' in m['pointer']:
            assert not m['comparison_ids'] and len(m['variant_ids']) == 3
    assert index['RESP-004']['record_v3']['variants'][0]['project']['sha256'] == cv['project']['sha256']
    assert 'no_direct_C-A_listening' in index['OBS-002']['record_v3']['feedback_interpretation']['label_evidence']
    rev = current['table2_schema_revision']
    feedbacks = {r['feedback_group_id']: r for r in rev['feedback_groups']}
    assert len(feedbacks) == 6
    cohort = feedbacks['FB:BREC-cohort']
    assert len(cohort['record_ids']) == 6 and len(cohort['audio_bindings']) == 12
    assert cohort['original_text'] == '全部没区别。'
    assert feedbacks['FB:RESP-002']['separate_location_messages'] == ['开头', '抱的字头']
    assert feedbacks['FB:OBS-001']['conflicting_legacy_field']['value'] == 'unknown'
    for r in rows[:12]:
        assert r['record_v3']['feedback_group_id'] in feedbacks
    for r in rows[4:10]:
        assert r['record_v3']['feedback_group_id'] == 'FB:BREC-cohort'
        assert all('_grid5/' in v['project']['path'] for v in r['record_v3']['variants'])
        flags = r['record_v3']['state_timeline'][0]['flags']
        assert flags['listening_pending'] is True
        assert r['measured']['mel_response']['perceived_improvement'] is False
    aud = load(OUT / 'comparison-bindings.json')
    verified_sources = [r for r in aud['source_bindings'] if r['hash_status'] == 'verified']
    for ref in verified_sources:
        assert Path(ref['path']).suffix in ['.json', '.md'], 'Only metadata/doc sources may be read'
        assert sha(ROOT / ref['path']) == ref['sha256']
    assert len(verified_sources) == 52
    maps = {}
    for ref in aud['sealed_manifests']:
        assert sha(ROOT / ref['manifest']) == ref['sha256']
        p = ROOT / ref['manifest']
        data = load(p)
        maps.update({((Path(k) if Path(k).is_absolute() else p.parent / k).relative_to(ROOT).as_posix()): h for k, h in data.get('files', data.get('files_sha256')).items()})
    for r in current['responses']:
        for v in r['record_v3']['variants']:
            for ref in v['state_origin']['artifacts']:
                assert maps[ref['path']] == ref['sha256']  # Metadata lookup, no array/audio read.
    migration = load(OUT / 'table2-schema-migration.json')
    for ref in migration['onset_file_label_mapping']['proof']:
        assert maps[ref['path']] == ref['sha256'] == sha(ROOT / ref['path'])
    pack = (ROOT / migration['onset_file_label_mapping']['proof'][0]['path']).read_text(encoding='utf-8')
    analyze = (ROOT / migration['onset_file_label_mapping']['proof'][1]['path']).read_text(encoding='utf-8')
    assert "('B',OLD/'dynamics_B/phrase_022.f32')" in pack
    assert "('C',ROOT/'dynamics_B/phrase_022.f32')" in pack
    assert "('B',old,'B'),('C',p,'B')" in analyze
    # CSV preserves all original cells and includes machine equivalent extensions.
    csv_new = read_csv(OUT / 'conditional-responses.csv')
    csv_old = read_csv(old('conditional-responses.csv'))
    assert len(csv_new) == len(csv_old) == 10
    for now, prior in zip(csv_new, csv_old):
        assert {k: now[k] for k in prior} == prior
        assert json.loads(now['record_v3']) == index[now['id']]['record_v3']
    structured = read_csv(OUT / 'table2-record-structure.csv')
    assert [r['id'] for r in structured] == [r['id'] for r in rows]
    for r in structured:
        assert json.loads(r['record_v3']) == index[r['id']]['record_v3']
    readable = (OUT / 'conditional-responses.md').read_text(encoding='utf-8')
    assert readable.endswith(old('conditional-responses.md').read_text(encoding='utf-8'))
    assert all(r['record_v3']['comparison_id'] in readable for r in rows)
    protected = load(ROOT / 'research/table1-confirmation/protected-inputs.json')['files']
    for ref in protected:
        assert sha(ROOT / ref['path']) == ref['sha256']
    assert len(protected) == 67
    ci = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch' in ci and not re.search(r'^\s*(push|pull_request|schedule)\s*:', ci, re.M)
    guard_results = []
    for script in ['research/table1-confirmation/build_stage_f.py', 'research/table1-confirmation/build_audit.py',
                   'research/table2-confirmation/build_stage_2a.py', 'research/table2-confirmation/verify_stage_2a.py']:
        process = subprocess.run([sys.executable, str(ROOT / script)], capture_output=True, text=True)
        assert process.returncode != 0 and 'Stage 2B registered' in process.stderr
        guard_results.append(dict(script=script, refused=True))
    for script in HERE.glob('*.py'):
        ast.parse(script.read_text(encoding='utf-8'))
    docs = [ROOT / n for n in ['README.md', 'AGENTS.md', 'plan.md', 'plan-table2.md', 'research/table2-confirmation/README.md']] + [OUT / n for n in ['README.md', 'conditional-responses.md', 'table2-fields.md', 'table2-schema-review.md']]
    links = 0
    for p in docs:
        for link in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
            if link.startswith(('http:', 'https:', '#', 'app:', 'codex:')):
                continue
            target = (p.parent / link.split('#')[0]).resolve()
            if target == OUT / 'table2-stage-2b-audit.json':
                continue  # Written at the end of this verification.
            assert target.exists(), (p, link)
            links += 1
    local = dict(status='not_run_in_this_invocation')
    if args.local_checks:
        pytest = (run / 'logs/pytest.txt').read_text(encoding='utf-8-sig')
        gate = (run / 'logs/worktree-check.txt').read_text(encoding='utf-8-sig')
        assert re.search(r'88 passed', pytest)
        gate_result = json.loads(gate.strip())
        assert gate_result['checks'] == 'passed' and gate_result['audio_payloads'] == 0
        assert gate_result['author_projects'] == 3 and gate_result['zip_members'] == 5 and gate_result['skill_links'] == 102
        exact = load(run / 'exact-rebuild.json')
        assert exact['identical'] and set(exact['artifact_sha256']) == set(OUTPUTS)
        for n, h in exact['artifact_sha256'].items():
            assert sha(OUT / n) == h
        assert load(run / 'freeze-overwrite-guard.json')['refused_and_unchanged']
        local = dict(status='passed', pytest_tests=88, worktree_gate=gate_result, deterministic_generated_outputs=6, bound_knowledge_outputs=len(OUTPUTS))
    result = dict(date='2026-10-10', stage='2B', status='passed_with_explicit_gaps',
        records=14, comparisons=17, feedback_groups=6, original_CSV_rows=10, full_structure_CSV_rows=14,
        snapshot_files=len(entries), source_metadata_SHA_checked=52, protected_input_SHA_checked=67,
        deep_restore_equal=True, old_CSV_cells_equal=True, original_Markdown_body_preserved=True,
        schema_validation_scope='declared type/required/const/enum/minItems/minLength/items/properties subset; three invalid specimens rejected; no external schema engine installed',
        historical_stage_audit_outputs_unchanged=True, historical_entry_guards=guard_results,
        document_links_checked=links, new_measurement_count=0, new_audio_or_array_reads=False,
        current_external_runtime_revalidated=False, new_user_feedback=0, stage_2C='not_executed',
        local_verification=local, baseline=binding,
        artifacts=[dict(path=(OUT / n).relative_to(ROOT).as_posix(), sha256=sha(OUT / n)) for n in OUTPUTS],
        research_and_current_entry_bindings=[dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)) for p in list(HERE.glob('*.py')) + [HERE / 'README.md', HERE / 'stage_2b_baseline_binding.json'] + [ROOT / n for n in ['README.md', 'AGENTS.md', 'plan.md', 'plan-table2.md']] + [OUT / 'README.md']])
    (OUT / 'table2-stage-2b-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], records=14, comparisons=17, sources=52, protected=67, links=links, local=local)))


if __name__ == '__main__':
    main()
