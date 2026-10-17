"""Execute one explicitly prepared VOIC design on two complete own contexts.

New run only. Historical scripts/runs, Skill, songs and author originals are read-only.
"""
import copy
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import soundfile as sf
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT, ENTRIES, load, save, sha, ref, check
from agent2utau.evaluation.controlled_probe import tensors, noise_adapter
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from agent2utau.resources.config import load_config
from shfc_path_backend import model_feed

RUN = ROOT / 'runs/experiments/lastpage-conditioned-voicing-20261011'
PRIOR = ROOT / 'runs/research/lastpage-voice-baseline-feedback-20261011'
VOICE = ROOT / 'runs/experiments/lastpage-voice-baseline-20261011'
BASE = ROOT / 'runs/lastpage_loudness_skill_v02_20261007'
CURRENT = ROOT / 'runs/production/lastpage-accepted-baseline-20261011'
CHANNELS = ['breathiness', 'voicing', 'tension']
INDICES = [28, 29]


def prepare():
    assert not RUN.exists(), 'New run only.'
    sealed = load(PRIOR / 'completion-manifest.json')
    check(sealed['files'] + sealed['documents'] + sealed['entries'])
    protected = load(PRIOR / 'protected-before.json') + sealed['files'] + sealed['documents']
    check(protected)
    plan = load(PRIOR / 'design/next-voicing-plan.json')
    check([plan['baseline']])
    RUN.mkdir(parents=True)
    for name in ENTRIES:
        p = RUN / 'before' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / name).read_bytes())
    save(RUN / 'protected-before.json', protected)
    original = yaml.safe_load((ROOT / plan['baseline']['path']).read_text(encoding='utf-8-sig'))
    candidate = copy.deepcopy(original)
    # Retain the prepared doses. Configure the minimum explicit project range
    # required by the existing190 + new25 overlap; native load must preserve it.
    assert original['expressions']['voic']['max']==200
    candidate['expressions']['voic']['max']=215
    assert original['resolution'] == 480 and original['tempos'] == [dict(position=0, bpm=120)]
    part = candidate['voice_parts'][28]
    curve = next(c for c in part['curves'] if c['abbr']=='voic')
    assert all(b-a==5 for a,b in zip(curve['xs'],curve['xs'][1:]))
    old_y = curve['ys'].copy()
    trace = []
    for action in plan['actions']:
        if not action['additive_UI']: continue
        s, e = action['support_s']; attack, release = action['attack_s'], action['release_s']
        amplitude = action['additive_UI']
        # Retain the actual original 5tick grid and integer baseline values.
        # First/last grid nodes INSIDE the vowel are zero guards, preventing
        # interpolated offsets from leaking into adjacent consonants/AP/SP.
        inside = [i for i,x in enumerate(curve['xs']) if s <= (part['position']+x)/960 <= e]
        assert len(inside)>=4
        delta = []
        for i in inside:
            t = (part['position']+curve['xs'][i])/960
            u = min(1.0, max(0.0,(t-s)/attack), max(0.0,(e-t)/release))
            q = 0 if i in (inside[0],inside[-1]) else round(amplitude*u)
            delta.append(q)
            curve['ys'][i] += q
        assert max(delta)==amplitude and delta[0]==delta[-1]==0
        trace.append(dict(word=action['word'],char=action['char'],support_s=[s,e],
            amplitude_UI=amplitude,attack_s=attack,release_s=release,
            zero_guard_ticks=[curve['xs'][inside[0]],curve['xs'][inside[-1]]],
            changed_grid_nodes=sum(q!=0 for q in delta),integer_grid=5))
    desc = candidate['expressions']['voic']
    assert all(desc['min']<=v<=desc['max'] for v in curve['ys']), 'No saturation allowed.'
    assert curve['xs']==next(c for c in original['voice_parts'][28]['curves'] if c['abbr']=='voic')['xs']
    for k in original:
        if k not in ['voice_parts','expressions']: assert original[k]==candidate[k]
    for k,v in original['expressions'].items():
        if k!='voic':assert v==candidate['expressions'][k]
        else:assert {q:w for q,w in v.items() if q!='max'}=={q:w for q,w in candidate['expressions'][k].items() if q!='max'}
    for i,(a,b) in enumerate(zip(original['voice_parts'],candidate['voice_parts'])):
        if i!=28: assert a==b
        else:
            assert {k:v for k,v in a.items() if k!='curves'}=={k:v for k,v in b.items() if k!='curves'}
            assert [c for c in a['curves'] if c['abbr']!='voic']==[c for c in b['curves'] if c['abbr']!='voic']
    (RUN/'score').mkdir()
    full = RUN/'score/lastpage_conditioned_voicing_B.ustx'
    full.write_text(yaml.safe_dump(candidate,allow_unicode=True,sort_keys=False),encoding='utf-8')
    for label, doc in [('A',original),('B',candidate)]:
        d = copy.deepcopy(doc)
        d['voice_parts'] = [d['voice_parts'][i] for i in INDICES]
        d['wave_parts'] = []; d['tracks'] = [d['tracks'][0]]
        d['tracks'][0].update(volume=0,pan=-100,mute=False,solo=False)
        (RUN/f'score/native_{label}.ustx').write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False),encoding='utf-8')
    frozen = copy.deepcopy(plan)
    frozen.update(state='frozen_before_native_execution',authorization='user 下一步 after prepared finite plan',
        previous_plan=ref(PRIOR/'design/next-voicing-plan.json'),candidate=ref(full),
        grid_compilation='add rounded explicit linear finite envelope on unchanged original 5tick grid; zero guards inside vowel',
        trace=trace,compiled_VOIC_range=[min(curve['ys']),max(curve['ys'])],
        native_reference_contexts=4,actual_new_waveforms_at_freeze=0)
    frozen.update(original_declared_VOIC_range=[0,200],candidate_declared_VOIC_range=[0,215],
        range_change_reason='word272 original190 plus prepared25 needs215; explicit minimum declaration, no value clipping/dose change',
        range_validation_required='native roundtrip expression max215 and curve exact, independent sampled delta bit-exact',
        rejected_prepare=ref(ROOT/'runs/research/lastpage-conditioned-voicing-rejected-compile-20261011/failure.txt'))
    save(RUN/'design/protocol.json',frozen)
    save(RUN/'design/compile-check.json',dict(original_grid_exact=True,other_curves_notes_and_33_parts_exact=True,
        declared_range=[desc['min'],desc['max']],compiled_range=frozen['compiled_VOIC_range'],
        no_clipping=True,baseline_preserved_within_overlay=True,trace=trace))
    save(RUN/'native-inputs/runtime.json',load(VOICE/'native-inputs/runtime.json'))
    runtime_check()
    (RUN/'logs').mkdir()
    print(json.dumps(dict(state='compiled',VOIC_range=frozen['compiled_VOIC_range'],trace=trace),ensure_ascii=False),flush=True)


