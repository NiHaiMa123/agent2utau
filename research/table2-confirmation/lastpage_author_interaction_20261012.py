"""Execute the frozen fourth author speaker/manual-control corner only."""
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

PRIOR=ROOT/'runs/research/lastpage-author-controls-feedback-20261012'
CONTROL=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
VOICE=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
MODELS=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011/fresh/models'
RUN=ROOT/'runs/experiments/lastpage-author-interaction-20261012'
CHANNELS=['breathiness','voicing','tension']


def runtime():
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h,p
    check(load(RUN/'design/protocol.json')['model_adapters'])


def prepare():
    assert not RUN.exists()
    sealed=load(PRIOR/'completion-manifest.json');check(sealed['files']+sealed['documents']+sealed['entries'])
    protected=load(PRIOR/'protected-before.json')+sealed['files']+sealed['documents']+[ref(PRIOR/'completion-manifest.json')]
    check(protected);RUN.mkdir(parents=True);(RUN/'logs').mkdir();(RUN/'score').mkdir();save(RUN/'protected-before.json',protected)
    for n in ENTRIES:
        p=RUN/'before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    frozen=load(PRIOR/'design/next-interaction-protocol.json');check(list(frozen['existing_scores'].values()))
    assert frozen['budget']['new_seeded_D_waveforms']==4 and frozen['contexts']==[0,1]
    doc=yaml.safe_load((ROOT/frozen['D_recipe']['base']['path']).read_text(encoding='utf-8-sig'));d=copy.deepcopy(doc)
    part=d['voice_parts'][0];end=max(n['position']+n['duration'] for n in part['notes'])+5
    for k,v in zip(['cl01','cl02','cl03','cl04','cl05'],frozen['D_recipe']['replace_only_cl01_cl05']):
        c=next(c for c in part['curves'] if c['abbr']==k);c['xs']=[0,end];c['ys']=[v,v]
    path=RUN/'score/D.ustx';path.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')
    frozen.update(status='frozen_before_execution',execution_authorization='2026-10-12 user 下一步',
        original_frozen_protocol=ref(PRIOR/'design/next-interaction-protocol.json'),D=ref(path),
        model_adapters=[ref(MODELS/'variance.onnx'),ref(MODELS/'acoustic.onnx')],
        actual_model_calls_and_new_waveforms='recorded separately on completion; prior audio_executed0 describes preparation')
    save(RUN/'design/protocol.json',frozen)
    save(RUN/'native-inputs/runtime.json',load(CONTROL/'native-inputs/runtime.json'))
    assert Path(load_config()['openutau_dir']).resolve()==Path(next(iter(load(RUN/'native-inputs/runtime.json')))).parent.resolve()
    runtime();print('Frozen D prepared; A/B/C explicit sealed reuse, no extra versions.',flush=True)


def native():
    runtime();exe=Path(load_config()['openutau_dir'])/'a2u-shfcprobe-20261008.exe';project=str(RUN/'score/D.ustx')
    commands=[('roundtrip',['roundtrip','--project',project,'--out',str(RUN/'native-inputs/D-roundtrip.ustx')]),
        ('phones',['export-phonemes','--project',project,'--out',str(RUN/'native-inputs/D-phones.json')]),
        ('pitch',['export-pitch','--project',project,'--out',str(RUN/'native-inputs/D-pitch.json')]),
        ('render',['render','--project',project,'--out',str(RUN/'native-render/D.wav'),'--mixdown','--timeout','15']),
        ('probe',['export-render-probe','--project',project,'--out',str(RUN/'native-inputs/D'),'--indices','0,1'])]
    for kind,args in commands:
        out=RUN/f'native-inputs/D-{kind}-result.json'
        if out.exists():continue
        print('Native D',kind,flush=True)
        p=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
        log=RUN/f'logs/D-{kind}.log';assert not log.exists();log.write_text(p.stdout+p.stderr,encoding='utf-8')
        assert p.returncode==0,p.stdout[-1000:]+p.stderr[-1000:]
        r=json.loads(p.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(out,r)
    runtime();print('Native D complete; independent gate required.',flush=True)


def execute():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed' and not (RUN/'fresh').exists();runtime()
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    f=load(RUN/'native-inputs/D/phrase_000.json')
    variance,acoustic,vocoder=[ort.InferenceSession(str(p),sess_options=options,providers=['CPUExecutionProvider']) for p in [MODELS/'variance.onnx',MODELS/'acoustic.onnx',f['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),model_adapters=load(RUN/'design/protocol.json')['model_adapters'],seeds=[11,101],max_waveforms=4,ort=ort.__version__,numpy=np.__version__))
    rows=[]
    for ctx in [0,1]:
        f=load(RUN/f'native-inputs/D/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/D/variance_{ctx:03}.json')
        for label in ['D','D_repeat']:
            ac,va=tensors(f['tensors']),tensors(v['tensors']);n=ac['f0'].size;va['probe_noise']=gaussian_frame_noise(11,3,24,n)
            names=[o.name for o in variance.get_outputs()];pred=dict(zip(names,variance.run(names,model_feed(variance,va))));clipping={}
            for ch in CHANNELS:
                lo,hi=(-10,10) if ch=='tension' else (-96,0);raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                clipping[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)));ac[ch]=np.clip(raw,lo,hi).astype(np.float32)
            ac['probe_noise']=gaussian_frame_noise(101,1,128,n);mel=acoustic.run(['mel'],model_feed(acoustic,ac))[0];vm=mel.copy()
            if f['acoustic_mel_base']!=f['vocoder_mel_base']:vm*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
            vf=np.asarray(f['vocoder_f0'],np.float32)[None,:];wave=vocoder.run(None,model_feed(vocoder,dict(mel=vm,f0=vf)))[0].reshape(-1)
            assert np.isfinite(wave).all() and len(wave)==n*512
            path=RUN/f'fresh/context{ctx}/{label}';path.mkdir(parents=True);np.save(path/'raw.npy',wave)
            for name,x in [('inputs',ac),('variance-inputs',va),('predictions',pred),('mel',dict(mel=mel)),('vocoder-f0',dict(f0=vf))]:np.savez_compressed(path/(name+'.npz'),**x)
            rows.append(dict(context=ctx,variant=label,frames=n,samples=len(wave),feature_clipping=clipping,
                wave_start_s=(f['position_ms']-f['head_frames']*float(np.float32(f['frame_ms'])))/1000,raw_peak=float(np.max(np.abs(wave)))))
            print('Fresh',ctx,label,'done',flush=True)
    runtime();save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=4,acoustic_vocoder_waveforms=4,old_A_B_C='sealed reuse; no new inference',measurement_validated=False))


if __name__=='__main__':{'prepare':prepare,'native':native,'execute':execute}[sys.argv[1]]()
