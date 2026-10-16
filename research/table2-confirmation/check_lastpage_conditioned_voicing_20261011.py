"""Independent native and seeded input/wave gate for the explicit VOIC probe.

Does not import the candidate compiler or execute a model.
"""
import copy
import json
import math
from pathlib import Path
import sys

import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT, load, save, ref, check
from agent2utau.evaluation.controlled_probe import tensors, require_isolation
from agent2utau.expression.variance_expectation import gaussian_frame_noise

RUN=ROOT/'runs/experiments/lastpage-conditioned-voicing-20261011'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
CHANNELS=['breathiness','voicing','tension']


def support_mask(a,plan):
    n=tensors(a['tensors'])['f0'].size
    t=(a['position_ms']+(np.arange(n)-a['head_frames'])*a['frame_ms'])/1000
    mask=np.zeros(n,bool)
    for action in plan['actions']:
        if action['additive_UI']:
            lo,hi=action['support_s'];mask|=(t>=lo)&(t<=hi)
    return t,mask


def reconstruct_voicing(project,a,part_index):
    part=project['voice_parts'][part_index]
    curve=next(c for c in part['curves'] if c['abbr']=='voic')
    xs,ys=curve['xs'],curve['ys']
    assert all(y==int(y) for y in ys) and all(b-a==5 for a,b in zip(xs,xs[1:]))
    n=tensors(a['tensors'])['f0'].size
    # Probe uses float32 frame period promoted to double. TimeAxis round-to-even
    # precedes native /5 interpolation; scalar delta multiplication is float32.
    period=float(np.float32(a['frame_ms']))
    origin=a['position_ms']-a['head_frames']*period
    output=[]
    for i in range(n):
        tick=round((origin+i*period)*.96)-part['position']
        if tick<=xs[0]:value=ys[0]
        elif tick>=xs[-1]:value=ys[-1]
        else:
            k=(tick-xs[0])//5
            value=ys[k]+(ys[k+1]-ys[k])*(tick-xs[k])/5
        # Local lambda: (float32(sampled UI)-100f)*12f/100f, then pred add.
        # Multiplying by .12f is algebraically equal but not bit-equivalent.
        offset=np.float32(np.float32(value)-np.float32(100))
        output.append(np.float32(np.float32(offset*np.float32(12))/np.float32(100)))
    return np.asarray(output,np.float32)


