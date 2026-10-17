"""Independent encoded PCM/pair and preservation gate before human delivery."""
import json
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from freeze_stage_2d import ROOT,HERE,OUT,load,sha
from prepare_stage_2e_execution import save
from shfc_path_runner import load_sealed_protocol
from check_stage_2e_raw import read_npz,check_arrays

def main():
    b=load(HERE/'stage_2e_execution_baseline_binding.json');run=ROOT/b['run']
    target=run/'technical-delivery-check.json';assert not target.exists()
    assert sha(ROOT/b['manifest'])==b['sha256']; baseline=load(ROOT/b['manifest'])
    allowed={'README.md','AGENTS.md','plan.md','plan-table2.md','research/table2-confirmation/README.md',
             'docs/knowledge/acoustic-manifestations-20261009/README.md',
             'research/table2-confirmation/build_stage_2e_native.py','research/table2-confirmation/verify_stage_2e_native.py'}
    for r in baseline['files']:
        assert sha(ROOT/r['snapshot'])==r['sha256']
        if r['path'] not in allowed:assert sha(ROOT/r['path'])==r['sha256']
    for r in baseline['production_skill_project_bindings']+baseline['protected_inputs']:
        assert sha(ROOT/r['path'])==r['sha256']
    old=load(ROOT/'runs/research/table2-2a-record-audit-20261010/observations/artifact-checks.json')
    memo={}
    for r in old['checks']:
        name=r['path'];value=r['expected_sha256']
        assert value and (name not in memo or memo[name]==value)
        memo[name]=value
    assert len(memo)==1079
    for name,value in memo.items():assert sha(ROOT/name)==value,name
    current_manifest_path=ROOT/'runs/lastpage_loudness_skill_v02_20261007/completion_manifest.json'
    current_manifest=load(current_manifest_path)
    # The old manifest also carries 75 repository/installed-Skill entries,
    # including pre-cleanup paths and the then-current mutable AGENTS.md.
    # The frozen preservation promise is the 567 sealed song-run files;
    # production/Skill/author files above use their current separate bindings.
    current_files={name:value for name,value in current_manifest['files'].items()
                   if Path(name).is_relative_to(current_manifest_path.parent)}
    assert len(current_files)==567
    for name,value in current_files.items():assert sha(Path(name))==value,name
    sources=load(OUT/'response-source-audit.json')['source_files']
    for r in sources:assert sha(ROOT/r['path'])==r['sha256']
    p=load_sealed_protocol();install=Path(load(run/'preparation.json')['install_root'])
    for name,value in p['fixed']['runtime_expected_hashes'].items():assert sha(install/name.removeprefix('external-resource/OpenUtau/'))==value
    raw_check=load(run/'raw-independent-check.json');assert raw_check['status']=='passed'
    pack=load(run/'pcm-packaging.json');assert pack['delivery_files']==72 and len(pack['files'])==88
    for ref in pack['files']:assert sha(ROOT/ref['path'])==ref['sha256']
    backing=ROOT/pack['backing']['path'];assert sha(backing)==pack['backing']['sha256']
    pairs_checked=0;context_checks=[]
    for case,c in zip(p['cases'],pack['conditions']):
        cid=c['condition_id'];n=c['samples'];i,j=c['focus_samples']
        coded=p['listening']['anonymous_code_map'][f'word{c["word"]}']
        with sf.SoundFile(backing) as f:
            f.seek(c['backing_start_sample']);back=f.read(n,dtype='float64',always_2d=True)
        for e in c['versions']:
            label=e['label'];assert coded[e['code']]==label
            dyn=np.fromfile(run/'dynamics'/cid/f'{label}-r0.f32',dtype='<f4')
            original=dyn.astype(np.float64)*1.5
            for kind,expected in [('vocal',original),('mix',original[:,None]+back*.7)]:
                full,sr=sf.read(ROOT/e['full_'+kind],dtype='float64',always_2d=kind=='mix')
                assert sr==44100 and full.shape==expected.shape
                assert np.max(np.abs(full-expected))<=2**-23+8*np.finfo(np.float64).eps
                full_int,_=sf.read(ROOT/e['full_'+kind],dtype='int32',always_2d=kind=='mix')
                focus_int,_=sf.read(ROOT/e['focus_'+kind],dtype='int32',always_2d=kind=='mix')
                assert np.array_equal(full_int[i:j],focus_int)
            repeat_a,_=sf.read(run/'pcm'/cid/f'{label}-r0.wav',dtype='float32')
            repeat_b,_=sf.read(run/'pcm'/cid/f'{label}-r1.wav',dtype='float32')
            assert np.array_equal(repeat_a,repeat_b)
        for row in [r for r in pack['pairs'] if r['condition_id']==cid]:
            assert row['direction']==p['listening']['presentation_order'][row['order']-1]
            assert row['codes']==[next(code for code,v in coded.items() if v==label) for label in row['direction'].split('-')]
            for kind in ['vocal','mix']:
                encoded,_=sf.read(ROOT/row[kind],dtype='int32',always_2d=kind=='mix')
                expected=[]
                for label in row['direction'].split('-'):
                    entry=next(x for x in c['versions'] if x['label']==label)
                    expected.append(sf.read(ROOT/entry['focus_'+kind],dtype='int32',always_2d=kind=='mix')[0])
                x,y=expected;m=row['segment_samples'];gap=row['gap_samples']
                assert np.array_equal(encoded[:m],x) and np.array_equal(encoded[m+gap:],y)
                assert np.all(encoded[m:m+gap]==0) and len(encoded)==2*m+gap
                pairs_checked+=1
        context_checks.append(dict(condition_id=cid,PCM_24_fixed_gain_and_mix_rebuilt=True,
            encoded_focus_slices_exact=True,focus_complete=c['focus_complete'],focus_role=c['focus_role']))
    observations=load(run/'observations.json');start=load(run/'observations-start.json')
    assert observations['F0_actual_inferences']==16 and len(observations['windows'])==53
    for ref in start['models']+start['implementation']:assert sha(Path(ref['path']))==ref['sha256']
    for ref in observations['F0_bindings']:
        assert sha(ROOT/ref['input']['path'])==ref['input']['sha256'] and sha(ROOT/ref['array']['path'])==ref['array']['sha256']
        d=read_npz(ROOT/ref['array']['path']);sr=ref['clock']['sr'];hop=ref['clock']['hop']
        assert d['f0_hz'].dtype==np.float32 and d['voiced'].dtype==np.bool_ and d['times'].dtype==np.float32
        assert np.array_equal(d['times'],(np.arange(len(d['times']))*hop/sr).astype(np.float32))
        assert d['times'].shape==d['f0_hz'].shape==d['voiced'].shape
    # Current S is a new execution, also exactly reconstructs the bound old C raw inputs/wave.
    c_row=next(r for r in load(OUT/'comparison-bindings.json')['rows'] if r['record_id']=='RESP-003')
    c_bindings=[]
    for suffix in ['B_raw.wav','B_inputs.npz','B_prediction.npz']:
        r=next(r for r in c_row['native_and_fresh_artifact_bindings'] if r['path'].endswith('/fresh/'+suffix))
        assert sha(ROOT/r['path'])==r['expected_sha256'];c_bindings.append(r)
        if suffix.endswith('.wav'):
            previous,sr=sf.read(ROOT/r['path'],dtype='float32');current=np.fromfile(run/'raw/current-word-225/S-r0.f32',dtype='<f4')
            assert sr==44100 and np.array_equal(previous,current)
        else:
            current=read_npz(run/('acoustic/current-word-225/S-r0/inputs.npz' if suffix.endswith('inputs.npz') else 'variance/current-word-225/S-r0/outputs.npz'))
            check_arrays(current,read_npz(ROOT/r['path']))
    guards=[]
    for name in ['build_stage_2e_native.py','verify_stage_2e_native.py']:
        before=[sha(OUT/x) for x in ['table2-stage-2e-native-check.json','table2-stage-2e-native-check.md','table2-stage-2e-native-audit.json']]
        r=subprocess.run([__import__('sys').executable,str(HERE/name)],capture_output=True,cwd=ROOT)
        assert r.returncode and b'Stage 2E execution registered' in r.stderr
        assert before==[sha(OUT/x) for x in ['table2-stage-2e-native-check.json','table2-stage-2e-native-check.md','table2-stage-2e-native-audit.json']]
        guards.append(dict(entry=name,refused=True))
    assert all(not r['measurement_validated'] for r in load(OUT/'measurement-protocols.json')['rows'])
    save(target,dict(status='passed_pending_human_listening',eligible_for_listening=True,
        snapshots_preserved=len(baseline['files']),production_skill_project_preserved=79,protected_inputs_preserved=67,
        old_2A_unique_paths_preserved=1079,current_song_run_files_preserved=len(current_files),
        current_song_manifest=dict(path=current_manifest_path.relative_to(ROOT).as_posix(),sha256=sha(current_manifest_path)),
        original_sources_preserved=len(sources),runtime47_exact=True,delivery_audio=72,FLOAT_diagnostics=16,
        encoded_two_order_pair_files_checked=pairs_checked,context_checks=context_checks,
        old_C_new_S_fresh_inputs_predictions_raw_PCM_exact=True,old_C_read_bindings=c_bindings,
        immutable_native_preflight_and_audit_guard=guards,source_unknown_preserved=True,
        agent_heard=False,new_feedback=0,generic_rules=0,measurement_validated_upgrades=False,
        auditory_status='pending',independent_effect_replications=0))
    print('Delivery PCM/pairs/model clocks + old SHA preservation passed; pending human listening')

if __name__=='__main__':main()