def runtime_check():
    check(load(RUN/'protected-before.json'))
    for p,digest in load(RUN/'native-inputs/runtime.json').items(): assert sha(Path(p))==digest,p


def native():
    runtime_check()
    exe = Path(load_config()['openutau_dir'])/'a2u-shfcprobe-20261008.exe'
    for label in ['A','B']:
        project = str(RUN/f'score/native_{label}.ustx')
        commands = [('roundtrip',['roundtrip','--project',project,'--out',str(RUN/f'native-inputs/{label}-roundtrip.ustx')]),
            ('phones',['export-phonemes','--project',project,'--out',str(RUN/f'native-inputs/{label}-phones.json')]),
            ('render',['render','--project',project,'--out',str(RUN/f'native-render/{label}.wav'),'--mixdown','--timeout','15']),
            ('probe',['export-render-probe','--project',project,'--out',str(RUN/f'native-inputs/{label}'),'--indices','0,1'])]
        for kind,args in commands:
            result = RUN/f'native-inputs/{label}-{kind}-result.json'
            if result.exists(): continue  # explicit same-run resume, no overwrite
            print('Native',label,kind,flush=True)
            p = subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf-8',errors='replace',timeout=1200)
            log = RUN/f'logs/{label}-{kind}.log'
            assert not log.exists()
            log.write_text(p.stdout+p.stderr,encoding='utf-8')
            assert p.returncode==0,p.stdout[-1500:]+p.stderr[-1500:]
            response = json.loads(p.stdout.strip().splitlines()[-1])
            assert not response.get('errors') and response.get('ok',True),response
            save(result,response)
            if kind=='roundtrip':
                loaded=yaml.safe_load((RUN/f'native-inputs/{label}-roundtrip.ustx').read_text(encoding='utf-8-sig'))
                written=yaml.safe_load(Path(project).read_text(encoding='utf-8-sig'))
                assert loaded['expressions']['voic']==written['expressions']['voic']
                assert all(next(c for c in p['curves'] if c['abbr']=='voic')==next(c for c in q['curves'] if c['abbr']=='voic')
                    for p,q in zip(loaded['voice_parts'],written['voice_parts']))
    runtime_check()
    print('Native complete; independent isolation gate required before fresh execution.',flush=True)


