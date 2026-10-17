"""Finite PCM/mel/input proxies and explicitly bound fresh dual-F0 observations."""
import math
from pathlib import Path
import numpy as np
import soundfile as sf
from freeze_stage_2d import ROOT,HERE,load,sha
from prepare_stage_2e_execution import save
from check_stage_2e_current_native import records
from check_stage_2e_raw import read_npz
from shfc_path_runner import load_sealed_protocol
from shfc_pcm_checks import interval_indices,level,centered_windows

def stats(x):
    x=np.asarray(x,np.float64)
    if not x.size:return dict(n=0,min=None,median=None,max=None)
    return dict(n=x.size,min=float(x.min()),median=float(np.median(x)),max=float(x.max()))

def f0_compare(a,b,interval,origin):
    if not np.array_equal(a['times'],b['times']):raise ValueError('Detector clocks differ across variants')
    clock=origin+a['times'].astype(np.float64);win=(clock>=interval[0])&(clock<interval[1])
    masks=[f['voiced']&np.isfinite(f['f0_hz'])&(f['f0_hz']>0) for f in [a,b]]
    m=win&masks[0]&masks[1];n=int(m.sum());total=int(win.sum())
    out=dict(window_frames=total,valid_pair_frames=n,valid_pair_fraction=n/total if total else None,
        voiced_A_frames=int((win&masks[0]).sum()),voiced_variant_frames=int((win&masks[1]).sum()),
        status='limited_detector_observation' if n>=3 else 'unknown_insufficient_coverage',true_F0_fixed='unknown')
    if n:
        cents=1200*np.log2(b['f0_hz'][m].astype(np.float64)/a['f0_hz'][m])
        out.update(cents=stats(cents),abs_cents_p50=float(np.median(np.abs(cents))),max_abs_cents=float(np.max(np.abs(cents))))
    else:out.update(cents=stats([]),abs_cents_p50=None,max_abs_cents=None)
    return out

