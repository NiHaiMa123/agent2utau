"""Independent finite-design/reference/preservation checks; no experiment."""
import argparse
import ast
import copy
import csv
import json
import re
import subprocess
import sys

from freeze_stage_2d import ROOT, HERE, OUT, BINDING, load, sha

OUTPUTS = ['table2-validation-gaps.json', 'table2-validation-gaps.csv',
    'table2-manifestation-gaps.csv', 'table2-protocol-review.md',
    'validation-protocols/shfc-path-separation-v1.json', 'validation-protocols/shfc-path-separation-v1.md']
SEAL = HERE / 'stage_2d_protocol_binding.json'
MUTABLE = {'AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md',
    'research/table2-confirmation/README.md',
    'research/table2-confirmation/build_stage_2c.py', 'research/table2-confirmation/verify_stage_2c.py',
    (OUT / 'README.md').relative_to(ROOT).as_posix()}


def validate_protocol(p):
    assert p['status'] == 'frozen_design_with_execution_dependencies' and p['execution_status'] == 'not_executed'
    assert p['table1_refs']['main_parameter'] == 'PARAM:C14.01'
    assert set(p['table1_refs']['mediated_parameters']) == {'PARAM:C11.01', 'PARAM:C12.01', 'PARAM:C13.01'}
    v = {r['id']: (r['acoustic_F0'], r['prediction'], r['native_equivalent']) for r in p['variant_matrix']}
    assert v == {'A': ('unshifted', 'fresh_unshifted_same_phrase', True),
        'S': ('SHFC_shifted', 'fresh_SHFC_shifted_same_phrase', True),
        'D': ('SHFC_shifted', 'fresh_unshifted_same_phrase', False),
        'P': ('unshifted', 'fresh_SHFC_shifted_same_phrase', False)}
    b = p['budget']
    assert (b['conditions'], b['logical_variants_per_condition'], b['identical_repetitions_per_variant']) == (2, 4, 2)
    assert b['total_acoustic_vocoder_waveforms'] == 2 * 4 * 2 == 16
    assert b['total_variance_inferences'] == 2 * 2 * 2 == 8
    assert b['independent_effect_replications'] == b['parameter_sweeps'] == 0
    assert b['infrastructure_retry_limit_per_failed_operation'] == 1
    assert b['total_listener_pairs'] == 2 * 5 == 10
    assert {r['direction'] for r in p['comparisons']} == {'S-A', 'D-A', 'P-A', 'S-D', 'S-P'}
    assert len(p['comparisons']) == 5
    assert p['listening']['presentation_order'] == ['S-A', 'A-S', 'D-A', 'A-D', 'P-A', 'A-P', 'S-D', 'D-S', 'S-P', 'P-S']
    for mapping in p['listening']['anonymous_code_map'].values():
        assert set(mapping) == {'K1', 'K2', 'K3', 'K4'} and set(mapping.values()) == {'A', 'S', 'D', 'P'}
    assert {c['condition']['word'] for c in p['cases']} == {225, 214}
    for c in p['cases']:
        assert c['independent_holdout'] is False and c['peak_cents'] == -400
        a = c['nominal_Q5_anchors_s']
        assert len(a) == 4 and all(x < y for x, y in zip(a, a[1:]))
        assert abs((a[1]-a[0]) * 1000 - 145) < 1e-7
        assert abs((a[3]-a[2]) * 1000 - 55) < 1e-7
        assert c['shifted_support_s'] == [a[0], a[3]]
        phones = c['condition']['native_phones']
        assert phones[0]['start_ms']/1000 < a[0] < c['condition']['vowel_s'][0]
        assert a[3] < c['condition']['vowel_s'][1]
        assert c['baseline_project']['sha256'] == 'a17d4bebdd3c5951f2b10138777a8fee8925ab5beb6bb70705342d1b6ba466af'
    assert p['geometry']['grid_ticks'] == 5 and p['geometry']['explicit_diagnostic_range_cents'] == [-1200, 1200]
    f = p['fixed']['common_context']
    assert (f['seed_variance'], f['seed_acoustic'], f['sample_rate_Hz'], f['hop_samples']) == (11, 101, 44100, 512)
    assert f['fixed_gain'] == {'vocal': 1.5, 'backing': .7}
    assert not f['normalization'] and not f['compressor']
    assert len(p['fixed']['runtime_expected_hashes']) == 47
    assert p['fixed']['acoustic_steps'] == 20 and p['fixed']['acoustic_depth'] == .6
    assert p['result'] == dict(new_audio=0, new_feedback=0, generic_rule_validated=False,
        causal_mechanism_validated=False, execution_adapter_validated=False, all_measurement_methods_validated=False)
    assert len(p['stop_rules']) == 5 and '不加剂量' in p['stop_rules'][0]


