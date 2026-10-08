import copy
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

SPEC=importlib.util.spec_from_file_location('design_functions',Path(__file__).parents[1]/'skills/singing-expression-editor/scripts/design_functions.py')
F=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(F)


def plan():
    return {'schema':1,'origin':'agent_designed','support_s':[0.,1.5],
            'center_nodes':[[0.,6000.,0.],[1.5,6000.,0.]],'components':[],
            'decisions':[{'support_s':[0.,1.5],'condition':'synthetic sustained vowel, neutral musical center',
                          'choice':'explicit hold','alternative':'continuous oscillation',
                          'reason':'test the selected hold, no source musical acceptance',
                          'uncertainty':'synthetic clock only','component_ids':[]}],
            'expectations':[{'support_s':[.3,1.2],'range_c':[0.,0.],'purpose':'chosen hold remains flat'}]}


def test_hermite_preserves_nonzero_middle_slope_and_matches_real_context_interface():
    from agent2utau.expression.context_actions import context_target
    p=plan();p['center_nodes']=[[0.,6000.,0.],[.5,6080.,220.],[1.5,6400.,0.]]
    p['expectations'][0]['range_c']=[0,500]
    t=np.linspace(0,1.5,1501)
    p_native={'note_targets':[{'note_index':0,'target_tone':60}], 'groups':[{'primary_index':0}],
              'phone_geometry':[], 'melody_nodes':[{'anchor':{'kind':'phrase_start','offset_s':x},'cents':y,'slope_c_per_s':d} for x,y,d in p['center_nodes']],
              'budgets':dict(body=0,articulation=0,release=0,periodic=0),'events':[]}
    native=context_target([dict(note_index=0,primary_index=0,start_ms=0,end_ms=1500,tone=60)],p_native,t)['target']
    np.testing.assert_allclose([F.evaluate(p,x) for x in t],native,atol=2e-12,rtol=0)
    eps=1e-6
    assert (F.evaluate(p,.5+eps)-F.evaluate(p,.5-eps))/(2*eps)==pytest.approx(220,abs=.002)


def test_asymmetric_finite_return_has_exact_peak_and_smooth_support():
    c={'id':'return','family':'finite_return','support_s':[.2,.8],'peak_s':.35,'peak_c':-32.}
    assert F.component_value(c,.35)==-32
    assert F.component_value(c,.1)==F.component_value(c,.2)==F.component_value(c,.8)==F.component_value(c,1)==0
    eps=1e-6
    for t in [.2,.35,.8]:
        assert abs((F.component_value(c,t+eps)-F.component_value(c,t-eps))/(2*eps))<.001
    assert F.component_value(c,.275)==pytest.approx(-16)
    assert F.component_value(c,.575)==pytest.approx(-16)


def test_integrated_rate_is_physical_seconds_and_piecewise_continuous():
    n=[[1.,4.],[1.5,6.],[2.,5.]]
    assert F.integrated_rate(n,1.25)==pytest.approx(1.125)
    assert F.integrated_rate(n,1.5)==pytest.approx(2.5)
    assert F.integrated_rate(n,2.)==pytest.approx(5.25)
    eps=1e-6
    assert (F.integrated_rate(n,1.5+eps)-F.integrated_rate(n,1.5-eps))/(2*eps)==pytest.approx(6,abs=2e-6)
    assert F.integrated_rate(n,1.25)!=5*.25


def test_periodic_pause_and_independent_exit_do_not_stretch_phase():
    c={'id':'period','family':'oscillation','support_s':[0.,1.5],'attack_end_s':.15,'release_start_s':1.3,
       'depth_nodes':[[0.,20.],[.4,25.],[.6,0.],[.9,0.],[1.1,35.],[1.5,20.]],
       'rate_nodes':[[0.,5.],[1.5,6.]],'phase_rad':.25}
    assert F.component_value(c,.7)==0
    t=1.4;depth=F.smooth_value(c['depth_nodes'],t)
    # Integral 5t+t²/3; at midpoint of exit the quintic envelope is exactly .5.
    expected=.5*depth*math.sin(.25+2*math.pi*(5*t+t*t/3))
    assert F.component_value(c,t)==pytest.approx(expected,abs=1e-11)
    eps=1e-6
    assert abs(F.component_value(c,eps)/eps)<.001
    assert abs(F.component_value(c,1.5-eps)/eps)<.001


def test_body_expectation_rejects_flat_interior_despite_large_entry():
    p=plan();p['center_nodes']=[[0.,5800.,0.],[.2,6000.,0.],[1.5,6000.,0.]]
    p['expectations'][0]['range_c']=[30.,70.]
    out=F.compile_plan(p)
    assert max(out['cents'])-min(out['cents'])==200
    assert out['local_checks'][0]['observed_range_c']==0
    assert not out['shape_checks_pass']


def test_compilation_checks_the_actual_composed_curve_and_keeps_failures():
    p=plan();p['components']=[{'id':'r','family':'finite_return','support_s':[.3,1.2],'peak_s':.61,'peak_c':25}]
    p['decisions'][0]['component_ids']=['r'];p['expectations'][0]['range_c']=[24.,26.]
    out=F.compile_plan(p,.007)
    assert out['shape_checks_pass'] and .61 in out['times_s']
    p['components'].append(dict(p['components'][0],id='cancel',peak_c=-25))
    p['decisions'][0]['component_ids'].append('cancel')
    assert not F.compile_plan(p)['shape_checks_pass']


def test_origin_arrays_and_gaps_cannot_silently_enter_the_helper():
    p=plan();p['reference_samples']=[6000,6001]
    with pytest.raises(ValueError):F.compile_plan(p)
    p=plan();p['origin']='author_reconstruction'
    with pytest.raises(ValueError):F.compile_plan(p)
    p=plan();d=copy.deepcopy(p['decisions'][0]);p['decisions'][0]['support_s']=[0,.6];d['support_s']=[.7,1.5];p['decisions'].append(d)
    with pytest.raises(ValueError):F.compile_plan(p)


def test_unsupported_family_and_missing_component_decisions_are_errors():
    p=plan();p['components']=[{'id':'r','family':'borrowed_route'}]
    with pytest.raises(ValueError):F.compile_plan(p)
    p['components']=[{'id':'r','family':'finite_return','support_s':[.3,1.2],'peak_s':.6,'peak_c':20.}]
    with pytest.raises(ValueError):F.compile_plan(p)


def test_finite_design_is_stable_under_sampling_phase_without_claiming_native_safety():
    p=plan();p['components']=[{'id':'r','family':'finite_return','support_s':[.2,1.2],'peak_s':.5,'peak_c':28.}]
    p['decisions'][0]['component_ids']=['r'];p['expectations'][0]['range_c']=[0,30]
    times=np.arange(0,1.5,.005)
    before=np.array([F.evaluate(p,t) for t in times])
    after=np.array([F.evaluate(p,t+.0005) for t in times])
    assert np.max(abs(after-before))<.1
    out=F.compile_plan(p)
    assert out['native_written'] is out['audio_rendered'] is out['musical_quality_validated'] is False
