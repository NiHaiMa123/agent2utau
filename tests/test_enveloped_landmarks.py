import numpy as np
import pytest
from agent2utau.expression.enveloped_landmarks import enveloped_landmarks


def test_actual_peak_trough_values_preserve_half_range_and_order():
    # Huahai le's first two cycles, relative to written 6500c center.
    x=[-.19,-.09,0,.10,.1916666667,.2916666667,.3666666667,.45,.55]
    y=[16,-10,16,-10,7,-7,15,-32,24]
    t=np.array([0,.10,.1916666667,.2916666667,.3666666667])
    v=enveloped_landmarks(t,x,y,-.08,-.02,.39,.53)
    np.testing.assert_array_equal(v,[16,-10,7,-7,15])
    assert (min(v[0],v[2])-v[1])/2==8.5
    assert (min(v[2],v[4])-v[3])/2==7


def test_fade_keeps_same_phase_and_c1_zero_endpoints():
    x=np.arange(-.2,1.41,.1);y=np.where(np.arange(len(x))%2==0,20,-13)
    t=np.linspace(0,1.07,10701)
    full=enveloped_landmarks(t,x,y,0,.03,1.05,1.07)
    faded=enveloped_landmarks(t,x,y,0,.03,.86,1.07)
    z=np.clip((1.07-t)/(1.07-.86),0,1);env=z**3*(10-15*z+6*z*z)
    np.testing.assert_allclose(faded[t<1.05],(full*env)[t<1.05],atol=1e-12)
    assert faded[0]==faded[-1]==0
    h=1e-6
    near=enveloped_landmarks([h,1.07-h],x,y,0,.03,.86,1.07)
    assert np.max(abs(near))/h<.001
    np.testing.assert_array_equal(faded[::11],enveloped_landmarks(t[::11],x,y,0,.03,.86,1.07))


def test_missing_phase_tail_cannot_be_stretched_or_extrapolated():
    with pytest.raises(ValueError,match='continuation'):
        enveloped_landmarks([0,.1,.6],[0,.1,.4],[10,-10,10],0,.03,.5,.6)
