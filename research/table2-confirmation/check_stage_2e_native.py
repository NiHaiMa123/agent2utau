"""Audit explicitly bound historical native inputs and current static backend.

Reads only selected JSON/USTX, four embeddings, three ONNX declarations and 47
registered runtime files. Never opens caches/prediction NPZ/PCM or starts ONNX.
Historical prediction fields in native JSON are not fed to the new runner.
"""
import copy
import json
from pathlib import Path
import numpy as np
import yaml
from freeze_stage_2d import ROOT, HERE, OUT, load, sha
from check_stage_2e_runtime import resolve_registry
from shfc_path_runner import load_sealed_protocol
from shfc_native_preflight import (check_identity, planned_curve, sample_curve,
    check_sample_support, normalize_model_inputs)
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.resources.config import load_config


def main():
    binding = load(HERE/'stage_2e_native_baseline_binding.json')
    run = ROOT/binding['run']; target = run/'native-static-check.json'
    assert not target.exists(), 'Preserve previous native-static check'
    protocol = load_sealed_protocol()
    comparisons = load(OUT/'comparison-bindings.json')
    reads = {}
    def read_bound(path, expected):
        p = ROOT/path
        assert sha(p)==expected, path
        reads[path]=expected
        return p
    def native(record_id, slot, index):
        row = next(r for r in comparisons['rows'] if r['record_id']==record_id)
        result=[]
        for name in [f'phrase_{index:03}.json',f'variance_{index:03}.json']:
            ref=next(r for r in row['native_and_fresh_artifact_bindings'] if f'/native_{slot}/{name}' in r['path'])
            result.append(load(read_bound(ref['path'],ref['expected_sha256'])))
        return result
    all_refs = [('RESP-002','A',22),('RESP-007','A',21)]
    records = [native(*r) for r in all_refs]
    c,vc = native('RESP-003','C',22)
    project_ref=protocol['cases'][0]['baseline_project']
    project=yaml.safe_load(read_bound(project_ref['path'],project_ref['sha256']).read_text(encoding='utf-8'))
    second_ref=protocol['cases'][1]['baseline_project']
    read_bound(second_ref['path'],second_ref['sha256'])
    c_row=next(r for r in comparisons['rows'] if r['record_id']=='RESP-003')
    c_ref=next(r for r in c_row['project_bindings'] if r['path'].endswith('/C.ustx'))
    c_project=yaml.safe_load(read_bound(c_ref['path'],c_ref['expected_sha256']).read_text(encoding='utf-8'))
    runtime_ref=next(r for r in load(OUT/'response-source-audit.json')['source_files'] if r['path']=='runs/lastpage_brec_cohort_probe_20261008/frozen_runtime.json')
    registry=load(read_bound(runtime_ref['path'],runtime_ref['sha256']))
    install=Path(load_config()['openutau_dir']).resolve()
    expected=protocol['fixed']['runtime_expected_hashes']
    resources=resolve_registry(registry,expected,install)
    for alias,p in resources.items(): assert sha(p)==expected[alias], alias
    speaker_checks=[]
    for a,v in records+[(c,vc)]:
        for record,key in [(a,'singer_location'),(v,'variance_speaker_root')]:
            speaker=[]
            for label in ['Normal','Classic']:
                p=Path(record[key])/f'Yousa_{label}.emb'
                alias='external-resource/OpenUtau/'+p.relative_to(install).as_posix()
                assert alias in expected and sha(p)==expected[alias]
                speaker.append(np.fromfile(p,dtype='<f4'))
            weighted=.75*speaker[0]+.25*speaker[1]
            values=tensors(record['tensors'])['spk_embed']
            assert np.array_equal(values,np.broadcast_to(weighted,values.shape))
            speaker_checks.append(dict(phrase=record['phrase_index'],stage=key,frames=values.shape[1],exact=True))
    rows=[]
    for (a,v),case in zip(records,protocol['cases']):
        identity=check_identity(a,v,case)
        curve=planned_curve(project,a,case)
        sampled=sample_curve(project,a,curve)
        sampling=check_sample_support(a,sampled,case)
        rows.append(dict(condition_id=case['condition']['id'],historical_identity=identity,
            planned_curve=curve,sampling=sampling,new_native_export_matches=False))
        (run/(case['condition']['id']+'-planned-curve.json')).write_text(json.dumps(dict(
            role='curve data only; no USTX write or current installed sampling',curve=curve,
            sampled_cents=sampled.tolist()),indent=2)+'\n',encoding='utf-8')
    old_curve=next(r for r in c_project['voice_parts'][22]['curves'] if r['abbr']=='shfc')
    planned=rows[0]['planned_curve'];old_points=dict(zip(old_curve['xs'],old_curve['ys']))
    assert all(old_points.get(x,0)==y for x,y in zip(planned['xs'],planned['ys']))
    assert not any(y for x,y in old_points.items() if x not in planned['xs'])
    sampled=sample_curve(project,records[0][0],planned)
    assert np.array_equal(sampled,np.asarray(c['tone_shift_cents'],np.float32))
    semitones=sample_curve(project,records[0][0],planned,unit='semitones')
    assert np.array_equal(semitones,np.asarray(vc['tone_shift_semitones'],np.float32))
    c_identity=check_identity(c,vc,protocol['cases'][0])
    rows[0]['old_C_integer_points_exact']=True
    rows[0]['old_C_native_SHFC_samples_exact']=True
    rows[0]['old_C_variance_shift_samples_exact']=True
    rows[0]['float32_cents_then_divide100_differs_frames']=int(np.count_nonzero(sampled/np.float32(100)!=semitones))
    # Actual-record negative controls: deliberate confounds must be rejected.
    rejected=[]
    for fault in ['phrase','clock','target_tone','target_start','duration','language']:
        a,v=copy.deepcopy(records[0])
        if fault=='phrase':a['phrase_index']=21
        elif fault=='clock':a['frame_ms']=float(np.nextafter(np.float32(a['frame_ms']),np.float32(np.inf)))
        elif fault=='target_tone':a['phones'][8]['tone']+=1
        elif fault=='target_start':a['phones'][8]['positionMs']+=1
        elif fault=='duration':next(t for t in a['tensors'] if t['name']=='durations')['values'][0]+=1
        elif fault=='language':next(t for t in a['tensors'] if t['name']=='languages')['values'][9]=3
        try:check_identity(a,v,protocol['cases'][0])
        except ValueError:rejected.append(fault)
        else:raise AssertionError('Identity guard accepted '+fault)
    # Model declarations were extracted with onnx.load, no session/inference.
    contracts=[]
    for role in ['variance','acoustic','vocoder']:
        path=run/f'{role}-model-contract.json'; model=load(path)
        assert model['sha256']==expected[model['source_alias']] and not model['model_executed']
        import onnx
        graph=onnx.load(str(resources[model['source_alias']]),load_external_data=False)
        def declaration(row):
            t=row.type.tensor_type
            return dict(name=row.name,type=t.elem_type,shape=[d.dim_value if d.HasField('dim_value') else d.dim_param for d in t.shape.dim])
        assert model['inputs']==[declaration(v) for v in graph.graph.input]
        assert model['outputs']==[declaration(v) for v in graph.graph.output]
        assert model['random_nodes']==[dict(name=n.name,op=n.op_type) for n in graph.graph.node if n.op_type.startswith('Random')]
        assert not any(t.data_location==1 for t in graph.graph.initializer)
        del graph
        assert model['external_initializers']==0
        contracts.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        for a,v in records:
            n=tensors(a['tensors'])['f0'].size
            if role=='variance':inputs=tensors(v['tensors']);noise=(1,3,24,n)
            elif role=='acoustic':inputs=tensors(a['tensors']);noise=(1,1,128,n)
            else:inputs=dict(mel=np.zeros((1,n,128),np.float32),f0=np.asarray(a['vocoder_f0'],np.float32)[None,:]);noise=None
            declarations=copy.deepcopy(model['inputs'])
            if noise:
                assert len(model['random_nodes'])==1 and model['random_nodes'][0]['op']=='RandomNormalLike'
                inputs['probe_noise']=np.zeros(noise,np.float32)
                declarations.append(dict(name='probe_noise',type=1,shape=[*noise[:3],'n_frames']))
            else:assert not model['random_nodes']
            feeds=normalize_model_inputs(inputs,declarations)
            for k,x in inputs.items():
                assert x.dtype==feeds[k].dtype and np.array_equal(x.ravel(),feeds[k].ravel())
    # Local IL, source reader and model summaries are evidence, not execution.
    metadata=load(run/'core-metadata.json')
    assert metadata['sha256']==expected['external-resource/OpenUtau/OpenUtau.Core.dll']
    selected=[]
    for typ,names in [('OpenUtau.Core.TimeAxis',['MsPosToTickPos','TickPosToMsPos']),
        ('OpenUtau.Core.DiffSinger.DiffSingerUtils',['SampleCurve','DurationsMsToFrames']),
        ('OpenUtau.Core.Render.RenderPhrase',['SampleCurve']),
        ('OpenUtau.Core.DiffSinger.DsVariance+<>c',['<Process>b__19_5'])]:
        t=next(t for t in metadata['types'] if t['name']==typ)
        for name in names:
            m=next(m for m in t['methods'] if m['name']==name)
            assert m['il']
            selected.append(dict(type=typ,**m))
    (run/'selected-clock-sampling-IL.json').write_text(json.dumps(selected,indent=2)+'\n',encoding='utf-8')
    for name,h in reads.items(): assert sha(ROOT/name)==h
    for alias,p in resources.items(): assert sha(p)==expected[alias]
    result=dict(stage='2E-native',status='historical_native_and_static_backend_checked_with_execution_gaps',
        baseline=binding,rows=rows,speaker_checks=speaker_checks,historical_C_identity=c_identity,
        source_bindings=[dict(path=n,sha256=h) for n,h in reads.items()],
        private_evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in
            [run/'core-metadata.json',run/'selected-clock-sampling-IL.json',run/'metadata-reader/Program.cs',run/'metadata-reader/MetadataReader.csproj']],
        model_contracts=contracts,actual_record_negative_controls=rejected,runtime_resources_rehashed=47,
        installed_models_executed=False,new_native_exports=0,real_waveforms=0,new_feedback=0,
        frozen_protocol_unchanged=True,stage_2E_complete=False,measurement_validated_upgrades=False,
        vocabulary_token_semantics_revalidated=False,semantic_boundary='No historical prediction feeds or historical audio used as new execution')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(conditions=2,phones=41,frames=[421,594],old_C_exact=True,
        speaker_checks=6,model_declarations=3,rejected_identity_confounds=len(rejected),runtime=47,new_audio=0)))


if __name__=='__main__':
    main()
