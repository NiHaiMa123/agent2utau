import importlib.util
from pathlib import Path
import numpy as np
import pytest
from scipy.interpolate import CubicHermiteSpline
P=Path(__file__).resolve().parents[1]/'skills/singing-expression-editor/scripts/sparse_contour.py'
s=importlib.util.spec_from_file_location('sparse',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_asymmetric_shallow_turns_survive_with_physical_times():
 t=np.arange(0,.71,.01);y=np.interp(t,[0,.12,.20,.39,.53,.70],[0,16,-10,7,-24,0])
 nodes=m.sparse_nodes(t,y,2,.025);x=np.array([n['time_s'] for n in nodes]);v=np.array([n['cents'] for n in nodes]);d=np.array([n['slope_c_per_s'] for n in nodes])
 assert any(abs(x-.12)<.011) and any(abs(x-.53)<.011)
 pred=CubicHermiteSpline(x,v,d)(np.linspace(0,.7,1001))
 assert pred.max()<=16.00001 and pred.min()>=-24.00001
 assert d[0]==d[-1]==0 and len(nodes)<len(t)/2

def test_native_connection_units_and_no_snap():
 n=m.note_connection([(2.0,6400),(2.08,6665),(2.15,6671),(2.22,6800)],2.075,68)
 assert not n['snap_first'] and n['data'][0]['x']==pytest.approx(-75)
 assert n['data'][0]['y']==-40 and n['data'][-1]['y']==0
 assert all(q['shape']=='io' for q in n['data'])

def test_monotonic_internal_slopes_are_not_forced_to_stop():
 n=m.sparse_nodes([0,.1,.2,.3,.4],[0,8,21,34,40],.1,.02)
 assert any(q['slope_c_per_s']>0 for q in n[1:-1])

def test_invalid_time_or_connection_is_rejected():
 with pytest.raises(ValueError):m.sparse_nodes([0,0],[0,2])
 with pytest.raises(ValueError):m.note_connection([(0,6000),(0,6400)],0,64)

def test_route_executor_consumes_slopes_and_legacy_default_stays_exact():
 from agent2utau.expression.enveloped_landmarks import enveloped_landmarks
 t=np.array([.25]);x=[0,.2,.4,.6];v=[0,10,30,0]
 legacy=enveloped_landmarks(t,x,v,0,.1,.5,.6)
 zero=enveloped_landmarks(t,x,v,0,.1,.5,.6,[0,0,0,0])
 route=enveloped_landmarks(t,x,v,0,.1,.5,.6,[0,80,0,0])
 np.testing.assert_array_equal(legacy,zero)
 assert abs(float(route[0]-legacy[0]))>2
 with pytest.raises(ValueError):enveloped_landmarks(t,x,v,0,.1,.5,.6,[0,1])
