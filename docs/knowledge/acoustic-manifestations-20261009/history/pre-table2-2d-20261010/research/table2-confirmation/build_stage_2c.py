"""Review record claims against sealed metadata and input arrays, never PCM."""
import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from stage_2c_inputs import arithmetic, changed, check_fresh, check_native, clock, tensors

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
STATUS = 'record_review_complete_with_explicit_gaps'
OUTPUTS = ['conditional-responses.json', 'conditional-responses.csv', 'conditional-responses.md',
    'table2-record-structure.csv', 'table2-record-schema.json', 'table2-record-confirmation.json',
    'table2-record-confirmation.csv', 'table2-record-confirmation.md', 'table2-confirmation-migration.json']


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_csv(p, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: json.dumps(r[k], ensure_ascii=False, sort_keys=True) if isinstance(r.get(k), (dict, list)) else str(r[k]) if k in r else '' for k in fields} for r in rows)


def baseline():
    binding = load(HERE / 'stage_2c_baseline_binding.json')
    assert sha(ROOT / binding['manifest_path']) == binding['manifest_sha256']
    freeze = load(ROOT / binding['manifest_path'])
    for r in freeze['files']:
        assert sha(ROOT / r['snapshot_path']) == r['sha256']
    docs = {Path(r['path']).name: ROOT / r['snapshot_path'] for r in freeze['files'] if r['path'].startswith('docs/')}
    return binding, freeze, docs


