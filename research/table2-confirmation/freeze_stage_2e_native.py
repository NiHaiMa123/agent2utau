"""Preserve interface-prep audit before actual native/static integration checks."""
import json
from freeze_stage_2d import ROOT, HERE, OUT, load, sha

BINDING = HERE / 'stage_2e_native_baseline_binding.json'
SNAP = OUT / 'history/pre-table2-2e-native-20261010'


def main():
    run = ROOT / 'runs/research/table2-2e-native-check-20261010'
    test_run = ROOT / 'runs/test-results/table2-2e-native-20261010'
    assert not any(p.exists() for p in (BINDING, SNAP, run, test_run)), 'Existing freeze must not be replaced'
    audit = load(OUT / 'table2-stage-2e-prep-audit.json')
    assert audit['local_verification']['status'] == 'passed'
    names = list(dict.fromkeys([r['path'] for r in audit['artifacts'] + audit['entry_and_code_bindings']]))
    for r in audit['artifacts'] + audit['entry_and_code_bindings']:
        assert sha(ROOT / r['path']) == r['sha256'], r['path']
    names += [(OUT / 'table2-stage-2e-prep-audit.json').relative_to(ROOT).as_posix()]
    baseline = load(ROOT / audit['baseline']['manifest'])
    for r in baseline['production_skill_project_bindings'] + baseline['protected_inputs']:
        assert sha(ROOT / r['path']) == r['sha256']
    refs = []
    for name in names:
        dest = SNAP / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / name).read_bytes())
        refs.append(dict(path=name, snapshot=dest.relative_to(ROOT).as_posix(), sha256=sha(dest)))
    manifest = SNAP / 'snapshot-manifest.json'
    manifest.write_text(json.dumps(dict(stage='2E-native', files=refs,
        production_skill_project_bindings=baseline['production_skill_project_bindings'],
        protected_inputs=baseline['protected_inputs']), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (run / 'logs').mkdir(parents=True)
    (test_run / 'temp').mkdir(parents=True)
    BINDING.write_text(json.dumps(dict(stage='2E-native', manifest=manifest.relative_to(ROOT).as_posix(),
        sha256=sha(manifest), run=run.relative_to(ROOT).as_posix(), test_run=test_run.relative_to(ROOT).as_posix()),
        indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(snapshots=len(refs), production=79, protected=67)))


if __name__ == '__main__':
    main()
