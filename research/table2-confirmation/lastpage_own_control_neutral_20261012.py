"""Execute frozen own F, neutralizing one three-channel manual control group."""
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
from shfc_path_backend import model_feed

PRIOR=ROOT/'runs/research/lastpage-own-bright-cute-feedback-20261012'
E=ROOT/'runs/experiments/lastpage-own-bright-cute-20261012'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
CURRENT=ROOT/'runs/production/lastpage-accepted-baseline-20261011'
MODELS=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011/fresh/models'
RUN=ROOT/'runs/experiments/lastpage-own-control-neutral-20261012'
CHANNELS=['breathiness','voicing','tension']

def runtime():
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h,p
    check(load(RUN/'design/protocol.json')['model_adapters'])

def prepare():
    assert not RUN.exists()
    seal=load(PRIOR/'completion-manifest.json');check(seal['files']+seal['documents']+seal['entries'])
    protected=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(protected);RUN.mkdir(parents=True);(RUN/'logs').mkdir();(RUN/'score').mkdir();save(RUN/'protected-before.json',protected)
    for name in ENTRIES:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    plan=load(PRIOR/'design/next-own-control-neutral-protocol.json');check([plan[k] for k in ['baseline_score','baseline_media','author_reference']])
    assert plan['contexts']==[28,29] and plan['budget']['new_seeded_waveforms']==4
    doc=yaml.safe_load((ROOT/plan['baseline_score']['path']).read_text(encoding='utf-8-sig'));f=copy.deepcopy(doc)
    for ctx in [28,29]:
        for abbr,default in plan['recipe']['UI_defaults'].items():
            assert default==f['expressions'][abbr]['default_value']
            c=next(c for c in f['voice_parts'][ctx]['curves'] if c['abbr']==abbr)
            assert all(x%5==0 for x in c['xs']);c['ys']=[default]*len(c['ys'])
    full=RUN/'score/lastpage_own_control_neutral_F.ustx';full.write_text(yaml.safe_dump(f,allow_unicode=True,sort_keys=False),encoding='utf-8')
    native=copy.deepcopy(f);native['voice_parts']=[native['voice_parts'][i] for i in [28,29]];native['wave_parts']=[];native['tracks']=[native['tracks'][0]]
    native['tracks'][0].update(volume=0,pan=-100,mute=False,solo=False)
    (RUN/'score/native_F.ustx').write_text(yaml.safe_dump(native,allow_unicode=True,sort_keys=False),encoding='utf-8')
    plan.update(status='frozen_before_execution',execution_authorization='2026-10-12 user 下一步',
        original_frozen_protocol=ref(PRIOR/'design/next-own-control-neutral-protocol.json'),candidate=ref(full),native_score=ref(RUN/'score/native_F.ustx'),
        model_adapters=[ref(MODELS/'variance.onnx'),ref(MODELS/'acoustic.onnx')],
        original_zero_counts='frozen preparation only; actual execution reported separately')
    save(RUN/'design/protocol.json',plan);save(RUN/'native-inputs/runtime.json',load(E/'native-inputs/runtime.json'))
    runtime();print('One own-F candidate prepared, E reused unchanged.',flush=True)

def native():
    runtime();exe=Path(load_config()['openutau_dir'])/'a2u-shfcprobe-20261008.exe';p=str(RUN/'score/native_F.ustx')
    commands=[('roundtrip',['roundtrip','--project',p,'--out',str(RUN/'native-inputs/F-roundtrip.ustx')]),
        ('phones',['export-phonemes','--project',p,'--out',str(RUN/'native-inputs/F-phones.json')]),
        ('pitch',['export-pitch','--project',p,'--out',str(RUN/'native-inputs/F-pitch.json')]),
        ('render',['render','--project',p,'--out',str(RUN/'native-render/F.wav'),'--mixdown','--timeout','15']),
        ('probe',['export-render-probe','--project',p,'--out',str(RUN/'native-inputs/F'),'--indices','0,1'])]
    for kind,args in commands:
        result=RUN/f'native-inputs/F-{kind}-result.json'
        if result.exists():continue
        print('Native F',kind,flush=True)
        proc=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
        log=RUN/f'logs/F-{kind}.log';assert not log.exists();log.write_text(proc.stdout+proc.stderr,encoding='utf-8')
        assert proc.returncode==0,proc.stdout[-1000:]+proc.stderr[-1000:]
        r=json.loads(proc.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(result,r)
    runtime();print('Native F exported; independent gate required.',flush=True)

def execute():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed' and not (RUN/'fresh').exists();runtime()
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    f=load(RUN/'native-inputs/F/phrase_000.json')
    variance,acoustic,vocoder=[ort.InferenceSession(str(p),sess_options=options,providers=['CPUExecutionProvider']) for p in [MODELS/'variance.onnx',MODELS/'acoustic.onnx',f['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),model_adapters=load(RUN/'design/protocol.json')['model_adapters'],seeds=[11,101],max_waveforms=4,ort=ort.__version__,numpy=np.__version__))
    rows=[]
    for j,ctx in enumerate([28,29]):
        f=load(RUN/f'native-inputs/F/phrase_{j:03}.json');v=load(RUN/f'native-inputs/F/variance_{j:03}.json')
        for label in ['F','F_repeat']:
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
    runtime();save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=4,acoustic_vocoder_waveforms=4,sealed_E_reused=True,measurement_validated=False))

if __name__=='__main__':{'prepare':prepare,'native':native,'execute':execute}[sys.argv[1]]()
