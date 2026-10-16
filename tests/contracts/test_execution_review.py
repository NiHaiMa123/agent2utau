"""Synthetic risk cases for production review, never naturalness scores."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from agent2utau.evaluation import execution_review as r
from agent2utau.evaluation.local_views import build_local_views
from agent2utau.openutau.ustx import save_ustx,sha256


def case(tmp_path, y=None, two=False, split=False, full_stage=False):
    """Real-shaped native packets, explicitly synthetic environment."""
    project=tmp_path/'score.ustx'
    notes=[dict(position=0,duration=960,tone=60,lyric='a',pitch={'data':[]},vibrato={'length':0})]
    if two:notes.append(dict(position=960,duration=960,tone=60,lyric='a',pitch={'data':[]},vibrato={'length':0}))
    if split:notes=[dict(position=0,duration=480,tone=60,lyric='a'),dict(position=480,duration=480,tone=62,lyric='+')]
    duration=2 if two else 1
    t=np.arange(0,duration+.0001,.005);yy=np.full(t.shape,6000.) if y is None else np.asarray(y(t))
    score=dict(resolution=480,tempos=[dict(position=0,bpm=120)],tracks=[dict(singer='synthetic')],expressions={},voice_parts=[dict(position=0,track_no=0,notes=notes,curves=[])])
    save_ustx(score,project)
    phones=[];nn=[]
    for i,n in enumerate(notes):
        primary=0 if split else i
        nn.append(dict(note_index=i,lyric=n['lyric'],tone=n['tone'],start_ms=n['position']/.96,end_ms=(n['position']+n['duration'])/.96,primary_index=primary))
        phones.append(dict(phone_index=i,phoneme='zh/a',start_ms=n['position']/.96,end_ms=(n['position']+n['duration'])/.96,owner_primary_indices=[primary],owner_note_indices=[i],ownership_status='matched',tone=n['tone']))
    p=dict(schema_version=1,units='absolute MIDI times 100 cents; absolute project milliseconds',phrases=[dict(part_position=0,track_no=0,position=0,times_ms=(t*1000).tolist(),final_cents=yy.tolist(),before_pitd_cents=[6000.]*len(t))])
    h=dict(schema_version=1,units='absolute project milliseconds; pitch absolute MIDI times 100 cents',parts=[dict(part_position=0,track_no=0,notes=nn,phrases=[dict(position=0,phones=phones,pitch_times_ms=(t*1000).tolist(),final_cents=yy.tolist())])])
    pp=tmp_path/'pitch.json';hp=tmp_path/'phones.json';bp=tmp_path/'provenance.json'
    r.write(pp,p);r.write(hp,h);r.write(bp,dict(schema_version=1,project_sha256=sha256(project),pitch_sha256=sha256(pp),phonemes_sha256=sha256(hp),environment=dict(core_sha256='1'*64,bridge_sha256='2'*64,singer_id='synthetic',singer_config_sha256='3'*64)))
    obs=tmp_path/'source-observation.json';r.write(obs,{'synthetic':True})
    sm=tmp_path/'sources.json';r.write(sm,dict(schema_version=1,sources=[dict(id='current-source',role='source_observation',file=r.ref(obs),description='Frozen synthetic current observation, no human audio truth')]))
    inv=tmp_path/'inventory.json';r.build_inventory(project,inv,pp,hp,bp,sources=sm)
    context=tmp_path/'context.json'
    rows=[]
    for u in r.read(inv)['units']:
        rows.append(dict(id=u['id'],condition=dict(status='observed',evidence_ids=['current-source'],observation='Synthetic sustained vowel with no change of pitch identity',interpretation='A steady nucleus is the explicit test condition',reliability='Synthetic construction, not listening'),stages=[dict(id=u['id']+':body',kind='body',support_s=[u['support_s'][0]+.25,u['support_s'][1]-.05],required=True)]))
    if full_stage:
        for row,unit in zip(rows,r.read(inv)['units']):row['stages'][0]['support_s']=unit['support_s']
    r.write(context,dict(schema_version=1,units=rows));annotated=tmp_path/'conditions.json';r.build_inventory(project,annotated,pp,hp,bp,context,sm)
    # Explicit synthetic target nodes; these are fixture truth, not inferred
    # decisions for an existing song. Native samples are independently checked.
    slopes=np.gradient(yy,t);ix=list(range(0,len(t),10))
    if ix[-1]!=len(t)-1:ix.append(len(t)-1)
    design=dict(schema=1,origin='agent_designed',support_s=[0.,float(duration)],
                center_nodes=[[float(t[i]),float(yy[i]),float(slopes[i])] for i in ix],components=[],
                decisions=[dict(support_s=[0.,float(duration)],condition='Synthetic fixture',choice='Explicit center',alternative='Hold',reason='Fixture target shape',uncertainty='No human singing',component_ids=[])],
                expectations=[dict(support_s=[0.,float(duration)],range_c=[0,1000],purpose='Synthetic helper coverage only; not review truth')])
    plan=tmp_path/'plan.json';r.write(plan,dict(phrases=[dict(part_index=0,position=0,design=design)]))
    return dict(project=project,pitch=pp,phones=hp,provenance=bp,inventory=annotated,plan=plan)


def ledger(c, choice='hold', checks=None):
    inv=r.read(c['inventory']);plan=r.read(c['plan']);nodes=plan['phrases'][0]['design']['center_nodes'];ds=[]
    for u in inv['units']:
        stage=u['stages'][0]
        ds.append(dict(id='dec-'+u['id'],unit_ids=[u['id']],stage_ids=[stage['id']],support_s=u['support_s'],evidence_ids=['current-source'],observation='Known constant source and stable musical target',interpretation='Current unit sustains while preserving neighboring note entry',reliability='Synthetic only',purpose='Verify that grounded hold is legal',choice=choice,alternative='Finite return',rejected_because='Synthetic condition requests no return at this unit',parameter_basis='Explicit current stable nucleus',execution=[dict(kind='center_nodes',part_index=0,position=0,id='center_nodes',support_s=u['support_s'],parameters_sha256=r.digest(nodes))],checks=checks(stage) if checks else [dict(stage_id=stage['id'],kind='hold',support_s=stage['support_s'],parameters=dict(min_c=0,max_c=.5))],uncertainty='No auditory quality assertion'))
    p=c['project'].parent/'ledger.json';r.write(p,dict(schema_version=1,inventory=r.ref(c['inventory']),plan=r.ref(c['plan']),timing='forward',decisions=ds,revisions=[]));return p


def execute(c,out,lp=None,reviews=None,atlas=False):
    return r.review_execution(c['project'],c['inventory'],out,c['pitch'],c['phones'],c['provenance'],lp,c['plan'],reviews,make_atlas=atlas)


def test_ledger_free_sentence_and_missing_required_stage(tmp_path):
    c=case(tmp_path,two=True);lp=ledger(c);obj=r.read(lp)
    obj['decisions']=[dict(obj['decisions'][0],unit_ids=[],stage_ids=[])];lp.write_text(json.dumps(obj))
    _,fails,_=r.ledger_check(lp,c['inventory'],c['plan'])
    assert any(x['code']=='missing_or_wrong_unit_mapping' for x in fails)
    assert sum(x['code']=='missing_stage' for x in fails)==2


def test_same_vowel_carry_and_same_tone_new_word_denominators(tmp_path):
    a=tmp_path/'carry';a.mkdir();c=case(a,split=True)
    inv=r.read(c['inventory']);assert inv['denominator']==1 and len(inv['units'][0]['note_ids'])==2
    b=tmp_path/'words';b.mkdir();c=case(b,two=True)
    assert r.read(c['inventory'])['denominator']==2


def test_just_arrival_cannot_satisfy_body_motion(tmp_path):
    c=case(tmp_path,lambda t:6000+500*np.clip(t/.15,0,1))
    lp=ledger(c,'center',lambda s:[dict(stage_id=s['id'],kind='range',support_s=s['support_s'],parameters=dict(min_c=30,max_c=70))])
    result=execute(c,tmp_path/'out',lp)
    assert result['action_execution']['status']=='fail' and not result['production_execution_complete']
    assert result['action_execution']['checks'][0]['raw_range_c']==0


@pytest.mark.parametrize('y,choice,check',[
    (lambda t:6000+35*t,'center',dict(kind='direction',parameters=dict(direction='up',min_delta_c=20,max_backtrack_c=1))),
    (lambda t:6000-40*np.sin(np.pi*t),'finite_return',dict(kind='landmarks',parameters=dict(points=[[.25,6000-40*np.sin(np.pi*.25)],[.5,5960],[.95,6000-40*np.sin(np.pi*.95)]],tolerance_c=.01,time_tolerance_s=.003)))])
def test_slow_center_and_finite_nonperiodic_are_not_forced_cycles(tmp_path,y,choice,check):
    c=case(tmp_path,y)
    lp=ledger(c,choice,lambda s:[dict(check,stage_id=s['id'],support_s=s['support_s'])])
    result=execute(c,tmp_path/'out',lp)
    assert result['action_execution']['status']=='pass'
    features=r.read(tmp_path/'out/independent-facts.json')['units'][0]['stages'][0]['features']
    assert features['cycles']==[]


@pytest.mark.parametrize('mode',['cancelled','wrong_phase','quantized_away'])
def test_declared_component_does_not_make_actual_flat_pass(tmp_path,mode):
    c=case(tmp_path);p=r.read(c['plan']);component=dict(id='active',family='finite_return',support_s=[.25,.95],peak_s=.5,peak_c=.2 if mode=='quantized_away' else 40);p['phrases'][0]['design']['components']=[component];c['plan'].write_text(json.dumps(p))
    lp=ledger(c,'finite_return',lambda s:[dict(stage_id=s['id'],kind='range',support_s=s['support_s'],parameters=dict(min_c=.1 if mode=='quantized_away' else 25,max_c=80))])
    d=r.read(lp);d['decisions'][0]['execution'].append(dict(kind='component',part_index=0,position=0,id='active',support_s=component['support_s'],parameters_sha256=r.digest(component)));lp.write_text(json.dumps(d))
    assert execute(c,tmp_path/'out',lp)['action_execution']['status']=='fail'


def test_unconsumed_mapping_and_generic_range_trigger_review(tmp_path):
    c=case(tmp_path);lp=ledger(c,'finite_return',lambda s:[dict(stage_id=s['id'],kind='range',support_s=s['support_s'],parameters=dict(min_c=0,max_c=1600))]);d=r.read(lp);d['decisions'][0]['execution'][0]['kind']='unknown_new_action';lp.write_text(json.dumps(d));result=execute(c,tmp_path/'out',lp)
    assert any(f['code']=='execution_mapping_failed' for f in result['inventory_coverage']['failures'])
    assert any(f['code']=='non_discriminating_movement_check' for f in result['choice_review']['findings'])


def test_independent_facts_does_not_read_plan_or_expectations(tmp_path):
    c=case(tmp_path);a=r.independent_facts(c['inventory'],c['project'],c['pitch'],c['phones'],c['provenance'])
    c['plan'].write_text('{"expectations":"unreadable musical truth"}')
    assert a==r.independent_facts(c['inventory'],c['project'],c['pitch'],c['phones'],c['provenance'])
    assert not a['expectations_read']


def test_inventory_tampering_and_unknown_native_ownership(tmp_path):
    c=case(tmp_path);obj=r.read(c['inventory']);obj['units'][0]['part_index']=7;obj['identity_sha256']=r.digest([r.identity(u) for u in obj['units']]);c['inventory'].write_text(json.dumps(obj))
    with pytest.raises(ValueError,match='clock/phones'):r.validate_inventory(c['inventory'])


def test_reference_numerics_even_with_renamed_path_are_not_originality_pass(tmp_path):
    c=case(tmp_path);inv=r.read(c['inventory']);inv['sources'][0]['role']='derived_author_parameters'
    assert r.audit_sources(inv)['status']=='fail'
    inv['sources'][0]['role']='unknown';assert r.audit_sources(inv)['status']=='review_required'
    assert not r.audit_sources(inv)['absolute_originality_certified']


def test_old_native_provenance_or_post_edit_rejects_review(tmp_path):
    c=case(tmp_path);lp=ledger(c);execute(c,tmp_path/'out',lp)
    c['project'].write_text(c['project'].read_text()+'\n# changed\n')
    with pytest.raises(ValueError,match='Stale'):r.validate_review(c['project'],tmp_path/'out/review.json')


def test_direct_script_missing_ledger_cannot_get_completed_report(tmp_path):
    c=case(tmp_path);result=execute(c,tmp_path/'out')
    assert not result['production_execution_complete']
    delivery=r.delivery_review(c['project'],tmp_path/'delivery.json',tmp_path/'out/review.json')
    assert delivery['execution_status']=='fail' and delivery['candidate_delivery_allowed']


def review_records(c,out,lp,method='image_and_numeric',count=None):
    facts=r.read(out/'independent-facts.json');atlas=r.read(out/'atlas/atlas.json')
    proof=c['project'].parent/'view-access.json';r.write(proof,dict(kind='synthetic tool-access test record; not actual Agent image viewing'))
    rows=[]
    for u in r.read(c['inventory'])['units'][:count]:
        rows.append(dict(unit_id=u['id'],view_ids=[v['id'] for v in atlas['views'] if v['unit_id']==u['id']],method=method,view_evidence=[r.ref(proof)],facts_sha256=r.digest(next(x for x in facts['units'] if x['id']==u['id'])),observation='Measured zero body range with maintained target and unchanged neighboring identity',result='keep',reason='Synthetic current condition explicitly holds this complete nucleus; finite motion would contradict the fixture',evidence_ids=['current-source'],resolved_findings=['repeated_choice_basis_requires_context_review']))
    p=c['project'].parent/'reviews.json';r.write(p,dict(schema_version=1,inventory=r.ref(c['inventory']),facts=r.ref(out/'independent-facts.json'),ledger=r.ref(lp),atlas=r.ref(out/'atlas/atlas.json'),records=rows));return p


def test_atlas_generation_does_not_count_as_review_and_numeric_only_not_visual(tmp_path):
    c=case(tmp_path,two=True);lp=ledger(c);result=execute(c,tmp_path/'first',lp,atlas=True)
    assert result['local_visual_review']['completed']==0 and result['local_visual_review']['pending']==2
    reviews=review_records(c,tmp_path/'first',lp,method='numeric_only',count=1)
    result=execute(c,tmp_path/'second',lp,reviews,atlas=True)
    assert result['local_visual_review']['completed']==0 and result['local_visual_review']['numeric_only']==1
    assert not result['production_execution_complete']


def test_grounded_all_hold_can_complete_execution_without_naturalness_or_transfer_claim(tmp_path):
    c=case(tmp_path,two=True,full_stage=True);lp=ledger(c);execute(c,tmp_path/'first',lp,atlas=True)
    reviews=review_records(c,tmp_path/'first',lp)
    result=execute(c,tmp_path/'second',lp,reviews,atlas=True)
    assert result['technical_execution_complete'] and result['local_visual_review']['completed']==2
    assert not result['production_execution_complete']  # Viewing is no longer musical-process completion.
    assert result['choice_review']['status']=='agent_attested'
    assert result['musical_review']['status']=='unverified'
    assert result['audio']['status']=='unknown' and result['transfer']['status']=='unknown'


def test_long_word_overlapping_pages_and_stale_view_rejected(tmp_path):
    c=case(tmp_path,split=True);lp=ledger(c)
    atlas=build_local_views(c['project'],c['inventory'],c['pitch'],c['phones'],c['provenance'],tmp_path/'small-pages',window_s=.5,overlap_s=.1)
    views=atlas['views'];assert len(views)>2
    assert all(b['view_s'][0]<a['view_s'][1] for a,b in zip(views,views[1:]))
    assert {v['px_per_s'] for v in views}=={600}
    result=execute(c,tmp_path/'first',lp,atlas=True);reviews=review_records(c,tmp_path/'first',lp)
    png=Path(r.read(tmp_path/'first/atlas/atlas.json')['views'][0]['files']['png']['path']);png.write_bytes(b'old version substituted')
    with pytest.raises(ValueError,match='Stale'):execute(c,tmp_path/'second',lp,reviews,atlas=True)


def test_static_inventory_never_fabricates_phone_clock(tmp_path):
    c=case(tmp_path);p=tmp_path/'static.json';obj=r.build_inventory(c['project'],p)
    assert obj['stage']=='static_only' and obj['units'][0]['phone_ids']==[]


def test_legacy_compile_calls_shared_review_and_does_not_claim_completion(tmp_path,monkeypatch):
    from test_workflow import setup_case
    from agent2utau.workflow import compile_functions
    plan,_,_=setup_case(tmp_path,monkeypatch);result=compile_functions(plan,tmp_path/'compiled',{})
    assert result['status']=='candidate_review_incomplete'
    assert r.read(Path(result['execution_review']))['inventory_coverage']['status']=='fail'
    assert 'source_or_author_curve_inherited' not in result


def test_ap_unknown_and_short_phones_keep_separate_denominators(tmp_path):
    c=case(tmp_path,two=True);h=r.read(c['phones']);h['parts'][0]['notes'][0]['lyric']='AP';score=__import__('yaml').safe_load(c['project'].read_text());score['voice_parts'][0]['notes'][0]['lyric']='AP';save_ustx(score,c['project'])
    h['parts'][0]['phrases'][0]['phones'][0]['phoneme']='AP'
    h['parts'][0]['phrases'][0]['phones'][1]['ownership_status']='ambiguous_or_absent'
    c['phones'].write_text(json.dumps(h));b=r.read(c['provenance']);b.update(project_sha256=sha256(c['project']),phonemes_sha256=sha256(c['phones']));c['provenance'].write_text(json.dumps(b))
    p=tmp_path/'new-inventory.json';inv=r.build_inventory(c['project'],p,c['pitch'],c['phones'],c['provenance'])
    assert inv['denominator']==0
    assert {x['region_type'] for x in inv['regions']}=={'non_singing','unknown'}
    stage=dict(support_s=[0,.01],times_s=[0,.005],raw_cents=[6000,6000])
    check=dict(stage_id='short',kind='cycles',support_s=[0,.01],parameters=dict(min_cycles=1,prominence_c=5))
    assert r.check_action(check,stage)['status']=='unknown'


def test_condition_change_with_identical_parameters_requires_explanation(tmp_path):
    c=case(tmp_path);lp=ledger(c);prior=tmp_path/'forward-v1.json';prior.write_bytes(lp.read_bytes());obj=r.read(lp)
    obj['decisions'][0]['observation']='Landing is now required on the clear beat'
    obj['revisions']=[dict(previous=r.ref(prior),reason='Explicit current condition changed',evidence_ids=['current-source'],unit_ids=[r.read(c['inventory'])['units'][0]['id']])];lp.write_text(json.dumps(obj))
    _,fails,flags=r.ledger_check(lp,c['inventory'],c['plan'])
    assert not fails and any(f['code']=='changed_conditions_require_reassessment' and f['execution_parameters_unchanged'] for f in flags)


def test_unregistered_literal_old_target_is_visible_source_finding(tmp_path):
    c=case(tmp_path);script=tmp_path/'generator.py';script.write_text('import numpy as np\nx=np.load("old-target.npy")\n',encoding='utf8');inv=r.read(c['inventory']);inv['sources'].append(dict(id='code',role='implementation',file=r.ref(script),description='Current generation script'))
    result=r.audit_sources(inv)
    assert result['status']=='review_required' and any(x['code']=='unregistered_literal_read' for x in result['findings'])


def test_wrong_parameter_binding_and_omitted_stage_cannot_be_closed_by_time_coverage(tmp_path):
    c=case(tmp_path);obj=r.read(c['inventory']);u=obj['units'][0];u['stages'].append(dict(id=u['id']+':arrival',kind='arrival',support_s=[0,.2],required=True));c['inventory'].write_text(json.dumps(obj));lp=ledger(c)
    _,fails,_=r.ledger_check(lp,c['inventory'],c['plan']);assert any(f['code']=='missing_stage' for f in fails)
    obj=r.read(lp);obj['decisions'][0]['execution'][0]['parameters_sha256']='0'*64;lp.write_text(json.dumps(obj))
    assert any(f['code']=='execution_mapping_failed' for f in execute(c,tmp_path/'out',lp)['inventory_coverage']['failures'])


def test_native_multilingual_vowel_roles_do_not_mix_english_v_with_chinese_v():
    from agent2utau.evaluation.features import phone_kind
    assert phone_kind('en/ey')==phone_kind('en/iy')==phone_kind('en/ah')=='vowel'
    assert phone_kind('en/v')==phone_kind('zh/y0')=='consonant'
    assert phone_kind('zh/v')==phone_kind('zh/En')=='vowel'
    assert phone_kind('zh/iu')==phone_kind('zh/ui')=='vowel'
    assert phone_kind('other/opaque')=='unknown'


def test_narrow_stage_does_not_certify_unassigned_native_entry_and_exit(tmp_path):
    c=case(tmp_path);lp=ledger(c);result=execute(c,tmp_path/'out',lp)
    assert any(f['code']=='native_support_without_stage' for f in result['choice_review']['unresolved'])
    assert not result['production_execution_complete']


def test_direction_checks_cumulative_reversal_and_landmarks_require_distinct_ordered_samples():
    t=np.arange(0,1.001,.005);y=np.interp(t,[0,.3,.6,1],[6000,6040,6010,6060])
    stage=dict(support_s=[0,1],times_s=t.tolist(),raw_cents=y.tolist())
    result=r.check_action(dict(stage_id='x',kind='direction',support_s=[0,1],parameters=dict(direction='up',min_delta_c=20,max_backtrack_c=3)),stage)
    assert result['status']=='fail' and result['max_cumulative_backtrack_c']==30
    y=np.zeros(len(t));y[100]=50;stage['raw_cents']=y.tolist()
    result=r.check_action(dict(stage_id='x',kind='landmarks',support_s=[0,1],parameters=dict(points=[[.4,50],[.6,50]],tolerance_c=0,time_tolerance_s=.2)),stage)
    assert result['status']=='fail' and not result['order_preserved']


def test_compile_contract_missing_stage_blocks_before_native(tmp_path,monkeypatch):
    from test_workflow import setup_case
    from agent2utau import workflow as w
    base=tmp_path/'knowledge';base.mkdir();planfile,_,plan=setup_case(base,monkeypatch)
    target=tmp_path/'native';target.mkdir();c=case(target)
    plan.update(project=str(c['project']),source_audio=str(base/'source.wav'),input_hashes={str(c['project']):sha256(c['project']),str(base/'source.wav'):sha256(base/'source.wav')},phrases=r.read(c['plan'])['phrases'])
    plan['knowledge_context']['path']=str(base/'knowledge.json');c['plan'].write_text(json.dumps(plan))
    lp=ledger(c);obj=r.read(lp);obj['decisions']=[];lp.write_text(json.dumps(obj))
    contract=target/'contract.json';r.write(contract,dict(schema_version=1,inventory=r.ref(c['inventory']),ledger=r.ref(lp),reviews=None))
    monkeypatch.setattr(w,'run_bridge',lambda *a,**k:pytest.fail('Coverage must block before native'))
    with pytest.raises(ValueError,match='contract coverage failed'):w.compile_functions(c['plan'],tmp_path/'blocked',{},contract)
    assert not (tmp_path/'blocked').exists()


def test_render_cli_stale_review_blocks_before_native(tmp_path,monkeypatch,capsys):
    from agent2utau import cli
    import agent2utau.openutau.bridge as bridge
    c=case(tmp_path);lp=ledger(c);execute(c,tmp_path/'out',lp)
    c['project'].write_text(c['project'].read_text()+'\n# post edit\n')
    monkeypatch.setattr(cli,'load_config',lambda:{})
    monkeypatch.setattr(bridge,'run_bridge',lambda *a,**k:pytest.fail('Stale review must block rendering'))
    result=cli.main(['render-project','--project',str(c['project']),'--out',str(tmp_path/'render'),'--execution-review',str(tmp_path/'out/review.json')])
    assert result==1 and 'Stale' in capsys.readouterr().out


def test_render_environment_change_is_not_hidden_by_old_provenance(tmp_path):
    c=case(tmp_path);lp=ledger(c);execute(c,tmp_path/'out',lp)
    with pytest.raises(ValueError,match='native environment differs'):
        r.validate_review(c['project'],tmp_path/'out/review.json',dict(openutau_dir=str(tmp_path/'changed-install')))


def test_wrong_singer_environment_cannot_claim_native_identity(tmp_path):
    c=case(tmp_path);provenance=r.read(c['provenance']);provenance['environment']['singer_id']='different-singer';c['provenance'].write_text(json.dumps(provenance))
    with pytest.raises(ValueError,match='singer/environment identity mismatch'):
        r.build_inventory(c['project'],tmp_path/'wrong-singer.json',c['pitch'],c['phones'],c['provenance'])


def test_single_parent_phone_retains_real_extender_music_stages(tmp_path):
    c=case(tmp_path,split=True);h=r.read(c['phones']);ph=h['parts'][0]['phrases'][0]['phones'][0]
    ph['end_ms']=1000;h['parts'][0]['phrases'][0]['phones']=[ph]
    c['phones'].write_text(json.dumps(h));b=r.read(c['provenance']);b['phonemes_sha256']=sha256(c['phones']);c['provenance'].write_text(json.dumps(b))
    result=r.build_inventory(c['project'],tmp_path/'real-parent-style.json',c['pitch'],c['phones'],c['provenance'])
    assert result['units'][0]['note_ids']==['p0:n0','p0:n1']
    assert len(result['units'][0]['musical_stages'])==2
    r.validate_inventory(tmp_path/'real-parent-style.json')


def test_exact_input_atlas_reuse_and_float_boundary_are_not_window_relaxation(tmp_path):
    c=case(tmp_path,full_stage=True);lp=ledger(c);execute(c,tmp_path/'first',lp,atlas=True)
    result=r.review_execution(c['project'],c['inventory'],tmp_path/'reuse',c['pitch'],c['phones'],c['provenance'],lp,c['plan'],atlas_path=tmp_path/'first/atlas/atlas.json')
    assert result['local_visual_review']['completed']==0
    samples=np.linspace(0,1,51)
    stage=dict(support_s=[0,1],times_s=samples.tolist(),raw_cents=np.interp(samples,[0,.5,1],[0,20,0]).tolist())
    check=dict(stage_id='x',kind='landmarks',support_s=[0,1],parameters=dict(points=[[0,0],[1.0000000000000002,0]],tolerance_c=0,time_tolerance_s=0))
    assert r.check_action(check,stage)['status']=='pass'
    atlas=r.read(tmp_path/'first/atlas/atlas.json');Path(atlas['views'][0]['files']['png']['path']).write_bytes(b'swapped')
    with pytest.raises(ValueError,match='Stale'):
        r.review_execution(c['project'],c['inventory'],tmp_path/'stale',c['pitch'],c['phones'],c['provenance'],lp,c['plan'],atlas_path=tmp_path/'first/atlas/atlas.json')
