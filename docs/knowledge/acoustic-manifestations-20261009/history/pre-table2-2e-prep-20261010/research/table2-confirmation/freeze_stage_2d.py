"""Freeze 2C documents before gap/protocol design; never copy arrays/audio."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
SNAP = OUT / 'history/pre-table2-2d-20261010'
BINDING = HERE / 'stage_2d_baseline_binding.json'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    run = ap.parse_args().run.resolve()
    assert not SNAP.exists() and not BINDING.exists(), 'Existing freeze must not be replaced'
    assert run.is_relative_to(ROOT / 'runs/research') and not run.exists()
    audit = load(OUT / 'table2-stage-2c-audit.json')
    assert audit['status'] == 'passed_with_explicit_gaps' and audit['local_verification']['status'] == 'passed'
    for r in audit['artifacts'] + audit['current_entry_and_code_bindings']:
        assert sha(ROOT / r['path']) == r['sha256'], r['path']
    names = [r['path'] for r in audit['artifacts']] + [
        (OUT / n).relative_to(ROOT).as_posix() for n in [
            'table2-stage-2c-audit.json', 'control-details.json', 'knowledge-table.json',
            'measurement-protocols.json', 'comparison-bindings.json', 'response-source-audit.json',
            'README.md']]
    names += ['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md',
        'research/table2-confirmation/build_stage_2c.py',
        'research/table2-confirmation/verify_stage_2c.py', 'research/table2-confirmation/README.md']
    refs = []
    for name in dict.fromkeys(names):
        p = ROOT / name
        dest = SNAP / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        assert sha(dest) == sha(p)
        refs.append(dict(path=name, snapshot=dest.relative_to(ROOT).as_posix(), sha256=sha(p)))
    sources = [ROOT / 'src/agent2utau/evaluation/controlled_probe.py',
        ROOT / 'docs/lastpage-brec-cohort-probe-20261008.md',
        ROOT / 'docs/lastpage-cross-condition-study-20261008.md',
        ROOT / 'docs/lastpage-shfc-onset-probe-20261008.md']
    source_refs = [dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)) for p in sources]
    manifest = dict(stage='2D', date='2026-10-10', files=refs, design_source_bindings=source_refs,
        role='pre-design documents; no new audio, model, native execution or feedback')
    m = SNAP / 'snapshot-manifest.json'
    m.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    run.mkdir(parents=True)
    (run / 'logs').mkdir()
    (run / 'temp').mkdir()
    binding = dict(stage='2D', manifest=m.relative_to(ROOT).as_posix(), sha256=sha(m),
        run=run.relative_to(ROOT).as_posix())
    BINDING.write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='frozen', documents=len(refs), sources=len(source_refs), **binding)))


if __name__ == '__main__':
    main()
