"""Independently reconstruct explicit polynomial targets and full native feeds."""
import copy,math,sys
from pathlib import Path
import numpy as np
import yaml
from apply_whole_song import ROOT,RUN,J,BASE,CURRENT,CHANNELS,COLORS
from assemble_lastpage_accepted_baseline_20261011 import load,save,ref
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from agent2utau.openutau.ustx import TempoMap
from agent2utau.knowledge import check_plan_knowledge
from check_lastpage_own_bright_cute_20261012 import native_mix
from check_lastpage_own_li_entry_pitch_20261013 import reconstruct_frames,phone_identity

def polynomial(t,nodes):
    for (a,y0,d0),(b,y1,d1) in zip(nodes,nodes[1:]):
        if a<=t<=b:
            h=b-a;u=(t-a)/h
            return (((2*(y0-y1)+h*(d0+d1))*u+3*(y1-y0)-h*(2*d0+d1))*u+h*d0)*u+y0
    raise ValueError(t)

def native():
    plan=load(RUN/'design/protocol.json');_,receipt=check_plan_knowledge(plan,RUN/'design/protocol.json')
    assert receipt==load(RUN/'evaluation/knowledge_receipt.json')
    base=yaml.safe_load((J/'delivery/lastpage_own_li_entry_pitch_J.ustx').read_text(encoding='utf8'))
    doc=yaml.safe_load((RUN/'score/lastpage_J_method_whole_song_v03.ustx').read_text(encoding='utf8'))
    actual=load(RUN/'native-inputs/v03-pitch.json')['phrases'];prior=load(BASE/'delivery_native_pitch.json')['phrases']
    j=load(J/'native-inputs/J-pitch.json')['phrases'];prior[28:30]=j
    assert len(actual)==len(doc['voice_parts'])==34
    assert phone_identity(load(RUN/'native-inputs/v03-phones.json'))==phone_identity(load(BASE/'delivery_native_phones.json'))
    assert doc['voice_parts'][22]==base['voice_parts'][22]
    assert doc['voice_parts'][28:30]==base['voice_parts'][28:30]
    gestures=load(RUN/'design/pitch-gestures.json');rows=[];maxerr=0;tm=TempoMap.from_doc(doc)
    for ctx,(p,q,a,b) in enumerate(zip(base['voice_parts'],doc['voice_parts'],prior,actual)):
        assert p['notes']==q['notes'] and p['position']==q['position']
        assert [x for x in p['curves'] if x['abbr']=='dyn']==[x for x in q['curves'] if x['abbr']=='dyn']
        for key in a:
            if key!='final_cents':assert a[key]==b[key],(ctx,key)
        curve=next(c for c in q['curves'] if c['abbr']=='pitd');old=next(c for c in p['curves'] if c['abbr']=='pitd');assert curve['xs']==old['xs']
        local=[g for g in gestures if g['context']==ctx];mask=np.zeros(len(curve['ys']),bool)
        for i,x in enumerate(curve['xs']):
            t=tm.tick_to_ms(q['position']+x)/1000
            g=next((g for g in local if g['support_s'][0]<=t<=g['support_s'][1]),None)
            if g:
                expected=polynomial(t,g['center_nodes']);value=int(np.rint(expected-a['before_pitd_cents'][i]))
                assert curve['ys'][i]==value;(err:=abs(b['final_cents'][i]-expected));assert err<=.501;maxerr=max(maxerr,err);mask[i]=True
            else:assert curve['ys'][i]==old['ys'][i]
        assert np.array_equal(np.asarray(a['final_cents'])[~mask],np.asarray(b['final_cents'])[~mask])
        f=load(RUN/f'native-inputs/v03/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/v03/variance_{ctx:03}.json');ac,va=tensors(f['tensors']),tensors(v['tensors'])
        assert f['native_acoustic_cache_verified'] and v['native_variance_cache_verified']
        for r,x,key in [(f,ac,'singer_location'),(v,va,'variance_speaker_root')]:
            mix,weights=native_mix(Path(r[key]),'A' if ctx==22 else 'E',f['phones'])
            assert np.array_equal(x['spk_embed'],np.broadcast_to(mix,x['spk_embed'].shape)),(ctx,key)
        pitch,f0,clocks=reconstruct_frames(doc,b,f)
        assert np.array_equal(np.asarray(f['vocoder_f0'],np.float32),f0),(ctx,'vocoder F0')
        if ctx!=22:
            assert np.array_equal(va['pitch'],pitch[None,:]) and np.array_equal(ac['f0'],f0[None,:]),ctx
            assert all(np.count_nonzero(f['expression_deltas'][ch])==0 for ch in CHANNELS),ctx
            assert np.count_nonzero(f['tone_shift_cents'])==0,ctx
        else:
            oldf=load(ROOT/'runs/lastpage_shfc_onset_probe_20261008/native_C/phrase_022.json')
            oldv=load(ROOT/'runs/lastpage_shfc_onset_probe_20261008/native_C/variance_022.json')
            oldac,oldva=tensors(oldf['tensors']),tensors(oldv['tensors'])
            assert all(np.array_equal(va[k],oldva[k]) for k in va),('bao variance input',ctx)
            assert all(np.array_equal(ac[k],oldac[k]) for k in ac if k not in CHANNELS),('bao acoustic input',ctx)
            assert f['expression_deltas']==oldf['expression_deltas'] and f['tone_shift_cents']==oldf['tone_shift_cents']
        assert len(f['vocoder_f0'])==ac['f0'].size
        rows.append(dict(context=ctx,changed_pitch_grid_points=int(np.count_nonzero(np.asarray(a['final_cents'])!=b['final_cents'])),
            planned_pitch_support_points=int(mask.sum()),both_speaker_exact=True,phone_clock_exact=True,pitch_inputs_rebuilt=True,
            manual_controls_neutral=ctx!=22,bao_old_inputs_exact=ctx==22,frames=ac['f0'].size))
    save(RUN/'evaluation/native-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),rows=rows,
        words_reviewed=len(load(RUN/'design/word-decisions.json')),native_max_error_cents=maxerr,
        accepted_J_contexts_exact=True,accepted_bao_context_exact=True,measurement_validated=False))
    print('Native gate passed:34 clocks/both speaker feeds;15 target polynomials; J/bao exact.',flush=True)

