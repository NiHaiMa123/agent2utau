"""Independent record/provenance/restore verification of Stage 2C."""
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

import numpy as np
from verify_stage_2b import check_declared_schema

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
STATUS = 'record_review_complete_with_explicit_gaps'
OUTPUTS = ['conditional-responses.json', 'conditional-responses.csv', 'conditional-responses.md',
    'table2-record-structure.csv', 'table2-record-schema.json', 'table2-record-confirmation.json',
    'table2-record-confirmation.csv', 'table2-record-confirmation.md', 'table2-confirmation-migration.json']
MUTABLE = {str(OUT.relative_to(ROOT) / n).replace('\\', '/') for n in ['conditional-responses.json', 'conditional-responses.csv',
    'conditional-responses.md', 'table2-record-structure.csv', 'table2-record-schema.json', 'README.md']}
MUTABLE.update(['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md',
    'research/table2-confirmation/build_stage_2b.py', 'research/table2-confirmation/verify_stage_2b.py',
    'research/table2-confirmation/README.md'])


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def csv_rows(p):
    assert p.read_bytes().startswith(b'\xef\xbb\xbf')
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def restore_extension(ext):
    value = copy.deepcopy(ext)
    del value['confirmation_ref']
    value['record_confirmation'] = 'schema_revised_with_explicit_gaps; 2C_not_executed'
    return value


def at_pointer(value, path):
    if not path:
        return value
    for key in path.strip('/').split('/'):
        value = value[int(key)] if isinstance(value, list) else value[key.replace('~1', '/').replace('~0', '~')]
    return value


