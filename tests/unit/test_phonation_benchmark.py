import numpy as np
import pytest
from agent2utau.evaluation.phonation_benchmark import SignalCase,cases,generate,measure
from agent2utau.evaluation.phonation import frame_features,PhonationConfig


def test_context_splits_do_not_leak_gain_or_noise_descendants():
    contexts={}
    for c in cases():contexts.setdefault(c.context_id,set()).add(c.split)
    assert len(cases())==324 and len(contexts)==54
    assert all(len(v)==1 for v in contexts.values())
    assert sum(c.split=='development' for c in cases())==108


def test_generator_preserves_component_snr_and_gain_without_hearing_labels():
    c=SignalCase(64,'B','steady',10,-18,104)
    y,t,f,r=generate(c);quiet,_,_,q=generate(SignalCase(64,'B','steady',10,-30,104))
    assert r['output_component_snr_db']==pytest.approx(10)
    assert r['achieved_rms_dbfs']==pytest.approx(-18)
    assert r['perceptual_label'] is r['physiological_label'] is None
    assert np.allclose(quiet,y*10**(-12/20),atol=1e-14)
    assert np.array_equal(generate(c)[0],y)


@pytest.mark.parametrize('midi',[57,64,71])
@pytest.mark.parametrize('filter_id',['A','B','C'])
def test_steady_noise_order_and_gain_invariance(midi,filter_id):
    rows=[measure(SignalCase(midi,filter_id,'steady',s,-18,205),frame_features,PhonationConfig()) for s in [0,10,25]]
    assert all(r['reliable_frames']>10 for r in rows)
    assert rows[0]['features']['periodicity_ratio_db_proxy']<rows[1]['features']['periodicity_ratio_db_proxy']<rows[2]['features']['periodicity_ratio_db_proxy']
    quiet=measure(SignalCase(midi,filter_id,'steady',10,-30,205),frame_features,PhonationConfig())
    for k in ['periodicity_ratio_db_proxy','highband_flatness_db']:
        assert quiet['features'][k]==pytest.approx(rows[1]['features'][k],abs=1e-7)


def test_filter_surface_is_a_confound_not_a_new_breath_label():
    a=measure(SignalCase(64,'A','steady',25,-18,104),frame_features,PhonationConfig())
    b=measure(SignalCase(64,'B','steady',25,-18,104),frame_features,PhonationConfig())
    assert a['truth']['output_component_snr_db']==pytest.approx(b['truth']['output_component_snr_db'])
    assert abs(a['features']['highband_flatness_db']-b['features']['highband_flatness_db'])>3


def test_dynamic_signal_cannot_be_treated_as_stationary_noise():
    c=SignalCase(57,'A','glide',25,-18,104)
    old=measure(c,frame_features,PhonationConfig(local_f0_span_c=80))
    strict=measure(c,frame_features,PhonationConfig())
    assert old['reliable_frames']>0
    assert strict['reliable_frames']==0 and strict['features'] is None
    assert strict['excluded']['nonstationary_or_unsupported_window']>0
