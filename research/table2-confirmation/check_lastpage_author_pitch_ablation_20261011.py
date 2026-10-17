"""Independent pitch-factor identity/dependency and fresh-repeat gates. No models."""
import copy
import sys

import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT, load, save, ref, check
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise

RUN=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011'
LABELS=['A','P','N','PN']
CHANNELS=['breathiness','voicing','tension']


def neutral(doc):
    # Strip only explicitly authorized factors; everything else must be identical.
    d=copy.deepcopy(doc)
    part=d['voice_parts'][0]
    for n in part['notes']:
        n['pitch']['snap_first']=False
        for p in n['pitch']['data']:p['y']=0
    next(c for c in part['curves'] if c['abbr']=='pitd')['ys']=[0]*len(next(c for c in part['curves'] if c['abbr']=='pitd')['ys'])
    return d


def native():
    plan=load(RUN/'design/protocol.json');check(list(plan['scores'].values())+[plan['source'],plan['original']])
    docs={l:yaml.safe_load((RUN/f'score/{l}.ustx').read_text(encoding='utf-8-sig')) for l in LABELS}
    assert all(neutral(d)==neutral(docs['A']) for d in docs.values())
    for label,d in docs.items():
        r=yaml.safe_load((RUN/f'native-inputs/{label}-roundtrip.ustx').read_text(encoding='utf-8-sig'))
        for n,m in zip(d['voice_parts'][0]['notes'],r['voice_parts'][0]['notes']):assert n['pitch']==m['pitch']
        for c in d['voice_parts'][0]['curves']:
            if c['xs']:assert c==next(c2 for c2 in r['voice_parts'][0]['curves'] if c2['abbr']==c['abbr'])
    phones={l:load(RUN/f'native-inputs/{l}-phones.json') for l in LABELS}
    # export-phonemes includes final pitch; phone identities are checked separately.
    for l in LABELS:
        parts=phones[l]['parts'];assert len(parts)==1 and len(parts[0]['phrases'])==3
        for a,b in zip(phones['A']['parts'][0]['phrases'],parts[0]['phrases']):
            for k in ['position','end','phones']:assert a[k]==b[k],(l,k)
    pitches={l:load(RUN/f'native-inputs/{l}-pitch.json')['phrases'] for l in LABELS}
    rows=[]
    for ctx in [0,1]:
        p={l:pitches[l][ctx] for l in LABELS}
        before={l:np.array(p[l]['before_pitd_cents'],np.float32) for l in LABELS}
        final={l:np.array(p[l]['final_cents'],np.float32) for l in LABELS}
        assert np.array_equal(before['A'],before['P'])
        assert np.array_equal(before['N'],before['PN'])
        assert np.array_equal(final['P'],before['P']) and np.array_equal(final['PN'],before['PN'])
        assert np.any(before['A']!=before['N'])
        residualA=final['A']-before['A'];residualN=final['N']-before['N']
        assert np.max(np.abs(residualA-residualN))<=.001, 'PITD additive contribution changed'
        records={l:[load(RUN/f'native-inputs/{l}/{kind}_{ctx:03}.json') for kind in ['phrase','variance']] for l in LABELS}
        fA,vA=records['A'];a,va=tensors(fA['tensors']),tensors(vA['tensors'])
        info=[]
        for l,(f,v) in records.items():
            for k in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','expression_deltas','tone_shift_cents',
                'singer_location','acoustic_model','vocoder_model']:assert f[k]==fA[k],(ctx,l,k)
            assert f['native_acoustic_cache_verified'] and v['native_variance_cache_verified']
            b,vb=tensors(f['tensors']),tensors(v['tensors'])
            assert a.keys()==b.keys() and va.keys()==vb.keys()
            changed_ac=[k for k in a if not np.array_equal(a[k],b[k])]
            changed_var=[k for k in va if not np.array_equal(va[k],vb[k])]
            assert set(changed_ac).issubset({'f0',*CHANNELS}),(ctx,l,changed_ac)
            assert set(changed_var).issubset({'pitch'}),(ctx,l,changed_var)
            assert np.array_equal(a['spk_embed'],b['spk_embed']) and np.array_equal(va['spk_embed'],vb['spk_embed'])
            if l!='A':assert 'f0' in changed_ac and changed_var==['pitch']
            vf=np.asarray(f['vocoder_f0'],np.float32)[None,:]
            shift=np.asarray(f['tone_shift_cents'],np.float32)[None,:]
            scale=np.array([np.float32(2**(float(x)/1200)) for x in shift.ravel()],np.float32).reshape(shift.shape)
            expected=vf*scale if f['vocoder_pitch_controllable'] else vf
            assert np.array_equal(b['f0'],expected), 'Authored SHFC must remain on acoustic path'
            for ch in CHANNELS:
                pred=np.asarray(f['native_variance_predictions'][ch],np.float32)[None,:]
                delta=np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                limits=(-10,10) if ch=='tension' else (-96,0)
                assert np.array_equal(b[ch],np.clip(pred+delta,*limits))
            info.append(dict(variant=l,changed_native_acoustic=changed_ac,changed_variance=changed_var,
                final_pitch_changed_frames=int(np.count_nonzero(final[l]!=final['A'])),
                max_final_pitch_delta_cents=float(np.max(np.abs(final[l]-final['A'])))))
        rows.append(dict(context=ctx,native_5tick_frames=len(final['A']),model_frames=a['f0'].size,
            phone_clock_and_both_stage_speaker_exact=True,PITD_and_note_pitch_separated=True,variants=info))
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,checker=ref(ROOT/'research/table2-confirmation/check_lastpage_author_pitch_ablation_20261011.py'),
        protocol=ref(RUN/'design/protocol.json'),measurement_validated=False))
    print('Independent native pitch-factor/dependency checks passed.',flush=True)


