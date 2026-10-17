"""Counterexamples to self-certified musical success; no auditory claims."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from agent2utau.evaluation import execution_review as r
from agent2utau.evaluation import musical_review as m
from test_execution_review import case,ledger,execute,review_records


def intent(c, checks, role='arrival', mode='must_differ', calibrated=False):
    units=r.read(c['inventory'])['units'];ids=[u['id'] for u in units]
    brief=dict(schema_version=1,inventory=r.ref(c['inventory']),phrases=[dict(id='sentence',unit_ids=ids,support_s=[0,units[-1]['support_s'][1]],
        observations=[dict(id='current-motion',source_id='current-source',source_window_s=[0,1],description='Synthetic known low approach to a stable destination; uncertain source audio is not filled',reliability='observed')],
        intention='Arrival develops through a low preparation, then the stable center stands',gestures=[dict(id='approach',unit_ids=ids,role=role,support_s=[0,units[-1]['support_s'][1]],observation_ids=['current-motion'],interpretation='The preparation must remain distinct from a fast direct arrival',alternative='Fast arrival followed by a micro return',rejected_because='That alternative loses the explicitly required low preparation',contrast=dict(mode=mode,shallow_limit_c=25,connection_s=.08,reason='Diagnostic micro-motion alternative for this synthetic intent, not a quality minimum'),checks=checks)])],
        phonation=dict(baseline='Synthetic speaker held, no voice inference',target='No perceptual judgment in this fixture',status='unvalidated',contexts=[]))
    if calibrated:
        evidence=c['project'].parent/'calibration.txt';evidence.write_text('Synthetic bound evidence fixture; NOT a performed listening test',encoding='utf8')
        brief['phonation'].update(status='listening_evidence',contexts=[dict(unit_ids=ids,role='Synthetic complete-context evidence',audio=r.ref(evidence),feedback=r.ref(evidence))])
    path=c['project'].parent/'intent.json';r.write(path,brief)
    # Fixture plan values are retained for technical simulation. The lock tool
    # must see an absent path; its declared scope never proves hidden reasoning.
    data=c['plan'].read_bytes();c['plan'].unlink();lock=c['project'].parent/'intent-lock.json';m.freeze_intent(path,c['inventory'],c['plan'],lock);c['plan'].write_bytes(data)
    return path,lock


def criteria(points):
    return [dict(kind='landmarks',support_s=[0,1],parameters=dict(points=points,tolerance_c=1,time_tolerance_s=.004))]


def critique(c,lock,facts,out):
    proof=c['project'].parent/'critical-observation.txt';proof.write_text('Synthetic actual geometry evidence; not human hearing',encoding='utf8')
    structural=m.structural_audit(c['plan'])
    path=c['project'].parent/'critique.json';r.write(path,dict(schema_version=1,lock=r.ref(lock),project=r.ref(c['project']),pitch=r.ref(c['pitch']),facts=r.ref(facts),records=[dict(phrase_id='sentence',judgment='retain',observed_consequences='The actual low preparation survives; the shallow ablation loses that preparation',evidence=[r.ref(proof)])],structural_responses=[dict(code=code,context='Known synthetic extrema/stable holds; no aesthetic inference',evidence=[r.ref(proof)]) for code in structural.get('findings',[])]));return path


def test_frozen_intent_rejects_existing_plan_before_writing(tmp_path):
    c=case(tmp_path,full_stage=True);path,lock=intent(c,criteria([[0,6000],[1,6000]]),role='hold',mode='may_match')
    with pytest.raises(ValueError,match='before creating'):m.freeze_intent(path,c['inventory'],c['plan'],tmp_path/'late.json')
    assert not (tmp_path/'late.json').exists()


def test_large_preparation_realized_and_micro_ablation_distinguished(tmp_path):
    c=case(tmp_path,lambda t:5850+150*t,full_stage=True);path,lock=intent(c,criteria([[0,5850],[1,6000]]));lp=ledger(c,'center',lambda s:[dict(stage_id=s['id'],kind='direction',support_s=[0,1],parameters=dict(direction='up',min_delta_c=140,max_backtrack_c=1))])
    result=r.review_execution(c['project'],c['inventory'],tmp_path/'review',c['pitch'],c['phones'],c['provenance'],lp,c['plan'],make_atlas=False,intent_lock=lock)
    music=result['musical_review'];assert music['intent_execution']=='pass' and music['discrimination']=='pass'
    assert music['gestures'][0]['distinguishes_shallow']
    assert music['musical_quality']=='unverified' and music['phonation']=='unvalidated'
    assert not result['workflow_review_complete']


def test_new_prose_and_exact_target_cannot_make_shallow_motion_discriminating(tmp_path):
    c=case(tmp_path,lambda t:6000+20*np.sin(np.pi*t)**2,full_stage=True)
    checks=[dict(kind='range',support_s=[0,1],parameters=dict(min_c=10,max_c=30))]
    path,lock=intent(c,checks,role='body');facts=tmp_path/'facts.json';r.write(facts,r.independent_facts(c['inventory'],c['project'],c['pitch'],c['phones'],c['provenance']))
    cr=critique(c,lock,facts,tmp_path)
    result=m.evaluate_intent(c['project'],c['inventory'],c['pitch'],facts,c['plan'],lock,cr)
    assert result['intent_execution']=='pass' and result['discrimination']=='fail'
    assert result['agent_judgment']=='agent_attested' and result['status']=='rejected'
    assert result['nondiscriminating_gestures']==['approach']


def test_fast_arrival_with_small_body_fails_predeclared_delayed_arrival(tmp_path):
    c=case(tmp_path,lambda t:6000+20*np.sin(np.pi*t)**2,full_stage=True)
    _,lock=intent(c,criteria([[.1,5850],[.3,5900],[.7,6000]]));facts=tmp_path/'facts.json';r.write(facts,{})
    result=m.evaluate_intent(c['project'],c['inventory'],c['pitch'],facts,c['plan'],lock)
    assert result['intent_execution']=='fail' and result['status']=='rejected'


def test_grounded_hold_is_legal_but_still_no_automatic_quality_pass(tmp_path):
    c=case(tmp_path,full_stage=True);_,lock=intent(c,[dict(kind='hold',support_s=[0,1],parameters=dict(min_c=0,max_c=.5))],role='hold',mode='may_match',calibrated=True);lp=ledger(c)
    r.review_execution(c['project'],c['inventory'],tmp_path/'first',c['pitch'],c['phones'],c['provenance'],lp,c['plan'],make_atlas=True,intent_lock=lock)
    views=review_records(c,tmp_path/'first',lp);cr=critique(c,lock,tmp_path/'first/independent-facts.json',tmp_path)
    result=r.review_execution(c['project'],c['inventory'],tmp_path/'final',c['pitch'],c['phones'],c['provenance'],lp,c['plan'],views,atlas_path=tmp_path/'first/atlas/atlas.json',intent_lock=lock,musical_critique=cr)
    assert result['technical_execution_complete'] and result['workflow_review_complete']
    assert result['musical_review']['agent_judgment']=='agent_attested'
    assert result['musical_review']['musical_quality']=='unverified' and result['listening']=='unknown'


def test_tampered_brief_critique_and_calibration_evidence_are_stale(tmp_path):
    c=case(tmp_path,full_stage=True);path,lock=intent(c,criteria([[0,6000],[1,6000]]),role='hold',mode='may_match',calibrated=True)
    (tmp_path/'calibration.txt').write_text('Changed calibration input')
    with pytest.raises(ValueError,match='Stale'):m.validate_lock(lock,c['inventory'],c['plan'])


def test_critique_evidence_swap_invalidates_completed_receipt(tmp_path):
    c=case(tmp_path,full_stage=True);_,lock=intent(c,[dict(kind='hold',support_s=[0,1],parameters=dict(min_c=0,max_c=.5))],role='hold',mode='may_match',calibrated=True);lp=ledger(c)
    r.review_execution(c['project'],c['inventory'],tmp_path/'first',c['pitch'],c['phones'],c['provenance'],lp,c['plan'],intent_lock=lock)
    views=review_records(c,tmp_path/'first',lp);cr=critique(c,lock,tmp_path/'first/independent-facts.json',tmp_path)
    r.review_execution(c['project'],c['inventory'],tmp_path/'final',c['pitch'],c['phones'],c['provenance'],lp,c['plan'],views,atlas_path=tmp_path/'first/atlas/atlas.json',intent_lock=lock,musical_critique=cr)
    r.validate_review(c['project'],tmp_path/'final/review.json')
    (tmp_path/'critical-observation.txt').write_text('Replaced evidence')
    with pytest.raises(ValueError,match='Stale'):r.validate_review(c['project'],tmp_path/'final/review.json')


def test_repeated_structure_does_not_use_ids_doses_or_reasons(tmp_path):
    plan=dict(phrases=[dict(part_index=0,position=0,design=dict(center_nodes=[[0,6000,0],[1,6000,0]],components=[dict(id='first',family='finite_return',support_s=[0,.4],peak_s=.2,peak_c=18),dict(id='different-words-and-ID',family='finite_return',support_s=[.5,1],peak_s=.75,peak_c=37)]))])
    path=tmp_path/'plan.json';r.write(path,plan);result=m.structural_audit(path)
    assert result['groups'][0]['signature']==['finite_return',5,1]
    assert len(result['groups'][0]['occurrences'])==2
    assert 'all_center_node_slopes_zero' in result['findings']


def test_old_receipt_cannot_be_silently_upgraded_at_delivery(tmp_path):
    c=case(tmp_path,full_stage=True);lp=ledger(c);execute(c,tmp_path/'first',lp,atlas=True);views=review_records(c,tmp_path/'first',lp);execute(c,tmp_path/'new',lp,views,atlas=True)
    old=r.read(tmp_path/'new/review.json');old.pop('review_contract_version');old.pop('workflow_review_complete');old.pop('technical_execution_complete');old['production_execution_complete']=True
    receipt=tmp_path/'old.json';r.write(receipt,old)
    result=r.delivery_review(c['project'],tmp_path/'delivery.json',receipt)
    assert result['technical_execution_complete'] and not result['workflow_review_complete']
    assert not result['production_execution_complete'] and result['musical_quality']=='unverified'


def test_missing_full_unit_and_source_observation_cannot_freeze(tmp_path):
    c=case(tmp_path,full_stage=True);path,lock=intent(c,criteria([[0,6000],[1,6000]]),role='hold',mode='may_match');brief=r.read(path)
    brief['phrases'][0]['gestures'][0]['support_s']=[.4,.6];brief['phrases'][0]['gestures'][0]['checks']=[dict(kind='hold',support_s=[.4,.6],parameters=dict(min_c=0,max_c=1))];path.write_text(json.dumps(brief))
    with pytest.raises(ValueError,match='full units'):m.validate_brief(path,c['inventory'])


def test_mutated_lock_is_rejected_before_native_compile(tmp_path,monkeypatch):
    from test_workflow import setup_case
    from agent2utau import workflow as w
    base=tmp_path/'knowledge';base.mkdir();_,_,plan=setup_case(base,monkeypatch)
    target=tmp_path/'native';target.mkdir();c=case(target,full_stage=True);_,lock=intent(c,criteria([[0,6000],[1,6000]]),role='hold',mode='may_match')
    plan.update(project=str(c['project']),source_audio=str(base/'source.wav'),input_hashes={str(c['project']):r.ref(c['project'])['sha256'],str(base/'source.wav'):r.ref(base/'source.wav')['sha256']},phrases=r.read(c['plan'])['phrases']);plan['knowledge_context']['path']=str(base/'knowledge.json');c['plan'].write_text(json.dumps(plan));lp=ledger(c)
    contract=target/'contract.json';r.write(contract,dict(schema_version=2,inventory=r.ref(c['inventory']),ledger=r.ref(lp),reviews=None,intent_lock=r.ref(lock),musical_critique=None));obj=r.read(lock);obj['plan_path']=str(target/'other.json');lock.write_text(json.dumps(obj))
    monkeypatch.setattr(w,'run_bridge',lambda *a,**k:pytest.fail('Intent must block before native'))
    with pytest.raises(ValueError,match='Stale'):w.compile_functions(c['plan'],tmp_path/'blocked',{},contract)
    assert not (tmp_path/'blocked').exists()
