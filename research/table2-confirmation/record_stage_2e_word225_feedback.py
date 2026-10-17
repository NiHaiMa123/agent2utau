"""Bind the user's local K3 preference without changing the sealed experiment."""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from freeze_stage_2d import ROOT, HERE, OUT, load, sha

RUN = ROOT / 'runs/research/table2-word225-feedback-20261011'
EXPERIMENT = ROOT / 'runs/experiments/table2-shfc-paths-20261011'
NAME = 'table2-stage-2e-word225-feedback-20261011'
ENTRIES = ['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md',
           'research/table2-confirmation/README.md',
           'docs/knowledge/acoustic-manifestations-20261009/README.md']


def ref(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def check_refs(rows):
    for row in rows:
        assert sha(ROOT / row['path']) == row['sha256'], row['path']


def main():
    outputs = [OUT / (NAME + suffix) for suffix in ('.json', '.md', '-audit.json')]
    assert not RUN.exists() and not any(p.exists() for p in outputs), 'Feedback already recorded'
    seal_path = EXPERIMENT / 'completion-manifest.json'
    assert sha(seal_path) == 'c3e55742a78a1c57bab2fa34943a2379bab5d16e6ebb1b57aa7cf15db9fddf85'
    seal = load(seal_path)
    assert len(seal['files']) == 484 and len(seal['documents']) == 4
    check_refs(seal['files'] + seal['documents'])
    baseline_binding = load(HERE / 'stage_2e_execution_baseline_binding.json')
    assert sha(ROOT / baseline_binding['manifest']) == baseline_binding['sha256']
    baseline = load(ROOT / baseline_binding['manifest'])
    protection = baseline['production_skill_project_bindings'] + baseline['protected_inputs']
    assert len(baseline['production_skill_project_bindings']) == 79
    assert len(baseline['protected_inputs']) == 67
    check_refs(protection)
    package = load(EXPERIMENT / 'pcm-packaging.json')
    condition = next(c for c in package['conditions'] if c['condition_id'] == 'current-word-225')
    versions = sorted(condition['versions'], key=lambda v: v['code'])
    assert [(v['code'], v['label']) for v in versions] == [('K1', 'A'), ('K2', 'D'), ('K3', 'S'), ('K4', 'P')]
    audio = []
    for version in versions:
        meta = next(f for f in package['files'] if f['path'] == version['full_vocal'])
        assert meta['channels'] == 1 and meta['subtype'] == 'PCM_24'
        audio.append(dict(code=version['code'], research_path=version['label'], **meta))
    check_refs(audio)

    current = '2E当前状态partial_human_feedback_recorded：2026-10-11收到用户原话“k3最好”，限定为抱225四份独立完整上下文人声中的K3偏好；固定映射K1=A、K2=D、K3=S、K4=P。新反馈1条，四音频SHA已绑定。字头/破音/响度/自然度等细项、实际试听顺序与设备未知；只214、混音及固定成对对照仍待明确反馈。2E整体未完成，全部measurement_validated仍false，通用规律0；下一步仅继续本批试听/反馈绑定，原歌曲、既有音频、Skill与自动CI边界保持，2F–2H未执行。'
    updates = {}
    for name in ENTRIES:
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        target = OUT / (NAME + '.md')
        import os
        link = Path(os.path.relpath(target, path.parent)).as_posix()
        paragraph = current + f' 见[抱K3局部反馈]({link})。'
        # Keep the technical status as an explicitly dated historical state.
        marker = '2E有限实际执行状态technical_execution_complete_pending_human_listening'
        assert marker in text, name
        text = text.replace(marker, '2E技术交付封存时状态technical_execution_complete_pending_human_listening', 1)
        if name == 'AGENTS.md':
            text = text.replace('## Codex与当前计划\n', '## Codex与当前计划\n\n- ' + paragraph + '\n', 1)
            text = text.replace('最新边界以本条及根目录plan为准', '最新边界以本文件顶部当前反馈条及根目录plan为准')
            text = text.replace('2E冻结实际渲染/技术交付已完成、待人工试听', '2E冻结实际渲染/技术交付已完成、抱局部偏好已绑定，其余听觉缺口保留')
        elif name == 'README.md':
            text = text.replace('## 当前任务与入口\n', '## 当前任务与入口\n\n' + paragraph + '\n', 1)
            text = text.replace('当前**表1 A–F固定范围整合完成；表2完成2A–2D及2E冻结16套实际渲染/技术交付，人工试听pending，确认缺口保留**', '技术交付封存时**表1 A–F固定范围整合完成；表2完成2A–2D及2E冻结16套实际渲染/技术交付，当时人工试听pending，确认缺口保留**')
            text = text.replace('人工试听待评价，缺口保留 |', '抱K3局部偏好已绑定，其余听觉缺口保留 |')
            text = text.replace('人工试听pending，2F–2H未执行；新因果试听按冻结范围 |', '抱K3局部偏好已绑定，其余听觉待评价，2F–2H未执行；新因果试听按冻结范围 |')
        else:
            title_end = text.index('\n')
            text = text[:title_end + 1] + '\n' + paragraph + '\n' + text[title_end + 1:]
            if name == 'plan.md':
                text = text.replace('现待本批人工试听', '已绑定抱K3局部偏好，其余本批听觉评价待完成')
                text = text.replace('2E有限渲染/技术交付完成、人工试听pending', '2E有限渲染/技术交付完成、抱K3局部偏好已绑定，其余听觉待评价')
                text = text.replace('下一工作为本批2E人工试听及反馈绑定；', '下一工作为本批2E其余人工试听及反馈绑定（抱K3局部偏好已记录；只214、细项与成对/混音反馈待明确）；')
            elif name == 'plan-table2.md':
                text = text.replace('人工试听pending；2F–2H未执行', '抱K3局部偏好已绑定，其余听觉待评价；2F–2H未执行')
                text = text.replace('人工试听pending，2F–2H未执行', '抱K3局部偏好已绑定，其余听觉待评价，2F–2H未执行')
        updates[path] = text

    RUN.mkdir(parents=True)
    snapshots = []
    for name in ENTRIES + [r['path'] for r in seal['documents']]:
        source = ROOT / name
        dest = RUN / 'before' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(source.read_bytes())
        assert sha(dest) == sha(source)
        snapshots.append(dict(**ref(source), snapshot=dest.relative_to(ROOT).as_posix()))
    save(RUN / 'before/snapshot-manifest.json', dict(files=snapshots))
    record = dict(
        schema_version=1, feedback_id='T2E-W225-K3-20261011',
        status='partial_human_feedback_recorded', stage_2E_complete=False,
        record_created_utc=datetime.now(timezone.utc).isoformat(),
        user_message_verbatim='k3最好', user_message_timestamp='unknown',
        message_source='human user in current chat, replying to four embedded 抱 full-context mono vocal files',
        condition_id='current-word-225', lyric='抱', presented_audio=audio,
        preferred_code='K3', preferred_research_path='S',
        preference_scope='ordinal preference within the four presented versions; actual listened set not separately enumerated',
        other_versions_order='unknown', pairwise_discrimination_results='unknown',
        auditory_details={k: 'unknown' for k in ('onset', 'break_or_crack', 'loudness', 'diction', 'body', 'naturalness', 'absolute_usability')},
        listening_metadata={k: 'unknown' for k in ('device', 'player', 'volume', 'actual_order', 'repetitions', 'complete_four_file_listening', 'blinding')},
        still_pending=['current-word-214', 'explicit fixed-pair feedback', 'mixed-audio feedback', 'specific auditory dimensions'],
        inference_boundary='Local preference for S; no unique causal mechanism, universal rule, held-out validation or whole-song acceptance',
        historical_relation='Technical audit found new 抱 S fresh input/prediction/raw PCM identical to old 抱 C; old C-B 可以 remains a separate feedback event',
        experiment_seal=ref(seal_path), packaging=ref(EXPERIMENT / 'pcm-packaging.json'),
        protocol=ref(OUT / 'validation-protocols/shfc-path-separation-v1.json'),
        pre_update_snapshot=ref(RUN / 'before/snapshot-manifest.json'),
        protected_baseline=baseline_binding,
        new_feedback=1, new_waveforms=0, new_model_calls=0,
        agent_heard=False, measurement_validated=False, general_rule_validated=False,
        production_song_changed=False, skill_changed=False, automatic_expansion=False,
        recorder=ref(Path(__file__).resolve()))
    save(RUN / 'feedback.json', record)
    save(outputs[0], record)
    rows = '\n'.join(f"| {a['code']} | {a['research_path']} | `{a['sha256']}` |" for a in audio)
    report = f'''# 2E抱225局部人工反馈

2026-10-11。状态partial_human_feedback_recorded，2E整体未完成。

用户原话：**k3最好**。消息紧接四份独立完整上下文“抱”人声K1–K4交付，记录为该呈现集合中的K3偏好。K3对应S完整SHFC路径，固定剂量−400c及145ms进入/55ms退出。其他三版之间的排序及逐对可辨性未获得明确反馈。

| 呈现编码 | 冻结研究路径 | 原交付完整单声道人声SHA256 |
|---|---|---|
{rows}

字头、破音、响度、咬字、字腹、自然度及绝对可用性均未细分评价；实际听过的文件集合、顺序、重复次数、设备、播放器、音量及盲听程度未知。本次不将排序补写为“完全无破音”或整曲验收。“只214”、混音和固定成对对照仍待明确反馈。

技术封存曾核查新抱S与旧抱C的fresh输入、预测及raw PCM精确相同；旧C-B“可以”和本次四版本排序为分别保存的反馈事件。本条只支持当前条件/剂量/呈现下S被选为最佳，不宣布单通道病因或通用调参规律。全部measurement_validated仍false。

本轮新反馈1、新模型调用0、新波形0；原歌曲、既有音频、Skill、安装与封存run不改。484运行文件和4份技术报告逐字节SHA重查，79生产/Skill/工程及67保护输入SHA保持。更新前6份当前入口与4份技术报告原字节保存至新反馈run，技术报告原先pending时态保留。

结构记录见[JSON]({NAME}.json)，本轮核查见[审计]({NAME}-audit.json)。原技术报告见[2E实际执行](table2-stage-2e-execution.md)，协议见[路径分离](validation-protocols/shfc-path-separation-v1.md)。下一步继续同批剩余试听/反馈，不增加条件、剂量或波形，不进入2F–2H。
'''
    with outputs[1].open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(report)
    for path, text in updates.items():
        path.write_text(text, encoding='utf-8', newline='\n')

    # Gate includes the new audit filename; the final content then replaces only this new placeholder.
    save(outputs[2], dict(status='checking'))
    result = subprocess.run([sys.executable, str(ROOT / 'tools/repository/check_repository.py'), '--worktree'],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    (RUN / 'worktree-gate.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
    check_refs(seal['files'] + seal['documents'] + protection + audio)
    for row in snapshots:
        assert sha(ROOT / row['snapshot']) == row['sha256']
    assert outputs[0].read_bytes() == (RUN / 'feedback.json').read_bytes()
    assert load(outputs[0])['user_message_verbatim'] == 'k3最好'
    links = 0
    for path in list(updates) + [outputs[1]]:
        for match in re.finditer(r'\]\(([^\s)]+)\)', path.read_text(encoding='utf-8')):
            target = match.group(1)
            if '://' in target or target.startswith('#'):
                continue
            assert (path.parent / target.split('#')[0]).exists(), (path, target)
            links += 1
    audit = dict(status='passed_partial_human_feedback', date='2026-10-11',
        execution_seal=ref(seal_path), sealed_run_files_SHA=484, sealed_documents_SHA=4,
        production_skill_project_SHA=79, protected_inputs_SHA=67,
        presented_full_vocal_SHA=4, snapshot_files_SHA=10,
        feedback=ref(outputs[0]), report=ref(outputs[1]),
        current_entries=[ref(ROOT / name) for name in ENTRIES],
        worktree_gate=dict(passed=True, log=ref(RUN / 'worktree-gate.txt')),
        current_markdown_links_checked=links, new_feedback=1,
        new_waveforms=0, new_model_calls=0, agent_heard=False,
        stage_2E_complete=False, measurement_validated=False, CI_manual_only=True)
    outputs[2].write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save(RUN / 'audit.json', audit)
    save(RUN / 'completion-manifest.json', dict(
        status='sealed_partial_human_feedback',
        files=[ref(p) for p in sorted(RUN.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in outputs], current_entries=audit['current_entries']))
    print(json.dumps(dict(status=audit['status'], preferred='current-word-225 K3=S',
                         sealed_run_files_SHA=484, protected_inputs_SHA=67,
                         new_feedback=1, new_waveforms=0, links_checked=links), ensure_ascii=False))


if __name__ == '__main__':
    main()
