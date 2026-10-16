"""Independent fixed gain/clock PCM, F0 reuse and window scalar reconstruction."""
from pathlib import Path
import numpy as np
import soundfile as sf
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,sha,check
from agent2utau.evaluation.controlled_probe import tensors

RUN=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
PRIOR=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'


def main():
    pack=load(RUN/'evaluation/delivery-check.json');check(list(pack['outputs'].values()))
    doc=yaml.safe_load((RUN/'score/C.ustx').read_text(encoding='utf-8-sig'))
    assert doc['expressions']['dyn']['default_value']==0 and not any(c['abbr']=='dyn' and c['xs'] for c in doc['voice_parts'][0]['curves'])
    sr=44100;start,end=[round(x*sr) for x in pack['preview_s']];error_max=0
    for l in ['A','C']:
        joined=np.zeros(end-start,np.float64)
        for ctx in [0,1]:
            f=load(RUN/f'native-inputs/{l}/phrase_{ctx:03}.json')
            origin=(f['position_ms']-f['head_frames']*float(np.float32(512/44100*1000)))/1000
            r=next(r for r in pack['contexts'] if r['context']==ctx and r['variant']==l);assert r['wave_start_s']==origin
            wave=np.load(RUN/f'fresh/context{ctx}/{l}/raw.npy',allow_pickle=False)
            assert len(wave)==int(tensors(f['tensors'])['durations'].sum())*512==r['samples']
            pcm,rate=sf.read(ROOT/r['PCM']['path'],dtype='float64');assert rate==sr
            error=float(np.max(np.abs(pcm-wave.astype(np.float64)*1.5)));assert error<=2**-23+1e-15;error_max=max(error,error_max)
            i=round(origin*sr);lo,hi=max(start,i),min(end,i+len(wave));joined[lo-start:hi-start]+=wave[lo-i:hi-i].astype(np.float64)
            if ctx==1:assert i+len(wave)<=end
        joined*=1.5;pcm,rate=sf.read(ROOT/pack['outputs'][l]['path'],dtype='float64')
        assert rate==sr and len(pcm)==pack['samples'] and sf.info(ROOT/pack['outputs'][l]['path']).subtype=='PCM_24'
        assert np.isfinite(joined).all() and np.max(np.abs(joined))<1
        error=float(np.max(np.abs(pcm-joined)));assert error<=2**-23+1e-15;error_max=max(error,error_max)
    assert pack['outputs']['A']['sha256']==sha(PRIOR/'delivery/A_two_phrases.wav')
    assert pack['outputs']['own_original_comparator']['sha256']==load(RUN/'feedback/voice-feedback.json')['audio']['own_original_comparator']['sha256']
    obs=load(RUN/'observations/results.json');assert obs['new_F0_calls']==4 and obs['reused_A_F0_arrays']==4 and len(obs['detector_bindings'])==8
    for b in obs['detector_bindings']:
        check([b['input'],b['output']])
        if b['reused']:
            check([b['current_input']]);assert b['current_input']['sha256']==b['input']['sha256']
        with np.load(ROOT/b['output']['path'],allow_pickle=False) as z:
            assert set(z.files)=={'f0_hz','voiced','times'}
            assert z['f0_hz'].dtype==z['times'].dtype==np.float32 and z['voiced'].dtype==np.bool_
            assert z['f0_hz'].shape==z['voiced'].shape==z['times'].shape and np.isfinite(z['f0_hz']).all() and np.all(np.diff(z['times'])>0)
    count=0
    for w in obs['windows']:
        if not w['sample_indices']:continue
        lo,hi=w['sample_indices'];rms=[]
        for l in ['A','C']:
            pcm,_=sf.read(RUN/f'evaluation/PCM-contexts/context{w["context"]}-{l}.wav',dtype='float64')
            r=float(np.sqrt(np.mean(pcm[lo:hi]**2)));assert r==w['variants'][l]['level']['rms'];rms.append(r);count+=1
        expected=float(20*np.log10(rms[1]/rms[0])) if all(rms) else None
        assert expected==w['C_minus_A']['RMS_ratio_db']
    assert count==64
    for m in load(RUN/'observations/start.json')['models']:assert sha(Path(m['path']))==m['sha256']
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        independent_RMS_values=count,PCM_quantization_max_error=error_max,full_second_phrase_tail_preserved=True,
        accepted_A_WAV_exact=True,own_comparator_unchanged=True,F0_A_reuse_same_PCM_and_models=True,new_F0_arrays=4,reused_F0_arrays=4,
        preflight_repair='Inherited B score filename corrected to actual C; prior checker/failure preserved in logs/rejected-delivery-preflight; no math/audio/model edits',
        agent_heard=False,measurement_validated=False))
    print('Independent PCM, exact accepted A, F0 reuse and 64 RMS values passed.',flush=True)


if __name__=='__main__':main()
