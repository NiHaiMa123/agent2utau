"""Independent frozen geometry and native nonselected-input checks, no inference."""
import numpy as np
import yaml
from pathlib import Path
from freeze_stage_2d import ROOT,HERE,OUT,load,sha
from prepare_stage_2e_execution import save
from shfc_path_runner import load_sealed_protocol
from shfc_native_preflight import check_identity,sample_curve,check_sample_support
from agent2utau.evaluation.controlled_probe import tensors,require_shift_isolation

def records(run,case,label):
    ix=case['condition']['context']; folder=run/'native'/case['condition']['id']/label
    return [load(folder/f'{prefix}_{ix:03}.json') for prefix in ['phrase','variance']]

def check_arrays(a,b):
    assert set(a)==set(b)
    for key in a:
        assert a[key].dtype==b[key].dtype and a[key].shape==b[key].shape and np.array_equal(a[key],b[key]),key

def main():
    binding=load(HERE/'stage_2e_execution_baseline_binding.json'); run=ROOT/binding['run']
    target=run/'native-current-check.json'; assert not target.exists()
    prep=load(run/'preparation.json'); acquisition=load(run/'native-acquisition.json')
    for row in acquisition['records']:
        for ref in row['files']: assert sha(ROOT/ref['path'])==ref['sha256']
    p=load_sealed_protocol(); rows=[]; sources=[]; comparisons=load(OUT/'comparison-bindings.json')
    for case,design,record_id in zip(p['cases'],prep['conditions'],['RESP-002','RESP-007']):
        a,va=records(run,case,'A'); s,vs=records(run,case,'S')
        for current,v in [(a,va),(s,vs)]: check_identity(current,v,case)
        project=yaml.safe_load((ROOT/design['S']['path']).read_text(encoding='utf-8'))
        cents=sample_curve(project,a,design['curve']); semis=sample_curve(project,a,design['curve'],unit='semitones')
        assert np.array_equal(cents,np.asarray(s['tone_shift_cents'],np.float32))
        assert np.array_equal(semis,np.asarray(vs['tone_shift_semitones'],np.float32))
        sampling=check_sample_support(s,cents,case)
        isolation=require_shift_isolation(a,s,va,vs,case['shifted_support_s'],case['peak_cents'])
        old_row=next(r for r in comparisons['rows'] if r['record_id']==record_id)
        old=[]
        for name in [f'phrase_{a["phrase_index"]:03}.json',f'variance_{a["phrase_index"]:03}.json']:
            ref=next(r for r in old_row['native_and_fresh_artifact_bindings'] if r['path'].endswith('/native_A/'+name))
            assert sha(ROOT/ref['path'])==ref['expected_sha256']; old.append(load(ROOT/ref['path']));sources.append(ref)
        oa,ov=old
        for key in ['phones','position_ms','frame_ms','head_frames','tail_frames','vocoder_f0','expression_deltas']:
            assert a[key]==oa[key],key
        check_arrays(tensors(va['tensors']),tensors(ov['tensors']))
        check_arrays(tensors(va['linguistic_tensors']),tensors(ov['linguistic_tensors']))
        aa,oo=tensors(a['tensors']),tensors(oa['tensors'])
        check_arrays({k:v for k,v in aa.items() if k not in ['breathiness','voicing','tension']},
                     {k:v for k,v in oo.items() if k not in ['breathiness','voicing','tension']})
        for current in [a,s,va,vs]:
            key='singer_location' if 'singer_location' in current else 'variance_speaker_root'
            root=Path(current[key]); speaker=.75*np.fromfile(root/'Yousa_Normal.emb',dtype='<f4')+.25*np.fromfile(root/'Yousa_Classic.emb',dtype='<f4')
            values=tensors(current['tensors'])['spk_embed']; assert np.array_equal(values,np.broadcast_to(speaker,values.shape))
        rows.append(dict(condition_id=case['condition']['id'],identity=check_identity(a,va,case),
            actual_Q5_sampling_exact=True,sampling=sampling,native_isolation=isolation,
            old_A_nonselected_inputs_and_linguistic_condition_exact=True,two_stage_speaker_exact=True,
            native_cached_predictions_not_used_for_new_fresh_inference=True))
    install=Path(prep['install_root'])
    for alias,digest in p['fixed']['runtime_expected_hashes'].items():
        assert sha(install/alias.removeprefix('external-resource/OpenUtau/'))==digest,alias
    save(target,dict(conditions=rows,historical_read_bindings=sources,runtime47_exact=True,
        source_project_binding=prep['conditions'],new_native_record_pairs=4,technical_native_cache_waveforms=4,
        seeded_variance_calls=0,seeded_acoustic_vocoder_waveforms=0,agent_heard=False))
    print('Current A/S exact Q5 + identity + historical nonselected inputs + speakers + runtime47 passed')

if __name__=='__main__':main()
