"""Assemble native-DYN-only full-song and equal-gain voice AB deliveries."""
from io import BytesIO
import json,math,shutil,sys
from pathlib import Path
import numpy as np
import soundfile as sf
from review_lastpage_v03_volume_20261014 import ROOT,RUN,V03,BASE,load,save,ref,sha

def short_windows(x,sr,span,ms):
    a,b=span;duration=b-a;length=ms/1000;starts=np.arange(length/2,duration-length/2+.0000001,.005)
    if not len(starts):return dict(count=0,status='too short')
    begin=round(a*sr);end=round(b*sr);v=x[begin:end];mid=np.round(starts*sr).astype(int);half=round(length*sr/2)
    good=(mid-half>=0)&(mid+half<=len(v));mid=mid[good];times=starts[good]+a;cs=np.r_[0.,np.cumsum(v*v,dtype=np.float64)]
    db=10*np.log10(np.maximum((cs[mid+half]-cs[mid-half])/(2*half),1e-24))
    return dict(count=len(db),p10_dbfs=float(np.percentile(db,10)),median_dbfs=float(np.median(db)),p90_dbfs=float(np.percentile(db,90)),
        min_dbfs=float(db.min()),min_center_s=float(times[db.argmin()]),range_p90_p10_db=float(np.percentile(db,90)-np.percentile(db,10)))

def main():
    assert load(RUN/'evaluation/processed-independent-check.json')['status']=='passed';assert not (RUN/'delivery').exists()
    baseline,sr=sf.read(V03/'delivery/lastpage_J_method_whole_song_v03_vocal.wav',dtype='int32');n=len(baseline);sumwave=np.zeros(n,np.float64);allowed=np.zeros(n,bool)
    for p in load(V03/'evaluation/assembly-check.json')['contributions']:
        ctx=p['context'];new=np.fromfile(RUN/f'dynamics/raw/phrase_{ctx:03}.f32',dtype='<f4');old=np.fromfile(V03/f'dynamics/raw/phrase_{ctx:03}.f32',dtype='<f4')
        start=p['start_sample'];a=max(0,start);b=min(n,start+len(new));sumwave[a:b]+=new[a-start:b-start];allowed[a:b]|=new[a-start:b-start]!=old[a-start:b-start]
    result=sumwave*1.5;assert np.isfinite(result).all() and np.max(abs(result))<1
    out=RUN/'delivery';out.mkdir();full=out/'lastpage_J_method_volume_v04_vocal.wav';sf.write(full,result,sr,subtype='PCM_24')
    pcm,_=sf.read(full,dtype='int32');assert np.array_equal(pcm[~allowed],baseline[~allowed])
    clips=[]
    for label,span in [('01_ru_guo',[85.6,89.4]),('02_emotional_chorus',[181.9,190.9]),('03_ru_guo',[195.6,199.8])]:
        a,b=[round(t*sr) for t in span];A=out/(label+'_A_v03.wav');B=out/(label+'_B_v04.wav');pair=out/(label+'_A_then_B.wav')
        sf.write(A,baseline[a:b],sr,subtype='PCM_24');sf.write(B,pcm[a:b],sr,subtype='PCM_24')
        combined=np.r_[baseline[a:b],np.zeros(round(.5*sr),np.int32),pcm[a:b]];sf.write(pair,combined,sr,subtype='PCM_24')
        clips.append(dict(label=label,interval_s=span,A=ref(A),B=ref(B),AB=ref(pair),order='A v03,0.5s silence,B v04',gain=1.5,normalization=False))
    project=out/'lastpage_J_method_volume_v04.ustx';shutil.copyfile(RUN/'score/lastpage_J_method_volume_v04.ustx',project)
    # Playback backing is unchanged. This is dependency/peak validation, not BGM analysis.
    backingname='lastpage_loudness_v02_backing.wav';backing=out/backingname;shutil.copyfile(V03/'delivery'/backingname,backing)
    published=ROOT/'projects/latest'/project.name;assert not published.exists();shutil.copyfile(project,published)
    assert sha(ROOT/'projects/latest'/backingname)==sha(backing)
    from agent2utau.audio.mix import mix
    mixed=out/'lastpage_J_method_volume_v04_mix.wav';db=20*math.log10(.9)
    mixing=mix(full,backing,mixed,vocal_gain_db=db,accomp_gain_db=db)
    old=sf.read(V03/'delivery/lastpage_J_method_whole_song_v03_vocal.wav',dtype='float64')[0];new=sf.read(full,dtype='float64')[0]
    review=load(RUN/'observations/envelope-review.json')['words'];rows=[]
    for w in review:
        a,b=w['native_vowel'];lo,hi=round(a*sr),round(b*sr);x=new[lo:hi];y=old[lo:hi]
        def rms(v):return float(20*np.log10(max(np.sqrt(np.mean(v*v)),1e-12)))
        oldlevel,newlevel=rms(y),rms(x)
        A={str(ms):short_windows(old,sr,[a,b],ms) for ms in [30,50]};B={str(ms):short_windows(new,sr,[a,b],ms) for ms in [30,50]}
        rows.append(dict(word=w['word'],char=w['char'],context=w['context'],source_unknown=w['source_unknown'],native_vowel=[a,b],
            in_feedback_interval=w['in_feedback_interval'],old_rms_dbfs=oldlevel,new_rms_dbfs=newlevel,rms_delta_db=newlevel-oldlevel,
            A_windows=A,B_windows=B,A_thirds=w['thirds_rms_dbfs'],B_thirds=[rms(v) for v in np.array_split(x,3)],
            current_features=w['actual_features'],features_reused_exact=True,interpretation='Output amplitude only; force/texture acceptance unknown',
            new_auditory_label='pending' if np.any(x!=y) else 'no new label; PCM held'))
    save(RUN/'observations/v04-volume-comparison.json',dict(words=rows,all318_observed=True,new_model_calls=0,new_F0_calls=0,
        old_v03_F0='source-bound reference only; not rerun or claimed identical detector output',BGM_relation_analysis=False,
        agent_heard=False,measurement_validated=False,general_rule_validated=False))
    changed=np.flatnonzero(pcm!=baseline)
    save(RUN/'evaluation/delivery-check.json',dict(status='packaged_pending_listening',outputs=dict(vocal=ref(full),project=ref(project),published=ref(published),mix=ref(mixed),backing=ref(backing)),
        AB_clips=clips,peak=float(np.max(abs(result))),fixed_vocal_gain=1.5,common_mix_margin=.9,mix_peak=mixing['peak'],
        samples=n,sr=sr,subtype='PCM_24',duration_s=n/sr,changed_PCM_samples=len(changed),outside_native_support_exact=True,
        original_backing_bytes_exact=True,no_new_models_or_variance=True,agent_heard=False,full_song_accepted=False))
    for w in rows:
        if w['in_feedback_interval']:print(w['word'],w['char'],'RMS change',round(w['rms_delta_db'],3),flush=True)
    print('Full v04 vocal/USTX and3 same-gain voice A→B pairs packaged;peak',float(np.max(abs(result))),flush=True)

if __name__=='__main__':main()
