"""Bound finite numerical checks. No audio files, models or songs are opened."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
from agent2utau.analysis.f0 import hz_to_midi
from agent2utau.analysis.onsets import frame_rms
from agent2utau.evaluation.features import shape_features, boundary_candidates
from agent2utau.evaluation.controlled_probe import spectral_response
from agent2utau.openutau.ustx import TempoMap

ROOT = Path(__file__).resolve().parents[2]
CODE = ['src/agent2utau/evaluation/features.py','src/agent2utau/evaluation/controlled_probe.py',
        'src/agent2utau/analysis/f0.py','src/agent2utau/analysis/onsets.py','src/agent2utau/openutau/ustx.py']


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    path=args.out.resolve()
    assert path.is_relative_to(ROOT/'runs/research') and not path.exists()
    cases=[]
    def add(id_, entities, input_spec, truth, observed, limit):
        cases.append(dict(id=id_,candidate_entities=entities,input_spec=input_spec,
            truth=truth,observed=observed,technical_check='passed',
            validation_scope=limit,real_audio_accuracy_validated=False,auditory_effect_validated=False))
    result=hz_to_midi(np.array([440.,880.]))
    assert np.allclose(result,[69,81],rtol=0,atol=1e-12)
    add('DVAL:01',['ACO:P1'],'Hz=[440,880]; positive finite values only',
        dict(midi=[69,81],difference_cents=1200),dict(midi=result.tolist(),difference_cents=float(np.diff(result)[0]*100)),
        'Unit conversion only; no FCPE/RMVPE execution, voiced mask accuracy or reference identity truth')
    t=np.arange(0,2,.005)
    platform=shape_features(t,np.full(len(t),6000.))
    drift=shape_features(t,6000+20*t)
    assert platform['morphology']=='platform' and drift['morphology']=='drift'
    assert abs(drift['trend_c_per_s']-20)<1e-8 and drift['residual_range_c']<1e-8
    add('DVAL:02',['EVT:P2','ACO:P5'],'t=arange(0,2,0.005); y=6000 or 6000+20*t',
        dict(linear_slope_c_per_s=20,residual=0),dict(platform=platform['morphology'],drift=drift),
        'OLS straight-line primitive only; frame residual not cycle jitter or a validated nonperiodic decomposition')
    y=6000+20*np.sin(2*np.pi*5*t)
    periodic=shape_features(t,y)
    reordered=shape_features(t,np.sort(y))
    rate=float(np.median([c['hz'] for c in periodic['cycles']]))
    width=float(np.median([c['peak_to_trough_c'] for c in periodic['cycles']]))
    assert periodic['morphology']=='oscillatory_candidate' and len(periodic['cycles'])>=7
    assert abs(rate-5)<.05 and abs(width-40)<1 and not reordered['cycles']
    add('DVAL:03',['ACO:P4'],'y=6000+20*sin(2*pi*5*t); same values sorted as negative control',
        dict(rate_hz=5,half_depth_cents=20,peak_to_trough_cents=40),
        dict(median_rate_hz=rate,median_peak_to_trough_cents=width,cycles=len(periodic['cycles']),sorted_cycles=len(reordered['cycles'])),
        'Known F0 curve values only; no extractor accuracy, fast-changing vibrato performance or perceived vibrato truth')
    bad=[shape_features(t[:10],y[:10]),shape_features(t,np.full(len(t),np.nan)),shape_features(t*20,np.zeros(len(t)))]
    assert all(r['status']=='unknown' for r in bad)
    rs=[dict(start_s=0,end_s=.012,region_type='non_singing'),dict(start_s=.012,end_s=.03,region_type='vowel')]
    b=boundary_candidates([0,.005,.01,.015,.02],[6000,6300,6000,6500,6500],rs)
    assert b['excluded_non_singing']==2 and any(x['code']=='non_singing_transition_risk' for x in b['findings'])
    add('DVAL:04',['ACO:P4','EVT:T5'],'short/NaN/100ms-gap curves; declared SP then vowel with known jumps',
        dict(invalid_cases_unknown=3,SP_internal_excluded=2),dict(invalid_reasons=[r['reason'] for r in bad],boundary=b),
        'Input validation and explicitly supplied region masks; no real phone classification or audible boundary truth')
    a=np.zeros((1,4,3),np.float32);clock=np.arange(4)*.01
    level=spectral_response(a,a+2,clock,[0,.03])
    shape=spectral_response(a,a+np.array([0,1,2]),clock,[0,.03])
    assert level['log_mel_rms']==2 and level['level_removed_log_mel_rms']==0
    assert abs(shape['level_removed_log_mel_rms']-np.sqrt(2/3))<1e-12
    add('DVAL:05',['ACO:R5'],'native log-mel constant +2 vs bins +[0,1,2]',
        dict(common_log_offset_shape_rms=0,nonuniform_shape_rms=float(np.sqrt(2/3))),dict(level=level,shape=shape),
        'Arithmetic of bound log-mel proxy only; not dBFS, formant truth, acoustic waveform level removal or improvement')
    tm=TempoMap([dict(position=0,bpm=120),dict(position=480,bpm=60)],480)
    ms=[tm.tick_to_ms(v) for v in [0,480,960]]
    assert np.allclose(ms,[0,500,1500],rtol=0,atol=1e-12)
    assert np.allclose([tm.ms_to_tick(v) for v in ms],[0,480,960],rtol=0,atol=1e-12)
    add('DVAL:06',['EVT:T1','ACO:T2'],'480PPQ; 120BPM to tick480, then60BPM',
        dict(milliseconds=[0,500,1500]),dict(milliseconds=ms),
        'Score tempo conversion only; no PCM offset, model latency, HFA boundary or perceived timing truth')
    levels=np.r_[np.full(500,.1),np.full(500,.2)]
    times=np.array([.2,.48,.6])
    rms30=frame_rms(levels,1000,times,win=30)
    rms50=frame_rms(levels,1000,times,win=50)
    truth30=np.sqrt((20*.1**2+10*.2**2)/30)
    truth50=np.sqrt((20*.1**2+30*.2**2)/50)
    assert abs(rms30[1]-truth30)<1e-12 and abs(rms50[1]-truth50)<1e-12
    gain_db=float(20*np.log10(rms30[2]/rms30[0]))
    assert abs(gain_db-20*np.log10(2))<1e-12
    add('DVAL:07',['ACO:L1','EVT:L2','EVT:L4'],'numeric level array .1 first500 then .2 next500; sr clock1000; forward30/50sample windows',
        dict(steady_change_db=float(20*np.log10(2)),boundary_window30=truth30,boundary_window50=truth50),
        dict(rms30=rms30.tolist(),rms50=rms50.tolist(),steady_change_db=gain_db),
        'Existing frame_rms uses forward window at frame time, not centered window. Numerical levels only, no new audio; no loudness or phonation test')
    amp=1+.2*np.sin(2*np.pi*5*t)
    index=float((amp.max()-amp.min())/(amp.max()+amp.min()))
    assert abs(index-.2)<1e-12
    add('DVAL:08',['ACO:L3'],'numeric envelope 1+.2*sin(2*pi*5*t)',
        dict(linear_modulation_index=.2),dict(linear_modulation_index=index),
        'Definition algebra only; no PCM envelope extraction or general AM detector validation')
    raw=np.array([-.5,-2.,0.,2.,.5]);clipped=np.clip(raw,-1,1)
    assert np.count_nonzero(clipped!=raw)==2 and np.max(abs(clipped))==1
    seam=np.r_[np.full(8,.1),np.full(8,.3)]
    assert abs(np.diff(seam)[7]-.2)<1e-12 and np.count_nonzero(np.diff(seam))==1
    add('DVAL:09',['ACO:X1','ACO:X2'],'known clip before/after and .1→.3 sample-array seam',
        dict(changed_clip_samples=2,seam_delta=.2),dict(clipped=clipped.tolist(),seam_delta=float(np.diff(seam)[7])),
        'Known algebraic clip/seam only; does not execute wavcheck, prove true peak, or establish click/破音 thresholds')
    left=np.tile([1.,-1.],128);right=-left
    corr=float(np.corrcoef(left,right)[0,1]);mono=(left+right)/2
    assert abs(corr+1)<1e-12 and np.max(abs(mono))==0 and np.mean(left*left)==1
    add('DVAL:10',['ACO:X4'],'numeric LR arrays [1,-1] repeated; R=-L',
        dict(correlation=-1,channel_RMS=1,arithmetic_mono_RMS=0),dict(correlation=corr,mono_rms=float(np.sqrt(np.mean(mono**2)))),
        'Channel/downmix identity only; no perceived spatial quality or playback device validation')
    payload=dict(schema_version=1,stage='D',status='finite_array_checks_passed',
        cases=cases,versions={p:importlib.metadata.version(p) for p in ['numpy','scipy','soundfile']},
        code_bindings=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in CODE],
        no_audio_files_read_or_written=True,no_models_or_native_execution=True,no_new_auditory_labels=True,
        all_measurement_methods_validated=False)
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=payload['status'],checks=len(cases))))


if __name__=='__main__':
    main()
