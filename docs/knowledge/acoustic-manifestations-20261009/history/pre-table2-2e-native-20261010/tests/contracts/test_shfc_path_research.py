"""Finite synthetic contract tests; never load models, songs or audio."""
import copy
from dataclasses import replace
import math
from pathlib import Path
import sys

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[2] / 'research/table2-confirmation'
sys.path.insert(0, str(RESEARCH))
from shfc_path_runner import load_sealed_protocol, prepare_condition, prepare_batch, render_prepared_batch
from shfc_path_adapter import assemble_paths, tensor_binding
from shfc_path_checks import check_paths, check_repetition
from check_stage_2e_runtime import resolve_registry

CHANNELS = ('breathiness', 'voicing', 'tension')


def synthetic_native(case):
    """Actual frozen nominal times, synthetic tokens/speaker/predictions only."""
    frame_ms = 512/44100*1000
    position_ms = case['condition']['native_phones'][0]['start_ms'] - 20
    frames = math.ceil((case['condition']['vowel_s'][1]*1000 + 40 - position_ms)/frame_ms)
    clock = (position_ms + np.arange(frames)*frame_ms)/1000
    anchors = case['nominal_Q5_anchors_s']
    cents = np.zeros(frames, np.float32)
    for i, t in enumerate(clock):
        if anchors[0] <= t < anchors[1]:
            u = (t-anchors[0])/(anchors[1]-anchors[0]); cents[i] = round(-400*(6*u**5-15*u**4+10*u**3))
        elif anchors[1] <= t <= anchors[2]:
            cents[i] = -400
        elif anchors[2] < t <= anchors[3]:
            u = (t-anchors[2])/(anchors[3]-anchors[2]); cents[i] = round(-400*(1-(6*u**5-15*u**4+10*u**3)))
    shape = (1, frames)
    f0 = np.full(shape, np.float32(440*2**((case['condition']['tone']-69)/12)), np.float32)
    manual = {'breathiness': np.full(shape, -.36, np.float32), 'voicing': np.zeros(shape, np.float32),
        'tension': np.full(shape, .7, np.float32)}
    pred = {k: np.full(shape, v, np.float32) for k, v in zip(CHANNELS, [-50, -45, 1])}
    def serialize(ts):
        return [dict(name=k, dtype=str(v.dtype), shape=list(v.shape), values=v.reshape(-1).tolist()) for k, v in ts.items()]
    values = {k: pred[k] + manual[k] for k in CHANNELS}
    values.update(f0=f0, spk_embed=np.full((1,frames,2), 2.5, np.float32),
        tokens=np.array([[1,2]], np.int64), steps=np.array([20], np.int64), depth=np.array([.6], np.float32))
    a = dict(position_ms=position_ms, frame_ms=frame_ms, head_frames=0, tail_frames=0,
        sample_rate=44100, singer_location='synthetic', acoustic_model='synthetic', vocoder_model='synthetic',
        acoustic_mel_base='e', vocoder_mel_base='e', phones=copy.deepcopy(case['condition']['native_phones']),
        vocoder_f0=f0.ravel().tolist(), vocoder_pitch_controllable=True, native_acoustic_cache_verified=True,
        native_variance_predictions={k: v.ravel().tolist() for k, v in pred.items()},
        expression_deltas={k: v.ravel().tolist() for k, v in manual.items()},
        tone_shift_cents=np.zeros(frames, np.float32).tolist(), tensors=serialize(values))
    s = copy.deepcopy(a)
    s['tone_shift_cents'] = cents.tolist()
    shifted_values = {k: v.copy() for k, v in values.items()}
    factors = np.asarray([math.pow(2, float(x)) for x in cents/np.float32(1200)], np.float32)
    shifted_values['f0'] = f0*factors[None,:]
    for k in CHANNELS:
        shifted_pred = pred[k] + np.float32(.25)
        s['native_variance_predictions'][k] = shifted_pred.ravel().tolist()
        shifted_values[k] = shifted_pred + manual[k]
    s['tensors'] = serialize(shifted_values)
    vp = np.full(shape, case['condition']['tone'], np.float32)
    variance_values = dict(pitch=vp, spk_embed=values['spk_embed'].copy(), tokens=values['tokens'].copy())
    va = dict(frame_ms=frame_ms, head_frames=0, tail_frames=0, variance_model='synthetic',
        variance_speaker_root='synthetic', native_linguistic_cache='synthetic', linguistic_tensors=[],
        native_variance_cache_verified=True, tone_shift_semitones=np.zeros(frames,np.float32).tolist(), tensors=serialize(variance_values))
    vs = copy.deepcopy(va)
    semitones = cents/np.float32(100)
    vs['tone_shift_semitones'] = semitones.tolist()
    variance_values['pitch'] = vp + semitones[None,:]
    vs['tensors'] = serialize(variance_values)
    return a,s,va,vs


