"""Fixed-gain current-song audio, editable and frozen playback delivery."""
from source import ROOT,RUN,load,save,sha,ref
from design import cfg
import yaml,numpy as np,soundfile as sf,shutil,copy,sys,math
from agent2utau.openutau.bridge import run_bridge

def package():
    out=RUN/'delivery';out.mkdir();raw,sr=sf.read(RUN/'final-stage/native-level/native_vocal.wav',dtype='float64');backing,bs=sf.read(RUN/'inputs/source_backing.wav',dtype='float64',always_2d=True)
    assert sr==bs==44100 and backing.shape[1]==2 and len(raw)<len(backing)
    voice=np.zeros(len(backing),np.float64);voice[:len(raw)]=raw*2.0;pre=backing+voice[:,None];peak=float(np.max(abs(pre)));common=min(1.0,.93/peak);mix=pre*common
    assert np.max(abs(voice))<1 and np.max(abs(mix))<1
    sf.write(out/'yuai_source_only_v01_vocal.wav',voice,sr,subtype='PCM_24');sf.write(out/'yuai_source_only_v01_mix.wav',mix,sr,subtype='PCM_24');shutil.copyfile(RUN/'inputs/source_backing.wav',out/'backing.wav');assert sha(out/'backing.wav')==sha(RUN/'inputs/source_backing.wav')
    doc=yaml.safe_load((RUN/'final-stage/compiled-level/project.ustx').read_text(encoding='utf8'));doc['name']='雨爱 / 从源数据独立制作 v01';doc['cache_dir']='UCache';doc['comment']='New source-only production. Singing track uses native functions/DYN. Fixed vocal gain2; original backing1; one shared mix headroom. Agent has not listened.'
    doc['tracks'][0]['track_name']='雨爱 / independent vocal';doc['tracks'][0]['volume']=20*math.log10(2*common)
    bt=copy.deepcopy(doc['tracks'][0]);bt.update(singer='',phonemizer='',renderer_settings={},track_name='雨爱 / source backing',volume=20*math.log10(common),mute=False,solo=False);doc['tracks'].append(bt)
    duration=round(len(backing)/sr*960)
    def wavepart(name,track,path):return dict(name=name,comment='',track_no=track,position=0,duration=duration,relative_path=path,file_duration_ms=len(backing)/sr*1000,skip_ms=0,trim_ms=0)
    doc['wave_parts']=[wavepart('source backing',1,'backing.wav')]
    engineering=out/'yuai_source_only_v01.ustx';engineering.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=10**6),encoding='utf8')
    playback=copy.deepcopy(doc);playback['name']='雨爱 / 从源制作 v01 / frozen playback';playback['tracks'][0]['mute']=True
    vt=copy.deepcopy(bt);vt.update(track_name='雨爱 / current generated vocal playback',volume=20*math.log10(common));playback['tracks'].append(vt);playback['wave_parts'].append(wavepart('current generated vocal',2,'yuai_source_only_v01_vocal.wav'))
    playable=out/'yuai_source_only_v01_playback.ustx';playable.write_text(yaml.safe_dump(playback,allow_unicode=True,sort_keys=False,width=10**6),encoding='utf8')
    latest=ROOT/'projects/latest';latest.mkdir(exist_ok=True)
    for name,d in [('yuai_source_only_v01.ustx',doc),('yuai_source_only_v01_playback.ustx',playback)]:
        p=latest/name;assert not p.exists();d=copy.deepcopy(d)
        for wp in d['wave_parts']:wp['relative_path']='../../runs/production/yuai-from-source-20261014/delivery/'+wp['relative_path']
        p.write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=10**6),encoding='utf8')
    for p in [engineering,playable,latest/'yuai_source_only_v01.ustx',latest/'yuai_source_only_v01_playback.ustx']:
        r=run_bridge(cfg(),['inspect','--project',str(p)]);save(RUN/f'evaluation/{p.parent.name}-{p.stem}-inspect.json',r);assert r['ok'] and all(w['loaded'] for w in r['wave_parts']),r
        assert sum(v['notes'] for v in r['voice_parts'])==440 and sum(v['renderPhrases'] for v in r['voice_parts'])==61
    audio={}
    for name in ['yuai_source_only_v01_vocal.wav','yuai_source_only_v01_mix.wav','backing.wav']:
        p=out/name;x,s=sf.read(p,dtype='float64',always_2d=True);assert s==sr and len(x)==len(backing) and np.isfinite(x).all() and np.max(abs(x))<1
        audio[name]=dict(file=ref(p),sample_rate=s,samples=len(x),channels=x.shape[1],duration_s=len(x)/s,subtype=sf.info(p).subtype,peak=float(np.max(abs(x))),full_scale_samples=int(np.count_nonzero(abs(x)>=1)))
    # WAV24 encoding bound; source backing remains exact original bytes.
    decoded,s=sf.read(out/'yuai_source_only_v01_mix.wav',dtype='float64',always_2d=True);assert np.max(abs(decoded-mix))<=2**-23
    save(out/'delivery-manifest.json',dict(status='rendered_checked_pending_human_listening',audio=audio,source_allowlist=ref(RUN/'inputs/allowed-source-manifest.json'),
        editable_project=ref(engineering),playback_project=ref(playable),source_key=True,original_clock=True,vocal_gain=2.0,backing_gain=1.0,common_mix_headroom=common,
        mix_formula='common*(2*native_Core_DYN_vocal+source_backing)',no_per_word_normalization=True,native_intermediate_subtype=sf.info(RUN/'final-stage/native-level/native_vocal.wav').subtype,
        native_intermediate_precision_note='OpenUtau RenderToFiles current output is PCM16; delivery PCM24 does not restore this quantization.',
        generated_now_only=True,author_and_historical_production_data_used=False,Agent_listened=False,naturalness_accepted=False))
    print('Delivery:',len(backing)/sr,'s; voice peak',audio['yuai_source_only_v01_vocal.wav']['peak'],'mix peak',audio['yuai_source_only_v01_mix.wav']['peak'],'shared headroom',common,flush=True)

