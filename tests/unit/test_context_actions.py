import numpy as np
import pytest
from agent2utau.expression.context_actions import context_target

def anchor(kind,index=None,offset_s=0):return dict(kind=kind,index=index,offset_s=offset_s)

def fixture():
    notes=[dict(note_index=0,primary_index=0,start_ms=1000,end_ms=2500,tone=60)]
    p=dict(note_targets=[dict(note_index=0,target_tone=60)],groups=[dict(primary_index=0)],phone_geometry=[dict(phone_index=0,start_ms=900,end_ms=1000)],
        melody_nodes=[dict(anchor=anchor('phrase_start'),cents=6000),dict(anchor=anchor('phrase_end'),cents=6000)],budgets=dict(body=45,articulation=180,release=100,periodic=40),events=[])
    return notes,p


def test_sparse_route_consumes_monotonic_slope_and_continuous_support():
    n,p=fixture()
    points=[(0,0,0),(.2,10,80),(.4,30,0),(.6,0,0)]
    event=dict(id='route',kind='sparse_enveloped_route',execution_state='planned',
        start=anchor('note_start',0),end=anchor('note_start',0,.6),
        attack_end=anchor('note_start',0,.1),release_start=anchor('note_start',0,.5),
        nodes=[dict(anchor=anchor('note_start',0,x),cents=y,slope_c_per_s=d) for x,y,d in points])
    p['events']=[event];t=np.array([.9,1,1.2,1.25,1.4,1.6,1.7])
    r=context_target(n,p,t)
    u=.25;h=.2
    expected=(2*u**3-3*u**2+1)*10+(u**3-2*u**2+u)*h*80+(-2*u**3+3*u**2)*30
    assert r['target'][3]==pytest.approx(6000+expected,abs=1e-10)
    assert r['periodic'][0]==r['periodic'][1]==r['periodic'][-2]==r['periodic'][-1]==0
    np.testing.assert_array_equal(r['target'][::2],context_target(n,p,t[::2])['target'])
    # The legacy route must ignore new slope metadata, preserving prior results.
    p['events']=[dict(event,kind='enveloped_periodic_landmarks')]
    legacy=context_target(n,p,t)
    p['events']=[dict(event,nodes=[dict(k,slope_c_per_s=0) for k in event['nodes']])]
    np.testing.assert_array_equal(legacy['target'],context_target(n,p,t)['target'])
    assert abs(r['target'][3]-legacy['target'][3])>2

def test_native_phone_anchored_dip_and_c1_support():
    n,p=fixture();p['events']=[dict(id='dip',kind='local_gesture',channel='articulation',label='declared',execution_state='planned',start=anchor('phone_start',0),peak=anchor('phone_start',0,.05),end=anchor('phone_end',0,.1),amplitude_c=-70)]
    t=np.array([.85,.9,.900001,.95,1.099999,1.1,1.2,2.6]);r=context_target(n,p,t)
    assert r['target'][3]==5930 and r['articulation'][0]==r['articulation'][-1]==0
    assert abs(r['articulation'][2])/1e-6<.1 and abs(r['articulation'][4])/1e-6<.1
    n[0]['body_cents']=99999
    np.testing.assert_array_equal(r['target'],context_target(n,p,t)['target'])

def test_variable_periodic_integrates_physical_rate():
    n,p=fixture();p['events']=[dict(id='v',kind='dynamic_periodic',execution_state='planned',start=anchor('note_start',0),attack_end=anchor('note_start',0,.1),release_start=anchor('note_end',0,-.1),end=anchor('note_end',0),depth_start_c=10,depth_end_c=30,rate_start_hz=4,rate_end_hz=6,phase_rad=.2)]
    t=np.linspace(.9,2.6,1701);r=context_target(n,p,t);k=np.argmin(abs(t-1.75));x=t[k]-1.;duration=1.5
    expected=(10+20*x/duration)*np.sin(.2+2*np.pi*(4*x+.5*2*x*x/duration))
    assert abs(r['periodic'][k]-expected)<1e-9 and np.max(abs(r['periodic']))<=30
    assert not r['periodic'][t<1].any() and not r['periodic'][t>2.5].any()

