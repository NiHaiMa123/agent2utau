"""Append withdrawn transition wording and re-deliver sealed author A/C for texture."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, sha, check
from agent2utau.knowledge import collect_context, check_plan_knowledge

PRIOR = ROOT / 'runs/research/lastpage-li-entry-pitch-feedback-20261013'
J = ROOT / 'runs/experiments/lastpage-own-li-entry-pitch-20261013'
RUN = ROOT / 'runs/research/lastpage-texture-listening-preparation-20261013'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'li-texture-listening-20261013'
KNOW = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
INDEX = 'table2-texture-listening-index-20261013'
REGISTRY = KNOW / 'active-knowledge-sources.json'
RESPONSE = 'RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01'


def csv_write(path, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def runtime_resources():
    resources = load(J / 'native-inputs/runtime.json')
    assert len(resources) == 44
    for p, digest in resources.items():
        assert sha(Path(p)) == digest, p
    legacy_path = ROOT / 'runs/lastpage_shfc_onset_probe_20261008/frozen_runtime.json'
    expected = {r['sha256'] for r in load(RUN / 'protected-before.json') if r['path'] == legacy_path.relative_to(ROOT).as_posix()}
    assert expected == {sha(legacy_path)}
    original = load(legacy_path)
    assert len(original) == 47
    for p, digest in original.items():
        assert sha(Path(p)) == digest, p
    result = dict(J_runtime_entries=44, original_installation_entries=47,
        unique_paths=len(set(resources) | set(original)), J_registry=ref(J / 'native-inputs/runtime.json'),
        installation_registry=ref(legacy_path), all_SHA_exact=True, branch_execution_verified=False,
        repair='Separated two different registries; initial44-versus47 assertion failed, no resource files changed',
        initial_checker=ref(RUN / 'logs/initial-runtime-count-script.py.txt'),
        failure=ref(RUN / 'logs/initial-runtime-count-failure.txt'),
        locator_rejection=ref(RUN / 'logs/runtime-registry-locator-failure.txt'),
        locator_checker=ref(RUN / 'logs/runtime-registry-locator-script.py.txt'))
    save(RUN / 'evaluation/runtime-byte-check.json', result)
    return result


def main():
    assert not RUN.exists() and not (REPORT / (NAME + '.json')).exists()
    seal = load(PRIOR / 'completion-manifest.json')
    check(seal['files'] + seal['documents'] + seal['entries'])
    original = load(PRIOR / 'protected-before.json') + seal['files'] + seal['documents'] + [ref(PRIOR / 'completion-manifest.json')]
    check(original)
    registry_ref = ref(REGISTRY)
    protected = [r for r in original if r['path'] != registry_ref['path']]
    RUN.mkdir(parents=True)
    (RUN / 'logs').mkdir()
    save(RUN / 'protected-before.json', protected)
    for name in ENTRIES + [registry_ref['path']]:
        p = RUN / 'before' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / name).read_bytes())
    save(RUN / 'design/mutable-registry-before.json', dict(registry=registry_ref,
        before=ref(RUN / 'before' / registry_ref['path']), reason='Append explicit correction; old feedback and reports remain immutable'))
    prior_report = load(REPORT / 'own-li-entry-pitch-feedback-20261013.json')
    correction = dict(date='2026-10-13', reply_count=1, type='prior_feedback_wording_correction',
        question='J 的“衔接不足”主要落在哪一处？我会据此选单因素对照，保留已经听到的实感。',
        verbatim='说错了，不是衔接，就是单独这里比较虚，其他太实',
        transition_issue_withdrawn=True,
        here_referent=dict(word=276, char='体', status='inferred from prior explicit 身体的体字; correction says 这里 without repeating name'),
        effective_focus='One part somewhat virtual against other parts too solid; overall author-anchored sanded filling remains target',
        ti_vs_F_regression='unknown: still not directly compared', new_named_word_labels=0,
        new_listening_trial=False, prior_listening_reply=ref(REPORT / 'own-li-entry-pitch-feedback-20261013.json'),
        prior_original_text_retained=True, l_level_drop='retained observation only; no longer selected as repair target',
        no_transition_repair=True, no_new_acceptance=True)
    save(RUN / 'feedback/location-correction.json', correction)
    author = load(REPORT / 'author-control-neutral-20261011.json')
    media = dict(A=author['delivery']['outputs']['A'], C=author['delivery']['outputs']['C'],
                 J=load(J / 'evaluation/delivery-check.json')['outputs']['candidate_preview'])
    check(list(media.values()))
    assert media['A']['sha256'] == prior_report['texture_reference_clarification']['reference']['sha256']
    assert author['native']['status'] == author['fresh']['status'] == 'passed'
    assert all(r['phones_full_pitch_CLR_both_speakers_exact'] and r['native_variance_feeds_and_predictions_exact']
               and r['actual_SHFC_intervened_frames'] == 0 for r in author['native']['rows'])
    assert author['fresh']['variance_predictions_exact'] and author['fresh']['only_three_manual_final_channels_changed']
    clipping = [dict(context=r['context'], variant=r['variant'], feature_clipping=r['feature_clipping']) for r in author['fresh']['rows']]
    assert [r['feature_clipping']['voicing'] for r in clipping if r['variant'] == 'A'] == [40, 45]
    assert all(not any(r['feature_clipping'].values()) for r in clipping if r['variant'] == 'C')
    comparison = dict(author_report=ref(REPORT / 'author-control-neutral-20261011.json'),
        original_protocol=author['protocol'], old_native_and_fresh_gates=dict(native=author['native'], fresh=author['fresh']),
        pair='A-C', actual_factor='author manual TENC/BREC/VOIC group together; SHFC originally0 so no SHFC intervention',
        fixed=['all author music/pitch/phones/full clock', 'two-stage speaker and variance conditions/predictions', 'native DYN/gain1.5', 'fixed seeds11/101'],
        dependency='Three final acoustic conditioning channels and their mel/wave responses; cannot isolate one channel or texture mechanism',
        old_feature_clipping=clipping, clipping_boundary='Existing A voicing feature clipping40/45frames and C0 are part of this finite group contrast; not file-amplitude clipping',
        previous_feedback='C very close to A was aggregate feedback in solidity task; texture equality was not separately stated',
        J_role='current supported direction with excess solidity/texture deficit; descriptive comparison only, different music/clock',
        native_cached_vs_seeded='Use sealed fixed-seeded PCM24 author A/C, not first native PCM16 reference or historical1.56 audio',
        new_audio_decodes=0, new_arrays_read=0, new_measurements=0, new_native_calls=0, new_models=0, new_waveforms=0)
    save(RUN / 'evaluation/reused-comparison-check.json', comparison)
    followup = dict(record_id=RESPONSE, append_only_clarification=True, correction=correction,
        prior_feedback=prior_report['feedback'], texture_reference=prior_report['texture_reference_clarification'],
        effective_interpretation=dict(direction_supported=True, overall_too_solid=True,
            localized_virtual_contrast='体 by prior context; no14individual labels', transition_issue='withdrawn by user',
            missing_sanded_filling_reference='sealed author A two phrases', mechanism='unknown'),
        planned_listening='Existing author A versus C for sanded filling texture; J contextual reference',
        new_condition_or_response_series=0, new_listening_feedback=0, new_correction_reply=1,
        media=media, no_production_adoption=True, agent_heard=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/table2-supplement.json', followup)
    report = dict(status='transition_withdrawn_author_A_C_texture_reused_delivered_pending_listening',
        table2_supplement=followup, reused_comparison=ref(RUN / 'evaluation/reused-comparison-check.json'), media=media,
        new_waveforms=0, new_models=0, new_native_calls=0, new_audio_decodes=0, new_arrays_read=0,
        K_frozen_or_generated=False, adoption=False, agent_heard=False, measurement_validated=False, general_rule_validated=False)
    save(REPORT / (NAME + '.json'), report)
    md = f'''# 最后一页：撤回衔接问题与复用作者A/C质感试听

2026-10-13。用户“继续”后，在位置澄清中明确更正：

> {correction['verbatim']}

本次计1条原反馈措辞更正，不是新合成或第二次独立试听验收。“衔接不足”撤回，体到里不是待修衔接问题；“这里”按前条明确“身体的体字”理解为体276，仍保留推定标记，不冒称本条重新命名。当前关注是单独一处略虚、其它太实的对比，以及整体缺白烁那种唱歌“磨砂填充”。原完整反馈/质感参照原字节保留，当前有效解释通过追加更正表达。

此前l准备RMS下降、音高运动、时间连续等保持技术观察，不据此补声母、改连接或把体一律调实；没有冻结/执行K，也没有新DYN/VOIC修复。J低位进入方向的支持保持，F旧对照保持，不把原话更正当作新物理因果或全句接受。

## 本轮完成的现成对照

复用已封存的作者A/C两句，按原字节/SHA分开交付。A保留作者三人工发声增量，C仅取消TENC/BREC/VOIC人工增量；SHFC原0，没有实际干预。双方完整音乐/音高/音素/时钟、两阶段speaker、variance条件/预测、固定11/101及DYN/公共1.5增益相同。旧原生/fresh门禁和重复结果沿用，不标成本轮新执行。作者A既有VOIC特征裁剪40/45帧、C0作为原输入条件明确保留，不写成全部特征无裁剪或新文件破音。

用户此前“C很接近A”没有单独评价磨砂/填充这一维度，因此当前不能据此认定三控制与质感无关。A−C这次只检验**这组控制在该作者条件下的质感贡献**；即使不同，也不能归因到某一通道。A/C都用当前1.65c固定种子PCM24，不是 unavailable1.56历史录音，也不是初次native PCM16参考。

J另作目前缺质感/偏实的描述性参照，双方音乐/时钟不同，不进行因果归因。J“体虚、其它太实”的反差未被本对照自动修复，磨砂也未被定义成气声、沙哑或噪声指标。接下来先听A与C磨砂填充是否有明显差别，再据反馈决定有依据的单因素候选，避免盲目添加BREC/减TENC或联合因素。

- [白烁当前参考A](../../../{media['A']['path']})：用户已选的质感参照。
- [白烁中和控制C](../../../{media['C']['path']})：与A同音乐/时钟的控制组比较。
- [自己的J](../../../{media['J']['path']})：更实方向支持、整体偏实/质感不足仍未接受。

试听问题：A和C的磨砂填充感是接近，还是某版明显更充分？相对这两版，J是否主要欠缺这一层？本协议不补过往14字标签，不以数组/RMS宣布质感通过；缺反馈unknown。

当前索引仍37行/近12系列，J原技术/原反馈与白烁参照保持，新增更正被实际检索并用于本试听计划的逐ID决策。新音频/工程/数组解码/复测/原生/模型0；旧资源47项SHA与保护链保持。原歌音频Skill/作者原件/抱C/旧阴性/unknown保持，Agent未听，measurement_validated=false、通用规律0，单Agent、CI仅手动。

[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')
    config = load(REGISTRY)
    old_path = ROOT / config['response_indices'][0]
    old_index = load(old_path)
    idx = copy.deepcopy(old_index)
    assert len(idx['rows']) == 37 and idx['recent_response_series_count'] == 12
    row = next(r for r in idx['rows'] if r['id'] == RESPONSE)
    old_row = copy.deepcopy(row)
    row['feedback_sources'].append(ref(REPORT / (NAME + '.json')))
    row.update(latest_correction_record=correction, effective_feedback_interpretation=followup['effective_interpretation'],
        scope='J direction retained; transition complaint explicitly withdrawn; local virtual/others too solid and author-anchored texture now focus')
    assert row['source_record'] == old_row['source_record'] and row['source'] == old_row['source']
    assert row['feedback_record'] == old_row['feedback_record'] and row['reference_clarification'] == old_row['reference_clarification']
    idx.update(prior_index=ref(old_path), generator=ref(Path(__file__)), status='current_index_transition_withdrawn_texture_listening_pending')
    save(KNOW / (INDEX + '.json'), idx)
    csvrows = [dict(id=r['id'], kind=r['kind'], source_path=r['source']['path'], source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']), table1_refs='|'.join(r['table1_refs']), scope=r['scope']) for r in idx['rows']]
    csv_write(KNOW / (INDEX + '.csv'), csvrows)
    imd = '# 表2当前索引：衔接问题撤回、质感试听待评\n\n37行/近12系列保持，追加用户措辞更正；原J反馈未改写，latest_correction_record明确撤回衔接，现成A/C试听不增加响应样本数。\n\n|ID|原记录|反馈/更正|\n|---|---|---|\n'
    for r in idx['rows']:
        fb = '、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包'
        imd += f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd += f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。\n'
    (KNOW / (INDEX + '.md')).write_text(imd, encoding='utf-8', newline='\n')
    config['response_indices'] = [ref(KNOW / (INDEX + '.json'))['path']]
    REGISTRY.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    packet = collect_context(['PER:S1', 'ACO:S3', 'ACO:S4', 'EVT:S4', 'EVT:T5'],
        ['PARAM:C11.01', 'PARAM:C12.01', 'PARAM:C13.01'], [RESPONSE, 'RESP:LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01'])
    decisions = []
    for r in packet['records']:
        ident = r['id']
        choice = 'reject' if ident == 'EVT:T5' else 'use' if ident in [RESPONSE, 'RESP:LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01'] else 'keep_unknown'
        reason = ('User explicitly withdrew transition issue; do not repair l/ti connection on old proxy' if choice == 'reject' else
            'Retain corrected J direction/contrast and reuse strict A/C group contrast; prior closeness does not establish texture equality' if choice == 'use' else
            'Sanded filling has no isolated noise/breathiness/tension mechanism; test perception before selecting a new control')
        decisions.append(dict(id=ident, decision=choice, reason=reason,
            condition_match='Two sealed author1.65c A/C conditions; J descriptive reference with different music/clock',
            limitations='Grouped three-channel intervention with historical A feature clipping; no independent holdout, new response or single-channel causal claim'))
    save(RUN / 'design/knowledge_context.json', packet)
    listening = dict(id='LASTPAGE-TEXTURE-REUSED-A-C-LISTENING-01', status='sealed_media_reused_delivered_pending_human_listening',
        media=media, source_comparison=ref(RUN / 'evaluation/reused-comparison-check.json'), correction=ref(RUN / 'feedback/location-correction.json'),
        factor='author manual three-channel group, no new intervention',
        main_comparison='A-C desired sanded filling texture', J_comparison='descriptive deficit anchor, no same-clock causal comparison',
        questions=['A/C sanded filling similar or noticeably different, and which is fuller?', 'J specifically missing this texture versus selected author reference?'],
        budget=dict(new_scores=0, new_native_calls=0, new_model_calls=0, new_waveforms=0, new_detector_calls=0),
        fixed_gain=1.5, no_normalization=True,
        stops=['source SHA mismatch', 'no new factor/dose/texture mechanism or automatic adoption before feedback'],
        knowledge_context=dict(path='knowledge_context.json', sha256=ref(RUN / 'design/knowledge_context.json')['sha256'], decisions=decisions),
        new_feedback=0, adoption=False, agent_heard=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'design/listening-protocol.json', listening)
    _, receipt = check_plan_knowledge(listening, RUN / 'design/listening-protocol.json')
    save(RUN / 'evaluation/knowledge_receipt.json', receipt)
    current_row = next(r for r in packet['records'] if r['id'] == RESPONSE)['record']
    assert current_row['latest_correction_record']['transition_issue_withdrawn']
    status = ('当前状态transition_withdrawn_author_A_C_texture_reused_delivered_pending_listening：2026-10-13用户更正“说错了，不是衔接，就是单独这里比较虚，其他太实”，'
        '撤回衔接问题，按前条体276理解这里并保留推定；J更实方向/局部虚与其它太实/缺磨砂质感及白烁参照保持，不补声母/体增益。'
        '复用作者同声线/完整pitch/时钟/variance/DYN1.5的封存A/C，实际仅三人工发声组差异；旧A VOIC特征裁剪40/45帧与C0保留，不能单通道归因。'
        'A/C/J原字节分开交付，目标只听磨砂填充差异，旧C接近A不冒称质感相同；37索引/近12系列追加更正并知识gate拒绝衔接修复。'
        'K未冻结/执行，新工程/音频/数组解码/复测/原生/模型0，47资源/保护SHA保持；原歌音频Skill/作者/抱C/旧阴性/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p = ROOT / name
        lines = p.read_text(encoding='utf-8').splitlines()
        ix = [i for i, l in enumerate(lines) if '当前状态J_direction_supported_transition_texture_gaps_recorded：' in l]
        assert len(ix) == 1, name
        rel = 'docs/reports/lastpage/' + NAME + '.md'
        if '/' in name:
            rel = ('../../' if name.startswith('research/') else '../../../') + rel
        lines[ix[0]] = ('- ' if lines[ix[0]].startswith('- ') else '') + status + f' 见[更正与作者质感对照]({rel})。'
        if name == 'plan.md':
            for i, l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i] = '下一工作进入逐首更新，先《最后一页》：用户明确撤回衔接问题，当前是体（由前文推定）略虚/其它太实及缺白烁磨砂填充；不做声母/衔接修复。现成作者A/C/J已按原字节再交付，下一步只接A/C磨砂填充差异及J相对参照的质感反馈，再选有依据的单因素候选；K未冻结/执行，无新合成。'
        if name == 'docs/knowledge/acoustic-manifestations-20261009/README.md':
            for i, l in enumerate(lines):
                if l.startswith('制作使用[当前表2索引]'):
                    lines[i] = f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近12系列/37行追加用户撤回衔接的更正，当前复用A/C质感试听待评；旧字段/SHA/阴性保持。'
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    check(protected)
    check(list(media.values()))
    for r in idx['rows']:
        check([r['source']] + r['feedback_sources'])
        if r['id'] != RESPONSE:
            assert r == next(q for q in old_index['rows'] if q['id'] == r['id'])
    with (KNOW / (INDEX + '.csv')).open(encoding='utf-8-sig', newline='') as f:
        assert list(csv.DictReader(f)) == [{k: str(v) for k, v in r.items()} for r in csvrows]
    complete(media, protected)


def complete(media, protected):
    assert not (RUN / 'completion-manifest.json').exists()
    check(protected)
    check(list(media.values()))
    listening = load(RUN / 'design/listening-protocol.json')
    _, receipt = check_plan_knowledge(listening, RUN / 'design/listening-protocol.json')
    assert receipt == load(RUN / 'evaluation/knowledge_receipt.json')
    resources = runtime_resources()
    gate = subprocess.run([sys.executable, 'tools/repository/check_repository.py', '--worktree'], cwd=ROOT, capture_output=True, encoding='utf-8')
    (RUN / 'logs/repository-gate.log').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    audit = dict(status='passed_with_explicit_texture_group_and_current_focus_gaps', source=ref(Path(__file__)),
        protected_references=len(protected), old_J_source_feedback_and_reference_exact=True, latest_correction_retrieved=True,
        author_A_reference_SHA_exact=True, author_C_group_gates_reused=True, historical_A_feature_clipping_retained=True,
        new_correction_reply=1, new_listening_feedback=0, new_response_series=0, new_waveforms=0,
        new_audio_decodes=0, new_arrays_read=0, new_native_calls=0, new_model_calls=0,
        runtime_resources=resources, runtime_byte_check=ref(RUN / 'evaluation/runtime-byte-check.json'),
        media=media, listening_protocol=ref(RUN / 'design/listening-protocol.json'),
        current_index=ref(KNOW / (INDEX + '.json')), gate=gate.stdout.strip(),
        adoption=False, agent_heard=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/audit.json', audit)
    save(REPORT / (NAME + '-audit.json'), audit)
    docs = [ref(p) for p in sorted(REPORT.glob(NAME + '*'))] + [ref(p) for p in sorted(KNOW.glob(INDEX + '*'))] + [ref(REGISTRY)]
    report = load(REPORT / (NAME + '.json'))
    save(RUN / 'completion-manifest.json', dict(status=report['status'], files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
                                               documents=docs, entries=[ref(ROOT / n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'], transition_withdrawn=True, reused_media=media, new_waveforms=0, gate=audit['gate']), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'finish':
        complete(load(REPORT / (NAME + '.json'))['media'], load(RUN / 'protected-before.json'))
    else:
        main()
