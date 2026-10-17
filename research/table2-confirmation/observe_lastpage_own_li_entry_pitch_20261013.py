"""Bound finite PCM/mel/feature proxies and dual F0 for one finite entry-pitch candidate.

No auditory judgment or parameter selection. Metrics cover all 15 words and
their onsets/releases; no new author audio is synthesized or normalized.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from assemble_lastpage_accepted_baseline_20261011 import ROOT, load, save, ref, sha, check
from agent2utau.resources.config import load_config
from agent2utau.analysis.f0 import extract_f0
from shfc_pcm_checks import interval_indices, level, centered_windows
from observe_stage_2e_paths import f0_compare, stats

RUN=ROOT/'runs/experiments/lastpage-own-li-entry-pitch-20261013'
F=ROOT/'runs/experiments/lastpage-own-control-neutral-20261012'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
CHANNELS=['breathiness','voicing','tension']


def read(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def main():
    assert (RUN/'evaluation/delivery-check.json').exists()
    assert not (RUN/'observations/start.json').exists()
    import torch
    import torchfcpe
    import librosa
    import onnxruntime as ort
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    rm_model=Path(load_config()['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx'
    fc_root=Path(torchfcpe.__file__).parent
    fc_weight=fc_root/'assets/fcpe_c_v001.pt'
    assert fc_weight.is_file() and rm_model.is_file()
    models=[dict(path=str(p),sha256=sha(p)) for p in [fc_weight,rm_model]]
    inputs=[ref(RUN/f'evaluation/PCM-contexts/context{ctx}-{v}.wav') for ctx in [28,29] for v in ['F','J']]
    sources=[ref(Path(__file__)),ref(ROOT/'src/agent2utau/analysis/f0.py'),
        ref(ROOT/'research/table2-confirmation/shfc_pcm_checks.py'),
        ref(ROOT/'research/table2-confirmation/observe_stage_2e_paths.py')]
    save(RUN/'observations/start.json',dict(models=models,inputs=inputs,source=sources,
        F0_calls_planned=2,backend='CPU single thread',packages=dict(torch=torch.__version__,librosa=librosa.__version__,onnxruntime=ort.__version__),
        ground_truth_calibration=False,agent_heard=False))
    options=ort.SessionOptions();options.intra_op_num_threads=options.inter_op_num_threads=1
    options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    session=ort.InferenceSession(str(rm_model),sess_options=options,providers=['CPUExecutionProvider'])
    def rmvpe(path):
        wave,sr=sf.read(path,dtype='float32');assert sr==44100 and wave.ndim==1
        wave=librosa.resample(wave,orig_sr=sr,target_sr=16000)
        result=session.run(None,dict(waveform=np.clip(wave,-1,1)[None,:].astype(np.float32),threshold=np.array(.03,np.float32)))
        f0,uv=[np.asarray(x[0]) for x in result];n=min(len(f0),len(uv))
        return dict(f0_hz=f0[:n].astype(np.float32),voiced=~uv[:n].astype(bool),
            times=(np.arange(n)*.01).astype(np.float32),sr=16000,hop=160,frame_ms=10.,threshold=.03)
    geometry={r['word']:r for r in load(BASE/'native_word_geometry.json')}
    execution=load(RUN/'fresh/execution.json')['rows']
    rows=[];bindings=[];calls=0;reused=0
    old_obs=load(F/'observations/results.json')
    for j,(ctx,first,last) in enumerate([(28,270,278),(29,279,284)]):
        entries=execution if ctx==28 else load(F/'fresh/execution.json')['rows'];entry=next(r for r in entries if r['context']==ctx and r['variant']==('J' if ctx==28 else 'F'));origin=entry['wave_start_s'];n=entry['samples']
        pcm={};raw={};mel={};feat={};det={}
        for variant in ['F','J']:
            folder=RUN/'fresh/context28/J' if variant=='J' and ctx==28 else F/f'fresh/context{ctx}/F'
            path=RUN/f'evaluation/PCM-contexts/context{ctx}-{variant}.wav'
            pcm[variant],sr=sf.read(path,dtype='float64');assert sr==44100 and len(pcm[variant])==n
            raw[variant]=np.load(folder/'raw.npy',allow_pickle=False)
            mel[variant]=read(folder/'mel.npz')['mel'].astype(np.float64)
            feat[variant]=read(folder/'inputs.npz')
            det[variant]={}
            for detector,fn in [('FCPE',extract_f0),('RMVPE',rmvpe)]:
                if variant=='F' or ctx==29:
                    binding=next(b for b in old_obs['detector_bindings'] if b['context']==ctx and b['variant']=='F' and b['detector']==detector)
                    check([binding['input'],binding['output']]);assert ref(path)['sha256']==binding['input']['sha256']
                    record={**read(ROOT/binding['output']['path']),**binding['clock']}
                    det[variant][detector]=record;bindings.append({**binding,'variant':variant,'input':ref(path),'reused_from_sealed_F':True});reused+=1
                    continue
                record=fn(path);det[variant][detector]=record
                p=RUN/f'observations/F0/context{ctx}-{variant}-{detector}.npz'
                p.parent.mkdir(parents=True,exist_ok=True)
                assert not p.exists()
                np.savez_compressed(p,**{k:record[k] for k in ['f0_hz','voiced','times']})
                bindings.append(dict(context=ctx,variant=variant,detector=detector,input=ref(path),output=ref(p),
                    clock={k:record[k] for k in ['sr','hop','frame_ms']},
                    voiced_frames=int((record['voiced']&np.isfinite(record['f0_hz'])&(record['f0_hz']>0)).sum())))
                calls+=1;print('F0',calls,'/2',ctx,variant,detector,flush=True)
        frame=load(F/f'native-inputs/F/phrase_{j:03d}.json')
        times=(frame['position_ms']+(np.arange(feat['F']['f0'].size)-frame['head_frames'])*frame['frame_ms'])/1000
        windows=[dict(context=ctx,word=None,char=None,role='whole_context',interval_s=[origin,origin+n/44100])]
        for word in range(first,last+1):
            g=geometry[word];s,e=g['native_vowel']
            for role,lo,hi in [('full_vowel',s,e),('core15_85',s+.15*(e-s),e-.15*(e-s)),
                ('vowel_first60ms',s,min(s+.060,e)),('vowel_last60ms',max(s,e-.060),e)]:
                windows.append(dict(context=ctx,word=word,char=g['char'],role=role,interval_s=[lo,hi]))
            for phone in g['phones']:
                if phone['end_ms']<=s*1000:
                    windows.append(dict(context=ctx,word=word,char=g['char'],role='preceding_consonant',phoneme=phone['phoneme'],
                        interval_s=[phone['start_ms']/1000,phone['end_ms']/1000]))
        if ctx==28:
            nodes=load(RUN/'design/protocol.json')['gesture']['center_nodes']
            phases=[('li_preparation',nodes[0][0],nodes[1][0]),('li_low_entry',nodes[1][0],nodes[2][0]),
                ('li_rise',nodes[2][0],nodes[3][0]),('li_rejoin',nodes[3][0],nodes[4][0]),
                ('li_retained_body',nodes[4][0],213.4152083333333),('li_retained_release',213.4152083333333,213.53020833333332),
                ('li_descending',213.53020833333332,213.58541666666667)]
            for role,lo,hi in phases:windows.append(dict(context=ctx,word=277,char='里',role=role,interval_s=[lo,hi]))
        for w in windows:
            interval=w['interval_s'];ix=interval_indices(interval,origin,n)
            if w['role']=='whole_context':ix=(0,n)
            item=dict(**w,sample_indices=ix,status='computed_proxy_only' if ix else 'unknown_outside_wave',variants={},J_minus_F={})
            if ix:
                mask=(times>=interval[0])&(times<interval[1]);a,b=[pcm[v][slice(*ix)] for v in ['F','J']]
                for variant in ['F','J']:
                    item['variants'][variant]=dict(level=level(pcm[variant][slice(*ix)]),raw_level=level(raw[variant][slice(*ix)]),
                        short_windows={str(width):centered_windows(pcm[variant],interval,origin,width) for width in [30,50]},
                        final_features={ch:stats(feat[variant][ch].ravel()[mask]) for ch in CHANNELS})
                rmsA,rmsB=level(a)['rms'],level(b)['rms']
                md=(mel['J']-mel['F'])[:,mask,:]
                shape=(mel['J']-mel['J'].mean(axis=2,keepdims=True))[:,mask,:]-(mel['F']-mel['F'].mean(axis=2,keepdims=True))[:,mask,:]
                f0={name:f0_compare(det['F'][name],det['J'][name],interval,origin) for name in ['FCPE','RMVPE']}
                item['J_minus_F']=dict(level_ratio_db=float(20*np.log10(rmsB/rmsA)) if rmsA and rmsB else None,
                    PCM_difference=level(b-a),mel_difference_rms=float(np.sqrt(np.mean(md*md))) if md.size else None,
                    centered_mel_shape_difference_rms=float(np.sqrt(np.mean(shape*shape))) if shape.size else None,
                    F0=f0,solidity_naturalness_break_cause='unknown',level_is_perceived_loudness=False)
            rows.append(item)
    assert calls==2 and reused==6
    for model in models:assert sha(Path(model['path']))==model['sha256']
    check(inputs);check(sources);check(load(RUN/'protected-before.json'))
    save(RUN/'observations/results.json',dict(windows=rows,detector_bindings=bindings,actual_F0_calls=calls,reused_F_F0_array_bindings=reused,
        finite_contexts=2,affected_contexts=1,scope_words=15,word_auditory_labels_added=0,
        actual_F0_truth='unknown: fixed input is not measured pitch equality; detectors not calibrated here',
        window_policy='half-open ceil PCM indices, two raw wave origins; no UV interpolation, <3 joint voiced frames unknown',
        feature_units='model input units, not physiology/HNR/output dB',mel_is_formant_truth=False,
        agent_heard=False,auditory_acceptance='pending',measurement_validated=False))
    summary=[dict(word=r['word'],char=r['char'],rms_delta_db=r['J_minus_F'].get('level_ratio_db'),
        F0={k:dict(valid=v['valid_pair_frames'],p50=v['abs_cents_p50'],maximum=v['max_abs_cents']) for k,v in r['J_minus_F'].get('F0',{}).items()})
        for r in rows if r['role']=='full_vowel']
    print(json.dumps(dict(status='observed_proxies_only',windows=len(rows),words=summary),ensure_ascii=False),flush=True)


if __name__=='__main__':main()


