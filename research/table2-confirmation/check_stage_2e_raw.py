"""Reopen persisted actual inputs/outputs and independently check the finite batch."""
import numpy as np
import soundfile as sf
from freeze_stage_2d import ROOT,HERE,OUT,load,sha
from prepare_stage_2e_execution import save
from check_stage_2e_current_native import records,check_arrays
from shfc_path_runner import load_sealed_protocol
from shfc_path_adapter import FreshPrediction,tensor_binding
from shfc_path_checks import check_paths,check_repetition
from shfc_path_backend import model_feed
from shfc_native_preflight import normalize_model_inputs
from shfc_pcm_checks import dynamic_gain,require_dynamics,require_finite_subfull
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise

def read_npz(path):
    with np.load(path,allow_pickle=False) as f:return {k:f[k].copy() for k in f.files}

def main():
    run=ROOT/load(HERE/'stage_2e_execution_baseline_binding.json')['run']; target=run/'raw-independent-check.json'
    assert not target.exists()
    execution=load(run/'raw-execution.json'); start=load(run/'execution-start.json')
    assert execution['variance_calls']==8 and execution['raw_acoustic_vocoder_calls']==16
    for r in start['implementation']: assert sha(ROOT/r['path'])==r['sha256']
    p=load_sealed_protocol(); comparisons=load(OUT/'comparison-bindings.json'); rows=[]; reads={}
    def read(path):
        reads[path.relative_to(ROOT).as_posix()]=sha(path);return read_npz(path)
    def floats(path):
        reads[path.relative_to(ROOT).as_posix()]=sha(path);return np.fromfile(path,dtype='<f4')
    for case,record_id in zip(p['cases'],['RESP-002','RESP-007']):
        cid=case['condition']['id']; a,va=records(run,case,'A');s,vs=records(run,case,'S')
        base,shifted=tensors(a['tensors']),tensors(s['tensors']); n=base['f0'].size
        manual={k:np.asarray(a['expression_deltas'][k],np.float32)[None,:] for k in ['breathiness','voicing','tension']}
        noise=gaussian_frame_noise(101,1,128,n); vn=gaussian_frame_noise(11,3,24,n)
        voc=np.asarray(a['vocoder_f0'],np.float32)[None,:]; reps=[]
        for rep in (0,1):
            draws={}; bindings={};paths={}
            for label,v in [('A',va),('S',vs)]:
                folder=run/'variance'/cid/f'{label}-r{rep}'
                actual=read(folder/'inputs.npz');expected=tensors(v['tensors']);expected['probe_noise']=vn
                check_arrays(actual,expected); bindings[label]=tensor_binding(actual)
                draws[label]=FreshPrediction(run.name,cid,label,rep,bindings[label],read(folder/'outputs.npz'))
            for label in ['A','S','D','P']:
                folder=run/'acoustic'/cid/f'{label}-r{rep}'; row=load(folder/'provenance.json')
                row.update(inputs=read(folder/'inputs.npz'),vocoder_f0=read(folder/'vocoder-f0.npz')['f0']); paths[label]=row
                # Saved normalized feed differs only in scalar singleton shape.
                actual_feed=read(folder/'actual-model-feed.npz');expected={k:v.copy() for k,v in row['inputs'].items()}
                for k in ['steps','depth']: expected[k]=expected[k].reshape(())
                check_arrays(actual_feed,expected)
                mel=read(folder/'mel.npz')['mel']; raw=floats(run/'raw'/cid/f'{label}-r{rep}.f32')
                assert mel.shape==(1,n,128) and mel.dtype==np.float32 and np.isfinite(mel).all()
                assert raw.shape==(n*512,);require_finite_subfull(raw)
            check=check_paths(paths,base,shifted,manual,draws,noise,voc,batch_id=run.name,
                condition_id=cid,repetition=rep,conditioning_bindings=bindings)
            reps.append(dict(condition_id=cid,batch_id=run.name,predictions=draws,paths=paths,checks=check))
        check_repetition(*reps)
        layout=load(run/'dynamics'/cid/'layout.json');gain=floats(run/'dynamics'/cid/'native-DYN-gain.f32')
        assert np.array_equal(gain,dynamic_gain(layout))
        peak=0.
        for label in ['A','S','D','P']:
            raw0,raw1=[floats(run/'raw'/cid/f'{label}-r{rep}.f32') for rep in (0,1)]
            assert np.array_equal(raw0,raw1)
            check_arrays(read(run/'acoustic'/cid/f'{label}-r0/mel.npz'),read(run/'acoustic'/cid/f'{label}-r1/mel.npz'))
            for rep,raw in zip((0,1),(raw0,raw1)):
                actual=floats(run/'dynamics'/cid/f'{label}-r{rep}.f32'); require_dynamics(raw,actual,gain)
                final=actual*np.float32(1.5); require_finite_subfull(final);peak=max(peak,float(np.max(np.abs(final))))
        old_row=next(r for r in comparisons['rows'] if r['record_id']==record_id)
        ref=next(r for r in old_row['native_and_fresh_artifact_bindings'] if r['path'].endswith('/fresh/A_raw.wav'))
        assert sha(ROOT/ref['path'])==ref['expected_sha256']; previous,sr=sf.read(ROOT/ref['path'],dtype='float32')
        assert sr==44100 and np.array_equal(previous,floats(run/'raw'/cid/'A-r0.f32')), 'Fresh A differs from bound historical PCM'
        reads[ref['path']]=ref['expected_sha256']
        for suffix,actual in [('A_inputs.npz',reps[0]['paths']['A']['inputs']),('A_prediction.npz',reps[0]['predictions']['A'].values)]:
            ref=next(r for r in old_row['native_and_fresh_artifact_bindings'] if r['path'].endswith('/fresh/'+suffix))
            assert sha(ROOT/ref['path'])==ref['expected_sha256']; check_arrays(actual,read(ROOT/ref['path']))
        rows.append(dict(condition_id=cid,independent_paths=reps[0]['checks'],repeat_inputs_predictions_mel_raw_DYN_exact=True,
            DYN_gain_reconstructed_from_actual_curve_exact=True,DYN_multiplication_exact=True,
            original_A_fresh_inputs_predictions_raw_PCM_exact=True,vocal_gain=1.5,vocal_peak=peak,
            waveform_samples=n*512,native_origin_s=(layout['position_ms']-layout['leading_ms'])/1000))
    save(target,dict(status='passed',conditions=rows,read_bindings=[dict(path=k,sha256=v) for k,v in reads.items()],
        actual_variance_calls=8,actual_seeded_waveforms=16,measurement_validated_upgrades=False,
        delivery_audio=0,agent_heard=False,auditory_acceptance='pending'))
    print('Persisted paths/repetition/native DYN/gain/historical A PCM independently passed')

if __name__=='__main__':main()
