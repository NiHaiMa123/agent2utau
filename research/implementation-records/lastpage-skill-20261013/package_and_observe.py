"""Native dynamics, fixed-gain complete delivery and independent observations."""
from io import BytesIO
import csv,json,math,sys,shutil
from pathlib import Path
import numpy as np
import soundfile as sf
from apply_whole_song import ROOT,RUN,BASE,CURRENT,J,resources,call
from assemble_lastpage_accepted_baseline_20261011 import load,save,ref,check
from agent2utau.resources.config import load_config

def dynamics():
    assert load(RUN/'evaluation/fresh-independent-check.json')['status']=='passed';resources()
    manifests={'raw':[],'unity':[]};ledger=load(CURRENT/'design/phrase-ledger.json');e=load(RUN/'fresh/execution.json')
    for ctx in range(34):
        f=load(RUN/f'native-inputs/v03/phrase_{ctx:03}.json');old=ledger[ctx];w=np.load(RUN/f'fresh/context{ctx:02}/v03/raw.npy',allow_pickle=False)
        row=next(r for r in e['rows'] if r['context']==ctx and r['variant']=='v03')
        assert abs(row['wave_start_s']-old['wave_start_s'])<1e-6 and len(w)==old['samples']
        clock=dict(phrase=ctx,position_ms=f['position_ms'],leading_ms=f['position_ms']-old['wave_start_s']*1000)
        for label,x in [('raw',w),('unity',np.ones_like(w))]:
            p=RUN/f'dynamics-inputs/{label}_{ctx:03}.f32';assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);x.astype('<f4').tofile(p)
            manifests[label].append(dict(**clock,input_f32=str(p)))
    for label,rows in manifests.items():
        mf=RUN/f'design/dynamics-{label}-manifest.json';save(mf,rows)
        call('apply-'+label,['apply-dynamics','--project',str(RUN/'score/native_v03.ustx'),'--manifest',str(mf),'--out',str(RUN/f'dynamics/{label}')],Path(load_config()['openutau_dir'])/'a2u-levelprobe-v15.exe')
    print('Core native DYN applied to34 new raw contributions and34 unity probes.',flush=True)

