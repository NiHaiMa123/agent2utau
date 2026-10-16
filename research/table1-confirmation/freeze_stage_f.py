"""Preserve portable pre-migration knowledge bytes; never copies audio/runs."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/knowledge/acoustic-manifestations-20261009'
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dest=OUT/'history/pre-f-20261010'
    assert not dest.exists() and not (HERE/'stage_f_baseline_binding.json').exists()
    audit=json.loads((OUT/'table1-execution-audit.json').read_text(encoding='utf-8'))
    assert audit['stage_E']=='coverage_review_complete_with_explicit_gaps' and audit['stage_F']=='not_executed'
    dest.mkdir(parents=True)
    rows=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.suffix in {'.json','.csv','.md'}:
            q=dest/p.name;q.write_bytes(p.read_bytes())
            assert sha(p)==sha(q)
            rows.append(dict(path=p.relative_to(ROOT).as_posix(),snapshot_path=q.relative_to(ROOT).as_posix(),sha256=sha(q)))
    manifest=dict(date='2026-10-10',role='immutable_pre_F_bytes_not_active_plan',files=rows,
        original_links_resolve_from_original_path=True,no_audio_projects_models_or_skill_copied=True)
    (dest/'snapshot-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    binding=dict(schema_version=1,manifest_path=(dest/'snapshot-manifest.json').relative_to(ROOT).as_posix(),
        manifest_sha256=sha(dest/'snapshot-manifest.json'),files=rows)
    (HERE/'stage_f_baseline_binding.json').write_text(json.dumps(binding,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='pre_F_snapshot_bound',files=len(rows),manifest_sha256=binding['manifest_sha256'])))

if __name__=='__main__':main()
