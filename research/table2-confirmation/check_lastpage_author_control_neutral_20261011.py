"""Independent group-neutral identity and exact native/fresh dependence gate."""
import copy
from pathlib import Path
import sys
import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise

RUN=ROOT/'runs/experiments/lastpage-author-control-neutral-20261011'
PRIOR=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
CHANNELS=['breathiness','voicing','tension']
NEUTRAL={'tenc':0,'brec':0,'voic':100,'shfc':0}


def native():
    plan=load(RUN/'design/protocol.json');check([plan['A'],plan['C']]+plan['model_adapters'])
    a,c=[yaml.safe_load((RUN/f'score/{l}.ustx').read_text(encoding='utf-8-sig')) for l in ['A','C']]
    d=copy.deepcopy(c)
    for k in NEUTRAL:
        orig=next(q for q in a['voice_parts'][0]['curves'] if q['abbr']==k);new=next(q for q in d['voice_parts'][0]['curves'] if q['abbr']==k)
        assert new['xs']==orig['xs'] and new['ys']==[NEUTRAL[k]]*len(orig['ys']);new['ys']=orig['ys'].copy()
    assert d==a
    rt=yaml.safe_load((RUN/'native-inputs/C-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    for k in NEUTRAL:
        assert next(q for q in rt['voice_parts'][0]['curves'] if q['abbr']==k)==next(q for q in c['voice_parts'][0]['curves'] if q['abbr']==k)
    assert load(RUN/'native-inputs/A-phones.json')['parts']==load(RUN/'native-inputs/C-phones.json')['parts']
    assert load(RUN/'native-inputs/A-pitch.json')['phrases']==load(RUN/'native-inputs/C-pitch.json')['phrases']
    rows=[]
    for ctx in [0,1]:
        fa,fc,va,vc=[load(RUN/f'native-inputs/{l}/{k}_{ctx:03}.json') for l,k in [('A','phrase'),('C','phrase'),('A','variance'),('C','variance')]]
        aa,cc,x,y=[tensors(q['tensors']) for q in [fa,fc,va,vc]]
        for k in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','vocoder_f0','tone_shift_cents','acoustic_model','vocoder_model','singer_location']:
            assert fa[k]==fc[k],(ctx,k)
        assert not np.any(fa['tone_shift_cents']) and not np.any(fc['tone_shift_cents'])
        assert x.keys()==y.keys() and all(np.array_equal(x[k],y[k]) for k in x), 'Variance feeds changed despite no SHFC intervention'
        assert aa.keys()==cc.keys() and all(np.array_equal(aa[k],cc[k]) for k in aa if k not in CHANNELS)
        assert fc['native_acoustic_cache_verified'] and vc['native_variance_cache_verified']
        removed={}
        for ch in CHANNELS:
            assert np.count_nonzero(fc['expression_deltas'][ch])==0 and np.count_nonzero(fa['expression_deltas'][ch])>0
            assert fa['native_variance_predictions'][ch]==fc['native_variance_predictions'][ch]
            removed[ch]=int(np.count_nonzero(fa['expression_deltas'][ch]))
            for f,inp in [(fa,aa),(fc,cc)]:
                raw=np.asarray(f['native_variance_predictions'][ch],np.float32)[None,:]+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                assert np.array_equal(inp[ch],np.clip(raw,*((-10,10) if ch=='tension' else (-96,0))))
        rows.append(dict(context=ctx,frames=aa['f0'].size,nonzero_manual_frames_removed=removed,
            native_variance_feeds_and_predictions_exact=True,phones_full_pitch_CLR_both_speakers_exact=True,
            actual_SHFC_intervened_frames=0,changed_acoustic_inputs=[k for k in aa if not np.array_equal(aa[k],cc[k])]))
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),measurement_validated=False))
    print('Independent three-active-channel group native check passed.',flush=True)


def read(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def fresh():
    rows=[]
    for ctx in [0,1]:
        values={}
        for l in ['A','C']:
            f=load(RUN/f'native-inputs/{l}/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/{l}/variance_{ctx:03}.json');rep=[]
            for suffix in ['', '_repeat']:
                d=RUN/f'fresh/context{ctx}/{l}{suffix}';x={k:read(d/(k+'.npz')) for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']};x['wave']=np.load(d/'raw.npy',allow_pickle=False)
                na,nv=tensors(f['tensors']),tensors(v['tensors']);n=na['f0'].size
                assert all(np.array_equal(x['inputs'][k],val) for k,val in na.items() if k not in CHANNELS)
                assert all(np.array_equal(x['variance-inputs'][k],val) for k,val in nv.items())
                assert np.array_equal(x['inputs']['probe_noise'],gaussian_frame_noise(101,1,128,n))
                assert np.array_equal(x['variance-inputs']['probe_noise'],gaussian_frame_noise(11,3,24,n))
                assert np.array_equal(x['vocoder-f0']['f0'],np.asarray(f['vocoder_f0'],np.float32)[None,:])
                clip={}
                for ch in CHANNELS:
                    lo,hi=(-10,10) if ch=='tension' else (-96,0);raw=x['predictions'][ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                    assert np.array_equal(x['inputs'][ch],np.clip(raw,lo,hi));clip[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)))
                assert len(x['wave'])==n*512 and x['wave'].dtype==np.float32 and np.isfinite(x['wave']).all()
                x['clip']=clip;rep.append(x)
            one,two=rep;assert np.array_equal(one['wave'],two['wave'])
            for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:assert all(np.array_equal(one[k][q],two[k][q]) for q in one[k])
            if l=='A':
                assert np.array_equal(one['wave'],np.load(PRIOR/f'fresh/context{ctx}/A/raw.npy',allow_pickle=False))
                for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:
                    old=read(PRIOR/f'fresh/context{ctx}/A/{k}.npz');assert all(np.array_equal(one[k][q],old[q]) for q in old)
            rows.append(dict(context=ctx,variant=l,feature_clipping=clip,repeat_exact=True,A_reproduced_previous_reference=l=='A'));values[l]=one
        a,c=values['A'],values['C']
        for k in ['variance-inputs','predictions','vocoder-f0']:assert all(np.array_equal(a[k][q],c[k][q]) for q in a[k])
        changed=[q for q in a['inputs'] if not np.array_equal(a['inputs'][q],c['inputs'][q])]
        assert set(changed)==set(CHANNELS)
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),waveforms=8,
        A_reproduced_previous_reference=True,variance_predictions_exact=True,only_three_manual_final_channels_changed=True,measurement_validated=False))
    print('Independent fresh A/repeats and group-only channel checks passed.',flush=True)


if __name__=='__main__':{'native':native,'fresh':fresh}[sys.argv[1]]()
