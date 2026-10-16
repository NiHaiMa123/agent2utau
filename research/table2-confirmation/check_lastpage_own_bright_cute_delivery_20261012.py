"""Independent all-contribution PCM and finite observation audit."""
from io import BytesIO
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,check,sha,ref
from lastpage_own_bright_cute_20261012 import RUN,BASE,CURRENT
from check_lastpage_own_bright_cute_20261012 import read
from shfc_pcm_checks import interval_indices,level

def main():
    pack=load(RUN/'evaluation/delivery-check.json');check(list(pack['outputs'].values()))
    pcm,sr=sf.read(ROOT/pack['outputs']['candidate_full']['path'],dtype='float64')
    encoded,_=sf.read(ROOT/pack['outputs']['candidate_full']['path'],dtype='int32')
    old_pcm,_=sf.read(CURRENT/'delivery/lastpage_accepted_C_baseline_vocal.wav',dtype='int32')
    assert sr==44100 and len(pcm)==pack['samples']
    assert sf.info(ROOT/pack['outputs']['candidate_full']['path']).subtype=='PCM_24'
    parts=load(CURRENT/'design/phrase-ledger.json');expected=np.zeros(len(pcm),np.float64);baseline=expected.copy();affected=np.zeros(len(pcm),bool)
    for p in parts:
        ctx=p['context'];old=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4');new=old
        if ctx in [28,29]:
            gain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ctx:03}.f32',dtype='<f4');assert np.all(gain==1)
            a=np.load(RUN/f'fresh/context{ctx}/A/raw.npy',allow_pickle=False)*gain;assert np.array_equal(a,old)
            new=np.load(RUN/f'fresh/context{ctx}/E/raw.npy',allow_pickle=False)*gain
            assert np.array_equal(new,np.fromfile(RUN/f'dynamics/context{ctx}-E.f32',dtype='<f4'))
            for label,x in [('A',a),('E',new)]:
                actual,_=sf.read(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',dtype='float64')
                assert len(actual)==len(x) and np.max(np.abs(actual-x.astype(np.float64)*1.5))<=2**-23+8*np.finfo(np.float64).eps
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(len(pcm),start+len(new))
        expected[lo:hi]+=new[lo-start:hi-start];baseline[lo:hi]+=old[lo-start:hi-start]
        if ctx in [28,29]:affected[lo:hi]=True
    expected*=1.5;baseline*=1.5
    error=float(np.max(np.abs(expected-pcm)))
    assert np.isfinite(expected).all() and np.max(np.abs(expected))<1
    assert error<=2**-23+8*np.finfo(np.float64).eps
    temp=BytesIO();sf.write(temp,baseline,sr,subtype='PCM_24',format='WAV');temp.seek(0)
    decoded,_=sf.read(temp,dtype='int32');assert np.array_equal(decoded,old_pcm)
    assert np.array_equal(old_pcm[~affected],encoded[~affected])
    p=parts[22];lo=round(p['wave_start_s']*sr);hi=lo+p['samples'];assert np.array_equal(old_pcm[lo:hi],encoded[lo:hi])
    lo,hi=[round(t*sr) for t in [209.4,218.0]]
    for key,source in [('candidate_preview',encoded),('original_preview',old_pcm)]:
        preview,_=sf.read(ROOT/pack['outputs'][key]['path'],dtype='int32');assert np.array_equal(preview,source[lo:hi])
    obs=load(RUN/'observations/results.json');assert obs['actual_F0_calls']==8 and len(obs['windows'])==77 and len(obs['detector_bindings'])==8
    for b in obs['detector_bindings']:
        check([b['input'],b['output']]);d=read(ROOT/b['output']['path'])
        assert set(d)=={'f0_hz','voiced','times'} and d['voiced'].dtype==np.bool_
        assert d['f0_hz'].dtype==d['times'].dtype==np.float32
        assert d['f0_hz'].shape==d['voiced'].shape==d['times'].shape
        assert np.isfinite(d['f0_hz']).all() and np.isfinite(d['times']).all() and np.all(np.diff(d['times'])>0)
    for row in obs['windows']:
        ctx=row['context'];origin=parts[ctx]['wave_start_s'];n=parts[ctx]['samples']
        ix=(0,n) if row['role']=='whole_context' else interval_indices(row['interval_s'],origin,n)
        assert (list(ix) if ix else None)==row['sample_indices']
        if not ix:continue
        values=[]
        for label in ['A','E']:
            audio,_=sf.read(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',dtype='float64')
            computed=level(audio[slice(*ix)]);assert computed==row['variants'][label]['level'];values.append(computed['rms'])
        delta=float(20*np.log10(values[1]/values[0])) if all(values) else None
        assert delta==row['E_minus_A']['level_ratio_db']
    start=load(RUN/'observations/start.json');check(start['source']+start['inputs'])
    for r in start['models']:assert sha(Path(r['path']))==r['sha256']
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        PCM_quantization_max_error=error,fixed_gain=1.5,all_34_contributions_checked=True,
        only_context28_29_contributions_changed=True,outside_union_and_bao_C_PCM_exact=True,
        baseline_reconstruction_and_preview_exact=True,F0_arrays_checked=8,metric_windows_independently_rebuilt=77,
        agent_heard=False,measurement_validated=False))
    print(json.dumps(dict(status='delivery_passed',quantization_error=error,F0_arrays=8),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
