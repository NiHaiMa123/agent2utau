"""Append J technical delivery, keep all negative evidence, seal finite execution."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, ref, check
from lastpage_own_li_entry_pitch_20261013 import RUN, F, runtime
from agent2utau.knowledge import collect_context, validate_context

REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'own-li-entry-pitch-probe-20261013'
KNOW = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
INDEX = 'table2-entry-pitch-delivery-index-20261013'


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
    assert obs['actual_F0_calls'] == 2 and obs['reused_F_F0_array_bindings'] == 6 and len(obs['windows']) == 84
    outputs = pack['outputs']
    check(list(outputs.values()))
    words, phases = [], []
    for w in obs['windows']:
        if w['role'] == 'full_vowel':
            words.append(dict(word=w['word'], char=w['char'], context=w['context'],
                action='independent low-entry pitch' if w['word'] == 277 else 'no manual change',
                vowel_RMS_change_db=w['J_minus_F']['level_ratio_db'],
                FCPE_abs_cents_p50=w['J_minus_F']['F0']['FCPE']['abs_cents_p50'],
                RMVPE_abs_cents_p50=w['J_minus_F']['F0']['RMVPE']['abs_cents_p50'],
                auditory_status='pending' if w['context'] == 28 else 'real phone PCM held; no new acceptance'))
        if w['role'].startswith('li_'):
            phases.append(dict(phase=w['role'], start_s=w['interval_s'][0], end_s=w['interval_s'][1],
                F_RMS_dbfs=w['variants']['F']['level']['dbfs'], J_RMS_dbfs=w['variants']['J']['level']['dbfs'],
                J_minus_F_db=w['J_minus_F']['level_ratio_db'],
                F_tension_median=w['variants']['F']['final_features']['tension']['median'],
                J_tension_median=w['variants']['J']['final_features']['tension']['median'], auditory_force='unknown'))
    assert len(words) == 15 and len(phases) == 7
    csv_write(REPORT / (NAME + '-words.csv'), words)
    csv_write(REPORT / (NAME + '-stages.csv'), phases)
    junit = ROOT / 'runs/test-results/lastpage-own-li-entry-pitch-20261013/junit.xml'
    suites = ET.parse(junit).getroot()
    tests = sum(int(s.get('tests', '0')) for s in suites.iter('testsuite'))
    assert tests > 0 and all(int(s.get('failures', '0')) == int(s.get('errors', '0')) == 0 for s in suites.iter('testsuite'))
    table1 = ['PER:S1', 'EVT:L2', 'ACO:L1', 'PARAM:C03.01']
    supplement = dict(record_id='RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01', status='rendered_checked_pending_human_listening',
        comparison='J-F', intervention='one own li277 absolute-pitch low entry via PITD, fixed voice/manual controls/DYN0',
        table1_refs=table1, protocol=ref(RUN / 'design/protocol.json'), knowledge_receipt=ref(RUN / 'evaluation/knowledge_receipt.json'),
        target_word=277, affected_context=28, control_context=29, independent_affected_contexts=1, review_words=list(range(270, 285)),
        changed_native_pitch_grid_points=gates['native']['rows'][0]['changed_pitch_grid_points'],
        changed_model_pitch_frames=gates['native']['rows'][0]['changed_pitch_model_frames'],
        max_native_pitch_delta_cents=gates['native']['rows'][0]['max_final_pitch_delta_cents'],
        native_target_max_error_cents=gates['native']['native_target_max_error_cents'],
        variance_changed_only_pitch=True, new_predictions_rebuilt=True, manual_controls_exact_F=True, repeat_exact=True, feature_clipping=0,
        new_variance_calls=2, new_acoustic_vocoder_waveforms=2, native_cached_technical_contexts=2,
        native_internal_neural_inference_count='unknown: cached technical path not instrumented',
        new_F0_calls=2, reused_F_F0_bindings=6, word_rows=words, phase_rows=phases, outputs=outputs,
        response_limit='Source-supported entry pitch is a finite hypothesis; both input F0 paths and all predicted features change. Perceptual force/solidity and low-entry acceptability pending; prior negatives retained.',
        new_feedback_count=0, adoption=False, agent_heard=False, measurement_validated=False, general_rule_validated=False)
    save(RUN / 'evaluation/table2-supplement.json', supplement)
    report = dict(status='J_entry_pitch_delivered_pending_listening', table2_supplement=supplement, table1_refs=table1,
        execution=exe, delivery=pack, phase_rows=phases, word_rows=words,
        checks={k: ref(RUN / f'evaluation/{k}-independent-check.json') for k in gates}, observations=ref(RUN / 'observations/results.json'),
        runtime_resources=len(load(RUN / 'native-inputs/runtime.json')), knowledge_ID_count=len(plan['knowledge_context']['decisions']),
        contracts_passed=tests, test_report=ref(junit),
        same_input_native_retry=ref(RUN / 'evaluation/native-retry.json') if (RUN / 'evaluation/native-retry.json').exists() else None,
        checker_stage_correction=dict(initial_checker=ref(RUN / 'logs/native-checker-initial.py.txt'),
            failure_note=ref(RUN / 'logs/native-checker-first-failure.txt'),
            correction='Authored F/J notes exact by restoration; loaded F/J notes exact. Do not compare pre-native float64 points against native rounded points.',
            loaded_F=ref(F / 'native-inputs/F-roundtrip.ustx'), loaded_J=ref(RUN / 'native-inputs/J-roundtrip.ustx'),
            score_model_inputs_changed_for_repair=False, tolerance_widened=False),
        agent_heard=False, adoption=False, measurement_validated=False, general_rule_validated=False)
    save(REPORT / (NAME + '.json'), report)
    phase_table = '|阶段|F RMS dBFS|J RMS dBFS|J−F dB|\n|---|---:|---:|---:|\n'
    for p in phases:
        phase_table += f"|{p['phase']}|{p['F_RMS_dbfs']:.3f}|{p['J_RMS_dbfs']:.3f}|{p['J_minus_F_db']:+.3f}|\n"
    li = next(w for w in words if w['word'] == 277)
    retry_note='原生初始化失败/同输入重试记录保留。' if (RUN/'evaluation/native-retry.json').exists() else '本轮原生执行未需重试。'
    md = f"""# 最后一页：里低位进入音高J

