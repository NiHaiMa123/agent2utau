"""Audit historical exposure and grouped coverage from metadata, without rendering."""
import csv
import io
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from record_stage_2e_word225_feedback import ROOT, HERE, OUT, ENTRIES, ref, save, check_refs

NAME = 'table2-stage-2f-exposure-coverage-20261011'
RUN = ROOT / 'runs/research/table2-exposure-coverage-20261011'
PREVIOUS = ROOT / 'runs/research/table2-sampling-review-20261011'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def csv_write(path, rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    with path.open('x', encoding='utf-8', newline='') as stream:
        stream.write(out.getvalue())


def main():
    outputs = {k: OUT / (NAME + suffix) for k, suffix in dict(record='.json', report='.md',
        candidates='-candidates.csv', coverage='-coverage.csv', precision='-precision.csv', audit='-audit.json').items()}
    assert not RUN.exists() and not any(p.exists() for p in outputs.values())
    previous_seal = load(PREVIOUS / 'completion-manifest.json')
    check_refs(previous_seal['files'] + previous_seal['documents'] + previous_seal['entries'])
    previous = load(PREVIOUS / 'sampling-review.json')
    prior_seals = [load(ROOT / r['path']) for r in previous['source_seals']]
    check_refs(previous['source_seals'])
    immutable = previous_seal['files'] + previous_seal['documents'] + [ref(PREVIOUS / 'completion-manifest.json')]
    immutable += [r for s in prior_seals for r in s['files'] + s['documents']]
    check_refs(immutable)
    binding = load(HERE / 'stage_2e_execution_baseline_binding.json')
    assert ref(ROOT / binding['manifest'])['sha256'] == binding['sha256']
    baseline = load(ROOT / binding['manifest'])
    protected = baseline['production_skill_project_bindings'] + baseline['protected_inputs']
    check_refs(protected)
    study_path = ROOT / previous['source']['path']
    check_refs([previous['source']])
    study = load(study_path)
    words = study['all_current_words']
    geometry_path = ROOT / 'runs/lastpage_loudness_skill_v02_20261007/native_word_geometry.json'
    assert ref(geometry_path)['sha256'] == study['bindings'][str(geometry_path)]
    geometry = {w['word']: w for w in load(geometry_path)}
    assert len(words) == len(geometry) == 318
    metadata_paths = dict(
        original_labels='runs/lastpage_tenc_feedback_20261008/current_four_contexts.json',
        bao_inventory='runs/lastpage_tenc_feedback_20261008/repeated_bao.json',
        bao_clips='runs/lastpage_tenc_feedback_20261008/same_bao_excerpts_binding.json',
        bao_feedback='runs/lastpage_tenc_feedback_20261008/same_bao_user_feedback.json',
        guo_inventory='runs/lastpage_guo_phoneme_audit_20261008/audit.json',
        guo_clips='runs/lastpage_guo_phoneme_audit_20261008/comparison.json',
        guo_feedback='runs/lastpage_guo_positive_comparison_20261008/feedback.json',
        brec_protocol='runs/lastpage_cross_condition_study_20261008/validation_protocol.json',
        brec_feedback='runs/lastpage_brec_cohort_feedback_20261008/feedback.json',
        shfc_protocol='docs/knowledge/acoustic-manifestations-20261009/validation-protocols/shfc-path-separation-v1.json',
        project_roles='projects/README.md')
    sources = [ref(study_path), ref(geometry_path)] + [ref(ROOT / p) for p in metadata_paths.values()]
    data = {k: load(ROOT / p) for k, p in metadata_paths.items() if p.endswith('.json')}
    assert data['bao_feedback']['user_verbatim'] == '我听着都一样'
    assert data['guo_feedback']['word295_unknown_retained']
    assert data['brec_feedback']['user_verbatim'] == '全部没区别。'
    # Do not correct the immutable U17 text: resolve the actual clip IDs here.
    assert [c['word'] for c in data['guo_clips']['clips']] == [112, 247, 295]
    events = []

    def event(eid, kind, ids, source, intervals=()):
        target_ids = sorted(set(ids))
        assert all(i in geometry for i in target_ids)
        overlap_ids = []
        for w in words:
            phones = w['native_phones']
            start = min(p['start_ms'] for p in phones) / 1000
            end = max(p['end_ms'] for p in phones) / 1000
            if any(start < b and end > a for a, b in intervals):
                overlap_ids.append(w['word'])
        events.append(dict(id=eid, kind=kind, target_words=target_ids,
            delivered_clip_overlap_words=overlap_ids, source=ref(ROOT / metadata_paths[source]),
            clip_overlap_definition='word native phone span intersects delivered source interval; not a new auditory label'))

    event('EX01', 'historical_explicit_labels', [r['word'] for r in data['original_labels']['rows']], 'original_labels')
    event('EX02', 'same_bao_metadata_and_prediction_analysis', [r['word'] for r in data['bao_inventory']['rows']], 'bao_inventory')
    event('EX03', 'same_bao_delivered_clips_and_aggregate_feedback', [r['word'] for r in data['bao_clips']['order']],
        'bao_clips', [r['source_s'] for r in data['bao_clips']['order']])
    event('EX04', 'same_guo_mapping_clock_analysis', [r['word'] for r in data['guo_inventory']['same_guo_source_native_comparison']], 'guo_inventory')
    event('EX05', 'same_guo_delivered_clips_and_partial_feedback', [r['word'] for r in data['guo_clips']['clips']],
        'guo_clips', [r['original_interval_s'] for r in data['guo_clips']['clips']])
    event('EX06', 'BREC_intervention_and_no_difference_feedback', [r['word'] for r in data['brec_protocol']['cases']], 'brec_protocol')
    event('EX07', 'SHFC_path_design_execution_and_feedback', [r['condition']['word'] for r in data['shfc_protocol']['cases']], 'shfc_protocol')
    by_id = {w['word']: w for w in words}
    direct_ids = {i for e in events for i in e['target_words']}
    clip_ids = {i for e in events for i in e['delivered_clip_overlap_words']}
    exposed_groups = {by_id[i]['context'] for i in direct_ids | clip_ids}
    phrase_words = defaultdict(list)
    for w in words:
        phrase_words[w['context']].append(w)
    for group in phrase_words.values():
        group.sort(key=lambda w: w['vowel_s'][0])
    rows = []
    for w in words:
        g = geometry[w['word']]
        assert w['vowel_s'] == g['native_vowel'] and w['native_phones'] == g['phones']
        v0, v1 = w['vowel_s']
        preceding = [p for p in w['native_phones'] if p['end_ms'] <= v0 * 1000 + 1e-6]
        onset = '|'.join(p['phoneme'] for p in preceding) or '(no_owned_pre_vowel_phone)'
        group = phrase_words[w['context']]
        index = next(i for i, x in enumerate(group) if x['word'] == w['word'])
        row = dict(candidate_id=w['id'], word=w['word'], char=g['char'], corpus_id='lastpage', phrase_group=w['context'], lyric_line=g['line'],
            raw_vowel_token=w['phoneme'], note_pitch_midi=w['tone'], vowel_duration_ms=1000 * (v1-v0),
            pitch_bucket='56-63' if w['tone'] < 64 else ('64-68' if w['tone'] < 69 else '69-73'),
            duration_bucket='<250ms' if v1-v0 < .250 else ('250-500ms' if v1-v0 < .500 else '>=500ms'),
            raw_owned_onset_tokens=onset, owned_onset_duration_ms=sum(p['end_ms']-p['start_ms'] for p in preceding),
            nominal_previous_interval_semitones=w['tone']-group[index-1]['tone'] if index else 'unknown',
            nominal_next_interval_semitones=group[index+1]['tone']-w['tone'] if index+1 < len(group) else 'unknown',
            phrase_position='single' if len(group)==1 else ('first' if index==0 else ('last' if index==len(group)-1 else 'middle')),
            source_unknown_retained=w['source_unknown_retained'], historical_label_unchanged=w['label'],
            direct_event_ids='|'.join(e['id'] for e in events if w['word'] in e['target_words']),
            delivered_clip_overlap_event_ids='|'.join(e['id'] for e in events if w['word'] in e['delivered_clip_overlap_words']),
            phrase_in_scoped_exposure_audit=w['context'] in exposed_groups,
            baseline_material_exposure='legacy_song_used_for_design_and_full_song_analysis',
            word_specific_history='documented_in_scoped_audit' if w['word'] in direct_ids | clip_ids else 'unknown_not_certified_unseen',
            prospective_holdout_eligible=False, prospective_role='unassigned', permissible_future_role='development_or_regression_after_protocol',
            phonetic_class='unknown_not_inferred_from_token_spelling')
        rows.append(row)
    coverage = []
    for vowel in sorted({r['raw_vowel_token'] for r in rows}):
        for pitch in ('56-63', '64-68', '69-73'):
            for duration in ('<250ms', '250-500ms', '>=500ms'):
                cell = [r for r in rows if (r['raw_vowel_token'],r['pitch_bucket'],r['duration_bucket'])==(vowel,pitch,duration)]
                coverage.append(dict(raw_vowel_token=vowel, pitch_bucket=pitch, duration_bucket=duration,
                    candidate_words=len(cell), phrase_groups=len({r['phrase_group'] for r in cell}),
                    documented_word_history=sum(r['word_specific_history']=='documented_in_scoped_audit' for r in cell),
                    unknown_word_history=sum(r['word_specific_history']=='unknown_not_certified_unseen' for r in cell),
                    clean_prospective_holdout_words=0, candidate_ids='|'.join(r['candidate_id'] for r in cell),
                    coverage_status='empty' if not cell else ('one_phrase_only' if len({r['phrase_group'] for r in cell})==1 else 'multiple_phrases_same_song')))
    # Planning sensitivity only: equal clusters of size two, hypothetical ICC.
    # Neither rho nor a feedback distribution is estimated from these old data.
    precision = []
    for n in (24,48,72,96,192,384):
        for rho in (0,.3,.6):
            deff = 1 + rho
            neff = n / deff
            precision.append(dict(evaluation_contexts=n, assumed_targets_per_phrase=2, assumed_within_phrase_ICC=rho,
                design_effect=deff, approximate_effective_contexts=neff,
                approximate_95pct_halfwidth_percentage_points=100 * 1.96 * math.sqrt(.25 / neff),
                role='worst_case_proportion_precision_sensitivity_not_actual_CI_or_power',
                song_level_clustering_accounted=False))
    counts = dict(words=318, phrase_groups=len(phrase_words), raw_vowel_tokens=33,
        documented_direct_target_words=len(direct_ids), delivered_clip_overlap_words=len(clip_ids),
        documented_word_union=len(direct_ids | clip_ids), scoped_exposed_phrase_groups=len(exposed_groups),
        word_history_unknown=len(set(by_id)-direct_ids-clip_ids), clean_holdout_words=0,
        coverage_cells=len(coverage), occupied_cells=sum(c['candidate_words']>0 for c in coverage),
        empty_cells=sum(c['candidate_words']==0 for c in coverage), one_phrase_cells=sum(c['coverage_status']=='one_phrase_only' for c in coverage),
        raw_owned_onset_patterns=len({r['raw_owned_onset_tokens'] for r in rows}))
    assert counts['words']==counts['documented_word_union']+counts['word_history_unknown']
    assert counts['coverage_cells']==297 and sum(c['candidate_words'] for c in coverage)==318
    source_registry = [dict(corpus_id=cid, project=ref(ROOT / path), role='previously_used_song_not_clean_holdout',
        native_metadata_scope='318 frozen rows' if cid=='lastpage' else 'not_audited_for_this_protocol',
        voice_chain_compatibility='bound_current_chain' if cid=='lastpage' else 'unknown',
        new_batch_execution_authorized=False) for cid,path in [
        ('lastpage','projects/latest/lastpage_loudness_v02.ustx'),
        ('yuai','projects/latest/yuai_skill_v17.ustx'),('huahai','projects/latest/huahai_plus4_smooth.ustx')]]
    sources += [r['project'] for r in source_registry]
    RUN.mkdir(parents=True)
    snapshots=[]
    for name in ENTRIES + [r['path'] for r in previous_seal['documents']]:
        p=ROOT/name; dest=RUN/'before'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as stream: stream.write(p.read_bytes())
        assert ref(p)['sha256']==ref(dest)['sha256']
        snapshots.append(dict(**ref(p),snapshot=dest.relative_to(ROOT).as_posix()))
    save(RUN/'before/snapshot-manifest.json',dict(files=snapshots))
    record=dict(status='exposure_and_coverage_audited_with_sampling_gaps',date='2026-10-11',counts=counts,
        sources=sources,previous_seal=ref(PREVIOUS/'completion-manifest.json'),events=events,source_registry=source_registry,
        exposure_scope='7 documented metadata/delivery/intervention families, not an exhaustive history of every prior listening; absence of an event is unknown',
        preparation_validator_note='First preflight rejected lyric line == native context at word7 (line1/context0), before file or entry mutations. Corrected by recording lyric_line separately and retaining bound study context for native phrase grouping; exact phone/clock checks unchanged.',
        holdout_rule='current legacy song has no certified prospective holdout; new sources selected before feedback, grouped by song and phrase, no tuning from holdout',
        descriptive_buckets_not_physiological_thresholds=True,
        endpoint_draft=dict(status='prepared_not_frozen',primary='S/A perceived power direction at each preselected context',
            response_options=['left_much_stronger','left_stronger','no_perceptible_difference','right_stronger','right_much_stronger','uncertain'],
            primary_reporting='report S stronger / A stronger / tie / uncertain / missing / technical failure separately over all preselected targets; report denominators; no silent complete-case filtering',
            side_effects=['voice_break_or_artifact','articulation','perceived_pitch','perceived_level','neighbor_regression'],
            side_effect_state='left_only/right_only/both/neither/uncertain; distinct from power; improvement and naturalness require separate judgements',
            unit='one word context nested in phrase/song, not each order, waveform, same-input repeat or rating',
            context_integrity='one target intervention per independently rendered full phrase; multiple targets in a phrase never combined in the same variant; shared phrase counts as one cluster',
            presentation='anonymous balanced S/A orders, fixed gain and duration, full phrase retained and focus time marked; no BGM or per-item normalization',
            batching='draft 8 primary contexts per session plus 1 hidden no-change and 1 hidden retest; reassess burden before freeze',
            controls='hidden no-change/retest excluded from condition N; inconsistent retests reported, no post-hoc filtering of inconvenient cases',
            repeated_orders='same context, record separately and summarize by a frozen rule; not new independent observations',
            listener='one current user, conditional personal judgement; no population listener inference',
            main_comparison='S/A in both phases; D/P mechanism comparisons development only, separate endpoints and multiplicity plan'),
        sample_size_review=dict(status='sensitivity_prepared_final_N_not_justified',
            old_24_plus_48_scenario='24 development cannot be added to 48 holdout for independent confirmatory N',
            assumptions='hypothetical equal two-target phrase groups and ICC 0/.3/.6, variance .25, normal 1.96 halfwidth; not empirical estimates',
            formula='DEFF=1+(m-1)*rho; N_eff=N/DEFF; h=1.96*sqrt(.25/N_eff)',
            precision_targets_not_selected={str(h): math.ceil(1.96**2*.25/h**2) for h in (.1,.15,.2)},
            precision_assumptions='iid worst-case single response-category proportion only; not clustered actual CI, power, subgroup or multi-song adequacy',
            unresolved=['minimum useful perceptual effect or desired precision','song-level variability and weighted sampling estimand','listener/session uncertainty','source availability and legal task scope','fixed-dose support and grid feasibility','final sample IDs, exclusions and stopping rule'],
            fixed_dose='new batch rule not chosen; do not silently copy the two historical distinct anchor constructions into all words'),
        new_contexts_assigned=0,new_waveforms=0,new_model_calls=0,audio_or_array_decodes=0,
        new_listening_feedback=0,stage_2F_validation_executed=False,measurement_validated=False,
        song_skill_changes=False,single_agent=True,CI_manual_only=True,generator=ref(Path(__file__).resolve()))
    save(outputs['record'],record);save(RUN/'exposure-coverage.json',record)
    csv_write(outputs['candidates'],rows);csv_write(outputs['coverage'],coverage);csv_write(outputs['precision'],precision)
    h48=[r for r in precision if r['evaluation_contexts']==48]
    report=f'''# 2F历史曝光、分组覆盖与样本量准备

2026-10-11。exposure_and_coverage_audited_with_sampling_gaps。仅只读元数据与设计准备，没有新音频、模型执行或人工反馈。

## 历史曝光审计

318字/34乐句来自已反复制作、交付、分析并据反馈设计过的《最后一页》。按7类已绑定事件，直接定位{counts['documented_direct_target_words']}字，历史裁片覆盖{counts['delivered_clip_overlap_words']}字，并集{counts['documented_word_union']}字，涉及{counts['scoped_exposed_phrase_groups']}乐句；其余{counts['word_history_unknown']}字的逐字试听历史unknown。这个清单不是全历史穷尽审计，不能从“无标签”推断“从未听过”。全曲分析的来源使用是已知的，完整逐字试听是未知的，两者分开。

已绑定同字抱90/225/273、果112/247/295及只214等历史位置。旧U17 word282误写在原文保留，本表按实际交付和勘误绑定295；没有改写原反馈、旧unknown或原JSON。交付片段相交的邻字只记录材料曝光，不补听感标签。已分析抱7处/果5处及旧阴性BREC保留；不加剂量，不重新试听抱。

现有318字全部标为不具备已认证的前瞻留出资格；这不意味着每个字都被单独听过，也不意味着它们不能在新协议中作开发/回归条件。乐句内相关字共享分组。雨爱/花海发布工程也属于以前用过的歌曲，本轮只核对文件身份，未读作者数组、未导出其元数据，不将它们直接算作新留出。真正跨歌留出需要新的材料身份、范围及历史使用审计。

## 覆盖清单

已补318行真实字符/原生声母token、名义前后音程、句内位置及曝光字段。仅按所属字原生音素时间计算，不把模型token名称自动解释成生理发声类型；句首/句末跨句邻接仍unknown。历史source unknown与听感标签保持。

33元音token×3音高档×3时长档=297描述格：{counts['occupied_cells']}有候选、{counts['empty_cells']}为空，{counts['one_phrase_cells']}只来自一个乐句。声母共有{counts['raw_owned_onset_patterns']}种原始token组合。所有格均无新留出。矩阵明确空格、字数与乐句数；72字草案不能证明每个元音和所有交互条件的规律。最终应先收窄要估计的覆盖范围，再增加合法材料；不要求用小批次填满整个笛卡尔积。

## 听觉终点与批量流程草案

主要终点：在固定S/A干预下，当前用户对目标上下文的力量感方向；选项为左右更强/明显更强、无可感知差别、不确定。揭盲后分开报告S强、A强、无差别、不确定、缺评与技术失败，并列出所有预选目标的分母。力量感不升级成自然度、改善或响度。

副作用独立记录破音/伪影、咬字、感知音高/电平及邻字回退，允许双方/一方/无/不确定。保持完整乐句，标焦点时间，固定增益、匿名和平衡顺序；本批不研究BGM。每个目标分别完整重算，同句多个目标不在同一变体一起干预，避免同时改两字混淆单点作用；同句仍一个统计聚类。

可按每场8个主要上下文，加1个隐藏无变化对照和1个隐藏复听安排短场次，此为负担草案而非已批准的试听量。隐藏检查、同输入技术重复、交换顺序均不计新样本；失败/不一致不按结果好坏事后删除。D/P只安排开发阶段机制对照，另外冻结分析与多重比较范围，不让它占满主要跨条件S/A试听。当前只有一位用户，不作人群偏好推断。

## 24＋48草案的精度复核

24开发条件不能与48留出条件合并宣称72个独立确认样本。以一个反馈类别比例的最坏方差0.25作**假设性成本敏感性计算**：每句2目标，假设句内相关rho=0/0.3/0.6，设计效应1+rho；48评估上下文约相当于{h48[0]['approximate_effective_contexts']:.1f}/{h48[1]['approximate_effective_contexts']:.1f}/{h48[2]['approximate_effective_contexts']:.1f}个条件，95%正态近似半宽约±{h48[0]['approximate_95pct_halfwidth_percentage_points']:.1f}/±{h48[1]['approximate_95pct_halfwidth_percentage_points']:.1f}/±{h48[2]['approximate_95pct_halfwidth_percentage_points']:.1f}个百分点。

若理想独立条件下要求半宽±10/15/20个百分点，相应粗略规划数为97/43/25；这些不是当前必须达到的阈值。rho未估计，歌曲层相关未纳入，当前数据未给出比例或功效；不能用这张表证明72足够、48无效或3首歌可外推总体。每元音分组和多终点还需要另行依据。样本量应与推断目的和所需信息对应，[方法来源](https://doi.org/10.1525/collabra.33267)；本轮未选择最终精度或有意义的差别。

## 下一步和执行范围

下一步先明确来源与目标总体、是否仅作当前声库内描述，确定主要差别/精度和人工负担，再冻结实际开发/前瞻留出ID、统一剂量/形状、原生支撑与5tick检查及退出规则。旧两字锚点构造不完全一致，不能简单当作全样本统一形状复制。新批次尚未冻结或执行；实际留出验证0，通用规律0，不改歌曲、既有音频、Skill或自动CI。

[候选与曝光]({NAME}-candidates.csv) · [覆盖矩阵]({NAME}-coverage.csv) · [精度敏感性]({NAME}-precision.csv) · [结构记录]({NAME}.json) · [核查]({NAME}-audit.json)。上轮[采样纠偏](table2-stage-2f-sampling-review-20261011.md)及原反馈原字节保留。
'''
    with outputs['report'].open('x',encoding='utf-8',newline='\n') as stream: stream.write(report)
    current=(f'当前2F准备状态exposure_and_coverage_audited_with_sampling_gaps：318字/34乐句历史曝光与覆盖元数据已核查；'
        f'7类事件直接/裁片并集{counts["documented_word_union"]}字，其余{counts["word_history_unknown"]}逐字曝光unknown；当前旧曲不认证前瞻留出。'
        f'33元音×3音高×3时长297格，{counts["occupied_cells"]}有候选/{counts["empty_cells"]}空格；'
        '已准备力量感主终点、副作用分栏、匿名分场试听和假设精度敏感性；24开发不能与48留出合并作确认N。'
        '新材料/主要差别或精度/实际名单/统一干预支撑仍待冻结，原72条件/384波形仅成本草案。'
        '2E两字仅机制预实验、原9条反馈及阴性保持；2F实际留出/新波形/模型调用/新反馈0，measurement_validated仍false，通用规律0。'
        '不继续抱单点或BGM，不改歌曲/既有音频/Skill，单Agent、CI仅手动。')
    for name in ENTRIES:
        path=ROOT/name; text=path.read_text(encoding='utf-8')
        old=next(line for line in text.splitlines() if '当前研究纠偏状态sampling_design_preparation_with_explicit_gaps：' in line)
        link=Path(os.path.relpath(outputs['report'],path.parent)).as_posix()
        text=text.replace(old,('- ' if old.startswith('- ') else '')+current+f' 见[曝光覆盖与终点准备]({link})。',1)
        if name=='plan.md':
            old_next=next(line for line in text.splitlines() if line.startswith('下一工作为2F采样准备：'))
            text=text.replace(old_next,'下一工作为2F协议前置冻结：明确目标总体与新材料身份/历史使用，选择主要差别或精度及试听预算，再冻结实际开发/留出分组ID与覆盖、统一干预支撑/5tick检查和停止规则。当前318旧曲字可供开发/回归，不认证为新留出；旧72条件草案未论证为最终N。已完成曝光/覆盖和终点/精度敏感性准备，实际渲染/留出验证0，不追加抱点对点或BGM，不改歌曲/Skill。',1)
        path.write_text(text,encoding='utf-8',newline='\n')
    save(outputs['audit'],dict(status='checking'))
    result=subprocess.run([sys.executable,str(ROOT/'tools/repository/check_repository.py'),'--worktree'],cwd=ROOT,
        capture_output=True,text=True,encoding='utf-8')
    (RUN/'worktree-gate.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    check_refs(immutable+protected+sources)
    for r in snapshots: assert ref(ROOT/r['snapshot'])['sha256']==r['sha256']
    with outputs['candidates'].open(encoding='utf-8',newline='') as stream: parsed=list(csv.DictReader(stream))
    assert len(parsed)==318 and all(r['prospective_holdout_eligible']=='False' and r['prospective_role']=='unassigned' for r in parsed)
    for w,r in zip(words,parsed):
        assert r['candidate_id']==w['id'] and r['historical_label_unchanged']==w['label']
        assert float(r['vowel_duration_ms'])==1000*(w['vowel_s'][1]-w['vowel_s'][0])
        assert r['source_unknown_retained']==str(w['source_unknown_retained'])
    with outputs['coverage'].open(encoding='utf-8',newline='') as stream: parsed_cells=list(csv.DictReader(stream))
    assert len(parsed_cells)==297 and sum(int(r['candidate_words']) for r in parsed_cells)==318
    for cell in parsed_cells:
        ids=[i for i in cell['candidate_ids'].split('|') if i]
        matches=[r for r in rows if r['candidate_id'] in ids]
        assert len(matches)==int(cell['candidate_words'])
        assert len({r['phrase_group'] for r in matches})==int(cell['phrase_groups'])
    link_count=0
    for path in [ROOT/n for n in ENTRIES]+[outputs['report']]:
        for link in re.findall(r'\]\(([^\s)]+)\)',path.read_text(encoding='utf-8')):
            if '://' not in link and not link.startswith('#'):
                assert (path.parent/link.split('#')[0]).exists(),(path,link)
                link_count+=1
    audit=dict(status='passed_metadata_and_design_preparation_only',counts=counts,
        protected_bindings=len(protected),immutable_bindings_checked=len(immutable),source_bindings=len(sources),
        snapshots=len(snapshots),markdown_links_checked=link_count,worktree_gate=json.loads(result.stdout),
        artifacts=[ref(p) for k,p in outputs.items() if k!='audit'],entries=[ref(ROOT/n) for n in ENTRIES],
        new_waveforms=0,new_model_calls=0,audio_or_array_decodes=0,new_listening_feedback=0,
        holdout_assigned=0,final_sample_size_justified=False,exposure_audit_exhaustive=False,generator=ref(Path(__file__).resolve()))
    outputs['audit'].write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save(RUN/'audit.json',audit)
    save(RUN/'completion-manifest.json',dict(status=audit['status'],
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],documents=[ref(p) for p in outputs.values()],entries=audit['entries']))
    print(json.dumps(dict(status=audit['status'],counts=counts,worktree_gate=audit['worktree_gate']),ensure_ascii=False))


if __name__=='__main__':
    main()
