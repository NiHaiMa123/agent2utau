"""Independent author-to-own speaker identity and exact dependency checks."""
import copy
from pathlib import Path
import sys

import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise

RUN=ROOT/'runs/experiments/lastpage-author-voice-swap-20261011'
PRIOR=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011'
CHANNELS=['breathiness','voicing','tension']
COLORS=['cl01','cl02','cl03','cl04','cl05']


def without_colors(doc):
    d=copy.deepcopy(doc);d['voice_parts'][0]['curves']=[c for c in d['voice_parts'][0]['curves'] if c['abbr'] not in COLORS];return d


def native():
    plan=load(RUN/'design/protocol.json');check([plan['A'],plan['B']]+plan['model_adapters'])
    a,b=[yaml.safe_load((RUN/f'score/{l}.ustx').read_text(encoding='utf-8-sig')) for l in ['A','B']]
    assert without_colors(a)==without_colors(b)
    roundtrip=yaml.safe_load((RUN/'native-inputs/B-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    for k,v in zip(COLORS,[0,0,75,0,25]):
        c=next(c for c in b['voice_parts'][0]['curves'] if c['abbr']==k)
        assert c['ys']==[v,v] and c==next(c for c in roundtrip['voice_parts'][0]['curves'] if c['abbr']==k)
    assert load(RUN/'native-inputs/A-phones.json')['parts']==load(RUN/'native-inputs/B-phones.json')['parts']
    assert load(RUN/'native-inputs/A-pitch.json')['phrases']==load(RUN/'native-inputs/B-pitch.json')['phrases']
    rows=[]
    for ctx in [0,1]:
        fa,fb,va,vb=[load(RUN/f'native-inputs/{l}/{kind}_{ctx:03}.json') for l,kind in [('A','phrase'),('B','phrase'),('A','variance'),('B','variance')]]
        for k in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','expression_deltas','vocoder_f0','tone_shift_cents',
            'acoustic_model','vocoder_model','singer_location']:assert fa[k]==fb[k],(ctx,k)
        assert fb['native_acoustic_cache_verified'] and vb['native_variance_cache_verified']
        aa,bb,x,y=[tensors(r['tensors']) for r in [fa,fb,va,vb]]
        assert aa.keys()==bb.keys() and x.keys()==y.keys()
        assert all(np.array_equal(x[k],y[k]) for k in x if k!='spk_embed')
        assert all(np.array_equal(aa[k],bb[k]) for k in aa if k not in ['spk_embed',*CHANNELS])
        for record,inp,field in [(fb,bb,'singer_location'),(vb,y,'variance_speaker_root')]:
            root=Path(record[field]);expected=.75*np.fromfile(root/'Yousa_Normal.emb',dtype='<f4')+.25*np.fromfile(root/'Yousa_Classic.emb',dtype='<f4')
            assert np.array_equal(inp['spk_embed'],np.broadcast_to(expected,inp['spk_embed'].shape))
        assert not np.array_equal(aa['spk_embed'],bb['spk_embed']) and not np.array_equal(x['spk_embed'],y['spk_embed'])
        for f,inp in [(fa,aa),(fb,bb)]:
            for ch in CHANNELS:
                expected=np.asarray(f['native_variance_predictions'][ch],np.float32)[None,:]+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                assert np.array_equal(inp[ch],np.clip(expected,*((-10,10) if ch=='tension' else (-96,0))))
        rows.append(dict(context=ctx,frames=aa['f0'].size,changed_variance=['spk_embed'],
            changed_native_acoustic=[k for k in aa if not np.array_equal(aa[k],bb[k])],
            phone_clock_CLR_and_full_pitch_exact=True,manual_deltas_exact=True,both_stage_B_Normal75_Classic25_exact=True))
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),
        reused_A_native_evidence=True,new_B_native_contexts=3,measurement_validated=False))
    print('Independent native speaker-only dependency check passed.',flush=True)


def read(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def fresh():
    rows=[]
    for ctx in [0,1]:
        values={}
        for label in ['A','B']:
            f=load(RUN/f'native-inputs/{label}/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/{label}/variance_{ctx:03}.json')
            repeats=[]
            for suffix in ['', '_repeat']:
                d=RUN/f'fresh/context{ctx}/{label}{suffix}'
                x={k:read(d/(k+'.npz')) for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']};x['wave']=np.load(d/'raw.npy',allow_pickle=False)
                native_ac,native_va=tensors(f['tensors']),tensors(v['tensors']);n=native_ac['f0'].size
                assert all(np.array_equal(x['inputs'][k],value) for k,value in native_ac.items() if k not in CHANNELS)
                assert all(np.array_equal(x['variance-inputs'][k],value) for k,value in native_va.items())
                assert np.array_equal(x['inputs']['probe_noise'],gaussian_frame_noise(101,1,128,n))
                assert np.array_equal(x['variance-inputs']['probe_noise'],gaussian_frame_noise(11,3,24,n))
                assert np.array_equal(x['vocoder-f0']['f0'],np.asarray(f['vocoder_f0'],np.float32)[None,:])
                clipping={}
                for ch in CHANNELS:
                    raw=x['predictions'][ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                    limits=(-10,10) if ch=='tension' else (-96,0)
                    assert np.array_equal(x['inputs'][ch],np.clip(raw,*limits))
                    clipping[ch]=int(np.count_nonzero((raw<limits[0])|(raw>limits[1])))
                assert x['wave'].dtype==np.float32 and len(x['wave'])==n*512 and np.isfinite(x['wave']).all()
                x['clipping']=clipping;repeats.append(x)
            one,two=repeats
            assert np.array_equal(one['wave'],two['wave'])
            for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:
                assert all(np.array_equal(one[k][q],two[k][q]) for q in one[k])
            if label=='A':
                assert np.array_equal(one['wave'],np.load(PRIOR/f'fresh/context{ctx}/A/raw.npy',allow_pickle=False))
                for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:
                    prior=read(PRIOR/f'fresh/context{ctx}/A/{k}.npz');assert all(np.array_equal(one[k][q],prior[q]) for q in prior)
            values[label]=one
            rows.append(dict(context=ctx,variant=label,feature_clipping=clipping,repeat_exact=True,A_exact_previous_accepted=label=='A'))
        a,b=values['A'],values['B'];changed=[k for k in a['inputs'] if not np.array_equal(a['inputs'][k],b['inputs'][k])]
        assert 'spk_embed' in changed and set(changed).issubset({'spk_embed',*CHANNELS})
        assert all(np.array_equal(a['variance-inputs'][k],b['variance-inputs'][k]) for k in a['variance-inputs'] if k!='spk_embed')
        assert np.array_equal(a['vocoder-f0']['f0'],b['vocoder-f0']['f0'])
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),
        waveforms=8,independent_contexts=2,A_inputs_prediction_mel_raw_exact=True,measurement_validated=False))
    print('Independent fresh A reconstruction and A/B repeat check passed.',flush=True)


if __name__=='__main__':{'native':native,'fresh':fresh}[sys.argv[1]]()
