"""New two-stage synthesis from actual current native inputs, no old song data."""
from lastpage_fresh_expression_20261007 import *
def tensors(items):return {q['name']:np.asarray(q['values'],dtype=q['dtype']).reshape(q['shape']) for q in items}

def feeds():
    guarded();bridge('render',['--project',str(OUT/'lastpage_fresh.ustx'),'--out',str(OUT/'native_full.wav'),'--mixdown','--timeout','13'],'native_render')
    bridge('export-render-probe',['--project',str(OUT/'lastpage_fresh.ustx'),'--out',str(OUT/'feeds'),'--indices',','.join(map(str,range(34)))],'native_feeds_export')
    print('NEW_NATIVE_FEEDS_READY',flush=True)

def adapter(src,dest,channels,bins):
    import onnx
    m=onnx.load(str(src));original=[x.SerializeToString() for x in m.graph.initializer]
    r=[x for x in m.graph.node if x.op_type=='RandomNormalLike'];assert len(r)==1
    n=r[0];n.op_type='Identity';del n.input[:];n.input.append('probe_noise');del n.attribute[:]
    m.graph.input.append(onnx.helper.make_tensor_value_info('probe_noise',onnx.TensorProto.FLOAT,[1,channels,bins,'n_frames']))
    onnx.checker.check_model(m);assert original==[x.SerializeToString() for x in m.graph.initializer];onnx.save(m,str(dest))
    return dict(source=str(src),source_sha256=sha(src),adapter_sha256=sha(dest),initializer_weights_exact=True)

def synthesize():
    guarded();import onnxruntime as ort
    from agent2utau.expression.variance_expectation import gaussian_frame_noise,CHANNELS
    f=read(OUT/'feeds/phrase_000.json');v0=read(OUT/'feeds/variance_000.json');md=OUT/'models';md.mkdir(exist_ok=True)
    manifests=[adapter(v0['variance_model'],md/'variance.onnx',3,24),adapter(f['acoustic_model'],md/'acoustic.onnx',1,128)];dump('model_adapter_manifest.json',manifests)
    opts=ort.SessionOptions();opts.intra_op_num_threads=opts.inter_op_num_threads=1
    vs,ac,vc=[ort.InferenceSession(str(p),sess_options=opts,providers=['CPUExecutionProvider']) for p in [md/'variance.onnx',md/'acoustic.onnx',f['vocoder_model']]]
    names=[q.name for q in vs.get_outputs()];pd=OUT/'synthesis';pd.mkdir(exist_ok=True);checks=[]
    for i in range(34):
        rec=read(OUT/f'feeds/phrase_{i:03}.json');vr=read(OUT/f'feeds/variance_{i:03}.json');b=tensors(rec['tensors']);v=tensors(vr['tensors']);cached=tensors(vr['cached_result']);nf=b['f0'].size
        assert rec['native_acoustic_cache_verified'] and vr['native_variance_cache_verified'];assert b['durations'].sum()==nf
        embederrs=[]
        for ts,root in [(b,Path(rec['singer_location'])),(v,Path(vr['variance_speaker_root']))]:
            expected=.75*np.fromfile(root/'Yousa_Normal.emb',dtype='<f4')+.25*np.fromfile(root/'Yousa_Classic.emb',dtype='<f4')
            er=float(np.max(abs(ts['spk_embed']-expected[None,None,:])));embederrs.append(er);assert er<1e-6
        wave=pd/f'phrase_{i:03}.npy';meta=wave.with_suffix('.json');binding=dict(acoustic_feed=sha(OUT/f'feeds/phrase_{i:03}.json'),variance_feed=sha(OUT/f'feeds/variance_{i:03}.json'),variance_seed=11,acoustic_seed=101)
        if wave.exists():
            ch=read(meta);assert ch['inputs']==binding and sha(wave)==ch['wave_sha256'];checks.append(ch);continue
        v['probe_noise']=gaussian_frame_noise(11,3,24,nf);pred=dict(zip(names,vs.run(names,v)));deltas={}
        for k in CHANNELS:
            lo,hi=(-10,10) if k=='tension' else (-96,0);delta=np.asarray(rec['expression_deltas'][k],np.float32)[None,:]
            assert np.array_equal(np.clip(cached[k+'_pred']+delta,lo,hi).astype(np.float32),b[k]),(i,k,'native arithmetic')
            b[k]=np.clip(pred[k+'_pred']+delta,lo,hi).astype(np.float32);deltas[k]=delta
        b['probe_noise']=gaussian_frame_noise(101,1,128,nf);mel=ac.run(['mel'],b)[0]
        if rec['acoustic_mel_base']!=rec['vocoder_mel_base']:mel*=np.log(10) if rec['acoustic_mel_base']=='10' else 1/np.log(10)
        w=vc.run(None,dict(mel=mel,f0=np.asarray(rec['vocoder_f0'],np.float32)[None,:]))[0].reshape(-1);assert np.isfinite(w).all();np.save(wave,w)
        np.savez_compressed(pd/f'state_{i:03}.npz',**{k:pred[k+'_pred'] for k in CHANNELS},**{'final_'+k:b[k] for k in CHANNELS},**{'delta_'+k:deltas[k] for k in CHANNELS})
        ch=dict(index=i,inputs=binding,wave_sha256=sha(wave),samples=len(w),frames=nf,speaker_both_stages={'Normal':75,'Classic':25},speaker_max_errors=embederrs,wave_start_s=(rec['position_ms']-rec['head_frames']*rec['frame_ms'])/1000)
        dump('synthesis/'+meta.name,ch);checks.append(ch);print(f'Fresh current two-stage synthesis {i+1}/34',flush=True)
    dump('synthesis_check.json',dict(phrases=checks,all_fresh=True,old_song_states=False,models={str(p):sha(p) for p in [Path(f['acoustic_model']),Path(v0['variance_model']),Path(f['vocoder_model'])]}))

if __name__=='__main__':globals()[sys.argv[1]]()
