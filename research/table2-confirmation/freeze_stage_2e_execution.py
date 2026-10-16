"""Freeze the passed native preflight before the explicitly authorized batch."""
import json
from freeze_stage_2d import ROOT, HERE, OUT, load, sha

BINDING = HERE / 'stage_2e_execution_baseline_binding.json'
SNAP = OUT / 'history/pre-table2-2e-execution-20261011'

def main():
    run = ROOT / 'runs/experiments/table2-shfc-paths-20261011'
    test = ROOT / 'runs/test-results/table2-2e-execution-20261011'
    assert not any(p.exists() for p in (BINDING, SNAP, run, test))
    audit_path = OUT / 'table2-stage-2e-native-audit.json'
    audit = load(audit_path)
    assert audit['status'] == 'passed_with_explicit_execution_gaps'
    assert audit['local_tests'] == 143 and audit['execution']['acoustic_vocoder_waveforms'] == 0
    rows = audit['artifacts'] + audit['entry_and_code_bindings']
    for r in rows:
        assert sha(ROOT / r['path']) == r['sha256'], r['path']
    baseline = load(ROOT / audit['baseline']['manifest'])
    for r in baseline['production_skill_project_bindings'] + baseline['protected_inputs']:
        assert sha(ROOT / r['path']) == r['sha256'], r['path']
    names = [r['path'] for r in rows] + [audit_path.relative_to(ROOT).as_posix()]
    names += [p.relative_to(ROOT).as_posix() for p in HERE.glob('shfc_*.py')]
    names += ['research/table2-confirmation/check_stage_2e_native.py',
              'research/table2-confirmation/build_stage_2e_native.py']
    refs = []
    for name in dict.fromkeys(names):
        p, dest = ROOT / name, SNAP / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        assert sha(dest) == sha(p)
        refs.append(dict(path=name, snapshot=dest.relative_to(ROOT).as_posix(), sha256=sha(p)))
    manifest = SNAP / 'snapshot-manifest.json'
    manifest.write_text(json.dumps(dict(stage='2E-execution', date='2026-10-11', files=refs,
        authorization=dict(user_text='可以，继续下一步', approved_scope='冻结协议16套实验对照，技术检查后人工试听；原歌曲、既有音频及Skill保持'),
        production_skill_project_bindings=baseline['production_skill_project_bindings'],
        protected_inputs=baseline['protected_inputs']), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (run / 'logs').mkdir(parents=True)
    (test / 'temp').mkdir(parents=True)
    BINDING.write_text(json.dumps(dict(stage='2E-execution', manifest=manifest.relative_to(ROOT).as_posix(),
        sha256=sha(manifest), run=run.relative_to(ROOT).as_posix(), test_run=test.relative_to(ROOT).as_posix()),
        indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(snapshots=len(refs), production=79, protected=67)))

if __name__ == '__main__':
    main()