2026-10-13。用户“继续”执行冻结J，基于既有原曲GAME/双F0候选及11系列/15字条件复核，实际消费19ID知识。G/H/I阴性、E挤细尖、F聚合改善/工作基底边界保持。此为自己的有限音高路径试验，不搬作者曲线、不加发声剂量，Skill/原歌/音频/作者原件不改。

## 唯一写入因素与完整依赖

保持notes.tone/tuning/positions/durations/note.pitch/vibrato、所有phone符号/时钟/CLR、Bright40/Cute60以及TENC0/BREC0/VOIC100/SHFC0/DYN0。仅context28里/l准备PITD原5tick grid的ys改变，按独立Hermite目标-minus-before-PITD整数编码。212.877291667s以自己F边界值和切线接入，212.957291667s到66、维持90ms，213.140s到68，213.200s接回F自身主体；后68→66与下字保持原目标。notes.tone未修改，因此不声称隔离phone选择用tone或谱面音符已修正；实际最后80ms l也改变pitch，咬字/体到里衔接是试听检查项。

独立多项式、完整谱面恢复等式和native读回通过：{supplement['changed_native_pitch_grid_points']}个5tick点改变，最大相对F {supplement['max_native_pitch_delta_cents']:.6f}c，目标点最大误差{supplement['native_target_max_error_cents']:.9f}c。实际写点与帧支撑/相邻插值段在native检查JSON列明，不以请求窗口掩盖采样边缘。模型pitch有{supplement['changed_model_pitch_frames']}帧改变；Core SampleCurve实际float32差分→double插值→double0.01缩放再float32、频率换算独立精确重建F/J两条输入路径。

variance输入只pitch改变，两阶段speaker/音素/其它固定输入精确F；三新预测完整重算，再用零人工增量生成新最终输入，acoustic F0/vocoder F0都来自新音高，不是保留旧预测或vocoder F0的SHFC反事实。context28 J/J_repeat两套新variance/acoustic/vocoder，固定11/101，输入/预测/mel/raw全部重复精确，feature clipping0。context29封存F贡献复用，2原生缓存技术上下文另列；原生内部神经执行次数未计数。{retry_note}

初始检查器误将写入前的note.pitch高精度值与原生读回舍入值直接比较，失败源码/说明保留；纠正为写入F/J恢复等式及加载F/J完整notes逐项精确检查。未更改谱面/模型输入或放宽容差，before-PITD亦精确F。

