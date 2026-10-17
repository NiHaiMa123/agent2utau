"""Explicit finite ONNX execution after native preflight; no delivery or adoption."""
import dataclasses
import json
import sys
from pathlib import Path
import numpy as np
from freeze_stage_2d import ROOT,HERE,load,sha
from prepare_stage_2e_execution import save
from check_stage_2e_current_native import records
from shfc_path_runner import load_sealed_protocol,prepare_batch,render_prepared_batch
from shfc_path_backend import OnnxPathsBackend,model_feed
from shfc_path_adapter import tensor_binding

def npz(path,values):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    np.savez_compressed(path,**values)

def main():
    import onnxruntime as ort
    import onnx
    b=load(HERE/'stage_2e_execution_baseline_binding.json'); run=ROOT/b['run']
    assert not (run/'execution-start.json').exists(), 'Never restart completed/partial model batch implicitly'
    native_check=load(run/'native-current-check.json'); assert native_check['runtime47_exact']
    p=load_sealed_protocol(); prep=load(run/'preparation.json'); batch_id=run.name
    native={c['condition']['id']:(*records(run,c,'A'),*records(run,c,'S')) for c in p['cases']}
    # Runner parameter order is acoustic A/S, variance A/S.
    native={cid:(a,s,va,vs) for cid,(a,va,s,vs) in native.items()}
    for row in load(run/'native-acquisition.json')['records']:
        for r in row['files']: assert sha(ROOT/r['path'])==r['sha256']
    sources=[HERE/n for n in ['execute_stage_2e_paths.py','shfc_path_backend.py','shfc_path_runner.py','shfc_path_adapter.py','shfc_path_checks.py','shfc_native_preflight.py']]
    python_native=Path(ort.__file__).parent/'capi/onnxruntime_pybind11_state.pyd'
    save(run/'execution-start.json',dict(batch_id=batch_id,protocol_id=p['id'],budget=p['budget'],
        native_check_sha256=sha(run/'native-current-check.json'),
        implementation=[dict(path=x.relative_to(ROOT).as_posix(),sha256=sha(x)) for x in sources],
        python=sys.version,executable=sys.executable,numpy=np.__version__,onnx=onnx.__version__,onnxruntime=ort.__version__,
        python_ort_binary=dict(path=str(python_native),sha256=sha(python_native)),
        actual_execution_started=True,automatic_retry=False))
    backend=None
    try:
        print('Loading bound models into CPU sequential single-thread sessions',flush=True)
        backend=OnnxPathsBackend({cid:(x[0],x[2]) for cid,x in native.items()},
            install_root=prep['install_root'],out=run/'models')
        save(run/'model-adapters.json',dict(proofs=backend.adapter_proofs,
            sessions=[dict(stage=stage,providers=s.get_providers(),inputs=[dict(name=x.name,type=x.type,shape=x.shape) for x in s.get_inputs()]) for stage,s in [('variance',backend.variance),('acoustic',backend.acoustic),('vocoder',backend.vocoder)]]))
        draws=[]
        def predict(values):
            i=backend.predictor_calls; case=p['cases'][i//4]; cid=case['condition']['id']
            repetition=(i%4)//2; label=['A','S'][i%2]; folder=run/'variance'/cid/f'{label}-r{repetition}'
            npz(folder/'inputs.npz',values); npz(folder/'actual-model-feed.npz',model_feed(backend.variance,values))
            outputs=backend.predict(values); npz(folder/'outputs.npz',outputs)
            draws.append(dict(condition_id=cid,source=label,repetition=repetition,
                conditioning_sha256=tensor_binding(values),inputs_sha256=sha(folder/'inputs.npz'),
                outputs_sha256=sha(folder/'outputs.npz')))
            print(f'variance {i+1}/8 {cid} {label} r{repetition}',flush=True)
            return outputs
        prepared=prepare_batch(native,batch_id=batch_id,predict=predict)
        summaries=[]
        for condition in prepared['conditions']:
            cid=condition['condition_id']; repetitions=[]
            for rep in condition['repetitions']:
                number=rep['paths']['A']['repetition']
                for label,row in rep['paths'].items():
                    folder=run/'acoustic'/cid/f'{label}-r{number}'
                    npz(folder/'inputs.npz',row['inputs']); npz(folder/'actual-model-feed.npz',model_feed(backend.acoustic,row['inputs']))
                    npz(folder/'vocoder-f0.npz',dict(f0=row['vocoder_f0']))
                    save(folder/'provenance.json',{k:v for k,v in row.items() if k not in ['inputs','vocoder_f0','clipping']})
                repetitions.append(dict(repetition=number,checks=rep['checks']))
            summaries.append(dict(condition_id=cid,native_isolation=condition['native_isolation'],repeat_checks=condition['repeat_checks'],repetitions=repetitions))
        save(run/'prepared-input-checks.json',dict(conditions=summaries,draws=draws,
            actual_seeded_variance_calls=backend.predictor_calls,fresh_predictions_executed=True,
            historical_prediction_arrays_fed=False))
        rawrows=[]
        def render(inputs,f0,cid):
            i=backend.renderer_calls; label=['A','S','D','P'][i%4]; repetition=(i%8)//4
            assert cid==p['cases'][i//8]['condition']['id']
            folder=run/'acoustic'/cid/f'{label}-r{repetition}'
            assert tensor_binding(inputs)==tensor_binding({k:v for k,v in np.load(folder/'inputs.npz').items()})
            mel,wave=backend.render(inputs,f0,cid)
            npz(folder/'mel.npz',dict(mel=mel))
            out=run/'raw'/cid/f'{label}-r{repetition}.f32'; out.parent.mkdir(parents=True,exist_ok=True)
            with out.open('xb') as f: f.write(wave.astype('<f4',copy=False).tobytes())
            rawrows.append(dict(condition_id=cid,label=label,repetition=repetition,
                raw=dict(path=out.relative_to(ROOT).as_posix(),sha256=sha(out)),mel_sha256=sha(folder/'mel.npz'),
                samples=wave.size,peak=float(np.max(np.abs(wave)))))
            print(f'acoustic/vocoder {i+1}/16 {cid} {label} r{repetition}',flush=True)
            return mel,wave
        rendered=render_prepared_batch(prepared,render=render)
        proof=backend.final_bindings_hold()
        assert proof['variance_calls']==8 and proof['raw_acoustic_vocoder_calls']==16
        save(run/'raw-execution.json',dict(**proof,raw=rawrows,
            raw_exact_repetitions=True,rendered_waveforms=rendered['raw_waveforms'],
            delivery_waveforms=0,DYN_or_gain_or_PCM_checked=False,
            source_unknown_preserved=True,independent_effect_replications=0,
            agent_heard=False,listening_status='pending',generic_rule_validated=False))
    except BaseException as exc:
        save(run/'execution-failure.json',dict(exception=type(exc).__name__,message=str(exc),
            variance_calls=backend.predictor_calls if backend else 0,
            acoustic_vocoder_calls=backend.renderer_calls if backend else 0,effect_interpretation_stopped=True))
        raise

if __name__=='__main__': main()
