"""Independent fourth-corner native and fresh dependency reconstruction."""
import copy
from pathlib import Path
import sys
import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise

RUN=ROOT/'runs/experiments/lastpage-author-interaction-20261012'
CONTROL=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
VOICE=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
CHANNELS=['breathiness','voicing','tension']
COLORS=['cl01','cl02','cl03','cl04','cl05']


def native():
    plan=load(RUN/'design/protocol.json');check([plan['D']]+list(plan['existing_scores'].values())+plan['model_adapters'])
    c=yaml.safe_load((CONTROL/'score/C.ustx').read_text(encoding='utf-8-sig'));d=yaml.safe_load((RUN/'score/D.ustx').read_text(encoding='utf-8-sig'))
    stripped=copy.deepcopy(d)
    for k,v in zip(COLORS,[0,0,75,0,25]):
        actual=next(q for q in d['voice_parts'][0]['curves'] if q['abbr']==k)
        assert actual['ys']==[v,v]
        old=next(q for q in c['voice_parts'][0]['curves'] if q['abbr']==k)
        replace=next(q for q in stripped['voice_parts'][0]['curves'] if q['abbr']==k);replace.clear();replace.update(old)
    assert stripped==c
    rt=yaml.safe_load((RUN/'native-inputs/D-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    for k in COLORS+['tenc','brec','voic','shfc']:
        assert next(q for q in rt['voice_parts'][0]['curves'] if q['abbr']==k)==next(q for q in d['voice_parts'][0]['curves'] if q['abbr']==k)
    for kind,key in [('phones','parts'),('pitch','phrases')]:
        target=load(RUN/f'native-inputs/D-{kind}.json')[key]
        for folder,l in [(CONTROL,'A'),(CONTROL,'C'),(VOICE,'B')]:assert target==load(folder/f'native-inputs/{l}-{kind}.json')[key]
    rows=[]
    for ctx in [0,1]:
        fd,vd=[load(RUN/f'native-inputs/D/{k}_{ctx:03}.json') for k in ['phrase','variance']]
        fc,vc=[load(CONTROL/f'native-inputs/C/{k}_{ctx:03}.json') for k in ['phrase','variance']]
        fb,vb=[load(VOICE/f'native-inputs/B/{k}_{ctx:03}.json') for k in ['phrase','variance']]
        ac,av=tensors(fd['tensors']),tensors(vd['tensors']);bc,bv=tensors(fb['tensors']),tensors(vb['tensors']);cc,cv=tensors(fc['tensors']),tensors(vc['tensors'])
        assert fd['native_acoustic_cache_verified'] and vd['native_variance_cache_verified']
        assert av.keys()==bv.keys()==cv.keys() and ac.keys()==bc.keys()==cc.keys()
        assert all(np.array_equal(av[k],bv[k]) for k in av)
        assert all(np.array_equal(av[k],cv[k]) for k in av if k!='spk_embed')
        for key in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','vocoder_f0','tone_shift_cents','acoustic_model','vocoder_model','singer_location']:
            assert fd[key]==fb[key]==fc[key],(ctx,key)
        assert all(np.array_equal(ac[k],bc[k]) for k in ac if k not in CHANNELS)
        assert all(np.array_equal(ac[k],cc[k]) for k in ac if k not in ['spk_embed',*CHANNELS])
        for record,inp,key in [(fd,ac,'singer_location'),(vd,av,'variance_speaker_root')]:
            root=Path(record[key]);mix=.75*np.fromfile(root/'Yousa_Normal.emb',dtype='<f4')+.25*np.fromfile(root/'Yousa_Classic.emb',dtype='<f4')
            assert np.array_equal(inp['spk_embed'],np.broadcast_to(mix,inp['spk_embed'].shape))
        for ch in CHANNELS:
            assert fd['expression_deltas'][ch]==fc['expression_deltas'][ch] and not np.any(fd['expression_deltas'][ch])
            assert fd['native_variance_predictions'][ch]==fb['native_variance_predictions'][ch]
            pred=np.asarray(fd['native_variance_predictions'][ch],np.float32)[None,:]
            assert np.array_equal(ac[ch],np.clip(pred,*((-10,10) if ch=='tension' else (-96,0))))
        rows.append(dict(context=ctx,frames=ac['f0'].size,D_variance_and_native_predictions_exact_B=True,
            D_manual_deltas_zero_exact_C=True,D_two_stage_speaker_exact_Normal75_Classic25=True,phones_full_pitch_F0_exact_all_corners=True))
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),measurement_validated=False))
    print('Independent native fourth-corner conditions passed.',flush=True)


