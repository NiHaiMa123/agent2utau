"""Audit the whole-song baseline and assemble already sealed vocal contributions.

This is an explicit reuse delivery, not a synthesis or a new control experiment.
No historical implementation module is imported or executed.
"""
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import soundfile as sf
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'runs/lastpage_loudness_skill_v02_20261007'
ONSET = ROOT / 'runs/lastpage_shfc_onset_probe_20261008'
GUO = ROOT / 'runs/lastpage_guo_register_probe_20261008'
RUN = ROOT / 'runs/production/lastpage-accepted-baseline-20261011'
REPORT = ROOT / 'docs/reports/lastpage'
NAME = 'whole-song-baseline-review-20261011'
ENTRIES = ['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md',
           'research/table2-confirmation/README.md',
           'docs/knowledge/acoustic-manifestations-20261009/README.md']
CLOSURE = ROOT / 'runs/research/table2-listening-cycle-closure-20261011/completion-manifest.json'


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ref(p):
    return {'path': Path(p).relative_to(ROOT).as_posix(), 'sha256': sha(p)}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(x, f, ensure_ascii=False, indent=2)
        f.write('\n')


def check(rows):
    for r in rows:
        assert sha(ROOT / r['path']) == r['sha256'], r['path']


def csv_write(p, rows):
    with p.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def structural_diff(a, b, path=''):
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        out = []
        for k in sorted(a.keys() | b.keys()):
            q = path + '/' + str(k)
            out.extend([q] if k not in a or k not in b else structural_diff(a[k], b[k], q))
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [path + '/length']
        return [q for i, (x, y) in enumerate(zip(a, b))
                for q in structural_diff(x, y, path + '/' + str(i))]
    return [] if a == b else [path]


