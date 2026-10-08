"""Confounder rejection and level-independent spectrum discrimination."""
import copy
import numpy as np
import pytest
from agent2utau.evaluation.controlled_probe import require_isolation, spectral_response


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
