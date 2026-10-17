"""Package one frozen own voice candidate, retaining all sealed contributions."""
from io import BytesIO
import json
import shutil
import numpy as np
import soundfile as sf
import yaml
from lastpage_own_bright_cute_20261012 import ROOT,RUN,BASE,CURRENT,runtime
from assemble_lastpage_accepted_baseline_20261011 import load,save,ref

def main():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed'
    assert not (RUN/'delivery').exists()
    sr=44100;n=load(CURRENT/'evaluation/assembly-check.json')['samples']
    old_sum=np.zeros(n,np.float64);new_sum=old_sum.copy();allowed=np.zeros(n,bool)
    parts=load(CURRENT/'design/phrase-ledger.json');contributions=[]
    score=yaml.safe_load((RUN/'score/native_E.ustx').read_text(encoding='utf-8'))
    assert score['expressions']['dyn']['default_value']==0
    (RUN/'dynamics').mkdir();(RUN/'evaluation/PCM-contexts').mkdir()
    for p in parts:
        ctx=p['context'];old=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4');new=old
        if ctx in [28,29]:
            gain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ctx:03}.f32',dtype='<f4')
            assert np.all(gain==1) and gain.shape==old.shape
            assert all(y==0 for c in score['voice_parts'][ctx-28]['curves'] if c['abbr']=='dyn' for y in c['ys'])
            for label in ['A','E']:
                raw=np.load(RUN/f'fresh/context{ctx}/{label}/raw.npy',allow_pickle=False)
                dyn=raw*gain
                if label=='A':assert np.array_equal(dyn,old)
                else:new=dyn;new.tofile(RUN/f'dynamics/context{ctx}-E.f32')
                assert np.max(np.abs(dyn.astype(np.float64)*1.5))<1
                sf.write(RUN/f'evaluation/PCM-contexts/context{ctx}-{label}.wav',dyn.astype(np.float64)*1.5,sr,subtype='PCM_24')
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(n,start+len(new))
        old_sum[lo:hi]+=old[lo-start:hi-start];new_sum[lo:hi]+=new[lo-start:hi-start]
        contributions.append((lo,hi,new[lo-start:hi-start]))
        if ctx in [28,29]:allowed[lo:hi]=True
    reverse=np.zeros(n,np.float64)
    for lo,hi,x in reversed(contributions):reverse[lo:hi]+=x
    assert np.array_equal(new_sum,reverse)
    old_pcm,rate=sf.read(CURRENT/'delivery/lastpage_accepted_C_baseline_vocal.wav',dtype='int32');assert rate==sr
    temp=BytesIO();sf.write(temp,old_sum*1.5,sr,subtype='PCM_24',format='WAV');temp.seek(0)
    decoded,_=sf.read(temp,dtype='int32');assert np.array_equal(decoded,old_pcm)
    d=RUN/'delivery';d.mkdir();full=d/'lastpage_own_bright_cute_E_vocal.wav'
    peak=float(np.max(np.abs(new_sum*1.5)));assert peak<1 and np.isfinite(new_sum).all()
    sf.write(full,new_sum*1.5,sr,subtype='PCM_24');pcm,_=sf.read(full,dtype='int32')
    assert np.array_equal(pcm[~allowed],old_pcm[~allowed])
    p=parts[22];lo=round(p['wave_start_s']*sr);hi=lo+p['samples'];assert np.array_equal(pcm[lo:hi],old_pcm[lo:hi])
    lo,hi=[round(t*sr) for t in [209.4,218.0]]
    for label,data in [('A',old_pcm),('E',pcm)]:
        sf.write(d/f'{label}_two_phrases.wav',data[lo:hi],sr,subtype='PCM_24')
        reread,_=sf.read(d/f'{label}_two_phrases.wav',dtype='int32');assert np.array_equal(reread,data[lo:hi])
    shutil.copyfile(RUN/'score/lastpage_own_bright_cute_E.ustx',d/'lastpage_own_bright_cute_E.ustx')
    author=ROOT/'runs/experiments/lastpage-author-interaction-20261012/delivery/A_two_phrases.wav'
    outputs=dict(candidate_preview=ref(d/'E_two_phrases.wav'),original_preview=ref(d/'A_two_phrases.wav'),
        candidate_full=ref(full),candidate_project=ref(d/'lastpage_own_bright_cute_E.ustx'),author_reference=ref(author))
    save(RUN/'evaluation/delivery-check.json',dict(outputs=outputs,peak=peak,fixed_gain=1.5,subtype='PCM_24',
        rate=sr,samples=n,duration_s=n/sr,accepted_bao_C_PCM_exact=True,outside_context28_29_union_exact=True,
        baseline_and_reverse_assembly_exact=True,preview_exact=True,native_DYN_preserved=True,
        two_context_overlap='Both28/29 contributions change; natural89ms overlap preserved, isolated observations distinguished from mixed preview.',
        author_reference_scope='Separate existing fresh author A current1.65c, fixed11/101; own209.4–218.0 vs author212–220.5 clocks unchanged.',
        no_normalization_compression_or_BGM=True,agent_heard=False))
    runtime();print(json.dumps(dict(status='packaged',peak=peak,outputs=outputs),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
