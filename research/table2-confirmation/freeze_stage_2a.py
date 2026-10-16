"""Freeze explicit post-F document inputs; never copy audio or run arrays."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
SNAP = OUT / 'history/pre-table2-2a-20261010'
BINDING = HERE / 'stage_2a_baseline_binding.json'
DOCUMENTS = [
    'conditional-responses.csv', 'conditional-responses.json', 'conditional-responses.md',
    'response-coverage.csv', 'response-source-audit.json', 'id-migration.json',
    'knowledge-table.json', 'control-details.json', 'measurement-protocols.json',
    'context-schema.json', 'table1-consolidation.json', 'table1-execution-audit.json', 'README.md',
]
ADDITIONAL_SOURCES = [
    'runs/lastpage_tenc_probe_20261008/frozen_dependencies.json',
    'runs/lastpage_tenc_feedback_20261008/user_feedback.json',
    'runs/lastpage_shfc_probe_20261008/frozen_runtime.json',
    'runs/lastpage_shfc_artifact_audit_20261008/feedback.json',
    'runs/lastpage_shfc_artifact_audit_20261008/audit.json',
    'runs/lastpage_shfc_artifact_audit_20261008/completion_manifest.json',
    'runs/lastpage_shfc_onset_probe_20261008/frozen_runtime.json',
    'runs/lastpage_shfc_onset_probe_20261008/native_isolation.json',
    'runs/lastpage_guo_register_probe_20261008/frozen_runtime.json',
    'runs/lastpage_guo_register_probe_20261008/native_isolation.json',
    'runs/lastpage_guo_positive_comparison_20261008/comparison.json',
    'runs/lastpage_guo_positive_comparison_20261008/feedback.json',
    'runs/lastpage_guo_positive_comparison_20261008/completion_manifest.json',
    'runs/lastpage_guo_phoneme_audit_20261008/audit.json',
    'runs/lastpage_guo_phoneme_audit_20261008/comparison.json',
    'runs/lastpage_guo_phoneme_audit_20261008/completion_manifest.json',
]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    args = ap.parse_args()
    run = args.run.resolve()
    assert run.is_relative_to(ROOT / 'runs/research') and not run.exists()
    assert not SNAP.exists() and not BINDING.exists(), 'Existing freeze must not be replaced'
    formal = load(OUT / 'table1-consolidation.json')
    assert formal['status'] == 'consolidated_with_explicit_gaps'
    for ref in formal['artifacts']:
        assert sha(ROOT / ref['path']) == ref['sha256'], ref['path']
    original_sources = load(OUT / 'response-source-audit.json')['source_files']
    sources = []
    for ref in original_sources:
        path = ROOT / ref['path']
        got = sha(path) if path.is_file() else None
        assert got is None or got == ref['sha256'], ref['path']
        sources.append(dict(**ref, available_at_freeze=got is not None, origin='original_table2_source_audit'))
    registered = {r['path'] for r in sources}
    for name in ADDITIONAL_SOURCES:
        assert name not in registered
        path = ROOT / name
        sources.append(dict(path=name, sha256=sha(path) if path.is_file() else None,
            available_at_freeze=path.is_file(), origin='existing_source_newly_bound_by_2A_not_new_execution'))
    targets = [OUT / name for name in DOCUMENTS] + [ROOT / name for name in ['AGENTS.md', 'README.md', 'plan.md', 'plan-table2.md']]
    entries = []
    for path in targets:
        destination = SNAP / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
        assert sha(destination) == sha(path)
        entries.append(dict(path=path.relative_to(ROOT).as_posix(), snapshot_path=destination.relative_to(ROOT).as_posix(), sha256=sha(path)))
    manifest = dict(date='2026-10-10', stage='2A', status='frozen_before_record_audit',
        files=entries, source_files=sources, record_counts=dict(responses=10, observations=2, audits=2),
        no_audio_model_array_copies=True, old_runs_and_original_reports_unchanged=True,
        snapshot_link_resolution='Interpret archived document links at their original path; exact archived bytes not rewritten.')
    manifest_path = SNAP / 'snapshot-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    binding = dict(manifest_path=manifest_path.relative_to(ROOT).as_posix(), manifest_sha256=sha(manifest_path))
    BINDING.write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    (run / 'observations').mkdir(parents=True)
    (run / 'logs').mkdir()
    (run / 'observations/freeze-binding.json').write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='frozen', documents=len(entries), sources=len(sources), unavailable=sum(not r['available_at_freeze'] for r in sources))))


if __name__ == '__main__':
    main()
