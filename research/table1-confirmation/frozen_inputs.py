"""Resolve an exact pre-F input by registry, not an arbitrary cache fallback."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'docs/knowledge/acoustic-manifestations-20261009'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def original_path(path,expected=None):
    path=Path(path)
    if not path.is_absolute():path=ROOT/path
    binding=HERE/'stage_f_baseline_binding.json'
    if not binding.exists():
        if expected is not None:assert sha(path)==expected
        return path
    data=json.loads(binding.read_text(encoding='utf-8'))
    manifest=ROOT/data['manifest_path'];assert sha(manifest)==data['manifest_sha256']
    entries={r['path']:r for r in data['files']}
    key=path.relative_to(ROOT).as_posix()
    if key not in entries:
        if expected is not None:assert sha(path)==expected
        return path
    r=entries[key]
    if expected is not None:assert expected==r['sha256'],(key,expected)
    snap=ROOT/r['snapshot_path'];assert snap.is_relative_to(OUT/'history/pre-f-20261010')
    assert sha(snap)==r['sha256'],f'Pre-F evidence changed: {key}'
    return snap

def refuse_after_formal_migration():
    if (OUT/'table1-consolidation.json').exists():
        raise SystemExit('A–E are frozen review builders. Rebuild current tables with build_stage_f.py; do not overwrite reviewed/migrated artifacts.')
