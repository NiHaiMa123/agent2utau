"""Confounder rejection and level-independent spectrum discrimination."""
import copy
import numpy as np
import pytest
from agent2utau.evaluation.controlled_probe import require_isolation, require_shift_isolation, spectral_response


def native_pair():
    def tensor(name, x):
        return dict(name=name, dtype='float32', shape=[1, 4], values=x)
    a = dict(position_ms=1000, frame_ms=10, head_frames=0, tail_frames=0,
        sample_rate=44100, singer_location='test', acoustic_model='test', vocoder_model='test',
        acoustic_mel_base='e', vocoder_mel_base='e', phones=[], vocoder_f0=[500]*4,
        native_acoustic_cache_verified=True,
        native_variance_predictions={k:[-2]*4 for k in ('tension','breathiness','voicing')},
        expression_deltas=dict(tension=[0,1,1,0],breathiness=[0]*4,voicing=[0]*4),
        tensors=[tensor('tension',[-2,-1,-1,-2]),tensor('breathiness',[-2]*4),tensor('voicing',[-2]*4)])
    b=copy.deepcopy(a)
    b['expression_deltas']['tension']=[0]*4
    b['tensors'][0]['values']=[-2]*4
    v=dict(native_variance_cache_verified=True, model='same')
    return a,b,v,copy.deepcopy(v)


def test_single_channel_guard_and_time_scope():
    a,b,v,w=native_pair()
    result=require_isolation(a,b,v,w,'tension',[1.01,1.02])
    assert result['changed_frames']==2
    with pytest.raises(ValueError,match='escapes'):
        require_isolation(a,b,v,w,'tension',[1.015,1.02])


@pytest.mark.parametrize('confound',['phones','pitch','voicing','prediction','variance','cache'])
def test_confounder_refused(confound):
    a,b,v,w=native_pair()
    if confound=='phones': b['phones']=['changed']
    elif confound=='pitch': b['vocoder_f0'][1]=501
    elif confound=='voicing': b['tensors'][2]['values'][1]=-3
    elif confound=='prediction': b['native_variance_predictions']['tension'][1]=-3
    elif confound=='variance': w['model']='different'
    elif confound=='cache': b['native_acoustic_cache_verified']=False
    with pytest.raises(ValueError): require_isolation(a,b,v,w,'tension',[1,1.04])


def test_level_change_does_not_count_as_spectral_shape_change():
    a=np.zeros((1,4,3),np.float32); clock=np.arange(4)*.01
    level=spectral_response(a,a+2,clock,[0,.03])
    shape=spectral_response(a,a+np.array([0,1,2]),clock,[0,.03])
    assert level['log_mel_rms']==2 and level['level_removed_log_mel_rms']==0
    assert shape['level_removed_log_mel_rms']>0
    assert not shape['formant_truth'] and not shape['perceived_improvement']


def shifted_pair():
    a,b,_,_=native_pair()
    b=copy.deepcopy(a)
    for r in (a,b):
        r.update(tone_shift_cents=[0]*4,vocoder_pitch_controllable=True)
        r['tensors'].append(dict(name='f0',dtype='float32',shape=[1,4],values=[500]*4))
    b['tone_shift_cents']=[0,-400,-400,0]
    f=np.array([1,2**(-400/1200),2**(-400/1200),1],np.float32)*np.float32(500)
    b['tensors'][-1]['values']=f.tolist()
    # A derived prediction changes, while manual offsets are kept.
    b['native_variance_predictions']['tension']=[-2,-3,-3,-2]
    b['tensors'][0]['values']=[-2,-2,-2,-2]
    v=dict(frame_ms=10,head_frames=0,tail_frames=0,variance_model='test',
        variance_speaker_root='test',native_linguistic_cache='same',linguistic_tensors=[],
        native_variance_cache_verified=True,tone_shift_semitones=[0]*4,
        tensors=[dict(name='pitch',dtype='float32',shape=[1,4],values=[71]*4)])
    w=copy.deepcopy(v);w['tone_shift_semitones']=[0,-4,-4,0]
    w['tensors'][0]['values']=[71,67,67,71]
    return a,b,v,w


def test_shfc_allows_verified_derived_prediction_not_output_pitch():
    a,b,v,w=shifted_pair()
    result=require_shift_isolation(a,b,v,w,[1.01,1.02],-400)
    assert result['changed_variance_inputs']==['pitch']
    assert result['manual_controls_exact'] and result['vocoder_F0_exact']
    assert result['changed_frames']==2


@pytest.mark.parametrize('confound',['vocoder_pitch','phones','speaker','manual_control',
                                   'pitch_dependency','acoustic_dependency','units','support'])
def test_shfc_confound_or_wrong_unit_refused(confound):
    a,b,v,w=shifted_pair();peak=-400;support=[1.01,1.02]
    if confound=='vocoder_pitch': b['vocoder_f0'][1]=400
    elif confound=='phones': b['phones']=['changed']
    elif confound=='speaker': w['tensors'].append(dict(name='spk_embed',dtype='float32',shape=[1],values=[1]))
    elif confound=='manual_control': b['expression_deltas']['tension'][1]=2
    elif confound=='pitch_dependency': w['tensors'][0]['values'][1]=68
    elif confound=='acoustic_dependency': b['tensors'][-1]['values'][1]=500
    elif confound=='units': peak=-4
    elif confound=='support': support=[1.015,1.02]
    with pytest.raises(ValueError): require_shift_isolation(a,b,v,w,support,peak)