def predictor(values):
    shape = values['pitch'].shape
    d = np.float32(np.mean(values['pitch'])/100)
    return {k+'_pred': np.full(shape, np.float32(v)+d, np.float32) for k,v in zip(CHANNELS,[-51,-46,2])}


def prepared(case_index=0, predict=predictor):
    case = load_sealed_protocol()['cases'][case_index]
    native = synthetic_native(case)
    result = prepare_condition(*native, case, batch_id='synthetic-new-batch', predict=predict)
    return result, native, case


def checker_arguments(result, native):
    from agent2utau.evaluation.controlled_probe import tensors
    from agent2utau.expression.variance_expectation import gaussian_frame_noise
    a,s,_,_ = native
    r = result['repetitions'][0]
    base,shifted = tensors(a['tensors']),tensors(s['tensors'])
    manual = {k:np.asarray(a['expression_deltas'][k],np.float32)[None,:] for k in CHANNELS}
    args = (base,shifted,manual,r['predictions'],gaussian_frame_noise(101,1,128,base['f0'].size),base['f0'].copy())
    kw = dict(batch_id=r['batch_id'],condition_id=r['condition_id'],repetition=0,
        conditioning_bindings={k:v.conditioning_sha256 for k,v in r['predictions'].items()})
    return r,args,kw


def test_two_conditions_four_paths_exact_and_full_phrase_prediction_response():
    calls = []
    def counted(values):
        calls.append(tensor_binding(values));return predictor(values)
    all_results = [prepared(i,counted)[0] for i in (0,1)]
    assert len(calls) == 8 and sum(r['prepared_acoustic_inputs'] for r in all_results) == 16
    assert all(r['new_audio']==r['acoustic_vocoder_calls']==0 for r in all_results)
    for result in all_results:
        rows = result['repetitions'][0]['paths']
        assert set(rows)=={'A','S','D','P'}
        assert rows['D']['native_equivalent'] is False and rows['P']['native_equivalent'] is False
        assert np.array_equal(rows['D']['inputs']['breathiness'],rows['A']['inputs']['breathiness'])
        assert np.array_equal(rows['P']['inputs']['f0'],rows['A']['inputs']['f0'])
        # Predictor deliberately responds across complete context, even where
        # sampled shift is zero. No artificial target-support mask is imposed.
        assert rows['P']['inputs']['tension'][0,0] != rows['A']['inputs']['tension'][0,0]
        assert result['repeat_checks']['final_input_repeat_exact']
        assert not result['fresh_model_execution_verified']


def test_zero_prediction_response_and_nonzero_manual_baseline_allowed():
    def same(values):
        return {k+'_pred': np.full(values['pitch'].shape,v,np.float32) for k,v in zip(CHANNELS,[-51,-46,2])}
    result,_,_ = prepared(predict=same)
    rows=result['repetitions'][0]['paths']
    assert np.array_equal(rows['P']['inputs']['tension'],rows['A']['inputs']['tension'])
    assert np.all(rows['A']['inputs']['tension']==np.float32(2)+np.float32(.7))
    assert result['repetitions'][0]['checks']['conditional_prediction_response_may_be_zero']


@pytest.mark.parametrize('confound',['direct_prediction','prediction_f0','vocoder_f0','speaker','tokens','noise',
                                   'manual_erased','partial_group','dtype','nonfinite','provenance','native_role'])
def test_independent_checker_refuses_confounded_paths(confound):
    result,native,_=prepared();r,args,kw=checker_arguments(result,native)
    paths=copy.deepcopy(r['paths']);predictions=copy.deepcopy(args[3]);args=list(args);args[3]=predictions
    if confound=='direct_prediction':paths['D']['inputs']['breathiness'][0,0]+=1
    elif confound=='prediction_f0':paths['P']['inputs']['f0'][0,0]+=1
    elif confound=='vocoder_f0':paths['S']['vocoder_f0'][0,0]+=1
    elif confound=='speaker':paths['S']['inputs']['spk_embed'][0,0,0]+=1
    elif confound=='tokens':paths['P']['inputs']['tokens'][0,0]+=1
    elif confound=='noise':paths['S']['inputs']['probe_noise'][0,0,0,0]+=1
    elif confound=='manual_erased':paths['A']['inputs']['tension'][0,0]-=.7
    elif confound=='partial_group':del predictions['S'].values['tension_pred']
    elif confound=='dtype':paths['A']['inputs']['tension']=paths['A']['inputs']['tension'].astype(np.float64)
    elif confound=='nonfinite':paths['P']['inputs']['voicing'][0,0]=np.nan
    elif confound=='provenance':predictions['S']=replace(predictions['S'],condition_id='another-word')
    else:paths['D']['native_equivalent']=True
    with pytest.raises(ValueError):check_paths(paths,*args,**kw)