def main():
    assert not RUN.exists(), 'New run only; no overwrite or rerun.'
    assert not (REPORT / (NAME + '.json')).exists()
    closure = load(CLOSURE)
    check(closure['files'] + closure['documents'] + closure['entries'])
    prior_refs = closure['files'] + closure['documents']
    # Freeze the actual current entry bytes before changing the active status.
    RUN.mkdir(parents=True)
    for name in ENTRIES:
        p = RUN / 'before' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, p)
    protected = []
    # Rehash each local file declared by the three reused sealed runs, without
    # decoding any array, PCM, model or external author resource during audit.
    for folder in [BASE, ONSET, GUO]:
        manifest = load(folder / 'completion_manifest.json')
        protected.append(ref(folder / 'completion_manifest.json'))
        for name, expected in manifest['files'].items():
            p = Path(name)
            if p.is_relative_to(folder):
                assert sha(p) == expected, name
                protected.append(ref(p))
    for folder in ['src/agent2utau', 'bridge/OuBridge', 'skills/singing-expression-editor', 'projects/latest']:
        for p in sorted((ROOT / folder).rglob('*')):
            if p.is_file() and not any(t in p.parts for t in ['__pycache__', 'bin', 'obj']):
                protected.append(ref(p))
    protected.append(ref(ROOT / '.github/workflows/ci.yml'))
    protected = list({r['path']: r for r in protected}.values())
    save(RUN / 'evaluation/protected-before.json', protected)
    print('Preflight: sealed runs and production/Skill/project files bound.', flush=True)

    working = GUO / 'A.ustx'
    published = ROOT / 'projects/latest/lastpage_loudness_v02.ustx'
    assert sha(working) == sha(ONSET / 'C.ustx') == '45d2b34e8086ad5f12f4c701d91672b3cc12eadffda2ab9d9e405dfb2fb71816'
    assert sha(published) == 'a17d4bebdd3c5951f2b10138777a8fee8925ab5beb6bb70705342d1b6ba466af'
    a = yaml.safe_load(published.read_text(encoding='utf-8-sig'))
    c = yaml.safe_load(working.read_text(encoding='utf-8-sig'))
    differences = structural_diff(a, c)
    assert differences == ['/expressions/shfc/max', '/expressions/shfc/min', '/voice_parts/22/curves/length'], differences
    assert a['voice_parts'][22]['curves'] == c['voice_parts'][22]['curves'][:-1]
    assert c['voice_parts'][22]['curves'][-1]['abbr'] == 'shfc'
    for i in range(34):
        assert a['voice_parts'][i]['notes'] == c['voice_parts'][i]['notes']

    source = load(BASE / 'source_observations.json')
    geometry = load(BASE / 'native_word_geometry.json')
    decisions = load(BASE / 'agent_word_decisions.json')
    functions = load(BASE / 'agent_function_plans.json')
    notes = load(BASE / 'note_bindings.json')
    phones = load(BASE / 'final_phones.json')
    synth = load(BASE / 'synthesis_check.json')['phrases']
    study = load(ROOT / 'runs/lastpage_cross_condition_study_20261008/study.json')
    assert len(source['words']) == len(geometry) == len(decisions) == len(study['all_current_words']) == 318
    assert len(functions) == len(synth) == len(phones['parts']) == len(c['voice_parts']) == 34
    assert len(notes) == sum(len(p['notes']) for p in c['voice_parts']) == 412
    assert [w['word'] for w in decisions] == list(range(318))
    source_unknowns = [w['word'] for w in source['words'] if w['unknown']]
    assert source_unknowns == [106] == [w['word'] for w in decisions if w['source_unknown']]
    assert all(l['identity_verified_by_listening'] is False for l in source['lines'])
    entry_notes = {e['note'] for p in functions for e in p['entries']}
    assert entry_notes == {n['note_index'] for n in notes if n['kind'] == 'sung'}
    assert len(entry_notes) == 332
    assert len({n['note_index'] for n in notes}) == 412
    source_reuse = load(BASE / 'source_and_own_design_reuse.json')
    historical_reuse_differences = []
    current_manifest = load(BASE / 'completion_manifest.json')
    for name, expected in source_reuse['source_files'].items():
        p = BASE / name
        current = sha(p)
        assert current_manifest['files'][str(p)] == current
        if current != expected:
            historical_reuse_differences.append(dict(file=name, historical_reuse_sha256=expected,
                                                     current_sealed_v02_sha256=current))
    # This register describes files at the original copy stage, before v02
    # changed its paths, control declarations and own decisions. Require the
    # core observation bytes unchanged and bind actual v02 metadata separately.
    assert {r['file'] for r in historical_reuse_differences} == {
        'separation.json', 'fresh_center.ustx', 'agent_function_plans.json', 'agent_word_decisions.json'}
    source_bindings = [ref(BASE / name) for name in source_reuse['source_files']]
    source_bindings += [ref(BASE / n) for n in ['agent_word_decisions.json', 'whole_song_loudness_decisions.json',
                       'note_bindings.json', 'final_phones.json', 'native_function_validation.json', 'residual_gain_choices.json']]
    source_bindings += [ref(ROOT / 'runs/lastpage_cross_condition_study_20261008/study.json'), ref(CLOSURE)]

    words = []
    for w, g, s, old in zip(decisions, geometry, source['words'], study['all_current_words']):
        i = w['word']
        assert w['char'] == g['char'] == s['char']
        assert i == old['word']
        assert w['context'] == old['context']
        assert w['native_geometry'] == g['native_vowel']
        assert w['line'] == g['line'] == s['line']
        assert set(e['note'] for e in w['entry_actions']) == set(g['indices'])
        assert w['entry_actions'], i
        for e in w['entry_actions']:
            assert all(e.get(k) for k in ['purpose', 'alternative', 'uncertainty'])
        label = old['label']
        if i == 225:
            label = 'accepted_C_local_usable; original_v02_false_forward_retained'
        protection = {
            112: 'old_problem; guo_SHFC_rejected; no_dose_or_gain_compensation',
            124: 'reported_solid; no_all_dimensions_normal_claim',
            214: 'reported_solid; all_current_SHFC_paths_no_difference; keep',
            225: 'keep_accepted_C_and_whole_phrase22_prediction; local_acceptance_only',
            247: 'local_usable; preserve',
            295: 'unreported_quality_unknown; corrected_guo_identity',
            106: 'source_unknown_retained; no_lyric_or_clock_claim',
        }.get(i, 'no_new_quality_label; retain_baseline')
        words.append(dict(word=i, char=w['char'], lyric_line=w['line'], native_context=w['context'],
                          vowel=old['phoneme'], midi=old['tone'], vowel_start_s=g['native_vowel'][0],
                          vowel_end_s=g['native_vowel'][1], source_unknown=s['unknown'],
                          entry_count=len(w['entry_actions']), entry_families='|'.join(e['family'] for e in w['entry_actions']),
                          body_families='|'.join(e['family'] for e in w['body']), intent=w['intent'],
                          historical_quality_label=label, protection=protection,
                          version_action='keep_accepted_C_baseline' if w['context'] == 22 else 'keep_v02_baseline',
                          prediction_source='onset_fresh_B_is_logical_C' if w['context'] == 22 else 'v02_phrase',
                          new_feedback='pending', measurement_validated=False))

    phrases = []
    for i, (p, sy) in enumerate(zip(functions, synth)):
        assert p['context'] == sy['index'] == i
        group = [w for w in words if w['native_context'] == i]
        assert group
        pp = phones['parts'][i]
        assert len(pp['phrases']) == 1
        assert pp['part_position'] == c['voice_parts'][i]['position']
        assert len(pp['notes']) == len(c['voice_parts'][i]['notes'])
        for w in group:
            assert p['support'][0] <= w['vowel_start_s'] < w['vowel_end_s'] <= p['support'][1]
        raw_path = BASE / f'synthesis/phrase_{i:03}.npy'
        dyn_path = BASE / f'native_dynamics_raw/phrase_{i:03}.f32'
        if i == 22:
            raw_path = ONSET / 'fresh/B.npy'
            dyn_path = ONSET / 'dynamics_B/phrase_022.f32'
        phrases.append(dict(context=i, text=''.join(w['char'] for w in group),
                            word_ids='|'.join(str(w['word']) for w in group),
                            lyric_lines='|'.join(str(v) for v in sorted({w['lyric_line'] for w in group})),
                            support_start_s=p['support'][0], support_end_s=p['support'][1],
                            notes=len(pp['notes']), sung_entries=len(p['entries']), finite_actions=len(p['finite']),
                            periodic_actions=len(p['periodic']), historical_controls=len(p['controls']),
                            keep_reason='accepted_C_entire_predicted_context' if i == 22 else 'no_new_whole_phrase_feedback; retain_explicit_design',
                            raw_wave_path=raw_path.relative_to(ROOT).as_posix(), raw_wave_sha256=sha(raw_path),
                            dynamic_wave_path=dyn_path.relative_to(ROOT).as_posix(), dynamic_wave_sha256=sha(dyn_path),
                            wave_start_s=sy['wave_start_s'], samples=sy['samples'],
                            fresh_prediction_this_run=False, new_listening='pending'))

    counts = dict(words=318, lyric_lines=len(source['lines']), native_contexts=34, notes=412,
                  sung_entries=332, breath_or_silence_notes=80, source_unknown_words=source_unknowns,
                  entry_families=dict(Counter(e['family'] for w in decisions for e in w['entry_actions'])),
                  body_families=dict(Counter(e['family'] for w in decisions for e in w['body'])),
                  historical_control_actions=dict(Counter(q['abbr'] for p in functions for q in p['controls'])))
    plan = dict(version='lastpage-accepted-baseline-20261011', execution='sealed_wave_reuse_assembly',
                authorization='Finish existing listening cycle, then update songs one at a time; latest 下一步',
                purpose='Deliver the complete accepted-C vocal baseline before whole-song correction; collect version-specific evidence',
                project=ref(working), published_reference=ref(published), differences=differences,
                musical_controls_changed_this_run=0, new_model_execution=0,
                all_contexts_planned=phrases, all_word_actions='keep baseline; see bound word ledger',
                audio_outputs_budget=1, waveform_rate=44100, fixed_vocal_gain=1.5,
                bgm_task=False, normalization=False, compression=False,
                original_pitch_and_phone_notes_preserved=True, source_unknowns_preserved=source_unknowns,
                predictions='Reuse sealed v02 33 phrases; reuse accepted logical C complete phrase22, not old v02 phrase22',
                independent_checks=['v02 reassembly equals old raw array and encoded PCM',
                                    'accepted-C 181.8–187.2s equals original accepted-C PCM',
                                    'outside phrase22 contribution support unchanged',
                                    'each phrase raw*native_DYN equals reused dynamic contribution',
                                    'forward/reverse sums, finite/peak/PCM24 quantization and identities'],
                next_correction='Whole-song listening locations -> word/stage/neighbor ledger -> one explicitly planned correction version',
                stop_conditions=['Any source/hash/reassembly mismatch stops delivery',
                                 'No speculative global SHFC/VOIC/BREC changes or dose increase',
                                 'No new feedback means quality remains pending; no automatic extra candidate'],
                measurement_validated=False, general_rules_validated=False, agent_heard=False)
    # This concrete plan is saved before any PCM or numeric audio array is read.
    save(RUN / 'design/expression-plan.json', plan)
    save(RUN / 'observations/source-bindings.json', source_bindings)
    save(RUN / 'design/word-ledger.json', words)
    save(RUN / 'design/phrase-ledger.json', phrases)
    print('Plan frozen: 34 kept contexts, one complete accepted-C vocal; no model execution.', flush=True)

    # Read only our own already sealed audio contributions. Never load source
    # F0 arrays, author data, detectors, acoustic/mel features or model resources.
    sr = 44100
    n = load(BASE / 'assembly_check.json')['samples']
    baseline = np.zeros(n, dtype=np.float64)
    result = np.zeros(n, dtype=np.float64)
    reverse = np.zeros(n, dtype=np.float64)
    contributions = []
    dyn_checks = []
    for p, sy in zip(phrases, synth):
        i = p['context']
        original = np.fromfile(BASE / f'native_dynamics_raw/phrase_{i:03}.f32', dtype='<f4')
        gain = np.fromfile(BASE / f'native_dynamics_ones/phrase_{i:03}.f32', dtype='<f4')
        raw = np.load(ROOT / p['raw_wave_path'], allow_pickle=False)
        wave = np.fromfile(ROOT / p['dynamic_wave_path'], dtype='<f4')
        assert len(raw) == len(wave) == len(original) == len(gain) == p['samples']
        assert np.array_equal(raw.astype('<f4') * gain, wave), i
        assert np.isfinite(wave).all()
        start = round(p['wave_start_s'] * sr)
        lo, hi = max(0, start), min(n, start + len(wave))
        baseline[lo:hi] += original[lo-start:hi-start]
        result[lo:hi] += wave[lo-start:hi-start]
        contributions.append((lo, hi, wave[lo-start:hi-start]))
        dyn_checks.append(dict(context=i, exact_raw_times_native_DYN=True,
                               native_gain_min=float(gain.min()), native_gain_max=float(gain.max())))
    for lo, hi, wave in reversed(contributions):
        reverse[lo:hi] += wave
    assert np.array_equal(result, reverse)
    old_array = np.load(BASE / 'raw_vocal.npy', allow_pickle=False)
    assert np.array_equal(baseline, old_array)
    original_file = BASE / 'delivery/lastpage_loudness_v02_vocal.wav'
    old_pcm, old_sr = sf.read(original_file, dtype='int32')
    check_buffer = io.BytesIO()
    sf.write(check_buffer, baseline * 1.5, sr, format='WAV', subtype='PCM_24')
    check_buffer.seek(0)
    rebuilt_pcm, rebuilt_sr = sf.read(check_buffer, dtype='int32')
    assert old_sr == rebuilt_sr == sr and np.array_equal(rebuilt_pcm, old_pcm)
    changed = np.flatnonzero(result != baseline)
    assert len(changed) > 0
    p22 = phrases[22]
    start22 = round(p22['wave_start_s'] * sr)
    end22 = start22 + p22['samples']
    assert changed[0] >= start22 and changed[-1] < end22
    assert np.array_equal(result[:start22], baseline[:start22])
    assert np.array_equal(result[end22:], baseline[end22:])
    peak = float(np.max(np.abs(result * 1.5)))
    assert peak < 1 and np.isfinite(result).all()
    dest = RUN / 'delivery'
    dest.mkdir()
    project_out = dest / 'lastpage_accepted_C_baseline.ustx'
    shutil.copyfile(working, project_out)
    audio_out = dest / 'lastpage_accepted_C_baseline_vocal.wav'
    sf.write(audio_out, result * 1.5, sr, subtype='PCM_24')
    pcm, rate = sf.read(audio_out, dtype='int32')
    decoded, _ = sf.read(audio_out, dtype='float64')
    quant_error = float(np.max(np.abs(decoded-result * 1.5)))
    assert rate == sr and len(pcm) == n and quant_error < 2**-23 + 1e-12
    focus = [181.8, 187.2]
    lo, hi = [round(t * sr) for t in focus]
    local_pcm, local_rate = sf.read(ONSET / 'delivery/C_vocal.wav', dtype='int32')
    assert local_rate == sr and np.array_equal(pcm[lo:hi], local_pcm)
    assert np.array_equal(pcm[:start22], old_pcm[:start22])
    assert np.array_equal(pcm[end22:], old_pcm[end22:])
    assert sha(project_out) == sha(working)
    pcm_clip_count = int(np.count_nonzero((pcm == 2147483392) | (pcm == -2147483648)))
    assert pcm_clip_count == 0
    assembly = dict(sample_rate=sr, samples=n, duration_s=n/sr, channels=1, subtype='PCM_24',
                    reused_complete_contexts=34, new_model_inferences=0, musical_parameter_changes=0,
                    baseline_raw_exact=True, baseline_PCM_exact=True, reverse_assembly_exact=True,
                    accepted_C_focus_PCM_exact=True, focus_s=focus,
                    actual_changed_sample_span=[int(changed[0]), int(changed[-1])+1],
                    changed_contribution_support_s=[start22/sr, end22/sr],
                    unchanged_outside_phrase22_float_and_PCM=True,
                    fixed_vocal_gain=1.5, peak_before_quantization=peak,
                    fullscale_PCM_samples=pcm_clip_count, quantization_max_abs=quant_error,
                    native_DYN_checks=dyn_checks, project_bytes_exact=True,
                    source_audio_decodes=0, author_array_reads=0, detector_or_mel_reads=0,
                    own_audio_arrays_and_PCM_read=True, agent_heard=False,
                    full_song_quality='pending', measurement_validated=False)
    save(RUN / 'evaluation/assembly-check.json', assembly)
    print('Assembly verified: original v02 exact; accepted C local PCM exact; outside phrase22 unchanged.', flush=True)

    REPORT.mkdir(parents=True, exist_ok=True)
    csv_write(REPORT / (NAME + '-words.csv'), words)
    csv_write(REPORT / (NAME + '-phrases.csv'), phrases)
    report = dict(status='whole_song_baseline_audited_and_delivered_pending_listening', counts=counts,
                  project_difference=differences, source_bindings=source_bindings,
                  version_plan=ref(RUN / 'design/expression-plan.json'), audio=ref(audio_out), project=ref(project_out),
                  assembly=assembly, source_unknowns_retained=True,
                  historical_function_format='34 explicit center_nodes/entries/finite/periodic/controls plans; not schema1 executable input',
                  historical_copy_stage_vs_v02_metadata_differences=historical_reuse_differences,
                  preflight_failure='Initial check wrongly treated original copy-stage register as final v02 metadata; four versions explicitly distinguished; current sealed SHA and core source SHA retained',
                  historical_prediction_caveat='v02 word state summaries not accepted-C phrase22 state; whole phrase22 uses sealed logical C',
                  historical_DYN_caveat='word89 finite +3dB output envelope remains in v02 native DYN; no new gain correction',
                  listening_cycle='previous cycle closed; this full-song delivery awaits new version-specific feedback',
                  no_new_universal_rule=True, source_lyric_listening_verified=False,
                  table1_update='318 word/stage slots linked to existing descriptions; unreported quality unknown',
                  table2_update='34 explicit reuse records; no new intervention or new user response',
                  next='whole-song vocal feedback -> bind word/stage/neighbor; select one correction batch before any new synthesis')
    save(REPORT / (NAME + '.json'), report)
    md = f'''# 《最后一页》整曲基线核查与交付

2026-10-11。状态：whole_song_baseline_audited_and_delivered_pending_listening。

已将已接受抱C整曲工作工程对应的34句封存波形组装为完整人声。没有新增控制、重新推理或改写旧歌曲/音频；新工程是工作基线的原字节副本。此版本用于整曲定位与后续纠错，不称作整曲改善或验收通过。

## 核查结果

- 318字、38歌词行、34原生上下文、412音符（332演唱阶段、80 AP/SP）逐项关联；歌词行与原生上下文分别登记。入口动作：{counts['entry_families']}；字腹动作：{counts['body_families']}。动作分布仅是既有设计事实，不证明听感成功。
- 源观测GAME/双F0/歌词时钟字节绑定保持；word106“没”source unknown保持。38行歌词身份仍未经过人工逐行确认。历史验证报告的0.5c以内误差、完整时钟等只是旧技术结论，本轮不重新测F0或确认原曲事实。
- 完整工作工程SHA：`{sha(working)}`；发布v02 SHA：`{sha(published)}`。差异限定抱所在context22新增SHFC和声明范围从±12修正为±1200；原音符、时钟、其它曲线保留。旧果B未采用。
- 原34份函数计划是旧center_nodes/entries/finite/periodic/controls格式，不能直接冒充当前schema1编译输入。旧v02的phrase22预测/逐字状态不冒充接受C；本次复用的是C完整上下文。旧word89 DYN +3dB有限包络仍在，未新加响度补偿。
- 首轮检查将最初复制阶段登记误当最终v02绑定而停止；失败快照保留在rejected-preflight下。四份元数据（separation、fresh_center工程、函数计划、逐字决策）最终SHA与原复制SHA不同，已按当前完成清单精确绑定，原复制登记和源观测SHA不改写。
- 旧整曲v02能逐句精确重建float数组及PCM；新整曲181.8–187.2秒与原接受C局部PCM精确。context22贡献以外float/PCM精确保持。逐句raw×原生DYN精确、正反组装精确、PCM24量化及满幅检查通过。
- 新人声{n/sr:.6f}秒、44100Hz、mono PCM24、固定增益1.5；峰值{peak:.9f}、满幅样本0。不研究BGM、不归一化、不压缩。33句沿用v02，1句沿用接受C；34句不是34次新实验。

## 保护范围与纠错入口

抱225保留C整句输入/预测/输出及原局部可用反馈，不能扩成全曲正常；果247原局部可用、124/214原偏实、112原问题/果SHFC否决、295未知和106源未知均保留。已停止的TENC/BREC/果SHFC加量不恢复。旧反馈来自各自旧版本，新整曲接受状态待评。

首轮整曲试听记录具体时间或字，以及字头/腹/尾、邻字/句内问题。先形成一个版本的修改目的、动作与保护范围，再编译及重建受影响完整下游；每轮同时记录未改善和副作用。若多控制同时变化按联合干预记录，不宣布唯一病因；最多两轮初始策略修订后收口当前设计，不自动追加候选。318字逐项有版本动作和待反馈槽，未报字不补“正常”。

表1保留描述候选与音频位置，表2保留版本/上下文/原输入、变化与反馈关系；本次只是34句复用交付记录，新人类反馈0、通用规律0、measurement_validated仍false。Agent未听。72条件/384波形旧成本草案仍暂不执行。

## 交付与绑定

- [完整接受C人声](../../../runs/production/lastpage-accepted-baseline-20261011/delivery/lastpage_accepted_C_baseline_vocal.wav)
- [完整工作工程副本](../../../runs/production/lastpage-accepted-baseline-20261011/delivery/lastpage_accepted_C_baseline.ustx)
- [318字账本]({NAME}-words.csv)、[34句账本]({NAME}-phrases.csv)、[JSON]({NAME}.json)、[审计]({NAME}-audit.json)。原试听收口报告与反馈不改写。
'''
    (REPORT / (NAME + '.md')).write_text(md, encoding='utf-8', newline='\n')

    status = ('当前状态whole_song_baseline_audited_and_delivered_pending_listening：2026-10-11已完成最后一页整曲基线核查，'
              '318字/38歌词行/34原生上下文/412音符与显式动作逐项登记，源未知106保留。'
              '已接受抱C完整工程与发布v02分列；首次组装完整接受C人声245.577143秒，33句沿用v02、1句沿用C封存波形，模型执行0/新参数0。'
              'v02整曲重建与原PCM精确、C局部PCM精确、context22以外精确；原生DYN/固定1.5/PCM24检查通过，旧word89 DYN有限包络保持。'
              '新交付音频1/工程原字节副本1，原歌曲/既有音频/Skill不改；整曲听感待评、Agent未听、通用规律0。'
              '旧试听循环已收口/10条回复与阴性保留；下一步先整曲人声定位，再冻结一轮修改并回填表1/表2，不自动加量或执行72/384草案，单Agent/CI仅手动。')
    link = 'docs/reports/lastpage/' + NAME + '.md'
    for name in ENTRIES:
        p = ROOT / name
        text = p.read_text(encoding='utf-8')
        lines = text.splitlines()
        indices = [i for i, line in enumerate(lines) if '当前状态closed_with_explicit_gaps：' in line]
        assert len(indices) == 1, name
        prefix = '- ' if lines[indices[0]].startswith('- ') else ''
        relative = link if '/' not in name else ('../../' if name.startswith('research/') else '../../../') + link
        lines[indices[0]] = prefix + status + f' 见[整曲基线核查与交付]({relative})。'
        text = '\n'.join(lines) + '\n'
        # Keep historical paragraphs unchanged; update the current next action.
        if name == 'plan.md':
            for line in text.splitlines():
                if line.startswith('下一工作进入逐首更新，先《最后一页》：'):
                    text = text.replace(line, '下一工作进入逐首更新，先《最后一页》：完整接受C基线人声已交付；先按该版本整曲定位，绑定word/阶段/邻字与原话，再冻结一轮修改目的、控制与重建范围。没有新反馈就保留待评，不自动渲染新候选。')
        p.write_text(text, encoding='utf-8', newline='\n')
    check(protected)
    check(prior_refs)
    assert 'workflow_dispatch:' in (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    gate = subprocess.run([sys.executable, 'tools/repository/check_repository.py', '--worktree'], cwd=ROOT,
                          capture_output=True, text=True, encoding='utf-8')
    (RUN / 'logs').mkdir()
    (RUN / 'logs/repository-gate.log').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    # Read back compact ledgers; inputs and payloads are fully SHA-bound.
    with (REPORT / (NAME + '-words.csv')).open(encoding='utf-8', newline='') as f:
        assert len(list(csv.DictReader(f))) == 318
    with (REPORT / (NAME + '-phrases.csv')).open(encoding='utf-8', newline='') as f:
        assert len(list(csv.DictReader(f))) == 34
    check(source_bindings)
    check(protected)
    check(prior_refs)
    audit = dict(status='passed_with_explicit_listening_and_measurement_gaps', protected_files=len(protected),
                 closure_files_and_docs=len(prior_refs), source_bindings=len(source_bindings),
                 identities_and_word_phrase_ledgers=True, baseline_and_accepted_C_PCM_exact=True,
                 no_old_file_mutation=True, no_historical_script_execution=True,
                 model_execution=0, new_user_feedback=0, new_audio_deliveries=1,
                 copied_project_bytes_exact=True, author_array_reads=0, source_unknowns_preserved=[106],
                 gate=gate.stdout.strip(), script=ref(Path(__file__)), outputs=[ref(audio_out), ref(project_out)])
    save(RUN / 'evaluation/audit.json', audit)
    save(REPORT / (NAME + '-audit.json'), audit)
    docs = [ref(p) for p in sorted(REPORT.glob(NAME + '*'))]
    files = [ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()]
    save(RUN / 'completion-manifest.json', dict(status=audit['status'], files=files, documents=docs,
                                               entries=[ref(ROOT / n) for n in ENTRIES]))
    print(json.dumps({'status': audit['status'], 'audio': ref(audio_out), 'words': 318, 'phrases': 34,
                      'protected': len(protected), 'gate': audit['gate']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