def check_csv(path, rows):
    with path.open(encoding='utf-8-sig', newline='') as f:
        actual = list(csv.DictReader(f))
    assert len(actual) == len(rows)
    for a, r in zip(actual, rows):
        assert a == {k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list, bool)) else str(v) for k, v in r.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--local-checks', action='store_true')
    args = ap.parse_args()
    binding = load(BINDING)
    run = ROOT / binding['run']
    assert sha(ROOT / binding['manifest']) == binding['sha256']
    snap = load(ROOT / binding['manifest'])
    for ref in snap['files']:
        assert sha(ROOT / ref['snapshot']) == ref['sha256']
        if ref['path'] not in MUTABLE:
            assert sha(ROOT / ref['path']) == ref['sha256'], ref['path']
    for ref in snap['design_source_bindings']:
        assert sha(ROOT / ref['path']) == ref['sha256']
    old = {r['path']: ROOT / r['snapshot'] for r in snap['files']}
    def frozen(name):
        return load(old[(OUT / name).relative_to(ROOT).as_posix()])
    ledger = frozen('conditional-responses.json')
    records = ledger['responses'] + ledger['observations'] + ledger['audits']
    cat = frozen('control-details.json')['rows']
    entities = frozen('knowledge-table.json')['entities']
    measurements = frozen('measurement-protocols.json')['rows']
    gap = load(OUT / 'table2-validation-gaps.json')
    rows = gap['parameter_rows']
    assert [r['parameter_id'] for r in rows] == [p['id'] for p in cat]
    assert len(rows) == len({r['parameter_id'] for r in rows}) == 352
    assert len({r['group_id'] for r in rows}) == 48
    for r, p in zip(rows, cat):
        assert (r['field'], r['scope'], r['actual_support'], r['condition']) == (p['field'], p['scope'], p['current_support'], p['condition'])
        for kind, key in [('responses', 'historical_response_ids'), ('observations', 'historical_observation_ids'), ('audits', 'historical_audit_ids')]:
            expected = [s['id'] for s in ledger[kind] if p['id'] in s['record_v3']['table1_refs']['parameter_ids']]
            assert r[key] == expected
        expected = [e['id'] for e in entities if 'CTRL:' + r['group_id'] in e['control_family_navigation_refs']]
        assert r['candidate_entity_ids'] == expected and not r['generic_rule_validated']
    mr = gap['manifestation_rows']
    assert [r['entity_id'] for r in mr] == [e['id'] for e in entities] + ['CAND:MULTI_F0']
    assert {r['measurement_protocol_id'] for r in mr} == {r['id'] for r in measurements}
    assert all(not r['measurement_validated'] and not r['generic_rule_validated'] for r in mr)
    for r, e in zip(mr, entities):
        assert r['historical_candidate_record_ids'] == [s['id'] for s in records if e['id'] in s['record_v3']['table1_refs']['entity_ids']]
        assert r['remaining_gap'] == e['required_followup']
    assert gap['counts']['directly_referenced_parameters'] == sum(bool(r['historical_response_ids'] or r['historical_observation_ids'] or r['historical_audit_ids']) for r in rows) == 10
    assert gap['counts']['intervention_referenced_parameters'] == sum(bool(r['historical_response_ids']) for r in rows) == 3
    assert gap['counts']['selected_main_interventions'] == 1 and gap['counts']['selected_parameter_roles'] == 5
    check_csv(OUT / OUTPUTS[1], rows)
    check_csv(OUT / OUTPUTS[2], mr)
    p = load(OUT / OUTPUTS[4])
    validate_protocol(p)
    for case in p['cases']:
        source = next(r for r in records if r['id'] == case['source_record_id'])
        assert source['condition'] == case['condition']
    bao = p['cases'][0]
    original = next(r for r in records if r['id'] == 'RESP-003')['intervention']
    assert bao['nominal_Q5_anchors_s'] == [original['support_s'][0], original['same_arrival_s'], original['same_release_start_s'], original['support_s'][1]]
    assert p['fixed']['runtime_expected_hashes'] == ledger['runtime_hash_bindings']
    selected = {r['parameter_id'] for r in rows if r['protocol_ids']}
    assert selected == {p['table1_refs']['main_parameter'], p['table1_refs']['driver'], *p['table1_refs']['mediated_parameters']}
    assert set(p['table1_refs']['entity_ids']) <= {r['entity_id'] for r in mr}
    assert set(p['table1_refs']['measurement_ids']) <= {r['id'] for r in measurements}
    for eid, mid in zip(p['table1_refs']['entity_ids'], p['table1_refs']['measurement_ids']):
        assert next(e for e in entities if e['id'] == eid)['measurement_protocol_ref'] == mid
    negatives = []
    for label in ['unlimited_budget', 'false_holdout', 'native_counterfactual']:
        bad = copy.deepcopy(p)
        if label == 'unlimited_budget':
            bad['budget']['total_acoustic_vocoder_waveforms'] = 32
        elif label == 'false_holdout':
            bad['cases'][1]['independent_holdout'] = True
        else:
            bad['variant_matrix'][2]['native_equivalent'] = True
        try:
            validate_protocol(bad)
        except AssertionError:
            negatives.append(label)
        else:
            raise AssertionError('Protocol confound was not rejected')
    protected = load(ROOT / 'research/table1-confirmation/protected-inputs.json')['files']
    for r in protected:
        assert sha(ROOT / r['path']) == r['sha256'], r['path']
    assert len(protected) == 67
    assert all(not r['measurement_validated'] for r in measurements)
    ci = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch' in ci and not re.search(r'^\s*(push|pull_request|schedule)\s*:', ci, re.M)
    guards = []
    for name in ['build_stage_2c.py', 'verify_stage_2c.py']:
        result = subprocess.run([sys.executable, str(HERE / name)], capture_output=True, text=True, encoding='utf-8')
        assert result.returncode != 0 and 'Stage 2D registered' in result.stderr
        guards.append(name)
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'))
    if SEAL.exists():
        sealed = load(SEAL)
        assert (sealed['id'], sealed['version']) == (p['id'], 1)
        for r in sealed['bindings']:
            assert sha(ROOT / r['path']) == r['sha256']
    links = 0
    paths = [ROOT / x for x in ['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md', 'research/table2-confirmation/README.md']] + [OUT / n for n in ['README.md', OUTPUTS[3], OUTPUTS[5]]]
    for path in paths:
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if link.startswith(('http:', 'https:', '#', 'app:', 'codex:')):
                continue
            target = (path.parent / link.split('#')[0]).resolve()
            if target == OUT / 'table2-stage-2d-audit.json':
                continue
            assert target.exists(), (path, link)
            links += 1
    local = dict(status='not_run_in_this_invocation')
    if args.local_checks:
        assert SEAL.exists()
        assert re.search(r'88 passed', (run / 'logs/pytest.txt').read_text(encoding='utf-8-sig'))
        gate = load(run / 'logs/worktree-check.txt')
        assert gate['checks'] == 'passed' and gate['audio_payloads'] == 0 and gate['skill_links'] == 102
        exact = load(run / 'exact-rebuild.json')
        assert exact['identical'] and len(exact['artifact_sha256']) == 6
        for n, h in exact['artifact_sha256'].items():
            assert sha(OUT / n) == h
        assert load(run / 'freeze-overwrite-guard.json')['refused_and_unchanged']
        local = dict(status='passed', pytest_tests=88, worktree_gate=gate, deterministic_generated_outputs=6)
    result = dict(stage='2D', date='2026-10-10', status='passed_with_explicit_gaps', baseline=binding,
        parameter_rows=352, manifestation_rows=50, directly_referenced_parameters=10,
        intervention_referenced_parameters=3, frozen_protocols=1, planned_waveforms=16,
        planned_listener_pairs=10, independent_holdout_conditions=0, independent_effect_replications=0,
        research_adapter_validated=False, snapshots=len(snap['files']), protected_inputs=67,
        design_sources_SHA_verified=len(snap['design_source_bindings']), old_2C_artifacts_unchanged=True,
        measurement_validated_upgrade=False, new_audio_arrays_or_model_execution=False, new_feedback=0,
        generic_rules_validated=0, protocol_confounds_rejected=negatives, history_write_guards=guards,
        protocol_sealed=SEAL.exists(), document_links_checked=links, local_verification=local,
        next_stage='2E_research_adapter_and_independent_checks_before_rendering_and_listening',
        artifacts=[dict(path=(OUT / n).relative_to(ROOT).as_posix(), sha256=sha(OUT / n)) for n in OUTPUTS],
        current_entry_and_code_bindings=[dict(path=x.relative_to(ROOT).as_posix(), sha256=sha(x)) for x in paths + list(HERE.glob('*2d*.py')) + [BINDING] + ([SEAL] if SEAL.exists() else [])])
    (OUT / 'table2-stage-2d-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['status', 'parameter_rows', 'manifestation_rows', 'snapshots', 'protocol_sealed', 'document_links_checked', 'local_verification']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