def f0():
    import torch
    torch.set_num_threads(1)
    from agent2utau.analysis.f0 import extract_f0
    from agent2utau.analysis.rmvpe import infer_rmvpe
    source=RUN/'delivery/yuai_source_only_v01_vocal.wav';out=RUN/'evaluation/final-F0';out.mkdir()
    for name,fn in [('FCPE',lambda:extract_f0(source)),('RMVPE',lambda:infer_rmvpe(source,RUN/'native-runtime/Dependencies/rmvpe/rmvpe.onnx'))]:
        print('Fresh final',name,flush=True);r=fn();save(out/f'{name}-metadata.json',{k:v for k,v in r.items() if not isinstance(v,np.ndarray)});np.savez_compressed(out/f'{name}.npz',**{k:v for k,v in r.items() if isinstance(v,np.ndarray)})
    words=load(RUN/'design/native-word-decisions-breath-final.json');native=load(RUN/'final-stage/compiled-level/pitch.json')['phrases'];rows=[]
    zs=[np.load(out/f'{name}.npz') for name in ['FCPE','RMVPE']]
    for w in words:
        a,b=w['native_nucleus_s'];ph=next(p for p in native if p['times_ms'][0]/1000<=a<=p['times_ms'][-1]/1000);metrics={}
        for name,z in zip(['FCPE','RMVPE'],zs):
            mask=(z['times']>=a+.065)&(z['times']<=b-.055)&z['voiced']&(z['f0_hz']>0);ts=z['times'][mask];measured=6900+1200*np.log2(z['f0_hz'][mask]/440);target=np.interp(ts,np.asarray(ph['times_ms'])/1000,ph['final_cents']);delta=measured-target
            metrics[name]=dict(frames=len(ts),median_delta_c=float(np.median(delta)) if len(ts) else None,p95_absolute_delta_c=float(np.percentile(abs(delta),95)) if len(ts) else None,
                unknown='too short/no detection' if len(ts)<4 else 'detector and phonation/timing errors remain; finite observation, not hearing')
        rows.append(dict(word=w['word'],char=w['char'],nucleus_s=[a,b],metrics=metrics))
    save(out/'audit.json',dict(source=ref(source),fresh_calls=2,words=rows,measurement_validated=False,naturalness_truth=False,Agent_listened=False))
    print('371 final F0 observations recorded',flush=True)

if __name__=='__main__':{'package':package,'f0':f0}[sys.argv[1]]()
