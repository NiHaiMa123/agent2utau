"""Freeze schema3 and review inputs; no waveform/array/model copies."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'docs/knowledge/acoustic-manifestations-20261009'
SNAP = OUT / 'history/pre-table2-2c-20261010'
BINDING = HERE / 'stage_2c_baseline_binding.json'
NAMES = ['conditional-responses.json', 'conditional-responses.csv', 'conditional-responses.md',
    'table2-record-schema.json', 'table2-schema-migration.json', 'table2-record-structure.csv',
    'table2-fields.md', 'table2-schema-review.md', 'table2-stage-2b-audit.json', 'comparison-bindings.json',
    'response-source-audit.json', 'control-details.json', 'knowledge-table.json', 'measurement-protocols.json',
    'table1-consolidation.json', 'table1-execution-audit.json', 'README.md', 'table2-review.md', 'table2-execution-audit.json']


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    run = ap.parse_args().run.resolve()
    assert run.is_relative_to(ROOT / 'runs/research') and not run.exists()
    assert not SNAP.exists() and not BINDING.exists(), 'Existing freeze must not be replaced'
    audit = load(OUT / 'table2-stage-2b-audit.json')
    assert audit['status'] == 'passed_with_explicit_gaps' and audit['local_verification']['status'] == 'passed'
    for ref in audit['artifacts'] + audit['research_and_current_entry_bindings']:
        assert sha(ROOT / ref['path']) == ref['sha256'], ref['path']
    ledger = load(OUT / 'conditional-responses.json')
    arrays = {}
    for r in ledger['responses']:
        for v in r['record_v3']['variants']:
            for ref in v['state_origin']['artifacts']:
                if ref['path'].endswith('.npz'):
                    assert sha(ROOT / ref['path']) == ref['sha256'], ref['path']
                    arrays[ref['path']] = ref['sha256']
    files = []
    names = ['README.md', 'AGENTS.md', 'plan.md', 'plan-table2.md',
        'research/table2-confirmation/build_stage_2b.py', 'research/table2-confirmation/verify_stage_2b.py',
        'research/table2-confirmation/README.md']
    for p in [OUT / n for n in NAMES] + [ROOT / n for n in names]:
        dest = SNAP / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        assert sha(dest) == sha(p)
        files.append(dict(path=p.relative_to(ROOT).as_posix(), snapshot_path=dest.relative_to(ROOT).as_posix(), sha256=sha(p)))
    manifest = dict(stage='2C', date='2026-10-10', files=files,
        array_inputs=[dict(path=k, sha256=h) for k, h in sorted(arrays.items())],
        array_read_scope='Read-only native/fresh input/prediction isolation; no PCM, mel, detector rerun or model execution',
        no_audio_array_model_copies=True, archived_link_resolution='Use original repository path for archived document links')
    mp = SNAP / 'snapshot-manifest.json'
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    binding = dict(manifest_path=mp.relative_to(ROOT).as_posix(), manifest_sha256=sha(mp))
    BINDING.write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    (run / 'observations').mkdir(parents=True)
    (run / 'logs').mkdir()
    (run / 'observations/freeze-binding.json').write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='frozen', documents=len(files), unique_input_prediction_arrays=len(arrays))))


if __name__ == '__main__':
    main()