def read(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def fresh():
    rows=[]
    for ctx in [0,1]:
        f=load(RUN/f'native-inputs/D/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/D/variance_{ctx:03}.json')
        values=[]
        for label in ['D','D_repeat']:
            folder=RUN/f'fresh/context{ctx}/{label}';data={k:read(folder/(k+'.npz')) for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']};data['wave']=np.load(folder/'raw.npy',allow_pickle=False)
            n=tensors(f['tensors'])['f0'].size;vin=tensors(v['tensors']);ac=tensors(f['tensors']);clipping={}
            assert all(np.array_equal(data['variance-inputs'][k],value) for k,value in vin.items())
            assert all(np.array_equal(data['inputs'][k],value) for k,value in ac.items() if k not in CHANNELS)
            assert np.array_equal(data['inputs']['probe_noise'],gaussian_frame_noise(101,1,128,n))
            assert np.array_equal(data['variance-inputs']['probe_noise'],gaussian_frame_noise(11,3,24,n))
            old_var=read(VOICE/f'fresh/context{ctx}/B/variance-inputs.npz');old_pred=read(VOICE/f'fresh/context{ctx}/B/predictions.npz')
            assert all(np.array_equal(data['variance-inputs'][k],old_var[k]) for k in old_var)
            assert all(np.array_equal(data['predictions'][k],old_pred[k]) for k in old_pred)
            for ch in CHANNELS:
                lo,hi=(-10,10) if ch=='tension' else (-96,0);pred=data['predictions'][ch+'_pred'];assert not np.any(f['expression_deltas'][ch])
                assert np.array_equal(data['inputs'][ch],np.clip(pred,lo,hi));clipping[ch]=int(np.count_nonzero((pred<lo)|(pred>hi)))
            assert np.array_equal(data['vocoder-f0']['f0'],np.asarray(f['vocoder_f0'],np.float32)[None,:])
            assert data['wave'].dtype==np.float32 and len(data['wave'])==n*512 and np.isfinite(data['wave']).all();values.append(data)
        a,b=values;assert np.array_equal(a['wave'],b['wave'])
        for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:assert all(np.array_equal(a[k][q],b[k][q]) for q in a[k])
        old_B=read(VOICE/f'fresh/context{ctx}/B/inputs.npz');old_C=read(CONTROL/f'fresh/context{ctx}/C/inputs.npz')
        changed_B=[k for k in old_B if not np.array_equal(a['inputs'][k],old_B[k])];changed_C=[k for k in old_C if not np.array_equal(a['inputs'][k],old_C[k])]
        assert set(changed_B)==set(CHANNELS) and set(changed_C).issubset({'spk_embed',*CHANNELS}) and 'spk_embed' in changed_C
        rows.append(dict(context=ctx,frames=n,feature_clipping=clipping,D_repeated_inputs_predictions_mel_vocoder_PCM_exact=True,
            D_fresh_variance_predictions_exact_B=True,changed_vs_B=changed_B,changed_vs_C=changed_C))
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),new_waveforms=4,independent_contexts=2,measurement_validated=False))
    print('Independent fresh D repeats and B/C dependencies passed.',flush=True)


if __name__=='__main__':{'native':native,'fresh':fresh}[sys.argv[1]]()