@pytest.mark.parametrize('confound',['batch','condition','source','repetition','cache','binding'])
def test_assembler_rejects_old_cross_condition_or_mislabeled_prediction(confound):
    result,native,_=prepared();r,args,kw=checker_arguments(result,native)
    base,shifted,manual,predictions,noise,vocoder=args
    p=dict(predictions);draw=p['S']
    if confound=='batch':draw=replace(draw,batch_id='old')
    elif confound=='condition':draw=replace(draw,condition_id='other')
    elif confound=='source':draw=replace(draw,source='A')
    elif confound=='repetition':draw=replace(draw,repetition=1)
    elif confound=='cache':draw=replace(draw,origin='historical_cache')
    else:draw=replace(draw,conditioning_sha256='0'*64)
    p['S']=draw
    with pytest.raises(ValueError):assemble_paths(base,shifted,manual,p,acoustic_noise=noise,vocoder_f0=vocoder,**kw)


def test_new_clipping_is_not_hidden_by_final_tensor_equality():
    result,native,_=prepared();r,args,kw=checker_arguments(result,native)
    base,shifted,manual,pred,noise,vocoder=args
    pred=copy.deepcopy(pred);pred['S'].values['tension_pred'][0,0]=100
    paths=assemble_paths(base,shifted,manual,pred,acoustic_noise=noise,vocoder_f0=vocoder,**kw)
    with pytest.raises(ValueError,match='New feature clipping'):
        check_paths(paths,base,shifted,manual,pred,noise,vocoder,**kw)


def test_silent_or_invalid_predictions_and_changed_repeat_stop():
    calls=0
    def nonrepeat(values):
        nonlocal calls
        calls+=1; out=predictor(values)
        if calls==4:out['tension_pred'][0,0]+=np.float32(.0001)
        return out
    with pytest.raises(ValueError,match='Repeat prediction not exact'):prepared(predict=nonrepeat)
    result,_,_=prepared();bad=copy.deepcopy(result['repetitions'][1]);bad['paths']['D']['vocoder_f0'][0,0]+=1
    with pytest.raises(ValueError,match='Repeat vocoder'):check_repetition(result['repetitions'][0],bad)


def test_backend_cannot_mutate_native_or_first_draw_through_aliases():
    saved=[]
    def aliases(values):
        out=predictor(values)
        values['pitch'][:]=0
        if saved:saved[-1]['tension_pred'][:]=100
        saved.append(out);return out
    result,native,_=prepared(predict=aliases)
    assert result['repeat_checks']['prediction_repeat_exact']
    assert all(np.max(r['predictions']['A'].values['tension_pred'])<10 for r in result['repetitions'])
    assert native[2]['tensors'][0]['values'][0] != 0


@pytest.mark.parametrize('confound',['dose','condition','clock','steps','depth','manual','variance_layout'])
def test_runner_refuses_frozen_design_or_native_dependency_changes(confound):
    case=copy.deepcopy(load_sealed_protocol()['cases'][0]);native=list(synthetic_native(case));a,s,va,vs=native
    if confound=='dose':case['peak_cents']=-399
    elif confound=='condition':case['condition']['id']='unselected'
    elif confound=='clock':a['sample_rate']=s['sample_rate']=48000
    elif confound=='steps':next(t for t in a['tensors'] if t['name']=='steps')['values']=[21];next(t for t in s['tensors'] if t['name']=='steps')['values']=[21]
    elif confound=='depth':next(t for t in a['tensors'] if t['name']=='depth')['values']=[1];next(t for t in s['tensors'] if t['name']=='depth')['values']=[1]
    elif confound=='manual':s['expression_deltas']['tension'][0]=0
    else:va['tail_frames']=vs['tail_frames']=1
    with pytest.raises(ValueError):prepare_condition(*native,case,batch_id='fixture',predict=predictor)


def test_runtime_alias_resolution_requires_declared_registry_root(tmp_path):
    core=tmp_path/'OpenUtau.Core.dll';config=tmp_path/'Singers/Yousa/dsconfig.yaml'
    registry={str(core):'a'*64,str(config):'b'*64}
    expected={'external-resource/OpenUtau/OpenUtau.Core.dll':'a'*64,'external-resource/OpenUtau/Singers/Yousa/dsconfig.yaml':'b'*64}
    resolved=resolve_registry(registry,expected,tmp_path)
    assert resolved['external-resource/OpenUtau/OpenUtau.Core.dll']==core
    with pytest.raises(ValueError):resolve_registry(registry,expected,tmp_path/'other')
    with pytest.raises(ValueError):resolve_registry(registry,{**expected,'external-resource/OpenUtau/missing':'c'*64},tmp_path)


