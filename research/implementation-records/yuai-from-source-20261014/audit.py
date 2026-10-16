"""Independent current native-input/whole-vowel audit; no repair selector."""
from source import ROOT,RUN,load,save,sha,ref
from pathlib import Path
import numpy as np,soundfile as sf,sys
from agent2utau.evaluation.controlled_probe import tensors

def rms(x):return float(np.sqrt(np.mean(np.asarray(x,dtype=np.float64)**2))) if len(x) else None
def db(x):return 20*np.log10(max(x,1e-9)) if x is not None else None
def windows(wave,sr,a,b,window):
    ts=np.arange(a+window/2,b-window/2+.00001,.005)
    return [dict(center_s=float(t),rms_db=float(db(rms(wave[round((t-window/2)*sr):round((t+window/2)*sr)])))) for t in ts]

def native(suffix='',wavepath=None):
    rows=[];total=0;clips=0;bound={};expected_voices={};start=load(RUN/'native-render/request.json')['start_unix']
    for i in range(61):
        ap=RUN/f'native-input/actual{suffix}/phrase_{i:03}.json';vp=RUN/f'native-input/actual{suffix}/variance_{i:03}.json';a=load(ap);v=load(vp);aa=tensors(a['tensors']);vv=tensors(v['tensors']);pred=tensors(v['cached_result']);frames=aa['f0'].size;total+=frames
        assert a['native_acoustic_cache_verified'] and v['native_variance_cache_verified'];assert a['frame_ms']==v['frame_ms'] and a['head_frames']==v['head_frames']
        for r,key in [(a,'singer_location'),(v,'variance_speaker_root')]:
            root=Path(r[key]);normal=root/'Yousa_Normal.emb';bright=root/'Yousa_Bright.emb'
            expected=np.float32(70*float(np.float32(.01)))*np.fromfile(normal,dtype='<f4')+np.float32(30*float(np.float32(.01)))*np.fromfile(bright,dtype='<f4')
            x=tensors(r['tensors'])['spk_embed'];assert np.array_equal(x,np.broadcast_to(expected,x.shape)),(i,key)
            for p in [normal,bright]:bound[str(p)]=sha(p)
        assert all(p['suffix']=='Yousa_Normal' for p in a['phones']);assert not np.any(np.asarray(a['tone_shift_cents']));assert not np.any(np.asarray(v['tone_shift_semitones']))
        assert np.array_equal(aa['f0'],np.asarray(a['vocoder_f0'],np.float32)[None,:]);assert np.max(abs(vv['pitch']-(69+12*np.log2(aa['f0']/440))))<.00002
        channel={}
        for k in ['breathiness','voicing','tension']:
            p=np.asarray(a['native_variance_predictions'][k],np.float32)[None,:];assert np.array_equal(p,pred[k+'_pred'])
            d=np.asarray(a['expression_deltas'][k],np.float32)[None,:];limits=(-10,10) if k=='tension' else (-96,0);assert np.array_equal(aa[k],np.clip(p+d,*limits));n=int(np.count_nonzero((p+d<limits[0])|(p+d>limits[1])));clips+=n
            if k!='tension':assert not np.any(d)
            channel[k]=dict(prediction_range=[float(p.min()),float(p.max())],delta_range=[float(d.min()),float(d.max())],final_range=[float(aa[k].min()),float(aa[k].max())],clipped_frames=n)
        dependencies=[Path(a['acoustic_model']),Path(a['vocoder_model']),Path(v['variance_model']),ap,vp]
        caches=[Path(a['native_acoustic_cache']),Path(v['native_variance_cache']),Path(v['native_linguistic_cache'])]
        for p in caches:assert p.is_relative_to(RUN/'native-runtime/Cache') and p.stat().st_mtime>=start-.1,(i,p)
        for p in dependencies+caches:bound[str(p)]=sha(p)
        rows.append(dict(phrase=i,frames=frames,two_stage_speaker_exact=True,phone_suffix='Yousa_Normal',unshifted_F0_exact=True,
            current_fresh_cache_only=True,channels=channel))
    # All raw waveform caches were created by this production's native render.
    wavs=list((RUN/'native-runtime/Cache').glob('*.wav'));assert len(wavs)>=61
    for p in wavs:assert p.stat().st_mtime>=start-.1;bound[str(p)]=sha(p)
    save(RUN/f'evaluation/native-dependency-audit{suffix}.json',dict(status='passed',phrases=rows,frames=total,feature_clip_count=clips,
        whole_wave=ref(wavepath or RUN/'native-render/native_vocal.wav'),native_randomness='Current native models use RandomNormalLike; no old seed adapter or historical prediction read; frozen newly-created outputs bound',
        current_fresh_variance_acoustic_vocoder_contexts=61,current_run_native_wav_caches=len(wavs),bindings=bound,Agent_listened=False))
    print('61 actual contexts verified,',total,'frames; clip count',clips,flush=True)

def energy(stage='raw',wavepath=None,wordpath=None):
    path=Path(wavepath) if wavepath else RUN/'native-render/native_vocal.wav';wave,sr=sf.read(path,dtype='float32');wave=wave.mean(axis=1) if wave.ndim>1 else wave
    words=load(wordpath or RUN/'design/native-word-decisions.json');ledger={w['word']:w for w in load(RUN/'design/word-ledger.json')};rows=[]
    for w in words:
        a,b=w['native_nucleus_s'];dur=b-a;x=wave[round(a*sr):round(b*sr)];n=len(x);third=[db(rms(q)) for q in np.array_split(x,3)]
        win={str(ms):windows(wave,sr,a,b,ms/1000) for ms in [30,50]}
        # Narrow windows are merely a review queue. They never choose gain.
        queue={k:min((q['rms_db'] for q in z),default=None) for k,z in win.items()}
        r=ledger[w['word']];rows.append(dict(word=w['word'],char=w['char'],line=w['line'],role=r['role'],final=r['final'],nucleus_s=[a,b],duration_s=dur,
            whole_rms_db=db(rms(x)),early_mid_late_db=third,windows=win,minimum_window_db=queue,
            action='pending Agent musical review' if stage=='raw' else 'checked against selected finite native envelope',listener_truth=False))
    save(RUN/f'evaluation/whole-vowel-energy-{stage}.json',dict(wave=ref(path),sample_rate=sr,word_count=len(rows),words=rows,voiced_short_window_not_audible_truth=True))
    for w in sorted(rows,key=lambda r:r['whole_rms_db'])[:35]:print(w['word'],w['char'],'line',w['line'],round(w['duration_s'],3),round(w['whole_rms_db'],2),[round(x,1) for x in w['early_mid_late_db']],w['role'],w['final'],flush=True)
    return rows

if __name__=='__main__':{'native':native,'energy':energy}[sys.argv[1]]()