def execute():
    check_record = load(RUN/'evaluation/native-independent-check.json')
    assert check_record['status']=='passed'
    assert not (RUN/'fresh').exists()
    runtime_check()
    records = []
    for j in range(2):
        records.append([load(RUN/f'native-inputs/{s}/{k}_{j:03d}.json') for s,k in [('A','phrase'),('A','variance'),('B','phrase'),('B','variance')]])
    (RUN/'fresh/models').mkdir(parents=True)
    model_dir = RUN/'fresh/models'
    adapters = [noise_adapter(records[0][1]['variance_model'],model_dir/'variance.onnx',3,24),
        noise_adapter(records[0][0]['acoustic_model'],model_dir/'acoustic.onnx',1,128)]
    import onnxruntime as ort
    options = ort.SessionOptions(); options.intra_op_num_threads=options.inter_op_num_threads=1
    options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    variance,acoustic,vocoder = [ort.InferenceSession(str(p),sess_options=options,providers=['CPUExecutionProvider'])
        for p in [model_dir/'variance.onnx',model_dir/'acoustic.onnx',records[0][0]['vocoder_model']]]
    save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),native_check=ref(RUN/'evaluation/native-independent-check.json'),
        adapters=adapters,ort_version=ort.__version__,numpy_version=np.__version__,seeds=[11,101],max_waveforms=8))
    rows = []
    for ctx,record in zip(INDICES,records):
        variants = {}
        for label in ['A','A_repeat','B','B_repeat']:
            f,v = record[:2] if label.startswith('A') else record[2:]
            inp,vin = tensors(f['tensors']),tensors(v['tensors']); frames=inp['f0'].size
            vin['probe_noise']=gaussian_frame_noise(11,3,24,frames)
            names=[o.name for o in variance.get_outputs()]
            pred=dict(zip(names,variance.run(names,model_feed(variance,vin))))
            clipped = {}
            for ch in CHANNELS:
                lo,hi=(-10,10) if ch=='tension' else (-96,0)
                raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                clipped[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)))
                inp[ch]=np.clip(raw,lo,hi).astype(np.float32)
            inp['probe_noise']=gaussian_frame_noise(101,1,128,frames)
            mel=acoustic.run(['mel'],model_feed(acoustic,inp))[0]
            voc_mel=mel.copy()
            if f['acoustic_mel_base']!=f['vocoder_mel_base']:
                voc_mel*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
            vf=np.asarray(f['vocoder_f0'],np.float32)[None,:]
            wave=vocoder.run(None,model_feed(vocoder,dict(mel=voc_mel,f0=vf)))[0].reshape(-1)
            assert np.isfinite(wave).all()
            folder=RUN/f'fresh/context{ctx}/{label}';folder.mkdir(parents=True)
            np.save(folder/'raw.npy',wave)
            np.savez_compressed(folder/'inputs.npz',**inp)
            np.savez_compressed(folder/'predictions.npz',**pred)
            np.savez_compressed(folder/'variance-inputs.npz',**vin)
            np.savez_compressed(folder/'mel.npz',mel=mel)
            np.savez_compressed(folder/'vocoder-f0.npz',f0=vf)
            variants[label]=dict(wave=wave,inp=inp,pred=pred,clipped=clipped)
            print('Fresh',ctx,label,'done',flush=True)
        a,b=variants['A'],variants['B']
        assert np.array_equal(a['wave'],np.load(BASE/f'synthesis/phrase_{ctx:03d}.npy',allow_pickle=False))
        with np.load(BASE/f'synthesis/state_{ctx:03d}.npz',allow_pickle=False) as old:
            for ch in CHANNELS:
                assert np.array_equal(a['pred'][ch+'_pred'],old[ch])
                assert np.array_equal(a['inp'][ch],old['final_'+ch])
        for label in ['A','B']:
            x,y=variants[label],variants[label+'_repeat']
            assert np.array_equal(x['wave'],y['wave'])
            assert all(np.array_equal(x['inp'][k],y['inp'][k]) for k in x['inp'])
            assert all(np.array_equal(x['pred'][k],y['pred'][k]) for k in x['pred'])
        assert all(np.array_equal(a['pred'][k],b['pred'][k]) for k in a['pred'])
        changed=[k for k in a['inp'] if not np.array_equal(a['inp'][k],b['inp'][k])]
        assert changed==(['voicing'] if ctx==28 else [])
        assert all(q==0 for x in variants.values() for q in x['clipped'].values())
        if ctx==29: assert np.array_equal(a['wave'],b['wave'])
        rows.append(dict(context=ctx,frames=frames,samples=len(a['wave']),changed_inputs=changed,
            predictions_exact=True,original_A_and_repeats_exact=True,feature_clipping=0,
            wave_start_s=load(BASE/f'synthesis/phrase_{ctx:03d}.json')['wave_start_s']))
    runtime_check()
    save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=8,acoustic_vocoder_waveforms=8,
        candidates=1,second_context_A_B_PCM_exact=True,measurement_validated=False))


