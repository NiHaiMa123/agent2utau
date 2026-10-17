"""Append I technical delivery, keep all negative evidence, seal finite execution."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, check
from lastpage_own_li_tenc_stages_20261012 import RUN, F, runtime
from agent2utau.knowledge import collect_context, validate_context

REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'own-li-TENC-stages-probe-20261012'
KNOW = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
INDEX = 'table2-TENC-delivery-index-20261012'


def csv_write(path, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    assert not (RUN / 'completion-manifest.json').exists() and not (REPORT / (NAME + '.json')).exists()
    gates = {k: load(RUN / f'evaluation/{k}-independent-check.json') for k in ['native', 'fresh', 'delivery']}
    assert all(g['status'] == 'passed' for g in gates.values())
    for g in gates.values():
        check([g['checker']])
    runtime()
    plan = load(RUN / 'design/protocol.json')
    exe = load(RUN / 'fresh/execution.json')
    pack = load(RUN / 'evaluation/delivery-check.json')
    obs = load(RUN / 'observations/results.json')
    assert exe['variance_calls'] == exe['acoustic_vocoder_waveforms'] == 2
    assert not any(gates['fresh']['rows'][0]['feature_clipping'].values())
    assert obs['actual_F0_calls'] == 2 and obs['reused_F_F0_array_bindings'] == 6 and len(obs['windows']) == 82
    outputs = pack['outputs']
    check(list(outputs.values()))
    words, phases = [], []
    for w in obs['windows']:
        if w['role'] == 'full_vowel':
            words.append(dict(word=w['word'], char=w['char'], context=w['context'],
                action='TENC0→10→4→0' if w['word'] == 277 else 'no manual change',
                vowel_RMS_change_db=w['I_minus_F']['level_ratio_db'],
                FCPE_abs_cents_p50=w['I_minus_F']['F0']['FCPE']['abs_cents_p50'],
                RMVPE_abs_cents_p50=w['I_minus_F']['F0']['RMVPE']['abs_cents_p50'],
                auditory_status='pending' if w['context'] == 28 else 'real phone PCM held; no new acceptance'))
        if w['role'].startswith('li_'):
            phases.append(dict(phase=w['role'], start_s=w['interval_s'][0], end_s=w['interval_s'][1],
                F_RMS_dbfs=w['variants']['F']['level']['dbfs'], I_RMS_dbfs=w['variants']['I']['level']['dbfs'],
                I_minus_F_db=w['I_minus_F']['level_ratio_db'],
                F_tension_median=w['variants']['F']['final_features']['tension']['median'],
                I_tension_median=w['variants']['I']['final_features']['tension']['median'], auditory_force='unknown'))
    assert len(words) == 15 and len(phases) == 5
    csv_write(REPORT / (NAME + '-words.csv'), words)
    csv_write(REPORT / (NAME + '-stages.csv'), phases)
    junit = ROOT / 'runs/test-results/lastpage-own-li-tenc-stages-20261012/junit.xml'
    suites = ET.parse(junit).getroot()
    tests = sum(int(s.get('tests', '0')) for s in suites.iter('testsuite'))
    assert tests > 0 and all(int(s.get('failures', '0')) == int(s.get('errors', '0')) == 0 for s in suites.iter('testsuite'))
    table1 = ['PER:S1', 'EVT:L2', 'ACO:L1', 'PARAM:C13.01']
    supplement = dict(record_id='RESP:LASTPAGE-OWN-LI-TENC-STAGES-01', status='rendered_checked_pending_human_listening',
        comparison='I-F', intervention='one li277 TENC gesture0→10→4→0 at own music/native vowel anchors, DYN0',
        table1_refs=table1, protocol=ref(RUN / 'design/protocol.json'), knowledge_receipt=ref(RUN / 'evaluation/knowledge_receipt.json'),
        target_word=277, affected_context=28, control_context=29, independent_affected_contexts=1, review_words=list(range(270, 285)),
        changed_native_tension_frames=gates['native']['rows'][0]['changed_tension_frames'],
        max_feature_delta=gates['native']['rows'][0]['max_TENC_model_increment'],
        variance_inputs_predictions_exact_F=True, only_final_tension_changed=True, repeat_exact=True, feature_clipping=0,
        new_variance_calls=2, new_acoustic_vocoder_waveforms=2, native_cached_technical_contexts=2,
        native_internal_neural_inference_count='unknown: cached technical path not instrumented',
        new_F0_calls=2, reused_F_F0_bindings=6, word_rows=words, phase_rows=phases, outputs=outputs,
        response_limit='Model tension and digital energy changes do not establish perceived force/solidity or physiological support. E adverse/G negative/H named insufficiency retained.',
        new_feedback_count=0, adoption=False, agent_heard=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/table2-supplement.json', supplement)
    report = dict(status='I_TENC_delivered_pending_listening', table2_supplement=supplement, table1_refs=table1,
        execution=exe, delivery=pack, phase_rows=phases, word_rows=words,
        checks={k: ref(RUN / f'evaluation/{k}-independent-check.json') for k in gates}, observations=ref(RUN / 'observations/results.json'),
        runtime_resources=len(load(RUN / 'native-inputs/runtime.json')), knowledge_ID_count=len(plan['knowledge_context']['decisions']),
        contracts_passed=tests, test_report=ref(junit),
        same_input_native_retry=ref(RUN / 'evaluation/native-retry.json'),
        agent_heard=False, adoption=False, measurement_validated=False, general_rule_validated=False)
    save(REPORT / (NAME + '.json'), report)
    phase_table = '|阶段|F RMS dBFS|I RMS dBFS|I−F dB|\n|---|---:|---:|---:|\n'
    for p in phases:
        phase_table += f"|{p['phase']}|{p['F_RMS_dbfs']:.3f}|{p['I_RMS_dbfs']:.3f}|{p['I_minus_F_db']:+.3f}|\n"
    li = next(w for w in words if w['word'] == 277)
    md = f'''# 最后一页：里TENC建立与回收I

2026-10-12。用户“下一步”授权执行已冻结I。此前H“里字不够实，强度也不够大”与G“不行”保留并实际进入11ID知识决策；F仍为工作比较基底，非整曲验收。沿用singing-expression-editor方法，Skill与旧原歌/音频/作者原件/封存实验均不改。

## 单因素执行

F的Bright40/Cute60、全部音高/音符/音素时钟/CLR、BREC0/VOIC100/SHFC0/DYN0保持，仅里元音212.9572917–213.5854167s按自己的音乐节点建立TENC0→+10→+4→0；入口与主音到达前保持，主体锚点展开，自己的回收/降音阶段承接，再在元音结束恢复。smoothstep零切线、原5tick整数采样，非作者节点或曲线复制。

原生独立重建确认{supplement['changed_native_tension_frames']}帧张力增量，最大{supplement['max_feature_delta']:.9f}模型单位；本机Core IL为sampledUI/20f，独立声线两阶段、完整pitch/phones/variance输入与三预测均精确F，只有最终张力输入改变，BREC/VOIC与vocoder F0保持。实际非零采样仅里元音，声母/邻字人工输入未增加；声学模型上下文仍可能影响邻字波形，不能将输入支撑当PCM支撑。

context28 I/I_repeat两套新的variance/acoustic/vocoder波形，固定11/101，重复全部输入/预测/mel/raw精确，特征裁剪0。context29 fresh贡献复用F，2句原生缓存技术渲染另列，原生内部神经推理次数未计数。2次新双F0检测与6个旧F数组绑定复用，不等于新增独立条件。82窗覆盖15字/辅音/两句及里5音乐阶段。

{phase_table}

整里RMS I−F为{li['vowel_RMS_change_db']:+.6f}dB；表中变化是数字能量与模型条件响应，不是听觉力量或实感改善。TENC正增量也不能证明生理发力更强。此前E前顶/挤细/尖、F及作者C组合中和改善的反例保留，本批专门试听这些副作用，不自动加剂量、叠加DYN或采用。

## 交付和验收边界

研究全曲245.577秒按34贡献重建、context28替换；原F全PCM重建、逆序拼接与量化/预览通过，固定1.5、44100Hz mono PCM24，峰值{pack['peak']:.6f}，无文件满幅削波/归一化/压缩/BGM。context29独立贡献及真实音素/看PCM精确，原89ms共享padding有{pack['overlap']['shared_padding_changed_samples']}样本变化，具体范围{pack['overlap']['shared_change_s']}，未越真实音素边界；其它32贡献/抱C及context28贡献外PCM保持。

- [I新版两句](../../../{outputs['candidate_preview']['path']})、[F工作基底](../../../{outputs['original_preview']['path']})：8.6秒，里约3.56–4.19秒。
- [白烁单独参考](../../../{outputs['author_reference']['path']})：既有当前1.65c fresh A，音乐/时钟不同，仅描述比较。
- [完整研究I工程](../../../{outputs['candidate_project']['path']})、[完整研究I人声](../../../{outputs['candidate_full']['path']})：研究副本，未采用为发布歌。

{tests}项本机相关契约与原生/重复/82窗/PCM独立检查通过，保护输入及47资源SHA保持。首次原生probe在ONNX声码器初始化发生0xC0000005，同工程/同输入重试通过，原失败日志与重试另列保存，未换种子/参数/预算。表2新I技术记录与当前索引追加，旧H/G否定仍可检索，旧知识receipt保留当时目录快照。下步只接本批里实感、力量展开/回收及前顶挤细尖、破音/咬字反馈，不自动扫剂量或扩大通道。Agent未听，新反馈0、measurement_validated=false、通用规律0，单Agent、CI仅手动。

[15字CSV]({NAME}-words.csv)、[阶段CSV]({NAME}-stages.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
'''
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')
    registry = KNOW / 'active-knowledge-sources.json'
    config = load(registry)
    old_path = ROOT / config['response_indices'][0]
    old_index = load(old_path)
    idx = copy.deepcopy(old_index)
    assert len(idx['rows']) == 34 and idx['recent_response_series_count'] == 10
    idx['rows'].append(dict(id=supplement['record_id'], kind='recent_response_series', source=ref(REPORT / (NAME + '.json')),
        feedback_sources=[], table1_refs=table1, source_record=supplement, scope='I TENC technical delivery, auditory feedback pending; H/G negatives retained'))
    idx.update(recent_response_series_count=11, status='current_index_I_TENC_pending_with_H_G_negatives_retained',
               prior_index=ref(old_path), generator=ref(Path(__file__)))
    save(KNOW / (INDEX + '.json'), idx)
    csvrows = [dict(id=r['id'], kind=r['kind'], source_path=r['source']['path'], source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']), table1_refs='|'.join(r['table1_refs']), scope=r['scope']) for r in idx['rows']]
    csv_write(KNOW / (INDEX + '.csv'), csvrows)
    imd = '# 表2当前制作索引：I TENC交付\n\n35行、近11系列，原记录与H/G否定保持；I待评。重复/窗口/索引行不是独立样本数。\n\n|ID|技术/原记录|追加反馈|\n|---|---|---|\n'
    for r in idx['rows']:
        fb = '、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包；I待评'
        imd += f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd += f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。局部/阴性/unknown保留，不升级通用规则。\n'
    (KNOW / (INDEX + '.md')).write_text(imd, encoding='utf-8', newline='\n')
    config['response_indices'] = [ref(KNOW / (INDEX + '.json'))['path']]
    registry.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    packet = collect_context(['PER:S1', 'EVT:L2'], ['PARAM:C13.01'], [supplement['record_id'],
        'RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01', 'RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01'])
    decisions = [dict(id=r['id'], decision='keep_unknown' if r['id'] == supplement['record_id'] else 'use',
        reason='I listening pending; H named insufficiency/G rejection preserved', condition_match='current F/li finite TENC context',
        limitations='Digital/model input response is not perceived force or general recipe') for r in packet['records']]
    save(RUN / 'evaluation/new_I_catalogue_context.json', packet)
    save(RUN / 'evaluation/new_I_catalogue_receipt.json', validate_context(packet, decisions))
    status = ('当前状态I_TENC_delivered_pending_listening：2026-10-12用户“下一步”执行I，实际消费11ID知识及H里两项不足/G否定、E/C反例；'
        'F/DYN0基底仅里TENC0→10→4→0，原生采样/单位/支撑、两阶段speaker/音乐时钟/variance输入预测精确F，只有final tension改变。'
        f"{supplement['changed_native_tension_frames']}帧/最大{supplement['max_feature_delta']:.6f}模型增量，2新seeded波形重复精确/裁剪0，2原生缓存技术上下文另列。"
        f"82窗/2新F0+6旧F绑定与34贡献PCM通过，里RMS相对{li['vowel_RMS_change_db']:+.4f}dB仅代理、实感力量与挤尖待听。"
        f"{tests}本机契约/47资源SHA通过，第二句真实音素/看及抱C/贡献外精确，共享padding{pack['overlap']['shared_padding_changed_samples']}样本变化范围列明。"
        'I/F/作者参考固定1.5分开交付，近11系列/35索引，I待评未采用；原歌音频Skill/作者/旧阴性/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p = ROOT / name
        lines = p.read_text(encoding='utf-8').splitlines()
        ix = [i for i, l in enumerate(lines) if '当前状态H_named_feedback_closed_TENC_design_frozen：' in l]
        assert len(ix) == 1, name
        rel = 'docs/reports/lastpage/' + NAME + '.md'
        if '/' in name:
            rel = ('../../' if name.startswith('research/') else '../../../') + rel
        lines[ix[0]] = ('- ' if lines[ix[0]].startswith('- ') else '') + status + f' 见[里TENC阶段I]({rel})。'
        if name == 'plan.md':
            for i, l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i] = '下一工作进入逐首更新，先《最后一页》：I里TENC单因素已技术检查并交付；下一步只接I相对F的实感/发力建立回收及前顶挤细尖、破音咬字反馈。H里两项不足/G否定进入实际知识决策并保持；不自动加剂量/叠加DYN或扩大条件，I未采用。'
        if name == 'docs/knowledge/acoustic-manifestations-20261009/README.md':
            for i, l in enumerate(lines):
                if l.startswith('制作使用[当前表2索引]'):
                    lines[i] = f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近11系列包含I待评及H/G否定；旧字段/SHA保持，不是通用规则。'
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    runtime()
    for r in old_index['rows']:
        assert r == next(q for q in idx['rows'] if q['id'] == r['id'])
    with (KNOW / (INDEX + '.csv')).open(encoding='utf-8-sig', newline='') as f:
        assert list(csv.DictReader(f)) == [{k: str(v) for k, v in r.items()} for r in csvrows]
    gate = subprocess.run([sys.executable, 'tools/repository/check_repository.py', '--worktree'], cwd=ROOT, capture_output=True, encoding='utf-8')
    (RUN / 'logs/repository-gate.log').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    scripts = [ref(ROOT / 'research/table2-confirmation' / n) for n in [
        'lastpage_own_li_tenc_stages_20261012.py', 'check_lastpage_own_li_tenc_stages_20261012.py',
        'package_lastpage_own_li_tenc_stages_20261012.py', 'observe_lastpage_own_li_tenc_stages_20261012.py',
        'check_lastpage_own_li_tenc_delivery_20261012.py', Path(__file__).name]]
    audit = dict(status='passed_with_explicit_TENC_phonation_perception_gaps', scripts=scripts, contracts_passed=tests, contract_report=ref(junit),
        protected_references=len(load(RUN / 'protected-before.json')), runtime_original_resources=47,
        new_variance_calls=2, new_acoustic_vocoder_waveforms=2, native_cached_technical_contexts=2,
        new_F0_calls=2, reused_F_F0_bindings=6, actual_new_feedback=0, gate=gate.stdout.strip(),
        current_index=ref(KNOW / (INDEX + '.json')), agent_heard=False, adoption=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/audit.json', audit)
    save(REPORT / (NAME + '-audit.json'), audit)
    docs = [ref(p) for p in sorted(REPORT.glob(NAME + '*'))] + [ref(p) for p in sorted(KNOW.glob(INDEX + '*'))] + [ref(registry)]
    save(RUN / 'completion-manifest.json', dict(status=report['status'], files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
                                               documents=docs, entries=[ref(ROOT / n) for n in ENTRIES]))
    print(json.dumps(dict(status=report['status'], tests=tests, preview=outputs['candidate_preview'], phase_rows=phases, gate=audit['gate']), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