def native():
    assert not (RUN/'evaluation/native-independent-check.json').exists()
    plan=load(RUN/'design/protocol.json')
    metadata_path=ROOT/'runs/research/table2-2e-native-check-20261010/core-metadata.json'
    metadata=load(metadata_path)
    selected=[dict(type=t['name'],**m) for t in metadata['types']
        if t['name']=='OpenUtau.Core.DiffSinger.DiffSingerUtils+<>c'
        for m in t['methods'] if m['name']=='<.cctor>b__31_2']
    assert len(selected)==1
    assert [i['operand'] for i in selected[0]['il'] if i['opcode']=='ldc.r4']==[100,12,100]
    project=yaml.safe_load((ROOT/plan['candidate']['path']).read_text(encoding='utf-8-sig'))
    baseline=yaml.safe_load((ROOT/plan['baseline']['path']).read_text(encoding='utf-8-sig'))
    check([plan['candidate'],plan['baseline']])
    assert baseline['expressions']['voic']['max']==200 and project['expressions']['voic']['max']==215
    for label in ['A','B']:
        loaded=yaml.safe_load((RUN/f'native-inputs/{label}-roundtrip.ustx').read_text(encoding='utf-8-sig'))
        written=yaml.safe_load((RUN/f'score/native_{label}.ustx').read_text(encoding='utf-8-sig'))
        assert loaded['expressions']['voic']==written['expressions']['voic']
        assert all(next(c for c in p['curves'] if c['abbr']=='voic')==next(c for c in q['curves'] if c['abbr']=='voic')
            for p,q in zip(loaded['voice_parts'],written['voice_parts']))
    assert load(RUN/'native-inputs/A-phones.json')['parts']==load(RUN/'native-inputs/B-phones.json')['parts']
    rows=[];sources=[ref(RUN/'design/protocol.json'),ref(ROOT/plan['candidate']['path']),ref(ROOT/plan['baseline']['path'])]
    for j,ctx in enumerate([28,29]):
        paths=[RUN/f'native-inputs/{s}/{k}_{j:03d}.json' for s,k in [('A','phrase'),('B','phrase'),('A','variance'),('B','variance')]]
        sources.extend(ref(p) for p in paths)
        a,b,va,vb=[load(p) for p in paths]
        if ctx==28:
            spans=[a['support_s'] for a in plan['actions'] if a['additive_UI']]
            isolation=require_isolation(a,b,va,vb,'voicing',(min(s[0] for s in spans),max(s[1] for s in spans)),cancel_selected=False)
            clock,allowed=support_mask(a,plan)
            delta=np.asarray(b['expression_deltas']['voicing'],np.float32)-np.asarray(a['expression_deltas']['voicing'],np.float32)
            changed=delta!=0
            assert np.any(changed) and np.all(delta>=0) and not np.any(changed&~allowed)
            per_word=[]
            for action in plan['actions']:
                if action['context']!=28:continue
                g=load(BASE/'native_word_geometry.json')[action['word']]
                lo,hi=g['native_vowel'];mask=(clock>=lo)&(clock<hi)
                if action['additive_UI']: assert np.any(changed&mask)
                else: assert not np.any(changed&mask)
                per_word.append(dict(word=action['word'],changed_frames=int((changed&mask).sum()),
                    peak_feature_increment=float(delta[mask].max())))
        else:
            assert a==b and va==vb
            isolation=dict(changed_native_inputs=[],complete_context_exact=True)
            per_word=[]
        for label,p,record in [('A',baseline,a),('B',project,b)]:
            rebuilt=reconstruct_voicing(p,record,ctx)
            actual=np.asarray(record['expression_deltas']['voicing'],np.float32)
            assert np.array_equal(rebuilt,actual), (ctx,label,'Independent native VOIC sample mismatch',float(np.max(np.abs(rebuilt-actual))))
            for ch in CHANNELS:
                pred=np.asarray(record['native_variance_predictions'][ch],np.float32)[None,:]
                d=np.asarray(record['expression_deltas'][ch],np.float32)[None,:]
                limits=(-10,10) if ch=='tension' else (-96,0)
                assert np.array_equal(np.clip(pred+d,*limits),tensors(record['tensors'])[ch])
            for inp,root in [(tensors(record['tensors']),Path(record['singer_location'])),(tensors(va['tensors']),Path(va['variance_speaker_root']))]:
                mix=.75*np.fromfile(root/'Yousa_Normal.emb',dtype='<f4')+.25*np.fromfile(root/'Yousa_Classic.emb',dtype='<f4')
                assert np.array_equal(inp['spk_embed'],np.broadcast_to(mix,inp['spk_embed'].shape))
        rows.append(dict(context=ctx,isolation=isolation,word_support_checks=per_word,
            independent_native_VOIC_sampling_exact=True,two_stage_speaker_exact=True,native_arithmetic_exact=True))
    # These guards must reject accidental expansion before any fresh inference.
    a,b,va,vb=[load(RUN/f'native-inputs/{s}/{k}_000.json') for s,k in [('A','phrase'),('B','phrase'),('A','variance'),('B','variance')]]
    rejected=[]
    for fault in ['changed_other_channel','unverified_cache']:
        wrong=copy.deepcopy(b)
        if fault=='changed_other_channel':
            next(q for q in wrong['tensors'] if q['name']=='tension')['values'][0]+=1
        else:wrong['native_acoustic_cache_verified']=False
        try: require_isolation(a,wrong,va,vb,'voicing',(210,215),cancel_selected=False)
        except ValueError:rejected.append(fault)
        else:raise AssertionError('Isolation guard accepted '+fault)
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/native-voicing-delta-IL.json',dict(metadata=ref(metadata_path),selected=selected))
    save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,sources=sources,
        rejected_faults=rejected,new_seeded_model_calls=0,support_policy='union of five vowel supports, not one broad phrase interval',
        sampling_IL=ref(ROOT/'runs/research/table2-2e-native-check-20261010/selected-clock-sampling-IL.json')))
    print(json.dumps(dict(status='native_passed',rows=rows),ensure_ascii=False),flush=True)


