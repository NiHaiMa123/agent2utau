"""Append nuanced J feedback and author texture anchor; no new synthesis."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, check
from agent2utau.knowledge import collect_context, validate_context, check_plan_knowledge

PRIOR = ROOT / 'runs/experiments/lastpage-own-li-entry-pitch-20261013'
RUN = ROOT / 'runs/research/lastpage-li-entry-pitch-feedback-20261013'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'own-li-entry-pitch-feedback-20261013'
KNOW = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
INDEX = 'table2-entry-pitch-feedback-index-20261013'
REGISTRY = KNOW / 'active-knowledge-sources.json'
BASE = ROOT / 'runs/lastpage_loudness_skill_v02_20261007'
TEXT = '方向对了，实了。就是衔接缺失有点不够，身体的体字就有点虚。不过这个虚是和白烁的一样。但其他都是很实的，所以感觉有点奇怪。还有就是整体缺失太实了一点，但不是之前那种前顶，声音变成一条缝的实。是缺少那种唱歌时带点磨砂的填充的感觉'


def write_csv(path, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    assert not RUN.exists() and not (REPORT / (NAME + '.json')).exists()
    seal = load(PRIOR / 'completion-manifest.json')
    check(seal['files'] + seal['documents'] + seal['entries'])
    original = load(PRIOR / 'protected-before.json') + seal['files'] + seal['documents'] + [ref(PRIOR / 'completion-manifest.json')]
    check(original)
    prior_plan = load(PRIOR / 'design/protocol.json')
    _, old_receipt = check_plan_knowledge(prior_plan, PRIOR / 'design/protocol.json')
    assert old_receipt == load(PRIOR / 'evaluation/knowledge_receipt.json')
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
        preserved_original_bytes=ref(RUN / 'before' / registry_ref['path']), reason='Append feedback/reference clarification, keep old indices/receipts'))
    media = load(PRIOR / 'evaluation/delivery-check.json')['outputs']
    check([media[k] for k in ['candidate_preview', 'original_preview', 'author_reference']])
    feedback = dict(verbatim=TEXT, date='2026-10-13', listening_submissions=1,
        response_record='RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01', candidate=media['candidate_preview'],
        baseline=media['original_preview'], author_reference=media['author_reference'],
        referent='J inferred from immediately preceding labelled J/F/author delivery',
        direction_supported=True, solidity_improvement_supported=True,
        target_li_solidity_scope='li is the intervention target; main reply does not repeat its name',
        transition=dict(verbatim='衔接缺失有点不够', precise_boundary_time='unknown; ti→li is a contextual candidate, not explicit user localization'),
        named_word_labels=[dict(word=276, char='体', label='有点虚', comparison='这个虚是和白烁的一样',
            limit='same reported virtual quality, not waveform equality or all other properties equal; no F comparison stated')],
        other_words_aggregate=dict(verbatim='但其他都是很实的，所以感觉有点奇怪',
            scope='preceding two-phrase preview inferred; not14 individual word acceptances', individual_labels_added=0),
        overall_solidity='too solid a little', difference_from_previous_adverse='Explicitly distinct from prior forward/slit-like solidity; not a universal absence of any squeezing/sharpness',
        missing_texture_verbatim='缺少那种唱歌时带点磨砂的填充的感觉',
        texture_mechanism='unknown: not automatically breathiness/roughness/subharmonics or a single control',
        strength_crescendo_acceptance='unknown: not separately restated',
        break_pitch_correctness_loudness_articulation_acceptance='unknown: not individually assessed',
        new_named_word_labels=1, new_other_individual_word_labels=0,
        working_comparator='Retain J as a provisionally useful direction for refinement, F original comparison also preserved',
        complete_phrase_or_song_accepted=False, adoption=False, agent_heard=False, measurement_validated=False, general_rule_validated=False)
    clarification = dict(date='2026-10-13', submissions=1, type='reference_selection_not_new_listening_trial',
        question='你说的“磨砂填充”质感，主要以哪个已有版本为参照？这能帮助下一轮区分颗粒质感和气声，而不是仅把声音调虚。',
        answer='白烁这两句的质感', reference=media['author_reference'],
        reference_boundary='Already delivered current1.65c fixed-seeded author A, not unavailable historical1.56 audio',
        target='Desired singing texture/filling reference only; no author curves/arrays transferred',
        new_candidate_or_new_auditory_acceptance=False)
    save(RUN / 'feedback/feedback.json', feedback)
    save(RUN / 'feedback/texture-reference.json', clarification)
    config = load(REGISTRY)
    old_path = ROOT / config['response_indices'][0]
    old_index = load(old_path)
    response_ids = [feedback['response_record'], 'RESP:LASTPAGE-OWN-BRIGHT-CUTE-01',
        'RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01', 'RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01',
        'RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01', 'RESP:LASTPAGE-OWN-LI-TENC-STAGES-01']
    entities = ['PER:S1', 'EVT:T5', 'ACO:L1', 'ACO:S3', 'ACO:S4', 'EVT:S4']
    parameters = ['PARAM:C03.01', 'PARAM:C11.01', 'PARAM:C12.01', 'PARAM:C13.01']
    packet = collect_context(entities, parameters, response_ids)
    review_decisions = [dict(id=r['id'], decision='keep_unknown', reason='Bind existing acoustic observations without equating level/features to perceptual texture or transition',
        condition_match='Current J/F li and adjacent ti, author reference has different clock/music',
        limitations='No calibrated roughness/force detector or exact feedback boundary; no new model/audio processing') for r in packet['records']]
    save(RUN / 'design/review-knowledge-context.json', packet)
    review_plan = dict(id='LASTPAGE-J-FEEDBACK-RESIDUAL-REVIEW-01', scope='sealed JSON/geometry only; no PCM/NPZ/model execution',
        knowledge_context=dict(path='review-knowledge-context.json', sha256=ref(RUN / 'design/review-knowledge-context.json')['sha256'], decisions=review_decisions))
    save(RUN / 'design/review-protocol.json', review_plan)
    _, receipt = check_plan_knowledge(review_plan, RUN / 'design/review-protocol.json')
    save(RUN / 'evaluation/review-knowledge-receipt.json', receipt)
    obs = load(PRIOR / 'observations/results.json')
    review_rows = []
    for w in obs['windows']:
        if w['word'] == 276 and w['role'] == 'full_vowel' or w['role'].startswith('li_'):
            row = dict(word=w['word'], role=w['role'], start_s=w['interval_s'][0], end_s=w['interval_s'][1],
                F_RMS_dbfs=w['variants']['F']['level']['dbfs'], J_RMS_dbfs=w['variants']['J']['level']['dbfs'],
                J_minus_F_db=w['J_minus_F']['level_ratio_db'])
            for variant in ['F', 'J']:
                for ch in ['breathiness', 'voicing', 'tension']:
                    row[variant+'_'+ch+'_median'] = w['variants'][variant]['final_features'][ch]['median']
            review_rows.append(row)
    assert len(review_rows) == 8
    geometry = {r['word']: r for r in load(BASE / 'native_word_geometry.json')}
    ti_end = geometry[276]['native_vowel'][1]
    l_start = geometry[277]['phones'][0]['start_ms'] / 1000
    assert abs(ti_end-l_start) < 1e-9
    with (KNOW / 'composite-descriptors.csv').open(encoding='utf-8-sig', newline='') as f:
        descriptor = next(r for r in csv.DictReader(f) if r['id'] == 'DESC:02')
    bindings = [ref(PRIOR / 'observations/results.json'), ref(PRIOR / 'evaluation/native-independent-check.json'),
        ref(BASE / 'native_word_geometry.json'), ref(KNOW / 'composite-descriptors.csv'), ref(KNOW / 'knowledge-table.json')]
    review = dict(source_bindings=bindings, existing_phase_and_ti_rows=review_rows,
        native_clock=dict(ti_vowel_end_s=ti_end, li_l_start_s=l_start, new_gap_ms=0,
            boundary='same native clock F/J; continuity of time is not perceptual connectedness'),
        native_pitch_support=load(PRIOR / 'evaluation/native-independent-check.json')['rows'][0],
        transition_candidate='J l-preparation RMS -12.3553dB versus F and voicing feature decrease are possible clues, not a proven cause of user transition complaint',
        ti_boundary='J ti RMS -0.2035dB and predicted feature changes are limited responses; user compares virtual quality with author, not F regression',
        model_dependency='Entry pitch changes all predicted features and context; manual TENC/BREC/VOIC remain0/0/100. No single-channel cause isolated.',
        descriptor_reference=dict(id='DESC:02', record=descriptor, candidate_only=True,
            semantic_equivalence_to_user_sanded_filling='unknown; do not silently substitute rough/hoarse/breathy',
            descriptor_is_not_new_validated_entity=True),
        followup_priority=['Retain useful low-entry direction and first localize/review transition',
            'Keep ti/other solidity contrast as musical/context issue, not automatic ti gain correction',
            'Study desired texture against explicitly selected author A separately from transition'],
        next_candidate_frozen=False, reason_no_recipe='Texture-to-channel mapping and exact transition boundary not established; no unsupported gain/BREC/TENC combination',
        new_PCM_NPZ_reads=0, new_acoustic_measurements=0, new_native_calls=0, new_models=0, new_waveforms=0)
    save(RUN / 'evaluation/residual-review.json', review)
    supplement = dict(record_id=feedback['response_record'], append_only_feedback=True, feedback=feedback,
        texture_reference_clarification=clarification, prior_report=ref(REPORT / 'own-li-entry-pitch-probe-20261013.json'),
        table1_refs=entities+parameters+['DESC:02'], texture_descriptor_mapping='candidate only, no new measured definition',
        direction_supported=True, complete_phrase_accepted=False, causal_mechanism='unknown',
        adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/table2-supplement.json', supplement)
    report = dict(status='J_direction_supported_transition_texture_gaps_recorded', feedback=feedback,
        texture_reference_clarification=clarification, table2_supplement=supplement,
        residual_review=ref(RUN / 'evaluation/residual-review.json'),
        next_boundary='Retain J direction/provisional research comparator; prioritize transition and separately define author-anchored texture; K not frozen or executed',
        new_listening_feedback=1, new_reference_clarification=1, new_native_calls=0, new_models=0,
        new_waveforms=0, new_PCM_NPZ_reads=0, new_acoustic_measurements=0, old_J_receipt_exact=True,
        agent_heard=False, adoption=False, measurement_validated=False, general_rule_validated=False)
    save(REPORT / (NAME + '.json'), report)
    write_csv(REPORT / (NAME + '-residual-stages.csv'), review_rows)
    md = f'''# 最后一页：J方向支持与衔接/磨砂填充反馈

2026-10-13。用户完整原话：

> {TEXT}

计1次试听回复，J按上轮标注推定。另1次参照澄清回答“白烁这两句的质感”，绑定已交付当前1.65c fresh作者A SHA；它不是第二次独立实验/听觉验收。原话“缺失”字样原样保留，不代为更正。

## 得到支持与尚未通过分别记录

“方向对了，实了”支持J低位进入处理的当前方向/实感改善，保留J作为待调整的研究比较基底，F原对照保持；不是全句/整曲采用、音乐准确或力量渐强已验收。“衔接缺失有点不够”没有精确字界/时间，体到里只是上下文候选，不冒称用户已定位。

“身体的体字就有点虚”明确word276体，且用户说这个虚与白烁一样；不写成J相对F退化或作者波形相同。“其他都是很实的，所以感觉有点奇怪”为整体反差描述，不补14条逐字通过。整体略太实与实感改善可同时成立，不把虚实压成越实越好的单轴。

当前实感被用户明确区分于此前“前顶、声音变成一条缝”的实，不补完全无尖细/破音/咬字等全维度标签。缺少“唱歌时带点磨砂的填充”是新增所需质感，参照明确为白烁这两句；不要直接改写成沙哑、气声、次谐波或某一旋钮需求。DESC:02仅提供非互斥候选描述的边界，语义同一性/声学机制unknown，不修改表1定义或验证状态。

## 只读残余问题复核

体i结束{ti_end:.9f}s与里l开始{l_start:.9f}s连续，F/J原生clock精确，没有新增时间空洞；数学时间连续不证明听觉衔接充分。已有J l准备80ms的RMS相对F约−12.3553dB、voicing模型中位从−52.5519到−68.9385，是可能线索，不是衔接病因或生理发声量。实际pitch写点/邻接插值范围在原native检查保持，不能把用户的衔接描述等同静音/吞字。

体既有RMS相对F约−0.2035dB，模型特征也有上下文响应；用户说与白烁一样虚，未直接评F/J差距，故不自动补体音量或把它标成必须改实。里主体相对F约+1.2716dB且预测三通道因pitch改变，人工增量仍0；不能把本次更实或缺磨砂唯一归因于tension/breathiness/voicing。这里只读取封存JSON/几何，未解码音频/NPZ、重跑检测或模型。

## 下一工作边界

保留有支持的J低位进入方向，先定位并复核衔接；体与其它字反差作为音乐/上下文问题保留，质感另以白烁作者A为参照研究。不同时改衔接、声线、气声、张力和输出增益；未建立磨砂到通道的映射，不自动加BREC、加TENC或做“都更实”的修复。K尚未冻结/生成。

表2当前37行/近12系列追加本次复杂反馈与参照澄清，J旧pending技术字段/音频/receipt原字节保持，G/H/I阴性保持。新记录实际进入知识决策，J方向use、衔接/质感机制keep_unknown，而非拒绝当前方向或宣称通用规则。原歌音频Skill/作者原件/旧封存/抱C/unknown保持，Agent未听、measurement_validated=false、通用规律0，单Agent、CI仅手动。

[JSON]({NAME}.json)、[既有阶段CSV]({NAME}-residual-stages.csv)、[审计]({NAME}-audit.json)。
'''
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')
    idx = copy.deepcopy(old_index)
    assert len(idx['rows']) == 37 and idx['recent_response_series_count'] == 12
    row = next(r for r in idx['rows'] if r['id'] == feedback['response_record'])
    prior_row = copy.deepcopy(row)
    assert not row['feedback_sources']
    row.update(feedback_sources=[ref(REPORT / (NAME + '.json'))], feedback_record=feedback,
        reference_clarification=clarification, scope='J direction/solidity supported, transition/over-solidity/author-anchored texture remain; no complete adoption')
    assert row['source_record'] == prior_row['source_record'] and row['source'] == prior_row['source']
    idx.update(prior_index=ref(old_path), generator=ref(Path(__file__)), status='current_index_J_direction_supported_with_transition_texture_gaps')
    save(KNOW / (INDEX + '.json'), idx)
    csvrows = [dict(id=r['id'], kind=r['kind'], source_path=r['source']['path'], source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']), table1_refs='|'.join(r['table1_refs']), scope=r['scope']) for r in idx['rows']]
    write_csv(KNOW / (INDEX + '.csv'), csvrows)
    imd = '# 表2当前索引：J方向支持与质感/衔接缺口\n\n37行/近12系列保持；J计1试听回复与1参照澄清，非新增两实验。体单字标签/其它整体反差、旧G/H/I阴性及OBS复核分开，未整句采用。\n\n|ID|技术/原记录|追加反馈|\n|---|---|---|\n'
    for r in idx['rows']:
        fb = '、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包'
        imd += f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd += f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。\n'
    (KNOW / (INDEX + '.md')).write_text(imd, encoding='utf-8', newline='\n')
    config['response_indices'] = [ref(KNOW / (INDEX + '.json'))['path']]
    REGISTRY.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    current = collect_context(entities, parameters, response_ids)
    decisions = []
    for r in current['records']:
        ident = r['id']
        choice = 'use' if ident in response_ids[:3] else 'reject' if ident in response_ids[3:] else 'keep_unknown'
        reason = ('Retain supported J direction and exact texture/reference/adverse/aggregate boundaries; no complete acceptance' if choice == 'use' else
            'Prior finite G/H/I failed target or no meaningful improvement; preserve, no dose escalation' if choice == 'reject' else
            'Transition and sanded filling have no calibrated mechanism or isolated control mapping; maintain distinctions')
        decisions.append(dict(id=ident, decision=choice, reason=reason,
            condition_match='Current J/F two phrases, ti276/li277; selected author A texture reference differs in music/clock',
            limitations='One listening reply plus one reference clarification; no14word labels, causal mechanism, universal rule or complete phrase acceptance'))
    save(RUN / 'design/knowledge_context.json', current)
    save(RUN / 'evaluation/knowledge_receipt.json', validate_context(current, decisions))
    rr = next(r for r in current['records'] if r['id'] == feedback['response_record'])['record']
    assert rr['feedback_record'] == feedback and rr['reference_clarification'] == clarification
    status = ('当前状态J_direction_supported_transition_texture_gaps_recorded：2026-10-13J反馈“方向对了，实了”支持当前低入口方向/实感，未全句采用；'
        '衔接不足具体边界unknown，体276有点虚且用户称与白烁一样、其它整体很实/反差奇怪，不拆14逐字标签或体对F退化。'
        '整体稍太实但明确区别旧前顶/一条缝，缺唱歌带磨砂填充；1试听回复+1参照澄清绑定白烁已交付作者A质感。'
        '体i→里l时钟无新空洞，l准备−12.3553dB/voicing下降仅线索非病因；质感不等同BREC/沙哑/单旋钮。'
        'J暂作改善方向研究对照/F原对照保持，下一步优先衔接、质感另研究，K未冻结/执行；37索引/近12系列反馈和实际知识决策更新。'
        '本轮新PCM/NPZ读取/复测/原生/模型/音频0，原歌音频Skill/作者/旧阴性/抱C/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p = ROOT / name
        lines = p.read_text(encoding='utf-8').splitlines()
        ix = [i for i, l in enumerate(lines) if '当前状态J_entry_pitch_delivered_pending_listening：' in l]
        assert len(ix) == 1, name
        rel = 'docs/reports/lastpage/' + NAME + '.md'
        if '/' in name:
            rel = ('../../' if name.startswith('research/') else '../../../') + rel
        lines[ix[0]] = ('- ' if lines[ix[0]].startswith('- ') else '') + status + f' 见[J方向与衔接/质感反馈]({rel})。'
        if name == 'plan.md':
            for i, l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i] = '下一工作进入逐首更新，先《最后一页》：J低位进入方向/实感获支持，保留J研究方向与F原对照；全句稍太实、体虚/其它实反差、衔接不足和缺磨砂填充仍未解决。质感已绑定白烁这两句，先定位/复核衔接，质感分开研究；不自动补体增益/加BREC或多因素联动，K未冻结/执行。'
        if name == 'docs/knowledge/acoustic-manifestations-20261009/README.md':
            for i, l in enumerate(lines):
                if l.startswith('制作使用[当前表2索引]'):
                    lines[i] = f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近12系列/37行追加J方向支持与衔接/质感缺口，作者质感参照明确；旧字段/SHA/阴性保持。'
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    check(protected)
    check(bindings)
    for r in idx['rows']:
        check([r['source']] + r['feedback_sources'])
        if r['id'] != feedback['response_record']:
            assert r == next(q for q in old_index['rows'] if q['id'] == r['id'])
    with (KNOW / (INDEX + '.csv')).open(encoding='utf-8-sig', newline='') as f:
        assert list(csv.DictReader(f)) == [{k: str(v) for k, v in r.items()} for r in csvrows]
    gate = subprocess.run([sys.executable, 'tools/repository/check_repository.py', '--worktree'], cwd=ROOT, capture_output=True, encoding='utf-8')
    (RUN / 'logs/repository-gate.log').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    audit = dict(status='passed_with_explicit_transition_texture_mechanism_gaps', source=ref(Path(__file__)),
        protected_references=len(protected), source_bindings=bindings, listening_feedback=1, reference_clarification=1,
        new_named_word_labels=1, other_individual_labels=0, old_J_receipt_exact=True,
        current_J_feedback_and_author_reference_retrieved=True, old_index_fields_exact=True,
        new_PCM_NPZ_reads=0, new_acoustic_measurements=0, new_native_calls=0, new_models=0, new_waveforms=0,
        current_index=ref(KNOW / (INDEX + '.json')), current_registry=ref(REGISTRY), gate=gate.stdout.strip(),
        agent_heard=False, adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/audit.json', audit)
    save(REPORT / (NAME + '-audit.json'), audit)
    docs = [ref(p) for p in sorted(REPORT.glob(NAME + '*'))] + [ref(p) for p in sorted(KNOW.glob(INDEX + '*'))] + [ref(REGISTRY)]
    save(RUN / 'completion-manifest.json', dict(status=report['status'], files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
                                               documents=docs, entries=[ref(ROOT / n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'], direction_supported=True, listening_feedback=1, reference_clarification=1,
        texture_reference=clarification['answer'], new_waveforms=0, gate=audit['gate']), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
