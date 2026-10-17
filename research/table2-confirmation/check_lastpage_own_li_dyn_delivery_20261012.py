"""Independent finite-sample DYN support, full PCM and83 observation windows."""
from io import BytesIO
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check,sha
from lastpage_own_li_dyn_20261012 import RUN,F,BASE,CURRENT
from check_lastpage_own_bright_cute_20261012 import read
from shfc_pcm_checks import dynamic_gain,interval_indices,level

def main():
    pack=load(RUN/'evaluation/delivery-check.json');check(list(pack['outputs'].values()))
    pcm,sr=sf.read(ROOT/pack['outputs']['candidate_full']['path'],dtype='float64');hpcm,_=sf.read(ROOT/pack['outputs']['candidate_full']['path'],dtype='int32')
    old=load(F/'evaluation/delivery-check.json')['outputs'];fpcm,_=sf.read(ROOT/old['candidate_full']['path'],dtype='int32')
    assert sr==44100 and sf.info(ROOT/pack['outputs']['candidate_full']['path']).subtype=='PCM_24'
    layout=load(RUN/'processed/layout.json');gain=np.fromfile(RUN/'processed/gain/phrase_000.f32',dtype='<f4');assert np.array_equal(gain,dynamic_gain(layout))
    parts=load(CURRENT/'design/phrase-ledger.json');expected=np.zeros(len(pcm),np.float64);baseline=expected.copy();allowed=np.zeros(len(pcm),bool)
    for p in parts:
        ctx=p['context'];a=b=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4')
        if ctx in [28,29]:
            a=np.load(F/f'fresh/context{ctx}/F/raw.npy',allow_pickle=False);b=a
            if ctx==28:
                b=a*gain;assert np.array_equal(b,np.fromfile(RUN/'processed/H/phrase_000.f32',dtype='<f4'))
                assert np.array_equal(b,np.fromfile(RUN/'processed/H_repeat/phrase_000.f32',dtype='<f4'))
            for label,w in [('F',a),('H',b)]:
                actual,_=sf.read(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',dtype='float64')
                assert np.max(np.abs(actual-w.astype(np.float64)*1.5))<=2**-23+8*np.finfo(np.float64).eps
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(len(pcm),start+len(b))
        expected[lo:hi]+=b[lo-start:hi-start];baseline[lo:hi]+=a[lo-start:hi-start]
        if ctx==28:allowed[lo:hi]=gain[lo-start:hi-start]!=1
    expected*=1.5;baseline*=1.5;err=float(np.max(np.abs(expected-pcm)))
    assert np.isfinite(expected).all() and np.max(np.abs(expected))<1 and err<=2**-23+8*np.finfo(np.float64).eps
    temp=BytesIO();sf.write(temp,baseline,sr,subtype='PCM_24',format='WAV');temp.seek(0);rebuilt,_=sf.read(temp,dtype='int32');assert np.array_equal(rebuilt,fpcm)
    assert np.array_equal(hpcm[~allowed],fpcm[~allowed])
    for ctx in [22,29]:
        p=parts[ctx];lo=round(p['wave_start_s']*sr);hi=lo+p['samples'];assert np.array_equal(hpcm[lo:hi],fpcm[lo:hi])
    lo,hi=[round(t*sr) for t in [209.4,218.0]]
    for key,x in [('candidate_preview',hpcm),('original_preview',fpcm)]:
        preview,_=sf.read(ROOT/pack['outputs'][key]['path'],dtype='int32');assert np.array_equal(preview,x[lo:hi])
    span=load(RUN/'evaluation/processed-independent-check.json')['actual_gain_change_span_s'];s,e=load(RUN/'design/protocol.json')['gesture']['support_s']
    tolerance=5*(60000/120/480)/1000+1/sr
    assert span[0]>=s-tolerance and span[1]<=e+tolerance
    obs=load(RUN/'observations/results.json');assert len(obs['windows'])==83 and obs['actual_F0_calls']==2 and obs['reused_F_F0_array_bindings']==6
    oldbindings=load(F/'observations/results.json')['detector_bindings']
    for b in obs['detector_bindings']:
        check([b['input'],b['output']]);d=read(ROOT/b['output']['path'])
        assert d['voiced'].dtype==np.bool_ and d['f0_hz'].dtype==d['times'].dtype==np.float32
        assert d['f0_hz'].shape==d['times'].shape==d['voiced'].shape and np.isfinite(d['f0_hz']).all() and np.all(np.diff(d['times'])>0)
        if b.get('reused_from_sealed_F'):
            original=next(q for q in oldbindings if q['context']==b['context'] and q['variant']=='F' and q['detector']==b['detector'])
            assert b['output']==original['output'] and b['clock']==original['clock'] and b['input']['sha256']==original['input']['sha256']
    for w in obs['windows']:
        ctx=w['context'];ix=(0,parts[ctx]['samples']) if w['role']=='whole_context' else interval_indices(w['interval_s'],parts[ctx]['wave_start_s'],parts[ctx]['samples'])
        assert (list(ix) if ix else None)==w['sample_indices']
        if not ix:continue
        vals=[]
        for label in ['F','H']:
            wave,_=sf.read(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',dtype='float64');result=level(wave[slice(*ix)])
            assert result==w['variants'][label]['level'];vals.append(result['rms'])
        delta=float(20*np.log10(vals[1]/vals[0])) if all(vals) else None;assert delta==w['H_minus_F']['level_ratio_db']
        assert w['variants']['F']['raw_level']==w['variants']['H']['raw_level'] and w['variants']['F']['final_features']==w['variants']['H']['final_features']
        assert w['H_minus_F']['mel_difference_rms'] in [0,None]
    phases={w['role']:w for w in obs['windows'] if w['role'].startswith('li_')}
    stage=[phases[k]['variants']['H']['level']['dbfs'] for k in ['li_entry','li_build','li_recover','li_release','li_descending']]
    assert stage[0]<stage[1]<stage[2] and stage[2]>stage[3]>stage[4]
    start=load(RUN/'observations/start.json');check(start['source']+start['inputs'])
    for m in start['models']:assert sha(Path(m['path']))==m['sha256']
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        native_gain_and_mul_exact=True,all34_and_F_baseline_PCM_reconstruction_exact=True,
        PCM_exact_outside_actual_gain_mask=True,accepted_baoC_and_entire_context29_PCM_exact=True,preview_exact=True,
        effective_support_within_one5tick_plus_sample=True,PCM_quantization_max_error=err,windows_independently_rebuilt=83,
        new_F0_calls=2,reused_F_F0_bindings=6,stage_RMS_rise_and_recovery_checked=True,
        actual_perceived_force_direction='unknown',agent_heard=False,measurement_validated=False))
    print(json.dumps(dict(status='delivery_passed',quantization_error=err,phase_RMS_dbfs=stage),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
