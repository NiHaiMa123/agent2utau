"""Append the word214 no-difference feedback; preserve both prior seals."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from record_stage_2e_word225_feedback import ENTRIES, EXPERIMENT, ROOT, HERE, OUT, ref, save, check_refs

RUN = ROOT / 'runs/research/table2-word214-feedback-20261011'
PRIOR = ROOT / 'runs/research/table2-word225-feedback-20261011'
NAME = 'table2-stage-2e-word214-feedback-20261011'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    outputs = [OUT / (NAME + suffix) for suffix in ('.json', '.md', '-audit.json')]
    assert not RUN.exists() and not any(p.exists() for p in outputs), 'Feedback already recorded'
    seal_path = EXPERIMENT / 'completion-manifest.json'
    assert ref(seal_path)['sha256'] == 'c3e55742a78a1c57bab2fa34943a2379bab5d16e6ebb1b57aa7cf15db9fddf85'
    seal = load(seal_path)
    prior_seal_path = PRIOR / 'completion-manifest.json'
    prior_seal = load(prior_seal_path)
    immutable = seal['files'] + seal['documents'] + prior_seal['files'] + prior_seal['documents']
    check_refs(immutable)
    binding = load(HERE / 'stage_2e_execution_baseline_binding.json')
    assert ref(ROOT / binding['manifest'])['sha256'] == binding['sha256']
    baseline = load(ROOT / binding['manifest'])
    protection = baseline['production_skill_project_bindings'] + baseline['protected_inputs']
    check_refs(protection)
    package_path = EXPERIMENT / 'pcm-packaging.json'
    package = load(package_path)
    condition = next(c for c in package['conditions'] if c['condition_id'] == 'current-word-214')
    versions = sorted(condition['versions'], key=lambda v: v['code'])
    assert [(v['code'], v['label']) for v in versions] == [('K1', 'P'), ('K2', 'S'), ('K3', 'A'), ('K4', 'D')]
    audio = [dict(code=v['code'], research_path=v['label'],
                  **next(f for f in package['files'] if f['path'] == v['full_vocal'])) for v in versions]
    assert all(a['channels'] == 1 and a['subtype'] == 'PCM_24' for a in audio)
    check_refs(audio)
    prior_record = load(PRIOR / 'feedback.json')
    assert prior_record['user_message_verbatim'] == 'k3最好'
    assert prior_record['preferred_research_path'] == 'S'
    current = ('2E当前状态partial_human_feedback_recorded：2026-10-11两条本批反馈已绑定：'
               '抱225原话“k3最好”（K3=S，四份独立完整上下文人声局部排序）；'
               '只214原话“没区别”（四份独立完整上下文人声未感知差别，K1=P/K2=S/K3=A/K4=D）。'
               '累计新反馈2条；只的限定阴性不否定抱的局部偏好，不宣称波形相同、通道无效或普遍规律。'
               '按协议停止只的扩大验证，不加剂量/时间形状/条件或新候选。细分听感、混音及固定成对对照尚缺明确反馈，'
               '设备/音量/实际试听顺序unknown；2E整体未完成，measurement_validated仍false，通用规律0。'
               '下一步仅本批证据收拢及已有对照的剩余反馈；原歌曲、既有音频、Skill不改，单Agent、CI仅手动，2F–2H未执行。')
    updates = {}
    for name in ENTRIES:
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        old = next(line for line in text.splitlines() if '2E当前状态partial_human_feedback_recorded：' in line)
        prefix = '- ' if old.startswith('- ') else ''
        link = Path(os.path.relpath(outputs[1], path.parent)).as_posix()
        text = text.replace(old, prefix + current + f' 见[两条件最新反馈]({link})。', 1)
        text = text.replace('抱K3局部偏好已绑定，其余听觉缺口保留', '抱K3偏好及只未感知差别已绑定，其余听觉缺口保留')
        text = text.replace('抱K3局部偏好已绑定，其余听觉待评价', '抱K3偏好及只未感知差别已绑定，其余听觉待评价')
        text = text.replace('已绑定抱K3局部偏好，其余本批听觉评价待完成', '已绑定抱K3偏好及只未感知差别，其余本批听觉缺口保留')
        text = text.replace('抱局部偏好已绑定，其余听觉缺口保留', '抱局部偏好及只未感知差别已绑定，其余听觉缺口保留')
        text = text.replace('下一工作为本批2E其余人工试听及反馈绑定（抱K3局部偏好已记录；只214、细项与成对/混音反馈待明确）；',
                            '下一工作为本批2E证据收拢及已有对照的剩余反馈（抱K3局部偏好、只214未感知差别已记录；细项与成对/混音仍待明确，只不扩大验证）；')
        assert '只214、混音及固定成对对照仍待明确反馈' not in text, name
        updates[path] = text
    RUN.mkdir(parents=True)
    snapshots = []
    for name in ENTRIES + [r['path'] for r in prior_seal['documents']]:
        path = ROOT / name
        dest = RUN / 'before' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(path.read_bytes())
        assert ref(dest)['sha256'] == ref(path)['sha256']
        snapshots.append(dict(**ref(path), snapshot=dest.relative_to(ROOT).as_posix()))
    save(RUN / 'before/snapshot-manifest.json', dict(files=snapshots))
    record = dict(schema_version=1, feedback_id='T2E-W214-NODIFF-20261011',
        status='partial_human_feedback_recorded', stage_2E_complete=False,
        record_created_utc=datetime.now(timezone.utc).isoformat(),
        user_message_verbatim='没区别', user_message_timestamp='unknown',
        message_source='human user replying to four embedded 只 full-context mono vocal files in current chat',
        condition_id='current-word-214', lyric='只', presented_audio=audio,
        auditory_result='no_perceptible_difference_reported', preferred_code=None,
        preference_status='no preference reported',
        feedback_scope='four presented full-context mono vocals; not explicit fixed-pair or mixed-audio feedback',
        actual_listened_set='not separately enumerated', pairwise_discrimination_results='not separately enumerated',
        auditory_details={k: 'unknown' for k in ('onset', 'break_or_crack', 'loudness', 'diction', 'body', 'naturalness', 'absolute_usability')},
        listening_metadata={k: 'unknown' for k in ('device', 'player', 'volume', 'actual_order', 'repetitions', 'complete_four_file_listening', 'blinding')},
        inference_boundary='Limited negative at this condition/dose/presentation; not waveform equality, a zero component effect, physiological cause or universal SHFC ineffectiveness',
        stopping_action='No expanded word214 dose/time-shape/condition/seed or new candidate under frozen protocol',
        preserved_word225_feedback=ref(PRIOR / 'feedback.json'),
        cumulative_new_feedback=2, this_record_new_feedback=1,
        remaining_gaps=['specific auditory dimensions', 'explicit fixed-pair feedback', 'mixed-audio feedback'],
        experiment_seal=ref(seal_path), prior_feedback_seal=ref(prior_seal_path), packaging=ref(package_path),
        protocol=ref(OUT / 'validation-protocols/shfc-path-separation-v1.json'),
        pre_update_snapshot=ref(RUN / 'before/snapshot-manifest.json'), protected_baseline=binding,
        new_waveforms=0, new_model_calls=0, agent_heard=False, measurement_validated=False,
        general_rule_validated=False, production_song_changed=False, skill_changed=False,
        automatic_expansion=False, recorder=ref(Path(__file__).resolve()))
    save(RUN / 'feedback.json', record)
    save(outputs[0], record)
    rows = '\n'.join(f"| {a['code']} | {a['research_path']} | `{a['sha256']}` |" for a in audio)
    report = f'''# 2E只214人工反馈与两条件当前结论

2026-10-11。partial_human_feedback_recorded，2E整体未完成。

用户在四份独立完整上下文“只”人声K1–K4交付后回报：**没区别**。原话保存为当前条件/−400c、145ms进入/55ms退出/当前呈现下未感知差别；没有偏好版本，也不补造逐对辨别结果。实际听过的文件集合未另列。

| 呈现编码 | 冻结研究路径 | 完整单声道人声SHA256 |
|---|---|---|
{rows}

本次编码是只214的独立映射，与抱225映射不同。按冻结协议“无区别/不确定→本协议限定阴性/unknown”及“不加剂量、不扫时间/元音/seed、不补第三条件”执行：只不扩大验证，不追加候选或增益补偿。该反馈不等于四波形PCM相同、某一分量效应为零、整个SHFC通道无效或原偏实标签通过/失败。

当前两条件结果分别保存：

| 条件 | 用户原话 | 限定结论 |
|---|---|---|
| 抱225 | k3最好 | 当前四版呈现中偏好K3=S完整路径；保留既往抱C局部反馈 |
| 只214 | 没区别 | 当前四版呈现未获得可感知差别支持；停止扩大验证 |

抱的偏好不被只的限定阴性覆盖，不能跨元音泛化或归因单一VOIC/BREC/TENC、生理机制。字头、破音、响度、咬字、字腹、自然度、绝对可用性以及设备/播放器/音量/顺序/重复/盲听程度仍unknown；混音及固定双顺序成对对照未获明确反馈。独立文件回复不冒充10组主对照全部验收，2E整体未完成，全部measurement_validated仍false，2F–2H未执行。

本轮追加反馈1条，累计2条；新模型调用/新波形均0，原歌曲、既有音频、Skill、安装与旧封存产物不改。484实验文件及4份技术报告、此前抱反馈run与3份报告、79生产/Skill/工程及67保护输入SHA重查；6份更新前入口与3份抱报告另存原字节。下一步仅本批证据收拢与已有对照剩余反馈，不自动加试验。

[结构记录]({NAME}.json) · [本轮审计]({NAME}-audit.json) · [原抱反馈](table2-stage-2e-word225-feedback-20261011.md) · [冻结协议](validation-protocols/shfc-path-separation-v1.md)。
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
    gate_summary = json.loads(gate.stdout)
    assert gate_summary['audio_payloads'] == 0 and gate_summary['checks'] == 'passed'
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
    ci = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert re.search(r'^on:\s*\n  workflow_dispatch:', ci, re.MULTILINE)
    assert not re.search(r'^  (push|pull_request|schedule):', ci, re.MULTILINE)
    audit = dict(status='passed_partial_human_feedback', date='2026-10-11',
        sealed_experiment_files_SHA=len(seal['files']), sealed_experiment_documents_SHA=len(seal['documents']),
        prior_feedback_files_SHA=len(prior_seal['files']), prior_feedback_documents_SHA=len(prior_seal['documents']),
        experiment_seal=ref(seal_path), prior_feedback_seal=ref(prior_seal_path),
        production_skill_project_SHA=len(baseline['production_skill_project_bindings']),
        protected_inputs_SHA=len(baseline['protected_inputs']), presented_full_vocal_SHA=4,
        snapshot_files_SHA=len(snapshots), current_markdown_links_checked=links,
        feedback=ref(outputs[0]), report=ref(outputs[1]), current_entries=[ref(ROOT / p) for p in ENTRIES],
        worktree_gate=gate_summary, worktree_gate_log=ref(RUN / 'worktree-gate.txt'),
        this_record_new_feedback=1, cumulative_new_feedback=2, new_waveforms=0, new_model_calls=0,
        stage_2E_complete=False, agent_heard=False, measurement_validated=False, CI_manual_only=True)
    outputs[2].write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save(RUN / 'audit.json', audit)
    save(RUN / 'completion-manifest.json', dict(status='sealed_partial_human_feedback',
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in outputs], current_entries=audit['current_entries']))
    print(json.dumps(dict(status=audit['status'], condition='current-word-214',
        verbatim=record['user_message_verbatim'], prior_word225_preserved=True,
        cumulative_feedback=2, new_waveforms=0, worktree_gate=gate_summary), ensure_ascii=False))


if __name__ == '__main__':
    main()