def subset_equal(legacy, source):
    """Count original scalar leaves checked, retaining supplementary legacy flags."""
    if isinstance(legacy, dict):
        assert isinstance(source, dict)
        return sum(subset_equal(v, source[k]) for k, v in legacy.items() if k != 'historical_perceived_improvement_field_is_not_listener_truth')
    if isinstance(legacy, list):
        assert len(legacy) == len(source)
        return sum(subset_equal(a, b) for a, b in zip(legacy, source))
    assert legacy == source, (legacy, source)
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    run = ap.parse_args().run.resolve()
    assert run.is_relative_to(ROOT / 'runs/research')
    binding, freeze, docs = baseline()
    assert load(run / 'observations/freeze-binding.json') == binding
    old = load(docs['conditional-responses.json'])
    audited = load(docs['comparison-bindings.json'])
    expected = {r['path']: r['sha256'] for r in audited['source_bindings'] if r['hash_status'] == 'verified'}
    for ref in audited['sealed_manifests']:
        assert sha(ROOT / ref['manifest']) == ref['sha256']
        mp = ROOT / ref['manifest']
        data = load(mp)
        for k, h in data.get('files', data.get('files_sha256')).items():
            p = Path(k) if Path(k).is_absolute() else mp.parent / k
            key = p.relative_to(ROOT).as_posix()
            if key in expected:
                assert expected[key] == h
            expected[key] = h
    for ref in freeze['array_inputs']:
        assert expected[ref['path']] == ref['sha256']
    reads = {}
    arrays = {}
    metadata = {}

    def read(path, role):
        key = str(path).replace('\\', '/')
        p = ROOT / key
        assert p.resolve().is_relative_to(ROOT) and key in expected
        assert p.suffix in ['.json', '.npz', '.py', '.md'], 'PCM/mel/model reads forbidden'
        assert not p.name.endswith(('_mel.npy',))
        h = sha(p)
        assert h == expected[key], key
        reads.setdefault(key, dict(path=key, sha256=h, roles=[]))['roles'].append(role)
        if p.suffix == '.npz':
            assert p.name.endswith(('_inputs.npz', '_prediction.npz')), 'No detector or waveform arrays'
            if key not in arrays:
                with np.load(p, allow_pickle=False) as archive:
                    arrays[key] = {k: archive[k] for k in archive.files}
                assert all(np.isfinite(a).all() for a in arrays[key].values())
            return arrays[key]
        if p.suffix == '.json':
            if key not in metadata:
                metadata[key] = load(p)
            return metadata[key]
        return p.read_text(encoding='utf-8')

    def native_paths(audit, label):
        suffix = f'/native_{label}/'
        refs = [r['path'] for r in audit['native_and_fresh_artifact_bindings'] if suffix in r['path']]
        phrase = [p for p in refs if '/phrase_' in p and p.endswith('.json')]
        variance = [p for p in refs if '/variance_' in p and p.endswith('.json')]
        assert len(phrase) == len(variance) == 1
        return phrase[0], variance[0]

    proof_rows = []
    review_rows = []
    study = read('runs/lastpage_cross_condition_study_20261008/study.json', 'conditions:baseline_source')
    study_labels = {r['id']: r for r in study['known_labels']}
    for index, (record, audit) in enumerate(zip(old['responses'], audited['rows'][:10])):
        rid = record['id']
        ext = record['record_v3']
        variant_map = {v['logical_label']: v for v in ext['variants']}
        onset = rid == 'RESP-003'
        brec = index >= 4
        target_label = 'C' if onset else 'B'
        operation = 'tension_cancel' if index == 0 else 'breathiness_delta' if brec else 'shfc_shift'
        an, av = native_paths(audited['rows'][1] if onset else audit, 'A')
        bn, bv = native_paths(audit, target_label)
        native_a, native_b, variance_a, variance_b = [read(p, rid + ':native') for p in [an, bn, av, bv]]
        support = record['intervention'].get('support_s', record['intervention'].get('Q5_anchors_s'))
        if onset:
            support = read(record['prior_run'] + '/intervention.json', rid + ':design')['new_support_s']
        support = [support[0], support[-1]]
        peak = record['intervention'].get('peak_cents', -400 if onset else None)
        native_check = check_native(native_a, native_b, variance_a, variance_b, operation, support, peak)
        label_source = study_labels[record['condition']['id']]
        baseline_leaves = subset_equal(record['condition']['baseline_actual_state'], label_source['metrics'])
        assert record['condition']['vowel_s'] == label_source['vowel_s']
        source_variants = [variant_map['A'], variant_map[target_label]]
        loaded = []
        for v in source_variants:
            refs = v['state_origin']['artifacts']
            loaded += [read(ref['path'], rid + ':fresh') for ref in refs if ref['path'].endswith('.npz')]
        ia, pa, ib, pb = loaded
        fresh_dir = Path(source_variants[0]['state_origin']['artifacts'][0]['path']).parent.as_posix()
        ri = read(fresh_dir + '/A_repeat_inputs.npz', rid + ':repeat')
        rp = read(fresh_dir + '/A_repeat_prediction.npz', rid + ':repeat')
        fresh_check = check_fresh(native_a, native_b, ia, ib, pa, pb, operation, ri, rp)
        response_path = str(Path(source_variants[-1]['state_origin']['artifacts'][0]['path']).parent / 'response.json').replace('\\', '/')
        fresh_report = read(response_path, rid + ':execution_metadata')
        assert set(fresh_report['fresh_final_changed_inputs']) == set(fresh_check['changed_final_inputs'])
        assert fresh_report['fresh_variance_prediction_exact'] == (not fresh_check['changed_predictions'])
        assert fresh_report['isolation']['changed_frames'] == native_check['finite_support']['changed_frames']
        assert fresh_report['seeds'] == {'variance': 11, 'acoustic': 101}
        if 'fresh_prediction_changes' in fresh_report:
            for k, maximum in fresh_report['fresh_prediction_changes'].items():
                assert float(np.max(np.abs(pa[k] - pb[k]))) == maximum
        if onset:
            b_paths = native_paths(audited['rows'][1], 'B')
            old_b, old_vb = [read(p, rid + ':old_B') for p in b_paths]
            old_refs = variant_map['B']['state_origin']['artifacts']
            old_ib, old_pb = [read(ref['path'], rid + ':old_B_fresh') for ref in old_refs if ref['path'].endswith('.npz')]
            native_check['primary_C_minus_B'] = check_native(old_b, native_b, old_vb, variance_b, 'shfc_onset', support,
                -400, unshifted_variance_pitch=tensors(variance_a)['pitch'])
            fresh_check['primary_C_minus_B'] = dict(changed_final_inputs=changed(old_ib, ib), changed_predictions=changed(old_pb, pb),
                original_B_waveform_reused=True, B_repeat_not_newly_executed=True)
            isolated = read(record['prior_run'] + '/native_isolation.json', rid + ':historical_isolation')
            assert isolated['previous_B_to_C_changed_shift_frames'] == native_check['primary_C_minus_B']['finite_support']['changed_frames'] == 12
        if brec:
            d = fresh_check['final_channel_delta_stats']['breathiness']
            assert d['min'] == record['measured']['input_delta_min'] and d['max'] == record['measured']['input_delta_max']
        # Direct array-derived checks are separate from source-matched PCM/F0 observations.
        metrics = []
        def match(pointer, path, source_pointer, value):
            result = read(path, rid + ':metric_source')
            for key in source_pointer.strip('/').split('/') if source_pointer else []:
                result = result[int(key)] if isinstance(result, list) else result[key]
            leaves = subset_equal(value, result)
            metrics.append(dict(record_pointer=pointer, source=dict(path=path, sha256=expected[path], pointer=source_pointer),
                scalar_leaves_equal=leaves, status='historical_value_source_matched; no_PCM_or_detector_remeasurement'))
        base = record['prior_run']
        measured = record['measured']
        if index in [0, 1]:
            match('/measured/PCM_vowel_metrics', base + '/delivery_check.json', '/metrics', measured['PCM_vowel_metrics'])
            ratio = measured['PCM_vowel_metrics']
            assert math.isclose(20 * math.log10(ratio['ao_RMS_B'] / ratio['ao_RMS_A']), ratio['ao_level_change_db'], abs_tol=1e-12)
            if index == 0:
                match('/measured/actual_dual_F0', base + '/actual_dual_f0.json', '/summary', measured['actual_dual_F0'])
            else:
                match('/measured/variance_prediction_response', base + '/prediction_response.json', '/rows', measured['variance_prediction_response'])
                pred_times = clock(native_a, ia['f0'].size)
                for k, values in measured['variance_prediction_response'].items():
                    delta = (pb[k] - pa[k]).ravel()
                    mask = delta != 0
                    outside = (pred_times < support[0]) | (pred_times > support[1])
                    assert int(mask.sum()) == values['changed_frames']
                    assert int((mask & outside).sum()) == values['changed_outside_selected_support']
                    assert float(np.max(np.abs(delta))) == values['max_abs_change']
                for method, value in measured['first_65ms_F0_B_minus_A'].items():
                    match('/measured/first_65ms_F0_B_minus_A/' + method,
                        'runs/lastpage_shfc_onset_probe_20261008/onset_response.json', '/windows/1/F0/' + method + '/differences/A_B', value)
                artifact = read('runs/lastpage_shfc_artifact_audit_20261008/audit.json', rid + ':artifact_boundary')
                assert all(v == 0 for case in artifact['feature_clipped_frames'].values() for v in case.values())
                assert not artifact['artifact_detector_validated'] and artifact['exact_artifact_sample_unknown']
        elif onset:
            match('/measured/window_responses', base + '/onset_response.json', '/windows', measured['window_responses'])
            match('/measured/neighbor_RMS_C_minus_B', base + '/neighbor_response.json', '', measured['neighbor_RMS_C_minus_B'])
            for item in read(base + '/neighbor_response.json', rid + ':RMS_formula'):
                assert math.isclose(20 * math.log10(item['vocal_RMS']['C'] / item['vocal_RMS']['B']), item['B_C_rms_change_db'], abs_tol=1e-12)
        elif index == 3:
            phone_source = read(base + '/phone_response.json', rid + ':phones')
            source_by_support = {(r['phone'], tuple(r['support_s'])): i for i, r in enumerate(phone_source['phones'])}
            for j, item in enumerate(measured['phones']):
                si = source_by_support[(item['phone'], tuple(item['support_s']))]
                match('/measured/phones/' + str(j), base + '/phone_response.json', '/phones/' + str(si), item)
                raw = phone_source['phones'][si]
                assert math.isclose(20 * math.log10(raw['vocal_RMS']['B'] / raw['vocal_RMS']['A']), raw['AB_level_change_db'], abs_tol=1e-12)
            report = read(record['report'], rid + ':rounded_proxies')
            assert measured['reported_30ms_min_change_db'] == -4.2 and '-4.200dB' in report
            assert measured['reported_2_to_5kHz_uo_change_db'] == -4.032 and '-4.032dB' in report
            metrics.append(dict(record_pointer='/measured/reported_*', source=dict(path=record['report'], sha256=expected[record['report']]),
                status='rounded_report_proxy_matched; no_precise_listener_location_or_PCM_remeasurement'))
        else:
            analysis = read(base + '/response_analysis.json', rid + ':analysis')
            si = next(i for i, r in enumerate(analysis['conditions']) if r['id'] == record['condition']['id'])
            match('/measured', base + '/response_analysis.json', '/conditions/' + str(si), measured)
        feedback = next(g for g in old['table2_schema_revision']['feedback_groups'] if g['feedback_group_id'] == ext['feedback_group_id'])
        fb = read(feedback['source']['path'], rid + ':feedback')
        # Metadata time/flags remain historical; user verdict is independently bound.
        verdict = record['status']['auditory_outcome']
        proof = dict(record_id=rid, primary_comparison_id=ext['comparison_id'], native_check=native_check,
            fresh_check=fresh_check, source_metric_checks=metrics,
            baseline_state_source=dict(path='runs/lastpage_cross_condition_study_20261008/study.json',
                condition_id=record['condition']['id'], variant='original_A' if onset else 'case_A', scalar_leaves_equal=baseline_leaves),
            historical_wave_repeat=dict(reported_max_abs=fresh_report['repeat_wave_max_abs'], newly_PCM_checked=False),
            no_current_native_cache_reexecution=True, no_new_model_or_PCM_execution=True)
        proof_rows.append(proof)
        row = dict(record_id=rid, record_kind='response', status=STATUS,
            comparison_id=ext['comparison_id'], input_review='native_and_fresh_input_math_rechecked',
            input_proof=proof, metric_review='historical_value_source_matched; PCM_mel_F0_not_remeasured',
            feedback=dict(group_id=ext['feedback_group_id'], source=feedback['source'], original_text=feedback['original_text'],
                outcome=verdict, audio_SHA_bindings=feedback['audio_bindings'], new_feedback=False,
                device_blinding_timestamp='unknown', listener_scope='original_local_comparison'),
            confirmed=['declared_external_input_and_downstream_path_within_loaded_sealed_inputs', 'original_numeric_values_and_comparison_direction_traceable', 'original_user_feedback_and_local_adoption_scope'],
            partial=['historical_PCM_mel_F0_metrics_source_confirmed_but_not_remeasured_or_detector_validated', 'historical_runtime_and_wave_determinism_not_current_execution'],
            unknown=['unique_causal_mediator', 'unreported_fine_grained_side_effects', 'whole_phrase_or_song_acceptance', 'held_out_or_cross_song_generalization', 'current_external_models_and_real_device_gain'],
            use_boundary=record['usage_boundary'], numerical_response_is_listener_improvement=False,
            general_rule_validated=False, record_content_or_original_feedback_changed=False)
        review_rows.append(row)

    # Three negative specimens must be refused by the new independent checker.
    first = old['responses'][0]
    p0, v0 = native_paths(audited['rows'][0], 'A')
    p1, v1 = native_paths(audited['rows'][0], 'B')
    a, b, va, vb = [read(p, 'negative_control_reference') for p in [p0, p1, v0, v1]]
    specimens = []
    for label in ['changed_phone', 'outside_support', 'nonselected_manual']:
        bad = copy.deepcopy(b)
        support = first['intervention']['support_s']
        if label == 'changed_phone':
            bad['phones'][0]['phoneme'] = 'invalid'
        elif label == 'nonselected_manual':
            bad['expression_deltas']['voicing'][0] += 1
        else:
            support = [0, .01]
        try:
            check_native(a, bad, va, vb, 'tension_cancel', support)
        except AssertionError:
            specimens.append(dict(specimen=label, refused=True))
        else:
            raise AssertionError('Undeclared confound accepted')

    study = read('runs/lastpage_cross_condition_study_20261008/study.json', 'OBS:state_source')
    for i, record in enumerate(old['observations'], 10):
        key = 'guo_cross_context' if record['id'] == 'OBS-001' else 'bao_same_context_SHFC'
        count = subset_equal(record['state_differences'], study['pair_differences'][key])
        # Recheck the stored pair arithmetic, using source medians rather than audio/NPZ.
        labels = {r['id']: r for r in study['known_labels']}
        a, b = [labels[c['id']] for c in record['conditions']]
        for window, values in record['state_differences'].items():
            for channel, delta in values.items():
                assert b['metrics'][window][channel]['median'] - a['metrics'][window][channel]['median'] == delta
        review_rows.append(dict(record_id=record['id'], record_kind='observation', status=STATUS,
            comparison_id=record['record_v3']['comparison_id'], input_review='stored_state_summary_and_pair_arithmetic_rechecked; no_independent_intervention',
            metric_review=dict(source='runs/lastpage_cross_condition_study_20261008/study.json#/pair_differences/' + key, scalar_leaves_equal=count),
            feedback=record['record_v3']['feedback_interpretation'],
            confirmed=['original_pair_identity_and_state_difference_direction', 'local_label_origin'],
            partial=['state_association_with_context_and_joint_intervention_confound'],
            unknown=['isolated_VOIC_BREC_TENC_mediation', 'held_out_or_general_rule'],
            use_boundary=record['conclusion'], general_rule_validated=False, record_content_or_original_feedback_changed=False))
    phoneme = read('runs/lastpage_guo_phoneme_audit_20261008/audit.json', 'AUD-001:source')
    assert phoneme['target_actual_tokens_languages_match'] and phoneme['uo_one_token_not_automatic_u_o_split']
    assert not phoneme['timing_listening_truth_verified'] and not phoneme['cause_confirmed']
    cohort = read('runs/lastpage_brec_cohort_probe_20261008/cohort.json', 'AUD-002:encoding')
    shift_design = read('runs/lastpage_shfc_probe_20261008/intervention.json', 'AUD-002:units')
    assert cohort['rejected_grid1_draft_retained'] and cohort['native_5tick_encoding_correction']
    assert shift_design['peak_cents'] == -400 and shift_design['rejected_draft']
    for record in old['audits']:
        review_rows.append(dict(record_id=record['id'], record_kind='technical_audit', status=STATUS,
            comparison_id=record['record_v3']['comparison_id'], input_review='bound_historical_identity_or_rejection_correction_record',
            metric_review='unit_clock_mapping_and_valid_version_role; not_auditory_effect',
            feedback='not_applicable', confirmed=['original_technical_finding_and_rejected_version_exclusion'],
            partial=['historical_source_scope; current_device_or_external_model_not_reexecuted'],
            unknown=['auditory_naturalness_or_unique_cause'], use_boundary=record['boundary'],
            general_rule_validated=False, record_content_or_original_feedback_changed=False))

    # Every read file is rehashed after the review; no array values are published.
    for ref in reads.values():
        assert sha(ROOT / ref['path']) == ref['sha256']
        ref['roles'] = sorted(set(ref['roles']))
    proof_path = run / 'input-rechecks.json'
    dump(proof_path, dict(rows=proof_rows, negative_specimens=specimens, read_bindings=list(reads.values()),
        input_prediction_arrays_read=len(arrays), array_values_published=False,
        PCM_or_mel_or_detector_arrays_read=False, model_or_native_engine_executed=False))
    statuses = {k: [dict(record_id=r['record_id'], scope=v) for r in review_rows for v in r[k]] for k in ['confirmed', 'partial', 'unknown']}
    package = dict(stage='2C', date='2026-10-10', status=STATUS, baseline=binding,
        rows=review_rows, status_lists=statuses, counts=dict(records=len(review_rows), intervention_records=10, designs=5,
            observations=2, technical_audits=2, input_prediction_arrays_read=len(arrays), read_bound_files=len(reads),
            metric_scalar_leaves_source_matched=sum(c.get('scalar_leaves_equal', 0) for r in proof_rows for c in r['source_metric_checks']),
            new_synthesis=0, new_PCM_or_detector_measurements=0, new_feedback=0, general_rules_validated=0),
        independent_input_proof=dict(path=proof_path.relative_to(ROOT).as_posix(), sha256=sha(proof_path)),
        feedback_groups=old['table2_schema_revision']['feedback_groups'],
        semantic_boundaries=['numeric_response_not_auditory_improvement', 'fixed_vocoder_input_not_fixed_measured_F0',
            'no_file_clipping_not_no_voice_break', 'C_local_accepted_not_full_song', 'BREC6_share1_feedback_not6_independent_replies',
            'same_seed_repeat_not_generalization', 'OBS2_C_A_association_uses_C_B_label_not_direct_C_A_listening'],
        next_stage='2D_not_executed; protocol_and_scope_before_new_causal_render_or_listening')
    dump(OUT / 'table2-record-confirmation.json', package)
    write_csv(OUT / 'table2-record-confirmation.csv', review_rows)
    text = ['# 表2 2C：逐行记录确认', '',
        '2026-10-10。状态record_review_complete_with_explicit_gaps。14条记录完成来源、比较、输入声明、历史指标与反馈结论复核。这里的“确认”限列明记录/数学范围，缺口继续公开；未确认通用响应规律。', '',
        '本轮读取60份输入/预测NPZ，129份明确SHA绑定的实际读取文件保持；823处原指标标量字段与来源匹配，20份A/目标最终输入另由独立验证器重建检查。逐记录列出36项限定确认、24项部分确认及56项unknown，均为声明范围，不是36个新实验/检测器或独立反馈。原2A的52份来源、67保护输入及26更新前快照另核对。', '',
        '[机器报告](table2-record-confirmation.json)含已确认/部分/未知逐项清单，[CSV](table2-record-confirmation.csv)同14行；[本轮审计](table2-stage-2c-audit.json)绑定检查和本地日志。[更新前快照](history/pre-table2-2c-20261010/snapshot-manifest.json)保存26份原字节和40份输入/预测数组SHA（不复制数组）。', '',
        '本轮只读核查原生输入JSON和封存fresh输入/预测NPZ，包括明确manifest绑定的A-repeat。独立检查直接通道/variance条件、支撑、SHFC浮点运算、人工增量与clip(pred+delta)、fresh通道/预测变化、输入/预测重复。没有运行原生引擎/模型、重新解码PCM、读取mel/检测器数组或生成新F0；原波形重复、DYN/混音/PCM代理仍是历史检查，不伪称本轮重验波形。speaker tensor精确保持不等于重新验证当前embedding/安装。', '',
        '| 记录 | 输入/比较复核 | 用户或使用边界 |', '|---|---|---|']
    for r in review_rows:
        feedback = r['feedback']['outcome'] if r['record_kind'] == 'response' else r['record_kind'] + '；非独立听觉因果比较'
        text.append(f'| {r["record_id"]} | {r["comparison_id"]}；{r["input_review"]} | {feedback} |')
    text += ['', '抱C：本轮fresh/B槽位为逻辑C，原A→C输入检查与主C-B检查分开；旧B未重新声码器执行。C-B仅12帧条件采样改变，平台/退出保持；完整预测可改变平台/邻字，不能独立归因“提前”与“拉长”。用户“可以”只支持3:04抱C局部使用，细分破音/咬字、乐句/全曲仍unknown。', '',
        '果：完整A来自接受抱C；uo RMS +0.090115dB与用户响度下降反馈并存。原报告-4.200dB短窗及-4.032dB频带是舍入代理，未作为用户精确位置或主观响度真值。保留用户“好像”的不确定表达，不采用果SHFC B，也不否定抱C局部接受。', '',
        'BREC：六个_grid5有效版本只改变breathiness最终输入，fresh预测相同；额外-10、基底曲线和最终状态分开，模型增量不写成PCM dB。六条仍共一份“全部没区别。”和12音频SHA，不用未报告副作用补造“全无副作用”。阴性反馈限定当前剂量/条件，不将通道整体判无效。', '',
        'TENC取消已有+14未获可感知差别支持；SHFC -400c“更实”伴抱字头破音，不采用B。无满幅削波只排除文件满幅，破音种类/生理寄存器/共振峰与唯一中介unknown。固定vocoder F0与原实测40–45c局部检测差不矛盾。', '',
        'OBS001是word247与word112跨上下文关联，word295仍unknown；OBS002为接受C与原A状态关联，其局部可用标签来自C-B，不伪造C-A听觉比较。AUD001合法g/uo映射与近似时钟不等于自然时长/咬字通过；AUD002拒绝4c/1tick草稿，保留400c/5tick有效版本，不能算新增听觉实验。', '',
        '历史声学数值按原JSON逐叶匹配并检查RMS比的dB方向、明确窗与帧数；高F0共振峰、破音分类、检测器估计真值未验证。未重新测量PCM/mel/F0，没有用报告代理或原perceived_improvement=false覆盖后来反馈。缺失反馈时间/设备/盲测、当前runtime、动作上下文、唯一机制、乐句/全曲/留出与跨曲状态都保留unknown。', '',
        '现行JSON/两份CSV/Markdown同步添加本轮确认引用，原2B扩展和全部更旧字段均可精确恢复；原报告、工程、Skill、旧run、F/2A/2B审计不重写。本轮属于2A–2C记录确认收口，下一步2D仅梳理缺口与冻结有限设计；新因果渲染/人工试听仍在2E并依实际授权范围进入。', '']
    text += ['本轮本地验证见执行审计：88项pytest和工作树门禁通过，音频载荷0、三作者工程/五ZIP成员、102处Skill链接；生成产物重复构建、既有冻结拒绝覆盖及2个2B写入口guard通过。使用本批新ignored run和TEMP/TMP，原运行不写入。两次研究读取器误用字段名的KeyError在任何现行产物写出前被拒绝，修正为实际known_labels[].metrics后通过；原失败日志保留，未修改原报告或数值。', '']
    (OUT / 'table2-record-confirmation.md').write_text('\n'.join(text), encoding='utf-8')
    current = copy.deepcopy(old)
    for i, r in enumerate(current['responses'] + current['observations'] + current['audits']):
        r['record_v3']['record_confirmation'] = STATUS + '; no_new_model_or_PCM_measurement'
        r['record_v3']['confirmation_ref'] = 'table2-record-confirmation.json#/rows/' + str(i)
    current['table2_record_confirmation'] = dict(stage='2C', revision='schema3_record_confirmation_1', status=STATUS,
        report='table2-record-confirmation.json', baseline=binding, historical_2B_payload_restorable=True,
        no_new_synthesis_or_PCM_measurement_or_feedback=True)
    dump(OUT / 'conditional-responses.json', current)
    with docs['conditional-responses.csv'].open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    by_id = {r['id']: r['record_v3'] for r in current['responses'] + current['observations'] + current['audits']}
    for r in rows:
        r['record_v3'] = json.dumps(by_id[r['id']], ensure_ascii=False, sort_keys=True)
    write_csv(OUT / 'conditional-responses.csv', rows)
    structured = [dict(id=rid, record_kind=ext['record_kind'], comparison_id=ext['comparison_id'], feedback_group_id=ext['feedback_group_id'] or '',
        record_v3=json.dumps(ext, ensure_ascii=False, sort_keys=True)) for rid, ext in by_id.items()]
    write_csv(OUT / 'table2-record-structure.csv', structured)
    prefix = '# 表2现行确认：2C\n\n14条记录复核完成，确认范围与缺口见[2C逐行报告](table2-record-confirmation.md)和[JSON](table2-record-confirmation.json)。输入/预测数学核查与历史声学/用户反馈分层；没有新模型、PCM测量或试听。以下2B及更早说明保留原时态。\n\n'
    (OUT / 'conditional-responses.md').write_text(prefix + docs['conditional-responses.md'].read_text(encoding='utf-8'), encoding='utf-8')
    schema = load(docs['table2-record-schema.json'])
    schema['properties']['record_confirmation'] = dict(enum=[schema['properties']['record_confirmation']['const'], STATUS + '; no_new_model_or_PCM_measurement'])
    schema['properties']['confirmation_ref'] = dict(type='string', minLength=1)
    dump(OUT / 'table2-record-schema.json', schema)
    dump(OUT / 'table2-confirmation-migration.json', dict(stage='2C', schema_version_retained=3, baseline=binding,
        source_ledger_sha256=sha(docs['conditional-responses.json']),
        restore_operation='Remove table2_record_confirmation; remove every record_v3.confirmation_ref; restore record_v3.record_confirmation to schema_revised_with_explicit_gaps; 2C_not_executed. Deep equality to pre2C JSON required. CSV restore these extensions; all other cells equal. Markdown remove current prefix.',
        older_record_fields_changed=False, prior_stage_audit_outputs_changed=False))
    print(json.dumps(dict(status=STATUS, counts=package['counts'], status_claim_counts={k: len(v) for k, v in statuses.items()})))


if __name__ == '__main__':
    main()