def read(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def fresh():
    rows=[]
    for ctx in [0,1]:
        values={}
        for l in LABELS:
            f=load(RUN/f'native-inputs/{l}/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/{l}/variance_{ctx:03}.json')
            repeats=[]
            for suffix in ['', '_repeat']:
                d=RUN/f'fresh/context{ctx}/{l}{suffix}'
                x={k:read(d/(k+'.npz')) for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']}
                x['wave']=np.load(d/'raw.npy',allow_pickle=False)
                native_in=tensors(f['tensors']);native_var=tensors(v['tensors']);n=native_in['f0'].size
                assert all(np.array_equal(x['inputs'][k],value) for k,value in native_in.items() if k not in CHANNELS)
                assert all(np.array_equal(x['variance-inputs'][k],value) for k,value in native_var.items())
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
            a,b=repeats
            assert np.array_equal(a['wave'],b['wave'])
            for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:
                assert a[k].keys()==b[k].keys() and all(np.array_equal(a[k][q],b[k][q]) for q in a[k])
            values[l]=a
        for l,x in values.items():
            changed=[k for k in x['inputs'] if not np.array_equal(x['inputs'][k],values['A']['inputs'][k])]
            assert set(changed).issubset({'f0',*CHANNELS})
            rows.append(dict(context=ctx,variant=l,changed_fresh_acoustic_inputs=changed,feature_clipping=x['clipping'],
                repeat_inputs_predictions_mel_vocoder_PCM_exact=True,raw_peak=float(np.max(np.abs(x['wave'])))))
    check(load(RUN/'protected-before.json'))
    save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',rows=rows,checker=ref(ROOT/'research/table2-confirmation/check_lastpage_author_pitch_ablation_20261011.py'),
        actual_waveforms=16,independent_contexts=2,measurement_validated=False))
    print('Independent 16-wave fresh/repeat checks passed.',flush=True)


if __name__=='__main__':{'native':native,'fresh':fresh}[sys.argv[1]]()