def package():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed'
    assert not (RUN/'delivery').exists()
    n=load(CURRENT/'evaluation/assembly-check.json')['samples'];sr=44100
    baseline=np.zeros(n,np.float64);candidate=np.zeros(n,np.float64);reverse=np.zeros(n,np.float64)
    parts=load(CURRENT/'design/phrase-ledger.json'); contributions=[]; allowed=np.zeros(n,bool)
    for p in parts:
        ctx=p['context'];old=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4');new=old
        if ctx in INDICES:
            gain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ctx:03d}.f32',dtype='<f4')
            a=np.load(RUN/f'fresh/context{ctx}/A/raw.npy',allow_pickle=False).astype('<f4')
            b=np.load(RUN/f'fresh/context{ctx}/B/raw.npy',allow_pickle=False).astype('<f4')
            assert np.array_equal(a*gain,old)
            new=b*gain
            (RUN/'dynamics').mkdir(exist_ok=True)
            dyn_path=RUN/f'dynamics/context{ctx}-B.f32'
            if dyn_path.exists():assert np.array_equal(new,np.fromfile(dyn_path,dtype='<f4'))
            else:new.tofile(dyn_path)
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(n,start+len(new))
        baseline[lo:hi]+=old[lo-start:hi-start];candidate[lo:hi]+=new[lo-start:hi-start]
        contributions.append((lo,hi,new[lo-start:hi-start]))
        if ctx==28: allowed[lo:hi]=True
    for lo,hi,x in reversed(contributions):reverse[lo:hi]+=x
    assert np.array_equal(candidate,reverse)
    old_pcm,rate=sf.read(CURRENT/'delivery/lastpage_accepted_C_baseline_vocal.wav',dtype='int32')
    assert rate==sr
    d=RUN/'delivery';d.mkdir()
    full=d/'lastpage_conditioned_voicing_B_vocal.wav'
    peak=float(np.max(np.abs(candidate*1.5)));assert peak<1 and np.isfinite(candidate).all()
    sf.write(full,candidate*1.5,sr,subtype='PCM_24')
    encoded,rate=sf.read(full,dtype='int32');assert rate==sr
    assert np.array_equal(old_pcm[~allowed],encoded[~allowed])
    # Validate baseline assembly through identical PCM24 quantization.
    from io import BytesIO
    temp=BytesIO();sf.write(temp,baseline*1.5,sr,subtype='PCM_24',format='WAV');temp.seek(0)
    decoded,_=sf.read(temp,dtype='int32');assert np.array_equal(decoded,old_pcm)
    p=parts[22];lo=round(p['wave_start_s']*sr);hi=lo+p['samples']
    assert np.array_equal(old_pcm[lo:hi],encoded[lo:hi])
    second=load(RUN/'native-inputs/A/phrase_001.json')
    second_start=math.ceil(second['phones'][0]['positionMs']/1000*sr)
    p=parts[29];lo=round(p['wave_start_s']*sr);hi=lo+p['samples']
    assert np.array_equal(old_pcm[second_start:hi],encoded[second_start:hi])
    shared=np.flatnonzero(old_pcm[lo:hi]!=encoded[lo:hi])
    assert len(shared) and lo+shared[-1]<second_start
    overlap=dict(context29_isolated_wave_exact=True,context29_from_first_real_phone_PCM_exact=True,
        shared_head_padding_changed_samples=len(shared),
        changed_shared_padding_support_s=[(lo+int(shared[0]))/sr,(lo+int(shared[-1]))/sr],
        first_real_phone_s=second['phones'][0]['positionMs']/1000,
        reason='previous context28 tail overlaps context29 head padding; no independent context29 input/wave change',
        waveform_clipping_crossfade_or_retiming=False)
    save(RUN/'evaluation/overlap-scope-clarification.json',overlap)
    lo,hi=[round(t*sr) for t in [209.4,218.0]]
    sf.write(d/'B_same_lyrics_vocal.wav',encoded[lo:hi],sr,subtype='PCM_24')
    reread,_=sf.read(d/'B_same_lyrics_vocal.wav',dtype='int32');assert np.array_equal(reread,encoded[lo:hi])
    shutil.copyfile(RUN/'score/lastpage_conditioned_voicing_B.ustx',d/'lastpage_conditioned_voicing_B.ustx')
    (RUN/'evaluation/PCM-contexts').mkdir()
    for j,ctx in enumerate(INDICES):
        gain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ctx:03d}.f32',dtype='<f4')
        for label in ['A','B']:
            raw=np.load(RUN/f'fresh/context{ctx}/{label}/raw.npy',allow_pickle=False).astype('<f4')
            sf.write(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',(raw*gain).astype(np.float64)*1.5,sr,subtype='PCM_24')
    reference=ROOT/'runs/research/lastpage-li-kan-author-reference-20261011/delivery'
    outputs=dict(candidate_preview=ref(d/'B_same_lyrics_vocal.wav'),candidate_full=ref(full),
        candidate_project=ref(d/'lastpage_conditioned_voicing_B.ustx'),
        original_preview=ref(reference/'agent_acceptedC_same_lyrics_vocal.wav'),
        author_reference=ref(reference/'baishuo_current165c_reference_vocal.wav'))
    save(RUN/'evaluation/delivery-check.json',dict(outputs=outputs,peak=peak,fixed_gain=1.5,subtype='PCM_24',
        rate=sr,samples=n,duration_s=n/sr,accepted_bao_C_PCM_exact=True,second_context=overlap,
        outside_context28_PCM_exact=True,baseline_and_reverse_assembly_exact=True,preview_exact=True,
        native_DYN_preserved=True,no_normalization_compression_or_BGM=True,agent_heard=False))
    runtime_check()
    print(json.dumps(dict(state='packaged_pending_observations',peak=peak,preview=outputs['candidate_preview']),ensure_ascii=False),flush=True)


if __name__=='__main__':
    {'prepare':prepare,'native':native,'execute':execute,'package':package}[sys.argv[1]]()
