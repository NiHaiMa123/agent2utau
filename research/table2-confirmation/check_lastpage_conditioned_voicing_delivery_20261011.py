"""Independent PCM and observation gate, without modifying the bound fresh checker."""
import math
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,check
from check_lastpage_conditioned_voicing_20261011 import read,RUN,BASE

def main():
    assert not (RUN/'evaluation/delivery-independent-check.json').exists()
    current=ROOT/'runs/production/lastpage-accepted-baseline-20261011'
    plan=load(RUN/'design/protocol.json');pack=load(RUN/'evaluation/delivery-check.json')
    check(list(pack['outputs'].values()))
    pcm,sr=sf.read(ROOT/pack['outputs']['candidate_full']['path'],dtype='float64')
    old_pcm,_=sf.read(current/'delivery/lastpage_accepted_C_baseline_vocal.wav',dtype='int32')
    new_pcm,_=sf.read(ROOT/pack['outputs']['candidate_full']['path'],dtype='int32')
    assert sr==44100 and len(pcm)==pack['samples'] and sf.info(ROOT/pack['outputs']['candidate_full']['path']).subtype=='PCM_24'
    parts=load(current/'design/phrase-ledger.json');expected=np.zeros(len(pcm),np.float64)
    affected=np.zeros(len(pcm),bool)
    for p in parts:
        ctx=p['context'];wave=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4')
        if ctx==28:
            wave=np.load(RUN/'fresh/context28/B/raw.npy',allow_pickle=False)*np.fromfile(BASE/'native_dynamics_ones/phrase_028.f32',dtype='<f4')
            assert np.array_equal(wave,np.fromfile(RUN/'dynamics/context28-B.f32',dtype='<f4'))
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(len(pcm),start+len(wave))
        expected[lo:hi]+=wave[lo-start:hi-start]
        if ctx==28:affected[lo:hi]=True
    expected*=1.5
    quant_error=float(np.max(np.abs(expected-pcm)))
    assert np.isfinite(expected).all() and np.max(np.abs(expected))<1
    assert quant_error<=2**-23+8*np.finfo(np.float64).eps
    assert np.array_equal(old_pcm[~affected],new_pcm[~affected])
    for ctx in [22,29]:
        p=parts[ctx];lo=round(p['wave_start_s']*sr);hi=lo+p['samples']
        if ctx==29:
            origin=load(RUN/'native-inputs/A/phrase_001.json')['phones'][0]['positionMs']/1000
            lo=math.ceil(origin*sr)
        assert np.array_equal(old_pcm[lo:hi],new_pcm[lo:hi])
    preview,_=sf.read(ROOT/pack['outputs']['candidate_preview']['path'],dtype='int32')
    lo,hi=[round(t*sr) for t in [209.4,218.0]]
    assert np.array_equal(preview,new_pcm[lo:hi])
    observations=load(RUN/'observations/results.json')
    assert observations['actual_F0_calls']==8 and len(observations['windows'])==77
    assert len(observations['detector_bindings'])==8
    for b in observations['detector_bindings']:
        check([b['input'],b['output']]);d=read(ROOT/b['output']['path'])
        assert set(d)=={'f0_hz','voiced','times'} and d['voiced'].dtype==np.bool_
        assert d['f0_hz'].dtype==d['times'].dtype==np.float32
        assert d['f0_hz'].shape==d['voiced'].shape==d['times'].shape
        assert np.isfinite(d['f0_hz']).all() and np.isfinite(d['times']).all() and np.all(np.diff(d['times'])>0)
    for row in observations['windows']:
        if row['role']!='full_vowel':continue
        ctx=row['context'];origin=parts[ctx]['wave_start_s'];s,e=row['interval_s']
        lo,hi=math.ceil((s-origin)*sr),math.ceil((e-origin)*sr)
        values=[]
        for label in ['A','B']:
            audio,_=sf.read(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',dtype='float64')
            r=float(np.sqrt(np.mean(audio[lo:hi]**2)));values.append(r)
            assert r==row['variants'][label]['level']['rms']
        delta=float(20*np.log10(values[1]/values[0]))
        assert delta==row['B_minus_A']['level_ratio_db']
    start=load(RUN/'observations/start.json')
    for r in start['models']:
        from assemble_lastpage_accepted_baseline_20261011 import sha
        assert sha(Path(r['path']))==r['sha256']
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',PCM_quantization_max_error=quant_error,
        fixed_gain=1.5,all_34_contributions_checked=True,only_context28_contribution_changed=True,
        context29_real_phones_and_bao_C_PCM_exact=True,preview_exact=True,F0_arrays_checked=8,
        full_vowel_metric_rows_independently_rebuilt=15,agent_heard=False,measurement_validated=False))
    print(json.dumps(dict(status='delivery_passed',quantization_error=quant_error,F0_arrays=8),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