def package():
    assert not (RUN/'delivery').exists();resources();sr=44100
    n=load(CURRENT/'evaluation/assembly-check.json')['samples'];total=np.zeros(n,np.float64);pieces=[];rows=[]
    ledger=load(CURRENT/'design/phrase-ledger.json');dyn=load(RUN/'native-inputs/v03-dynamics.json')['phrases']
    for ctx in range(34):
        raw=np.load(RUN/f'fresh/context{ctx:02}/v03/raw.npy',allow_pickle=False)
        wave=np.fromfile(RUN/f'dynamics/raw/phrase_{ctx:03}.f32',dtype='<f4');gain=np.fromfile(RUN/f'dynamics/unity/phrase_{ctx:03}.f32',dtype='<f4')
        assert np.array_equal(wave,raw*gain) and len(wave)==ledger[ctx]['samples']
        oldgain=np.fromfile(BASE/f'native_dynamics_ones/phrase_{ctx:03}.f32',dtype='<f4')
        assert np.array_equal(gain,oldgain),(ctx,'native DYN preserved')
        if ctx in [22,28,29]:
            old=(ROOT/ledger[22]['dynamic_wave_path']) if ctx==22 else (J/'dynamics/context28-J.f32') if ctx==28 else (ROOT/'runs/experiments/lastpage-own-control-neutral-20261012/fresh/context29/F/raw.npy')
            target=np.load(old,allow_pickle=False) if ctx==29 else np.fromfile(old,dtype='<f4')
            assert np.array_equal(wave,target),(ctx,'accepted contribution')
        start=round(ledger[ctx]['wave_start_s']*sr);lo=max(0,start);hi=min(n,start+len(wave));piece=wave[lo-start:hi-start]
        total[lo:hi]+=piece;pieces.append((lo,hi,piece));rows.append(dict(context=ctx,origin_s=ledger[ctx]['wave_start_s'],
            native_frame_origin_s=next(r for r in load(RUN/'fresh/execution.json')['rows'] if r['context']==ctx and r['variant']=='v03')['wave_start_s'],
            samples=len(wave),start_sample=start,dynamic_gain_min=float(gain.min()),dynamic_gain_max=float(gain.max()),
            waveform=ref(RUN/f'dynamics/raw/phrase_{ctx:03}.f32'),accepted_contribution_exact=ctx in [22,28,29]))
    reverse=np.zeros_like(total)
    for lo,hi,piece in reversed(pieces):reverse[lo:hi]+=piece
    assert np.array_equal(reverse,total)
    fixed=1.5;peak=float(np.max(abs(total*fixed)));assert peak<1 and np.isfinite(total).all(),peak
    delivery=RUN/'delivery';delivery.mkdir();full=delivery/'lastpage_J_method_whole_song_v03_vocal.wav'
    sf.write(full,total*fixed,sr,subtype='PCM_24');pcm,rate=sf.read(full,dtype='int32');assert rate==sr and len(pcm)==n
    original,_=sf.read(J/'delivery/lastpage_own_li_entry_pitch_J_vocal.wav',dtype='int32')
    # Boundary paddings from neighbouring changed contributions can affect a few samples.
    # Compare actual accepted phones, not an unbounded claim about full context overlaps.
    accepted=[]
    geom=load(BASE/'native_word_geometry.json');dec=load(BASE/'agent_word_decisions.json')
    for ctx in [22,28,29]:
        ids=[d['word'] for d in dec if d['context']==ctx]
        for word in ids:
            g=geom[word];a=math.ceil(g['phones'][0]['start_ms']/1000*sr);b=math.floor(g['phones'][-1]['end_ms']/1000*sr)
            accepted.append(dict(context=ctx,word=word,char=g['char'],actual_phone_PCM_exact=bool(np.array_equal(pcm[a:b],original[a:b]))))
    # Accepted contributions remain exact; changed neighbouring padding is separate.
    a,b=[round(t*sr) for t in [209.4,218.0]]
    changed=np.flatnonzero(pcm[a:b]!=original[a:b])
    sf.write(delivery/'J_context_in_v03.wav',pcm[a:b],sr,subtype='PCM_24')
    assert np.array_equal(sf.read(delivery/'J_context_in_v03.wav',dtype='int32')[0],pcm[a:b])
    shutil.copyfile(J/'delivery/J_two_phrases.wav',delivery/'accepted_J_reference.wav')
    assert sf.read(delivery/'accepted_J_reference.wav',dtype='int32')[0].shape==pcm[a:b].shape
    project=delivery/'lastpage_J_method_whole_song_v03.ustx';shutil.copyfile(RUN/'score/lastpage_J_method_whole_song_v03.ustx',project)
    published=ROOT/'projects/latest/lastpage_J_method_whole_song_v03.ustx';assert not published.exists();shutil.copyfile(project,published)
    spans=[('verse1',13.5,40.5),('chorus1',71.4,99.1),('verse2',127.0,153.6),('chorus2',182.0,208.8),('final_chorus',209.4,237.0)]
    clips=[]
    for label,t0,t1 in spans:
        a,b=round(t0*sr),round(t1*sr);p=delivery/(label+'.wav');sf.write(p,pcm[a:b],sr,subtype='PCM_24')
        assert np.array_equal(sf.read(p,dtype='int32')[0],pcm[a:b]);clips.append(dict(label=label,start_s=t0,end_s=t1,audio=ref(p)))
    save(RUN/'evaluation/assembly-check.json',dict(status='passed',samples=n,sr=sr,duration_s=n/sr,peak=peak,
        fixed_vocal_gain=fixed,subtype='PCM_24',finite_no_fullscale_clipping=True,reverse_assembly_exact=True,
        all_native_DYN_exact=True,accepted_J_raw_contexts_exact=True,accepted_J_reference_exact=True,
        new_full_J_preview_exact_to_old=not len(changed),new_J_preview_changed_samples=len(changed),
        new_J_preview_change_span_s=[(a+int(changed[0]))/sr,(a+int(changed[-1]))/sr] if len(changed) else None,
        change_reason='Changed neighbouring contexts27/30 can contribute within previous J crop; J context28/29 independent waveforms exact',accepted_real_phone_windows=accepted,
        accepted_bao_raw_context_exact=True,neighbour_padding_may_change=True,contributions=rows,clips=clips,
        outputs=dict(full_vocal=ref(full),project=ref(project),published=ref(published)),no_BGM_change=True,agent_heard=False))
    print('Packaged complete245.577s PCM24 vocal,peak',peak,';J contributions exact, neighbour-padding changed samples',len(changed),flush=True)