def original_leaf_pairs(legacy, source):
    if isinstance(legacy, dict):
        for key, value in legacy.items():
            if key != 'historical_perceived_improvement_field_is_not_listener_truth':
                yield from original_leaf_pairs(value, source[key])
    elif isinstance(legacy, list):
        assert len(legacy) == len(source)
        for a, b in zip(legacy, source):
            yield from original_leaf_pairs(a, b)
    else:
        yield legacy, source


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--local-checks', action='store_true')
    args = ap.parse_args()
    run = args.run.resolve()
    assert run.is_relative_to(ROOT / 'runs/research')
    binding = load(HERE / 'stage_2c_baseline_binding.json')
    assert sha(ROOT / binding['manifest_path']) == binding['manifest_sha256']
    freeze = load(ROOT / binding['manifest_path'])
    entries = {r['path']: r for r in freeze['files']}
    for r in entries.values():
        assert sha(ROOT / r['snapshot_path']) == r['sha256']
        if r['path'] not in MUTABLE:
            assert sha(ROOT / r['path']) == r['sha256'], r['path']
    def old(name):
        return ROOT / entries[(OUT / name).relative_to(ROOT).as_posix()]['snapshot_path']
    previous = load(old('conditional-responses.json'))
    current = load(OUT / 'conditional-responses.json')
    assert current['schema_version'] == previous['schema_version'] == 3
    restored = copy.deepcopy(current)
    del restored['table2_record_confirmation']
    for r in restored['responses'] + restored['observations'] + restored['audits']:
        r['record_v3'] = restore_extension(r['record_v3'])
    assert restored == previous, 'Old record values and all 2B structure must restore exactly'
    review = load(OUT / 'table2-record-confirmation.json')
    assert review['status'] == STATUS and review['baseline'] == binding
    assert review['counts']['records'] == 14 and review['counts']['designs'] == 5
    assert review['counts']['new_synthesis'] == review['counts']['new_PCM_or_detector_measurements'] == review['counts']['new_feedback'] == review['counts']['general_rules_validated'] == 0
    rows = current['responses'] + current['observations'] + current['audits']
    assert [r['id'] for r in rows] == [r['record_id'] for r in review['rows']]
    schema = load(OUT / 'table2-record-schema.json')
    for i, (r, checked) in enumerate(zip(rows, review['rows'])):
        ext = r['record_v3']
        check_declared_schema(ext, schema)
        assert ext['confirmation_ref'] == f'table2-record-confirmation.json#/rows/{i}'
        assert ext['record_confirmation'] == STATUS + '; no_new_model_or_PCM_measurement'
        assert ext['comparison_id'] == checked['comparison_id']
        assert checked['general_rule_validated'] is False and checked['record_content_or_original_feedback_changed'] is False
    for kind in ['confirmed', 'partial', 'unknown']:
        expected = [dict(record_id=r['record_id'], scope=scope) for r in review['rows'] for scope in r[kind]]
        assert review['status_lists'][kind] == expected
    assert [len(review['status_lists'][k]) for k in ['confirmed', 'partial', 'unknown']] == [36, 24, 56]
    # Original source metadata (52) and all newly read bindings rehashed, arrays read only.
    audited = load(OUT / 'comparison-bindings.json')
    expected = {}
    for r in audited['source_bindings']:
        if r['hash_status'] == 'verified':
            assert sha(ROOT / r['path']) == r['sha256']
            expected[r['path']] = r['sha256']
    assert len(expected) == 52
    for r in audited['sealed_manifests']:
        assert sha(ROOT / r['manifest']) == r['sha256']
        p = ROOT / r['manifest']
        data = load(p)
        for k, h in data.get('files', data.get('files_sha256')).items():
            path = Path(k) if Path(k).is_absolute() else p.parent / k
            expected[path.relative_to(ROOT).as_posix()] = h
    ref = review['independent_input_proof']
    assert ref['path'] == (run / 'input-rechecks.json').relative_to(ROOT).as_posix()
    assert sha(ROOT / ref['path']) == ref['sha256']
    proof = load(ROOT / ref['path'])
    assert proof['input_prediction_arrays_read'] == 60 and not proof['array_values_published']
    assert not proof['PCM_or_mel_or_detector_arrays_read'] and not proof['model_or_native_engine_executed']
    assert len(proof['read_bindings']) == review['counts']['read_bound_files'] == 129
    array_count = 0
    for r in proof['read_bindings']:
        p = ROOT / r['path']
        assert p.resolve().is_relative_to(ROOT) and sha(p) == expected[r['path']] == r['sha256']
        assert p.suffix in ['.json', '.md', '.py', '.npz']
        if p.suffix == '.npz':
            assert p.name.endswith(('_inputs.npz', '_prediction.npz'))
            array_count += 1
    assert array_count == 60
    assert len(proof['negative_specimens']) == 3 and all(r['refused'] for r in proof['negative_specimens'])
    assert proof['rows'][2]['native_check']['primary_C_minus_B']['finite_support']['changed_frames'] == 12
    assert proof['rows'][2]['fresh_check']['primary_C_minus_B']['original_B_waveform_reused']
    assert all(r['fresh_check']['repeat_input_and_prediction_exact'] for r in proof['rows'])
    assert all(not r['historical_wave_repeat']['newly_PCM_checked'] for r in proof['rows'])
    assert all(r['historical_wave_repeat']['reported_max_abs'] == 0 for r in proof['rows'])
    assert all(r['native_check']['native_arithmetic_exact'] and not r['native_check']['current_cache_or_engine_execution_verified'] for r in proof['rows'])
    count = sum(c.get('scalar_leaves_equal', 0) for r in proof['rows'] for c in r['source_metric_checks'])
    assert count == review['counts']['metric_scalar_leaves_source_matched'] == 823
    prior_by_id = {r['id']: r for r in previous['responses']}
    independently_matched = 0
    for r in proof['rows']:
        for check in r['source_metric_checks']:
            if 'scalar_leaves_equal' not in check:
                continue  # The two rounded guo proxies have a separate report source.
            source = check['source']
            assert source['sha256'] == expected[source['path']]
            a = at_pointer(prior_by_id[r['record_id']], check['record_pointer'])
            b = at_pointer(load(ROOT / source['path']), source['pointer'])
            pairs = list(original_leaf_pairs(a, b))
            assert len(pairs) == check['scalar_leaves_equal'] and all(x == y for x, y in pairs)
            independently_matched += len(pairs)
    assert independently_matched == 823
    # Independent final feature check: exactly reconstruct the 20 original A/target arrays.
    arithmetic_variants = 0
    for i, r in enumerate(previous['responses']):
        labels = ['A', 'C'] if i == 2 else ['A', 'B']
        source = audited['rows'][1] if i == 2 else audited['rows'][i]
        for v in r['record_v3']['variants']:
            if v['logical_label'] not in labels:
                continue
            label = v['logical_label']
            native_audit = source if label == 'A' else audited['rows'][i]
            native_path = next(x['path'] for x in native_audit['native_and_fresh_artifact_bindings'] if f'/native_{label}/phrase_' in x['path'])
            native = load(ROOT / native_path)
            inputs_ref, prediction_ref = [a for a in v['state_origin']['artifacts'] if a['path'].endswith('.npz')]
            with np.load(ROOT / inputs_ref['path'], allow_pickle=False) as inputs, np.load(ROOT / prediction_ref['path'], allow_pickle=False) as prediction:
                for channel in ['breathiness', 'voicing', 'tension']:
                    raw = prediction[channel + '_pred'].astype(np.float32) + np.asarray(native['expression_deltas'][channel], dtype=np.float32).reshape(1, -1)
                    low, high = (-10, 10) if channel == 'tension' else (-96, 0)
                    # Use nested minimum/maximum instead of the builder's np.clip.
                    reconstructed = np.minimum(np.maximum(raw, np.float32(low)), np.float32(high))
                    assert np.array_equal(reconstructed, inputs[channel])
            arithmetic_variants += 1
    assert arithmetic_variants == 20
    feedbacks = {r['feedback_group_id']: r for r in review['feedback_groups']}
    assert len(feedbacks) == 6 and len(feedbacks['FB:BREC-cohort']['record_ids']) == 6 and len(feedbacks['FB:BREC-cohort']['audio_bindings']) == 12
    for fg, r in feedbacks.items():
        source = load(ROOT / r['source']['path'])
        text = source.get('user_verbatim', source.get('user_text', source.get('verbatim')))
        if text is None:
            text = source.get('user_feedback')
        assert text == r['original_text'], (fg, text, r['original_text'])
        assert r['submission_timestamp'] == r['device'] == r['blinding'] == r['task_protocol'] == 'unknown'
    assert feedbacks['FB:RESP-002']['separate_location_messages'] == ['开头', '抱的字头']
    assert feedbacks['FB:BREC-cohort']['original_text'] == '全部没区别。'
    for r in review['rows'][:10]:
        original_record = next(s for s in previous['responses'] if s['id'] == r['record_id'])
        assert r['feedback']['outcome'] == original_record['status']['auditory_outcome']
    assert 'no_direct_C-A_listening' in review['rows'][11]['feedback']['label_evidence']
    # CSV numeric/legacy columns unchanged; only extension confirmation fields change.
    for filename in ['conditional-responses.csv', 'table2-record-structure.csv']:
        now, then = csv_rows(OUT / filename), csv_rows(old(filename))
        assert len(now) == len(then)
        for r, p in zip(now, then):
            assert {k: v for k, v in r.items() if k != 'record_v3'} == {k: v for k, v in p.items() if k != 'record_v3'}
            assert restore_extension(json.loads(r['record_v3'])) == json.loads(p['record_v3'])
    review_csv = csv_rows(OUT / 'table2-record-confirmation.csv')
    assert len(review_csv) == 14
    for csv_row, r in zip(review_csv, review['rows']):
        for key, value in r.items():
            normalized = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
            assert csv_row[key] == normalized
    assert (OUT / 'conditional-responses.md').read_text(encoding='utf-8').endswith(old('conditional-responses.md').read_text(encoding='utf-8'))
    for r in review['rows']:
        assert r['record_id'] in (OUT / 'table2-record-confirmation.md').read_text(encoding='utf-8')
    protected = load(ROOT / 'research/table1-confirmation/protected-inputs.json')['files']
    for ref in protected:
        assert sha(ROOT / ref['path']) == ref['sha256']
    assert len(protected) == 67
    assert all(not r['measurement_validated'] for r in load(OUT / 'measurement-protocols.json')['rows'])
    ci = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch' in ci and not re.search(r'^\s*(push|pull_request|schedule)\s*:', ci, re.M)
    guards = []
    for name in ['build_stage_2b.py', 'verify_stage_2b.py']:
        p = subprocess.run([sys.executable, str(HERE / name)], capture_output=True, text=True, encoding='utf-8')
        assert p.returncode != 0 and 'Stage 2C registered' in p.stderr
        guards.append(dict(script=name, refused=True))
    for p in HERE.glob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'))
    link_count = 0
    paths = [ROOT / n for n in ['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md', 'research/table2-confirmation/README.md']] + [OUT / n for n in ['README.md', 'conditional-responses.md', 'table2-record-confirmation.md']]
    for p in paths:
        for link in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
            if link.startswith(('http:', 'https:', '#', 'app:', 'codex:')):
                continue
            target = (p.parent / link.split('#')[0]).resolve()
            if target == OUT / 'table2-stage-2c-audit.json':
                continue
            assert target.exists(), (p, link)
            link_count += 1
    local = dict(status='not_run_in_this_invocation')
    if args.local_checks:
        pytest = (run / 'logs/pytest.txt').read_text(encoding='utf-8-sig')
        assert re.search(r'88 passed', pytest)
        gate = json.loads((run / 'logs/worktree-check.txt').read_text(encoding='utf-8-sig').strip())
        assert gate['checks'] == 'passed' and gate['audio_payloads'] == 0 and gate['author_projects'] == 3 and gate['zip_members'] == 5 and gate['skill_links'] == 102
        exact = load(run / 'exact-rebuild.json')
        assert exact['identical'] and set(exact['artifact_sha256']) == set(OUTPUTS)
        for name, h in exact['artifact_sha256'].items():
            assert sha(OUT / name) == h
        assert load(run / 'freeze-overwrite-guard.json')['refused_and_unchanged']
        local = dict(status='passed', pytest_tests=88, worktree_gate=gate, deterministic_generated_outputs=9)
    for r in proof['read_bindings']:
        assert sha(ROOT / r['path']) == r['sha256'], 'Read source changed during independent verification'
    result = dict(stage='2C', date='2026-10-10', status='passed_with_explicit_gaps', baseline=binding,
        records=14, comparisons=17, input_prediction_arrays=60, independently_reconstructed_variants=20,
        source_metadata_SHA=52, read_bound_files=129, source_metric_scalar_leaves=823, independently_source_matched_fields=independently_matched, snapshots=26, protected_inputs=67,
        status_claim_counts=dict(confirmed=36, partial=24, unknown=56),
        original_2B_JSON_restore_equal=True, old_CSV_nonconfirmation_cells_equal=True, old_Markdown_body_preserved=True,
        schema_keywords_and_ID_reference_checks=True, negative_confounds_rejected=3,
        PCM_or_mel_or_detector_arrays_read=False, model_or_native_engine_executed=False,
        new_feedback=0, general_rules_validated=0, table1_measurement_validated_upgrade=False,
        history_guards=guards, document_links_checked=link_count, local_verification=local,
        next_stage='2D_not_executed',
        artifacts=[dict(path=(OUT / n).relative_to(ROOT).as_posix(), sha256=sha(OUT / n)) for n in OUTPUTS],
        current_entry_and_code_bindings=[dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)) for p in list(HERE.glob('*.py')) + [HERE / 'stage_2c_baseline_binding.json', HERE / 'README.md', ROOT / 'src/agent2utau/evaluation/controlled_probe.py'] + [ROOT / n for n in ['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md']] + [OUT / 'README.md']])
    (OUT / 'table2-stage-2c-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], records=14, arrays=60, source_fields=823, protected=67, links=link_count, local=local)))


if __name__ == '__main__':
    main()
