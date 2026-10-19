import copy
import numpy as np
import pytest

from agent2utau.evaluation.phonation import (PhonationConfig, frame_features,
    measure_regions, conditioned_scores, phrase_summaries)


def signal(f0=250, noise=0, gain=.12, sr=16000, seconds=.2):
    t=np.arange(round(sr*seconds))/sr
    y=sum(np.sin(2*np.pi*k*f0*t)/k for k in range(1,16) if k*f0<sr/2)
    y+=noise*np.random.default_rng(17).normal(size=len(t))
    return y*gain


def test_periodic_plus_noise_orders_proxies_and_gain_is_not_firmness():
    a=frame_features(signal(noise=.02),16000,250)
    b=frame_features(signal(noise=.6),16000,250)
    assert a['periodicity_ratio_db_proxy']>b['periodicity_ratio_db_proxy']+8
    assert b['highband_flatness_db']>a['highband_flatness_db']+5
    quiet=frame_features(signal(noise=.6,gain=.012),16000,250)
    for k in ['periodicity_ratio_db_proxy','highband_flatness_db','output_spectral_tilt_db_oct']:
        assert quiet[k]==pytest.approx(b[k],abs=1e-7)
    assert quiet['rms_dbfs']==pytest.approx(b['rms_dbfs']-20)


@pytest.mark.parametrize('f0',[200,350,600])
def test_period_lag_follows_supplied_frequency(f0):
    clean=frame_features(signal(f0=f0,noise=.01),16000,f0)
    noisy=frame_features(signal(f0=f0,noise=.5),16000,f0)
    assert clean['period_lag_ncc']>noisy['period_lag_ncc']


def test_silence_nonfinite_and_clipped_unknown():
    assert frame_features(np.zeros(1000),16000,250)['reason']=='silence_or_low_level'
    assert frame_features(np.full(1000,np.nan),16000,250)['status']=='unknown'
    assert frame_features(signal(gain=2),16000,250)['reason']=='clipping_risk'


def test_absent_highband_is_not_mislabeled_as_flat_noise():
    t=np.arange(8000)/16000
    r=frame_features(.1*np.sin(2*np.pi*250*t),16000,250)
    assert r['status']=='unknown' and r['reason']=='unresolved_highband_energy'


def tracks(f0=250, seconds=.6):
    t=np.arange(0,seconds,.01)
    return (t,np.full(len(t),f0),np.ones(len(t),bool))


def test_actual_vowel_boundary_and_disagreement_refusals():
    audio=signal(seconds=.6);regions=[dict(id='u',phrase_id='s1',phone='zh/a',support_s=[.1,.5])]
    good=measure_regions(audio,16000,0,regions,[tracks(),tracks()])[0]
    assert good['status']=='measured'
    assert good['excluded_frames']['crosses_vowel_boundary']>0
    assert all(.1+8/250/2<=f['time_s']<=.5-8/250/2 for f in good['frames'])
    bad=measure_regions(audio,16000,0,regions,[tracks(),tracks(500)])[0]
    assert bad['status']=='unknown' and bad['body'] is None
    assert bad['excluded_frames']['F0_disagreement']>0


def test_fricative_never_a_breathy_vowel_and_short_phone_unknown():
    regions=[dict(id='f',phrase_id='s1',phone='zh/sh',support_s=[.1,.3]),dict(id='v',phrase_id='s1',phone='zh/a',support_s=[.31,.33])]
    rows=measure_regions(signal(seconds=.6),16000,0,regions,[tracks(),tracks()])
    assert rows[0]['status']=='excluded' and rows[0]['frames']==[]
    assert rows[1]['status']=='unknown'


def word(ident, phone='zh/a', pitch=60, periodicity=10, flatness=-12, phrase='s1'):
    return dict(id=ident,phone=phone,phrase_id=phrase,median_midi=pitch,status='measured',body=dict(periodicity_ratio_db_proxy=periodicity,highband_flatness_db=flatness,output_spectral_tilt_db_oct=-8,rms_dbfs=-20))


def test_no_self_reference_vowel_or_register_shortcut():
    anchors=[word('a'),word('b')];rows=[word('a'),word('wrong_vowel','zh/i'),word('too_high',pitch=68)]
    scores=conditioned_scores(rows,anchors)
    assert scores[0]['reference_ids']==['b']
    assert scores[1]['status']==scores[2]['status']=='unknown'
    assert conditioned_scores([word('a')],[word('a')])[0]['status']=='unknown'


def test_separate_axes_do_not_make_a_perceptual_score_or_phrase_pass():
    anchors=[word('anchor')];strong=word('s',periodicity=16,flatness=-18);soft=word('w',periodicity=4,flatness=-6)
    scores=conditioned_scores([strong,soft],anchors)
    assert all(s['relative_firmness_proxy'] is None and s['firmness_assessment'] is None for s in scores)
    assert scores[0]['axis_contrasts']['periodicity_ratio_db_proxy']['change']==6
    assert scores[1]['axis_contrasts']['periodicity_ratio_db_proxy']['change']==-6
    assert scores[0]['consistency_distance_proxy']==pytest.approx(scores[1]['consistency_distance_proxy'])
    rows=[strong,word('unknown','zh/i')];scores=conditioned_scores(rows,anchors);summary=phrase_summaries(rows,scores,['s1'])[0]
    assert summary['comparable_fraction']==.5
    assert summary['status']=='insufficient_matched_coverage'
    assert summary['perceptual_consistency']=='unvalidated'


def test_center_agreement_does_not_override_window_disagreement():
    t=np.arange(0,.6,.01);f=np.full(len(t),250.);g=f.copy()
    g[::2]*=2**(60/1200)
    regions=[dict(id='u',phrase_id='s1',phone='zh/a',support_s=[.1,.5])]
    # Allow each track's motion to isolate the cross-track window check.
    rows=measure_regions(signal(seconds=.6),16000,0,regions,[(t,f,np.ones(len(t),bool)),(t,g,np.ones(len(t),bool))],PhonationConfig(local_f0_span_c=100))
    assert rows[0]['status']=='unknown'


def test_invalid_overlap_or_audio_clock_rejected():
    regions=[dict(id='v',phrase_id='s1',phone='zh/a',support_s=[0,.4])]
    with pytest.raises(ValueError):measure_regions(signal(seconds=.6),16000,.1,regions,[tracks(),tracks()])
    regions.append(dict(id='v2',phrase_id='s1',phone='zh/a',support_s=[.3,.5]))
    with pytest.raises(ValueError):measure_regions(signal(seconds=.6),16000,0,regions,[tracks(),tracks()])


@pytest.mark.parametrize('kwargs',[dict(periods=2),dict(hop_s=0),dict(min_body_frames=1),dict(robust_scale_floor_db=0),dict(min_phrase_matched_fraction=2)])
def test_invalid_config(kwargs):
    with pytest.raises(ValueError):PhonationConfig(**kwargs)
