"""Preservation/provenance verification; never writes historical stage audits."""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
import numpy as np
import yaml
from freeze_stage_2d import ROOT, HERE, OUT, load, sha
from shfc_native_preflight import check_identity, planned_curve, sample_curve, check_sample_support
from check_stage_2e_runtime import resolve_registry
from agent2utau.resources.config import load_config
from build_stage_2e_native import OUTPUTS


def main():
    if (HERE/'stage_2e_execution_baseline_binding.json').exists():
        raise SystemExit('Stage 2E execution registered; preserve native preflight audit')
    binding=load(HERE/'stage_2e_native_baseline_binding.json')
    manifest=ROOT/binding['manifest'];assert sha(manifest)==binding['sha256']
    frozen=load(manifest);run=ROOT/binding['run']
    mutable={'README.md','AGENTS.md','plan.md','plan-table2.md',
        'research/table2-confirmation/README.md','docs/knowledge/acoustic-manifestations-20261009/README.md',
        *['research/table2-confirmation/'+n for n in ['build_stage_2e_prep.py','verify_stage_2e_prep.py',
            'shfc_path_adapter.py','shfc_path_runner.py','shfc_path_backend.py']],
        'tests/contracts/test_shfc_path_research.py'}
    for r in frozen['files']:
        assert sha(ROOT/r['snapshot'])==r['sha256']
        if r['path'] not in mutable:assert sha(ROOT/r['path'])==r['sha256'],r['path']
    assert len(frozen['files'])==20
    for r in frozen['production_skill_project_bindings']+frozen['protected_inputs']:
        assert sha(ROOT/r['path'])==r['sha256'],r['path']
    # Previous protocol/records/2D outputs remain current; allow only the prior
    # documented 2D verifier guard change, never overwrite 2D/prep artifacts.
    prep=load(HERE/'stage_2e_prep_baseline_binding.json')
    assert sha(ROOT/prep['manifest'])==prep['sha256']
    for r in load(ROOT/prep['manifest'])['files']:
        assert sha(ROOT/r['snapshot'])==r['sha256']
        if r['path'] not in mutable|{'research/table2-confirmation/verify_stage_2d.py'}:
            assert sha(ROOT/r['path'])==r['sha256']
    report=load(OUT/OUTPUTS[0]);assert report['stage_2E_complete'] is False
    for r in report['protocol_bindings']+report['implementation_bindings']+report['source_bindings']:
        assert sha(ROOT/r['path'])==r['sha256'],r['path']
    proof=load(ROOT/report['proof']['path']);assert sha(ROOT/report['proof']['path'])==report['proof']['sha256']
    assert not proof['installed_models_executed'] and proof['real_waveforms']==proof['new_feedback']==proof['new_native_exports']==0
    for r in proof['private_evidence']+proof['model_contracts']:
        assert sha(ROOT/r['path'])==r['sha256']
    expected_execution=dict(new_native_exports=0,variance_inferences=0,acoustic_vocoder_waveforms=0,
        delivered_PCM=0,new_feedback=0,generic_rules=0,measurement_validated_upgrades=False)
    assert report['execution']==expected_execution
    assert len(proof['speaker_checks'])==6 and all(r['exact'] for r in proof['speaker_checks'])
    assert len(proof['actual_record_negative_controls'])==6
    assert all(not r['new_native_export_matches'] for r in report['conditions'])
    protocol=load(OUT/'validation-protocols/shfc-path-separation-v1.json')
    refs={r['path']:r['sha256'] for r in report['source_bindings']}
    project=yaml.safe_load((ROOT/protocol['cases'][0]['baseline_project']['path']).read_text(encoding='utf-8'))
    for row,case in zip(proof['rows'],protocol['cases']):
        index=case['condition']['context']
        paths=[p for p in refs if p.endswith(f'/native_A/phrase_{index:03}.json')]
        assert len(paths)==1
        a=load(ROOT/paths[0]);v=load(ROOT/paths[0].replace('phrase_','variance_'))
        assert check_identity(a,v,case)==row['historical_identity']
        curve=planned_curve(project,a,case);assert curve==row['planned_curve']
        sampled=sample_curve(project,a,curve)
        assert check_sample_support(a,sampled,case)==row['sampling']
        planned=load(run/(case['condition']['id']+'-planned-curve.json'))
        assert planned['curve']==curve and np.array_equal(np.asarray(planned['sampled_cents'],np.float32),sampled)
        if index==22:
            c=load(ROOT/'runs/lastpage_shfc_onset_probe_20261008/native_C/phrase_022.json')
            cv=load(ROOT/'runs/lastpage_shfc_onset_probe_20261008/native_C/variance_022.json')
            assert np.array_equal(sampled,np.asarray(c['tone_shift_cents'],np.float32))
            assert np.array_equal(sample_curve(project,a,curve,unit='semitones'),np.asarray(cv['tone_shift_semitones'],np.float32))
    registry=load(ROOT/'runs/lastpage_brec_cohort_probe_20261008/frozen_runtime.json')
    paths=resolve_registry(registry,protocol['fixed']['runtime_expected_hashes'],Path(load_config()['openutau_dir']))
    for alias,p in paths.items():assert sha(p)==protocol['fixed']['runtime_expected_hashes'][alias]
    assert all(not r['measurement_validated'] for r in load(OUT/'measurement-protocols.json')['rows'])
    ci=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch' in ci and not re.search(r'^\s*(push|pull_request|schedule)\s*:',ci,re.M)
    for name in ['build_stage_2e_prep.py','verify_stage_2e_prep.py']:
        p=subprocess.run([sys.executable,str(HERE/name)],capture_output=True,text=True,encoding='utf-8')
        assert p.returncode and 'Stage 2E native registered' in p.stderr
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    assert '143 passed' in (run/'logs/pytest.txt').read_text(encoding='utf-8-sig')
    assert '55 passed' in (run/'logs/pytest-targeted-corrected.txt').read_text(encoding='utf-8-sig')
    gate=load(run/'logs/worktree-check-final.txt');assert gate['checks']=='passed' and gate['audio_payloads']==0
    assert load(run/'exact-rebuild.json')['identical']
    assert load(run/'freeze-overwrite-guard.json')['refused_and_unchanged']
    files=[ROOT/n for n in ['README.md','AGENTS.md','plan.md','plan-table2.md','research/table2-confirmation/README.md']]+[OUT/'README.md',OUT/OUTPUTS[1]]
    links=0
    for p in files:
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if link.startswith(('http:','https:','#','app:','codex:')):continue
            assert (p.parent/link.split('#')[0]).resolve().exists(),(p,link)
            links+=1
    audit=dict(stage='2E-native',date='2026-10-10',status='passed_with_explicit_execution_gaps',
        baseline=binding,stage_2E_complete=False,snapshots=20,production_skill_project_SHA=79,protected_inputs_SHA=67,
        protocol_and_old_audits_unchanged=True,runtime_rehashed=47,local_tests=143,research_contract_tests=55,
        gate=gate,links_checked=links,execution=expected_execution,
        artifacts=[dict(path=(OUT/n).relative_to(ROOT).as_posix(),sha256=sha(OUT/n)) for n in OUTPUTS],
        entry_and_code_bindings=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in files]+[
            dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in [HERE/'verify_stage_2e_native.py',
                HERE/'stage_2e_native_baseline_binding.json',HERE/'build_stage_2e_prep.py',HERE/'verify_stage_2e_prep.py']],
        next='2E finite execution prerequisites and explicitly authorized new batch; human listening after technical gates')
    (OUT/'table2-stage-2e-native-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=audit['status'],snapshots=20,protected=67,runtime=47,tests=143,links=links)))


if __name__=='__main__':main()
