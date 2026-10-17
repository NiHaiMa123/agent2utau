"""Assemble F and independently reused E with retained sealed song contributions."""
from io import BytesIO
import json
import shutil
import numpy as np
import soundfile as sf
import yaml
from lastpage_own_control_neutral_20261012 import ROOT,RUN,E,BASE,CURRENT,runtime
from assemble_lastpage_accepted_baseline_20261011 import load,save,ref,check

def main():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed' and not (RUN/'delivery').exists()
    sr=44100;n=load(CURRENT/'evaluation/assembly-check.json')['samples']
    esum=np.zeros(n,np.float64);fsum=esum.copy();allowed=np.zeros(n,bool);contributions=[]
    score=yaml.safe_load((RUN/'score/native_F.ustx').read_text(encoding='utf-8'));assert score['expressions']['dyn']['default_value']==0
    (RUN/'dynamics').mkdir();(RUN/'evaluation/PCM-contexts').mkdir()
    parts=load(CURRENT/'design/phrase-ledger.json')
    for p in parts:
        ctx=p['context'];ew=fw=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4')
        if ctx in [28,29]:
            gain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ctx:03}.f32',dtype='<f4');assert np.all(gain==1) and len(gain)==p['samples']
            assert all(y==0 for c in score['voice_parts'][ctx-28]['curves'] if c['abbr']=='dyn' for y in c['ys'])
            ew=np.load(E/f'fresh/context{ctx}/E/raw.npy',allow_pickle=False)*gain
            assert np.array_equal(ew,np.fromfile(E/f'dynamics/context{ctx}-E.f32',dtype='<f4'))
            fw=np.load(RUN/f'fresh/context{ctx}/F/raw.npy',allow_pickle=False)*gain;fw.tofile(RUN/f'dynamics/context{ctx}-F.f32')
            assert np.isfinite(fw).all() and np.max(np.abs(fw.astype(np.float64)*1.5))<1
            sf.write(RUN/f'evaluation/PCM-contexts/context{ctx}-F.wav',fw.astype(np.float64)*1.5,sr,subtype='PCM_24')
            shutil.copyfile(E/f'evaluation/PCM-contexts/context{ctx}-E.wav',RUN/f'evaluation/PCM-contexts/context{ctx}-E.wav')
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(n,start+len(fw))
        esum[lo:hi]+=ew[lo-start:hi-start];fsum[lo:hi]+=fw[lo-start:hi-start];contributions.append((lo,hi,fw[lo-start:hi-start]))
        if ctx in [28,29]:allowed[lo:hi]=True
    reverse=np.zeros(n,np.float64)
    for lo,hi,x in reversed(contributions):reverse[lo:hi]+=x
    assert np.array_equal(reverse,fsum)
    oldoutputs=load(E/'evaluation/delivery-check.json')['outputs'];check(list(oldoutputs.values()))
    epcm,rate=sf.read(ROOT/oldoutputs['candidate_full']['path'],dtype='int32');assert rate==sr
    temp=BytesIO();sf.write(temp,esum*1.5,sr,subtype='PCM_24',format='WAV');temp.seek(0)
    decoded,_=sf.read(temp,dtype='int32');assert np.array_equal(decoded,epcm)
    d=RUN/'delivery';d.mkdir();full=d/'lastpage_own_control_neutral_F_vocal.wav'
    peak=float(np.max(np.abs(fsum*1.5)));assert peak<1 and np.isfinite(fsum).all()
    sf.write(full,fsum*1.5,sr,subtype='PCM_24');fpcm,_=sf.read(full,dtype='int32')
    assert np.array_equal(fpcm[~allowed],epcm[~allowed])
    p=parts[22];lo=round(p['wave_start_s']*sr);hi=lo+p['samples'];assert np.array_equal(fpcm[lo:hi],epcm[lo:hi])
    lo,hi=[round(t*sr) for t in [209.4,218.0]]
    sf.write(d/'F_two_phrases.wav',fpcm[lo:hi],sr,subtype='PCM_24');preview,_=sf.read(d/'F_two_phrases.wav',dtype='int32');assert np.array_equal(preview,fpcm[lo:hi])
    shutil.copyfile(RUN/'score/lastpage_own_control_neutral_F.ustx',d/'lastpage_own_control_neutral_F.ustx')
    outputs=dict(candidate_preview=ref(d/'F_two_phrases.wav'),original_preview=oldoutputs['candidate_preview'],
        own_A_preview=oldoutputs['original_preview'],author_reference=oldoutputs['author_reference'],
        candidate_full=ref(full),candidate_project=ref(d/'lastpage_own_control_neutral_F.ustx'))
    save(RUN/'evaluation/delivery-check.json',dict(outputs=outputs,peak=peak,fixed_gain=1.5,subtype='PCM_24',rate=sr,samples=n,duration_s=n/sr,
        outside_context28_29_union_exact=True,accepted_bao_C_PCM_exact=True,native_DYN_preserved=True,
        E_baseline_and_reverse_F_assembly_exact=True,preview_exact=True,
        two_context_overlap='Both28/29 contributions change; original89ms overlap preserved, isolated metrics vs mixed preview distinguished.',
        E_original_preview_raw_and_PCM_reused=True,no_normalization_compression_or_BGM=True,agent_heard=False))
    runtime();print(json.dumps(dict(status='packaged',peak=peak,preview=outputs['candidate_preview']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
