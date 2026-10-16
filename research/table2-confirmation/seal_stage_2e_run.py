"""One-time manifest of the new technical batch. Future feedback is separate."""
from freeze_stage_2d import ROOT,HERE,OUT,load,sha
from prepare_stage_2e_execution import save

def main():
    run=ROOT/load(HERE/'stage_2e_execution_baseline_binding.json')['run']
    target=run/'completion-manifest.json';assert not target.exists()
    audit=load(OUT/'table2-stage-2e-execution-audit.json');assert audit['status']=='passed_pending_human_listening'
    refs=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in sorted(run.rglob('*')) if p.is_file() and p!=target]
    documents=[OUT/n for n in ['table2-stage-2e-execution.json','table2-stage-2e-execution.md',
        'table2-stage-2e-execution-comparisons.csv','table2-stage-2e-execution-audit.json']]
    save(target,dict(stage='2E-execution',status='sealed_pending_human_listening',files=refs,
        documents=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in documents],
        agent_heard=False,auditory_status='pending',new_feedback=0,seeded_waveforms=16,
        technical_native_cache_waveforms=4,automatic_expansion=False,
        generator=dict(path=(HERE/'seal_stage_2e_run.py').relative_to(ROOT).as_posix(),sha256=sha(HERE/'seal_stage_2e_run.py'))))
    print(dict(files=len(refs),manifest=target.relative_to(ROOT).as_posix(),sha256=sha(target)))

if __name__=='__main__':main()
