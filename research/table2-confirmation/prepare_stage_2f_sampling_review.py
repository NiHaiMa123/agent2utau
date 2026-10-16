"""Prepare a grouped sampling review from frozen metadata; never render audio."""
import csv
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from record_stage_2e_word225_feedback import ROOT, HERE, OUT, ENTRIES, ref, save, check_refs

RUN = ROOT / 'runs/research/table2-sampling-review-20261011'
NAME = 'table2-stage-2f-sampling-review-20261011'
USER_TEXT = '我感觉有点不对，就是不应该验证的样本量很大的吗？怎么感觉你还是在点对点的操作。'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    outputs = [OUT / (NAME + s) for s in ('.json', '.md', '-candidates.csv', '-audit.json')]
    assert not RUN.exists() and not any(p.exists() for p in outputs), 'Preparation already exists'
    scope_run = ROOT / 'runs/research/table2-vocal-scope-review-20261011'
    scope_record = load(scope_run / 'feedback.json')
    seal_paths = [ROOT / r['path'] for r in scope_record['source_seals']]
    seal_paths.append(scope_run / 'completion-manifest.json')
    seals = [load(p) for p in seal_paths]
    immutable = [r for s in seals for r in s['files'] + s['documents']]
    check_refs(immutable)
    check_refs(seals[-1]['current_entries'])
    binding = load(HERE / 'stage_2e_execution_baseline_binding.json')
    assert ref(ROOT / binding['manifest'])['sha256'] == binding['sha256']
    baseline = load(ROOT / binding['manifest'])
    protection = baseline['production_skill_project_bindings'] + baseline['protected_inputs']
    check_refs(protection)
    study_path = ROOT / 'runs/lastpage_cross_condition_study_20261008/study.json'
    old_manifest_path = study_path.parent / 'completion_manifest.json'
    old_manifest = load(old_manifest_path)
    assert ref(study_path)['sha256'] == old_manifest['files_sha256']['study.json']
    assert ref(study_path)['sha256'] == '31722a1cfa88d5a36db52a712c8a3301c0ee7b2f87f95db2eddb7a32fe81a4b0'
    study = load(study_path)
    words = study['all_current_words']
    assert len(words) == 318 and study['unknown_current_words'] == 313
    assert len({w['id'] for w in words}) == 318
    rows = []
    for w in words:
        duration = 1000 * (w['vowel_s'][1] - w['vowel_s'][0])
        assert duration > 0
        rows.append(dict(candidate_id=w['id'], word=w['word'], phrase_group=w['context'],
            corpus_id='lastpage', voice_model='YousaV1.65c', raw_vowel_token=w['phoneme'],
            note_pitch_midi=w['tone'], vowel_duration_ms=duration,
            descriptive_pitch_bucket='56-63' if w['tone'] < 64 else ('64-68' if w['tone'] < 69 else '69-73'),
            descriptive_duration_bucket='<250ms' if duration < 250 else ('250-500ms' if duration < 500 else '>=500ms'),
            raw_native_phone_tokens='|'.join(p['phoneme'] for p in w['native_phones']),
            source_unknown_retained=w['source_unknown_retained'], historical_auditory_label=w['label'],
            prospective_role='unassigned', historical_exposure_audit='required_before_holdout_assignment'))
    counts = dict(candidate_contexts=len(rows), phrase_groups=len({r['phrase_group'] for r in rows}),
        songs=1, voice_models=1, raw_vowel_tokens=len({r['raw_vowel_token'] for r in rows}),
        old_labels=dict(sorted(Counter(r['historical_auditory_label'] for r in rows).items())),
        vowel_counts=dict(sorted(Counter(r['raw_vowel_token'] for r in rows).items())),
        pitch_bucket_counts=dict(sorted(Counter(r['descriptive_pitch_bucket'] for r in rows).items())),
        duration_bucket_counts=dict(sorted(Counter(r['descriptive_duration_bucket'] for r in rows).items())),
        phrase_counts=dict(sorted(Counter(r['phrase_group'] for r in rows).items())),
        pitch_range=[min(r['note_pitch_midi'] for r in rows), max(r['note_pitch_midi'] for r in rows)],
        duration_ms_range=[min(r['vowel_duration_ms'] for r in rows), max(r['vowel_duration_ms'] for r in rows)])
    RUN.mkdir(parents=True)
    snapshots = []
    for name in ENTRIES + [r['path'] for r in seals[-1]['documents']]:
        source = ROOT / name
        dest = RUN / 'before' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(source.read_bytes())
        assert ref(source)['sha256'] == ref(dest)['sha256']
        snapshots.append(dict(**ref(source), snapshot=dest.relative_to(ROOT).as_posix()))
    save(RUN / 'before/snapshot-manifest.json', dict(files=snapshots))
    record = dict(status='sampling_design_preparation_with_explicit_gaps', date='2026-10-11',
        user_design_steering_verbatim=USER_TEXT, auditory_feedback_count_unchanged=9,
        completed_batch=dict(design='T2D-SHFC-PATHS-01 v1', independent_context_candidates=2,
            phrase_groups=2, songs=1, voice_models=1, seeded_waveforms=16,
            paths_per_context=4, same_input_repetitions=2, derived_delivery_files=72,
            heldout_contexts=0, word225_vocal_comparisons_with_feedback=5,
            word214_independent_version_aggregate='no perceptible difference reported',
            role='engineering_and_local_mechanism_pilot_not_generalization_validation'),
        sampling_frame=counts, source=ref(study_path), source_manifest=ref(old_manifest_path),
        sampled_or_assigned_new_contexts=0, source_arrays_decoded=0, audio_decoded=0,
        inventory_scope='frozen word/phone/clock/pitch metadata only; stored prediction metrics not reanalysed',
        old_labels_not_current_auditory_truth=True, descriptive_buckets_not_physiological_thresholds=True,
        design_proposal=dict(status='not_frozen_not_authorized_for_execution',
            target='first validate SHFC conditional power response in the bound DiffSinger/voice chain; other controls/engines need separate studies',
            provisional_development_contexts=24, provisional_holdout_contexts=48,
            provisional_total_contexts=72, provisional_minimum_phrase_groups=36,
            provisional_minimum_corpus_sources=3,
            role='coverage/resource planning scenario, not a statistically justified final sample size',
            development_paths=['A', 'S', 'D', 'P'], holdout_paths=['A', 'S'],
            technical_repetitions=2, provisional_seeded_waveforms=384,
            allocation_rule='at most two targets per phrase; disjoint phrase/song groups between development and holdout; audit prior exposure before assignment',
            primary_vocal_comparison='S-A at every selected context; D/P mechanism pairs in development only',
            dose_shape='one predeclared legal dose and time-shape rule per batch, no per-word tuning; too-short cases explicitly excluded or separately designed, not silently compressed',
            final_sample_size='pending primary endpoint, meaningful effect/precision target, cluster variability and listener budget; sensitivity analysis before freeze',
            sound_bank_scope='same bound voice first; other voices/models explicitly outside current inference',
            listener_scope='current single user; condition generalization does not establish population-wide listener preference',
            prospective_holdout='not used to choose the new dose/shape/hypothesis; metadata access not misrepresented as never-seen baseline',
            human_workflow='batch anonymous balanced vocal comparisons, short sessions, null/retest controls; no response-dependent parameter changes',
            missing_material='only one 34-phrase source currently inventoried; new source permissions, historical exposure and cluster coverage must be resolved',
            no_statistical_significance_or_adequate_power_claim=True),
        methodology_sources=[dict(title='Lakens (2022), Sample Size Justification', url='https://doi.org/10.1525/collabra.33267',
            use='Sample size justification must match inferential goals, effect sizes, precision, resource constraints and sensitivity; 24/48 here remain an unfrozen scenario')],
        stage_2F_validation_executed=False, new_waveforms=0, new_model_calls=0,
        measurement_validated=False, general_rule_validated=False, BGM_research=False,
        song_or_skill_changed=False, single_agent=True, CI_manual_only=True,
        source_seals=[ref(p) for p in seal_paths], recorder=ref(Path(__file__).resolve()),
        pre_update_snapshot=ref(RUN / 'before/snapshot-manifest.json'))
    save(outputs[0], record)
    save(RUN / 'sampling-review.json', record)
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    with outputs[2].open('x', encoding='utf-8', newline='') as target:
        target.write(stream.getvalue())
    report = f'''# 表2采样纠偏：机制预实验之后的跨条件验证准备

2026-10-11。sampling_design_preparation_with_explicit_gaps；仅设计准备，未分配新样本、未渲染、未执行留出验证。

用户原话：**{USER_TEXT}**。这项质疑成立。近期执行只完成两字机制预实验，却连续围绕同一个抱推进成对试听；没有进入原计划2F的跨条件/留出验证。已归档的人声结果保留，但当前执行方向应转向采样与整批验证设计，停止追加抱的点对点操作和BGM关系复核。

## 当前到底有多少样本

| 数量 | 实际角色 | 是否增加可外推条件 |
|---|---|---|
| 2个字上下文、2个乐句 | 抱225、只214，均参加设计 | 本批只有这两个条件，留出0 |
| 16套种子波形 | 2条件×4路径×2同输入重复 | 同条件版本/确定性重复，不是16个不同条件 |
| 72份衍生试听文件 | 人声/片段/顺序/混音呈现 | 不增加独立条件 |
| 318个旧字上下文 | 冻结候选总体，1歌曲/1声库 | 不是318个干预验证或正常听感标签 |
| 34个旧乐句组 | 同曲内上下文聚类 | 多字同句相关，不能把318字当318独立乐句 |

本轮只读整理候选元数据：{counts['raw_vowel_tokens']}种原生元音token，MIDI {counts['pitch_range'][0]}–{counts['pitch_range'][1]}，元音时长{counts['duration_ms_range'][0]:.1f}–{counts['duration_ms_range'][1]:.1f}ms。旧标签5个位置/313 unknown按原字节含义保留；它不是当前完整标签集，未将未知标正常。已新增的反馈另存历史绑定，不覆盖旧JSON。CSV三个音高档及三个时长档仅便于描述覆盖，不是生理音区或已验证阈值。

## 当前下一步与规模情景

先研究当前已校验的SHFC/DiffSinger路径，目标是“在哪些元音、音区、时长和起声上下文中出现力量感变化及副作用”。这不能一次代表全部352字段、其它引擎或声库。

1. 先完成候选总体与历史曝光审计。按实际元音token、音高、时长、起声/转换及乐句角色列覆盖和缺口；不要只挑已出问题或已成功的字。已用于选择抱形状、剂量/听感解释的条件和相关句组放机制/开发或回归集，不能伪装留出。只的阴性与旧果/BREC否决保留，不重新加量。
2. 以乐句/歌曲分组冻结开发与评估留出名单，同句目标不跨分区。同一个固定干预规则施加全批，不把每个字分别调到满意。预测和声学上下文完整重建；几何不容纳既定进入/退出的样本明确排除或单独设计，不偷偷缩时长。
3. 一个具体的**待审规模情景**为24开发条件+48评估留出=72个不同字上下文，至少36个乐句组、3个授权来源；每句最多2目标，所有来源与分组尚未确定。开发A/S/D/P×各两次=192波形，留出A/S×各两次=192波形，总384波形对应72个条件，仍不能把384当独立样本。当前只盘点到1来源/34句，不能用同曲复制、作者数组或同句更多字冒充新来源。
4. 24/48是覆盖和成本情景，不是已证明充分的样本量。先定义主要听觉终点、实际有意义的差别或期望估计精度，使用开发集估计条件/乐句内相关与反馈变化，进行样本量/敏感性分析，再冻结最终数量和人声试听预算。不能在看过留出结果后改假设或继续加样本直至好看。[样本量论证方法](https://doi.org/10.1525/collabra.33267)支持按推断目标说明样本量，而非只报一个大数。
5. 人工试听仍需参与：S/A主要比较覆盖全部选定条件，机制D/P比较留在开发部分；按预定条件批次匿名、平衡顺序、分短场次提交，安排无变化与隐藏复听检查。不因单个反馈改参数，也不要求用户每听一次就重新批准下一字。重复播放不增加条件数；当前只有一位用户，不外推人群偏好。未听到差别、不确定、副作用全部保留。

不同歌曲/来源的留出用来检查跨上下文迁移；其它声库/模型要独立协议，不把当前Yousa的结论称为“所有OpenUtau都如此”。如果材料/覆盖不足，应补合法来源或收窄结论，而不是靠复制现有字凑数量。

## 本轮完成与执行边界

已完成318行候选元数据CSV和覆盖统计，所有新分区仍unassigned，历史曝光审计仍待完成；没有冻结72个实际ID，没有统计充分性结论。2E两条件保留机制预实验角色，2F只有采样设计准备，实际新留出/模型调用/波形均0。下一步完成来源、分组名单、覆盖、终点与样本量依据后再建立新的有限协议和执行范围，不扩大原两字16套协议，不自动执行新批次，不改歌曲/Skill或BGM。

[元数据CSV]({NAME}-candidates.csv) · [结构与覆盖统计]({NAME}.json) · [本轮核查]({NAME}-audit.json) · [原两字人声结论](table2-stage-2e-vocal-scope-review-20261011.md)。
'''
    with outputs[1].open('x', encoding='utf-8', newline='\n') as target:
        target.write(report)
    current = ('当前研究纠偏状态sampling_design_preparation_with_explicit_gaps：2026-10-11用户指出样本不足与点对点偏移。'
        '2E两字批次仅机制预实验（2上下文/1曲/1声库，16波形及72衍生文件不增加独立条件，留出0）；'
        '原9条回复/反馈保持，不继续抱的单点或BGM复核。已只读整理318字/34乐句候选元数据，313旧听感unknown不当正常样本。'
        '下一步按元音/音高/时长/起声/乐句覆盖，先审历史曝光，再按乐句/歌曲组冻结开发与留出、统一干预和批量人声试听。'
        '24开发+48留出/72条件/384波形仅待审成本情景，非最终样本量或执行授权；分区未分配，样本量依据/材料/终点尚待完善。'
        '2F仅采样设计准备，实际留出验证0；measurement_validated仍false，通用规律0。新音频/模型调用0，歌曲/既有音频/Skill不改，单Agent、CI仅手动，2G–2H未执行。')
    for name in ENTRIES:
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        old = next(line for line in text.splitlines() if '2E当前状态partial_human_feedback_recorded：' in line)
        link = Path(os.path.relpath(outputs[1], path.parent)).as_posix()
        text = text.replace(old, ('- ' if old.startswith('- ') else '') + current + f' 见[采样纠偏准备]({link})。', 1)
        if name == 'plan.md':
            old_next = next(line for line in text.splitlines() if line.startswith('本批现有人声结果已归档；下一工作'))
            text = text.replace(old_next, '下一工作为2F采样准备：审计历史曝光与合法材料，构建跨元音/音高/时长/起声/乐句覆盖；按乐句/歌曲分组确定开发与评估留出，明确主要终点、样本量依据、统一干预和批量人声试听预算。两字2E只保留机制预实验角色，不追加抱的点对点试听，不研究BGM；新批次未冻结/未授权执行，不自动渲染、加剂量或更新Skill。', 1)
        if name == 'plan-table2.md':
            text = text.replace('| 2F／P1 | 验证重复性、有效条件与副作用边界，使用冻结的留出条件复查 | 条件关系/反例/失效边界、留出结果 | 不将同一字重复作为泛化；输入/输出/感知重复性分开，未知不升级 |',
                '| 2F／P1 | 当前先准备跨条件总体、曝光审计、覆盖与乐句/歌曲分组留出，建立终点/样本量依据后按明确范围批量验证 | 候选清单、冻结分区与预算、条件关系/反例/留出结果 | 当前仅设计准备、实际留出0；重复/衍生文件不计新条件，同句不跨分区，失败/未知不升级 |')
        if name in ('plan.md', 'plan-table2.md', 'README.md'):
            text = text.replace('本批OpenUtau人声路径结果已整理并保留缺口；用户停止BGM关系复核，原反馈保持', '2E两字机制预实验保留；当前准备2F跨条件采样/留出设计，BGM复核停止')
            text = text.replace('本批OpenUtau人声路径结果已整理并保留缺口；后续BGM关系复核由用户取消', '2E两字机制预实验保留，当前2F采样设计准备、实际留出验证0，后续BGM关系复核取消')
        path.write_text(text, encoding='utf-8', newline='\n')
    save(outputs[3], dict(status='checking'))
    result = subprocess.run([sys.executable, str(ROOT / 'tools/repository/check_repository.py'), '--worktree'],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    (RUN / 'worktree-gate.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
    check_refs(immutable + protection + [record['source']])
    for row in snapshots:
        assert ref(ROOT / row['snapshot'])['sha256'] == row['sha256']
    parsed = list(csv.DictReader(outputs[2].open(encoding='utf-8', newline='')))
    assert len(parsed) == 318 and all(r['prospective_role'] == 'unassigned' for r in parsed)
    for old, row in zip(words, parsed):
        assert row['candidate_id'] == old['id'] and row['historical_auditory_label'] == old['label']
        assert float(row['vowel_duration_ms']) == 1000 * (old['vowel_s'][1] - old['vowel_s'][0])
    links = 0
    for p in [ROOT / n for n in ENTRIES] + [outputs[1]]:
        for target in re.findall(r'\]\(([^\s)]+)\)', p.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            assert (p.parent / target.split('#')[0]).exists(), (p, target)
            links += 1
    audit = dict(status='passed_sampling_preparation_not_executed', source=ref(study_path),
        sealed_files_SHA=sum(len(s['files']) for s in seals), sealed_documents_SHA=sum(len(s['documents']) for s in seals),
        production_skill_project_SHA=79, protected_inputs_SHA=67, snapshot_files_SHA=len(snapshots),
        candidate_rows=318, phrase_groups=34, all_roles_unassigned=True,
        artifacts=[ref(p) for p in outputs[:3]], entries=[ref(ROOT / n) for n in ENTRIES],
        markdown_links_checked=links, worktree_gate=json.loads(result.stdout),
        model_calls=0, new_waveforms=0, audio_or_array_decodes=0, stage_2F_validation_executed=False,
        final_sample_size_justified=False, CI_manual_only=True, generator=ref(Path(__file__).resolve()))
    outputs[3].write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save(RUN / 'audit.json', audit)
    save(RUN / 'completion-manifest.json', dict(status=audit['status'],
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in outputs], entries=audit['entries']))
    print(json.dumps(dict(status=audit['status'], candidates=318, phrase_groups=34,
        raw_vowel_tokens=counts['raw_vowel_tokens'], allocated=0, new_waveforms=0,
        worktree_gate=audit['worktree_gate']), ensure_ascii=False))


if __name__ == '__main__':
    main()
