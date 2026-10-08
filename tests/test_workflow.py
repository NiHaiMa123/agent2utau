"""Verify explicit plans, native encoding and fresh source-only behavior."""
import copy, json
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from agent2utau import workflow as w
from agent2utau.openutau.ustx import save_ustx, load_ustx, sha256

def setup_case(tmp_path, monkeypatch):
    source=tmp_path/'source.wav';sf.write(source,np.zeros(4410),44100)
    project=tmp_path/'score.ustx'
    save_ustx(dict(resolution=480,tempos=[dict(position=0,bpm=120)],expressions={'pitd':dict(min=-1200,max=1200)},voice_parts=[dict(position=0,notes=[dict(position=0,duration=960,tone=60,lyric='a',pitch={'data':[]},vibrato={'length':30})],curves=[dict(abbr='pitd',xs=[0],ys=[999]),dict(abbr='tenc',xs=[0,960],ys=[-9,-9])])]),project)
    design=dict(schema=1,origin='agent_designed',support_s=[0.,1.],center_nodes=[[0.,6000.,0.],[1.,6060.,0.]],components=[],
      decisions=[dict(support_s=[0.,1.],condition='synthetic vowel',choice='rising center',alternative='hold',reason='verify own selected movement',uncertainty='synthetic only',component_ids=[])],expectations=[dict(support_s=[0.,1.],range_c=[60.,60.],purpose='chosen center rises 60 cents')])
    plan=dict(schema_version=1,project='score.ustx',source_audio='source.wav',input_hashes={'score.ustx':sha256(project),'source.wav':sha256(source)},scope='whole_song',phrases=[dict(part_index=0,position=0,design=design)])
    planfile=tmp_path/'functions.json';w.write_json(planfile,plan)
    def bridge(cfg,args):
        doc=load_ustx(args[args.index('--project')+1]);part=doc['voice_parts'][0];output=Path(args[args.index('--out')+1])
        if args[0]=='export-pitch':
            c=next((c for c in part['curves'] if c['abbr']=='pitd'),None)
            final=(6000+np.interp(np.arange(0,961,5),c['xs'],c['ys'])).tolist() if c else [6000.]*193
            result={'phrases':[dict(part_position=0,position=0,times_ms=(np.arange(0,961,5)/.96).tolist(),pitch_start_tick=0,pitch_interval_ticks=5,before_pitd_cents=[6000.]*193,final_cents=final)]}
        else: result={'parts':[dict(notes=[dict(tone=60)],phrases=[dict(phones=['a'],final_cents=[])])]}
        w.write_json(output,result);return {'ok':True}
    monkeypatch.setattr(w,'run_bridge',bridge)
    return planfile,project,plan

def test_complete_design_encodes_own_target_and_keeps_controls(tmp_path,monkeypatch):
    planfile,project,_=setup_case(tmp_path,monkeypatch);before=sha256(project)
    report=w.compile_functions(planfile,tmp_path/'compiled',{})
    assert report['native_max_error_c']<=.5 and not report['audio_rendered']
    doc=load_ustx(report['project']);curves=doc['voice_parts'][0]['curves']
    assert next(c for c in curves if c['abbr']=='pitd')['ys'][0]==0
    assert next(c for c in curves if c['abbr']=='pitd')['ys'][-1]==60
    assert next(c for c in curves if c['abbr']=='tenc')['ys']==[-9,-9]
    assert sha256(project)==before and doc['voice_parts'][0]['notes'][0]['vibrato']['length']==0

def test_changed_source_and_missing_phrase_are_rejected(tmp_path,monkeypatch):
    path,_,plan=setup_case(tmp_path,monkeypatch);plan['phrases']=[];w.write_json(path,plan)
    with pytest.raises(ValueError,match='coverage'): w.compile_functions(path,tmp_path/'bad',{})
    plan['input_hashes']['source.wav']='0'*64;w.write_json(path,plan)
    with pytest.raises(ValueError,match='Changed input'): w.compile_functions(path,tmp_path/'changed',{})

def test_no_author_samples_or_unknown_function_fields(tmp_path,monkeypatch):
    path,_,plan=setup_case(tmp_path,monkeypatch);plan['phrases'][0]['design']['profile']='author.npy';w.write_json(path,plan)
    with pytest.raises(ValueError,match='imported profiles'): w.compile_functions(path,tmp_path/'bad',{})

def test_observer_only_decodes_when_no_model_steps_selected(tmp_path,monkeypatch):
    source=tmp_path/'source.wav';sf.write(source,np.zeros(100),44100)
    from agent2utau.audio import decode
    monkeypatch.setattr(decode,'decode',lambda src,dst:Path(dst).write_bytes(Path(src).read_bytes()))
    report=w.observe_source(source,tmp_path/'fresh',{},[])
    manifest=json.loads((tmp_path/'fresh/manifest.json').read_text())
    assert manifest['source_sha256']==sha256(source) and not report['expression_generated']
    with pytest.raises(FileExistsError): w.observe_source(source,tmp_path/'fresh',{},[])

def test_fixed_mix_keeps_selected_gain_and_refuses_clipping(tmp_path):
    from agent2utau.audio.mix import mix
    for name in ['v.wav','b.wav']: sf.write(tmp_path/name,np.full(100,.1),44100,subtype='FLOAT')
    result=mix(tmp_path/'v.wav',tmp_path/'b.wav',tmp_path/'out.wav',vocal_gain_db=0,accomp_gain_db=0)
    data,_=sf.read(tmp_path/'out.wav');assert np.max(abs(data-.2))<2**-23 and not result['normalized']
    with pytest.raises(ValueError,match='clip'): mix(tmp_path/'v.wav',tmp_path/'b.wav',tmp_path/'bad.wav',vocal_gain_db=20,accomp_gain_db=20)
