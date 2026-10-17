"""Bind one human reply and review sealed two-phrase feature responses.

Only reads existing NPZ arrays; no waveform decoding or model/native execution.
The following explicit VOIC design is preparation, not an implemented control.
"""
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, check

PROBE = ROOT / 'runs/experiments/lastpage-voice-baseline-20261011'
BASE = ROOT / 'runs/lastpage_loudness_skill_v02_20261007'
RUN = ROOT / 'runs/research/lastpage-voice-baseline-feedback-20261011'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'voice-baseline-feedback-20261011'
CHANNELS = ['breathiness', 'voicing', 'tension']


def main():
    assert not RUN.exists(), 'New run only.'
    assert not (REPORT / (NAME + '.json')).exists()
    sealed = load(PROBE / 'completion-manifest.json')
    check(sealed['files'] + sealed['documents'] + sealed['entries'])
    protected = load(PROBE / 'protected-before.json') + sealed['files'] + sealed['documents']
    check(protected)
    RUN.mkdir(parents=True)
    for name in ENTRIES:
        p = RUN / 'before' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / name).read_bytes())
    save(RUN / 'protected-before.json', protected)
    original = load(REPORT / 'voice-baseline-probe-20261011.json')
    # Use the actual previously displayed media, not unrelated full-song files.
    feedback = dict(original_text='还是虚，没有退化', reply_count=1,
        target_record='RESP:LASTPAGE-VOICE-BASELINE-01', comparison='B-A',
        scope='delivered two-phrase preview, aggregate reply; full song not confirmed heard',
        candidate=original['deliveries']['candidate_preview'],
        original_A=original['deliveries']['original_preview'],
        author_reference=original['deliveries']['author_reference'],
        target_solidity='still airy; target unresolved', deterioration='none reported, aggregate',
        kan_specific_deterioration='unknown: not separately named in this reply',
        break_articulation_loudness_separate_labels='unknown',
        no_perceptible_difference='not explicitly stated', adoption=False,
        independent_word_labels_added=0, agent_heard=False)
    check([feedback[k] for k in ['candidate', 'original_A', 'author_reference']])
    save(RUN / 'feedback/feedback.json', feedback)
    geometry = {r['word']: r for r in load(BASE / 'native_word_geometry.json')}
    execution = load(PROBE / 'fresh/execution.json')['rows']
    sources = [ref(BASE / 'native_word_geometry.json'), ref(PROBE / 'fresh/execution.json')]
    rows = []
    for j, (ctx, first, last) in enumerate([(28, 270, 278), (29, 279, 284)]):
        clock_path = PROBE / f'native-inputs/A/phrase_{j:03d}.json'
        clock = load(clock_path)
        sources.append(ref(clock_path))
        arrays = {}
        for v in ['A', 'B']:
            for kind in ['inputs', 'predictions']:
                path = PROBE / f'fresh/context{ctx}/{v}/{kind}.npz'
                sources.append(ref(path))
                with np.load(path, allow_pickle=False) as z:
                    arrays[v, kind] = {k: z[k].copy() for k in z.files}
        time = execution[j]['wave_start_s'] + np.arange(execution[j]['frames']) * clock['frame_ms'] / 1000
        for word in range(first, last + 1):
            g = geometry[word]
            lo, hi = g['native_vowel']
            for label, a, b in [('full_vowel', lo, hi), ('core15_85', lo + .15*(hi-lo), hi - .15*(hi-lo))]:
                mask = (time >= a) & (time < b)
                assert mask.any(), (word, label)
                for ch in CHANNELS:
                    ap = arrays['A', 'predictions'][ch + '_pred'].reshape(-1)[mask]
                    bp = arrays['B', 'predictions'][ch + '_pred'].reshape(-1)[mask]
                    af = arrays['A', 'inputs'][ch].reshape(-1)[mask]
                    bf = arrays['B', 'inputs'][ch].reshape(-1)[mask]
                    rows.append(dict(context=ctx, word=word, char=g['char'], window=label,
                        start_s=a, end_s=b, frames=int(mask.sum()), channel=ch,
                        A_pred_median=float(np.median(ap)), B_pred_median=float(np.median(bp)),
                        A_final_median=float(np.median(af)), B_final_median=float(np.median(bf)),
                        B_minus_A_final_median=float(np.median(bf)-np.median(af)),
                        median_framewise_B_minus_A=float(np.median(bf-af))))
    core = [r for r in rows if r['window'] == 'core15_85']
    counts = {ch: dict(positive=sum(r['B_minus_A_final_median'] > 0 for r in core if r['channel']==ch),
        negative=sum(r['B_minus_A_final_median'] < 0 for r in core if r['channel']==ch)) for ch in CHANNELS}
    assert len(rows)==90 and counts['breathiness']['positive']==15
    save(RUN / 'evaluation/word-feature-review.json', dict(rows=rows, sources=sources,
        clock='raw wave_start_s + frame index * exported float32 frame_ms; half-open windows',
        units='model input feature units, not output dB, HNR or physiological measurements',
        no_new_measurements=True, core_direction_counts=counts))
    with (REPORT / (NAME + '-words.csv')).open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    # Explicit next strategy. Constants express an independently selected intent;
    # they are not learned auditory thresholds or an inverse prediction curve.
    core_voic = {r['word']: r for r in core if r['channel']=='voicing'}
    selected = {271, 272, 274, 277, 278}
    baseline = ROOT / 'runs/production/lastpage-accepted-baseline-20261011/delivery/lastpage_accepted_C_baseline.ustx'
    doc = yaml.safe_load(baseline.read_text(encoding='utf-8-sig'))
    limits = doc['expressions']['voic']
    assert limits['min']==0 and limits['max']==200 and limits['default_value']==100
    actions = []
    for word in range(270, 285):
        lo, hi = geometry[word]['native_vowel']
        value = core_voic[word]['A_final_median']
        dose = round(min(3.0, max(0.0, .5*(-44.0-value)))/.12) if word in selected else 0
        assert (dose > 0) == (word in selected)
        actions.append(dict(word=word, char=geometry[word]['char'], context=28 if word<279 else 29,
            action='finite_voicing_overlay' if dose else 'keep_baseline',
            evidence_status='aggregate airy feedback plus current model descriptor; no individual airy label',
            baseline_core_voicing=value, additive_UI=dose, nominal_feature_increment=dose*.12,
            support_s=[lo, hi] if dose else None,
            attack_s=min(.050,.2*(hi-lo)) if dose else None,
            release_s=min(.045,.2*(hi-lo)) if dose else None,
            shape='continuous linear attack/hold/release, zero outside vowel; no reattack at extension notes' if dose else None,
            execution_state='planned'))
    plan = dict(protocol_id='LASTPAGE-CONDITIONED-VOIC-01', state='planned_not_compiled_or_executed',
        baseline=ref(baseline), speaker='Normal75/Classic25 both stages',
        phrase_intent='first sentence sustained support across linking words; preserve stronger bodies and release; second sentence unchanged',
        design_reference=-44.0, partial_fraction=.5, feature_cap=3.0,
        reference_status='Agent design choice; not an auditory threshold, universal target, author fit or physiological scale',
        actions=actions, selected_words=sorted(selected), scope_words=list(range(270,285)),
        original_declared_VOIC_range=[0,200], native_loading_quantization_and_overlay_range='must verify before any render',
        condition_changes=['manual voicing only'],
        retained=['pitch','phones','speaker','manual breathiness','manual tension','SHFC','native DYN','fixed gain1.5'],
        expected='test additional finite voicing support on first phrase without discarding baseline contours',
        possible_side_effects=['hardness','break','articulation change','level change','unintended neighboring response'],
        budget=dict(candidates=1, contexts=2, variants=['A','A_repeat','B','B_repeat'], seeded_waveforms=8),
        required_checks=['5tick native readback; baseline plus overlay without saturation; no AP/SP or consonant edits',
            'two-stage speaker, pitch/phones/predictions and other input channels exact',
            'fresh A equals sealed A; all same-input repeats exact; changed input only voicing on declared support',
            'context29 input and PCM exact; all 32 other contexts including accepted bao C exact',
            'DYN/fixed gain/PCM assembly and output F0/limited acoustic response separately checked',
            'deliver full carrier and same-gain phrases plus separate unchanged author reference; human solidity and side effects required'],
        stop='one candidate then accept or close; no automatic dose increase, parameter sweep or universal conclusion',
        new_waveforms=0, author_arrays_used=False, measurement_validated=False)
    save(RUN / 'design/next-voicing-plan.json', plan)
    supplement = dict(record_id='RESP:LASTPAGE-VOICE-BASELINE-01', append_only_feedback=True,
        prior_report=ref(REPORT / 'voice-baseline-probe-20261011.json'), feedback=feedback,
        status='target_unresolved_no_deterioration_reported', adoption=False,
        independent_contexts=2, candidate_feedback_count=1, new_waveforms=0,
        table1_refs=['PER:S1','PARAM:C20.01','PARAM:C20.03','PARAM:C20.05'],
        new_voicing_plan_is_not_a_response_record=True, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/table2-supplement.json', supplement)
    report = dict(status=supplement['status'], feedback=feedback, table2_supplement=supplement,
        direction_counts=counts, word_review=ref(RUN / 'evaluation/word-feature-review.json'),
        next_plan=plan, sealed_probe_unchanged=True, agent_heard=False)
    save(REPORT / (NAME + '.json'), report)
    md = '''# 最后一页：声线候选反馈收口与下一项准备

2026-10-11。用户原话：“还是虚，没有退化”。绑定已交付B/A两句与独立白烁参考的SHA，计1条聚合反馈。B仍偏虚、目标未解决；没有报告退化。未细分“看”、破音、咬字或响度，不补造逐字阴性/正常标签，也不改写为“完全没区别”。本候选不采用，原Normal75/Classic25与已接受抱C保留。原封存报告的pending是交付时状态，本补充记录后续反馈。

只读核对15字、全元音及15%–85%主体、三个预测/最终输入，共90行。以波形起点和实际float32帧时钟取半开窗口；两个窗口不能混用。主体气声特征中位数B−A在15字均为正，有声特征有升有降，说明此次speaker替换没有形成统一的有声补偿；不将特征直接解释为输出气声/谐噪比或虚实病因。

下一项仅准备：回到原声线，在“想把你抱进身体里面”整句规划持续支撑，为把271、你272、进274、里277、面278设计有限VOIC包络；想/抱/身/体保持，其后“不敢让你看见”六字完整保持。“看”原正例不是全句验收；选中五字也不是新增五条偏虚标签。设计参考−44、补偿比例0.5与上限3特征单位由Agent选择，只作当前音乐意图的有限实现依据；不作为听觉阈值或通用规律。全部15字均有处理台账，低预测值不会自动变成坏音标签。

在元音内缓慢建立、保持、回收，不在延续音重启；辅音和呼吸保护，原人工事件叠加后须原生读回检查合法范围、5tick量化与裁剪。保持音高/音素/两阶段speaker/其它控制/DYN/固定1.5。预算单个候选、两完整上下文各A/重复/B/重复，共8套固定种子波形；目前编译、原生导出、模型执行和新波形均0。通过执行检查后交付完整载体及两句，同增益，白烁独立参考继续单独给出。试听后接受或收口，不自动加量。此计划并非新控制响应证据。

Agent未听；全曲接受、独立留出和通用规律均未完成。原歌曲/音频/Skill/作者资料/旧run保持，单Agent、CI仅手动。详见[逐字输入核对](voice-baseline-feedback-20261011-words.csv)、[JSON](voice-baseline-feedback-20261011.json)、[审计](voice-baseline-feedback-20261011-audit.json)。
'''
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')
    status = ('当前状态voice_baseline_feedback_closed_next_voicing_planned：2026-10-11“还是虚，没有退化”绑定B/A两句与独立白烁参考，'
        '计1聚合回复，目标未解决/未报告退化，不新增逐字标签；Bright25候选不采用、原声线及抱C保留。'
        '两句15字/两窗口/三通道90行已读，气声主体特征15字均升、有声有升有降，非听觉病因。'
        '下一项仅准备原声线下第一句五字有限VOIC补偿、其它十字含看所在整句保持；15字处理台账、单候选8套预算列明，'
        '须先验证原生叠加范围/采样/隔离与重复，编译/新导出/新波形0。Agent未听、通用规律0，原工程/音频/Skill不改，单Agent/CI仅手动。')
    for name in ENTRIES:
        p = ROOT / name
        lines = p.read_text(encoding='utf-8').splitlines()
        ids = [i for i,line in enumerate(lines) if '当前状态one_voice_baseline_candidate_delivered_pending_listening：' in line]
        assert len(ids)==1, name
        relative = 'docs/reports/lastpage/' + NAME + '.md'
        if '/' in name: relative = ('../../' if name.startswith('research/') else '../../../') + relative
        lines[ids[0]] = ('- ' if lines[ids[0]].startswith('- ') else '') + status + f' 见[声线反馈与发声准备]({relative})。'
        for i, line in enumerate(lines):
            if name=='plan.md' and line.startswith('下一工作进入逐首更新，先《最后一页》：'):
                lines[i] = '下一工作进入逐首更新，先《最后一页》：声线替换已收口不采用；按本轮15字台账准备原声线下第一句有限VOIC补偿。先核查现有VOIC叠加、原生范围/5tick量化及独立检查器，再执行单候选两上下文8套预算并分开交付自身/白烁参考；不扫参数，不把准备当执行或整曲验收。'
        p.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    check(protected); check(sources)
    gate = subprocess.run([sys.executable,'tools/repository/check_repository.py','--worktree'], cwd=ROOT,
        capture_output=True, encoding='utf-8')
    (RUN / 'logs').mkdir()
    (RUN / 'logs/repository-gate.log').write_text(gate.stdout+gate.stderr, encoding='utf-8')
    assert gate.returncode==0, gate.stdout+gate.stderr
    audit = dict(status='passed_with_execution_and_auditory_gaps', protected_count=len(protected),
        sealed_probe_refs_checked=len(sealed['files']+sealed['documents']+sealed['entries']),
        reply_count=1, individual_labels_added=0, reviewed_words=15, review_rows=90,
        selected_next_words=sorted(selected), next_plan_only=True, new_waveforms=0,
        agent_heard=False, measurement_validated=False, script=ref(Path(__file__)), gate=gate.stdout.strip())
    save(RUN / 'evaluation/audit.json', audit)
    save(REPORT / (NAME + '-audit.json'), audit)
    save(RUN / 'completion-manifest.json', dict(status=audit['status'],
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in sorted(REPORT.glob(NAME+'*'))], entries=[ref(ROOT/n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'], counts=counts, actions=[(a['word'],a['additive_UI']) for a in actions], gate=audit['gate']), ensure_ascii=False))


if __name__=='__main__':
    main()
