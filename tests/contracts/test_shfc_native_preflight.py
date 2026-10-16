"""Synthetic guards for actual-export representations; no song/model/audio loads."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'research/table2-confirmation'))
from shfc_native_preflight import FRAME_MS, normalize_model_inputs, q5_value, sample_curve, check_sample_support
from shfc_path_adapter import tensor_binding
from shfc_path_runner import load_sealed_protocol, prepare_condition
from test_shfc_path_research import synthetic_native, predictor


def test_native_export_float32_clock_and_boolean_retake_are_supported():
    case=load_sealed_protocol()['cases'][0]; native=synthetic_native(case)
    for r in native:r['frame_ms']=11.609978
    for v in native[2:]:
        n=next(t for t in v['tensors'] if t['name']=='pitch')['shape'][1]
        v['tensors'].append(dict(name='retake',dtype='bool',shape=[1,n,3],values=[True]*(n*3)))
    result=prepare_condition(*native,case,batch_id='export-representation-fixture',predict=predictor)
    assert result['predictor_calls']==4 and result['new_audio']==0
    assert tensor_binding({'retake':np.array([True],bool)}) != tensor_binding({'retake':np.array([False],bool)})


def test_clock_guard_rejects_next_float32_value_before_predictor():
    case=load_sealed_protocol()['cases'][0];native=synthetic_native(case)
    for r in native:r['frame_ms']=float(np.nextafter(np.float32(FRAME_MS),np.float32(np.inf)))
    with pytest.raises(ValueError,match='clock'):
        prepare_condition(*native,case,batch_id='reject',predict=lambda x:pytest.fail('must reject first'))


def test_feed_uses_boolean_dtype_and_only_scalar_rank_conversion():
    x={'retake':np.ones((1,4,3),bool),'pitch':np.ones((1,4),np.float32),'steps':np.array([20],np.int64)}
    d=[dict(name='retake',type=9,shape=[1,'n_frames',3]),dict(name='pitch',type=1,shape=[1,'n_frames']),dict(name='steps',type=7,shape=[])]
    y=normalize_model_inputs(x,d)
    assert y['steps'].shape==() and y['steps']==20 and x['steps'].shape==(1,)
    assert np.array_equal(y['retake'],x['retake'])


@pytest.mark.parametrize('fault',['missing','dtype','rank','dimension','shared_frames','nonfinite','nonscalar','unnamed_scalar'])
def test_model_feed_rejects_confounds(fault):
    x={'pitch':np.ones((1,4),np.float32),'retake':np.ones((1,4,3),bool),'steps':np.array([20],np.int64)}
    d=[dict(name='pitch',type=1,shape=[1,'n_frames']),dict(name='retake',type=9,shape=[1,'n_frames',3]),dict(name='steps',type=7,shape=[])]
    if fault=='missing':del x['retake']
    elif fault=='dtype':x['retake']=x['retake'].astype(np.int64)
    elif fault=='rank':x['pitch']=x['pitch'].ravel()
    elif fault=='dimension':x['retake']=np.ones((1,4,2),bool)
    elif fault=='shared_frames':x['retake']=np.ones((1,5,3),bool)
    elif fault=='nonfinite':x['pitch'][0,0]=np.nan
    elif fault=='nonscalar':x['steps']=np.array([20,20],np.int64)
    else:x['other']=x.pop('steps');d[-1]['name']='other'
    with pytest.raises(ValueError):normalize_model_inputs(x,d)


def test_Q5_quantization_support_and_independent_polynomial():
    anchors=[1.,1.145,1.3,1.355]
    for t in np.linspace(.9,1.45,400):
        if t<1 or t>1.355:expected=0
        elif 1.145<=t<=1.3:expected=-400
        else:
            u=(t-1)/.145 if t<1.145 else (t-1.3)/.055
            q=6*u**5-15*u**4+10*u**3
            expected=round(-400*(q if t<1.145 else 1-q))
        assert q5_value(t,anchors,-400)==expected
    with pytest.raises(ValueError):q5_value(1,[1,1.2,1.1,1.3],-400)


def test_integer_tick_sampling_precedes_interpolation():
    project=dict(voice_parts=[dict(position=0)])
    a=dict(phrase_index=0,position_ms=10.,head_frames=0,tensors=[dict(name='f0',dtype='float32',shape=[1,2],values=[100,100])])
    curve=dict(xs=[0,5,10,15,20,25],ys=[0,-5,-10,-15,-20,0])
    result=sample_curve(project,a,curve)
    # 10ms -> round(9.6)=10tick; next model frame -> round(20.745...)=21tick.
    assert np.array_equal(result,np.array([-10,-16],np.float32))


def test_variance_converts_double_interpolation_before_float32():
    project=dict(voice_parts=[dict(position=0)])
    a=dict(phrase_index=0,position_ms=8/.96,head_frames=0,tensors=[dict(name='f0',dtype='float32',shape=[1,1],values=[100])])
    curve=dict(xs=[0,5,10,15],ys=[0,-25,-38,0])
    # 8 tick interpolates -32.8c, exposing the same rounding-order risk as old C.
    cents=sample_curve(project,a,curve)
    semi=sample_curve(project,a,curve,unit='semitones')
    assert cents[0]==np.float32(-32.8) and semi[0]==np.float32(-.328)
    assert semi[0]!=cents[0]/np.float32(100)


def test_support_escape_and_missing_peak_stop_without_adjusting_geometry():
    case=load_sealed_protocol()['cases'][0]
    a=dict(position_ms=case['shifted_support_s'][0]*1000-20,head_frames=0,frame_ms=11.609978)
    with pytest.raises(ValueError,match='support'):check_sample_support(a,np.array([-400,0],np.float32),case)
    with pytest.raises(ValueError,match='peak'):check_sample_support(a,np.array([-399,0],np.float32),case)