def test_sparse_body_landmarks_are_distinct_and_bounded():
    n,p=fixture();p['events']=[dict(id='body',kind='body_landmarks',execution_state='planned',start=anchor('note_start',0),end=anchor('note_end',0),nodes=[dict(anchor=anchor('note_start',0),cents=0),dict(anchor=anchor('note_start',0,.4),cents=14),dict(anchor=anchor('note_start',0,.8),cents=-8),dict(anchor=anchor('note_end',0),cents=0)])]
    r=context_target(n,p,[.9,1,1.4,1.8,2.5,2.6]);np.testing.assert_allclose(r['body'],[0,0,14,-8,0,0],atol=1e-9)

def test_missing_anchor_unsupported_and_stacking_cannot_be_hidden():
    n,p=fixture();p['melody_nodes'][0]['anchor']=anchor('phone_start',10)
    with pytest.raises(ValueError,match='Unknown phone'):context_target(n,p,[.9,1,2.5])
    n,p=fixture();p['events']=[dict(id='missing',execution_state='unsupported')]
    with pytest.raises(ValueError,match='Unsupported'):context_target(n,p,[.9,1,2.5])
    n,p=fixture();e=dict(id='one',kind='local_gesture',channel='body',label='arc',execution_state='planned',start=anchor('note_start',0),peak=anchor('note_start',0,.5),end=anchor('note_end',0),amplitude_c=30)
    p['events']=[e,dict(e,id='two')]
    with pytest.raises(ValueError,match='Stacked'):context_target(n,p,[.9,1,1.5,2.5])


def test_periodic_landmarks_preserve_local_cycles_across_continuation():
    from scipy.signal import find_peaks
    n,p=fixture()
    n=[dict(n[0],end_ms=1350),dict(n[0],note_index=1,start_ms=1350)]
    p['note_targets']=[dict(note_index=i,target_tone=60) for i in (0,1)]
    p['budgets']['body']=5
    offsets=[0,.10,.19,.29,.40,.52,.64]
    values=[0,14,-14,28,-22,9,0]
    p['events']=[dict(id='cycles',kind='periodic_landmarks',execution_state='planned',
        start=anchor('note_start',0),end=anchor('note_start',0,.64),
        nodes=[dict(anchor=anchor('note_start',0,x),cents=y) for x,y in zip(offsets,values)])]
    t=np.arange(.9,2.501,.001);r=context_target(n,p,t)
    crests=find_peaks(r['target'])[0];troughs=find_peaks(-r['target'])[0]
    np.testing.assert_allclose(t[crests],[1.10,1.29,1.52],atol=1e-10)
    np.testing.assert_allclose(t[troughs],[1.19,1.40],atol=1e-10)
    np.testing.assert_allclose(np.diff(t[crests]),[.19,.23],atol=1e-10)
    assert not r['body'].any() and not r['periodic'][t<1].any()
    # A note continuation inside a cycle must not reset or flatten it.
    unsplit_notes,unused=fixture()
    unsplit_plan=dict(p,note_targets=[dict(note_index=0,target_tone=60)])
    np.testing.assert_array_equal(r['target'],context_target(unsplit_notes,unsplit_plan,t)['target'])
    shifted=context_target(n,p,t[::5])
    np.testing.assert_array_equal(shifted['target'],r['target'][::5])


def test_periodic_landmark_budget_cannot_use_body_allowance():
    n,p=fixture();p['budgets']['body']=90
    p['events']=[dict(id='large_cycle',kind='periodic_landmarks',execution_state='planned',
        start=anchor('note_start',0),end=anchor('note_end',0),
        nodes=[dict(anchor=anchor('note_start',0),cents=0),
               dict(anchor=anchor('note_start',0,.5),cents=41),
               dict(anchor=anchor('note_end',0),cents=0)])]
    with pytest.raises(ValueError,match='landmark budget'):context_target(n,p,[.9,1,1.5,2.5])
