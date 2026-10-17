"""Record comparative power/softness and absence of audible break in S/A."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from record_stage_2e_word225_feedback import ENTRIES, EXPERIMENT, ROOT, HERE, OUT, ref, save, check_refs

RUN = ROOT / 'runs/research/table2-word225-sa-feedback-20261011'
NAME = 'table2-stage-2e-word225-sa-feedback-20261011'
MESSAGE = '就是k3更有力量，k1更柔，都没有破音'
PREVIOUS = [ROOT / ('runs/research/' + name) for name in (
    'table2-word225-feedback-20261011', 'table2-word214-feedback-20261011')]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    outputs = [OUT / (NAME + s) for s in ('.json', '.md', '-audit.json')]
    assert not RUN.exists() and not any(p.exists() for p in outputs), 'Already recorded'
    seal_path = EXPERIMENT / 'completion-manifest.json'
    assert ref(seal_path)['sha256'] == 'c3e55742a78a1c57bab2fa34943a2379bab5d16e6ebb1b57aa7cf15db9fddf85'
    seals = [load(seal_path)] + [load(p / 'completion-manifest.json') for p in PREVIOUS]
    immutable = [r for seal in seals for r in seal['files'] + seal['documents']]
    check_refs(immutable)
    binding = load(HERE / 'stage_2e_execution_baseline_binding.json')
    assert ref(ROOT / binding['manifest'])['sha256'] == binding['sha256']
    baseline = load(ROOT / binding['manifest'])
    protection = baseline['production_skill_project_bindings'] + baseline['protected_inputs']
    check_refs(protection)
    package_path = EXPERIMENT / 'pcm-packaging.json'
    package = load(package_path)
    pairs = [p for p in package['pairs'] if p['condition_id'] == 'current-word-225' and p['order'] in (1, 2)]
    assert [(p['direction'], p['codes']) for p in pairs] == [('S-A', ['K3', 'K1']), ('A-S', ['K1', 'K3'])]
    audio = [dict(presentation=p, **next(f for f in package['files'] if f['path'] == p['vocal'])) for p in pairs]
    assert all(a['channels'] == 1 and a['subtype'] == 'PCM_24' for a in audio)
    check_refs(audio)
    snapshots = []
    updates = {}
    current = ('2E当前状态partial_human_feedback_recorded：2026-10-11累计3条本批反馈：'
               '抱225四版“k3最好”、只214四版“没区别”；抱K3/K1成对人声新增原话“'
               + MESSAGE + '”。K3=S力量感更强、K1=A更柔，用户回报两者均无破音，'
               '范围只限本次成对焦点人声；不等于客观响度/生理机制或全曲验收。'
               '只的限定阴性保留且不扩大验证；其余抱D/P对照、混音及未明确细项仍待反馈，'
               '两个顺序分别评价及设备/音量/实际试听顺序unknown。2E整体未完成，'
               'measurement_validated仍false，通用规律0；下一步仅已有对照剩余试听与证据收拢，'
               '不生成新候选，原歌曲/既有音频/Skill不改，单Agent、CI仅手动，2F–2H未执行。')
    for name in ENTRIES:
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        old = next(line for line in text.splitlines() if '2E当前状态partial_human_feedback_recorded：' in line)
        link = Path(os.path.relpath(outputs[1], path.parent)).as_posix()
        prefix = '- ' if old.startswith('- ') else ''
        text = text.replace(old, prefix + current + f' 见[抱S/A细分反馈]({link})。', 1)
        text = text.replace('抱K3偏好及只未感知差别已绑定，其余听觉缺口保留',
                            '抱K3偏好及S/A力量感/柔和/无破音、只未感知差别已绑定，其余听觉缺口保留')
        text = text.replace('抱K3偏好及只未感知差别已绑定，其余听觉待评价',
                            '抱S/A细分反馈及只未感知差别已绑定，其余听觉待评价')
        text = text.replace('已绑定抱K3偏好及只未感知差别，其余本批听觉缺口保留',
                            '已绑定抱S/A细分反馈及只未感知差别，其余本批听觉缺口保留')
        text = text.replace('抱局部偏好及只未感知差别已绑定，其余听觉缺口保留',
                            '抱局部偏好及S/A细分反馈、只未感知差别已绑定，其余听觉缺口保留')
        text = text.replace('抱K3局部偏好、只214未感知差别已记录；细项与成对/混音仍待明确，只不扩大验证',
                            '抱S/A力量感/柔和/两者无破音、只214未感知差别已记录；其余抱D/P成对与混音及未明确细项待反馈，只不扩大验证')
        updates[path] = text
    RUN.mkdir(parents=True)
    for name in ENTRIES + [r['path'] for seal in seals[1:] for r in seal['documents']]:
        source = ROOT / name
        dest = RUN / 'before' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(source.read_bytes())
        assert ref(source)['sha256'] == ref(dest)['sha256']
        snapshots.append(dict(**ref(source), snapshot=dest.relative_to(ROOT).as_posix()))
    save(RUN / 'before/snapshot-manifest.json', dict(files=snapshots))
    record = dict(schema_version=1, feedback_id='T2E-W225-SA-20261011',
        status='partial_human_feedback_recorded', stage_2E_complete=False,
        record_created_utc=datetime.now(timezone.utc).isoformat(), user_message_timestamp='unknown',
        user_message_verbatim=MESSAGE,
        message_source='human user replying to paired mono vocals 01 K3→K1 and 02 K1→K3 in current chat',
        condition_id='current-word-225', lyric='抱', comparison='S-A', presented_audio=audio,
        feedback_scope='aggregate report for the two presented focus-vocal orders; not full-context/mix/whole-song acceptance',
        per_order_results='not separately stated', actual_listened_set='not separately enumerated',
        version_results=[dict(code='K3', research_path='S', relative_description_verbatim='更有力量',
                             audible_break_user_report='none_in_current_presentation'),
                         dict(code='K1', research_path='A', relative_description_verbatim='更柔',
                             audible_break_user_report='none_in_current_presentation')],
        prior_preference='word225 K3 preferred within four-version presentation remains unchanged',
        new_preference_statement='not repeated in this message; comparative qualities supplied',
        audible_break_scope='two current paired focal versions only; not objective detector confirmation or all prior variants',
        auditory_details={k: 'unknown' for k in ('objective_loudness', 'subjective_loudness', 'diction', 'body', 'naturalness', 'absolute_usability')},
        listening_metadata={k: 'unknown' for k in ('device', 'player', 'volume', 'actual_order', 'repetitions', 'both_order_completion', 'blinding')},
        inference_boundary='Perceptible local power/softness distinction in complete S versus A; not single-channel attribution, physiology or universal rule',
        preserved_feedback=[ref(p / 'feedback.json') for p in PREVIOUS],
        paired_comparison_groups_with_explicit_feedback=1, frozen_main_comparison_groups=10,
        cumulative_new_feedback=3, this_record_new_feedback=1,
        remaining_gaps=['other word225 D/P paired comparisons', 'mixed-audio feedback', 'unreported auditory dimensions', 'order-specific results'],
        experiment_seal=ref(seal_path), previous_feedback_seals=[ref(p / 'completion-manifest.json') for p in PREVIOUS],
        packaging=ref(package_path), protocol=ref(OUT / 'validation-protocols/shfc-path-separation-v1.json'),
        pre_update_snapshot=ref(RUN / 'before/snapshot-manifest.json'), protected_baseline=binding,
        new_waveforms=0, new_model_calls=0, agent_heard=False, measurement_validated=False,
        general_rule_validated=False, production_song_changed=False, skill_changed=False,
        automatic_expansion=False, recorder=ref(Path(__file__).resolve()))
    save(RUN / 'feedback.json', record)
    save(outputs[0], record)
    rows = '\n'.join(f"| {a['presentation']['order']:02d} | {'→'.join(a['presentation']['codes'])} | `{a['sha256']}` |" for a in audio)
    report = f'''# 2E抱225 S/A成对人声细分反馈

2026-10-11。partial_human_feedback_recorded；2E整体未完成。

用户在01 K3→K1、02 K1→K3焦点人声交付后回报：**{MESSAGE}**。

| 版本 | 本次相对听感 | 用户回报的破音 |
|---|---|---|
| K3=S完整SHFC路径 | 更有力量 | 本次呈现未听到 |
| K1=A未偏移基底 | 更柔 | 本次呈现未听到 |

保留原四版“k3最好”偏好，本条补充力量感/柔和差异与两者无破音的听觉反馈。力量感不改写为更响、更实、VOIC更高或声带机制；更柔不标为缺陷。无破音限本次焦点人声中的两个版本，不能覆盖历史其它SHFC进入形状/旧B反馈或宣布整曲无破音。此次回复没有分别评价两个播放顺序，实际听过集合/设备/播放器/音量/重复/盲听程度unknown。

| 呈现 | 顺序 | 已封存焦点成对单声道人声SHA256 |
|---|---|---|
{rows}

本次仅能支持当前抱条件、剂量和路径S/A的可感知力量感/柔和差别。D/P单独路径尚缺成对反馈，不能归因单一VOIC/BREC/TENC、证明分量为零或交互。客观/主观响度、咬字、字腹、自然度及绝对可用性仍未明确。本条不是混音评价或完整乐句/全曲验收。

累计3条新反馈：抱四版偏好K3、只四版“没区别”、本条抱S/A细分描述；只的限定阴性与停止扩大验证保持。10组冻结主对照中1组获明确成对描述（双顺序呈现的合并回复，不算2次独立复制）。其余抱D/P对照、混音和未报细项待反馈；2E整体未完成，measurement_validated仍false，2F–2H未执行。

本轮新波形/模型调用0，原歌曲/音频/Skill/安装不改。实验484文件/4报告、前两份反馈run/6报告、79生产/Skill/工程与67保护输入SHA重查；6入口及6旧反馈报告更新前原字节另存。下一步继续已有冻结对照，不加剂量/条件或候选。

[JSON]({NAME}.json) · [本轮审计]({NAME}-audit.json) · [前两条反馈](table2-stage-2e-word214-feedback-20261011.md) · [冻结协议](validation-protocols/shfc-path-separation-v1.md)。
'''
    with outputs[1].open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(report)
    for path, text in updates.items():
        path.write_text(text, encoding='utf-8', newline='\n')
    save(outputs[2], dict(status='checking'))
    gate = subprocess.run([sys.executable, str(ROOT / 'tools/repository/check_repository.py'), '--worktree'],
                          cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    (RUN / 'worktree-gate.txt').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    check_refs(immutable + protection + audio)
    for row in snapshots:
        assert ref(ROOT / row['snapshot'])['sha256'] == row['sha256']
    assert outputs[0].read_bytes() == (RUN / 'feedback.json').read_bytes()
    links = 0
    for path in list(updates) + [outputs[1]]:
        for target in re.findall(r'\]\(([^\s)]+)\)', path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            assert (path.parent / target.split('#')[0]).exists(), (path, target)
            links += 1
    audit = dict(status='passed_partial_human_feedback', date='2026-10-11',
        sealed_experiment_files_SHA=len(seals[0]['files']), sealed_experiment_documents_SHA=len(seals[0]['documents']),
        previous_feedback_files_SHA=sum(len(s['files']) for s in seals[1:]), previous_feedback_documents_SHA=6,
        production_skill_project_SHA=len(baseline['production_skill_project_bindings']),
        protected_inputs_SHA=len(baseline['protected_inputs']), presented_pair_audio_SHA=2,
        snapshot_files_SHA=len(snapshots), current_markdown_links_checked=links,
        feedback=ref(outputs[0]), report=ref(outputs[1]), current_entries=[ref(ROOT / p) for p in ENTRIES],
        worktree_gate=json.loads(gate.stdout), worktree_gate_log=ref(RUN / 'worktree-gate.txt'),
        this_record_new_feedback=1, cumulative_new_feedback=3, new_waveforms=0, new_model_calls=0,
        stage_2E_complete=False, agent_heard=False, measurement_validated=False, CI_manual_only=True)
    outputs[2].write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save(RUN / 'audit.json', audit)
    save(RUN / 'completion-manifest.json', dict(status='sealed_partial_human_feedback',
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in outputs], current_entries=audit['current_entries']))
    print(json.dumps(dict(status=audit['status'], verbatim=MESSAGE,
        feedback_count=3, new_waveforms=0, worktree_gate=audit['worktree_gate']), ensure_ascii=False))


if __name__ == '__main__':
    main()
