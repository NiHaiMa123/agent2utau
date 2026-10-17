"""Independent J/F assembly, real second phrase protection, and84 proxy windows."""
from io import BytesIO
import json
import math
from pathlib import Path
import numpy as np
import soundfile as sf
from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check,sha
from lastpage_own_li_entry_pitch_20261013 import RUN,F,BASE,CURRENT
from check_lastpage_own_bright_cute_20261012 import read
from shfc_pcm_checks import interval_indices,level

def main():
    pack=load(RUN/'evaluation/delivery-check.json');check(list(pack['outputs'].values()))
    pcm,sr=sf.read(ROOT/pack['outputs']['candidate_full']['path'],dtype='float64');gpcm,_=sf.read(ROOT/pack['outputs']['candidate_full']['path'],dtype='int32')
    old=load(F/'evaluation/delivery-check.json')['outputs'];fpcm,_=sf.read(ROOT/old['candidate_full']['path'],dtype='int32')
    assert sr==44100 and sf.info(ROOT/pack['outputs']['candidate_full']['path']).subtype=='PCM_24'
    parts=load(CURRENT/'design/phrase-ledger.json');base=np.zeros(len(pcm),np.float64);expected=base.copy();allowed=np.zeros(len(pcm),bool)
    for p in parts:
        ctx=p['context'];a=b=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4')
        if ctx in [28,29]:
            gain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ctx:03}.f32',dtype='<f4');assert np.all(gain==1)
            a=np.load(F/f'fresh/context{ctx}/F/raw.npy',allow_pickle=False)*gain;b=a
            if ctx==28:
                b=np.load(RUN/'fresh/context28/J/raw.npy',allow_pickle=False)*gain;assert np.array_equal(b,np.fromfile(RUN/'dynamics/context28-J.f32',dtype='<f4'))
            for label,w in [('F',a),('J',b)]:
                actual,_=sf.read(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',dtype='float64')
                assert np.max(np.abs(actual-w.astype(np.float64)*1.5))<=2**-23+8*np.finfo(np.float64).eps
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(len(pcm),start+len(b))
        base[lo:hi]+=a[lo-start:hi-start];expected[lo:hi]+=b[lo-start:hi-start]
        if ctx==28:allowed[lo:hi]=True
    expected*=1.5;base*=1.5;err=float(np.max(np.abs(expected-pcm)))
    assert np.max(np.abs(expected))<1 and err<=2**-23+8*np.finfo(np.float64).eps
    temp=BytesIO();sf.write(temp,base,sr,subtype='PCM_24',format='WAV');temp.seek(0);rebuilt,_=sf.read(temp,dtype='int32');assert np.array_equal(rebuilt,fpcm)
    assert np.array_equal(gpcm[~allowed],fpcm[~allowed])
    for ctx in [22,29]:
        p=parts[ctx];lo=round(p['wave_start_s']*sr);hi=lo+p['samples']
        if ctx==29:lo=math.ceil(load(RUN/'native-inputs/J/phrase_001.json')['phones'][0]['positionMs']/1000*sr)
        assert np.array_equal(gpcm[lo:hi],fpcm[lo:hi])
    lo,hi=[round(t*sr) for t in [209.4,218.0]]
    for key,x in [('candidate_preview',gpcm),('original_preview',fpcm)]:
        preview,_=sf.read(ROOT/pack['outputs'][key]['path'],dtype='int32');assert np.array_equal(preview,x[lo:hi])
    obs=load(RUN/'observations/results.json');assert len(obs['windows'])==84 and obs['actual_F0_calls']==2 and obs['reused_F_F0_array_bindings']==6
    oldbindings=load(F/'observations/results.json')['detector_bindings']
    for b in obs['detector_bindings']:
        check([b['input'],b['output']]);d=read(ROOT/b['output']['path'])
        assert d['voiced'].dtype==np.bool_ and d['f0_hz'].dtype==d['times'].dtype==np.float32
        assert d['f0_hz'].shape==d['times'].shape==d['voiced'].shape and np.isfinite(d['f0_hz']).all() and np.all(np.diff(d['times'])>0)
        if b.get('reused_from_sealed_F'):
            ob=next(q for q in oldbindings if q['context']==b['context'] and q['variant']=='F' and q['detector']==b['detector'])
            assert b['output']==ob['output'] and b['clock']==ob['clock'] and b['input']['sha256']==ob['input']['sha256']
    for w in obs['windows']:
        ctx=w['context'];ix=(0,parts[ctx]['samples']) if w['role']=='whole_context' else interval_indices(w['interval_s'],parts[ctx]['wave_start_s'],parts[ctx]['samples'])
        assert (list(ix) if ix else None)==w['sample_indices']
        if not ix:continue
        values=[]
        for label in ['F','J']:
            wave,_=sf.read(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',dtype='float64');result=level(wave[slice(*ix)])
            assert result==w['variants'][label]['level'];values.append(result['rms'])
        delta=float(20*np.log10(values[1]/values[0])) if all(values) else None;assert delta==w['J_minus_F']['level_ratio_db']
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed'
    start=load(RUN/'observations/start.json');check(start['source']+start['inputs'])
    for r in start['models']:assert sha(Path(r['path']))==r['sha256']
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        all34_contributions_and_F_PCM_reconstruction_exact=True,outside_context28_and_baoC_and_context29_real_phones_exact=True,
        preview_exact=True,PCM_quantization_max_error=err,windows_independently_rebuilt=84,new_F0_calls=2,reused_F_F0_bindings=6,
        entry_pitch_native_target_checked=True,actual_perceived_force_direction='unknown',agent_heard=False,measurement_validated=False))
    print(json.dumps(dict(status='delivery_passed',quantization_error=err,windows=84),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
