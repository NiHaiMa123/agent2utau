"""Add reversible record_v3 structure from bound historical metadata only."""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
OUTPUTS = ['conditional-responses.json', 'conditional-responses.csv', 'conditional-responses.md',
    'table2-record-schema.json', 'table2-schema-migration.json', 'table2-record-structure.csv', 'table2-fields.md', 'table2-schema-review.md']
PARAM = {'TENC': 'PARAM:C13.01', 'SHFC': 'PARAM:C14.01', 'ONSET': 'PARAM:C14.01',
    'GUO': 'PARAM:C14.01', 'BREC': 'PARAM:C12.01'}


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def baseline():
    binding = load(HERE / 'stage_2b_baseline_binding.json')
    assert sha(ROOT / binding['manifest_path']) == binding['manifest_sha256']
    frozen = load(ROOT / binding['manifest_path'])
    for r in frozen['files']:
        assert sha(ROOT / r['snapshot_path']) == r['sha256']
    return binding, {Path(r['path']).name: ROOT / r['snapshot_path'] for r in frozen['files'] if r['path'].startswith('docs/')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    run = ap.parse_args().run.resolve()
    assert run.is_relative_to(ROOT / 'runs/research')
    binding, frozen = baseline()
    assert load(run / 'observations/freeze-binding.json') == binding
    old = load(frozen['conditional-responses.json'])
    ledger = copy.deepcopy(old)
    audited = load(frozen['comparison-bindings.json'])
    assert sha(OUT / 'comparison-bindings.json') == sha(frozen['comparison-bindings.json'])
    sources = {r['path']: r for r in audited['source_bindings'] if r['hash_status'] == 'verified'}
    runtime = {r['group']: r for r in audited['runtime_registry_comparisons']}
    manifests = {}
    for r in audited['sealed_manifests']:
        assert sha(ROOT / r['manifest']) == r['sha256']
        data = load(ROOT / r['manifest'])
        base = (ROOT / r['manifest']).parent
        files = data.get('files', data.get('files_sha256'))
        manifests[r['group']] = {((Path(p) if Path(p).is_absolute() else base / p).relative_to(ROOT).as_posix()): h for p, h in files.items()}

    def source(ref):
        assert ref['path'] in sources and ref['sha256'] == sources[ref['path']]['sha256']
        assert sha(ROOT / ref['path']) == ref['sha256']
        return load(ROOT / ref['path'])

    def sealed_ref(group, path):
        return dict(path=path, sha256=manifests[group][path], binding_role='historical_sealed_manifest_checked_in_2A; not reexecuted_in_2B')

    extensions = {}
    feedbacks = {}
    for r, audit in zip(ledger['responses'], audited['rows'][:10]):
        rid = r['id']
        group = audit['native_and_fresh_artifact_bindings'][0]['role'].split(':')[0]
        cid = rid + ':B-A' if rid != 'RESP-003' else rid + ':C-B'
        response_ref = next(a for a in audit['native_and_fresh_artifact_bindings'] if a['path'].endswith('/fresh/response.json'))
        response_path = response_ref['path']
        assert sha(ROOT / response_path) == response_ref['expected_sha256']
        metadata = load(ROOT / response_path)
        fresh_root = str(Path(response_path).parent).replace('\\', '/')
        variants = []
        for project in audit['project_bindings']:
            label = 'A' if 'project_A' in project['role'] else 'B' if 'project_B' in project['role'] else 'C'
            slot = 'B' if group == 'ONSET' and label == 'C' else label
            origin_group = 'SHFC' if group == 'ONSET' and label == 'B' else group
            origin_fresh = 'runs/lastpage_shfc_probe_20261008/fresh' if group == 'ONSET' and label == 'B' else fresh_root
            artifacts = [sealed_ref(origin_group, f'{origin_fresh}/{slot}_{suffix}') for suffix in ['inputs.npz', 'prediction.npz', 'raw.wav']]
            variants.append(dict(variant_id=rid + ':' + label, logical_label=label, artifact_slot=slot,
                project=dict(path=project['path'], sha256=project['expected_sha256']),
                state_origin=dict(run=str(Path(origin_fresh).parent).replace('\\', '/'),
                    execution='reused_prior_SHFC_B_for_listener' if group == 'ONSET' and label == 'B' else 'fresh_in_historical_experiment',
                    newly_executed_in_2B=False, artifacts=artifacts,
                    inference_stages=['variance', 'acoustic', 'vocoder'],
                    seeds=metadata['seeds'], speaker=metadata['speaker_mix']),
                context_project_scope='accepted_bao_C_in_complete_A_and_B; target_guo_baseline_retained' if group == 'GUO' else 'original_v02_auxiliary_reference' if group == 'ONSET' and label == 'A' else audit['reference_variant'] if (label == 'A' or group == 'ONSET' and label == 'B') else audit['intervention_variant']))
        comparisons = [dict(comparison_id=cid, kind='intervention', reference_variant=rid + (':B' if group == 'ONSET' else ':A'),
            intervention_variant=rid + (':C' if group == 'ONSET' else ':B'),
            direction='C-B' if group == 'ONSET' else 'B-A', operation='signed_delta_intervention_minus_reference; absolute_F0_distance_separate',
            listener_evidence=True)]
        if group == 'ONSET':
            comparisons += [dict(comparison_id=rid + ':' + label + '-A', kind='auxiliary_reference',
                reference_variant=rid + ':A', intervention_variant=rid + ':' + label,
                direction=label + '-A', operation='signed_delta_or_absolute_distance_as_declared', listener_evidence=False) for label in ['B', 'C']]
        condition = r['condition']
        condition_id = condition['id']
        baseline_variant = rid + ':A'
        fg = 'FB:BREC-cohort' if group == 'BREC' else 'FB:' + rid
        fbsource = audit['feedback_source']
        fbdata = source(fbsource)
        if fg not in feedbacks:
            feedbacks[fg] = dict(feedback_group_id=fg, source=fbsource,
                original_text=audit['feedback_original_text'],
                separate_location_messages=fbdata.get('location_user_verbatim', []),
                submission_timestamp='unknown', device='unknown', blinding='unknown', task_protocol='unknown',
                agent_listened=False, record_ids=[], audio_bindings=[])
        feedbacks[fg]['record_ids'].append(rid)
        feedbacks[fg]['audio_bindings'] += audit['actual_listener_bindings']
        metric_refs = []
        if group == 'ONSET':
            for wi, window in enumerate(r['measured']['window_responses']):
                metric_refs.append(dict(pointer=f'/measured/window_responses/{wi}/adjacent_frame_level_removed_mel_shape_RMS',
                    comparison_ids=[], variant_ids=[rid + ':' + l for l in ['A', 'B', 'C']],
                    operation='within_each_variant_adjacent_frame_shape_RMS; not_C_minus_B',
                    unit='level_removed_log_mel_feature_RMS', window_s=window['interval_s'], frames=window['mel_frames']))
                for method, values in window['F0'].items():
                    for pair in values['differences']:
                        first, second = pair.split('_')
                        metric_refs.append(dict(pointer=f'/measured/window_responses/{wi}/F0/{method}/differences/{pair}',
                            comparison_ids=[rid + ':' + second + '-' + first], operation='absolute_cents_distance',
                            unit='cents', window_s=window['interval_s'], frames=values['all_three_comparable_frames']))
            metric_refs.append(dict(pointer='/measured/neighbor_RMS_C_minus_B', comparison_ids=[cid],
                operation='20_log10_RMS_C_over_RMS_B', unit='dB_PCM_RMS_ratio', window_s='per_phone_support_s', frames='PCM_samples_not_model_frames'))
        else:
            for key in r['measured']:
                metric_refs.append(dict(pointer='/measured/' + key, comparison_ids=[cid],
                    operation='see_original_named_metric_and_table2-fields; no_recalculation',
                    unit='see_metric_contract', window_s='per_named_original_window_or_source_metadata', frames='original_comparable_frames_or_unknown'))
        direct = 'manual_tension_increment_cancelled' if group == 'TENC' else 'additional_manual_breathiness_increment' if group == 'BREC' else 'SHFC_acoustic_and_variance_condition_pitch'
        allowed = ['variance_breathiness_voicing_tension_predictions', 'acoustic_mel', 'PCM_and_measured_F0'] if group in ['SHFC', 'ONSET', 'GUO'] else ['acoustic_mel', 'PCM_and_measured_F0']
        ext = dict(record_version=3, record_kind='response', comparison_id=cid, comparisons=comparisons, variants=variants,
            table1_refs=dict(parameter_ids=[PARAM[group]], entity_ids=r['atomic_ids'], control_navigation_ids=r['control_ids'],
                relation='reviewed_control_path_and_schema_candidates; not_measured_occurrences_or_dose_rule'),
            condition_context=dict(identity=condition_id, legacy_pointer='/condition', baseline_state_variant=baseline_variant,
                baseline_state_source=condition['condition_source'],
                baseline_not_comparator=group == 'ONSET',
                runtime_registry=audit['runtime_source_ref'], runtime_registry_entries=runtime[group]['declared_entries'],
                current_runtime_revalidated=False, version_components='per_experiment_registry; absent_members_unknown',
                speaker_clock='separate_native_variance_and_acoustic_frame_clocks; SHA_bound_artifacts',
                source_unknown_changed=condition['source_unknown_changed'],
                neighboring_intervals_and_musical_intent='unknown_unless_explicit_in_original_condition',
                physiological_register_and_formant_truth='unknown'),
            control_layers=dict(external_operation=r['intervention'], direct_input=direct,
                prediction_base=dict(source='variant.state_origin.artifacts/*_prediction.npz', unit='model_feature_units', numerical_summary='unknown_if_not_in_legacy_measured'),
                manual_increment=dict(source='/intervention', unit='UI_storage_then_declared_transform', final_absolute_value='not_the_additional_delta'),
                final_model_input=dict(source='variant.state_origin.artifacts/*_inputs.npz', unit='model_feature_units_not_PCM_dB', clipping_count='unknown_unless_original_bound_report_states_it'),
                baseline_final_summary_pointer='/condition/baseline_actual_state',
                exact_preservation_claim_source='/frozen_inputs', allowed_downstream=allowed,
                historical_actual_response_pointer='/measured', newly_verified_isolation=False,
                unisolated_mediators=['formant', 'physiological_register', 'unique_voice_break_cause'],
                joint_time_geometry=group == 'ONSET'),
            pitch_layers=dict(native_note_target=dict(source='/condition/tone', unit='MIDI_note', clock='native_note/phone_clock'),
                acoustic_condition=dict(source='native_phrase_and_final_inputs', unit='MIDI_condition; native_storage_conversion_separate', clock='native_frame'),
                vocoder_target=dict(source='final_inputs', unit='Hz_F0; baseline_summary_MIDI_separate', clock='native_frame'),
                measured_F0=dict(source='/measured', unit='Hz_or_cents_as_named', clock='detector_output_time',
                    mask='original_comparable_voiced_frames; exact_threshold_unknown_if_absent',
                    invariant_not_implied_by_fixed_vocoder_input=True)),
            metric_bindings=metric_refs, feedback_group_id=fg,
            feedback_interpretation=dict(comparison_id=cid, scope='local_delivered_comparison',
                source_original_text_preserved=True, fine_grained_unreported_labels='unknown',
                whole_phrase_acceptance='unknown', whole_song_acceptance='unknown'),
            state_timeline=[dict(event='historical_execution_metadata', source=sealed_ref(group, response_path),
                flags={k: metadata[k] for k in ['listening_pending', 'naturalness_accepted'] if k in metadata},
                semantics='execution_time_flags; not_later_listener_truth', timestamp='unknown'),
                dict(event='later_user_feedback', source=fbsource, group_id=fg, timestamp='unknown'),
                dict(event='current_summary', source='/status', status=r['status'], causal_or_general_rule_validated=False)],
            historical_binding_ref='comparison-bindings.json#/rows/' + str(len(extensions)),
            record_confirmation='schema_revised_with_explicit_gaps; 2C_not_executed')
        r['record_v3'] = ext
        extensions[rid] = ext

    for index, r in enumerate(ledger['observations'], 10):
        audit = audited['rows'][index]
        rid = r['id']
        is_guo = rid == 'OBS-001'
        labels = ['word112', 'word247'] if is_guo else ['original_A', 'accepted_C']
        cid = rid + ':' + labels[1] + '-' + labels[0]
        refs = audit['related_sources']
        for ref in refs:
            source(ref)
        variants = [dict(variant_id=rid + ':' + l, logical_label=l,
            condition_pointer='/conditions/' + str(i), state_origin=dict(sources=refs,
                artifact_bindings=[a for a in audit['artifact_bindings'] if any(token in a['path'] for token in [f'state_{r["conditions"][i]["context"]:03}.npz', f'phrase_{r["conditions"][i]["context"]:03}.json'])] if is_guo else extensions['RESP-003']['variants'][0 if i == 0 else 2]['state_origin']['artifacts'],
                condition_source=r['conditions'][i].get('condition_source', 'unknown'),
                mapping='original_condition_ID_and_context; no_new_inference',
                execution='historical_state_read_only_association', newly_executed_in_2B=False)) for i, l in enumerate(labels)]
        fg = 'FB:OBS-001' if is_guo else 'FB:RESP-003'
        if is_guo:
            fbref = next(ref for ref in refs if ref['path'].endswith('/feedback.json'))
            fbdata = source(fbref)
            feedbacks[fg] = dict(feedback_group_id=fg, source=fbref, original_text=fbdata['user_text'],
                record_ids=[rid], audio_bindings=dict(playlist_sha256=fbdata['playlist_sha256'], accepted_clip=fbdata['accepted_clip']),
                submission_timestamp='unknown', device='unknown', blinding='unknown', task_protocol='unknown', agent_listened=False,
                conflicting_legacy_field=dict(pointer='accepted_clip/perceptual_label', value=fbdata['accepted_clip']['perceptual_label'],
                    interpretation=fbdata['interpretation'], boundary='legacy_unknown_retained; user_text_supports_word247_local_usable_only; word295_unknown'))
        ext = dict(record_version=3, record_kind='observation', comparison_id=cid,
            comparisons=[dict(comparison_id=cid, kind='association', reference_variant=rid + ':' + labels[0],
                intervention_variant=rid + ':' + labels[1], direction=labels[1] + '-' + labels[0],
                operation='state_summary_difference; not_isolated_intervention', listener_evidence=False)], variants=variants,
            table1_refs=dict(parameter_ids=['PARAM:C11.01', 'PARAM:C12.01', 'PARAM:C13.01', 'PARAM:C14.01'], entity_ids=r['atomic_ids'],
                relation='state_channels_described; no_new_causal_rule'),
            condition_context=dict(legacy_pointer='/conditions', current_runtime_revalidated=False, source_unknown_changed=False),
            control_layers=dict(external_operation='none; observational_pair', final_model_input='legacy condition actual state summaries',
                state_differences_pointer='/state_differences', unit='model_feature_units_or_MIDI_as_named; not_PCM_dB'),
            metric_bindings=[dict(pointer='/state_differences', comparison_ids=[cid], operation='second_minus_first_state_summary',
                unit='model_feature_units_and_MIDI_per_named_field', window_s='original_named_windows', frames='original_n_or_unknown')],
            feedback_group_id=fg, feedback_interpretation=dict(direct_listener_comparison=False,
                label_evidence='word247_middle_clip_local_usable' if is_guo else 'C_local_accepted_in_RESP-003_C-B; no_direct_C-A_listening'),
            state_timeline=[dict(event='historical_observation', sources=refs),
                dict(event='current_summary', source='/status', status=r['status'], causal_or_general_rule_validated=False)],
            historical_binding_ref='comparison-bindings.json#/rows/' + str(index),
            record_confirmation='schema_revised_with_explicit_gaps; 2C_not_executed')
        r['record_v3'] = ext
        extensions[rid] = ext

    for index, r in enumerate(ledger['audits'], 12):
        audit = audited['rows'][index]
        rid = r['id']
        episodes = [('native_g_uo', 'HFA_observation')] if rid == 'AUD-001' else [('SHFC_4c_rejected', 'SHFC_400c_intended'), ('BREC_1tick_rejected', 'BREC_5tick_effective')]
        for ref in audit['related_sources']:
            source(ref)
        comparisons = [dict(comparison_id=rid + ':' + b + '-' + a, kind='technical_audit',
            reference_variant=rid + ':' + a, intervention_variant=rid + ':' + b,
            direction=b + '-' + a, operation='clock_or_encoding_check; not_auditory_effect', listener_evidence=False) for a, b in episodes]
        ext = dict(record_version=3, record_kind='technical_audit', comparison_id=comparisons[0]['comparison_id'], comparisons=comparisons,
            variants=[dict(variant_id=rid + ':' + label, logical_label=label, state_origin=dict(sources=audit['related_sources'],
                execution='historical_technical_check; rejected_draft_not_effect_sample', newly_executed_in_2B=False)) for pair in episodes for label in pair],
            table1_refs=dict(parameter_ids=['PARAM:C23.03', 'PARAM:C23.05', 'PARAM:C24.01'] if rid == 'AUD-001' else ['PARAM:C12.01', 'PARAM:C14.01', 'PARAM:C36.04', 'PARAM:C36.05', 'PARAM:C47.06'], entity_ids=r['atomic_ids'], control_navigation_ids=r['control_ids'],
                relation='specific_field_review_reference_for_identity_units_or_encoding; no_auditory_or_all_group_parameter_validation'),
            condition_context=dict(source_unknown_changed=False, current_runtime_revalidated=False),
            control_layers=dict(external_operation='technical_identity_or_encoding_check', findings_pointer='/finding', boundary_pointer='/boundary'),
            metric_bindings=[], feedback_group_id=None,
            state_timeline=[dict(event='historical_technical_check', sources=audit['related_sources'], listener_outcome='not_applicable')],
            historical_binding_ref='comparison-bindings.json#/rows/' + str(index),
            record_confirmation='schema_revised_with_explicit_gaps; 2C_not_executed')
        r['record_v3'] = ext
        extensions[rid] = ext

    ledger['schema_version'] = 3
    ledger['table2_schema_revision'] = dict(stage='2B', date='2026-10-10', status='schema_revised_with_explicit_gaps',
        baseline=binding, added_record_key='record_v3', legacy_payload_unchanged=True,
        feedback_groups=list(feedbacks.values()), runtime_registry_scope=audited['runtime_registry_comparisons'],
        no_new_synthesis_measurement_listening_or_runtime_execution=True, stage_2C='not_executed')
    dump(OUT / 'conditional-responses.json', ledger)
    with frozen['conditional-responses.csv'].open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
        fields = reader.fieldnames + ['record_version', 'comparison_id', 'feedback_group_id', 'record_v3']
    for r in csv_rows:
        ext = extensions[r['id']]
        r.update(record_version='3', comparison_id=ext['comparison_id'], feedback_group_id=ext['feedback_group_id'] or '',
            record_v3=json.dumps(ext, ensure_ascii=False, sort_keys=True))
    with (OUT / 'conditional-responses.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)
    with (OUT / 'table2-record-structure.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'record_kind', 'comparison_id', 'feedback_group_id', 'record_v3'])
        writer.writeheader()
        writer.writerows(dict(id=rid, record_kind=ext['record_kind'], comparison_id=ext['comparison_id'],
            feedback_group_id=ext['feedback_group_id'] or '', record_v3=json.dumps(ext, ensure_ascii=False, sort_keys=True)) for rid, ext in extensions.items())
    readable = frozen['conditional-responses.md'].read_text(encoding='utf-8')
    prefix = '# 表2现行结构：schema 3（2B）\n\n'
    prefix += '14条记录保留原值，新增record_v3。比较、逻辑版本/文件标签、基底/增量/最终输入/PCM、反馈组与时态分开。'
    prefix += ' [字段说明](table2-fields.md)、[迁移](table2-schema-migration.json)、[2B报告](table2-schema-review.md)、[原字节快照](history/pre-table2-2b-20261010/snapshot-manifest.json)。2C未执行。\n\n'
    table = '| 记录 | 主比较ID | 状态来源/反馈边界 |\n|---|---|---|\n'
    for rid, ext in extensions.items():
        note = 'fresh/B标签对应新C；旧B复用；A基底不是B' if rid == 'RESP-003' else 'C-B局部反馈借用，不是C-A试听' if rid == 'OBS-002' else '技术审计，无听觉效果比较' if rid.startswith('AUD') else str(ext['feedback_group_id'])
        table += f'| {rid} | {ext["comparison_id"]} | {note} |\n'
    (OUT / 'conditional-responses.md').write_text(prefix + table + '\n## 原阶段叙述（数值与时态保留，现行结构以上方为准）\n\n' + readable, encoding='utf-8')
    dump(OUT / 'table2-schema-migration.json', dict(stage='2B', from_schema_version=2, to_schema_version=3,
        source=dict(path=str(frozen['conditional-responses.json'].relative_to(ROOT)).replace('\\', '/'), sha256=sha(frozen['conditional-responses.json'])),
        restore_operation='Remove table2_schema_revision and every record_v3; set schema_version=2. Deep JSON equality with frozen source required. CSV remove four new columns; all old cells identical. Markdown original body retained verbatim after explicit current prefix.',
        baseline=binding, record_ids=list(extensions), legacy_fields_not_overwritten=True,
        onset_file_label_mapping=dict(logical_C='ONSET/fresh/B_*', logical_B='SHFC/fresh/B_* reused', proof=[sealed_ref('ONSET', 'runs/lastpage_shfc_onset_probe_20261008/' + n) for n in ['package.py', 'analyze.py']]),
        historical_audits='F and 2A apply to frozen versions; not overwritten to claim current schema3 approval',
        original_source_index='response-source-audit.json remains historical36; comparison-bindings.json indexes verified52 and preserves misnamed optional candidate',
        newly_validated_measurements=0, new_listener_feedback=0))
    dump(OUT / 'table2-record-schema.json', dict(
        **{'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': 'urn:agent2utau:table2:record-v3'},
        title='Table2 record_v3 extension', type='object',
        required=['record_version', 'record_kind', 'comparison_id', 'comparisons', 'variants', 'table1_refs', 'condition_context',
            'control_layers', 'metric_bindings', 'feedback_group_id', 'state_timeline', 'historical_binding_ref', 'record_confirmation'],
        properties=dict(record_version=dict(const=3), record_kind=dict(enum=['response', 'observation', 'technical_audit']),
            comparison_id=dict(type='string', minLength=1),
            comparisons=dict(type='array', minItems=1, items=dict(type='object', required=['comparison_id', 'kind', 'reference_variant', 'intervention_variant', 'direction', 'operation', 'listener_evidence'],
                properties=dict(listener_evidence=dict(type='boolean')))),
            variants=dict(type='array', minItems=2, items=dict(type='object', required=['variant_id', 'logical_label', 'state_origin'])),
            table1_refs=dict(type='object'), condition_context=dict(type='object'), control_layers=dict(type='object'),
            metric_bindings=dict(type='array'), feedback_group_id=dict(type=['string', 'null']), state_timeline=dict(type='array', minItems=1),
            historical_binding_ref=dict(type='string'), record_confirmation=dict(const='schema_revised_with_explicit_gaps; 2C_not_executed'))))
    print(json.dumps(dict(status='schema_revised_with_explicit_gaps', records=len(extensions),
        comparisons=sum(len(v['comparisons']) for v in extensions.values()), feedback_groups=len(feedbacks), outputs=len(OUTPUTS))))


if __name__ == '__main__':
    main()