def read(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def fresh():
    assert not (RUN/'evaluation/fresh-independent-check.json').exists()
    plan=load(RUN/'design/protocol.json');rows=[];sources=[]
    for j,ctx in enumerate([28,29]):
        a,b=[load(RUN/f'native-inputs/{label}/phrase_{j:03d}.json') for label in ['A','B']]
        variants={}
        for label in ['A','A_repeat','B','B_repeat']:
            folder=RUN/f'fresh/context{ctx}/{label}'
            paths=[folder/f'{name}.npz' for name in ['inputs','predictions','variance-inputs','mel','vocoder-f0']]
            sources.extend(ref(p) for p in paths);sources.append(ref(folder/'raw.npy'))
            inp,pred,var,mel,vf=[read(p) for p in paths];wave=np.load(folder/'raw.npy',allow_pickle=False)
            f=a if label.startswith('A') else b
            n=inp['f0'].size
            assert np.array_equal(inp['probe_noise'],gaussian_frame_noise(101,1,128,n))
            assert np.array_equal(var['probe_noise'],gaussian_frame_noise(11,3,24,n))
            assert np.array_equal(vf['f0'],np.asarray(a['vocoder_f0'],np.float32)[None,:])
            native_inp=tensors(f['tensors'])
            for k in native_inp:
                if k not in CHANNELS:assert np.array_equal(inp[k],native_inp[k])
            for ch in CHANNELS:
                raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                lo,hi=(-10,10) if ch=='tension' else (-96,0)
                assert np.all((raw>=lo)&(raw<=hi))
                assert np.array_equal(inp[ch],raw)
            assert np.isfinite(wave).all() and wave.dtype==np.float32
            variants[label]=dict(inp=inp,pred=pred,var=var,mel=mel,vf=vf,wave=wave)
        A,B=variants['A'],variants['B']
        for group in ['pred','var','vf']:
            assert all(np.array_equal(A[group][k],B[group][k]) for k in A[group])
        assert np.array_equal(A['wave'],np.load(BASE/f'synthesis/phrase_{ctx:03d}.npy',allow_pickle=False))
        for label in ['A','B']:
            x,y=variants[label],variants[label+'_repeat']
            for group in ['inp','pred','var','mel','vf']:
                assert all(np.array_equal(x[group][k],y[group][k]) for k in x[group])
            assert np.array_equal(x['wave'],y['wave'])
        changed=[k for k in A['inp'] if not np.array_equal(A['inp'][k],B['inp'][k])]
        assert changed==(['voicing'] if ctx==28 else [])
        if ctx==28:
            clock,allowed=support_mask(a,plan)
            offset=B['inp']['voicing'].ravel()-A['inp']['voicing'].ravel()
            assert not np.any((offset!=0)&~allowed) and np.all(offset>=0)
        else:
            assert np.array_equal(A['wave'],B['wave'])
            assert np.array_equal(A['mel']['mel'],B['mel']['mel'])
        rows.append(dict(context=ctx,frames=A['inp']['f0'].size,changed_inputs=changed,
            all_predictions_variance_feeds_vocoder_F0_exact=True,baseline_and_repeats_exact=True,
            feature_clipping=0,whole_unchanged_context_exact=ctx==29))
    check(load(RUN/'protected-before.json'));check(sources)
    save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',rows=rows,sources=sources,
        variance_calls=8,acoustic_vocoder_waveforms=8,candidates=1,checker=ref(Path(__file__)),measurement_validated=False))
    print(json.dumps(dict(status='fresh_passed',rows=rows),ensure_ascii=False),flush=True)


if __name__=='__main__':
    {'native':native,'fresh':fresh}[sys.argv[1]]()
