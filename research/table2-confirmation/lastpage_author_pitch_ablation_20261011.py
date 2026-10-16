"""Explicit user-authorized author-copy research; never modifies production inputs."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, sha, ref, check
from agent2utau.evaluation.controlled_probe import tensors, noise_adapter
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from agent2utau.resources.config import load_config
from shfc_path_backend import model_feed

RUN=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011'
PRIOR=ROOT/'runs/research/lastpage-conditioned-voicing-feedback-20261011'
AUTHOR=ROOT/'runs/research/lastpage-li-kan-author-reference-20261011'
LABELS=['A','P','N','PN']
CHANNELS=['breathiness','voicing','tension']


def runtime_check():
    check(load(RUN/'protected-before.json'))
    for p,h in load(RUN/'native-inputs/runtime.json').items():assert sha(Path(p))==h,p


def prepare():
    assert not RUN.exists()
    seal=load(PRIOR/'completion-manifest.json')
    check(seal['files']+seal['documents']+seal['entries'])
    protected=load(PRIOR/'protected-before.json')+seal['files']+seal['documents']
    RUN.mkdir(parents=True)
    save(RUN/'protected-before.json',protected)
    for n in ENTRIES:
        p=RUN/'before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    source=AUTHOR/'score/baishuo-main-part2-current165c.ustx'
    doc=yaml.safe_load(source.read_text(encoding='utf-8-sig'))
    assert len(doc['voice_parts'])==1 and len(doc['voice_parts'][0]['notes'])==42
    assert all(n['vibrato']['length']==0 for n in doc['voice_parts'][0]['notes'])
    (RUN/'score').mkdir();(RUN/'logs').mkdir()
    scores={}
    for label in LABELS:
        d=copy.deepcopy(doc)
        part=d['voice_parts'][0]
        if label in ['P','PN']:
            c=next(c for c in part['curves'] if c['abbr']=='pitd');c['ys']=[0]*len(c['ys'])
        if label in ['N','PN']:
            for n in part['notes']:
                n['pitch']['snap_first']=False
                for point in n['pitch']['data']:point['y']=0
        p=RUN/f'score/{label}.ustx'
        if label=='A':p.write_bytes(source.read_bytes())
        else:p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')
        scores[label]=ref(p)
    protocol=dict(id='LASTPAGE-AUTHOR-PITCH-ABLATION-01',status='frozen_before_execution',
        user_authorization='这一段你复制白烁的项目，然后逐步更改内容，比如音高线，pitch这些，看下是什么影响的',
        source=ref(source),original=ref(ROOT/'research/baishuo/projects/最后一页-有参by白烁.ustx'),scores=scores,
        phrases=['想把你抱进身体里面','不敢让你看见'],contexts=[0,1],
        variants={'A':'author current165c copy, all authored pitch/control intact',
            'P':'PITD ys=0 on unchanged xs; note.pitch retained',
            'N':'note.pitch point y=0 and snap_first=false; x/shape/PITD retained',
            'PN':'both preceding interventions'},
        comparisons=['P-A','N-A','PN-P','PN-N'],
        fixed=['notes tone/tuning/lyrics/durations/positions','all non-pitch curves/expressions',
            'phonemizer/phone clock','both stage speaker','DYN','track gain/pan','variance11/acoustic101'],
        permitted_dependencies=['native before/final pitch','variance pitch','all three predicted/final features',
            'acoustic f0/mel','vocoder f0/wave'],
        note_pitch_definition='Neutralizes relative offsets and automatic previous-note snapping; native note transitions still exist. Not equivalent to a fixed absolute tone.',
        extent='Keep complete original 42-note main part and its 3 native phrases for identity/context. Neutralizations span that part; seeded research/listening covers only first two phrases. Third native phrase is technical only.',
        budget=dict(score_versions=4,native_cached_contexts=12,seeded_variance_calls=16,
            seeded_acoustic_vocoder_waveforms=16,independent_contexts=2,repeats_per_version_context=2),
        previous_reference=ref(AUTHOR/'delivery/baishuo_current165c_reference_vocal.wav'),
        historical_singer='yousaV1.56 unavailable; use same current165c as previous reference',
        seed_caveat='Previous liked reference used native cached randomness/PCM16 export. New A is fresh fixed11/101 and PCM24, not claimed equal. Confirm new A solidity before interpreting factors.',
        listening='Full two phrases, separately; first check A vs liked reference, then P/N/PN vs new A. Assess solidity, pitch/melody, articulation/break/level. Missing feedback unknown.',
        no_production_adoption=True,author_arrays_for_research_only=True,agent_heard=False,
        measurement_validated=False,general_rule_validated=False,
        stops=['identity/dependency/repeat failure','nonfinite or file clipping','no adaptive extra versions before feedback'])
    save(RUN/'design/protocol.json',protocol)
    save(RUN/'native-inputs/runtime.json',load(ROOT/'runs/experiments/lastpage-conditioned-voicing-20261011/native-inputs/runtime.json'))
    runtime_check()
    print('Frozen author-copy four-version/two-context protocol.',flush=True)


def native():
    runtime_check()
    exe=Path(load_config()['openutau_dir'])/'a2u-shfcprobe-20261008.exe'
    for label in LABELS:
        project=str(RUN/f'score/{label}.ustx')
        cmds=[('roundtrip',['roundtrip','--project',project,'--out',str(RUN/f'native-inputs/{label}-roundtrip.ustx')]),
            ('phones',['export-phonemes','--project',project,'--out',str(RUN/f'native-inputs/{label}-phones.json')]),
            ('pitch',['export-pitch','--project',project,'--out',str(RUN/f'native-inputs/{label}-pitch.json')]),
            ('render',['render','--project',project,'--out',str(RUN/f'native-render/{label}.wav'),'--mixdown','--timeout','15']),
            ('probe',['export-render-probe','--project',project,'--out',str(RUN/f'native-inputs/{label}'),'--indices','0,1'])]
        for kind,args in cmds:
            out=RUN/f'native-inputs/{label}-{kind}-result.json'
            if out.exists():continue
            print('Native',label,kind,flush=True)
            proc=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
            log=RUN/f'logs/{label}-{kind}.log';assert not log.exists()
            log.write_text(proc.stdout+proc.stderr,encoding='utf-8')
            assert proc.returncode==0,proc.stdout[-1000:]+proc.stderr[-1000:]
            r=json.loads(proc.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True),r
            save(out,r)
    runtime_check()
    print('Native complete; require independent checks before fresh models.',flush=True)


def execute():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed'
    assert not (RUN/'fresh').exists()
    runtime_check()
    f=load(RUN/'native-inputs/A/phrase_000.json');v=load(RUN/'native-inputs/A/variance_000.json')
    folder=RUN/'fresh/models';folder.mkdir(parents=True)
    adapters=[noise_adapter(v['variance_model'],folder/'variance.onnx',3,24),noise_adapter(f['acoustic_model'],folder/'acoustic.onnx',1,128)]
    import onnxruntime as ort
    opts=ort.SessionOptions();opts.intra_op_num_threads=opts.inter_op_num_threads=1;opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    variance,acoustic,vocoder=[ort.InferenceSession(str(p),sess_options=opts,providers=['CPUExecutionProvider'])
        for p in [folder/'variance.onnx',folder/'acoustic.onnx',f['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),adapters=adapters,seeds=[11,101],max_waveforms=16,ort=ort.__version__,numpy=np.__version__))
    rows=[]
    for ctx in [0,1]:
        for label in LABELS:
            f=load(RUN/f'native-inputs/{label}/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/{label}/variance_{ctx:03}.json')
            for suffix in ['', '_repeat']:
                inp,vin=tensors(f['tensors']),tensors(v['tensors']);frames=inp['f0'].size
                vin['probe_noise']=gaussian_frame_noise(11,3,24,frames)
                names=[o.name for o in variance.get_outputs()];pred=dict(zip(names,variance.run(names,model_feed(variance,vin))))
                clipped={}
                for ch in CHANNELS:
                    limits=(-10,10) if ch=='tension' else (-96,0)
                    raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                    clipped[ch]=int(np.count_nonzero((raw<limits[0])|(raw>limits[1])))
                    inp[ch]=np.clip(raw,*limits).astype(np.float32)
                inp['probe_noise']=gaussian_frame_noise(101,1,128,frames)
                mel=acoustic.run(['mel'],model_feed(acoustic,inp))[0];vm=mel.copy()
                if f['acoustic_mel_base']!=f['vocoder_mel_base']:vm*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
                vf=np.asarray(f['vocoder_f0'],np.float32)[None,:]
                wave=vocoder.run(None,model_feed(vocoder,dict(mel=vm,f0=vf)))[0].reshape(-1)
                assert np.isfinite(wave).all() and len(wave)==frames*512
                d=RUN/f'fresh/context{ctx}/{label}{suffix}';d.mkdir(parents=True)
                np.save(d/'raw.npy',wave)
                for name,arrays in [('inputs',inp),('variance-inputs',vin),('predictions',pred),('mel',{'mel':mel}),('vocoder-f0',{'f0':vf})]:
                    np.savez_compressed(d/(name+'.npz'),**arrays)
                # Native DiffSinger uses float32 frame period for its head-origin clock.
                origin=(f['position_ms']-f['head_frames']*float(np.float32(f['frame_ms'])))/1000
                rows.append(dict(context=ctx,variant=label+suffix,frames=frames,samples=len(wave),wave_start_s=origin,
                    feature_clipping=clipped,raw_peak=float(np.max(np.abs(wave)))))
                print('Fresh',ctx,label+suffix,'done',flush=True)
    runtime_check()
    save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=16,acoustic_vocoder_waveforms=16,measurement_validated=False))


if __name__=='__main__':{'prepare':prepare,'native':native,'execute':execute}[sys.argv[1]]()
