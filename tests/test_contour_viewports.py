"""Check physical display invariants, not expression quality."""
import importlib.util,json,math,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('viewports',ROOT/'skills/singing-expression-editor/scripts/contour_viewports.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class PhysicalDisplayTests(unittest.TestCase):
 def test_period_and_amplitude_survive_quiet_and_deep_views(self):
  t=[i/1000 for i in range(401)]
  for amplitude in [3.,100.]:
   c={'id':'unseen','times_s':t,'cents':[6400+amplitude*math.sin(2*math.pi*5*x) for x in t]}
   _,m=mod.viewport(c,0,.4,960,30)
   xy=m['pitch_coordinates'];self.assertAlmostEqual(xy[250][2]-xy[50][2],192.)
   self.assertAlmostEqual(xy[150][3]-xy[50][3],2*amplitude*.3)
   self.assertEqual([p[:2] for p in xy],list(map(list,zip(t,c['cents']))))
 def test_full_coverage_and_partial_last_view(self):
  c={'id':'unseen','times_s':[2+i*.1 for i in range(24)],'cents':[6400]*24}
  with tempfile.TemporaryDirectory() as d:
   m=mod.atlas({'curves':[c]},d,1,960,30)
   self.assertEqual(len(m),3);self.assertEqual(set(i for v in m for i in v['sample_indices']),set(range(24)))
   self.assertEqual(m[-1]['start_s'],4.);self.assertEqual(m[-1]['end_s'],5.)
   self.assertIn('max-width:none',(Path(d)/'index.html').read_text(encoding='utf-8'))
 def test_invalid_geometry_cannot_silently_plot(self):
  for c in [{'times_s':[0,0],'cents':[0,1]},{'times_s':[0,1],'cents':[0,float('nan')]},
            {'times_s':[0,1],'cents':[0,1],'before_cents':[0,float('inf')]}]:
   with self.assertRaises(ValueError):mod.checked(c)
  with self.assertRaises(ValueError):mod.atlas({'curves':[]},'unused',float('nan'))
 def test_scales_are_independent_of_pitch_span(self):
  for y in [[6400,6401,6500],[1000,6401,12000]]:
   _,m=mod.viewport({'id':'unseen','times_s':[0,.1,.2],'cents':y},0,.2,800,40)
   p=m['pitch_coordinates'][1];self.assertAlmostEqual(p[2],152.)
   self.assertAlmostEqual(p[3],44+(m['cents_high']-6401)*.4)
if __name__=='__main__':unittest.main()
