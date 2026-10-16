import copy
import json
import pytest
from agent2utau import knowledge as k

@pytest.fixture
def catalogue(tmp_path,monkeypatch):
    monkeypatch.setattr(k,'REPO_ROOT',tmp_path)
    d=tmp_path/'docs/knowledge/test';d.mkdir(parents=True)
    (d/'table.json').write_text(json.dumps({'entities':[{'id':'PER:S1','measurement_validated':False,'unknown':'retained'}]}))
    (d/'parameters.csv').write_text('id,abbreviation\nPARAM:C11.01,voic\n')
    (d/'response.json').write_text(json.dumps({'record_id':'RESP:TEST','feedback':'no difference','general_rule_validated':False}))
    ref=k._ref(d/'response.json')
    (d/'index.json').write_text(json.dumps({'rows':[{'id':'RESP:TEST','source':ref,'feedback_sources':[],'source_record':{'unknown':True}}]}))
    p=d/'catalogue.json';p.write_text(json.dumps({'table1':'docs/knowledge/test/table.json','parameters':'docs/knowledge/test/parameters.csv','response_indices':['docs/knowledge/test/index.json'],'response_packets':[]}))
    return p

def packet(p):return k.collect_context(['PER:S1'],['PARAM:C11.01'],['RESP:TEST'],catalogue_path=p)
def decisions(p):return [dict(id=r['id'],decision='keep_unknown',reason='Retain evidence',condition_match='Only test condition',limitations='No generalization') for r in p['records']]

def test_conditional_and_unknown_fields_retained(catalogue):
    p=packet(catalogue);assert p['records'][0]['record']['measurement_validated'] is False
    assert p['records'][0]['record']['unknown']=='retained'
    assert k.validate_context(p,decisions(p))['status']=='passed'

def test_stale_source_rejected(catalogue):
    p=packet(catalogue);(catalogue.parent/'response.json').write_text('{}')
    with pytest.raises(ValueError,match='Changed knowledge'):k.validate_context(p,decisions(p))

def test_forged_context_not_a_source_record(catalogue):
    p=packet(catalogue);p['records'][0]['record']['measurement_validated']=True
    with pytest.raises(ValueError,match='do not match'):k.validate_context(p,decisions(p))

@pytest.mark.parametrize('field',['reason','condition_match','limitations'])
def test_empty_decision_fields_rejected(catalogue,field):
    p=packet(catalogue);d=decisions(p);d[0][field]=' '
    with pytest.raises(ValueError,match='Missing decision'):k.validate_context(p,d)

def test_unknown_ids_and_duplicate_decisions_rejected(catalogue):
    with pytest.raises(ValueError,match='Unknown parameter'):k.collect_context(['PER:S1'],['PARAM:NONE'],[],catalogue_path=catalogue)
    p=packet(catalogue);d=decisions(p);d[1]=copy.deepcopy(d[0])
    with pytest.raises(ValueError,match='every retrieved'):k.validate_context(p,d)

def test_absence_is_explicit(catalogue):
    with pytest.raises(ValueError,match='evidence absence'):k.collect_context(['PER:S1'],['PARAM:C11.01'],[],catalogue_path=catalogue)
    p=k.collect_context(['PER:S1'],['PARAM:C11.01'],[],absence_reason='No matching voice/phoneme trial',catalogue_path=catalogue)
    assert k.validate_context(p,decisions(p))['status']=='passed'

def test_general_rule_upgrade_rejected(catalogue):
    p=packet(catalogue);d=decisions(p);d[0]['general_rule_claim']=True
    with pytest.raises(ValueError,match='general rule'):k.validate_context(p,d)
