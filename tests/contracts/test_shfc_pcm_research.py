import math
import sys
from pathlib import Path
import numpy as np
import pytest

HERE=Path(__file__).resolve().parents[2]/'research/table2-confirmation'
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from shfc_pcm_checks import (dynamic_gain,require_dynamics,interval_indices,level,
                             centered_windows,require_finite_subfull)
from observe_stage_2e_paths import f0_compare

def test_ceil_clock_half_open_never_fills_outside_boundary():
    assert interval_indices((.01001,.03001),0,44100)==(442,1324)
    assert interval_indices((9.01001,9.03001),9,44100)==(442,1324)
    # ceil(-0.441)==0: this interval contains no negative-index sample.
    assert interval_indices((-.00001,.01),0,44100)==(0,441)
    assert interval_indices((-.00003,.01),0,44100) is None
    assert interval_indices((0,1.00001),0,44100) is None

@pytest.mark.parametrize('width',[30,50])
def test_center_windows_known_constant_and_short_unknown(width):
    wave=np.full(44100,.5,np.float64)
    result=centered_windows(wave,(.1,.2),0,width)
    assert result['status']=='computed_proxy_only'
    assert np.all(np.array(result['rms'])==.5) and np.all(np.array(result['peak'])==.5)
    assert centered_windows(wave,(0,.020),0,width)['status']=='unknown_short_window'

def test_zero_energy_is_zero_with_null_db():
    m=level(np.zeros(100))
    assert m['zero_energy'] and m['rms']==0 and m['dbfs'] is None

def test_dynamic_curve_reconstruction_and_ulp_failure():
    layout=dict(samples=1000,dynamic_curve=[.5,1.,.75],dynamic_start_tick=0,
        dynamic_end_ms=[5*(60000/120/480),10*(60000/120/480),15*(60000/120/480)],position_ms=0.,leading_ms=0.)
    gain=dynamic_gain(layout)
    assert gain.dtype==np.float32 and gain[0]==np.float32(.5)
    # Native interval endpoints truncate: int(5.20833ms*44.1)==229.
    assert gain[228]<1 and gain[229]==1 and gain[-1]==1
    raw=np.full(1000,.21,np.float32);actual=raw*gain; require_dynamics(raw,actual,gain)
    actual[9]=np.nextafter(actual[9],np.float32(1))
    with pytest.raises(ValueError,match='multiplication'):require_dynamics(raw,actual,gain)
    layout['dynamic_end_ms'][0]+=.001
    with pytest.raises(ValueError,match='clock'):dynamic_gain(layout)

@pytest.mark.parametrize('bad',[np.nan,np.inf,1.,-1.])
def test_nonfinite_or_fullscale_stops_delivery(bad):
    with pytest.raises(ValueError):require_finite_subfull(np.array([0.,bad]))

def test_missing_dynamic_curve_requires_empty_clock():
    assert np.all(dynamic_gain(dict(samples=10,dynamic_curve=None,dynamic_end_ms=[]))==1)
    with pytest.raises(ValueError):dynamic_gain(dict(samples=10,dynamic_curve=None,dynamic_end_ms=[1]))

def test_f0_no_interpolation_over_uv_or_nonfinite():
    a=dict(times=np.arange(5,dtype=np.float32)*.01,f0_hz=np.array([400,400,0,400,400],np.float32),voiced=np.array([1,1,0,1,1],bool))
    b=dict(times=a['times'].copy(),f0_hz=np.array([400,800,800,np.nan,800],np.float32),voiced=np.ones(5,bool))
    r=f0_compare(a,b,(0,.05),0)
    assert r['valid_pair_frames']==3 and r['cents']['median']==1200
    assert r['true_F0_fixed']=='unknown'
    b['voiced'][1]=False
    assert f0_compare(a,b,(0,.05),0)['status']=='unknown_insufficient_coverage'
    b['times'][2]=np.nextafter(b['times'][2],np.float32(1))
    with pytest.raises(ValueError,match='clocks'):f0_compare(a,b,(0,.05),0)
