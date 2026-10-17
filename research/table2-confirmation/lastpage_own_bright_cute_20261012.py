"""One frozen named speaker candidate under the own-song conditions."""
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

PRIOR=ROOT/'runs/research/lastpage-author-interaction-feedback-20261012'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
CURRENT=ROOT/'runs/production/lastpage-accepted-baseline-20261011'
MODELS=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011/fresh/models'
RUN=ROOT/'runs/experiments/lastpage-own-bright-cute-20261012'
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
    for name in ENTRIES:
        p=RUN/'before'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    plan=load(PRIOR/'design/next-own-voice-protocol.json');check([plan['baseline'],plan['baseline_preview'],plan['author_focal_speaker_evidence']])
    assert plan['contexts']==[28,29] and plan['budget']['new_seeded_waveforms']==8 and plan['target_cl01_cl05']==[40,60,0,0,0]
    a=yaml.safe_load((ROOT/plan['baseline']['path']).read_text(encoding='utf-8-sig'));e=copy.deepcopy(a)
    for ctx in plan['contexts']:
        part=e['voice_parts'][ctx];grid=next(c for c in part['curves'] if c['abbr']=='cl03')['xs'].copy()
        for k,v in zip(['cl01','cl02','cl03','cl04','cl05'],plan['target_cl01_cl05']):
            assert a['expressions'][k]['min']<=v<=a['expressions'][k]['max']
            curve=next((c for c in part['curves'] if c['abbr']==k),None)
            if curve is None:curve=dict(abbr=k,xs=grid.copy(),ys=[]);part['curves'].append(curve)
            curve['xs']=grid.copy();curve['ys']=[v]*len(grid)
    full=RUN/'score/lastpage_own_bright_cute_E.ustx';full.write_text(yaml.safe_dump(e,allow_unicode=True,sort_keys=False),encoding='utf-8')
    for label,doc in [('A',a),('E',e)]:
        d=copy.deepcopy(doc);d['voice_parts']=[d['voice_parts'][ctx] for ctx in [28,29]];d['wave_parts']=[];d['tracks']=[d['tracks'][0]]
        d['tracks'][0].update(volume=0,pan=-100,mute=False,solo=False)
        (RUN/f'score/native_{label}.ustx').write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')
    plan.update(status='frozen_before_execution',execution_authorization='2026-10-12 user 下一步',original_frozen_protocol=ref(PRIOR/'design/next-own-voice-protocol.json'),
        candidate=ref(full),native_scores={l:ref(RUN/f'score/native_{l}.ustx') for l in ['A','E']},
        baseline_preview_field_clarification='in original frozen design this points to full accepted-C carrier; actual comparison preview209.4–218.0 is made explicitly at packaging',
        model_adapters=[ref(MODELS/'variance.onnx'),ref(MODELS/'acoustic.onnx')],new_execution_counts='reported separately after execution; original0 fields describe preparation')
    save(RUN/'design/protocol.json',plan)
    runtime_source=ROOT/'runs/experiments/lastpage-author-interaction-20261012/native-inputs/runtime.json'
    save(RUN/'native-inputs/runtime.json',load(runtime_source))
    ou=Path(load_config()['openutau_dir']);singer=ou/'Singers/YousaV1.65c'
    order=['Yousa_Bright','Yousa_Cute','Yousa_Normal','Yousa_Whisper','Yousa_Classic'];mapping=[]
    for p in [singer/'dsconfig.yaml',singer/'dsvariance/dsconfig.yaml']:
        cfg=yaml.safe_load(p.read_text(encoding='utf-8-sig'));assert cfg['speakers']==order
        mapping.append(dict(path=str(p),sha256=sha(p),speakers=cfg['speakers']))
    save(RUN/'native-inputs/speaker-name-mapping.json',dict(current_name_order=mapping,actual_tensor_gate_required=True,
        own_generic_cl_descriptor_names_not_used_as_semantic_truth=True))
    runtime();print('One frozen own E prepared; 34-part copy changed only two speaker mixtures.',flush=True)


