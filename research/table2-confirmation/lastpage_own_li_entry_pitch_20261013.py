"""One frozen independent low-entry pitch gesture, with production knowledge gate."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT,ENTRIES,load,save,sha,ref,check
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from agent2utau.resources.config import load_config
from agent2utau.openutau.ustx import TempoMap
from agent2utau.knowledge import collect_context,check_plan_knowledge
from shfc_path_backend import model_feed

PRIOR=ROOT/'runs/research/lastpage-li-condition-review-20261013'
F=ROOT/'runs/experiments/lastpage-own-control-neutral-20261012'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
CURRENT=ROOT/'runs/production/lastpage-accepted-baseline-20261011'
MODELS=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011/fresh/models'
RUN=ROOT/'runs/experiments/lastpage-own-li-entry-pitch-20261013'
CHANNELS=['breathiness','voicing','tension']

def runtime():
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h,p
    plan=load(RUN/'design/protocol.json');check(plan['model_adapters']+plan['integration_sources'])
    check_plan_knowledge(plan,RUN/'design/protocol.json')

def pitch_function(time,nodes):
    for (a,x,dx),(b,y,dy) in zip(nodes,nodes[1:]):
        if a<=time<=b:
            u=(time-a)/(b-a);h=b-a
            return (2*u**3-3*u**2+1)*x+(u**3-2*u**2+u)*h*dx+(-2*u**3+3*u**2)*y+(u**3-u**2)*h*dy
    raise ValueError(time)


def prepare():
    assert not RUN.exists()
    seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    original=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(original);RUN.mkdir(parents=True);(RUN/'logs').mkdir();(RUN/'score').mkdir()
    registry='docs/knowledge/acoustic-manifestations-20261009/active-knowledge-sources.json'
    save(RUN/'protected-before.json',[r for r in original if r['path']!=registry])
    for name in ENTRIES+[registry]:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    plan=load(PRIOR/'design/next-li-entry-pitch-protocol.json')
    assert plan['budget']['new_seeded_synthesis_waveforms']==2
    check([plan[k] for k in ['baseline_score','baseline_audio','author_reference']]+plan['source_bindings'])
    (RUN/'design').mkdir();(RUN/'design/knowledge_context.json').write_bytes((PRIOR/'design/knowledge_context.json').read_bytes())
    _,receipt=check_plan_knowledge(plan,RUN/'design/protocol.json');save(RUN/'evaluation/knowledge_receipt.json',receipt)
    doc=yaml.safe_load((ROOT/plan['baseline_score']['path']).read_text(encoding='utf-8-sig'));candidate=copy.deepcopy(doc)
    part=candidate['voice_parts'][28];curve=next(c for c in part['curves'] if c['abbr']=='pitd')
    before=load(F/'native-inputs/F-pitch.json')['phrases'][0];tm=TempoMap.from_doc(doc)
    assert len(curve['xs'])==len(before['final_cents']) and all(b-a==5 for a,b in zip(curve['xs'],curve['xs'][1:]))
    nodes=plan['gesture']['center_nodes'];lo,hi=plan['gesture']['support_s'];rows=[]
    for i,x in enumerate(curve['xs']):
        tick=part['position']+x;sec=tm.tick_to_ms(tick)/1000
        assert tick==before['pitch_start_tick']+i*5 and abs(sec-before['times_ms'][i]/1000)<1e-9
        if lo<=sec<=hi:
            target=pitch_function(sec,nodes);value=int(np.rint(target-before['before_pitd_cents'][i]))
            rows.append(dict(grid_index=i,tick=tick,time_s=sec,target_cents=target,old_pitd=curve['ys'][i],new_pitd=value))
            curve['ys'][i]=value
    desc=doc['expressions']['pitd'];assert min(curve['ys'])>=desc['min'] and max(curve['ys'])<=desc['max']
    assert any(r['new_pitd']!=r['old_pitd'] for r in rows)
    full=RUN/'score/lastpage_own_li_entry_pitch_J.ustx';full.write_text(yaml.safe_dump(candidate,allow_unicode=True,sort_keys=False),encoding='utf-8')
    native=copy.deepcopy(candidate);native['voice_parts']=[native['voice_parts'][i] for i in [28,29]];native['wave_parts']=[];native['tracks']=[native['tracks'][0]]
    native['tracks'][0].update(volume=0,pan=-100,mute=False,solo=False)
    (RUN/'score/native_J.ustx').write_text(yaml.safe_dump(native,allow_unicode=True,sort_keys=False),encoding='utf-8')
    plan.update(status='frozen_before_execution',execution_authorization='2026-10-13 user 继续',
        original_frozen_protocol=ref(PRIOR/'design/next-li-entry-pitch-protocol.json'),candidate=ref(full),native_score=ref(RUN/'score/native_J.ustx'),
        model_adapters=[ref(MODELS/'variance.onnx'),ref(MODELS/'acoustic.onnx')],integration_sources=[ref(ROOT/p) for p in
            ['src/agent2utau/knowledge.py','src/agent2utau/workflow.py','src/agent2utau/cli.py','docs/guides/knowledge-use-in-production.md']])
    save(RUN/'design/protocol.json',plan);_,again=check_plan_knowledge(plan,RUN/'design/protocol.json');assert again==receipt
    save(RUN/'native-inputs/runtime.json',load(F/'native-inputs/runtime.json'))
    save(RUN/'design/compiled-pitch.json',dict(nodes=nodes,support_s=[lo,hi],rows=rows,original5tick_grid=True,encoding='target minus native before-PITD, nearest-even integer cents',score=ref(full)))
    runtime();print('J own-entry pitch and inherited19-ID receipt prepared.',flush=True)


def native():
    runtime();exe=Path(load_config()['openutau_dir'])/'a2u-shfcprobe-20261008.exe';p=str(RUN/'score/native_J.ustx')
    commands=[('roundtrip',['roundtrip','--project',p,'--out',str(RUN/'native-inputs/J-roundtrip.ustx')]),
        ('phones',['export-phonemes','--project',p,'--out',str(RUN/'native-inputs/J-phones.json')]),
        ('pitch',['export-pitch','--project',p,'--out',str(RUN/'native-inputs/J-pitch.json')]),
        ('render',['render','--project',p,'--out',str(RUN/'native-render/J.wav'),'--mixdown','--timeout','15']),
        ('probe',['export-render-probe','--project',p,'--out',str(RUN/'native-inputs/J'),'--indices','0,1'])]
    for kind,args in commands:
        result=RUN/f'native-inputs/J-{kind}-result.json'
        if result.exists():continue
        print('Native J',kind,flush=True)
        proc=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
        log=RUN/f'logs/J-{kind}.log';assert not log.exists();log.write_text(proc.stdout+proc.stderr,encoding='utf-8')
        assert proc.returncode==0,proc.stdout[-1000:]+proc.stderr[-1000:]
        r=json.loads(proc.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(result,r)
    runtime();print('Native J exported; independent gate required.',flush=True)


def execute():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed' and not (RUN/'fresh').exists();runtime()
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    f=load(RUN/'native-inputs/J/phrase_000.json')
    variance,acoustic,vocoder=[ort.InferenceSession(str(p),sess_options=options,providers=['CPUExecutionProvider']) for p in [MODELS/'variance.onnx',MODELS/'acoustic.onnx',f['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),model_adapters=load(RUN/'design/protocol.json')['model_adapters'],seeds=[11,101],max_waveforms=2,ort=ort.__version__,numpy=np.__version__))
    rows=[]
    for j,ctx in enumerate([28]):
        f=load(RUN/f'native-inputs/J/phrase_{j:03}.json');v=load(RUN/f'native-inputs/J/variance_{j:03}.json')
        for label in ['J','J_repeat']:
            ac,va=tensors(f['tensors']),tensors(v['tensors']);n=ac['f0'].size;va['probe_noise']=gaussian_frame_noise(11,3,24,n)
            names=[o.name for o in variance.get_outputs()];pred=dict(zip(names,variance.run(names,model_feed(variance,va))));clipping={}
            for ch in CHANNELS:
                lo,hi=(-10,10) if ch=='tension' else (-96,0);raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                clipping[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)));ac[ch]=np.clip(raw,lo,hi).astype(np.float32)
            ac['probe_noise']=gaussian_frame_noise(101,1,128,n);mel=acoustic.run(['mel'],model_feed(acoustic,ac))[0];vm=mel.copy()
            if f['acoustic_mel_base']!=f['vocoder_mel_base']:vm*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
            vf=np.asarray(f['vocoder_f0'],np.float32)[None,:];wave=vocoder.run(None,model_feed(vocoder,dict(mel=vm,f0=vf)))[0].reshape(-1)
            assert np.isfinite(wave).all() and len(wave)==n*512
            d=RUN/f'fresh/context{ctx}/{label}';d.mkdir(parents=True);np.save(d/'raw.npy',wave)
            for name,x in [('inputs',ac),('variance-inputs',va),('predictions',pred),('mel',dict(mel=mel)),('vocoder-f0',dict(f0=vf))]:np.savez_compressed(d/(name+'.npz'),**x)
            rows.append(dict(context=ctx,variant=label,frames=n,samples=len(wave),feature_clipping=clipping,
                wave_start_s=load(BASE/f'synthesis/phrase_{ctx:03}.json')['wave_start_s'],raw_peak=float(np.max(np.abs(wave)))))
            print('Fresh',ctx,label,'done',flush=True)
    runtime();save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=2,acoustic_vocoder_waveforms=2,sealed_F_reused=True,measurement_validated=False))



if __name__=='__main__': {'prepare':prepare,'native':native,'execute':execute}[sys.argv[1]]()