## 有限观测与交付

{phase_table}

整里J−F RMS为{li['vowel_RMS_change_db']:+.6f}dB，音高/预测/谱与电平响应均是有限代理，不证明更实、更强或自然度通过。84窗覆盖两句15字/辅音及7个里/l阶段，2新双F0检测与6旧F绑定明确复用。源F0候选不是实测目标真值，新输出F0也不因输入精确而自动固定或接受。

完整研究人声245.577秒按34贡献组装，仅替换context28贡献，DYN0/gain1、固定1.5、44100Hz mono PCM24，峰值{pack['peak']:.6f}，无归一化/压缩/BGM/文件满幅削波。F原全PCM重建、逆序拼接、量化和预览通过；context29独立贡献/真实音素/看及抱C/贡献外PCM精确。原89ms共享padding有{pack['overlap']['shared_padding_changed_samples']}样本变化，范围{pack['overlap']['shared_change_s']}，未越真实音素边界；模型上下文也可影响context28邻字，不把人工输入支撑等同波形支撑。

- [J新版两句](../../../{outputs['candidate_preview']['path']})、[F工作基底](../../../{outputs['original_preview']['path']})：8.6秒，里3.56–4.19秒，l准备约3.48秒开始。
- [白烁单独参考](../../../{outputs['author_reference']['path']})：既有当前1.65c fresh A，只作描述比较，音乐/时钟不同。
- [完整研究J工程](../../../{outputs['candidate_project']['path']})、[完整研究J人声](../../../{outputs['candidate_full']['path']})：未采用为原发布歌。

{tests}项相关本机契约及native/fresh/84窗/PCM门禁通过，47资源/保护SHA保持。新J响应追加表2当前索引，OBS条件复核保留、近12系列/37行，旧G/H/I否定及当时receipt不改。下步只接J相对F的里实感、发力发展、新低入口音乐是否合适及咬字/挤尖/破音副作用，不自动改音符tone/加发声通道/扫候选。Agent未听、新反馈0、measurement_validated=false、通用规律0，单Agent/CI仅手动。

