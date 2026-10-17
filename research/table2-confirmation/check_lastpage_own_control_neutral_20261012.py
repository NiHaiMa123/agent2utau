"""Independent F neutral group, full score and native/fresh identity checks."""
import copy
from pathlib import Path
import sys
import numpy as np
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check
from lastpage_own_control_neutral_20261012 import RUN,E,CHANNELS
from check_lastpage_own_bright_cute_20261012 import read,native_mix
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise

DEFAULTS={'tenc':0,'brec':0,'voic':100}

def native():
    plan=load(RUN/'design/protocol.json');check([plan['baseline_score'],plan['candidate'],plan['native_score']]+plan['model_adapters'])
    old=yaml.safe_load((ROOT/plan['baseline_score']['path']).read_text(encoding='utf-8-sig'))
    full=yaml.safe_load((ROOT/plan['candidate']['path']).read_text(encoding='utf-8-sig'));restore=copy.deepcopy(full)
    for ctx in [28,29]:
        for abbr,default in DEFAULTS.items():
            c=next(c for c in full['voice_parts'][ctx]['curves'] if c['abbr']==abbr)
            orig=next(c for c in old['voice_parts'][ctx]['curves'] if c['abbr']==abbr)
            assert c['xs']==orig['xs'] and c['ys']==[default]*len(orig['ys'])
            restored=next(c for c in restore['voice_parts'][ctx]['curves'] if c['abbr']==abbr);restored['ys']=orig['ys']
    assert restore==old
    doc=yaml.safe_load((RUN/'score/native_F.ustx').read_text(encoding='utf-8-sig'))
    rt=yaml.safe_load((RUN/'native-inputs/F-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    for p,q in zip(doc['voice_parts'],rt['voice_parts']):
        for abbr,default in DEFAULTS.items():
            c=next(c for c in p['curves'] if c['abbr']==abbr)
            assert c==next(c for c in q['curves'] if c['abbr']==abbr) and all(v==default for v in c['ys'])
    assert load(RUN/'native-inputs/F-phones.json')['parts']==load(E/'native-inputs/E-phones.json')['parts']
    assert load(RUN/'native-inputs/F-pitch.json')['phrases']==load(E/'native-inputs/E-pitch.json')['phrases']
    rows=[]
    for j,ctx in enumerate([28,29]):
        f,v,fe,ve=[load(p) for p in [RUN/f'native-inputs/F/phrase_{j:03}.json',RUN/f'native-inputs/F/variance_{j:03}.json',
            E/f'native-inputs/E/phrase_{j:03}.json',E/f'native-inputs/E/variance_{j:03}.json']]
        ac,va,ae,vare=[tensors(r['tensors']) for r in [f,v,fe,ve]]
        assert ac.keys()==ae.keys() and va.keys()==vare.keys()
        assert f['native_acoustic_cache_verified'] and v['native_variance_cache_verified']
        assert all(np.array_equal(va[k],vare[k]) for k in va)
        assert all(np.array_equal(ac[k],ae[k]) for k in ac if k not in CHANNELS)
        for key in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','vocoder_f0','tone_shift_cents','singer_location','acoustic_model','vocoder_model']:
            assert f[key]==fe[key],(ctx,key)
        for record,inp,key in [(f,ac,'singer_location'),(v,va,'variance_speaker_root')]:
            mix,weights=native_mix(Path(record[key]),'E',f['phones']);assert np.array_equal(inp['spk_embed'],np.broadcast_to(mix,inp['spk_embed'].shape))
        for ch in CHANNELS:
            assert not np.any(f['expression_deltas'][ch])
            assert f['native_variance_predictions'][ch]==fe['native_variance_predictions'][ch]
            pred=np.asarray(f['native_variance_predictions'][ch],np.float32)[None,:]
            assert np.array_equal(ac[ch],np.clip(pred,*((-10,10) if ch=='tension' else (-96,0))))
        rows.append(dict(context=ctx,frames=ac['f0'].size,full_score_only_three_manual_curves_changed=True,
            native_phone_full_pitch_variance_input_prediction_speaker_exact_E=True,manual_deltas_zero=True,
            native_effective_voice_weights=weights.tolist()))
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,
        checker=ref(Path(__file__)),speaker_arithmetic_source=ref(ROOT/'research/table2-confirmation/check_lastpage_own_bright_cute_20261012.py'),measurement_validated=False))
    print('Independent F native clocks/two-stage voice/variance exact E; three manual deltas0.',flush=True)

def fresh():
    rows=[]
    for j,ctx in enumerate([28,29]):
        f=load(RUN/f'native-inputs/F/phrase_{j:03}.json');v=load(RUN/f'native-inputs/F/variance_{j:03}.json')
        old={k:read(E/f'fresh/context{ctx}/E/{k}.npz') for k in ['inputs','variance-inputs','predictions','vocoder-f0']};values=[]
        for label in ['F','F_repeat']:
            d=RUN/f'fresh/context{ctx}/{label}';data={k:read(d/(k+'.npz')) for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']}
            data['wave']=np.load(d/'raw.npy',allow_pickle=False);ac,va=tensors(f['tensors']),tensors(v['tensors']);n=ac['f0'].size
            assert all(np.array_equal(data['variance-inputs'][k],va[k]) for k in va)
            assert all(np.array_equal(data['inputs'][k],ac[k]) for k in ac if k not in CHANNELS)
            assert np.array_equal(data['variance-inputs']['probe_noise'],gaussian_frame_noise(11,3,24,n))
            assert np.array_equal(data['inputs']['probe_noise'],gaussian_frame_noise(101,1,128,n))
            for k in ['variance-inputs','predictions','vocoder-f0']:
                assert data[k].keys()==old[k].keys() and all(np.array_equal(data[k][q],old[k][q]) for q in old[k])
            clipping={}
            for ch in CHANNELS:
                lo,hi=(-10,10) if ch=='tension' else (-96,0);pred=data['predictions'][ch+'_pred']
                assert np.array_equal(data['inputs'][ch],np.clip(pred,lo,hi));clipping[ch]=int(np.count_nonzero((pred<lo)|(pred>hi)))
            assert np.array_equal(data['vocoder-f0']['f0'],np.asarray(f['vocoder_f0'],np.float32)[None,:])
            assert data['wave'].dtype==np.float32 and len(data['wave'])==n*512 and np.isfinite(data['wave']).all();values.append(data)
        a,b=values;assert np.array_equal(a['wave'],b['wave'])
        for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:
            assert a[k].keys()==b[k].keys() and all(np.array_equal(a[k][q],b[k][q]) for q in a[k])
        changed=[k for k in old['inputs'] if not np.array_equal(old['inputs'][k],a['inputs'][k])];assert set(changed)==set(CHANNELS)
        rows.append(dict(context=ctx,frames=n,F_variance_inputs_predictions_exact_E=True,F_manual_deltas0=True,
            changed_vs_E=changed,repeated_inputs_predictions_mel_raw_exact=True,feature_clipping=clipping))
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',rows=rows,
        checker=ref(Path(__file__)),new_waveforms=4,independent_contexts=2,measurement_validated=False))
    print('Fresh F repeats/variance exact E and only three final channels changed.',flush=True)

if __name__=='__main__':{'native':native,'fresh':fresh}[sys.argv[1]]()