def observe():
    from agent2utau.analysis.f0 import extract_f0
    from agent2utau.analysis.rmvpe import infer_rmvpe
    import torch
    torch.set_num_threads(1)
    full=RUN/'delivery/lastpage_J_method_whole_song_v03_vocal.wav';f0={}
    for label,fn in [('FCPE',lambda:extract_f0(full)),('RMVPE',lambda:infer_rmvpe(full,Path(load_config()['openutau_dir'])/'Dependencies/rmvpe/rmvpe.onnx'))]:
        print('Whole-song F0',label,flush=True);result=fn();f0[label]=result
        save(RUN/f'observations/{label}-metadata.json',{k:v for k,v in result.items() if not isinstance(v,np.ndarray)})
        np.savez_compressed(RUN/f'observations/{label}.npz',**{k:v for k,v in result.items() if isinstance(v,np.ndarray)})
    pcm,sr=sf.read(full,dtype='float64');old,_=sf.read(J/'delivery/lastpage_own_li_entry_pitch_J_vocal.wav',dtype='float64')
    pitch=load(RUN/'native-inputs/v03-pitch.json')['phrases'];geom=load(BASE/'native_word_geometry.json');dec=load(BASE/'agent_word_decisions.json');words=[]
    def level(x):
        return dict(rms_dbfs=float(20*np.log10(max(np.sqrt(np.mean(x*x)),1e-12))),peak=float(np.max(abs(x))))
    for g,d in zip(geom,dec):
        a,b=g['native_vowel'];newlevel=level(pcm[math.ceil(a*sr):math.floor(b*sr)]);oldlevel=level(old[math.ceil(a*sr):math.floor(b*sr)])
        q=pitch[d['context']];ts=np.asarray(q['times_ms'])/1000;cent=np.asarray(q['final_cents']);summary={}
        for label,z in f0.items():
            m=(z['times']>=a)&(z['times']<b)&z['voiced']&(z['f0_hz']>0);time=z['times'][m]
            y=6900+1200*np.log2(z['f0_hz'][m]/440);diff=y-np.interp(time,ts,cent)
            summary[label]=dict(voiced_frames=int(m.sum()),median_abs_target_error_cents=float(np.median(abs(diff))) if len(diff) else None,
                p95_abs_target_error_cents=float(np.percentile(abs(diff),95)) if len(diff) else None)
        words.append(dict(word=g['word'],char=g['char'],context=d['context'],source_unknown=d['source_unknown'],
            native_vowel=[a,b],v03_level=newlevel,old_J_carrier_level=oldlevel,
            level_delta_db=newlevel['rms_dbfs']-oldlevel['rms_dbfs'],F0=summary,auditory_quality='unknown unless exact prior accepted J scope',
            level_does_not_measure_force_or_texture=True))
    save(RUN/'observations/word-metrics.json',dict(audio=ref(full),new_F0_calls=2,words=words,
        F0_are_finite_proxies=True,source_unknowns_retained=True,agent_heard=False,measurement_validated=False,general_rule_validated=False))
    with (RUN/'observations/word-metrics.csv').open('x',encoding='utf-8-sig',newline='') as f:
        rows=[dict(word=w['word'],char=w['char'],context=w['context'],source_unknown=w['source_unknown'],
            rms_dbfs=w['v03_level']['rms_dbfs'],level_delta_db=w['level_delta_db'],
            FCPE_median_abs_error_c=w['F0']['FCPE']['median_abs_target_error_cents'],RMVPE_median_abs_error_c=w['F0']['RMVPE']['median_abs_target_error_cents'],new_listening_label='unknown') for w in words]
        c=csv.DictWriter(f,fieldnames=list(rows[0]));c.writeheader();c.writerows(rows)
    print('Whole-song two F0 observations and318 vowel level/error records completed; listening unknown.',flush=True)

if __name__=='__main__':{'dynamics':dynamics,'package':package,'observe':observe}[sys.argv[1]]()
