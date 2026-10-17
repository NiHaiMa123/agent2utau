"""Freeze explicitly selected document bytes before the schema migration."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
SNAP = OUT / 'history/pre-table2-2b-20261010'
BINDING = HERE / 'stage_2b_baseline_binding.json'
NAMES = [
    'conditional-responses.json', 'conditional-responses.csv', 'conditional-responses.md',
    'README.md', 'knowledge-table.json', 'control-details.json', 'measurement-protocols.json',
    'response-coverage.csv', 'response-source-audit.json', 'table1-consolidation.json',
    'table1-execution-audit.json', 'comparison-bindings.json', 'comparison-bindings.csv',
    'table2-record-differences.json', 'table2-record-differences.csv', 'table2-review.md',
    'table2-execution-audit.json',
]
SCRIPTS = ['research/table1-confirmation/build_stage_f.py',
    'research/table1-confirmation/build_audit.py',
    'research/table2-confirmation/build_stage_2a.py',
    'research/table2-confirmation/verify_stage_2a.py',
    'research/table2-confirmation/README.md']


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    run = ap.parse_args().run.resolve()
    assert run.is_relative_to(ROOT / 'runs/research') and not run.exists()
    assert not SNAP.exists() and not BINDING.exists(), 'Existing freeze must not be replaced'
    audited = json.loads((OUT / 'comparison-bindings.json').read_text(encoding='utf-8'))
    assert audited['status'] == 'source_binding_audit_complete_with_explicit_gaps'
    files = []
    targets = [OUT / n for n in NAMES] + [ROOT / n for n in SCRIPTS + ['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md']]
    for p in targets:
        dest = SNAP / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        assert sha(dest) == sha(p)
        files.append(dict(path=p.relative_to(ROOT).as_posix(), snapshot_path=dest.relative_to(ROOT).as_posix(), sha256=sha(p)))
    manifest = dict(stage='2B', date='2026-10-10', files=files,
        no_audio_array_or_model_copies=True,
        archived_link_resolution='Resolve links at original repository path; archived bytes are unchanged.')
    mp = SNAP / 'snapshot-manifest.json'
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    binding = dict(manifest_path=mp.relative_to(ROOT).as_posix(), manifest_sha256=sha(mp))
    BINDING.write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    (run / 'observations').mkdir(parents=True)
    (run / 'logs').mkdir()
    (run / 'observations/freeze-binding.json').write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='frozen', documents=len(files))))


if __name__ == '__main__':
    main()
