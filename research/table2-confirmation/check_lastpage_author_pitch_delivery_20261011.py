"""Independent PCM assembly, old-author identity, detector and scalar audit."""
import math
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT, load, save, ref, sha, check
from agent2utau.evaluation.controlled_probe import tensors

RUN=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011'
AUTHOR=ROOT/'runs/research/lastpage-li-kan-author-reference-20261011'


def main():
    pack=load(RUN/'evaluation/delivery-check.json');check(list(pack['outputs'].values()))
    doc=yaml.safe_load((RUN/'score/A.ustx').read_text(encoding='utf-8-sig'))
    assert doc['expressions']['dyn']['default_value']==0
    assert not any(c['abbr']=='dyn' and c['xs'] for c in doc['voice_parts'][0]['curves'])
    assert sha(RUN/'score/A.ustx')==sha(AUTHOR/'score/baishuo-main-part2-current165c.ustx')
    for ctx in [0,1]:
        old=load(AUTHOR/f'native-inputs/probe/phrase_{ctx:03}.json');new=load(RUN/f'native-inputs/A/phrase_{ctx:03}.json')
        for k in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','expression_deltas','vocoder_f0','tone_shift_cents']:
            assert old[k]==new[k],(ctx,k)
        a,b=tensors(old['tensors']),tensors(new['tensors'])
        assert all(np.array_equal(a[k],b[k]) for k in a if k not in ['breathiness','voicing','tension'])
    sr=44100;start,end=[round(x*sr) for x in pack['preview_s']];max_error=0
    for label in ['A','P','N','PN']:
        joined=np.zeros(end-start,np.float64)
        for ctx in [0,1]:
            f=load(RUN/f'native-inputs/{label}/phrase_{ctx:03}.json')
            r=next(r for r in pack['contexts'] if r['context']==ctx and r['variant']==label)
            origin=(f['position_ms']-f['head_frames']*float(np.float32(512/44100*1000)))/1000
            assert origin==r['wave_start_s']
            wave=np.load(RUN/f'fresh/context{ctx}/{label}/raw.npy',allow_pickle=False)
            assert len(wave)==int(tensors(f['tensors'])['durations'].sum())*512
            pcm,rate=sf.read(ROOT/r['PCM']['path'],dtype='float64')
            assert rate==sr and sf.info(ROOT/r['PCM']['path']).subtype=='PCM_24'
            error=float(np.max(np.abs(pcm-wave.astype(np.float64)*1.5)));max_error=max(max_error,error)
            assert error<=2**-23+1e-15
            tick=round(origin*sr);lo,hi=max(start,tick),min(end,tick+len(wave))
            joined[lo-start:hi-start]+=wave[lo-tick:hi-tick].astype(np.float64)
            if ctx==1:assert tick+len(wave)<=end, 'Preview lost second phrase release'
        joined*=1.5
        pcm,rate=sf.read(ROOT/pack['outputs'][label]['path'],dtype='float64')
        assert rate==sr and len(pcm)==len(joined)==pack['samples'] and np.max(np.abs(joined))<1
        error=float(np.max(np.abs(pcm-joined)));assert error<=2**-23+1e-15;max_error=max(error,max_error)
    assert sha(ROOT/pack['outputs']['previous_liked_reference']['path'])==sha(AUTHOR/'delivery/baishuo_current165c_reference_vocal.wav')
    obs=load(RUN/'observations/results.json');assert obs['actual_F0_calls']==16 and len(obs['detector_bindings'])==16
    for row in obs['detector_bindings']:
        check([row['input'],row['output']])
        with np.load(ROOT/row['output']['path'],allow_pickle=False) as z:
            assert set(z.files)=={'f0_hz','times','voiced'}
            assert z['voiced'].dtype==np.bool_ and z['f0_hz'].dtype==z['times'].dtype==np.float32
            assert z['f0_hz'].shape==z['voiced'].shape==z['times'].shape
            assert np.isfinite(z['f0_hz']).all() and np.all(np.diff(z['times'])>0)
    rebuilt=0
    for w in obs['windows']:
        if not w['sample_indices']:continue
        a,b=w['sample_indices']
        for label in ['A','P','N','PN']:
            pcm,rate=sf.read(RUN/f'evaluation/PCM-contexts/context{w["context"]}-{label}.wav',dtype='float64')
            expected=float(np.sqrt(np.mean(pcm[a:b]**2)))
            assert expected==w['variants'][label]['level']['rms'];rebuilt+=1
        for comparison,v in w['comparisons'].items():
            new,old=comparison.split('-');a0,b0=[w['variants'][l]['level']['rms'] for l in [old,new]]
            expected=float(20*np.log10(b0/a0)) if a0 and b0 else None
            assert expected==v['RMS_ratio_db']
    for m in load(RUN/'observations/start.json')['models']:assert sha(Path(m['path']))==m['sha256']
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        max_PCM_quantization_error=max_error,old_author_A_score_and_nonprediction_inputs_exact=True,
        previous_liked_reference_bytes_exact=True,full_second_phrase_tail_included=True,DYN_absent_default0dB_unity=True,
        observed_F0_arrays=16,independently_rebuilt_RMS_values=rebuilt,agent_heard=False,measurement_validated=False))
    print('Independent author identity, PCM, F0 and level checks passed.',flush=True)


if __name__=='__main__':main()
