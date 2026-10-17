"""Freeze 2D and entry documents before research-interface work."""
import argparse
import json
from pathlib import Path

from freeze_stage_2d import ROOT, HERE, OUT, load, sha

BINDING = HERE / 'stage_2e_prep_baseline_binding.json'
SNAP = OUT / 'history/pre-table2-2e-prep-20261010'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    run = ap.parse_args().run.resolve()
    assert not BINDING.exists() and not SNAP.exists(), 'Existing freeze must not be replaced'
    assert not run.exists() and run.is_relative_to(ROOT / 'runs/research')
    audit = load(OUT / 'table2-stage-2d-audit.json')
    assert audit['protocol_sealed'] and audit['local_verification']['status'] == 'passed'
    for r in audit['artifacts'] + audit['current_entry_and_code_bindings']:
        assert sha(ROOT / r['path']) == r['sha256'], r['path']
    names = list(dict.fromkeys([r['path'] for r in audit['artifacts'] + audit['current_entry_and_code_bindings']] + [
        (OUT / 'table2-stage-2d-audit.json').relative_to(ROOT).as_posix(),
        (OUT / 'conditional-responses.json').relative_to(ROOT).as_posix(),
        (OUT / 'measurement-protocols.json').relative_to(ROOT).as_posix(),
        'src/agent2utau/evaluation/controlled_probe.py',
        'src/agent2utau/expression/variance_expectation.py', 'tests/contracts/test_controlled_probe.py']))
    refs = []
    for name in names:
        dest = SNAP / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / name).read_bytes())
        refs.append(dict(path=name, snapshot=dest.relative_to(ROOT).as_posix(), sha256=sha(dest)))
    protected = load(ROOT / 'research/table1-confirmation/protected-inputs.json')['files']
    for r in protected:
        assert sha(ROOT / r['path']) == r['sha256']
    code = []
    for folder in ['src', 'bridge/OuBridge', 'skills', 'projects/latest']:
        for p in sorted((ROOT / folder).rglob('*')):
            if p.is_file() and not any(x in p.parts for x in ['__pycache__', 'bin', 'obj']):
                code.append(dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)))
    m = SNAP / 'snapshot-manifest.json'
    m.write_text(json.dumps(dict(stage='2E-prep', files=refs, protected_inputs=protected,
        production_skill_project_bindings=code, role='pre-research-interface baseline; no audio/arrays/model copies'),
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    run.mkdir(parents=True)
    (run / 'logs').mkdir()
    # Repository convention keeps all test fixtures out of production/research input directories.
    test_run = ROOT / 'runs/test-results/table2-2e-prep-20261010'
    assert not test_run.exists()
    test_run.mkdir(parents=True)
    (test_run / 'temp').mkdir()
    BINDING.write_text(json.dumps(dict(stage='2E-prep', manifest=m.relative_to(ROOT).as_posix(), sha256=sha(m),
        run=run.relative_to(ROOT).as_posix(), test_run=test_run.relative_to(ROOT).as_posix()), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(documents=len(refs), production_skill_project_files=len(code), protected=67)))


if __name__ == '__main__':
    main()
