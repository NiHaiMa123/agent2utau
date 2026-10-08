"""Frozen synthetic feature truth; none of these labels assert vocal naturalness."""
import copy, json
from pathlib import Path
import numpy as np
import pytest
import yaml
from agent2utau.evaluation.features import Thresholds, boundary_candidates, control_coupling, polyline_complexity, shape_features
from agent2utau.evaluation.independent import dump, evaluate
from agent2utau.openutau.ustx import sha256


def fixture(tmp_path):
    score=dict(resolution=480,tempos=[dict(position=0,bpm=120)],tracks=[dict(singer='synthetic')],expressions={},voice_parts=[dict(position=0,track_no=0,notes=[dict(position=0,duration=480,tone=60,lyric='a'),dict(position=480,duration=480,tone=60,lyric='+')],curves=[])],expectations=dict(amplitude='do not read me'))
    project=tmp_path/'synthetic.ustx';project.write_text(yaml.safe_dump(score),encoding='utf8')
    times=np.arange(0,1.001,.005);cents=6000+20*np.sin(2*np.pi*5*times)
    phones=[dict(phone_index=i,phoneme='zh/a',start_ms=i*500,end_ms=(i+1)*500,owner_primary_indices=[0],owner_note_indices=[i],ownership_status='matched',tone=60) for i in range(2)]
    ph=dict(position=0,pitch_times_ms=(times*1000).tolist(),final_cents=cents.tolist(),phones=phones)
    part=dict(part_position=0,track_no=0,notes=[dict(note_index=i,lyric=n['lyric'],tone=60,start_ms=i*500,end_ms=(i+1)*500,primary_index=0) for i,n in enumerate(score['voice_parts'][0]['notes'])],phrases=[ph])
    pitch=dict(schema_version=1,units='absolute MIDI times 100 cents; absolute project milliseconds',phrases=[dict(part_position=0,track_no=0,position=0,times_ms=(times*1000).tolist(),final_cents=cents.tolist(),before_pitd_cents=[6000.]*len(times))])
    phone_data=dict(schema_version=1,units='absolute project milliseconds; pitch absolute MIDI times 100 cents',parts=[part])
    pp=tmp_path/'pitch.json';hp=tmp_path/'phones.json';bp=tmp_path/'binding.json'
    dump(pp,pitch);dump(hp,phone_data)
    bind=dict(schema_version=1,project_sha256=sha256(project),pitch_sha256=sha256(pp),phonemes_sha256=sha256(hp),environment=dict(core_sha256='1'*64,bridge_sha256='2'*64,singer_id='synthetic',singer_config_sha256='3'*64))
    dump(bp,bind)
    return project,pp,hp,bp,bind


def test_platform_periodic_and_same_distribution_different_order():
    t=np.arange(0,2,.005);y=20*np.sin(2*np.pi*5*t)
    platform=shape_features(t,np.zeros(len(t)));periodic=shape_features(t,y)
    reordered=shape_features(t,np.sort(y))
    assert platform['morphology']=='platform' and periodic['morphology']=='oscillatory_candidate'
    assert len(periodic['cycles'])>=7 and not reordered['cycles']
    assert np.mean(y)==pytest.approx(np.mean(np.sort(y)))
    assert np.mean(y*y)==pytest.approx(np.mean(np.sort(y)**2))


def test_regular_variable_fading_descriptive_only():
    t=np.arange(0,3,.005)
    a=shape_features(t,25*np.sin(2*np.pi*5*t))
    b=shape_features(t,25*(1-.2*t)*np.sin(2*np.pi*(4*t+.3*t*t)))
    assert np.std([r['hz'] for r in a['cycles']])<.1
    assert np.std([r['hz'] for r in b['cycles']])>.2
    assert b['exit_range_c']<b['entry_range_c'] and 'good' not in b and 'bad' not in b


def test_sp_exclusion_and_transition():
    t=[0,.005,.01,.015,.02];y=[6000,6300,6000,6500,6500]
    rs=[dict(start_s=0,end_s=.012,region_type='non_singing'),dict(start_s=.012,end_s=.03,region_type='vowel')]
    r=boundary_candidates(t,y,rs)
    assert r['excluded_non_singing']==2
    assert any(f['code']=='non_singing_transition_risk' for f in r['findings'])
    assert not any(f['code']=='singing_boundary_risk' for f in r['findings'])


def test_same_vowel_continuation_not_split(tmp_path):
    project,pp,hp,bp,_=fixture(tmp_path)
    result=evaluate(project,tmp_path/'out',native_pitch=pp,phonemes=hp,provenance=bp)
    assert result['region_counts']['vowel']==3  # two raw phones, one merged vowel group
    regions=[json.loads(x) for x in (tmp_path/'out/regions.jsonl').read_text(encoding='utf8').splitlines()]
    groups=[r for r in regions if 'phone_ids' in r]
    assert len(groups)==1 and len(groups[0]['features']['cycles'])>=3