def read(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}

def fresh():
    rows=[];e=load(RUN/'fresh/execution.json');assert e['variance_calls']==e['acoustic_vocoder_waveforms']==37
    for ctx in range(34):
        f=load(RUN/f'native-inputs/v03/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/v03/variance_{ctx:03}.json');ac,va=tensors(f['tensors']),tensors(v['tensors'])
        d=RUN/f'fresh/context{ctx:02}/v03';saved={k:read(d/(k+'.npz')) for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']};wave=np.load(d/'raw.npy',allow_pickle=False)
        assert all(np.array_equal(saved['variance-inputs'][k],va[k]) for k in va)
        assert all(np.array_equal(saved['inputs'][k],ac[k]) for k in ac if k not in CHANNELS)
        assert np.array_equal(saved['variance-inputs']['probe_noise'],gaussian_frame_noise(11,3,24,ac['f0'].size))
        assert np.array_equal(saved['inputs']['probe_noise'],gaussian_frame_noise(101,1,128,ac['f0'].size))
        assert np.array_equal(saved['vocoder-f0']['f0'],np.asarray(f['vocoder_f0'],np.float32)[None,:])
        clipping={}
        for ch in CHANNELS:
            lo,hi=(-10,10) if ch=='tension' else (-96,0);raw=saved['predictions'][ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
            assert np.array_equal(saved['inputs'][ch],np.clip(raw,lo,hi));clipping[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)))
        repeat=False
        if ctx in [0,22,28]:
            r=RUN/f'fresh/context{ctx:02}/repeat';assert np.array_equal(wave,np.load(r/'raw.npy',allow_pickle=False))
            for k,x in saved.items():
                other=read(r/(k+'.npz'));assert x.keys()==other.keys() and all(np.array_equal(x[key],other[key]) for key in x)
            repeat=True
        accepted=False
        if ctx in [22,28,29]:
            old=(ROOT/'runs/lastpage_shfc_onset_probe_20261008/fresh/B.npy') if ctx==22 else (J/'fresh/context28/J/raw.npy') if ctx==28 else (ROOT/'runs/experiments/lastpage-own-control-neutral-20261012/fresh/context29/F/raw.npy')
            assert np.array_equal(wave,np.load(old,allow_pickle=False)),('accepted PCM',ctx);accepted=True
        assert wave.dtype==np.float32 and np.isfinite(wave).all() and len(wave)==ac['f0'].size*512
        rows.append(dict(context=ctx,feature_clipping=clipping,repeat_exact=repeat,accepted_raw_exact=accepted,
            predicted_features_median={ch:float(np.median(saved['inputs'][ch])) for ch in CHANNELS}))
    save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),rows=rows,
        actual_fresh_waveforms=37,all_inputs_current=True,agent_heard=False,measurement_validated=False,general_rule_validated=False))
    print('Fresh gate passed:37 waveforms,current dependencies,3 repeats and3 accepted raw contexts exact.',flush=True)