def main():
    import torch
    import torchfcpe
    import librosa
    import onnxruntime as ort
    from agent2utau.analysis.f0 import extract_f0
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=ROOT/load(HERE/'stage_2e_execution_baseline_binding.json')['run'];p=load_sealed_protocol()
    packaging=load(run/'pcm-packaging.json'); prep=load(run/'preparation.json')
    assert not (run/'observations-start.json').exists()
    rm_model=Path(prep['install_root'])/'Dependencies/rmvpe/rmvpe.onnx'
    fc_root=Path(torchfcpe.__file__).parent
    fc_weight=fc_root/'assets/fcpe_c_v001.pt'; assert fc_weight.is_file() and rm_model.is_file()
    sources=[HERE/'observe_stage_2e_paths.py',HERE/'shfc_pcm_checks.py',ROOT/'src/agent2utau/analysis/f0.py',ROOT/'src/agent2utau/analysis/rmvpe.py',fc_root/'models_infer.py',fc_root/'tools.py']
    weight_refs=[dict(path=str(x),sha256=sha(x)) for x in [fc_weight,rm_model]]
    save(run/'observations-start.json',dict(models=weight_refs,
        implementation=[dict(path=str(x),sha256=sha(x)) for x in sources],
        packages=dict(torch=torch.__version__,librosa=librosa.__version__,onnxruntime=ort.__version__),
        inputs=[x for x in packaging['files'] if '/delivery/full/vocal/' in x['path']],
        F0_inferences_planned=16,ground_truth_validation=False))
    opts=ort.SessionOptions();opts.intra_op_num_threads=opts.inter_op_num_threads=1
    opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    rm=ort.InferenceSession(str(rm_model),sess_options=opts,providers=['CPUExecutionProvider'])
    def rmvpe(path):
        wave,sr=sf.read(path,dtype='float32'); assert wave.ndim==1 and sr==44100
        wave=librosa.resample(wave,orig_sr=sr,target_sr=16000)
        outputs=rm.run(None,dict(waveform=np.clip(wave,-1,1)[None,:].astype(np.float32),threshold=np.array(.03,np.float32)))
        f0,uv=[np.asarray(x[0]) for x in outputs];n=min(len(f0),len(uv))
        return dict(f0_hz=f0[:n].astype(np.float32),voiced=~uv[:n].astype(bool),times=(np.arange(n)*160/16000).astype(np.float32),
            sr=16000,hop=160,frame_ms=10.,threshold=.03,backend='rmvpe-onnx-CPU-single-thread')
    obs=[];f0bindings=[];calls=0
    for case,packed in zip(p['cases'],packaging['conditions']):
        cid=case['condition']['id'];origin=packed['origin_s'];a,_=records(run,case,'A')
        ix=next(r for r in load(run/'native-current-check.json')['conditions'] if r['condition_id']==cid)['identity']['target_phone_indices']
        phones=a['phones'];c,v=[phones[i] for i in ix]
        windows=[dict(id=f'phone-{i:02}',role='full_phone',phoneme=q['phoneme'],interval_s=[q['positionMs']/1000,q['endMs']/1000]) for i,q in enumerate(phones)]
        vs,ve=v['positionMs']/1000,v['endMs']/1000
        windows += [dict(id='vowel-core20-80',role='target_core',interval_s=[vs+(ve-vs)*.2,vs+(ve-vs)*.8]),
            dict(id='vowel-first60ms',role='target_onset',interval_s=[vs,min(vs+.06,ve)]),
            dict(id='vowel-last60ms',role='target_tail',interval_s=[max(vs,ve-.06),ve]),
            dict(id='before-vowel60ms',role='cross_phone_window',interval_s=[vs-.06,vs]),
            dict(id='after-vowel60ms',role='cross_phone_window',interval_s=[ve,ve+.06]),
            dict(id='whole-phrase',role='full_model_context',interval_s=[origin,origin+packed['samples']/44100])]
        pcm={};mels={};feeds={};detectors={}
        for entry in packed['versions']:
            label=entry['label'];path=ROOT/entry['full_vocal']
            ref=next(r for r in packaging['files'] if r['path']==entry['full_vocal']);assert sha(path)==ref['sha256']
            pcm[label],sr=sf.read(path,dtype='float64');assert sr==44100
            mels[label]=read_npz(run/'acoustic'/cid/f'{label}-r0/mel.npz')['mel'].astype(np.float64)
            feeds[label]=read_npz(run/'acoustic'/cid/f'{label}-r0/inputs.npz');detectors[label]={}
            for name,fn in [('FCPE',extract_f0),('RMVPE',rmvpe)]:
                record=fn(path);folder=run/'observations/F0'/cid;folder.mkdir(parents=True,exist_ok=True)
                file=folder/f'{label}-{name}.npz';assert not file.exists()
                np.savez_compressed(file,**{k:record[k] for k in ['f0_hz','voiced','times']})
                detectors[label][name]=record;calls+=1
                f0bindings.append(dict(condition_id=cid,variant=label,detector=name,
                    input=dict(path=entry['full_vocal'],sha256=sha(path)),array=dict(path=file.relative_to(ROOT).as_posix(),sha256=sha(file)),
                    clock={k:record[k] for k in ['sr','hop','frame_ms']},
                    valid_frames=int((record['voiced']&np.isfinite(record['f0_hz'])&(record['f0_hz']>0)).sum())))
                print(f'F0 {calls}/16 {cid} {label} {name}',flush=True)
        frame_clock=(a['position_ms']+(np.arange(feeds['A']['f0'].size)-a['head_frames'])*a['frame_ms'])/1000
        for window in windows:
            interval=window['interval_s'];indices=interval_indices(interval,origin,packed['samples'])
            # Whole PCM boundary is represented by exact sample count, not rounded decimal time.
            if window['id']=='whole-phrase':indices=(0,packed['samples'])
            item=dict(**window,pcm_indices=indices,status='computed_proxy_only' if indices else 'unknown_outside_pcm',variants={},comparisons={})
            if indices:
                frame=(frame_clock>=interval[0])&(frame_clock<interval[1])
                for label in ['A','S','D','P']:
                    x=pcm[label][slice(*indices)]
                    item['variants'][label]=dict(level=level(x),short_windows={str(w):centered_windows(pcm[label],interval,origin,w) for w in [30,50]},
                        final_channels={k:stats(feeds[label][k].ravel()[frame]) for k in ['breathiness','voicing','tension']})
                for direction in ['S-A','D-A','P-A','S-D','S-P']:
                    changed,base=direction.split('-');x,y=[pcm[label][slice(*indices)] for label in [base,changed]]
                    delta=level(y-x);rx,ry=level(x)['rms'],level(y)['rms']
                    mel=mels[changed][:,frame,:]-mels[base][:,frame,:]
                    shape=(mels[changed]-mels[changed].mean(axis=2,keepdims=True))[:,frame,:]-(mels[base]-mels[base].mean(axis=2,keepdims=True))[:,frame,:]
                    f0={name:f0_compare(detectors[base][name],detectors[changed][name],interval,origin) for name in ['FCPE','RMVPE']}
                    med=[f0[name]['cents']['median'] for name in ['FCPE','RMVPE']]
                    item['comparisons'][direction]=dict(pcm_difference=delta,level_ratio_db=20*math.log10(ry/rx) if rx>0 and ry>0 else None,
                        mel_difference_rms=float(np.sqrt(np.mean(mel*mel))) if mel.size else None,
                        mean_removed_mel_shape_difference_rms=float(np.sqrt(np.mean(shape*shape))) if shape.size else None,
                        F0=f0,detector_median_direction_disagreement=None if any(t is None for t in med) else bool(np.sign(med[0])!=np.sign(med[1])),
                        naturalness_or_break_cause='unknown')
            obs.append(dict(condition_id=cid,**item))
    assert calls==16
    for ref in weight_refs:assert sha(Path(ref['path']))==ref['sha256']
    save(run/'observations.json',dict(windows=obs,F0_bindings=f0bindings,F0_actual_inferences=16,
        actual_fresh_effect_repetitions=0,PCM_windows_clock='ceil(relative_seconds*44100), no boundary zero fill',
        spectrum='native mel and per-frame mean-removed shape proxy; not formant/physiology truth',
        F0_truth_status='unknown_no_calibrated_reference',coverage_policy='joint voiced finite >0, no UV interpolation; less than three frames unknown; report detector disagreements',
        level_is_perceived_loudness=False,agent_heard=False,auditory_acceptance='pending',measurement_validated_upgrades=False))

if __name__=='__main__':main()