@pytest.mark.parametrize('failure',['project_hash','units','length','geometry','time_order'])
def test_wrong_native_data_refused(tmp_path,failure):
    project,pp,hp,bp,bind=fixture(tmp_path)
    p=json.loads(pp.read_text());h=json.loads(hp.read_text())
    if failure=='project_hash':bind['project_sha256']='0'*64
    elif failure=='units':p['units']='seconds, hz'
    elif failure=='length':p['phrases'][0]['before_pitd_cents'].pop()
    elif failure=='geometry':h['parts'][0]['notes'][0]['tone']=61
    else:p['phrases'][0]['times_ms'][1]=0;h['parts'][0]['phrases'][0]['pitch_times_ms'][1]=0
    dump(pp,p);dump(hp,h);bind['pitch_sha256']=sha256(pp);bind['phonemes_sha256']=sha256(hp);dump(bp,bind)
    with pytest.raises(ValueError):evaluate(project,tmp_path/'out',native_pitch=pp,phonemes=hp,provenance=bp)


def test_tempo_static_missing_native_and_bad_samples(tmp_path):
    project,_,_,_,_=fixture(tmp_path);d=yaml.safe_load(project.read_text());d['tempos'].append(dict(position=480,bpm=60));project.write_text(yaml.safe_dump(d))
    result=evaluate(project,tmp_path/'out')
    rows=[json.loads(x) for x in (tmp_path/'out/regions.jsonl').read_text().splitlines()]
    assert rows[1]['end_s']==pytest.approx(1.5)
    assert result['native_absolute_pitch']=='unavailable' and result['vowel_evaluation']['unknown']==2
    assert shape_features([],[])['status']=='unknown'
    assert shape_features([0,.1,.1],[1,2,3])['status']=='unknown'
    assert shape_features(np.arange(100)*.005,[np.nan]*100)['status']=='unknown'
    assert shape_features(np.arange(100)*.1,np.zeros(100))['status']=='unknown'


def test_control_coupling_and_separate_units():
    t=np.linspace(0,2*np.pi,500)
    correlated=control_coupling(np.sin(t),-np.sin(t))
    independent=control_coupling(np.sin(t),np.cos(t))
    assert correlated['coupling_risk'] and correlated['correlation']<-.99
    assert not independent['coupling_risk'] and not independent['causal']
    assert polyline_complexity([0,1,2],[0,1,2])['retained']==2
    assert polyline_complexity([0,0],[0,1])['status']=='unknown'


def test_determinism_and_ownership_unknown(tmp_path):
    project,pp,hp,bp,bind=fixture(tmp_path)
    h=json.loads(hp.read_text());h['parts'][0]['phrases'][0]['phones'][0]['ownership_status']='ambiguous_or_absent';dump(hp,h);bind['phonemes_sha256']=sha256(hp);dump(bp,bind)
    a=evaluate(project,tmp_path/'a',native_pitch=pp,phonemes=hp,provenance=bp)
    b=evaluate(project,tmp_path/'b',native_pitch=pp,phonemes=hp,provenance=bp)
    assert a==b and a['region_counts']['unknown']==1
    for name in ['summary.json','regions.jsonl','findings.jsonl','report.md']:
        assert (tmp_path/'a'/name).read_bytes()==(tmp_path/'b'/name).read_bytes()


def test_noise_short_support_and_frozen_negative_controls():
    rng=np.random.default_rng(142);t=np.arange(0,2,.005)
    noise=shape_features(t,rng.normal(0,.3,len(t)))
    assert noise['cycles']==[]
    assert shape_features(t[:10],25*np.sin(2*np.pi*5*t[:10]))['status']=='unknown'
    false_positives=0
    for y in [np.full(len(t),6000),6000+10*t,6000+rng.normal(0,.2,len(t))]:
        rs=[dict(start_s=0,end_s=2,region_type='vowel')]
        false_positives+=len(boundary_candidates(t,y,rs)['findings'])
    assert false_positives==0  # synthetic technical negatives, not unlabeled song regions


def test_missing_binding_and_invalid_threshold(tmp_path):
    project,pp,hp,_,_=fixture(tmp_path)
    assert evaluate(project,tmp_path/'out',native_pitch=pp,phonemes=hp)['stage']=='static_only'
    with pytest.raises(ValueError):Thresholds(jump_c=-1)
    with pytest.raises(ValueError):Thresholds(min_samples=3.5)


def test_voic_dyn_kept_separate_and_nonfinite_time(tmp_path):
    project,_,_,_,_=fixture(tmp_path);d=yaml.safe_load(project.read_text())
    d['expressions']=dict(voic=dict(default_value=100),dyn=dict(default_value=0))
    d['voice_parts'][0]['curves']=[dict(abbr='voic',xs=[0,100,200],ys=[100,112,100]),dict(abbr='dyn',xs=[0,100,200],ys=[0,30,0])]
    project.write_text(yaml.safe_dump(d))
    r=evaluate(project,tmp_path/'out')['parts'][0]['curve_counts']
    assert r['voic'][0]['default_value']==100 and r['dyn'][0]['default_value']==0
    assert r['voic'][0]['effective_points']==1 and r['dyn'][0]['effective_points']==1
    assert shape_features([0,float('nan')],[1,2])['duration_s']==0
