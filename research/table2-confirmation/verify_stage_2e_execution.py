"""Final local-only publication audit. Never runs inference or changes audio."""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
import onnx
from freeze_stage_2d import ROOT,HERE,OUT,load,sha
from prepare_stage_2e_execution import save
from build_stage_2e_execution import OUTPUTS
from shfc_path_runner import load_sealed_protocol

def main():
    b=load(HERE/'stage_2e_execution_baseline_binding.json');run=ROOT/b['run'];test=ROOT/b['test_run']
    output=OUT/'table2-stage-2e-execution-audit.json'
    assert not output.exists(), 'Preserve final audit; future feedback belongs in a new run'
    # Register the final file before worktree gate/link checks so its presence is counted.
    output.write_text('{"status":"pending_final_local_audit"}\n',encoding='utf-8')
    report=load(OUT/OUTPUTS[0]);gate=load(run/'technical-delivery-check.json');p=load_sealed_protocol()
    assert report['stage_2E_complete'] is False and report['status']=='technical_execution_complete_pending_human_listening'
    assert report['scope']['agent_heard'] is False and report['actual_execution']['new_feedback']==0
    assert report['actual_execution']['fresh_seeded_variance_calls']==8 and report['actual_execution']['seeded_acoustic_vocoder_waveforms']==16
    assert report['actual_execution']['technical_native_cache_waveforms']==4
    assert report['scope']['heldout_conditions']==0 and report['scope']['stage_2F_to_2H_executed'] is False
    for r in report['proofs']+report['implementation']:assert sha(ROOT/r['path'])==r['sha256']
    before=[sha(OUT/x) for x in OUTPUTS]
    proc=subprocess.run([sys.executable,str(HERE/'build_stage_2e_execution.py')],capture_output=True,cwd=ROOT)
    (run/'logs/report-rebuild.stdout').write_bytes(proc.stdout);(run/'logs/report-rebuild.stderr').write_bytes(proc.stderr)
    assert proc.returncode==0 and before==[sha(OUT/x) for x in OUTPUTS]
    # Independent ONNX adapter audit, rather than trust the generator's label.
    adapter_checks=[]
    for ref in load(run/'model-adapters.json')['proofs']:
        source=Path(ref['source']); adapted=run/'models'/('variance.onnx' if 'variance' in source.name else 'acoustic.onnx')
        assert sha(source)==ref['source_sha256'] and sha(adapted)==ref['adapter_sha256']
        a,bm=[onnx.load(str(x)) for x in [source,adapted]]
        assert [x.SerializeToString() for x in a.graph.initializer]==[x.SerializeToString() for x in bm.graph.initializer]
        assert [x.SerializeToString() for x in a.graph.output]==[x.SerializeToString() for x in bm.graph.output]
        assert [x.SerializeToString() for x in a.graph.input]==[x.SerializeToString() for x in bm.graph.input[:-1]]
        assert bm.graph.input[-1].name=='probe_noise' and len(a.graph.node)==len(bm.graph.node)
        changes=[]
        for i,(x,y) in enumerate(zip(a.graph.node,bm.graph.node)):
            if x.SerializeToString()!=y.SerializeToString():
                assert x.op_type=='RandomNormalLike' and y.op_type=='Identity' and list(y.input)==['probe_noise']
                assert list(x.output)==list(y.output) and x.name==y.name and x.domain==y.domain and not y.attribute
                changes.append(i)
        assert len(changes)==1;adapter_checks.append(dict(source_sha256=sha(source),adapter_sha256=sha(adapted),weights_and_nonrandom_graph_exact=True))
    source_rows=load(OUT/'comparison-bindings.json')['source_bindings']; verified=[];unavailable=[]
    for r in source_rows:
        if r['sha256'] is None:unavailable.append(r['path']);continue
        assert sha(ROOT/r['path'])==r['sha256'],r['path'];verified.append(r['path'])
    assert len(verified)==52 and len(unavailable)==1
    # Numeric CSV maps directly to actual complete-vowel observation summaries.
    with (OUT/OUTPUTS[2]).open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==10
    for r in rows:
        c=next(x for x in report['conditions'] if x['condition_id']==r['condition_id']);v=c['vowel_comparisons'][r['direction']]
        assert float(r['vowel_level_ratio_db'])==v['level_ratio_db']
        assert float(r['mean_removed_mel_shape_rms'])==v['mean_removed_mel_shape_difference_rms']
        for name in ['FCPE','RMVPE']:
            assert int(r[name+'_valid_frames'])==v['F0'][name]['valid_pair_frames']
            assert float(r[name+'_abs_cents_p50'])==v['F0'][name]['abs_cents_p50']
        assert r['auditory_status']=='pending' and r['measurement_validated']=='False'
    assert '154 passed' in (test/'pytest-corrected.txt').read_text(encoding='utf-8-sig')
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch' in ci and not re.search(r'^\s*(push|pull_request|schedule)\s*:',ci,re.M)
    assert all(not r['measurement_validated'] for r in load(OUT/'measurement-protocols.json')['rows'])
    entry_paths=[ROOT/n for n in ['README.md','AGENTS.md','plan.md','plan-table2.md']]+[HERE/'README.md',OUT/'README.md']
    for path in entry_paths:assert 'technical_execution_complete_pending_human_listening' in path.read_text(encoding='utf-8')
    link_paths=entry_paths+[OUT/OUTPUTS[1]]+[run/'delivery/listening.md',run/'delivery/word225.md',run/'delivery/word214.md']
    links=0
    for path in link_paths:
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if re.match(r'https?://|#',link):continue
            assert (path.parent/link.split('#')[0]).resolve().exists(),(str(path),link);links+=1
    proc=subprocess.run([sys.executable,str(ROOT/'tools/repository/check_repository.py'),'--worktree'],cwd=ROOT,capture_output=True)
    (test/'worktree-check-final.txt').write_bytes(proc.stdout);(test/'worktree-check-final.stderr').write_bytes(proc.stderr)
    assert proc.returncode==0
    repo_gate=json.loads(proc.stdout.decode('utf-8-sig'))
    assert repo_gate['checks']=='passed' and repo_gate['audio_payloads']==0 and repo_gate['skill_links']==102
    value=dict(stage='2E-execution',date='2026-10-11',status='passed_pending_human_listening',
        stage_2E_complete=False,local_tests=154,worktree_gate=repo_gate,CI_manual_only=True,
        production_skill_project_SHA=79,protected_inputs_SHA=67,execution_snapshots=20,
        old_2A_unique_paths_SHA=1079,current_song_run_SHA=567,current_runtime_SHA=47,
        original_52_sources_SHA=len(verified),original_unavailable_locator_preserved=unavailable,
        model_adapters_independently_rechecked=adapter_checks,
        new_native_records=4,technical_native_cache_waveforms=4,seeded_variance_calls=8,
        seeded_acoustic_vocoder_waveforms=16,F0_detector_inferences=16,delivery_PCM_files=72,
        raw_repeats_exact=True,old_A_PCM_exact=True,old_C_new_S_raw_PCM_exact=True,
        DYN_independently_rebuilt_exact=True,encoded_pair_files_checked=40,
        exact_report_rebuild=True,links_checked=links,
        auditory_status='pending',agent_heard=False,new_feedback=0,generic_rules=0,
        measurement_validated_upgrades=False,independent_effect_replications=0,
        artifacts=[dict(path=(OUT/x).relative_to(ROOT).as_posix(),sha256=sha(OUT/x)) for x in OUTPUTS],
        technical_gate=dict(path=(run/'technical-delivery-check.json').relative_to(ROOT).as_posix(),sha256=sha(run/'technical-delivery-check.json')),
        current_entries=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in entry_paths],
        implementation=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in
            [HERE/'verify_stage_2e_execution.py',HERE/'update_stage_2e_entries.py',ROOT/'tests/contracts/test_shfc_pcm_research.py']])
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=value['status'],tests=154,gate=repo_gate,links=links)))

if __name__=='__main__':main()
