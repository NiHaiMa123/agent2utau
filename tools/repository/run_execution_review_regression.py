"""Read-only actual-project review regression; no song-specific IDs or numbers."""
import argparse
import json
from pathlib import Path

from agent2utau.evaluation.execution_review import build_inventory, ref, review_execution, write
from agent2utau.openutau.bridge import run_bridge
from agent2utau.openutau.ustx import load_ustx, sha256
from agent2utau.resources.config import load_config


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--context',type=Path);p.add_argument('--sources',type=Path)
    p.add_argument('--ledger',type=Path);p.add_argument('--plan',type=Path)
    args=p.parse_args();cfg=load_config();project=args.project.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=sha256(project);write(out/'request.json',dict(project=ref(project),readonly=True,model_synthesis=False,fill_missing_decisions=False))
    for command,name in [('export-pitch','pitch'),('export-phonemes','phones')]:
        result=run_bridge(cfg,[command,'--project',str(project),'--out',str(out/(name+'.json'))])
        write(out/(name+'-receipt.json'),result)
        if not result.get('ok'):raise RuntimeError('Native export failed; prior project preserved')
    doc=load_ustx(project);ou=Path(cfg['openutau_dir']);singer=doc['tracks'][0]['singer']
    env=dict(core_sha256=sha256(ou/'OpenUtau.Core.dll'),bridge_sha256=sha256(ou/'a2u-bridge.exe'),singer_id=singer,singer_config_sha256=sha256(ou/'Singers'/singer/'dsconfig.yaml'))
    write(out/'provenance.json',dict(schema_version=1,project_sha256=before,pitch_sha256=sha256(out/'pitch.json'),phonemes_sha256=sha256(out/'phones.json'),environment=env))
    inv=build_inventory(project,out/'inventory.json',out/'pitch.json',out/'phones.json',out/'provenance.json',args.context,args.sources)
    result=review_execution(project,out/'inventory.json',out/'review',out/'pitch.json',out/'phones.json',out/'provenance.json',args.ledger,args.plan)
    if sha256(project)!=before:raise RuntimeError('Read-only regression unexpectedly changed the project')
    summary=dict(actual_units=inv['denominator'],native_stage=result['native_stage'],technical_execution_complete=result['technical_execution_complete'],workflow_review_complete=result['workflow_review_complete'],musical_quality=result['musical_review']['musical_quality'],musical_review_status=result['musical_review']['status'],execution_complete=result['production_execution_complete'],local_visual_review=result['local_visual_review'],
                 inventory_status=result['inventory_coverage']['status'],choice_review=result['choice_review']['status'],reference_scope=result['reference_sources'],
                 project_SHA_preserved=True,audio_synthesized=False,retrospective_decisions_invented=False)
    write(out/'regression-summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='local_visual_review'},ensure_ascii=False))


if __name__=='__main__':main()
