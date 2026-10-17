"""Append scoped vocal/mix feedback without rewriting the sealed v1 recorder."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from record_stage_2e_word225_feedback import ENTRIES, EXPERIMENT, ROOT, HERE, OUT, ref, save, check_refs


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    assert len(sys.argv) == 2, 'Supply the explicit feedback specification'
    spec_path = (ROOT / sys.argv[1]).resolve()
    assert spec_path.is_relative_to(HERE)
    spec = load(spec_path)
    run = ROOT / 'runs/research' / spec['run_name']
    outputs = [OUT / (spec['document_name'] + s) for s in ('.json', '.md', '-audit.json')]
    assert not run.exists() and not any(p.exists() for p in outputs), 'Already recorded'
    experiment_seal_path = EXPERIMENT / 'completion-manifest.json'
    assert ref(experiment_seal_path)['sha256'] == 'c3e55742a78a1c57bab2fa34943a2379bab5d16e6ebb1b57aa7cf15db9fddf85'
    previous = [ROOT / 'runs/research' / name for name in spec['previous_feedback_runs']]
    seal_paths = [experiment_seal_path] + [p / 'completion-manifest.json' for p in previous]
    seals = [load(p) for p in seal_paths]
    immutable = [r for seal in seals for r in seal['files'] + seal['documents']]
    check_refs(immutable)
    binding = load(HERE / 'stage_2e_execution_baseline_binding.json')
    assert ref(ROOT / binding['manifest'])['sha256'] == binding['sha256']
    baseline = load(ROOT / binding['manifest'])
    protection = baseline['production_skill_project_bindings'] + baseline['protected_inputs']
    check_refs(protection)
    package_path = EXPERIMENT / 'pcm-packaging.json'
    package = load(package_path)
    audio = []
    for request in spec['presented_pairs']:
        pair = next(p for p in package['pairs'] if p['condition_id'] == request['condition_id'] and p['order'] == request['order'])
        assert pair['codes'] == request['codes'] and pair['direction'] == request['direction']
        role = request['role']
        assert role in ('vocal', 'mix')
        meta = next(f for f in package['files'] if f['path'] == pair[role])
        assert meta['channels'] == (1 if role == 'vocal' else 2) and meta['subtype'] == 'PCM_24'
        audio.append(dict(presentation=pair, delivery_role=role, **meta))
    check_refs(audio)
    updates = {}
    for name in ENTRIES:
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        old = next(line for line in text.splitlines() if '2E当前状态partial_human_feedback_recorded：' in line)
        link = Path(os.path.relpath(outputs[1], path.parent)).as_posix()
        text = text.replace(old, ('- ' if old.startswith('- ') else '') + spec['current_status'] + f' 见[最新成对反馈]({link})。', 1)
        for before, after in spec['entry_replacements']:
            text = text.replace(before, after)
        updates[path] = text
    run.mkdir(parents=True)
    snapshots = []
    for name in ENTRIES + [r['path'] for seal in seals[1:] for r in seal['documents']]:
        source = ROOT / name
        dest = run / 'before' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(source.read_bytes())
        assert ref(dest)['sha256'] == ref(source)['sha256']
        snapshots.append(dict(**ref(source), snapshot=dest.relative_to(ROOT).as_posix()))
    save(run / 'before/snapshot-manifest.json', dict(files=snapshots))
    record = dict(spec['record'],
        schema_version=1, status='partial_human_feedback_recorded', stage_2E_complete=False,
        record_created_utc=datetime.now(timezone.utc).isoformat(), user_message_timestamp='unknown',
        presented_audio=audio, preserved_feedback=[ref(p / 'feedback.json') for p in previous],
        source_seals=[ref(p) for p in seal_paths], packaging=ref(package_path),
        protocol=ref(OUT / 'validation-protocols/shfc-path-separation-v1.json'),
        pre_update_snapshot=ref(run / 'before/snapshot-manifest.json'), protected_baseline=binding,
        this_record_new_feedback=1, new_waveforms=0, new_model_calls=0, agent_heard=False,
        measurement_validated=False, general_rule_validated=False, production_song_changed=False,
        skill_changed=False, automatic_expansion=False,
        recorder=ref(Path(__file__).resolve()), explicit_feedback_specification=ref(spec_path),
        preserved_v1_recorder=ref(HERE / 'record_stage_2e_feedback_supplement.py'))
    save(run / 'feedback.json', record)
    save(outputs[0], record)
    rows = '\n'.join(f"| {a['presentation']['order']:02d} | {'→'.join(a['presentation']['codes'])} | {a['delivery_role']} / {a['channels']}通道 | `{a['sha256']}` |" for a in audio)
    report = spec['report_text'] + '\n\n| 呈现 | 顺序 | 交付角色 | 已封存成对音频SHA256 |\n|---|---|---|---|\n' + rows
    report += f"\n\n[JSON]({spec['document_name']}.json) · [审计]({spec['document_name']}-audit.json) · [冻结协议](validation-protocols/shfc-path-separation-v1.md)。\n"
    with outputs[1].open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(report)
    for path, text in updates.items():
        path.write_text(text, encoding='utf-8', newline='\n')
    save(outputs[2], dict(status='checking'))
    gate = subprocess.run([sys.executable, str(ROOT / 'tools/repository/check_repository.py'), '--worktree'],
                          cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    (run / 'worktree-gate.txt').write_text(gate.stdout + gate.stderr, encoding='utf-8')
    assert gate.returncode == 0, gate.stdout + gate.stderr
    check_refs(immutable + protection + audio)
    for row in snapshots:
        assert ref(ROOT / row['snapshot'])['sha256'] == row['sha256']
    assert outputs[0].read_bytes() == (run / 'feedback.json').read_bytes()
    assert load(outputs[0])['user_message_verbatim'] == spec['record']['user_message_verbatim']
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
    audit = dict(status='passed_partial_human_feedback', date=spec['date'], source_seals=[ref(p) for p in seal_paths],
        sealed_experiment_files_SHA=len(seals[0]['files']), sealed_experiment_documents_SHA=len(seals[0]['documents']),
        previous_feedback_files_SHA=sum(len(s['files']) for s in seals[1:]),
        previous_feedback_documents_SHA=sum(len(s['documents']) for s in seals[1:]),
        production_skill_project_SHA=len(baseline['production_skill_project_bindings']),
        protected_inputs_SHA=len(baseline['protected_inputs']), presented_pair_audio_SHA=len(audio),
        snapshot_files_SHA=len(snapshots), current_markdown_links_checked=links,
        feedback=ref(outputs[0]), report=ref(outputs[1]), current_entries=[ref(ROOT / p) for p in ENTRIES],
        worktree_gate=json.loads(gate.stdout), worktree_gate_log=ref(run / 'worktree-gate.txt'),
        this_record_new_feedback=1, cumulative_new_feedback=record['cumulative_new_feedback'],
        new_waveforms=0, new_model_calls=0, stage_2E_complete=False,
        agent_heard=False, measurement_validated=False, CI_manual_only=True)
    outputs[2].write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save(run / 'audit.json', audit)
    save(run / 'completion-manifest.json', dict(status='sealed_partial_human_feedback',
        files=[ref(p) for p in sorted(run.rglob('*')) if p.is_file()],
        documents=[ref(p) for p in outputs], current_entries=audit['current_entries']))
    print(json.dumps(dict(status=audit['status'], verbatim=record['user_message_verbatim'],
        feedback_count=record['cumulative_new_feedback'], new_waveforms=0,
        worktree_gate=audit['worktree_gate']), ensure_ascii=False))


if __name__ == '__main__':
    main()
