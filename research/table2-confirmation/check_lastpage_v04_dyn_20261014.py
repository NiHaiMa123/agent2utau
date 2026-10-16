"""Independent DYN-only identity, polynomial, sample support and PCM checks."""
from io import BytesIO
import copy,math,sys
from pathlib import Path
import numpy as np
import soundfile as sf
import yaml
from review_lastpage_v03_volume_20261014 import ROOT,RUN,V03,BASE,load,save,ref,check
from agent2utau.openutau.ustx import TempoMap
from agent2utau.knowledge import check_plan_knowledge
from shfc_pcm_checks import dynamic_gain

def native():
    p=load(RUN/'design/protocol.json');_,receipt=check_plan_knowledge(p,RUN/'design/protocol.json');assert receipt==load(RUN/'evaluation/execution-knowledge-receipt.json')
    old=yaml.safe_load((ROOT/p['baseline'][0]['path']).read_text(encoding='utf8'));new=yaml.safe_load((ROOT/p['candidate']['path']).read_text(encoding='utf8'));restored=copy.deepcopy(new)
    tm=TempoMap.from_doc(new);traces=load(RUN/'design/compiled-DYN.json');dyn=load(RUN/'native-inputs/v04-dynamics.json')['phrases'];rows=[]
    rt=yaml.safe_load((RUN/'native-inputs/v04-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    for ctx in range(34):
        prior=old['voice_parts'][ctx];part=new['voice_parts'][ctx]
        assert part['curves']==rt['voice_parts'][ctx]['curves']
        if ctx in p['changed_contexts']:
            a=next(c for c in prior['curves'] if c['abbr']=='dyn');b=next(c for c in part['curves'] if c['abbr']=='dyn');assert a['xs']==b['xs']
            nodes=next(t for t in traces if t['context']==ctx)['UI_nodes_s'];expected=[]
            for tick in b['xs']:
                t=tm.tick_to_ms(part['position']+tick)/1000;y=0.
                for (lo,v0),(hi,v1) in zip(nodes,nodes[1:]):
                    if lo<=t<=hi:
                        u=(t-lo)/(hi-lo);q=6*u**5-15*u**4+10*u**3;y=(1-q)*v0+q*v1;break
                expected.append(int(np.rint(y)))
            assert expected==b['ys'],ctx
            next(c for c in restored['voice_parts'][ctx]['curves'] if c['abbr']=='dyn')['ys']=a['ys']
        ph=dyn[ctx];curve=next(c for c in part['curves'] if c['abbr']=='dyn');start=ph['position']-ph['leading'];expected=[]
        for i in range(len(ph['dynamics'])):
            tick=start+5*i-part['position'];ui=np.float32(np.interp(tick,curve['xs'],curve['ys']))
            expected.append(np.float32(0 if ui==new['expressions']['dyn']['min'] else math.pow(10,float(ui)*.1/20)))
        assert np.array_equal(np.asarray(expected),np.asarray(ph['dynamics'],np.float32)),ctx
        rows.append(dict(context=ctx,native_DYN_values_exact=True,changed=ctx in p['changed_contexts']))
    assert restored==old
    assert load(RUN/'native-inputs/v04-pitch.json')['phrases']==load(V03/'native-inputs/v03-pitch.json')['phrases']
    assert load(RUN/'native-inputs/v04-phones.json')['parts']==load(V03/'native-inputs/v03-phones.json')['parts']
    save(RUN/'evaluation/native-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),score_only_DYN_changed=True,
        current_notes_pitch_clock_phones_speaker_controls_exact=True,quintic_and_native_sampling_exact=True,rows=rows,new_model_calls=0))
    print('Native DYN-only identity/4 quintics/34 dynamic arrays exact.',flush=True)

def processed():
    doc=yaml.safe_load((RUN/'score/native_v04.ustx').read_text(encoding='utf8'));tm=TempoMap.from_doc(doc)
    dyn=load(RUN/'native-inputs/v04-dynamics.json')['phrases'];ledger=load(V03/'evaluation/assembly-check.json')['contributions'];rows=[]
    for p,ph in zip(ledger,dyn):
        ctx=p['context'];raw=np.load(V03/f'fresh/context{ctx:02}/v03/raw.npy',allow_pickle=False)
        gain=np.fromfile(RUN/f'dynamics/unity/phrase_{ctx:03}.f32',dtype='<f4');actual=np.fromfile(RUN/f'dynamics/raw/phrase_{ctx:03}.f32',dtype='<f4')
        f=load(V03/f'native-inputs/v03/phrase_{ctx:03}.json')
        start=ph['position']-ph['leading'];layout=dict(samples=len(raw),raw_origin_s=p['origin_s'],dynamic_curve=ph['dynamics'],
            position_ms=f['position_ms'],leading_ms=f['position_ms']-p['origin_s']*1000,dynamic_start_tick=start,
            dynamic_end_ms=[tm.tick_to_ms(start+5*(i+1)) for i in range(len(ph['dynamics']))])
        assert np.array_equal(gain,dynamic_gain(layout)),ctx
        assert np.array_equal(actual,raw*gain),ctx
        old=np.fromfile(V03/f'dynamics/raw/phrase_{ctx:03}.f32',dtype='<f4');indices=np.flatnonzero(actual!=old)
        if ctx in load(RUN/'design/protocol.json')['changed_contexts']:
            repeat=np.fromfile(RUN/f'dynamics/repeat/phrase_{ctx:03}.f32',dtype='<f4');assert np.array_equal(repeat,actual)
            nodes=next(t for t in load(RUN/'design/compiled-DYN.json') if t['context']==ctx)['UI_nodes_s']
            span=[p['origin_s']+indices[0]/44100,p['origin_s']+(indices[-1]+1)/44100]
            assert span[0]>=nodes[0][0]-.011 and span[1]<=nodes[-1][0]+.011,(ctx,span)
        else:assert np.array_equal(actual,old);span=None
        rows.append(dict(context=ctx,raw_current_reused_exact=True,gain_Core_independent_exact=True,changed_samples=len(indices),actual_change_span_s=span,
            gain_min=float(gain.min()),gain_max=float(gain.max()),repeat_exact=ctx in [11,22,23,25]))
    save(RUN/'evaluation/processed-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),rows=rows,new_variance_calls=0,new_acoustic_vocoder_waveforms=0))
    print('All34 Core gains/raw-times-gain exact;4 repetitions;30 contexts held.',flush=True)

def delivery():
    e=load(RUN/'evaluation/delivery-check.json');check(list(e['outputs'].values()))
    pcm,sr=sf.read(ROOT/e['outputs']['vocal']['path'],dtype='int32');old,_=sf.read(V03/'delivery/lastpage_J_method_whole_song_v03_vocal.wav',dtype='int32')
    n=len(pcm);expected=np.zeros(n,np.float64);allowed=np.zeros(n,bool)
    for p in load(V03/'evaluation/assembly-check.json')['contributions']:
        ctx=p['context'];w=np.fromfile(RUN/f'dynamics/raw/phrase_{ctx:03}.f32',dtype='<f4');oldw=np.fromfile(V03/f'dynamics/raw/phrase_{ctx:03}.f32',dtype='<f4')
        start=p['start_sample'];a=max(0,start);b=min(n,start+len(w));expected[a:b]+=w[a-start:b-start];allowed[a:b]|=w[a-start:b-start]!=oldw[a-start:b-start]
    temp=BytesIO();sf.write(temp,expected*1.5,sr,subtype='PCM_24',format='WAV');temp.seek(0);assert np.array_equal(pcm,sf.read(temp,dtype='int32')[0])
    assert np.array_equal(pcm[~allowed],old[~allowed]) and np.max(abs(expected*1.5))<1
    for row in e['AB_clips']:
        a,b=[round(t*sr) for t in row['interval_s']];x=sf.read(ROOT/row['A']['path'],dtype='int32')[0];y=sf.read(ROOT/row['B']['path'],dtype='int32')[0]
        assert np.array_equal(x,old[a:b]) and np.array_equal(y,pcm[a:b])
        pair=sf.read(ROOT/row['AB']['path'],dtype='int32')[0];assert np.array_equal(pair[:len(x)],x) and np.array_equal(pair[-len(y):],y)
    project=yaml.safe_load((ROOT/e['outputs']['project']['path']).read_text(encoding='utf8'));assert (ROOT/e['outputs']['project']['path']).read_bytes()==(RUN/'score/lastpage_J_method_volume_v04.ustx').read_bytes()
    obs=load(RUN/'observations/v04-volume-comparison.json');assert len(obs['words'])==318 and [w['word'] for w in obs['words'] if w['source_unknown']]==[106]
    save(RUN/'evaluation/delivery-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),full_PCM_reconstructed_exact=True,
        outside_native_sample_support_exact=True,AB_same_gain_and_native_DYN_exact=True,all318_vowel_records_present=True,source_unknown106_held=True,
        model_inputs_pitch_voice_and_phonation_unchanged=True,agent_heard=False,measurement_validated=False))
    print('Full PCM/unchanged support/3 AB crops/318 records passed.',flush=True)

if __name__=='__main__':{'native':native,'processed':processed,'delivery':delivery}[sys.argv[1]]()
