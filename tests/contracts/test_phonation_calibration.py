import json
import pytest
from agent2utau.evaluation.execution_review import ref
from agent2utau.evaluation.phonation_calibration import AXES,validate_partition,validate_ratings


def fixture(tmp_path):
    def save(p,d):p.write_text(json.dumps(d),encoding='utf-8')
    samples=[]
    for name in ['a','b']:
        wav=tmp_path/(name+'.wav');wav.write_bytes(name.encode())
        samples.append(dict(id=name,context_id='same-vowel-register',split='development',audio=ref(wav)))
    c=tmp_path/'catalog.json';save(c,dict(samples=samples))
    p=tmp_path/'packet.json';packet=dict(schema_version=1,catalog=ref(c),pairs=[dict(id='p1',A='a',B='b',context_id='same-vowel-register',split='development')],instructions='No automatic score');save(p,packet)
    r=tmp_path/'ratings.json';rating=dict(schema_version=1,packet_sha256=ref(p)['sha256'],rater_id='',ratings=[dict(pair_id='p1',answers={a:None for a in AXES},comment='')]);save(r,rating)
    return c,p,r,packet,rating


def test_pending_is_not_a_perceptual_pass_and_complete_labels_still_do_not_fit(tmp_path):
    c,p,r,packet,rating=fixture(tmp_path)
    out=validate_ratings(c,p,r)
    assert out['pending_pairs']==1 and not out['perceptual_scale_validated']
    with pytest.raises(ValueError,match='pending'):validate_ratings(c,p,r,True)
    rating['rater_id']='listener-1';rating['ratings'][0]['answers']={k:'same' for k in AXES};r.write_text(json.dumps(rating))
    out=validate_ratings(c,p,r,True)
    assert out['completed_pairs']==1 and not out['automatic_song_pass']
    assert out['rater_id']=='listener-1' and out['rater_status']=='provided'


@pytest.mark.parametrize('bad',['audio','order','missing','duplicate','bad_axis','knob_as_answer'])
def test_rating_provenance_and_separate_axes_refusals(tmp_path,bad):
    c,p,r,packet,rating=fixture(tmp_path)
    if bad=='audio':(tmp_path/'a.wav').write_bytes(b'changed')
    if bad=='order':
        packet['pairs'][0]['A'],packet['pairs'][0]['B']='b','a';p.write_text(json.dumps(packet))
    if bad=='missing':rating['ratings']=[]
    if bad=='duplicate':rating['ratings']*=2
    if bad=='bad_axis':rating['ratings'][0]['answers'].pop('airiness')
    if bad=='knob_as_answer':rating['ratings'][0]['answers']['firmness']='VOIC190'
    r.write_text(json.dumps(rating))
    with pytest.raises(ValueError):validate_ratings(c,p,r)


def test_duplicated_waveform_descendants_cannot_split_the_same_context():
    with pytest.raises(ValueError,match='leak'):
        validate_partition([dict(id='a',context_id='x',split='development'),dict(id='b',context_id='x',split='holdout')])


def test_identical_audio_cannot_hide_partition_leak_by_renaming_context():
    with pytest.raises(ValueError,match='audio leaks'):
        validate_partition([dict(id='a',context_id='x',split='development',audio={'sha256':'same'}),dict(id='b',context_id='y',split='holdout',audio={'sha256':'same'})])
