"""Verify Stage A–F artifacts, original snapshots and explicit protected inputs."""
import ast
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from frozen_inputs import original_path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
HERE = Path(__file__).resolve().parent

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p):
    return json.loads(p.read_text(encoding='utf-8'))

def verify_csv(name, expected):
    p = OUT / name
    assert p.read_bytes().startswith(b'\xef\xbb\xbf'), name
    with p.open(encoding='utf-8-sig', newline='') as f:
        actual = list(csv.DictReader(f))
    normalized = [{k: ';'.join(v) if isinstance(v, list) else json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, dict) else str(v)
                   for k,v in r.items()} for r in expected]
    assert actual == normalized, f'CSV/JSON mismatch: {name}'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verification-run',type=Path)
    args = ap.parse_args()
    a = load(OUT / 'table1-row-review.json')
    b = load(OUT / 'claim-evidence.json')
    core = load(OUT / 'core-definition-review.json')
    composites = load(OUT / 'composite-review.json')
    c = load(OUT / 'control-details.json')
    m = load(original_path(OUT / 'id-migration.json'))
    assert a['original_rows'] == len(a['rows']) == 31
    assert len({r['legacy_id'] for r in a['rows']}) == 31
    ids = {i for r in a['rows'] for i in r['proposed_ids']}
    assert len(ids) == a['proposed_entity_count'] == 47
    for r in a['rows']:
        assert all(r[k] for k in ['problem', 'decision', 'operational_scope_proposal',
                                  'exclude', 'units_and_clock', 'unknown_rule', 'required_followup'])
        assert r['legacy_id'] in m['namespaces']['dimension']
        assert m['namespaces']['dimension'][r['legacy_id']]['candidates'] == r['proposed_ids']
    assert m['status'] == 'proposed_not_applied'
    assert len(m['second_layer_candidate_links']) == 14
    assert all(not r['legacy_atoms'] and not r['proposed_candidates'] for r in m['second_layer_candidate_links']), 'Pre-F empty-reference defect not as documented'
    assert len(b['claims']) == 30 and not b['all_core_definitions_checked']
    assert b['all_core_definitions_reviewed'] and b['all_composite_descriptors_reviewed']
    assert not b['all_composite_descriptors_checked']
    assert b['status'] == core['status'] == composites['status'] == 'reviewed_with_explicit_gaps'
    assert len(core['rows']) == 31 and len(composites['rows']) == 30
    assert {r['legacy_id'] for r in core['rows']} == {r['legacy_id'] for r in a['rows']}
    claims = {r['id'] for r in b['claims']}
    assert len(claims) == 30
    with original_path(OUT / 'composite-descriptors.csv').open(encoding='utf-8-sig', newline='') as f:
        original_composites = list(csv.DictReader(f))
    assert len(original_composites) == 30
    assert [r['descriptor'] for r in composites['rows']] == [r['descriptor'] for r in original_composites]
    assert [r['legacy_row'] for r in composites['rows']] == list(range(1, 31))
    assert len({r['id'] for r in composites['rows']}) == 30
    for r in core['rows'] + composites['rows']:
        assert r['claim_refs'] and set(r['claim_refs']) <= claims
        assert not r['measurement_validated']
        assert r['status'] == 'reviewed_with_explicit_gaps'
    for r in core['rows']:
        assert all(r[k] for k in ['working_definition', 'boundary', 'remaining_gap', 'source_review_status'])
        assert r['current_engine_effect'] == 'not_established'
    for r in composites['rows']:
        assert all(r[k] for k in ['ambiguity', 'candidate_path_A', 'candidate_path_B',
                                  'counterexample', 'needed_observations'])
        assert r['mapping_role'] == 'authored_hypothesis_component_sources_only'
        assert r['counterexample_role'] == 'hypothetical_not_new_audio_or_coverage_test'
        assert not r['synonym_equivalence_validated']
    for r in b['claims']:
        assert all(r[k] for k in ['url', 'source_title', 'authors_year', 'locator', 'study_scope', 'limitations', 'read_status'])
        assert r['url'].startswith('https://')
        assert not r['measurement_validated_here']
    verify_csv('table1-row-review.csv', a['rows'])
    verify_csv('claim-evidence.csv', b['claims'])
    verify_csv('core-definition-review.csv', core['rows'])
    verify_csv('composite-review.csv', composites['rows'])
    verify_csv('control-details.csv', c['rows'])
    assert c['status'] == 'reviewed_with_explicit_gaps'
    assert c['frozen_scope_review_complete']
    assert not c['all_controls_enumerated'] and not c['all_local_paths_confirmed']
    assert c['counts']['parameters'] == len(c['rows']) == 352
    assert len({r['id'] for r in c['rows']}) == len(c['rows'])
    from stage_c_control_data import controls
    original = controls()
    assert [(r['id'],r['group_id'],r['field']) for r in c['rows'][:184]] == [(r['id'],r['group_id'],r['field']) for r in original]
    from stage_c_remaining_data import extra_controls
    sequence = Counter(r['group_id'] for r in original)
    for r in extra_controls():
        sequence[r['group_id']] += 1
        r['id'] = f'PARAM:{r["group_id"]}.{sequence[r["group_id"]]:02}'
        original.append(r)
    assert len(original)==320
    assert [(r['id'],r['group_id'],r['field']) for r in c['rows'][:320]] == [(r['id'],r['group_id'],r['field']) for r in original]
    graph = load(OUT / 'graph-node-review.json')
    local = load(OUT / 'local-capability-review.json')
    assert graph['type_count'] == len(graph['types']) == len({r['type'] for r in graph['types']}) == 31
    assert graph['all_frozen_registered_types_enumerated'] and not graph['installed_graph_supported']
    control_ids = {r['id'] for r in c['rows']}
    for node in graph['types']:
        assert set(node['control_refs']) <= control_ids
        expected_fields = {f'graph.nodes[type={node["type"]}].type'}
        expected_fields |= {f'graph.nodes[type={node["type"]}].input[{p["name"]}]' for p in node['ports']}
        expected_fields |= {f'graph.nodes[type={node["type"]}].parameters[{p["name"]}]' for p in node['parameters']}
        assert {r['field'] for r in c['rows'] if r['id'] in node['control_refs']} == expected_fields
    local_ids = {r['id'] for r in local['rows']}
    assert len(local_ids) == len(local['rows']) == 23
    assert local['mode']=='offline_PE_metadata_and_IL_no_target_execution'
    assert not local['live_preferences_read'] and not local['models_executed'] and not local['audio_read_or_written']
    assert not local['all_local_paths_confirmed']
    assert len(local['bindings'])==2 and local['bindings'][0]['sha256']==c['installed_bindings_rechecked'][0]['sha256']
    groups = Counter(r['group_id'] for r in c['rows'])
    assert set(groups) == {f'C{i:02}' for i in range(1,49)}
    assert dict(groups) == c['group_counts']
    assert dict(Counter(r['scope'] for r in c['rows'])) == c['counts']['by_scope']
    source_hashes = {r['path']: r['sha256'] for r in c['source_bindings']}
    assert len(source_hashes)==86
    assert Counter(r['binding_role'] for r in c['source_bindings'])=={'original_44_rechecked':44,'additional_25_frozen_source_review':25,'editor_frozen_source_review':17}
    preferences = load(OUT / 'editor-preferences-review.json')
    assert preferences['status']=='reviewed_with_explicit_gaps'
    assert preferences['all_scoped_declarations_classified']
    assert not preferences['all_consumers_or_plugins_enumerated'] and not preferences['live_preferences_read']
    assert len(preferences['rows']) == preferences['declaration_count'] == c['editor_declarations_reviewed'] == 103
    assert len({r['field'] for r in preferences['rows']})==103
    assert len(preferences['nested_properties'])==8
    assert preferences['local_core_sha256']==local['bindings'][0]['sha256']
    assert preferences['metadata_sha256']==local['bindings'][0]['metadata_sha256']
    with (OUT / 'editor-preferences-review.csv').open(encoding='utf-8-sig',newline='') as f:
        expected = [{k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict)) else str(v) for k,v in r.items()} for r in preferences['rows']]
        assert list(csv.DictReader(f))==expected
    assert (OUT / 'editor-preferences-review.csv').read_bytes().startswith(b'\xef\xbb\xbf')
    assert dict(Counter(r['category'] for r in preferences['rows']))==preferences['category_counts']
    for r in preferences['rows']:
        assert r['source_sha256']==source_hashes[r['declaration_path']]
        assert set(r['control_refs']) <= control_ids
        assert r['live_value']=='not_read' and not r['auditory_effect_validated']
        for ref in r['checked_reference_sites']:
            assert ref['source_sha256']==source_hashes[ref['path']] and ref['line']>0
    for r in preferences['nested_properties']:
        assert r['source_sha256']==source_hashes[r['source_path']]
    for r in c['rows']:
        assert all(r[k] for k in ['field', 'storage_unit', 'default_or_baseline',
                                  'declared_or_code_limits', 'transform', 'source_path',
                                  'source_anchor', 'current_support', 'stage', 'condition',
                                  'sampling_interpolation_clip', 'recalculate', 'limitation', 'engine'])
        assert r['source_sha256'] == source_hashes[r['source_path']]
        assert r['source_line'] > 0 and '#' in r['source_url']
        assert not r['dose_or_auditory_direction_validated']
        assert r['auditory_label_status'] == 'no_new_labels'
        assert not r['local_evidence_refs'] or r['local_evidence_refs'] in local_ids
    assert len(c['installed_bindings_rechecked']) == 6
    assert all(r['rechecked'] for r in c['installed_bindings_rechecked'])
    assert len(c['pending']) == 6
    # Deliberately distinguish the raw published declarations from the frozen
    # upstream defaults and diagnostic projects; no inferred compatibility.
    descriptor = {r['abbreviation']: r['current_published_descriptor'] for r in c['rows'] if r['abbreviation']}
    assert descriptor['shfc']['min'] == -12 and descriptor['shfc']['max'] == 12
    assert descriptor['voic']['max'] == 200
    d = load(OUT / 'measurement-protocols.json')
    ds = load(OUT / 'measurement-source-review.json')
    assert d['status'] == 'protocol_review_complete_with_explicit_gaps'
    assert len(d['rows']) == d['protocol_count'] == 50
    assert d['original_rows_covered'] == 31 and d['A_entities_covered'] == 47
    assert d['B_extra_candidates'] == 3
    assert {r['candidate_entity_id'] for r in d['rows']} == ids | {'ACO:L5','PER:P1','CAND:MULTI_F0'}
    assert [r['id'] for r in d['rows']] == [f'MEAS:D{i:02}' for i in range(1,51)]
    assert dict(Counter(r['candidate_entity_id'].split(':')[0] for r in d['rows'])) == d['counts_by_namespace']
    assert {r['candidate_entity_id'] for r in d['extra_candidates']} == {'ACO:L5','PER:P1','CAND:MULTI_F0'}
    for r in a['rows']:
        link = next(v for v in d['legacy_links'] if v['legacy_id'] == r['legacy_id'])
        assert link['protocol_refs'] == [v['id'] for v in d['rows'] if r['legacy_id'] in v['legacy_ids']]
        assert set(r['proposed_ids']) <= {v['candidate_entity_id'] for v in d['rows'] if v['id'] in link['protocol_refs']}
        assert not link['all_associated_methods_validated']
    assert len(d['legacy_links']) == 31
    assert not d['all_measurement_methods_validated'] and not d['all_real_audio_estimators_validated']
    assert d['stages_E_F'] == 'not_executed' and d['formal_id_migration'] == 'proposed_not_applied'
    assert all(d[k] for k in ['no_new_audio_or_synthesis','no_models_or_native_execution',
                             'no_project_skill_or_production_change','no_new_auditory_labels'])
    bindings = load(HERE / 'stage_d_source_bindings.json')['files']
    assert bindings == d['implementation_bindings'] and len(bindings) == 12
    dhashes = {r['path']:r['sha256'] for r in bindings}
    assert len(dhashes) == 12
    for path, expected in dhashes.items():
        assert digest(ROOT / path) == expected, f'D implementation changed: {path}'
    numerical = d['numerical_verification']
    array_path = (ROOT / numerical['path']).resolve()
    assert array_path.is_relative_to(ROOT / 'runs/research')
    assert digest(array_path) == numerical['sha256']
    observed = load(array_path)
    assert observed['cases'] == numerical['cases'] and observed['versions'] == numerical['versions']
    assert observed['status'] == numerical['status'] == 'finite_array_checks_passed'
    assert len(observed['cases']) == 10
    assert all(observed[k] for k in ['no_audio_files_read_or_written','no_models_or_native_execution','no_new_auditory_labels'])
    assert not observed['all_measurement_methods_validated']
    for ref in observed['code_bindings']:
        assert ref['sha256'] == dhashes[ref['path']]
    cases = {r['id']:r for r in observed['cases']}
    assert set(cases) == {f'DVAL:{i:02}' for i in range(1,11)}
    for r in cases.values():
        assert r['technical_check'] == 'passed' and r['input_spec'] and r['truth'] and r['observed'] and r['validation_scope']
        assert not r['real_audio_accuracy_validated'] and not r['auditory_effect_validated']
    dsource_ids = {r['id'] for r in ds['sources']}
    assert len(dsource_ids) == len(ds['sources']) == d['component_source_entries'] == 10
    for r in ds['sources']:
        assert r['url'].startswith('https://') and all(r[k] for k in ['title','locator','scope_limit','read_status'])
        assert not r['measurement_validated']
    for r in d['rows']:
        assert all(r[k] for k in ['name','observation_object','input_requirements','stage_and_clock',
            'window_hop_and_support','method_or_formula','units','quality_mask','unknown_or_refusal',
            'reference_and_uncertainty','parameter_status','source_role','implementation_status','remaining_gap'])
        assert set(r['source_refs']) <= dsource_ids | claims
        assert set(r['inherited_B_component_refs']) <= claims
        assert r['measurement_defined'] == 'protocol_defined_with_gaps' and not r['measurement_validated']
        assert r['real_audio_accuracy'] == 'not_validated_in_D' and r['auditory_label_status'] == 'no_new_listening'
        expected = [v for v in observed['cases'] if r['candidate_entity_id'] in v['candidate_entities']]
        assert r['technical_validation_refs'] == [v['id'] for v in expected]
        assert r['technical_validation_scope'] == ([v['validation_scope'] for v in expected] or ['no_new_algorithm_accuracy_validation'])
        for ref in r['implementation_refs']:
            assert ref['sha256'] == dhashes[ref['path']]
            lines = (ROOT / ref['path']).read_text(encoding='utf-8').splitlines()
            assert ref['anchor'] in lines[ref['line']-1]
    dp = OUT / 'measurement-protocols.csv'
    assert dp.read_bytes().startswith(b'\xef\xbb\xbf')
    with dp.open(encoding='utf-8-sig',newline='') as f:
        expected = [{k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict)) else str(v) for k,v in r.items()} for r in d['rows']]
        assert list(csv.DictReader(f)) == expected
    e = load(OUT / 'description-coverage.json')
    freeze = load(HERE / 'stage_e_freeze_binding.json')
    checklist = load(OUT / 'coverage-checklist.json')
    assert e['status'] == 'coverage_review_complete_with_explicit_gaps'
    assert e['checklist_binding'] == freeze and freeze['frozen_before_mapping']
    assert digest(ROOT / freeze['path']) == freeze['sha256']
    assert digest(ROOT / freeze['checkpoint_path']) == freeze['checkpoint_sha256'] == freeze['sha256']
    assert checklist == load(ROOT / freeze['checkpoint_path'])
    assert digest(ROOT / freeze['checklist_authoring_source']['path']) == freeze['checklist_authoring_source']['sha256']
    assert digest(ROOT / freeze['definition_baseline']['path']) == freeze['definition_baseline']['sha256']
    assert len(checklist['rows']) == len(e['rows']) == e['counts']['case_count'] == 42
    assert checklist['main_count'] == e['counts']['main_mapping'] == 36
    assert checklist['deferred_recheck_count'] == e['counts']['deferred_recheck'] == 6
    for ref in checklist['input_bindings']:
        assert digest(original_path(ROOT / ref['path'],ref['sha256'])) == ref['sha256'], ref['path']
    assert len(checklist['author_structures']) == 3
    for r in checklist['author_structures']:
        assert digest(ROOT / r['path']) == r['sha256']
        assert not r['curve_arrays_exported_or_reused'] and r['auditory_label'] == 'unknown'
    cp = e['main_mapping_checkpoint']
    assert digest(ROOT / cp['path']) == cp['sha256']
    checkpoint = load(ROOT / cp['path'])
    from stage_e_mapping_data import main_mappings
    from stage_e_recheck_data import recheck_mappings
    assert checkpoint['rows'] == main_mappings() and checkpoint['case_count'] == 36
    assert checkpoint['mapping_source_sha256'] == digest(HERE / 'stage_e_mapping_data.py')
    assert checkpoint['frozen_checklist_sha256'] == freeze['sha256']
    authored = {r['case_id']:r for r in main_mappings()+recheck_mappings()}
    drefs = {r['candidate_entity_id']:r for r in d['rows']}
    prior_evidence = load(original_path(OUT / 'conditional-responses.json'))
    prior_records = {r['id']:r for group in ['responses','observations','audits'] for r in prior_evidence[group]}
    assert e['sources'] == checklist['sources'] and len(e['sources']) == 6
    assert len({r['id'] for r in e['sources']}) == 6
    for source in e['sources']:
        assert source['url'].startswith('https://') and all(source[k] for k in ['locator','read_status','scope'])
    for raw,r in zip(checklist['rows'],e['rows']):
        assert all(r[k] == v for k,v in raw.items()), raw['id']
        assert all(r[k] == v for k,v in authored[r['case_id']].items())
        assert r['id'] == r['case_id']
        assert not any(k in raw for k in ['candidate_entity_refs','protocol_refs','mapping_reason'])
        assert set(r['candidate_entity_refs']) <= set(drefs)
        assert r['protocol_refs'] == [drefs[k]['id'] for k in r['candidate_entity_refs']]
        assert all(r[k] for k in ['temporal_or_context_relation','mapping_reason','unexpressed_or_unknown','new_dimension_decision'])
        assert r['user_label_available'] == (raw['label_text']!='unknown')
        assert not any(r[k] for k in ['reliable_measurement_for_case_conclusion','auditory_label_added','independent_audio_holdout','formal_entity_migration'])
        assert r['description_coverage_checked'] == 'reviewed_with_explicit_gaps'
        record = prior_records.get(raw['evidence_key'])
        assert r['historical_record_id'] == (record['id'] if record else '')
        assert r['historical_audio_hash_refs'] == (record.get('bindings',{}).get('delivered_audio',{}) if record else {})
        if r['user_label_available'] and raw['label_kind']=='verbatim':
            assert raw['label_text'] in (ROOT/raw['source_refs'][0]).read_text(encoding='utf-8')
    assert {r['shared_evidence_group'] for r in e['rows'] if r['case_id'] in {'CASE:EU'+str(i) for i in range(11,17)}} == {'brec-six-shared-feedback'}
    assert [r['case_id'] for r in e['rows']] == [r['id'] for r in checklist['rows']]
    assert e['counts']['by_origin'] == dict(Counter(r['origin'] for r in e['rows']))
    assert e['counts']['by_role'] == dict(Counter(r['role'] for r in e['rows']))
    assert e['counts']['by_structure_status'] == {'representable_with_scope':34,'partial_structure':8}
    assert e['counts']['by_structure_status'] == dict(Counter(r['structure_status'] for r in e['rows']))
    assert e['counts']['existing_user_label_rows'] == sum(r['user_label_available'] for r in e['rows']) == 16
    assert e['counts']['reliable_measurement_for_case_conclusion'] == 0
    linked = {x for r in e['rows'] for x in r['candidate_entity_refs']}
    assert len(linked) == e['counts']['distinct_candidate_entities_linked'] == 34
    assert {r['candidate_entity_id'] for r in e['uncovered_candidate_entities']} == set(drefs)-linked
    assert len(e['sampling_axes']) == 9
    for r in e['sampling_axes']:
        assert r['scope'] and set(r['case_refs']) <= set(authored)
    assert set(r['case_id'] for r in e['rows'] if r['review_partition']=='deferred_mapping_recheck') == {'CASE:E'+x for x in ['M10','M12','L04','L05','L07','A04']}
    err = e['identity_errata'][0]
    assert len(e['identity_errata']) == 1 and err['corrected_identity'] == 'word295'
    assert digest(ROOT / err['path']) == err['sha256']
    assert load(ROOT / err['path'])['word295_unknown_retained'] is True
    assert not err['frozen_checklist_rewritten'] and err['label_remains']=='unknown'
    assert not e['all_descriptions_fully_expressible'] and not e['statistical_or_universal_completeness_validated']
    assert not e['all_measurement_methods_validated'] and not e['formal_ids_migrated']
    assert e['stage_F'] == 'not_executed' and e['no_new_audio_or_synthesis'] and e['no_new_auditory_labels']
    ep = OUT / 'description-coverage.csv'
    assert ep.read_bytes().startswith(b'\xef\xbb\xbf')
    with ep.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);actual=list(reader)
        expected=[{k:json.dumps(r[k],ensure_ascii=False,sort_keys=True) if isinstance(r.get(k),(list,dict)) else str(r[k]) if k in r else '' for k in reader.fieldnames} for r in e['rows']]
        assert actual == expected
    formal = load(OUT / 'table1-consolidation.json')
    registry = load(OUT / 'knowledge-table.json')
    migration = load(OUT / 'id-migration.json')
    context = load(OUT / 'context-schema.json')
    correction = load(OUT / 'source-quality-correction.json')
    fbind = load(HERE / 'stage_f_baseline_binding.json')
    assert formal['status'] == 'consolidated_with_explicit_gaps'
    assert formal['formal_entities'] == len(registry['entities']) == 49
    assert formal['entity_types'] == dict(Counter(r['entity_type'] for r in registry['entities'])) == {'ACO':24,'EVT':15,'PER':9,'META':1}
    entity_ids = {r['id'] for r in registry['entities']}
    assert entity_ids == set(drefs)-{'CAND:MULTI_F0'}
    assert not formal['all_measurement_validated'] and not formal['universal_completeness_validated']
    assert formal['table2_special_plan_status'] == 'not_executed'
    assert digest(ROOT / fbind['manifest_path']) == fbind['manifest_sha256']
    assert len(fbind['files']) == 40 and formal['baseline_manifest'] == fbind
    for ref in fbind['files']:
        assert digest(ROOT / ref['snapshot_path']) == ref['sha256']
    for ref in formal['artifacts']:
        assert digest(ROOT / ref['path']) == ref['sha256']
    assert migration['status'] == 'applied_schema_migration_with_explicit_gaps'
    assert set(migration['formal_entity_ids']) == entity_ids
    assert len(migration['open_candidates']) == 1 and migration['open_candidates'][0]['id'] == 'CAND:MULTI_F0'
    assert len(migration['namespaces']['dimension']) == 31
    for lid, ref in migration['namespaces']['dimension'].items():
        assert set(ref['targets']) <= entity_ids and set(m['namespaces']['dimension'][lid]['candidates']) <= set(ref['targets'])
    assert len(registry['composite_descriptors']) == 30 and len(registry['controls']) == 48
    ctrl_ids={r['id'] for r in registry['controls']}
    assert ctrl_ids == {'CTRL:C'+f'{i:02}' for i in range(1,49)}
    assert {x for r in registry['controls'] for x in r['parameter_refs']} == control_ids
    assert sum(r['parameter_count'] for r in registry['controls']) == 352
    for r in registry['controls']:
        assert r['id'] == 'CTRL:'+r['legacy_group_id']
        assert r['parameter_refs'] == [p['id'] for p in c['rows'] if p['group_id']==r['legacy_group_id']]
    for r in registry['entities']:
        assert not r['measurement_validated'] and r['measurement_protocol_ref'] == drefs[r['id']]['id']
        assert set(r['control_family_navigation_refs']) <= ctrl_ids
        assert set(r['source_refs']) <= dsource_ids | claims
        assert r['description_case_refs'] == [v['case_id'] for v in e['rows'] if r['id'] in v['candidate_entity_refs']]
    assert len(context['rows']) == len(registry['context_schema']) == 8
    assert context['rows'] == registry['context_schema'] and not context['measurement_or_causal_rules']
    assert context['unfilled_historical_fields_remain_unknown']
    case_ids={r['case_id'] for r in e['rows']}
    assert len({r['id'] for r in context['rows']})==8
    for r in context['rows']:
        assert r['fields'] and r['unknown_rule'] and set(r['coverage_case_refs'])<=case_ids
    before_registry=load(original_path(OUT/'knowledge-table.json'))
    for key,namespace in [('evidence','project_evidence'),('primary_sources','source'),('mechanisms','code_mechanism')]:
        assert len(registry[key])==len(before_registry[key])
        for old_record,current in zip(before_registry[key],registry[key]):
            assert current['legacy_id']==old_record['id']
            assert current['id']==migration['namespaces'][namespace][old_record['id']]
            assert all(current[k]==v for k,v in old_record.items() if k!='id' and not (key=='mechanisms' and k=='status'))
    for raw,r in zip(composites['rows'],registry['composite_descriptors']):
        assert all(r[k]==v for k,v in raw.items())
        for field in ['candidate_path_A_refs','candidate_path_B_refs']:
            for lid,refs in r[field].items():assert refs==migration['namespaces']['dimension'][lid]['targets']
    def verify_formal_csv(name,rows):
        path=OUT/name;assert path.read_bytes().startswith(b'\xef\xbb\xbf')
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);actual=list(reader)
            expected=[{k:json.dumps(r[k],ensure_ascii=False,sort_keys=True) if isinstance(r.get(k),(list,dict)) else str(r[k]) if k in r else '' for k in reader.fieldnames} for r in rows]
            assert actual==expected,name
    for name,key in [('atomic-manifestations.csv','entities'),('composite-descriptors.csv','composite_descriptors'),
                     ('openutau-controls.csv','controls'),('current-evidence.csv','evidence')]:
        verify_formal_csv(name,registry[key])
    ledger=load(OUT / 'conditional-responses.json')
    restored=json.loads(json.dumps(ledger))
    restored['schema_version']=prior_evidence['schema_version'];del restored['formal_reference_migration']
    assert len(migration['second_layer_links']) == 14
    for group in ['responses','observations','audits']:
        for current,raw in zip(ledger[group],prior_evidence[group]):
            assert current['legacy_atomic_ids']==raw['atomic_ids'] and raw['atomic_ids']
            expected={lid:migration['namespaces']['dimension'][lid]['targets'] for lid in raw['atomic_ids']}
            assert current['entity_reference_candidates']==expected
            assert current['atomic_ids']==sorted({x for v in expected.values() for x in v})
            assert current['control_ids']==['CTRL:'+x for x in raw['control_ids']]
            assert current['evidence_ids']==[migration['namespaces']['project_evidence'][x] for x in raw['evidence_ids']]
        for r in restored[group]:
            r['atomic_ids']=r.pop('legacy_atomic_ids');r['control_ids']=r.pop('legacy_control_ids');r['evidence_ids']=r.pop('legacy_evidence_ids')
            del r['entity_reference_candidates'];del r['reference_role']
    for r in restored['coverage']:r['control_id']=r.pop('legacy_control_id')
    assert restored==prior_evidence,'Original experiment values/labels/bindings changed beyond ID translation'
    readable=(OUT/'conditional-responses.md').read_text(encoding='utf-8')
    old_readable=original_path(OUT/'conditional-responses.md').read_text(encoding='utf-8')
    assert all(line in readable for line in old_readable.splitlines() if line.startswith('|')),'Original readable conditions/timing/response tables lost'
    verify_formal_csv('response-coverage.csv',ledger['coverage'])
    with original_path(OUT/'conditional-responses.csv').open(encoding='utf-8-sig',newline='') as f:old_csv=list(csv.DictReader(f))
    with (OUT/'conditional-responses.csv').open(encoding='utf-8-sig',newline='') as f:new_csv=list(csv.DictReader(f))
    for raw,now,record in zip(old_csv,new_csv,ledger['responses']):
        assert all(now[k]==v for k,v in raw.items() if k not in {'atoms','controls'})
        assert now['legacy_atoms']==raw['atoms'] and now['legacy_controls']==raw['controls']
        assert now['atoms']==';'.join(record['atomic_ids']) and now['controls']==';'.join(record['control_ids'])
    assert correction['status']=='E_mojibake_claim_corrected; no_file_text_corruption_found'
    assert correction['inspected_original_sha256']==digest(original_path(OUT/'conditional-responses.json'))
    assert correction['string_values_inspected']==1174 and correction['replacement_character_count']==0 and correction['latin1_nonascii_string_count']==0
    assert not correction['original_feedback_text_changed'] and len(correction['feedback_report_csv_checks'])==10
    for raw,checked in zip(prior_evidence['responses'],correction['feedback_report_csv_checks']):
        assert checked['verbatim']==raw['user_feedback']['verbatim']
        assert digest(ROOT/checked['report'])==checked['sha256']
    baseline = []
    for name, expected in a['baseline_sha256'].items():
        got = digest(original_path(OUT / name,expected))
        assert got == expected, (name, got)
        baseline.append({'path': (OUT / name).relative_to(ROOT).as_posix(), 'sha256': got})

    protected = load(HERE / 'protected-inputs.json')
    available, unavailable = [], []
    for r in protected['files']:
        p = ROOT / r['path']
        if not p.exists():
            unavailable.append(r['path'])
            continue
        got = digest(p)
        assert got == r['sha256'], f'Protected input changed: {r["path"]}'
        available.append(r)

    links = 0
    docs = [ROOT / n for n in ['plan.md', 'README.md', 'AGENTS.md', 'research/README.md']]
    docs += list(HERE.glob('*.md'))
    docs += [OUT / n for n in ['README.md', 'table1-schema.md', 'table1-review.md', 'table1-source-review.md', 'table1-control-review.md', 'table1-measurement-review.md','table1-coverage-review.md','table1-consolidation-review.md','conditional-responses.md']]
    for p in docs:
        for url in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
            if '://' in url or url.startswith('#'):
                continue
            target = p.parent / url.split('#')[0]
            # This audit file is written below; all other links must exist now.
            if target.resolve() != (OUT / 'table1-execution-audit.json').resolve():
                assert target.exists(), (p, url)
            links += 1
    for p in HERE.glob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'), filename=str(p))

    # Refresh only declared F artifacts; retain original execution/evidence claims.
    inventory = load(OUT / 'control-inventory-audit.json')
    changed = []
    for r in inventory['artifact_sha256']:
        p = ROOT / r['path']
        got = digest(p)
        if got != r['sha256']:
            formal = load(OUT / 'table1-consolidation.json')
            planned = {r['path']:r['sha256'] for r in formal['artifacts']}
            assert p == OUT / 'README.md' or (r['path'] in planned and planned[r['path']]==got), f'Unexpected original artifact change: {p}'
            changed.append({'path': r['path'], 'old_sha256': r['sha256'], 'sha256': got})
            r['sha256'] = got
    if changed:
        inventory['pre_F_counts'] = load(original_path(OUT / 'control-inventory-audit.json'))['counts']
        inventory['formal_schema_counts'] = dict(entities=49,open_candidates=1,descriptors=30,control_groups=48,parameters=352,context_groups=8)
        inventory['formal_migration_note'] = 'Current artifact hashes refreshed for F; original runtime/source/evidence claims retain their original scope. Pre-F inventory preserved by snapshot.'
        (OUT / 'control-inventory-audit.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    names = ['table1-schema.md', 'table1-review.md', 'table1-row-review.csv', 'table1-row-review.json',
             'id-migration.json', 'table1-source-review.md', 'claim-evidence.csv', 'claim-evidence.json',
             'core-definition-review.csv', 'core-definition-review.json', 'composite-review.csv', 'composite-review.json',
             'control-details.csv', 'control-details.json', 'table1-control-review.md',
             'graph-node-review.json','local-capability-review.json','editor-preferences-review.csv','editor-preferences-review.json',
             'measurement-protocols.csv','measurement-protocols.json','measurement-source-review.json','table1-measurement-review.md']
    names += ['coverage-checklist.json','description-coverage.csv','description-coverage.json','table1-coverage-review.md']
    names += ['atomic-manifestations.csv','composite-descriptors.csv','openutau-controls.csv','knowledge-table.json',
              'current-evidence.csv','conditional-responses.csv','conditional-responses.json','conditional-responses.md','response-coverage.csv',
              'context-schema.json','source-quality-correction.json','table1-consolidation.json','table1-consolidation-review.md']
    artifacts = [OUT / n for n in names] + list(HERE.glob('*.py')) + [HERE / 'protected-inputs.json', HERE / 'stage_c_source_bindings.json',HERE / 'stage_c_editor_source_bindings.json']
    artifacts += list((HERE / 'metadata-reader').glob('*.cs')) + list((HERE / 'metadata-reader').glob('*.csproj'))
    artifacts += [HERE / 'stage_d_source_bindings.json']
    artifacts += [HERE / 'stage_e_freeze_binding.json']
    artifacts += [HERE / 'stage_f_baseline_binding.json']
    audit = {
        'schema_version': 1, 'date': '2026-10-10', 'stage_A': 'structural_review_complete',
        'stage_B': 'reviewed_with_explicit_gaps', 'stage_C': c['status'], 'stage_D': d['status'], 'stage_E':e['status'],'stage_F':'consolidated_with_explicit_gaps',
        'checks': {'row_review_count': 31, 'proposed_entities': 47,
                   'linked_second_layer_records': 14, 'literature_claims': len(b['claims']),
                   'source_pages': len({r['url'] for r in b['claims']}),
                   'core_definitions_reviewed': len(core['rows']),
                   'composite_groups_reviewed': len(composites['rows']),
                   'all_scientific_definitions_verified': False,
                   'all_composite_mappings_validated': False,
                   'concrete_control_rows': len(c['rows']), 'control_groups_with_rows': len(groups),
                   'all_concrete_controls_enumerated': False, 'all_local_control_paths_confirmed': False,
                   'local_resource_bindings_rechecked': len(c['installed_bindings_rechecked']),
                   'original_184_control_ids_preserved': True, 'graph_types_enumerated': 31,
                   'original_320_control_ids_preserved': True,
                   'frozen_scope_review_complete_with_gaps': True,
                   'editor_preference_declarations': len(preferences['rows']),
                   'nested_preference_properties': len(preferences['nested_properties']),
                   'fixed_upstream_sources': 86, 'offline_local_capability_entries': len(local['rows']),
                   'offline_DLL_bindings': len(local['bindings']),
                   'observation_protocols': 50, 'measurement_A_entities': 47, 'measurement_extra_candidates': 3,
                   'measurement_component_sources': 10, 'measurement_bound_local_sources': 12,
                   'finite_array_checks': 10, 'all_measurement_methods_validated': False,
                   'coverage_cases':42, 'coverage_main':36,'coverage_process_recheck':6,
                   'structure_representable_with_scope':34,'structure_partial':8,
                   'coverage_existing_label_rows':16,'coverage_reliable_measurement_conclusions':0,
                   'coverage_linked_candidates':34,'coverage_unlinked_candidates':16,
                   'independent_audio_holdout':False,'universal_description_completeness':False,
                   'formal_entities':49,'formal_open_candidates':1,'formal_context_groups':8,
                   'second_layer_actual_ID_migrations':14,'legacy_empty_mapping_issue_corrected':True,
                   'historical_ledger_restored_exact':True,'E_file_corruption_claim_corrected':True,
                   'csv_json_identical': True, 'csv_utf8_bom': True, 'document_links_checked': links,
                   'builder_syntax_checked': True},
        'original_baseline_matches': baseline,
        'protected_inputs': {'verified': available, 'unavailable': unavailable,
                             'scope': 'Explicit repository originals, Skill, published projects and prior evidence bindings; not a rehash of every audio/cache file.'},
        'inventory_bookkeeping_update': 'Only declared F artifact hashes refreshed; pre-F counts and original source/runtime/evidence claims retained; formal counts listed separately.',
        'artifacts': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': digest(p)} for p in artifacts],
        'no_new_audio_or_synthesis': True, 'no_new_auditory_labels': True,
        'no_production_code_project_skill_change': True,
        'scientific_completeness_or_naturalness_validated': False,
        'D_numerical_verification': numerical,
        'E_checklist_binding':freeze,'E_main_mapping_checkpoint':cp,'E_identity_errata':e['identity_errata'],
    }
    if args.verification_run is not None:
        run = args.verification_run.resolve()
        assert run.is_relative_to(ROOT / 'runs/research')
        first_log = run / 'logs/pytest.txt'
        retry_log = run / 'logs/pytest-retry.txt'
        test_log = retry_log if retry_log.is_file() else first_log
        gate_log = run / 'logs/worktree-check.txt'
        test_text = test_log.read_text(encoding='utf-8-sig')
        assert re.search(r'\b88 passed\b',test_text) and not re.search(r'\b(?:failed|errors)\b',test_text)
        gate = json.loads(gate_log.read_text(encoding='utf-8-sig'))
        assert gate['checks']=='passed' and gate['audio_payloads']==0
        assert gate['author_projects']==3 and gate['zip_members']==5
        audit['local_verification'] = dict(pytest='88 passed', worktree_gate=gate,
            test_environment='workspace TEMP/TMP and fresh pytest basetemp',
            retry_used=retry_log.is_file(),
            logs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in dict.fromkeys([first_log,test_log,gate_log])])
        guard_path=run/'observations/frozen-builder-guards.json'
        repeat_path=run/'observations/deterministic-rebuild.json'
        failure_path=run/'observations/guard-first-failure.json'
        guard=load(guard_path);repeat=load(repeat_path)
        assert guard['current_package_bytes_unchanged'] and len(guard['checks'])==6
        assert {r['builder'] for r in guard['checks']}=={'build_stage_a.py','build_stage_b.py','build_stage_c.py','build_stage_d.py','freeze_stage_e.py','build_stage_e.py'}
        assert all(r['returncode']!=0 and 'A–E are frozen review builders' in r['stderr'] for r in guard['checks'])
        assert repeat['status']=='passed' and repeat['same_bytes'] and repeat['count']==15
        repeat_expected={r['path']:r['sha256'] for r in formal['artifacts']}
        repeat_expected[(OUT/'table1-consolidation.json').relative_to(ROOT).as_posix()]=digest(OUT/'table1-consolidation.json')
        assert repeat['artifact_sha256']==repeat_expected
        audit['local_verification']['F_builder_guards_and_exact_rebuild']=dict(guarded_builders=6,exact_rebuild_files=15,
            first_capture_failure_preserved=True,
            bindings=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in [guard_path,repeat_path,failure_path]])
    ci = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    trigger_block = ci.split('on:',1)[1].split('jobs:',1)[0]
    assert trigger_block.strip()=='workflow_dispatch:'
    audit['checks']['CI_manual_only'] = True
    (OUT / 'table1-execution-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'passed', 'A_rows': 31, 'B_claims': len(b['claims']),
                      'B_core_rows': len(core['rows']), 'B_composite_groups': len(composites['rows']),
                      'C_control_rows': len(c['rows']), 'C_groups': len(groups),
                      'D_protocols': 50, 'D_array_checks': 10,
                      'E_cases':42,'E_partial_structure':8,
                      'protected_matches': len(available), 'unavailable': len(unavailable), 'links': links}))

if __name__ == '__main__':
    main()