[15字CSV]({NAME}-words.csv)、[阶段CSV]({NAME}-stages.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。
"""
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')
    registry = KNOW / 'active-knowledge-sources.json'
    config = load(registry)
    old_path = ROOT / config['response_indices'][0]
    old_index = load(old_path)
    idx = copy.deepcopy(old_index)
    assert len(idx['rows']) == 36 and idx['recent_response_series_count'] == 11
    idx['rows'].append(dict(id=supplement['record_id'], kind='recent_response_series', source=ref(REPORT / (NAME + '.json')),
        feedback_sources=[], table1_refs=table1, source_record=supplement, scope='J entry pitch technical delivery, auditory feedback pending; H/G negatives retained'))
    idx.update(recent_response_series_count=12, status='current_index_J_entry_pitch_pending_with_G_H_I_negatives_retained',
               prior_index=ref(old_path), generator=ref(Path(__file__)))
    save(KNOW / (INDEX + '.json'), idx)
    csvrows = [dict(id=r['id'], kind=r['kind'], source_path=r['source']['path'], source_sha256=r['source']['sha256'],
        feedback_paths='|'.join(p['path'] for p in r['feedback_sources']), table1_refs='|'.join(r['table1_refs']), scope=r['scope']) for r in idx['rows']]
    csv_write(KNOW / (INDEX + '.csv'), csvrows)
    imd = '# 表2当前制作索引：J进入音高交付\n\n37行、近12系列，原记录与G/H/I否定保持；J待评。重复/窗口/索引行不是独立样本数。\n\n|ID|技术/原记录|追加反馈|\n|---|---|---|\n'
    for r in idx['rows']:
        fb = '、'.join(f"[{Path(p['path']).stem}](../../../{p['path']})" for p in r['feedback_sources']) or '见原包；J待评'
        imd += f"|{r['id']}|[{Path(r['source']['path']).stem}](../../../{r['source']['path']})|{fb}|\n"
    imd += f'\n[CSV]({INDEX}.csv)、[JSON]({INDEX}.json)。局部/阴性/unknown保留，不升级通用规则。\n'
    (KNOW / (INDEX + '.md')).write_text(imd, encoding='utf-8', newline='\n')
    config['response_indices'] = [ref(KNOW / (INDEX + '.json'))['path']]
    registry.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    packet = collect_context(['PER:S1', 'EVT:L2'], ['PARAM:C03.01'], [supplement['record_id'],
        'RESP:LASTPAGE-OWN-LI-DYN-LAYERS-01', 'RESP:LASTPAGE-OWN-LI-VOIC-STAGES-01', 'RESP:LASTPAGE-OWN-LI-TENC-STAGES-01'])
    decisions = [dict(id=r['id'], decision='keep_unknown' if r['id'] == supplement['record_id'] else 'use',
        reason='J listening pending; G rejection/H named insufficiency/I no meaningful difference preserved', condition_match='current F/li entry pitch context',
        limitations='Digital/model input response is not perceived force or general recipe') for r in packet['records']]
    save(RUN / 'evaluation/new_J_catalogue_context.json', packet)
    save(RUN / 'evaluation/new_J_catalogue_receipt.json', validate_context(packet, decisions))
    status = ('当前状态J_entry_pitch_delivered_pending_listening：2026-10-13用户“继续”执行J，19ID知识消费11系列与OBS条件复核/旧阴性；'
        f"F基底仅里/l准备独立低66进入再到68并接回原主体，notes.tone/完整音素/两阶段speaker/人工发声/DYN0保持。{supplement['changed_native_pitch_grid_points']}个5tick点/{supplement['changed_model_pitch_frames']}模型pitch帧、native目标误差{supplement['native_target_max_error_cents']:.6f}c，采样边缘明确。"
        'variance只pitch变、三预测完整重建，acoustic/vocoder F0独立精确重建；2新seeded重复精确/裁剪0，2原生技术上下文另列。'
        f"84窗/2新F0+6旧F绑定、34贡献PCM通过，里RMS相对{li['vowel_RMS_change_db']:+.4f}dB仅代理非实感/发力通过；{tests}契约/47资源SHA保持。"
        f"第二句真实音素/看与抱C/贡献外精确，共享padding{pack['overlap']['shared_padding_changed_samples']}样本变化范围列明；J/F/作者分开交付、近12系列/37索引，J待评未采用。"
        '原歌音频Skill/作者/旧阴性/unknown保持，Agent未听/通用规律0，单Agent/CI仅手动。')
    for name in ENTRIES:
        p = ROOT / name
        lines = p.read_text(encoding='utf-8').splitlines()
        ix = [i for i, l in enumerate(lines) if '当前状态li_conditions_reviewed_entry_pitch_J_design_frozen：' in l]
        assert len(ix) == 1, name
        rel = 'docs/reports/lastpage/' + NAME + '.md'
        if '/' in name:
            rel = ('../../' if name.startswith('research/') else '../../../') + rel
        lines[ix[0]] = ('- ' if lines[ix[0]].startswith('- ') else '') + status + f' 见[里进入音高J]({rel})。'
        if name == 'plan.md':
            for i, l in enumerate(lines):
                if l.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    lines[i] = '下一工作进入逐首更新，先《最后一页》：J低位进入音高已技术检查并交付，三预测与acoustic/vocoder F0完整重建；下一步只接J相对F的里实感/发力与低入口音乐、咬字/衔接/挤尖破音反馈。保留G/H/I阴性；不自动改notes.tone/加发声通道或扩大条件，J未采用。'
        if name == 'docs/knowledge/acoustic-manifestations-20261009/README.md':
            for i, l in enumerate(lines):
                if l.startswith('制作使用[当前表2索引]'):
                    lines[i] = f'制作使用[当前表2索引]({INDEX}.md)与[显式来源目录](active-knowledge-sources.json)，知识接入见[指南](../../guides/knowledge-use-in-production.md)。近12系列/37行包含J待评、OBS复核及G/H/I否定；旧字段/SHA保持，不是通用规则。'
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
        'lastpage_own_li_entry_pitch_20261013.py', 'check_lastpage_own_li_entry_pitch_20261013.py',
        'package_lastpage_own_li_entry_pitch_20261013.py', 'observe_lastpage_own_li_entry_pitch_20261013.py',
        'check_lastpage_own_li_entry_pitch_delivery_20261013.py', Path(__file__).name]]
    audit = dict(status='passed_with_explicit_entry_pitch_phonation_perception_gaps', scripts=scripts, contracts_passed=tests, contract_report=ref(junit),
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
