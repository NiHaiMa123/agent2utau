import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'skills/singing-expression-editor/scripts/compile_control_overlay.py'
spec=importlib.util.spec_from_file_location('control_overlay',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
D={k:dict(min=0 if k=='voic' else -100,max=100,default_value=100 if k=='voic' else 0) for k in ['tenc','brec','voic']}
def event(channel='tenc',delta=20):
 return dict(channel=channel,purpose='finite vowel support',allowed_ms=[100,700],nodes=[dict(anchor='v',offset_ms=x,delta=y) for x,y in [(0,0),(200,delta),(600,0)]])
def test_restore_actual_baseline_and_preserve_other_channels():
 source=[dict(abbr='tenc',xs=[0,800],ys=[-10,-10]),dict(abbr='pitd',xs=[0,99],ys=[3,8])]
 out,tr=m.compile_overlay(source,[event()],{'v':100},lambda x:x,D)
 assert out[1]==source[1] and source[0]['ys']==[-10,-10]
 c=out[0]
 assert [m.linear(c['xs'],c['ys'],x,0) for x in [0,100,300,700,800]]==[-10,-10,10,-10,-10]
 assert tr[0]['resolved_ms']==[100,300,700]
def test_voicing_default_is_100_and_cannot_be_boosted():
 out,_=m.compile_overlay([],[event('voic',-8)],{'v':100},lambda x:x,D)
 assert out[0]['ys']==[100,100,92,100,100]
 with pytest.raises(ValueError,match='native range'):m.compile_overlay([],[event('voic',8)],{'v':100},lambda x:x,D)
def test_reject_unplanned_collisions_and_overlap():
 with pytest.raises(ValueError,match='collide'):m.compile_overlay([],[event()],{'v':100},lambda x:x*.001,D)
 with pytest.raises(ValueError,match='overlap'):m.compile_overlay([],[event(),event()],{'v':100},lambda x:x,D)
def test_protect_support_and_require_return():
 e=event();e['allowed_ms']=[150,700]
 with pytest.raises(ValueError,match='phone support'):m.compile_overlay([],[e],{'v':100},lambda x:x,D)
 e=event();e['nodes'][-1]['delta']=1
 with pytest.raises(ValueError,match='baseline return'):m.compile_overlay([],[e],{'v':100},lambda x:x,D)
def test_reject_speaker_or_pitch_conditioning_shortcuts():
 with pytest.raises(ValueError,match='Unsupported'):m.compile_overlay([],[event('shfc')],{'v':100},lambda x:x,D)
def test_reject_ambiguous_nondefault_baseline_extension():
 with pytest.raises(ValueError,match='baseline edge'):
  m.compile_overlay([dict(abbr='tenc',xs=[0,200],ys=[10,10])],[event()],{'v':100},lambda x:x,D)