def delivery():
    from io import BytesIO
    import soundfile as sf
    pack=load(RUN/'evaluation/assembly-check.json');mix=load(RUN/'evaluation/mix-check.json');sr=44100;n=pack['samples']
    out=np.zeros(n,np.float64)
    for p in reversed(pack['contributions']):
        w=np.fromfile(ROOT/p['waveform']['path'],dtype='<f4');start=p['start_sample'];a=max(0,start);b=min(n,start+len(w));out[a:b]+=w[a-start:b-start]
    probe=BytesIO();sf.write(probe,out*1.5,sr,subtype='PCM_24',format='WAV');probe.seek(0)
    expected=sf.read(probe,dtype='int32')[0];actual,s=sf.read(ROOT/pack['outputs']['full_vocal']['path'],dtype='int32')
    assert s==sr and np.array_equal(actual,expected)
    full,rate=sf.read(ROOT/pack['outputs']['full_vocal']['path'],dtype='float64',always_2d=True)
    backing,bsr=sf.read(ROOT/mix['delivery_backing']['path'],dtype='float64',always_2d=True)
    pre=np.repeat(full,2,axis=1)+backing;common=.9;post=pre*common
    assert rate==bsr==sr and np.max(abs(post))<1
    assert float(np.max(abs(pre)))==mix['unattenuated_mix_peak'] and np.count_nonzero(abs(pre)>=1)==8
    # audio.mix uses two multiplication terms; reconstruct its actual operation order.
    factor=10**(mix['common_margin_db']/20);post=np.repeat(full,2,axis=1)*factor+backing*factor
    probe=BytesIO();sf.write(probe,post,sr,subtype='PCM_24',format='WAV');probe.seek(0)
    assert np.array_equal(sf.read(probe,dtype='int32')[0],sf.read(ROOT/mix['output']['path'],dtype='int32')[0])
    old=yaml.safe_load((RUN/'delivery/lastpage_J_method_whole_song_v03.ustx').read_text(encoding='utf8'))
    play=yaml.safe_load((ROOT/mix['playback_project']['path']).read_text(encoding='utf8'));restored=copy.deepcopy(play)
    for a,b in zip(restored['tracks'],old['tracks']):a['volume']=b['volume']
    assert restored==old
    assert all(abs((a['volume']-b['volume'])-mix['common_margin_db'])<1e-12 for a,b in zip(play['tracks'],old['tracks']))
    for p in [ROOT/mix['playback_project']['path'],ROOT/mix['published_playback_project']['path']]:
        assert (p.parent/play['wave_parts'][0]['relative_path']).read_bytes()==(ROOT/mix['original_backing']['path']).read_bytes()
    observations=load(RUN/'observations/word-metrics.json');assert len(observations['words'])==318
    assert [w['word'] for w in observations['words'] if w['source_unknown']]==[106]
    for name in ['FCPE','RMVPE']:
        z=read(RUN/f'observations/{name}.npz');assert len(z['times'])==len(z['f0_hz'])==len(z['voiced'])
        assert np.isfinite(z['times']).all() and np.isfinite(z['f0_hz']).all()
    save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        full_vocal_PCM_reconstructed_exact=True,constant_mix_PCM_reconstructed_exact=True,
        playback_score_only_equal_track_margin=True,backing_loadable_from_both_new_projects=True,
        all318_records_and_source_unknown_preserved=True,new_auditory_acceptance=False,agent_heard=False))
    print('Independent delivery gate passed:full PCM,mix,playback score/backing,318 records/unknown.',flush=True)

if __name__=='__main__':{'native':native,'fresh':fresh,'delivery':delivery}[sys.argv[1]]()
