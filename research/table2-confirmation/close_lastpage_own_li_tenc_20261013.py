"""Append I/F listening feedback without new synthesis or dose escalation."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, check
from agent2utau.knowledge import collect_context, validate_context, check_plan_knowledge

PRIOR = ROOT / 'runs/experiments/lastpage-own-li-tenc-stages-20261012'
RUN = ROOT / 'runs/research/lastpage-own-li-TENC-feedback-20261013'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'own-li-TENC-feedback-20261013'
KNOW = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
INDEX = 'table2-TENC-feedback-index-20261013'
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
    plan = load(PRIOR / 'design/protocol.json')
    _, receipt = check_plan_knowledge(plan, PRIOR / 'design/protocol.json')
    assert receipt == load(PRIOR / 'evaluation/knowledge_receipt.json')
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
        reason='Explicit active catalogue pointer maintenance; all old indices and receipts preserved',
        registry=registry_ref, preserved_original_bytes=ref(RUN / 'before' / registry_ref['path'])))
    media = load(PRIOR / 'evaluation/delivery-check.json')['outputs']
    feedback = dict(verbatim='和f没什么区别', date='2026-10-13', submissions=1,
        response_record='RESP:LASTPAGE-OWN-LI-TENC-STAGES-01',
        candidate=media['candidate_preview'], baseline=media['original_preview'], author_reference=media['author_reference'],
        referent='I inferred from preceding labelled I/F/author delivery; F comparator explicitly named',
        comparison='I-F', finding='No meaningful perceived difference reported at the current finite TENC gesture',
        target_word=277, target_word_is_experiment_scope_not_new_user_named_label=True,
        precise_word_subword_location_dimension_magnitude='unknown: no word, time or dimension specified',
        new_individual_word_labels=0, solidity_strength_squeezing_sharpness_break_articulation='unknown: not individually assessed in this reply',
        improvement_supported=False, adoption=False, baseline_status='F retained as improved working comparator, not full-song acceptance',
        numerical_or_waveform_equality_claim=False, all_TENC_ineffective=False,
        dose_escalation=False, agent_heard=False, measurement_validated=False, general_rule_validated=False)
    check([feedback[k] for k in ['candidate', 'baseline', 'author_reference']])
    save(RUN / 'feedback/feedback.json', feedback)
    prior_report = load(REPORT / 'own-li-TENC-stages-probe-20261012.json')
    phases = prior_report['phase_rows']
    li = next(w for w in prior_report['word_rows'] if w['word'] == 277)
    assert len(phases) == 5
    supplement = dict(record_id=feedback['response_record'], append_only_feedback=True, feedback=feedback,
        prior_report=ref(REPORT / 'own-li-TENC-stages-probe-20261012.json'),
        table1_refs=prior_report['table1_refs'], measured_failure_cause='unknown',
        adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/table2-supplement.json', supplement)
    report = dict(status='I_feedback_closed_no_meaningful_difference', feedback=feedback, table2_supplement=supplement,
        prior_phase_rows=phases, prior_li_word_row=li, old_receipt_exact=True,
        next_boundary='No automatic TENC escalation, new combined controls or new synthesis; review existing conditional evidence before any next frozen candidate',
        unresolved_goal='Desired li solidity and strength development remain unconfirmed; F is a working comparator only',
        new_models=0, new_waveforms=0, new_PCM_NPZ_reads=0, new_measurements=0,
        agent_heard=False, adoption=False, measurement_validated=False, general_rule_validated=False)
    save(REPORT / (NAME + '.json'), report)
    write_csv(REPORT / (NAME + '-prior-stages.csv'), phases)
    md = f'''# 最后一页：里TENC阶段I相对F无明显区别反馈

2026-10-13。用户原话“和f没什么区别”，计1聚合回复，F为明确比较对象，I按上轮I/F/白烁标注推定。当前有限TENC处理未获得明显可感知改善支持，I不采用，F继续作先前“更好了”的工作基底，非整曲验收。本回复没有新命名字/字内时点或实感、力量、前顶挤细尖、破音、咬字等细分评判，不补逐字标签，也不将H里明确不足覆盖成正常。

## 有限阴性与技术响应并存

此前I仅在自身里277改变42帧最终张力、最大+0.5模型单位，variance输入/预测与其余声学输入精确F；2次固定种子波形重复精确，裁剪0。5阶段输入建立回收与成声变化属于技术事实，里RMS约{li['vowel_RMS_change_db']:+.6f}dB属于电平代理，不等于力量或实感。用户“没什么区别”是本条件的感知反馈，不是波形/模型特征相同的声明，不否定全部TENC、其他声线/音区/剂量的可能作用。

本轮仅追加反馈、复核封存JSON/旧receipt和文件字节SHA，没有解码PCM/NPZ/mel/F0、复测、原生执行、模型或新合成。旧I pending技术报告、工程、音频、失败/重试日志和知识receipt保持原字节；当前索引另追加反馈来源。

## 当前研究边界

G VOIC阶段“不行”、H DYN“里字不够实，强度也不够大”、I TENC“和f没什么区别”分别保留，三项不是同维度或独立留出证据，不宣称已确定共同病因。需要的实感与发力层次仍未确认；不通过增加TENC或联动DYN/VOIC继续点对点扫剂量。下一步先复核已有条件证据与未隔离差异，再决定有依据的有限对照；此处没有冻结或执行J候选。

当前知识索引仍35行/近11系列，原source_record与来源SHA精确保持；新增I/F反馈被实际检索，并在逐ID决策中拒绝采用当前I，H/G阴性继续可读。表1定义/参数不因阴性修改或升级，measurement_validated=false、通用规律0。原歌曲/音频/Skill/作者原件及抱C/旧unknown保持，Agent未听，单Agent、CI仅手动。

[JSON]({NAME}.json)、[旧阶段CSV]({NAME}-prior-stages.csv)、[审计]({NAME}-audit.json)。
'''
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')
    config = load(REGISTRY)
    old_path = ROOT / config['response_indices'][0]
    old_index = load(old_path)
    idx = copy.deepcopy(old_index)
    assert len(idx['rows']) == 35 and idx['recent_response_series_count'] == 11
    row = next(r for r in idx['rows'] if r['id'] == feedback['response_record'])
    before_row = copy.deepcopy(row)
    assert not row['feedback_sources']
    row.update(feedback_sources=[ref(REPORT / (NAME + '.json'))], feedback_record=feedback,
               scope='I technical fields retained; appended no meaningful difference versus F, not adopted')
    assert row['source_record'] == before_row['source_record'] and row['source'] == before_row['source']
    idx.update(prior_index=ref(old_path), generator=ref(Path(__file__)), status='current_index_I_no_difference_feedback_with_H_G_negatives_retained')
    save(KNOW / (INDEX + '.json'), idx)
    csvrows = [dict(id=r['id'], kind=r['kind'], source_path=r['source']['path'], source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']), table1_refs='|'.join(r['table1_refs']), scope=r['scope']) for r in idx['rows']]
    write_csv(KNOW / (INDEX + '.csv'), csvrows)
    imd = '# 表2当前索引：I相对F没什么区别\n\n35行/近11系列保持；I/F本条件无明显可感知差别，H/G阴性与旧技术字段保持。重复/窗口/索引行不是独立样本。\n\n|ID|技术/原记录|追加反馈|\n|---|---|---|\n'
    for r in idx['rows']:
        fb = '、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包'
        imd += f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd += f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。不升级通用规律或全面测量验证。\n'
    (KNOW / (INDEX + '.md')).write_text(imd, encoding='utf-8', newline='\n')
    config['response_indices'] = [ref(KNOW / (INDEX + '.json'))['path']]
    REGISTRY.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    responses = [feedback['response_record'], 'RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01',
                 'RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01', 'RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01']
    packet = collect_context(['PER:S1', 'EVT:L2', 'ACO:L1'], ['PARAM:C13.01'], responses)
    decisions = [dict(id=r['id'], decision='reject' if r['id'] in responses[:3] else 'use',
        reason='Current finite I lacks perceived difference; H named insufficiency and G rejection retained; no dose escalation' if r['id'] in responses[:3] else 'Keep F working comparator and perception/model/level distinctions',
        condition_match='Current1.65c F/li finite VOIC/DYN/TENC responses; feedback scope differs between replies',
        limitations='No causal diagnosis, universal inefficacy or individual word labeling from aggregate I reply') for r in packet['records']]
    save(RUN / 'design/knowledge_context.json', packet)
    save(RUN / 'evaluation/knowledge_receipt.json', validate_context(packet, decisions))
    rr = {r['id']: r['record'] for r in packet['records']}
    assert rr[responses[0]]['feedback_record'] == feedback
    assert rr[responses[1]]['feedback_record']['verbatim'] == '里字不够实，强度也不够大'
    assert rr[responses[2]]['feedback_record']['verbatim'] == '不行'
    status = ('当前状态I_feedback_closed_no_meaningful_difference：2026-10-13“和f没什么区别”计1聚合回复，F明确比较对象/I按上轮标注推定，当前TENC处理未获明显可感知改善支持，I不采用。'
        '不补具体字/时点/虚实力量挤尖破音标签、不声称波形相同或TENC全无效；F仍改善工作基底、实感及发力层次目标未确认。'
        '35索引/近11系列追加反馈且实际知识决策拒绝I、保留H里两项不足/G否定；旧I技术记录/音频/receipt原字节保持。'
        '不自动加TENC剂量或联动DYN/VOIC，下一步先已有条件证据与未隔离差异复核，未冻结J。'
        '本轮新PCM/NPZ读取/复测/原生/模型/音频0，原歌音频Skill/作者/旧阴性/抱C/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p = ROOT / name
        lines = p.read_text(encoding='utf-8').splitlines()
        ix = [i for i, l in enumerate(lines) if '当前状态I_TENC_delivered_pending_listening：' in l]
        assert len(ix) == 1, name
        rel = 'docs/reports/lastpage/' + NAME + '.md'
        if '/' in name:
            rel = ('../../' if name.startswith('research/') else '../../../') + rel
        lines[ix[0]] = ('- ' if lines[ix[0]].startswith('- ') else '') + status + f' 见[I相对F反馈]({rel})。'
        if name == 'plan.md':
            for i, l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i] = '下一工作进入逐首更新，先《最后一页》：I相对F“没什么区别”已回填表2/知识决策，I不采用，F仍工作比较基底；H里实感/强度不足与G否定保持。下一步先复核已有条件证据与未隔离差异，不自动加TENC或组合DYN/VOIC；J未冻结/执行，实感和发力层次目标仍未确认。'
        if name == 'docs/knowledge/acoustic-manifestations-20261009/README.md':
            for i, l in enumerate(lines):
                if l.startswith('制作使用[当前表2索引]'):
                    lines[i] = f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近11系列保留I/F无明显区别及H/G阴性；旧字段/SHA保持，不是通用规则。'
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    check(protected)
    for r in idx['rows']:
        check([r['source']] + r['feedback_sources'])
        if r['id'] != feedback['response_record']:
            assert r == next(q for q in old_index['rows'] if q['id'] == r['id'])
    with (KNOW / (INDEX + '.csv')).open(encoding='utf-8-sig', newline='') as f:
        assert list(csv.DictReader(f)) == [{k: str(v) for k, v in r.items()} for r in csvrows]
    gate = subprocess.run([sys.executable, 'tools/repository/check_repository.py', '--worktree'], cwd=ROOT, capture_output=True, encoding='utf-8')
    (RUN / 'logs/repository-gate.log').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    audit = dict(status='passed_with_explicit_conditional_negative_and_causal_gaps', source=ref(Path(__file__)),
        feedback_submissions=1, new_individual_word_labels=0, new_models=0, new_waveforms=0,
        new_PCM_NPZ_reads=0, protected_references=len(protected), original_I_receipt_exact=True,
        I_H_G_feedbacks_retrieved=True, current_index=ref(KNOW / (INDEX + '.json')), current_registry=ref(REGISTRY),
        CSV_and_prior_index_fields_exact=True, gate=gate.stdout.strip(), agent_heard=False,
        adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/audit.json', audit)
    save(REPORT / (NAME + '-audit.json'), audit)
    docs = [ref(p) for p in sorted(REPORT.glob(NAME + '*'))] + [ref(p) for p in sorted(KNOW.glob(INDEX + '*'))] + [ref(REGISTRY)]
    save(RUN / 'completion-manifest.json', dict(status=report['status'], files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
                                               documents=docs, entries=[ref(ROOT / n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'], feedback=feedback['verbatim'], new_waveforms=0,
        old_receipt_exact=True, negatives_retrieved=True, gate=audit['gate']), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
