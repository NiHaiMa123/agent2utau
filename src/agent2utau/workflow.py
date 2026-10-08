"""Fresh source observations and explicit Agent functions; no musical selector."""
from pathlib import Path
import copy, importlib.util, json
import numpy as np
from .openutau.ustx import load_ustx, save_ustx, sha256
from .openutau.bridge import run_bridge
from .resources.config import REPO_ROOT

def write_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')

def design_math():
    spec=importlib.util.spec_from_file_location('agent_design_functions',REPO_ROOT/'skills/singing-expression-editor/scripts/design_functions.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def observe_source(source, out, cfg, steps, seed=11, asr_model='large-v3-turbo'):
    from .audio.decode import decode
    source=Path(source).resolve();out=Path(out).resolve()
    if not source.is_file(): raise FileNotFoundError(source)
    if not set(steps)<={'separate','asr','game','fcpe','rmvpe'}: raise ValueError('Unknown observation step')
    out.mkdir(parents=True,exist_ok=False)
    binding=dict(source=str(source),source_sha256=sha256(source),seed=seed,steps=steps,source_only=True,expression_generated=False)
    write_json(out/'request.json',binding);decode(source,out/'source.wav');vocal=out/'source.wav'
    if 'separate' in steps:
        from .audio.separate import separate
        separated=separate(vocal,out/'stems');write_json(out/'separation.json',separated);vocal=Path(separated['vocals'])
    if 'asr' in steps:
        from .analysis.lyrics import transcribe
        write_json(out/'asr.json',transcribe(vocal,model=asr_model))
    if 'game' in steps:
        import soundfile as sf
        from .transcription.game_onnx import GameOnnx
        samples,sr=sf.read(vocal,dtype='float32');samples=samples.mean(axis=1) if samples.ndim>1 else samples
        model_dir=Path(cfg['openutau_dir'])/'Dependencies/game';game=GameOnnx(model_dir)
        if sr!=game.sr:
            import librosa
            samples=librosa.resample(samples,orig_sr=sr,target_sr=game.sr)
        write_json(out/'game.json',dict(semantics='note events, NOT frame F0',notes=game.infer(samples,language='zh',seed=seed),models={str(p):sha256(p) for p in model_dir.glob('*.onnx')}))
    for name in ['fcpe','rmvpe']:
        if name not in steps: continue
        if name=='fcpe':
            from .analysis.f0 import extract_f0
            result=extract_f0(vocal)
        else:
            from .analysis.rmvpe import infer_rmvpe
            result=infer_rmvpe(vocal,Path(cfg['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx')
        np.savez_compressed(out/f'{name}.npz',**{k:v for k,v in result.items() if isinstance(v,np.ndarray)})
        write_json(out/f'{name}_provenance.json',dict(input_sha256=sha256(vocal),metadata={k:v for k,v in result.items() if not isinstance(v,np.ndarray)}))
    if sha256(source)!=binding['source_sha256']: raise ValueError('Source changed during observation')
    binding['files']={str(p.relative_to(out)):sha256(p) for p in out.rglob('*') if p.is_file()};write_json(out/'manifest.json',binding)
    return dict(status='completed',out=str(out),source_only=True,expression_generated=False)

def compile_functions(plan_path, out, cfg):
    """Compile explicit absolute functions, preserving caller-owned note connections."""
    plan_path=Path(plan_path).resolve();plan=json.loads(plan_path.read_text(encoding='utf8'))
    if set(plan)!={'schema_version','project','source_audio','input_hashes','scope','phrases'} or plan['schema_version']!=1 or plan['scope']!='whole_song':
        raise ValueError('Use the documented complete whole-song function plan')
    def resolve(p):
        p=Path(p);return (plan_path.parent/p).resolve() if not p.is_absolute() else p.resolve()
    project=resolve(plan['project']);source=resolve(plan['source_audio']);bindings={resolve(p):h for p,h in plan['input_hashes'].items()}
    if project not in bindings or source not in bindings: raise ValueError('Bind current source audio and Agent score by SHA256')
    for p,h in bindings.items():
        if p.is_relative_to(REPO_ROOT/'research') or p.is_relative_to(REPO_ROOT/'.local-archive'): raise ValueError('Research/archive is not a production compiler input')
        if sha256(p)!=h: raise ValueError(f'Changed input: {p}')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);doc=copy.deepcopy(load_ustx(project))
    for part in doc.get('voice_parts',[]):
        part['curves']=[c for c in part.get('curves',[]) if c['abbr']!='pitd']
        for note in part['notes']:
            if 'vibrato' in note: note['vibrato']['length']=0
    save_ustx(doc,out/'baseline.ustx')
    def export(command, project, target):
        report=run_bridge(cfg,[command,'--project',str(project),'--out',str(target)]);write_json(out/(target.stem+'_export.json'),report)
        if not report.get('ok'): raise RuntimeError(f'Native {command} failed; logs retained')
        return json.loads(target.read_text(encoding='utf8'))
    baseline=export('export-pitch',out/'baseline.ustx',out/'baseline_pitch.json')['phrases']
    phones=export('export-phonemes',out/'baseline.ustx',out/'baseline_phones.json')
    if not baseline or len(baseline)!=len(plan['phrases']): raise ValueError('Incomplete native phrase coverage')
    math=design_math();points={};targets=[];checks=[]
    for native,intent in zip(baseline,plan['phrases']):
        if set(intent)!={'part_index','position','design'}: raise ValueError('Unknown phrase-plan fields')
        if not isinstance(intent['part_index'],int) or not 0<=intent['part_index']<len(doc['voice_parts']): raise ValueError('Unknown native part index')
        part=doc['voice_parts'][intent['part_index']]
        if native['part_position']!=part['position'] or native['position']!=intent['position']: raise ValueError('Native phrase identity/order changed')
        times=np.asarray(native['times_ms'],float)/1000;design=intent['design'];math.validate(design)
        if not np.allclose(design['support_s'],[times[0],times[-1]],rtol=0,atol=1e-9): raise ValueError('Design must cover the complete native phrase clock')
        local=math.compile_plan(design)
        if not local['shape_checks_pass']: raise ValueError('Agent local expectation failed')
        target=np.array([math.evaluate(design,float(t)) for t in times]);offsets=np.rint(target-np.asarray(native['before_pitd_cents'])).astype(int)
        descriptor=doc.get('expressions',{}).get('pitd',{'min':-1200,'max':1200})
        if np.any(offsets<descriptor['min']) or np.any(offsets>descriptor['max']): raise ValueError('PITD exceeds configured range; redesign note connections')
        own=points.setdefault(intent['part_index'],{});ticks=native['pitch_start_tick']+np.arange(len(times))*native['pitch_interval_ticks']-part['position']
        for tick,value in zip(ticks,offsets):
            if tick!=int(tick) or int(tick) in own: raise ValueError('Colliding/non-integer native pitch samples')
            own[int(tick)]=int(value)
        targets.append(target);checks.append(local['local_checks'])
    for pi,own in points.items():
        xs=sorted(own);doc['voice_parts'][pi]['curves'].append(dict(abbr='pitd',xs=xs,ys=[own[x] for x in xs]))
    save_ustx(doc,out/'project.ustx');actual=export('export-pitch',out/'project.ustx',out/'pitch.json')['phrases']
    if len(actual)!=len(baseline): raise ValueError('Native phrase count changed')
    error=0.
    for before,after,target in zip(baseline,actual,targets):
        if before['times_ms']!=after['times_ms']: raise ValueError('Native pitch clock changed')
        error=max(error,float(np.max(abs(np.asarray(after['final_cents'])-target))))
    if error>.501: raise ValueError(f'Native target readback failed: {error} cents')
    afterphones=export('export-phonemes',out/'project.ustx',out/'phones.json')
    def geometry(parts): return [{**p,'phrases':[{k:v for k,v in ph.items() if k!='final_cents'} for ph in p['phrases']]} for p in parts]
    if geometry(phones['parts'])!=geometry(afterphones['parts']): raise ValueError('Native note/phone geometry changed')
    report=dict(status='completed',stage='native_checked',project=str(out/'project.ustx'),plan_sha256=sha256(plan_path),native_max_error_c=error,local_checks=checks,audio_rendered=False,naturalness_accepted=False,source_or_author_curve_inherited=False,files={str(p.relative_to(out)):sha256(p) for p in out.rglob('*') if p.is_file()})
    write_json(out/'compile_report.json',report);return report
