"""Explicit historical registry -> configured current install byte check."""
import json
from pathlib import Path

from freeze_stage_2d import ROOT, HERE, OUT, sha, load
from agent2utau.resources.config import load_config


def resolve_registry(registry, expected, install_root):
    core_paths = [Path(p) for p in registry if Path(p).name == 'OpenUtau.Core.dll']
    if len(core_paths) != 1 or core_paths[0].parent.resolve() != install_root.resolve():
        raise ValueError('Historical registry and explicitly configured install differ')
    resolved = {}
    for name, digest in registry.items():
        path = Path(name).resolve()
        if not path.is_relative_to(install_root.resolve()):
            raise ValueError('Registry resource outside declared installation')
        alias = 'external-resource/OpenUtau/' + path.relative_to(install_root.resolve()).as_posix()
        if alias in resolved or expected.get(alias) != digest:
            raise ValueError('Registry identity/SHA differs from sealed protocol')
        resolved[alias] = path
    if set(resolved) != set(expected):
        raise ValueError('Incomplete runtime registry')
    return resolved


def main():
    binding = load(HERE / 'stage_2e_prep_baseline_binding.json')
    run = ROOT / binding['run']
    target = run / 'runtime-byte-check.json'
    assert not target.exists(), 'Preserve prior byte-check output'
    protocol = load(OUT / 'validation-protocols/shfc-path-separation-v1.json')
    name = 'runs/lastpage_brec_cohort_probe_20261008/frozen_runtime.json'
    ref = next(r for r in load(OUT / 'response-source-audit.json')['source_files'] if r['path'] == name)
    assert sha(ROOT / name) == ref['sha256']
    registry = load(ROOT / name)
    root = Path(load_config()['openutau_dir'])
    resolved = resolve_registry(registry, protocol['fixed']['runtime_expected_hashes'], root)
    rows = []
    for alias, path in resolved.items():
        expected = protocol['fixed']['runtime_expected_hashes'][alias]
        actual = sha(path) if path.is_file() else None
        rows.append(dict(path=alias, expected_sha256=expected, actual_sha256=actual,
            status='missing' if actual is None else 'exact' if actual == expected else 'changed'))
    assert sha(ROOT / name) == ref['sha256']
    result = dict(stage='2E-prep', role='current installed bytes only; no model loading or engine execution',
        locator_source=ref, configured_install_matches_registry=True,
        configuration_bindings=[dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)) for p in
            [ROOT / 'configs/defaults.yaml', ROOT / 'configs/local.yaml'] if p.exists()],
        rows=rows, counts={s: sum(r['status'] == s for r in rows) for s in ['exact', 'changed', 'missing']},
        actual_model_execution=False, current_branch_or_speaker_execution_verified=False)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
