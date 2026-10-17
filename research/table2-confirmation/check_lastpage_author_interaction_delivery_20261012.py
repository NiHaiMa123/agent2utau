"""Independent D PCM assembly, unchanged references, F0 reuse and interaction audit."""
from pathlib import Path
import numpy as np
import soundfile as sf
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,sha,check
from agent2utau.evaluation.controlled_probe import tensors

RUN=ROOT/'runs/experiments/lastpage-author-interaction-20261012'
CONTROL=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
VOICE=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
OLD={'A':CONTROL,'B':VOICE,'C':CONTROL}
CHANNELS=['breathiness','voicing','tension']


def main():
    pack=load(RUN/'evaluation/delivery-check.json');check(list(pack['outputs'].values()))
    d=yaml.safe_load((RUN/'score/D.ustx').read_text(encoding='utf-8-sig'))
    assert d['expressions']['dyn']['default_value']==0 and not any(c['abbr']=='dyn' and c['xs'] for c in d['voice_parts'][0]['curves'])
    sr=44100;start,end=[round(x*sr) for x in pack['preview_s']];expected=np.zeros(end-start,np.float64);max_error=0
    for ctx in [0,1]:
        f=load(RUN/f'native-inputs/D/phrase_{ctx:03}.json')
        origin=(f['position_ms']-f['head_frames']*float(np.float32(512/44100*1000)))/1000
        r=next(r for r in pack['contexts'] if r['context']==ctx and r['variant']=='D');assert origin==r['wave_start_s']
        raw=np.load(RUN/f'fresh/context{ctx}/D/raw.npy',allow_pickle=False);assert len(raw)==int(tensors(f['tensors'])['durations'].sum())*512==r['samples']
        pcm,rate=sf.read(ROOT/r['PCM']['path'],dtype='float64');assert rate==sr and sf.info(ROOT/r['PCM']['path']).subtype=='PCM_24'
        error=float(np.max(np.abs(pcm-raw.astype(np.float64)*1.5)));assert error<=2**-23+1e-15;max_error=max(max_error,error)
        i=round(origin*sr);lo,hi=max(start,i),min(end,i+len(raw));expected[lo-start:hi-start]+=raw[lo-i:hi-i].astype(np.float64)
        if ctx==1:assert i+len(raw)<=end
    expected*=1.5;pcm,rate=sf.read(ROOT/pack['outputs']['D']['path'],dtype='float64')
    assert rate==sr and len(pcm)==pack['samples'] and np.isfinite(expected).all() and np.max(np.abs(expected))<1
    error=float(np.max(np.abs(pcm-expected)));assert error<=2**-23+1e-15;max_error=max(error,max_error)
    for label,folder in OLD.items():
        assert pack['outputs'][label]['sha256']==sha(folder/f'delivery/{label}_two_phrases.wav')
        for ctx in [0,1]:assert sha(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav')==sha(folder/f'evaluation/PCM-contexts/context{ctx}-{label}.wav')
    obs=load(RUN/'observations/results.json');assert obs['new_F0_calls']==4 and obs['reused_A_B_C_F0_arrays']==12 and len(obs['detector_bindings'])==16
    for b in obs['detector_bindings']:
        check([b['input'],b['output']])
        if b['reused']:
            check([b['current_input']]);assert b['current_input']['sha256']==b['input']['sha256']
        with np.load(ROOT/b['output']['path'],allow_pickle=False) as z:
            assert set(z.files)=={'f0_hz','voiced','times'} and z['f0_hz'].dtype==z['times'].dtype==np.float32 and z['voiced'].dtype==np.bool_
            assert z['f0_hz'].shape==z['voiced'].shape==z['times'].shape and np.isfinite(z['f0_hz']).all() and np.all(np.diff(z['times'])>0)
    count=0;interaction_rows=0
    for w in obs['windows']:
        if not w['sample_indices']:continue
        ctx=w['context'];lo,hi=w['sample_indices'];rms={};means={}
        f=load(RUN/f'native-inputs/D/phrase_{ctx:03}.json');time=(f['position_ms']+(np.arange(tensors(f['tensors'])['f0'].size)-f['head_frames'])*f['frame_ms'])/1000
        mask=(time>=w['interval_s'][0])&(time<w['interval_s'][1])
        for l in ['A','B','C','D']:
            pcm,_=sf.read(RUN/f'evaluation/PCM-contexts/context{ctx}-{l}.wav',dtype='float64')
            value=float(np.sqrt(np.mean(pcm[lo:hi]**2)));assert value==w['variants'][l]['level']['rms'];rms[l]=value;count+=1
            folder=RUN if l=='D' else OLD[l]
            with np.load(folder/f'fresh/context{ctx}/{l}/inputs.npz',allow_pickle=False) as z:
                means[l]={ch:float(np.mean(z[ch].ravel()[mask].astype(np.float64))) if mask.any() else None for ch in CHANNELS}
            assert means[l]==w['variants'][l]['feature_means']
        ratios={}
        for key,v in w['comparisons'].items():
            new,base=key.split('-');r=float(20*np.log10(rms[new]/rms[base])) if rms[new] and rms[base] else None
            assert r==v['RMS_ratio_db'];ratios[key]=r
        interaction=ratios['D-C']-ratios['B-A'] if ratios['D-C'] is not None and ratios['B-A'] is not None else None
        assert interaction==w['interaction']['RMS_db_difference_of_differences']
        for ch in CHANNELS:
            expected=(means['D'][ch]-means['C'][ch])-(means['B'][ch]-means['A'][ch]) if mask.any() else None
            assert expected==w['interaction']['feature_mean_difference_of_differences'][ch]
        interaction_rows+=1
    assert count==128 and interaction_rows==32
    for m in load(RUN/'observations/start.json')['models']:assert sha(Path(m['path']))==m['sha256']
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        PCM_quantization_max_error=max_error,old_A_B_C_WAV_bytes_exact=True,new_F0_arrays=4,reused_F0_arrays=12,
        independently_rebuilt_RMS_values=count,interaction_rows=interaction_rows,full_second_phrase_tail_included=True,
        agent_heard=False,measurement_validated=False))
    print('Independent D PCM/reference bytes/F0 and 32 factorial proxy rows passed.',flush=True)


if __name__=='__main__':main()