def native():
    runtime();exe=Path(load_config()['openutau_dir'])/'a2u-shfcprobe-20261008.exe'
    for label in ['A','E']:
        p=str(RUN/f'score/native_{label}.ustx')
        commands=[('roundtrip',['roundtrip','--project',p,'--out',str(RUN/f'native-inputs/{label}-roundtrip.ustx')]),
            ('phones',['export-phonemes','--project',p,'--out',str(RUN/f'native-inputs/{label}-phones.json')]),
            ('pitch',['export-pitch','--project',p,'--out',str(RUN/f'native-inputs/{label}-pitch.json')]),
            ('render',['render','--project',p,'--out',str(RUN/f'native-render/{label}.wav'),'--mixdown','--timeout','15']),
            ('probe',['export-render-probe','--project',p,'--out',str(RUN/f'native-inputs/{label}'),'--indices','0,1'])]
        for kind,args in commands:
            result=RUN/f'native-inputs/{label}-{kind}-result.json'
            if result.exists():continue
            print('Native',label,kind,flush=True)
            proc=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
            log=RUN/f'logs/{label}-{kind}.log';assert not log.exists();log.write_text(proc.stdout+proc.stderr,encoding='utf-8')
            assert proc.returncode==0,proc.stdout[-1000:]+proc.stderr[-1000:]
            r=json.loads(proc.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(result,r)
    runtime();print('Native own A/E ready; independent identity/speaker gate required.',flush=True)


def execute():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed' and not (RUN/'fresh').exists();runtime()
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    f=load(RUN/'native-inputs/A/phrase_000.json')
    variance,acoustic,vocoder=[ort.InferenceSession(str(p),sess_options=options,providers=['CPUExecutionProvider']) for p in [MODELS/'variance.onnx',MODELS/'acoustic.onnx',f['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),model_adapters=load(RUN/'design/protocol.json')['model_adapters'],seeds=[11,101],max_waveforms=8,ort=ort.__version__,numpy=np.__version__))
    rows=[]
    for j,ctx in enumerate([28,29]):
        for label in ['A','E']:
            f=load(RUN/f'native-inputs/{label}/phrase_{j:03}.json');v=load(RUN/f'native-inputs/{label}/variance_{j:03}.json')
            for suffix in ['', '_repeat']:
                ac,va=tensors(f['tensors']),tensors(v['tensors']);n=ac['f0'].size;va['probe_noise']=gaussian_frame_noise(11,3,24,n)
                names=[o.name for o in variance.get_outputs()];pred=dict(zip(names,variance.run(names,model_feed(variance,va))));clipping={}
                for ch in CHANNELS:
                    lo,hi=(-10,10) if ch=='tension' else (-96,0);raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                    clipping[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)));ac[ch]=np.clip(raw,lo,hi).astype(np.float32)
                ac['probe_noise']=gaussian_frame_noise(101,1,128,n);mel=acoustic.run(['mel'],model_feed(acoustic,ac))[0];vm=mel.copy()
                if f['acoustic_mel_base']!=f['vocoder_mel_base']:vm*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
                vf=np.asarray(f['vocoder_f0'],np.float32)[None,:];wave=vocoder.run(None,model_feed(vocoder,dict(mel=vm,f0=vf)))[0].reshape(-1)
                assert np.isfinite(wave).all() and len(wave)==n*512
                d=RUN/f'fresh/context{ctx}/{label}{suffix}';d.mkdir(parents=True);np.save(d/'raw.npy',wave)
                for name,x in [('inputs',ac),('variance-inputs',va),('predictions',pred),('mel',dict(mel=mel)),('vocoder-f0',dict(f0=vf))]:np.savez_compressed(d/(name+'.npz'),**x)
                rows.append(dict(context=ctx,variant=label+suffix,frames=n,samples=len(wave),feature_clipping=clipping,
                    wave_start_s=load(BASE/f'synthesis/phrase_{ctx:03}.json')['wave_start_s'],raw_peak=float(np.max(np.abs(wave)))))
                print('Fresh',ctx,label+suffix,'done',flush=True)
    runtime();save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=8,acoustic_vocoder_waveforms=8,measurement_validated=False))


if __name__=='__main__':{'prepare':prepare,'native':native,'execute':execute}[sys.argv[1]]()
