import copy,json
from dataclasses import asdict
from pathlib import Path
import numpy as np
import soundfile as sf
import pytest
from agent2utau.evaluation.phonation import evaluate_phonation,PhonationConfig
from agent2utau.knowledge import collect_context
from agent2utau.evaluation.execution_review import ref


def fixture(tmp_path):
    def save(p,d):p.write_text(json.dumps(d),encoding='utf-8')
    project=tmp_path/'score.ustx';project.write_text('Synthetic identity only; no production expectations read')
    regions=tmp_path/'regions.json';save(regions,[dict(id='a',phrase_id='s1',phone='zh/a',support_s=[.05,.25]),dict(id='b',phrase_id='s2',phone='zh/a',support_s=[.3,.55])])
    ctx=collect_context(['ACO:S1'],['PARAM:C11.01'],[],absence_reason='Synthetic contract validation only');kp=tmp_path/'knowledge.json';save(kp,ctx);dec=[dict(id=r['id'],decision='keep_unknown',reason='Synthetic',condition_match='Synthetic',limitations='No perception') for r in ctx['records']]
    versions=[];sr=16000;t=np.arange(int(sr*.6))/sr
    for label,noise in [('clean',.02),('noisy',.4)]:
        audio=tmp_path/f'{label}.wav';y=.1*(np.sin(2*np.pi*250*t)+.3*np.sin(2*np.pi*500*t)+noise*np.random.default_rng(1).normal(size=len(t)));sf.write(audio,y,sr,subtype='FLOAT');tracks=[]
        for detector in ['one','two']:
            fp=tmp_path/f'{label}-{detector}.npz';ft=np.arange(0,.6,.01);np.savez(fp,times=ft,f0_hz=np.full(len(ft),250),voiced=np.ones(len(ft),bool));tracks.append(dict(file=ref(fp),audio_sha256=ref(audio)['sha256'],absolute_offset_s=0,detector=detector))
        versions.append(dict(id=label,audio=ref(audio),absolute_offset_s=0,f0=tracks))
    manifest=dict(schema_version=1,signal_role='pure_solo_vocal',project=ref(project),regions=ref(regions),versions=versions,reference_version='clean',reference_phrases=['s1'],phrase_order=['s1','s2'],config=asdict(PhonationConfig()),knowledge_context=dict(path=str(kp),sha256=ref(kp)['sha256'],decisions=dec));mp=tmp_path/'manifest.json';save(mp,manifest);return mp,manifest


def test_readonly_bound_end_to_end_no_perceptual_pass(tmp_path):
    mp,m=fixture(tmp_path);files={p:p.read_bytes() for p in tmp_path.iterdir() if p.is_file()};r=evaluate_phonation(mp,tmp_path/'out')
    assert all(p.read_bytes()==data for p,data in files.items())
    assert r['hearing_pass'] is None and not r['perceptual_scale_validated']
    assert (tmp_path/'out/words.csv').exists()
    clean=r['versions']['clean']['scores'][1];noisy=r['versions']['noisy']['scores'][1]
    assert clean['consistency_distance_proxy']<noisy['consistency_distance_proxy']
    assert r['versions']['clean']['scores'][0]['status']=='unknown'  # no self-anchoring
    again=evaluate_phonation(mp,tmp_path/'repeat')
    assert again==r  # no random score fitting or cached target search


@pytest.mark.parametrize('kind',['audio_hash','f0_audio_hash','clock','same_detector','mixture','unknown_expectation_field','missing_phrase','f0_clock_coverage'])
def test_refuses_wrong_bindings_clocks_and_scope(tmp_path,kind):
    mp,m=fixture(tmp_path)
    if kind=='audio_hash':Path(m['versions'][0]['audio']['path']).write_bytes(b'changed')
    if kind=='f0_audio_hash':m['versions'][0]['f0'][0]['audio_sha256']='0'*64
    if kind=='clock':m['versions'][0]['f0'][0]['absolute_offset_s']=.1
    if kind=='same_detector':m['versions'][0]['f0'][1]['detector']='one'
    if kind=='mixture':m['signal_role']='mixed_song'
    if kind=='unknown_expectation_field':m['expected_firmness']='perfect'
    if kind=='missing_phrase':m['phrase_order']=['s1']
    if kind=='f0_clock_coverage':
        p=Path(m['versions'][0]['f0'][0]['file']['path']);np.savez(p,times=np.arange(.2,.6,.01),f0_hz=np.full(40,250),voiced=np.ones(40,bool));m['versions'][0]['f0'][0]['file']=ref(p)
    mp.write_text(json.dumps(m),encoding='utf-8')
    with pytest.raises(ValueError):evaluate_phonation(mp,tmp_path/'out')
    assert not (tmp_path/'out').exists()
