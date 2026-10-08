"""Read-only evaluation of USTX and explicitly bound native observations."""
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import json, subprocess
import numpy as np
import yaml
from ..openutau.ustx import TempoMap, sha256
from .features import Thresholds, boundary_candidates, control_coupling, phone_kind, polyline_complexity, shape_features, vowel_groups

SCHEMA=1


def dump(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf8')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def finding(code,time_range,region_type,evidence,source,confidence='structural',severity='info',next_probe='Review contextual evidence'):
    return dict(code=code,severity=severity,confidence=confidence,source=source,time_range=time_range,region_type=region_type,evidence=evidence,
                limitations=['technical observation, not perceived naturalness or cause'],next_probe=next_probe)


def validate_native(project,doc,tm,pitch_path,phones_path,provenance):
    """A path in an export is insufficient; byte binding plus geometry is required."""
    if not all([pitch_path,phones_path,provenance]):return None,'missing_native_inputs_or_provenance'
    bind=read(provenance)
    for key,path in [('project_sha256',project),('pitch_sha256',pitch_path),('phonemes_sha256',phones_path)]:
        if bind.get(key)!=sha256(path):raise ValueError('Native binding mismatch: '+key)
    environment=bind.get('environment',{})
    if bind.get('schema_version')!=SCHEMA or not all(environment.get(k) for k in ['core_sha256','bridge_sha256','singer_id','singer_config_sha256']):
        return None,'missing_native_environment_binding'
    pitch,phones=read(pitch_path),read(phones_path)
    if pitch.get('schema_version')!=1 or phones.get('schema_version')!=1:
        raise ValueError('Unsupported native schema')
    if pitch.get('units')!='absolute MIDI times 100 cents; absolute project milliseconds' or phones.get('units')!='absolute project milliseconds; pitch absolute MIDI times 100 cents':
        raise ValueError('Native units mismatch')
    if len(phones['parts'])!=len(doc['voice_parts']):raise ValueError('Native part geometry mismatch')
    flat=[]
    for part,original in zip(phones['parts'],doc['voice_parts']):
        if part['part_position']!=original['position'] or part['track_no']!=original['track_no'] or len(part['notes'])!=len(original['notes']):
            raise ValueError('Native part identity mismatch')
        for i,(n,raw) in enumerate(zip(part['notes'],original['notes'])):
            if n['note_index']!=i or n['lyric']!=raw['lyric'] or n['tone']!=raw['tone'] or not np.allclose([n['start_ms'],n['end_ms']],[tm.tick_to_ms(original['position']+raw['position']),tm.tick_to_ms(original['position']+raw['position']+raw['duration'])],rtol=0,atol=1e-6):
                raise ValueError('Native note identity/time mismatch')
        flat.extend((part,ph) for ph in part['phrases'])
    if len(flat)!=len(pitch['phrases']):raise ValueError('Native phrase count mismatch')
    for (part,ph),line in zip(flat,pitch['phrases']):
        if line['part_position']!=part['part_position'] or line['track_no']!=part['track_no'] or line['position']!=ph['position'] or line['times_ms']!=ph['pitch_times_ms'] or line['final_cents']!=ph['final_cents']:
            raise ValueError('Native pitch/phone identity mismatch')
        t=np.asarray(line['times_ms'],float);y=np.asarray(line['final_cents'],float);b=np.asarray(line['before_pitd_cents'],float)
        if len(t)!=len(y) or len(t)!=len(b) or len(t)<2 or not all(np.all(np.isfinite(z)) for z in [t,y,b]) or np.any(np.diff(t)<=0):
            raise ValueError('Invalid native samples')
    return dict(pitch=pitch,phones=phones,provenance=bind),None


def extract_regions(native):
    regions=[];phrases=[]
    for pi,part in enumerate(native['phones']['parts']):
        for fi,ph in enumerate(part['phrases']):
            prefix=f'p{pi}:f{fi}';phone_regions=[]
            for row in ph['phones']:
                owners=row.get('owner_primary_indices',[]);kind=phone_kind(row['phoneme'])
                valid=row.get('ownership_status')=='matched' and len(owners)==1 and 0<=owners[0]<len(part['notes'])
                if not valid:kind='unknown'
                elif part['notes'][owners[0]]['lyric'] in {'AP','SP'}:kind='non_singing'
                if not np.isfinite(row['start_ms']) or not np.isfinite(row['end_ms']) or row['end_ms']<=row['start_ms']:
                    raise ValueError('Invalid native phone span')
                r=dict(id=prefix+':h'+str(row['phone_index']),part_index=pi,phrase_index=fi,primary_index=owners[0] if valid else None,
                       symbol=row['phoneme'],region_type=kind,start_s=row['start_ms']/1000,end_s=row['end_ms']/1000,ownership_status=row.get('ownership_status'),note_indices=row.get('owner_note_indices',[]),source='bound_native_phone_clock')
                phone_regions.append(r);regions.append(r)
            groups=vowel_groups(phone_regions)
            for gi,g in enumerate(groups):
                g.update(id=prefix+':v'+str(gi),part_index=pi,phrase_index=fi,source='bound_native_vowel_clock');regions.append(g)
            phrases.append(dict(id=prefix,part_index=pi,phrase_index=fi,phones=phone_regions,vowels=groups,raw=ph))
    return regions,phrases


def sample_curve(curves,abbr,grid,default):
    curve=next((c for c in curves if c['abbr']==abbr),None)
    if curve is None or not curve.get('xs'):return np.full(len(grid),default,float)
    return np.interp(grid,curve['xs'],curve['ys'],left=default,right=default)


def static_inventory(doc,tm,cfg):
    regions=[];parts=[];findings=[]
    for pi,part in enumerate(doc['voice_parts']):
        counts={};curves=part.get('curves',[]);curve_valid=True
        for ci,c in enumerate(curves):
            x=np.asarray(c.get('xs',[]),float);y=np.asarray(c.get('ys',[]),float);desc=doc.get('expressions',{}).get(c['abbr'],{})
            default=desc.get('default_value');complexity=polyline_complexity(x,y,cfg.redundancy_error_units)
            valid=complexity['status']=='evaluated';curve_valid &= valid
            active=(y!=default) if default is not None else None
            span=(tm.tick_to_ms(part['position']+x[-1])-tm.tick_to_ms(part['position']+x[0]))/1000 if valid and len(x)>1 else None
            rows=counts.setdefault(c['abbr'],[])
            rows.append(dict(points=len(x),default_points=int(sum(y==default)) if default is not None else None,
                             effective_points=int(sum(y!=default)) if default is not None else None,default_value=default,
                             nondefault_point_runs=int(sum(active & ~np.r_[False,active[:-1]])) if active is not None and len(active) else 0,
                             declared_span_s=span,points_per_second=len(x)/span if span else None,
                             value_range=[float(min(y)),float(max(y))] if valid and len(y) else None,
                             complexity=complexity,coordinate_system='part-relative ticks',value_units='USTX descriptor units',descriptor=desc))
            if not valid:findings.append(finding('invalid_control_samples',None,'unknown',dict(part_index=pi,curve_index=ci,abbr=c['abbr']),'ustx',severity='warning'))
            elif len(y) and 'min' in desc and 'max' in desc:
                outside=(y<desc['min'])|(y>desc['max'])
                if any(outside):findings.append(finding('outside_declared_control_range',None,'control',dict(part_index=pi,abbr=c['abbr'],points=int(sum(outside))),'ustx',severity='warning'))
        notes=[]
        for ni,n in enumerate(part['notes']):
            start=tm.tick_to_ms(part['position']+n['position'])/1000;end=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
            if not np.isfinite(start) or not np.isfinite(end) or end<=start:raise ValueError('Invalid written note span')
            pitch=n.get('pitch',{}).get('data',[])
            r=dict(id=f'p{pi}:n{ni}',part_index=pi,note_index=ni,start_s=start,end_s=end,lyric=n['lyric'],tone=n['tone'],
                   region_type='non_singing' if n['lyric'] in {'AP','SP'} else 'note_only',continuation=str(n['lyric']).startswith('+'),
                   note_pitch_points=len(pitch),note_pitch_nonzero_points=sum(p.get('y',0)!=0 for p in pitch),note_pitch_coordinates='relative-note milliseconds; y units are 10 cents',source='written_score')
            notes.append(r);regions.append(r)
        grid=np.unique([float(x) for c in curves if c['abbr'] in {'tenc','brec'} for x in c.get('xs',[])])
        if len(grid) and curve_valid:
            a=sample_curve(curves,'tenc',grid,doc.get('expressions',{}).get('tenc',{}).get('default_value',0))
            b=sample_curve(curves,'brec',grid,doc.get('expressions',{}).get('brec',{}).get('default_value',0))
            coupling=control_coupling(a,b,doc.get('expressions',{}).get('tenc',{}).get('default_value',0),doc.get('expressions',{}).get('brec',{}).get('default_value',0),cfg)
            coupling['time_basis']='union of stored knots, unweighted; declared polyline proxy, not model inputs'
            if coupling.get('coupling_risk'):findings.append(finding('coupling_risk',[min(r['start_s'] for r in notes),max(r['end_s'] for r in notes)],'control',dict(part_index=pi,**coupling),'ustx_declared_controls',severity='review',next_probe='Bind predicted variance and actual inputs before causal testing'))
        else:coupling=dict(status='unknown' if not curve_valid else 'evaluated',both=0,a_only=0,b_only=0,neither=0,correlation=None,coupling_risk=False)
        parts.append(dict(part_index=pi,track_no=part['track_no'],notes=len(notes),note_pitch_points=sum(n['note_pitch_points'] for n in notes),curve_counts=counts,tenc_brec=coupling))
    return regions,parts,findings


def feedback_cases(path,project,doc,tm,native,regions,cfg):
    if path is None:return []
    feedback=read(path);base=Path(path).resolve().parent
    def resolve(p):return (base/p).resolve() if not Path(p).is_absolute() else Path(p)
    bound=feedback.get('project_sha256')==sha256(project)
    audio=resolve(feedback['audio_path']);audio_exists=audio.is_file()
    if audio_exists and sha256(audio)!=feedback.get('audio_sha256'):raise ValueError('Feedback audio hash mismatch')
    clock=False
    if feedback.get('delivery_manifest'):
        manifest=read(resolve(feedback['delivery_manifest']));files=manifest.get('files',{})
        clock=bound and feedback.get('timebase')=='delivery_identity' and files.get(Path(project).name)==sha256(project) and files.get(audio.name)==feedback.get('audio_sha256')
    result=[]
    for case in feedback['cases']:
        t=float(case['time_s']);located=audio_exists and bound and clock and native is not None
        phones=[r for r in regions if r.get('source')=='bound_native_phone_clock' and r['start_s']<=t<r['end_s']] if located else []
        context=[r for r in regions if r['source']=='written_score' and r['end_s']>t-.6 and r['start_s']<t+.6] if located else []
        controls=[]
        context_parts={r['part_index']:r for r in context}
        for r in context_parts.values():
            part=doc['voice_parts'][r['part_index']];ticks=np.array([tm.ms_to_tick((t-.5)*1000),tm.ms_to_tick(t*1000),tm.ms_to_tick((t+.5)*1000)])-part['position']
            if any(c['abbr'] in {'voic','dyn','tenc','brec'} and polyline_complexity(c.get('xs',[]),c.get('ys',[]),cfg.redundancy_error_units)['status']!='evaluated' for c in part.get('curves',[])):
                controls.append(dict(part_index=r['part_index'],status='unknown'));continue
            controls.append(dict(part_index=r['part_index'],source='declared_control_polyline_proxy',samples_at_s=[t-.5,t,t+.5],values={abbr:sample_curve(part.get('curves',[]),abbr,ticks,doc.get('expressions',{}).get(abbr,{}).get('default_value',100 if abbr=='voic' else 0)).tolist() for abbr in ['tenc','brec','voic','dyn']}))
        result.append(dict(id=case['id'],time_s=t,label=case['label'],label_source='explicit_user_feedback',status='located' if located and phones else ('timebase_unverified' if audio_exists and bound else 'insufficient_data'),
                           audio_sha256=feedback.get('audio_sha256'),project_sha256=feedback.get('project_sha256'),native_phone_hits=phones,written_context=context,control_context=controls,
                           hypotheses=[dict(name='pitch-dependent register or spectral response',falsifier='A fixed-context pitch intervention fails to change the relevant independently evaluated response'),dict(name='phoneme-dependent or voicing-conditioning response',falsifier='A fixed-phone/clock VOIC-only intervention fails to change the relevant independently evaluated response')],
                           limitations=['timestamp is approximate; native phone is not an acoustic lesion','different phones/tones confound between-position comparisons','predicted and actual model inputs not evaluated here','no audio perception'],cause='unknown',acoustic_boundary_verified=False))
    return result


def evaluate(project,out,role='current_agent_generated',native_pitch=None,phonemes=None,provenance=None,feedback=None,cfg=Thresholds(),command=None):
    project=Path(project).resolve();out=Path(out).resolve();before=sha256(project)
    doc=yaml.load(project.read_bytes(),Loader=getattr(yaml,'CSafeLoader',yaml.SafeLoader))
    if not isinstance(doc,dict) or not doc.get('voice_parts'):raise ValueError('No written voice parts')
    tempos=doc.get('tempos') or [dict(position=0,bpm=doc.get('bpm',120))]
    resolution=doc.get('resolution',480)
    if not isinstance(resolution,int) or resolution<=0 or any(not np.isfinite(t['bpm']) or t['bpm']<=0 for t in tempos) or len({t['position'] for t in tempos})!=len(tempos):
        raise ValueError('Invalid tempo/resolution')
    tm=TempoMap(tempos,resolution);regions,parts,findings=static_inventory(doc,tm,cfg)
    native,missing=validate_native(project,doc,tm,native_pitch,phonemes,provenance)
    stats=dict(evaluated=0,unknown=0,excluded_non_singing_candidates=0,unknown_boundary_candidates=0,unknown_phone_regions=0)
    if native:
        phone_regions,phrases=extract_regions(native);regions.extend(phone_regions)
        stats['unknown_phone_regions']=sum(r['region_type']=='unknown' for r in phone_regions)
        for phrase,line in zip(phrases,native['pitch']['phrases']):
            times=np.asarray(line['times_ms'])/1000;y=np.asarray(line['final_cents'])
            phrase_region=dict(id=phrase['id'],part_index=phrase['part_index'],region_type='phrase',start_s=float(times[0]),end_s=float(times[-1]),source='bound_native_intended_pitch')
            phrase_region['features']=shape_features(times,y,cfg);regions.append(phrase_region)
            for v in phrase['vowels']:
                mask=(times>=v['start_s'])&(times<v['end_s']);v['features']=shape_features(times[mask],y[mask],cfg)
                v['valid_samples']=int(sum(mask));v['coverage_fraction']=float(min(1,(times[mask][-1]-times[mask][0])/(v['end_s']-v['start_s']))) if sum(mask)>1 else 0.
                stats[v['features']['status']]+=1
            boundary=boundary_candidates(times,y,phrase['phones'],cfg);stats['excluded_non_singing_candidates']+=boundary['excluded_non_singing'];stats['unknown_boundary_candidates']+=boundary['unknown_region']
            for f in boundary['findings']:
                findings.append(finding(f['code'],f['time_range'],'boundary',dict(phrase_id=phrase['id'],**{k:v for k,v in f.items() if k not in {'code','time_range'}}),'bound_native_5tick_pitch','native_grid',severity='review',next_probe='Inspect context and actual renderer frames; multi-phase coverage remains unknown'))
    else:
        stats['unknown']=sum(r['region_type']=='note_only' for r in regions)
        findings.append(finding('native_absolute_pitch_unavailable',None,'unknown',dict(reason=missing),'missing_data',confidence='unknown',next_probe='Provide explicitly bound current native pitch and phones'))
    stats['unit']='merged_native_vowel_groups' if native else 'written_note_only_regions'
    findings.append(finding('requires_native_probe',None,'unknown',dict(multi_phase_verified=False),'coverage',confidence='unknown',next_probe='Verify native frame resampling and additional sampling phases without changing geometry'))
    cases=feedback_cases(feedback,project,doc,tm,native,regions,cfg)
    for case in cases:
        case['nearby_shape_candidates']=[f for f in findings if f['time_range'] is not None and f['source']=='bound_native_5tick_pitch' and f['time_range'][1]>case['time_s']-.6 and f['time_range'][0]<case['time_s']+.6] if case['status']=='located' else []
    inputs=dict(project=dict(sha256=before,name=project.name,role=role))
    for key,p in [('native_pitch',native_pitch),('phonemes',phonemes),('provenance',provenance),('feedback',feedback)]:
        if p:inputs[key]=dict(sha256=sha256(p),name=Path(p).name)
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[3],stderr=subprocess.DEVNULL).decode().strip()
    except (OSError,subprocess.CalledProcessError):commit='unavailable'
    code_files={p.name:sha256(p) for p in [Path(__file__),Path(__file__).with_name('features.py'),Path(__file__).with_name('__main__.py')]}
    summary=dict(schema_version=SCHEMA,inputs=inputs,code_commit=commit,code_files_sha256=code_files,command=command,thresholds=asdict(cfg),time_axis=dict(resolution=resolution,tempos=tempos,units='absolute project seconds'),
                 stage='native_verified' if native else 'static_only',native_absolute_pitch='bound_intended_pitch' if native else 'unavailable',environment=native['provenance']['environment'] if native else None,
                 parts=parts,region_counts=dict(Counter(r['region_type'] for r in regions)),vowel_evaluation=stats,findings_counts=dict(Counter(f['code'] for f in findings)),
                 coverage=dict(model_inputs='unknown',actual_audio_f0='unknown',acoustic_alignment='unknown',multi_phase='unknown',audio_perception_verified=False),
                 skipped_checks=['acoustic perception','measured formants','multi-phase native sampling','predicted/actual model input evaluation'],naturalness_accepted=False,
                 real_audio_error_rates=None,limitations=['unlabelled song candidates are not false positives','no automatic repair or sound-quality verdict'])
    if sha256(project)!=before:raise ValueError('Project changed during read-only evaluation')
    out.mkdir(parents=True,exist_ok=False);dump(out/'summary.json',summary)
    for name,rows in [('regions.jsonl',regions),('findings.jsonl',findings)]:
        (out/name).write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n' for r in rows),encoding='utf8')
    if feedback:dump(out/'feedback_cases.json',cases)
    (out/'report.md').write_text(f"# Independent evaluation v0\n\nInput: {project.name}, role: {role}, SHA256: {before}\n\nStage: {summary['stage']}; original unchanged.\n\nFindings: {json.dumps(summary['findings_counts'],ensure_ascii=False)}\n\nVowel coverage: {json.dumps(stats)}\n\nAll candidates are retained in findings.jsonl. Unknown and skipped checks are recorded in summary.json. Native arrays describe intended pitch/phones; audio perception and naturalness remain unverified.\n",encoding='utf8')
    return summary