def synthetic_batch():
    cases=load_sealed_protocol()['cases']
    native={c['condition']['id']:synthetic_native(c) for c in cases}
    return prepare_batch(native,batch_id='synthetic-batch-only',predict=predictor),native


def test_batch_requires_two_frozen_conditions_and_keeps_finite_callback_budget():
    batch,native=synthetic_batch()
    assert batch['predictor_calls']==8 and batch['prepared_acoustic_inputs']==16
    assert batch['rendered_waveforms']==0 and not batch['model_execution_verified']
    with pytest.raises(ValueError):prepare_batch({next(iter(native)):next(iter(native.values()))},batch_id='same',predict=predictor)
    with pytest.raises(ValueError):prepare_batch({**native,'third':next(iter(native.values()))},batch_id='same',predict=predictor)


def test_render_interface_fixed_sixteen_mock_calls_no_files_or_delivery():
    batch,_=synthetic_batch();calls=[]
    def mocked(inputs,f0,condition):
        calls.append((condition,inputs['f0'].copy(),f0.copy()))
        return np.zeros((1,inputs['f0'].shape[1],128),np.float32),np.zeros(4,np.float32)
    result=render_prepared_batch(batch,render=mocked)
    assert len(calls)==16 and result['raw_waveforms']==16 and result['delivery_waveforms']==0
    assert not result['DYN_or_gain_or_PCM_checked']
    for i in (0,8):
        assert np.array_equal(calls[i+1][1],calls[i+2][1])
        assert np.array_equal(calls[i][1],calls[i+3][1])
        assert all(np.array_equal(calls[i][2],calls[i+j][2]) for j in range(8))


@pytest.mark.parametrize('fault',['nonrepeat','fullscale','nonfinite','wrong_mel_layout'])
def test_raw_output_gate_refuses_mock_failures(fault):
    batch,_=synthetic_batch();calls=0
    def mocked(inputs,f0,condition):
        nonlocal calls
        calls+=1
        mel=np.zeros((1,inputs['f0'].shape[1],128),np.float32);wave=np.zeros(4,np.float32)
        if fault=='nonrepeat' and calls==5:wave[0]=np.float32(.00001)
        elif fault=='fullscale':wave[0]=1
        elif fault=='nonfinite':wave[0]=np.nan
        elif fault=='wrong_mel_layout':mel=mel[:,:-1]
        return mel,wave
    with pytest.raises(ValueError):render_prepared_batch(batch,render=mocked)


def test_render_gate_rechecks_paths_even_if_two_mutated_repeats_match():
    batch,_=synthetic_batch()
    for rep in batch['conditions'][0]['repetitions']:
        rep['paths']['D']['inputs']['spk_embed'][0,0,0]+=1
    with pytest.raises(ValueError,match='Nonselected'):
        render_prepared_batch(batch,render=lambda *args: (_ for _ in ()).throw(AssertionError('Backend must not be called')))


def test_lazy_backend_wrong_output_location_does_not_load_onnx(tmp_path):
    from shfc_path_backend import OnnxPathsBackend
    with pytest.raises(ValueError,match='Explicit unused'):
        OnnxPathsBackend({},install_root=tmp_path,out=tmp_path/'invalid-model-output')


def test_backend_budget_and_mel_conversion_with_fake_sessions():
    from shfc_path_backend import OnnxPathsBackend
    backend=OnnxPathsBackend.__new__(OnnxPathsBackend)
    backend.predictor_calls=8;backend.renderer_calls=0
    with pytest.raises(ValueError,match='variance budget'):backend.predict({})
    backend.records={'case':(dict(singer_location='fixture',acoustic_mel_base='10',vocoder_mel_base='e'),{})}
    backend.check_speaker=lambda values,root:None
    class Acoustic:
        def run(self,names,inputs):return [np.ones((1,2,128),np.float32)]
    seen=[]
    class Vocoder:
        def run(self,names,inputs):seen.append(inputs);return [np.zeros((1,4),np.float32)]
    backend.acoustic=Acoustic();backend.vocoder=Vocoder()
    f0=np.full((1,2),500,np.float32)
    mel,_=backend.render({},f0,'case')
    assert np.all(mel==1) and np.all(seen[0]['mel']==np.float32(np.log(10)))
    assert np.array_equal(seen[0]['f0'],f0)
    backend.renderer_calls=16
    with pytest.raises(ValueError,match='rendering budget'):backend.render({},f0,'case')
