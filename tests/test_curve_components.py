import numpy as np
import pytest
from agent2utau.expression.curve_components import LocalGesture,VibratoSegment,compose_curve

def test_c1_join_and_finite_support_for_overlapping_events():
    t=np.linspace(0,2,20001)
    g=LocalGesture(.6,.83,1.3,-45,'preparation_candidate')
    v=VibratoSegment(.4,.7,1.5,1.8,20,40,5,6,.2)
    y=compose_curve(t,[0,1,2],[6000,6300,6200],[0,30,0],gestures=[g],vibratos=[v])
    for boundary in (.4,.6,.7,.83,1,1.3,1.5,1.8):
        local=np.array([boundary-1e-6,boundary,boundary+1e-6])
        values=compose_curve(local,[0,1,2],[6000,6300,6200],[0,30,0],gestures=[g],vibratos=[v])
        left=(values[1]-values[0])/1e-6;right=(values[2]-values[1])/1e-6
        assert abs(left-right)<.1
    assert g.evaluate(np.array([0,2])).tolist()==[0,0]
    assert v.evaluate(np.array([0,2])).tolist()==[0,0]

def test_no_pitch_written_through_unvoiced_gap_and_transpose_equivariance():
    t=np.linspace(0,1,101);uv=(t>.4)&(t<.6)
    a=compose_curve(t,[0,1],[6000,6300],[0,0],voiced=~uv)
    b=compose_curve(t,[0,1],[6400,6700],[0,0],voiced=~uv)
    assert np.isnan(a[uv]).all()
    np.testing.assert_allclose(b[~uv]-a[~uv],400,atol=1e-8)

def test_curve_requires_complete_base_and_ordered_event_support():
    with pytest.raises(ValueError):compose_curve([0,1],[.1,1],[6000,6200],[0,0])
    with pytest.raises(ValueError):LocalGesture(1,0,2,20).evaluate([0,1])
    with pytest.raises(ValueError):VibratoSegment(0,.8,.5,1,20,30,5,6).evaluate([0,1])
