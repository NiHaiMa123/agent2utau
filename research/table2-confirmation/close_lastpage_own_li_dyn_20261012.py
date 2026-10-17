"""Append named H feedback; freeze one independent TENC hypothesis from F."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, check
from agent2utau.knowledge import collect_context, validate_context, check_plan_knowledge

PRIOR = ROOT / 'runs/experiments/lastpage-own-li-dyn-20261012'
F = ROOT / 'runs/experiments/lastpage-own-control-neutral-20261012'
BASE = ROOT / 'runs/lastpage_loudness_skill_v02_20261007'
RUN = ROOT / 'runs/research/lastpage-own-li-DYN-feedback-20261012'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'own-li-DYN-feedback-20261012'
KNOW = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
INDEX = 'table2-DYN-feedback-index-20261012'
REGISTRY = KNOW / 'active-knowledge-sources.json'


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
    registry_ref = ref(REGISTRY)
    protected = [r for r in original if r['path'] != registry_ref['path']]
    RUN.mkdir(parents=True)
    (RUN / 'logs').mkdir()
    save(RUN / 'protected-before.json', protected)
    for name in ENTRIES + [registry_ref['path']]:
        p = RUN / 'before' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / name).read_bytes())
    save(RUN / 'design/mutable-registry-before.json', dict(
        reason='Explicit catalogue pointer maintenance; original registry bytes and all old indices/receipts preserved',
        registry=registry_ref, preserved_original_bytes=ref(RUN / 'before' / registry_ref['path'])))
    media = load(PRIOR / 'evaluation/delivery-check.json')['outputs']
    feedback = dict(
        verbatim='里字不够实，强度也不够大', submissions=1, date='2026-10-12',
        response_record='RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01',
        candidate=media['candidate_preview'], baseline=media['original_preview'], author_reference=media['author_reference'],
        referent='H inferred from preceding labelled H/F/author delivery; word li explicitly named',
        target_word=277, char='里', interval_s=[212.9572916666667, 213.58541666666667],
        explicit_attributes=dict(solidity='insufficient', strength='insufficient'),
        exact_comparator_and_magnitude='unknown: no explicit H-versus-F/author ranking or magnitude',
        precise_subword_location='unknown: no onset/body/tail location selected',
        other_word_and_squeezing_sharpness_break_articulation_labels='unknown',
        named_word_feedback_count=1, attribute_count=2, whole_candidate_explicit_rejection=False,
        target_requirement_met=False, adoption=False, agent_heard=False, measurement_validated=False,
        all_DYN_ineffective=False, general_rule_validated=False)
    check([feedback[k] for k in ['candidate', 'baseline', 'author_reference']])
    save(RUN / 'feedback/feedback.json', feedback)
    old_report = load(REPORT / 'own-li-DYN-probe-20261012.json')
    phases = old_report['phase_rows']
    assert len(phases) == 6
    f_window = next(w for w in load(F / 'observations/results.json')['windows']
                    if w['word'] == 277 and w['role'] == 'full_vowel')
    features = f_window['variants']['F']['final_features']
    geometry = next(r for r in load(BASE / 'native_word_geometry.json') if r['word'] == 277)
    own = next(r for r in load(BASE / 'agent_word_decisions.json') if r['word'] == 277)
    s, e = geometry['native_vowel']
    arrival = own['entry_actions'][0]['arrival']
    peak = own['body'][0]['parameters'][1]
    body_end = own['entry_actions'][0]['body_end']
    turn = own['entry_actions'][1]['onset']
    nodes = [[s, 0], [arrival, 0], [peak, 10], [body_end, 4], [turn, 4], [e, 0]]
    doc = yaml.safe_load((F / 'score/lastpage_own_control_neutral_F.ustx').read_text(encoding='utf-8-sig'))
    desc = doc['expressions']['tenc']
    assert desc['default_value'] == 0 and desc['min'] <= 0 and desc['max'] >= 10
    bindings = [ref(REPORT / 'own-li-DYN-probe-20261012.json'), ref(BASE / 'native_word_geometry.json'),
                ref(BASE / 'agent_word_decisions.json'), ref(F / 'score/lastpage_own_control_neutral_F.ustx'),
                ref(F / 'observations/results.json'), ref(KNOW / 'knowledge-table.json'),
                ref(KNOW / 'control-details.csv'),
                ref(ROOT / 'skills/singing-expression-editor/references/joint-phonation-and-sustain.md')]
    review = dict(source_bindings=bindings, H_phase_rows=phases, F_final_features_full_li=features,
        observed_boundary='H gain gesture changed output only; phonation/raw model output exactly F. Full-li RMS H-F -1.2304237982370876dB.',
        causal_boundary='Energy reduction may be relevant but is not the proven cause of reported solidity/strength. Negative tension median is a model feature, not insufficient physiological support.',
        baseline='F improved working comparator; not full-song accepted or proven fully solid',
        next_hypothesis='One TENC-only establishment/recovery from F, DYN restored to F 0; efficacy and cause unknown',
        choice_reason='VOIC G and output envelope H failed current target; TENC changes a distinct acoustic conditioning channel and has not been isolated for this F/li condition.',
        counterevidence='E was solid but squeezed/thin/sharp; removing grouped controls improved F and author C approached A. These do not isolate TENC and prohibit treating positive TENC as automatically better.',
        alternative_rejected='Do not boost H DYN or combine VOIC/BREC/TENC: it would confound sound-level and phonation effects. No dose sweep.',
        TENC_descriptor=desc, native_geometry=geometry, new_PCM_NPZ_reads=0, new_measurements=0,
        new_models=0, new_waveforms=0)
    save(RUN / 'evaluation/strength-review.json', review)
    supplement = dict(record_id=feedback['response_record'], append_only_feedback=True, feedback=feedback,
        prior_report=ref(REPORT / 'own-li-DYN-probe-20261012.json'),
        table1_refs=['PER:S1', 'EVT:L2', 'ACO:L1', 'PARAM:C10.01'],
        measured_failure_cause='unknown', adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/table2-supplement.json', supplement)
    report = dict(status='H_named_feedback_closed_TENC_design_frozen', feedback=feedback, table2_supplement=supplement,
        strength_review=ref(RUN / 'evaluation/strength-review.json'),
        next_protocol_path=(RUN / 'design/next-li-TENC-protocol.json').relative_to(ROOT).as_posix(),
        new_models=0, new_waveforms=0, new_PCM_NPZ_reads=0, agent_heard=False, adoption=False,
        measurement_validated=False, general_rule_validated=False)
    save(REPORT / (NAME + '.json'), report)
    write_csv(REPORT / (NAME + '-prior-stages.csv'), phases)
    md = f'''# 最后一页：里DYN层次H反馈与发声候选

2026-10-12。用户原话“里字不够实，强度也不够大”，计1次回复、1个明确命名字、2项属性，按上轮标注绑定H的word277“里”。当前目标实感与强度未通过，H不采用。未明确H与F/作者的排序、字内时点或量级，也未评价其它字、前顶/挤细/尖、破音或咬字；这些保持unknown，不写成全句逐字否定。F仍为先前“更好了”的工作基底，非整曲验收。

## 反馈与技术响应分开

H仅改变原生DYN，发声输入、预测与模型raw保持F；阶段输出由弱入口展开后回收的数字变化不能证明听觉发力通过。已有数据中整体里H−F RMS约−1.2304dB，入口约−4dB，主体回收阶段约+0.798dB；这提示H还有整体减弱的作用，但不是用户反馈病因或感知响度真值。本次仅复核封存JSON/自己时钟/工程描述，音频与数组流式核SHA，没有新解码、复测、模型或合成。

## 下一项I：从F隔离TENC建立与回收

回到F原生DYN0，保留Bright40/Cute60、全部音高/音乐与音素时钟、CLR/BREC/VOIC/SHFC。只在里元音{s:.9f}–{e:.9f}s设计TENC：UI节点{nodes}。入口及自身到达前保持0，到达后建立到主体锚点+10，再回收至+4，保留到自己的降音准备，元音结束恢复0。逐段smoothstep零切线、原整数5tick网格；+10对应张力输入增量约+0.5，+4约+0.2，执行须独立核当前原生算术/实际支撑/clip。声母l不主动添加，真实采样边缘若触及l或面必须另列，不缩掩码掩盖。

此为单个有限的模型条件假设，不是TENC等于力量或实感的定论。F已有里张力模型中位数{features['tension']['median']:.6f}也不能证明生理支撑不足。此前E“更实但前顶、挤细、尖”，组合中和F改善及作者中和C接近A均保留为反例；尚不能把它们归因到单一TENC。选+10为温和首轮设计，并检验是否重现挤尖，不恢复原组合、不扩大VOIC或DYN剂量。数值及阶段由自己音乐判断选择，不复制作者曲线/包络。

I工程/音频尚未生成。有限预算：context28 I/I_repeat两套新的固定种子variance/acoustic/vocoder波形（重复不是独立条件），2新F0；context29复用绑定F并检查全PCM/看，另2句原生缓存技术导出单列。独立重建仅最终张力改变，variance输入/预测及其它通道保持F；DYN0、固定1.5/PCM24、34贡献拼接/重叠与全部15字邻域/自身阶段检查。声学上下文可能影响相邻字，不能预先声称音频仅里改变；accepted抱C与其它贡献保持。试听关注里实感、发力发展及前顶/挤细/尖/破音/l咬字，技术代理不替代验收。

表2当前索引追加H本次命名反馈，旧pending技术记录与SHA保持；下一项知识检索实际包含H/G否定、F工作基底与E/C反例，逐ID决策保留外推。Agent未听，measurement_validated=false、通用规律0。原歌/旧音频/Skill/作者原件不改，单Agent、CI仅手动。

[阶段CSV]({NAME}-prior-stages.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')
    config = load(REGISTRY)
    old_path = ROOT / config['response_indices'][0]
    old_index = load(old_path)
    index = copy.deepcopy(old_index)
    assert len(index['rows']) == 34 and index['recent_response_series_count'] == 10
    row = next(r for r in index['rows'] if r['id'] == feedback['response_record'])
    before_row = copy.deepcopy(row)
    assert not row['feedback_sources']
    row.update(feedback_sources=[ref(REPORT / (NAME + '.json'))], feedback_record=feedback,
               scope='H technical delivery retained; li explicitly insufficient solidity/strength, not adopted')
    assert row['source_record'] == before_row['source_record'] and row['source'] == before_row['source']
    index.update(generator=ref(Path(__file__)), prior_index=ref(old_path), status='current_index_H_named_feedback_appended_with_explicit_gaps')
    save(KNOW / (INDEX + '.json'), index)
    csvrows = [dict(id=r['id'], kind=r['kind'], source_path=r['source']['path'], source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']), table1_refs='|'.join(r['table1_refs']), scope=r['scope']) for r in index['rows']]
    write_csv(KNOW / (INDEX + '.csv'), csvrows)
    imd = '# 表2当前索引：H里实感/强度不足反馈\n\n34行、近10系列保持；H计1命名字回复/2属性，G否定与旧阴性保留。重复/窗口/packet不是独立样本。旧技术状态与后续反馈分开。\n\n|ID|技术/原记录|追加反馈|\n|---|---|---|\n'
    for r in index['rows']:
        fb = '、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包'
        imd += f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd += f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。局部反馈不升级通用规则或全面测量验证。\n'
    (KNOW / (INDEX + '.md')).write_text(imd, encoding='utf-8', newline='\n')
    config['response_indices'] = [ref(KNOW / (INDEX + '.json'))['path']]
    REGISTRY.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    response_ids = [feedback['response_record'], 'RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01',
        'RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01', 'RESP:LASTPAGE-OWN-BRIGHT-CUTE-01', 'RESP:LASTPAGE-AUTHOR-CONTROL-NEUTRAL-01']
    packet = collect_context(['PER:S1', 'EVT:L2', 'ACO:L1'], ['PARAM:C10.01', 'PARAM:C11.01', 'PARAM:C13.01'], response_ids)
    reasons = {
        feedback['response_record']: ('reject', 'H li explicitly insufficient solidity and strength; do not retain H attenuation or boost its dose'),
        response_ids[1]: ('reject', 'G rejected without dimensions; no VOIC escalation'),
        response_ids[2]: ('use', 'F aggregate improvement is working comparator; retain its music, voice and neutral DYN'),
        response_ids[3]: ('use', 'E squeezed/thin/sharp is a required adverse comparator, not proof of isolated TENC cause'),
        response_ids[4]: ('use', 'Author grouped control cancellation approached A; preserve counterexample against universal added tension'),
        'PARAM:C13.01': ('extrapolate', 'One gentle TENC establishment/recovery; perceptual strength/solidity effect unverified'),
        'PARAM:C10.01': ('use', 'Keep F DYN0 to separate output attenuation from acoustic conditioning'),
        'PARAM:C11.01': ('use', 'Keep F VOIC100; failed G dose is not recycled')}
    decisions = [dict(id=r['id'], decision=reasons.get(r['id'], ('use', 'Separate perceived strength, level and model feature'))[0],
        reason=reasons.get(r['id'], ('use', 'Separate perceived strength, level and model feature'))[1],
        condition_match='Current1.65c own li277 and F voice/music; author C is cross-condition counterevidence',
        limitations='No universal dose, physiology estimate or causal attribution; only H has explicit named solidity/strength feedback') for r in packet['records']]
    save(RUN / 'design/knowledge_context.json', packet)
    save(RUN / 'evaluation/knowledge_receipt.json', validate_context(packet, decisions))
    retrieved = next(r for r in packet['records'] if r['id'] == feedback['response_record'])
    assert retrieved['record']['feedback_record'] == feedback
    nextplan = dict(id='LASTPAGE-OWN-LI-TENC-STAGES-01', status='finite_design_frozen_not_executed', variant='I',
        baseline_score=ref(F / 'score/lastpage_own_control_neutral_F.ustx'), baseline_project=ref(F / 'delivery/lastpage_own_control_neutral_F.ustx'),
        baseline_audio=media['original_preview'], author_reference=media['author_reference'],
        target_word=277, affected_context=28, control_context=29, review_words=list(range(270, 285)),
        gesture=dict(channel='tenc', UI_baseline=0, UI_nodes_s=nodes, unit='UI/20 model tension delta, not PCM dB',
            interpolation='piecewise cubic smoothstep, original integer5tick UI quantization', support_s=[s, e],
            purposes=['retain onset/arrival', 'establish at own body anchor', 'recover with own music', 'restore at native vowel exit']),
        fixed=['all music/pitch/vibrato/notes', 'lyrics/CLR/full phoneme clock', 'two-stage Bright40/Cute60',
               'BREC0/VOIC100/SHFC0/DYN0', 'variance inputs/predictions', 'seeds11/101', 'common gain1.5'],
        hypothesis='Limited TENC change may affect establishment/solidity/force; unknown, adverse squeezed/thin/sharp risk explicit',
        alternative_rejected=review['alternative_rejected'], dependencies='New full native inputs and fresh variance/acoustic/vocoder; check unchanged F predictions and all non-tension feeds',
        budget=dict(candidate_count=1, new_native_cached_contexts=2, new_seeded_variance_calls=2,
            new_seeded_synthesis_waveforms=2, new_F0_calls=2, sealed_F_context29_reuse=True),
        gates=['SHA-bound knowledge receipt before score/model writes', 'score changes only target tenc ys; roundtrip and original5tick identity',
            'independent native TENC units/sample arithmetic/support/clip; only final tension changes, variance/predictions/other feeds exact F',
            'I/I_repeat exact; finite unclipped fixed1.5 PCM24, original34contributions and shared overlap explicitly checked',
            'DYN0; full15word/phone/own-stage raw/mel/features/F0/PCM proxies scoped, not perceptual verdicts',
            'context29 independent contribution and kan real phone PCM exact; shared padding separately; acceptedbaoC retained'],
        stops=['hash/identity/isolation mismatch', 'nonfinite/file clipping', 'no dose sweep/combined channels/automatic adoption'],
        listening=['li solidity', 'strength establishment/recovery', 'front-pushing/squeezed/thin/sharp', 'break/articulation/neighbor effects'],
        knowledge_context=dict(path='knowledge_context.json', sha256=ref(RUN / 'design/knowledge_context.json')['sha256'], decisions=decisions),
        new_score_written=0, new_models=0, new_audio=0, adoption=False, agent_heard=False,
        measurement_validated=False, general_rule_validated=False)
    save(RUN / 'design/next-li-TENC-protocol.json', nextplan)
    _, receipt = check_plan_knowledge(nextplan, RUN / 'design/next-li-TENC-protocol.json')
    assert receipt == dict(load(RUN / 'evaluation/knowledge_receipt.json'), packet_sha256=nextplan['knowledge_context']['sha256'])
    status = ('当前状态H_named_feedback_closed_TENC_design_frozen：2026-10-12“里字不够实，强度也不够大”计1命名字回复/2属性，绑定H里277，目标未通过/H不采用。'
        '不补H对F/作者排序、字内时点/其它字/挤尖破音咬字标签。H输出包络数字变化非发力通过、全里−1.2304dB仅代理非病因；F仍工作基底。'
        '近10系列/34索引追加反馈且知识receipt实际消费H/G否定、F与E/C反例。下一项仅冻结F/DYN0基底I：里TENC0→+10→+4→0、自身时钟，实感/力量效果unknown并检查前顶挤细尖。'
        '2新seeded重复/2新F0/2原生技术上下文预算实际0，I工程音频未写；本轮新PCM/NPZ读取/复测/模型/音频0。'
        '原歌音频Skill/作者/旧阴性/抱C/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p = ROOT / name
        lines = p.read_text(encoding='utf-8').splitlines()
        ix = [i for i, l in enumerate(lines) if '当前状态H_DYN_delivered_pending_listening：' in l]
        assert len(ix) == 1, name
        rel = 'docs/reports/lastpage/' + NAME + '.md'
        if '/' in name:
            rel = ('../../' if name.startswith('research/') else '../../../') + rel
        lines[ix[0]] = ('- ' if lines[ix[0]].startswith('- ') else '') + status + f' 见[里实感/强度反馈]({rel})。'
        if name == 'plan.md':
            for i, l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i] = '下一工作进入逐首更新，先《最后一页》：H里明确不够实/强度不足，已回填表2与知识决策；H不采用，F保留工作比较基底。下一项I仅冻结F/DYN0基底的里TENC建立回收，未执行；独立核查输入/真实支撑后试听实感、发力及前顶挤细尖副作用，不组合通道或扫剂量。'
        if name == 'docs/knowledge/acoustic-manifestations-20261009/README.md':
            for i, l in enumerate(lines):
                if l.startswith('制作使用[当前表2索引]'):
                    lines[i] = f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近10系列追加H里两项不足、G否定保持；旧记录/SHA保持，不是通用规则。'
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    check(protected)
    check(bindings)
    for r in index['rows']:
        check([r['source']] + r['feedback_sources'])
        if r['id'] != feedback['response_record']:
            assert r == next(q for q in old_index['rows'] if q['id'] == r['id'])
    with (KNOW / (INDEX + '.csv')).open(encoding='utf-8-sig', newline='') as f:
        assert list(csv.DictReader(f)) == [{k: str(v) for k, v in r.items()} for r in csvrows]
    gate = subprocess.run([sys.executable, 'tools/repository/check_repository.py', '--worktree'], cwd=ROOT, capture_output=True, encoding='utf-8')
    (RUN / 'logs/repository-gate.log').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    audit = dict(status='passed_with_explicit_perception_and_TENC_cause_gaps', source=ref(Path(__file__)),
        feedback_submissions=1, named_word_feedback_count=1, attribute_count=2,
        new_models=0, new_waveforms=0, new_PCM_NPZ_reads=0, protected_references=len(protected),
        source_bindings=bindings, current_index=ref(KNOW / (INDEX + '.json')), current_registry=ref(REGISTRY),
        next_protocol=ref(RUN / 'design/next-li-TENC-protocol.json'), knowledge_H_feedback_retrieved=True,
        CSV_and_prior_index_fields_exact=True, gate=gate.stdout.strip(), agent_heard=False,
        adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/audit.json', audit)
    save(REPORT / (NAME + '-audit.json'), audit)
    docs = [ref(p) for p in sorted(REPORT.glob(NAME + '*'))] + [ref(p) for p in sorted(KNOW.glob(INDEX + '*'))] + [ref(REGISTRY)]
    save(RUN / 'completion-manifest.json', dict(status=report['status'], files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
                                               documents=docs, entries=[ref(ROOT / n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'], feedback=feedback['verbatim'], new_waveforms=0,
                         knowledge_feedback_retrieved=True, gate=audit['gate']), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
