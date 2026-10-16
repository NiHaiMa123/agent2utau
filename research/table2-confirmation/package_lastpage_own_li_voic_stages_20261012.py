"""Package G with F controls and protected second-context real phones."""
from io import BytesIO
import json
import math
import shutil
import numpy as np
import soundfile as sf
import yaml
from lastpage_own_li_voic_stages_20261012 import ROOT,RUN,F,BASE,CURRENT,runtime
from assemble_lastpage_accepted_baseline_20261011 import load,save,ref,check

def main():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed' and not (RUN/'delivery').exists()
    sr=44100;n=load(CURRENT/'evaluation/assembly-check.json')['samples'];fsum=np.zeros(n,np.float64);gsum=fsum.copy();allowed=np.zeros(n,bool)
    parts=load(CURRENT/'design/phrase-ledger.json');contributions=[]
    (RUN/'dynamics').mkdir();(RUN/'evaluation/PCM-contexts').mkdir()
    score=yaml.safe_load((RUN/'score/native_G.ustx').read_text(encoding='utf-8'));assert score['expressions']['dyn']['default_value']==0
    for p in parts:
        ctx=p['context'];fw=gw=np.fromfile(ROOT/p['dynamic_wave_path'],dtype='<f4')
        if ctx in [28,29]:
            gain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ctx:03}.f32',dtype='<f4');assert np.all(gain==1)
            assert all(v==0 for c in score['voice_parts'][ctx-28]['curves'] if c['abbr']=='dyn' for v in c['ys'])
            fw=np.load(F/f'fresh/context{ctx}/F/raw.npy',allow_pickle=False)*gain;gw=fw
            if ctx==28:
                gw=np.load(RUN/'fresh/context28/G/raw.npy',allow_pickle=False)*gain;gw.tofile(RUN/'dynamics/context28-G.f32')
                assert np.max(np.abs(gw.astype(np.float64)*1.5))<1
                sf.write(RUN/'evaluation/PCM-contexts/context28-G.wav',gw.astype(np.float64)*1.5,sr,subtype='PCM_24')
            else:shutil.copyfile(F/'evaluation/PCM-contexts/context29-F.wav',RUN/'evaluation/PCM-contexts/context29-G.wav')
            shutil.copyfile(F/f'evaluation/PCM-contexts/context{ctx}-F.wav',RUN/f'evaluation/PCM-contexts/context{ctx}-F.wav')
        start=round(p['wave_start_s']*sr);lo=max(0,start);hi=min(n,start+len(gw))
        fsum[lo:hi]+=fw[lo-start:hi-start];gsum[lo:hi]+=gw[lo-start:hi-start];contributions.append((lo,hi,gw[lo-start:hi-start]))
        if ctx==28:allowed[lo:hi]=True
    reverse=np.zeros(n,np.float64)
    for lo,hi,x in reversed(contributions):reverse[lo:hi]+=x
    assert np.array_equal(reverse,gsum)
    old=load(F/'evaluation/delivery-check.json')['outputs'];check(list(old.values()));fpcm,_=sf.read(ROOT/old['candidate_full']['path'],dtype='int32')
    temp=BytesIO();sf.write(temp,fsum*1.5,sr,subtype='PCM_24',format='WAV');temp.seek(0)
    decoded,_=sf.read(temp,dtype='int32');assert np.array_equal(decoded,fpcm)
    d=RUN/'delivery';d.mkdir();full=d/'lastpage_own_li_voic_G_vocal.wav';peak=float(np.max(np.abs(gsum*1.5)));assert peak<1 and np.isfinite(gsum).all()
    sf.write(full,gsum*1.5,sr,subtype='PCM_24');gpcm,_=sf.read(full,dtype='int32');assert np.array_equal(gpcm[~allowed],fpcm[~allowed])
    p=parts[22];lo=round(p['wave_start_s']*sr);hi=lo+p['samples'];assert np.array_equal(gpcm[lo:hi],fpcm[lo:hi])
    p=parts[29];lo=round(p['wave_start_s']*sr);hi=lo+p['samples'];first=load(RUN/'native-inputs/G/phrase_001.json')['phones'][0]['positionMs']/1000
    real=math.ceil(first*sr);assert np.array_equal(gpcm[real:hi],fpcm[real:hi])
    shared=np.flatnonzero(gpcm[lo:hi]!=fpcm[lo:hi]);assert not len(shared) or lo+shared[-1]<real
    overlap=dict(context29_isolated_inputs_wave_exact=True,context29_all_real_phones_and_kan_PCM_exact=True,
        shared_padding_changed_samples=len(shared),first_real_phone_s=first,
        shared_change_s=[(lo+int(shared[0]))/sr,(lo+int(shared[-1]))/sr] if len(shared) else None,
        cause_scope='Original89ms context28 tail/context29 head overlap; no context29 independent change or retiming')
    lo,hi=[round(t*sr) for t in [209.4,218.0]];sf.write(d/'G_two_phrases.wav',gpcm[lo:hi],sr,subtype='PCM_24')
    preview,_=sf.read(d/'G_two_phrases.wav',dtype='int32');assert np.array_equal(preview,gpcm[lo:hi])
    shutil.copyfile(RUN/'score/lastpage_own_li_voic_G.ustx',d/'lastpage_own_li_voic_G.ustx')
    outputs=dict(candidate_preview=ref(d/'G_two_phrases.wav'),original_preview=old['candidate_preview'],author_reference=old['author_reference'],
        candidate_full=ref(full),candidate_project=ref(d/'lastpage_own_li_voic_G.ustx'))
    save(RUN/'evaluation/delivery-check.json',dict(outputs=outputs,peak=peak,fixed_gain=1.5,subtype='PCM_24',rate=sr,samples=n,duration_s=n/sr,
        outside_context28_contribution_exact=True,accepted_bao_C_PCM_exact=True,native_DYN_preserved=True,
        F_reconstruction_and_reverse_G_assembly_exact=True,preview_exact=True,overlap=overlap,
        F_and_author_sealed_reused=True,no_normalization_compression_or_BGM=True,agent_heard=False))
    runtime();print(json.dumps(dict(status='packaged',peak=peak,preview=outputs['candidate_preview'],overlap=overlap),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
