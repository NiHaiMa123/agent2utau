"""Preparation audit; do not execute real models or rewrite old audits."""
import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

from freeze_stage_2d import ROOT, HERE, OUT, load, sha
from check_stage_2e_runtime import resolve_registry
from agent2utau.resources.config import load_config

OUTPUTS = ['table2-stage-2e-preparation.json', 'table2-stage-2e-preparation.md']
MUTABLE = {'AGENTS.md','README.md','plan.md','plan-table2.md',
    'research/table2-confirmation/README.md','research/table2-confirmation/verify_stage_2d.py',
    (OUT/'README.md').relative_to(ROOT).as_posix()}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--local-checks',action='store_true')
    args=ap.parse_args()
    binding=load(HERE/'stage_2e_prep_baseline_binding.json');run=ROOT/binding['run']
    assert sha(ROOT/binding['manifest'])==binding['sha256']
    snap=load(ROOT/binding['manifest'])
    for r in snap['files']:
        assert sha(ROOT/r['snapshot'])==r['sha256']
        if r['path'] not in MUTABLE:assert sha(ROOT/r['path'])==r['sha256'],r['path']
    for r in snap['production_skill_project_bindings']+snap['protected_inputs']:
        assert sha(ROOT/r['path'])==r['sha256'],r['path']
    assert len(snap['files'])==24 and len(snap['production_skill_project_bindings'])==79 and len(snap['protected_inputs'])==67
    seal=load(HERE/'stage_2d_protocol_binding.json')
    for r in seal['bindings']:assert sha(ROOT/r['path'])==r['sha256']
    report=load(OUT/OUTPUTS[0])
    assert report['stage']=='2E-prep' and not report['stage_2E_complete']
    assert report['validation_scope']==dict(contract_tests=40,synthetic_conditions=2,prepared_mock_acoustic_inputs=16,
        mock_raw_renderer_callback_budget=16,actual_current_native_inputs_or_Q5_sampling_validated=False,
        actual_ONNX_predictor_or_acoustic_or_vocoder_executed=False,real_embeddings_loaded=False,
        actual_output_PCM_or_DYN_or_gain_validated=False,real_waveforms_created=0,new_auditory_feedback=0,
        installed_resource_bytes_rehashed=47,installed_resource_bytes_identical=47)
    for r in report['implementation_bindings']:assert sha(ROOT/r['path'])==r['sha256']
    byte=load(ROOT/report['runtime_binding']['path'])
    assert sha(ROOT/report['runtime_binding']['path'])==report['runtime_binding']['sha256']
    registry_ref=byte['locator_source'];assert sha(ROOT/registry_ref['path'])==registry_ref['sha256']
    protocol=load(OUT/'validation-protocols/shfc-path-separation-v1.json')
    paths=resolve_registry(load(ROOT/registry_ref['path']),protocol['fixed']['runtime_expected_hashes'],
        Path(load_config()['openutau_dir']))
    assert len(paths)==len(byte['rows'])==47 and byte['counts']==dict(exact=47,changed=0,missing=0)
    for r in byte['rows']:
        assert r['status']=='exact' and sha(paths[r['path']])==r['expected_sha256']==r['actual_sha256']
    for r in byte['configuration_bindings']:assert sha(ROOT/r['path'])==r['sha256']
    assert byte['configured_install_matches_registry'] and not byte['actual_model_execution']
    # Source independence: checker imports only numpy and no assembly helpers.
    tree=ast.parse((HERE/'shfc_path_checks.py').read_text(encoding='utf-8'))
    imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
    assert len(imports)==1 and isinstance(imports[0],ast.Import) and imports[0].names[0].name=='numpy'
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    assert all(not r['measurement_validated'] for r in load(OUT/'measurement-protocols.json')['rows'])
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch' in ci and not re.search(r'^\s*(push|pull_request|schedule)\s*:',ci,re.M)
    guard=subprocess.run([sys.executable,str(HERE/'verify_stage_2d.py')],capture_output=True,text=True,encoding='utf-8')
    assert guard.returncode!=0 and 'Stage 2E prep registered' in guard.stderr
    files=[ROOT/n for n in ['README.md','AGENTS.md','plan.md','plan-table2.md','research/table2-confirmation/README.md']]+[OUT/'README.md',OUT/OUTPUTS[1]]
    links=0
    for p in files:
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if link.startswith(('http:','https:','#','app:','codex:')):continue
            target=(p.parent/link.split('#')[0]).resolve()
            if target==OUT/'table2-stage-2e-prep-audit.json':continue
            assert target.exists(),(p,link);links+=1
    local=dict(status='not_run_in_this_invocation')
    if args.local_checks:
        assert re.search(r'128 passed',(run/'logs/pytest.txt').read_text(encoding='utf-8-sig'))
        assert re.search(r'40 passed',(run/'logs/pytest-targeted-gates.txt').read_text(encoding='utf-8-sig'))
        gate=load(run/'logs/worktree-check.txt');assert gate['checks']=='passed' and gate['audio_payloads']==0 and gate['skill_links']==102
        exact=load(run/'exact-rebuild.json');assert exact['identical'] and set(exact['artifacts'])==set(OUTPUTS)
        for n,h in exact['artifacts'].items():assert sha(OUT/n)==h
        assert load(run/'freeze-overwrite-guard.json')['refused_and_unchanged']
        local=dict(status='passed',pytest_tests=128,new_contract_tests=40,worktree_gate=gate,deterministic_outputs=2)
    audit=dict(stage='2E-prep',date='2026-10-10',status='passed_preparation_with_explicit_execution_gaps',
        baseline=binding,stage_2E_complete=False,snapshots=24,production_skill_project_files_SHA=79,protected_inputs_SHA=67,
        protocol_and_2D_outputs_SHA_unchanged=True,old_2C_records_SHA_unchanged=True,
        installed_runtime_files_SHA_rechecked=47,current_model_or_native_execution=False,
        synthetic_contract_tests=40,real_waveforms=0,new_feedback=0,generic_rules=0,
        actual_Q5_sampling_or_speaker_or_PCM_validation=False,measurement_validated_upgrades=False,
        checker_source_independent=True,old_2D_audit_write_refused=True,document_links_checked=links,local_verification=local,
        artifacts=[dict(path=(OUT/n).relative_to(ROOT).as_posix(),sha256=sha(OUT/n)) for n in OUTPUTS],
        entry_and_code_bindings=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in files+[
            HERE/n for n in ['freeze_stage_2e_prep.py','check_stage_2e_runtime.py','build_stage_2e_prep.py','verify_stage_2e_prep.py',
                'shfc_path_adapter.py','shfc_path_checks.py','shfc_path_runner.py','shfc_path_backend.py',
                'stage_2e_prep_baseline_binding.json','verify_stage_2d.py']]+[ROOT/'tests/contracts/test_shfc_path_research.py']],
        next_stage='2E actual native/geometry and integration checks; audio/listening not executed')
    (OUT/'table2-stage-2e-prep-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=audit['status'],runtime=47,protected=67,production=79,links=links,local=local)))


if __name__=='__main__':
    main()
