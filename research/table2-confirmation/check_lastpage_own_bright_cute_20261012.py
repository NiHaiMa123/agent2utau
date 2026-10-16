"""Independent own-E score identity, two-stage mixtures and fresh baseline gate."""
import copy
from pathlib import Path
import sys
import numpy as np
import yaml

from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise

RUN=ROOT/'runs/experiments/lastpage-own-bright-cute-20261012'
BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
COLORS=['cl01','cl02','cl03','cl04','cl05']
CHANNELS=['breathiness','voicing','tension']


def native_mix(root,label,phones):
    # Installed lambda promotes 0.01f to double, multiplies sampled UI in
    # double, then casts float32. Sum(float[]) is cast back to float32;
    # residual is added to the default speaker WEIGHT before NumSharp dot.
    # All bound phones here use Bright, including propagated padded defaults.
    assert {p['suffix'] for p in phones}=={'Yousa_Bright'}
    ui=[0,0,75,0,25] if label=='A' else [40,60,0,0,0]
    w=np.array([np.float32(float(v)*float(np.float32(.01))) for v in ui],np.float32)
    total=np.float32(sum(float(v) for v in w))
    if total>1:w/=total
    else:w[0]=np.float32(w[0]+np.float32(np.float32(1)-total))
    result=np.zeros(384,np.float32)
    for weight,name in zip(w,['Bright','Cute','Normal','Whisper','Classic']):
        result+=weight*np.fromfile(root/f'Yousa_{name}.emb',dtype='<f4')
    return result,w


def native():
    plan=load(RUN/'design/protocol.json');check([plan['baseline'],plan['candidate']]+list(plan['native_scores'].values())+plan['model_adapters'])
    a=yaml.safe_load((ROOT/plan['baseline']['path']).read_text(encoding='utf-8-sig'));e=yaml.safe_load((ROOT/plan['candidate']['path']).read_text(encoding='utf-8-sig'))
    d=copy.deepcopy(e)
    for ctx in [28,29]:
        orig=a['voice_parts'][ctx]['curves'];changed=d['voice_parts'][ctx]['curves']
        assert [c for c in orig if c['abbr'] not in COLORS]==[c for c in changed if c['abbr'] not in COLORS]
        d['voice_parts'][ctx]['curves']=copy.deepcopy(orig)
    assert d==a
    for label,expected in [('A',[0,0,75,0,25]),('E',[40,60,0,0,0])]:
        doc=yaml.safe_load((RUN/f'score/native_{label}.ustx').read_text(encoding='utf-8-sig'))
        rt=yaml.safe_load((RUN/f'native-inputs/{label}-roundtrip.ustx').read_text(encoding='utf-8-sig'))
        for p,q in zip(doc['voice_parts'],rt['voice_parts']):
            for k,v in zip(COLORS,expected):
                c=next((c for c in p['curves'] if c['abbr']==k),None)
                if c is None:assert v==doc['expressions'][k]['default_value']==0
                else:assert all(y==v for y in c['ys']) and c==next(c for c in q['curves'] if c['abbr']==k)
    assert load(RUN/'native-inputs/A-phones.json')['parts']==load(RUN/'native-inputs/E-phones.json')['parts']
    assert load(RUN/'native-inputs/A-pitch.json')['phrases']==load(RUN/'native-inputs/E-pitch.json')['phrases']
    proof=load(RUN/'evaluation/speaker-selected-IL.json')
    percent=next(m for m in proof['methods'] if m['name']=='<PhraseSpeakerEmbedByFrame>b__10_0')
    cast=next(m for m in proof['methods'] if m['name']=='<PhraseSpeakerEmbedByFrame>b__10_1')
    assert [q['operand'] for q in percent['il'] if q['opcode']=='ldc.r8']==[float(np.float32(.01))]
    assert [q['opcode'] for q in percent['il']]==['ldarg.1','ldc.r8','mul','ret']
    assert [q['opcode'] for q in cast['il']]==['ldarg.1','conv.r4','ret']
    frame=next(m for m in proof['methods'] if m['name']=='PhraseSpeakerEmbedByFrame')
    assert any(q['operand']=='System.Linq.Enumerable::Sum' for q in frame['il'])
    assert [q['opcode'] for q in frame['il'] if 665<=q['offset']<=678]==['ldc.r4','ldloc.s','sub','call','callvirt']
    assert any(q['operand']=='NumSharp.np::dot' and q['offset']>678 for q in frame['il'])
    assert proof['core_sha256']==next(v for p,v in load(RUN/'native-inputs/runtime.json').items() if p.endswith('OpenUtau.Core.dll'))
    rows=[]
    for j,ctx in enumerate([28,29]):
        fa,fe,va,ve=[load(RUN/f'native-inputs/{l}/{k}_{j:03}.json') for l,k in [('A','phrase'),('E','phrase'),('A','variance'),('E','variance')]]
        aa,ee,x,y=[tensors(r['tensors']) for r in [fa,fe,va,ve]]
        for key in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','vocoder_f0','expression_deltas','tone_shift_cents','singer_location','acoustic_model','vocoder_model']:
            assert fa[key]==fe[key],(ctx,key)
        assert fe['native_acoustic_cache_verified'] and ve['native_variance_cache_verified']
        assert aa.keys()==ee.keys() and x.keys()==y.keys()
        assert all(np.array_equal(x[k],y[k]) for k in x if k!='spk_embed')
        assert all(np.array_equal(aa[k],ee[k]) for k in aa if k not in ['spk_embed',*CHANNELS])
        for label,f,v,ac,var in [('A',fa,va,aa,x),('E',fe,ve,ee,y)]:
            for r,inp,key in [(f,ac,'singer_location'),(v,var,'variance_speaker_root')]:
                root=Path(r[key])
                mix,weights=native_mix(root,label,f['phones'])
                assert np.array_equal(inp['spk_embed'],np.broadcast_to(mix,inp['spk_embed'].shape)),(ctx,label,key)
            for ch in CHANNELS:
                raw=np.asarray(f['native_variance_predictions'][ch],np.float32)[None,:]+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                assert np.array_equal(ac[ch],np.clip(raw,*((-10,10) if ch=='tension' else (-96,0))))
        assert not np.array_equal(aa['spk_embed'],ee['spk_embed']) and not np.array_equal(x['spk_embed'],y['spk_embed'])
        rows.append(dict(context=ctx,frames=aa['f0'].size,score_other_32_parts_and_notes_controls_exact=True,
            phone_full_pitch_manual_deltas_F0_exact=True,both_stage_native_percent_and_residual_reconstruction_exact=True,
            E_effective_float32_weights=weights.tolist()))
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),
        native_percent_IL=ref(RUN/'evaluation/speaker-selected-IL.json'),repair='Literal real .4/.6 gate failed; corrected to installed percent sampling/default-weight-before-dot arithmetic. UI40/60, score, tolerances and budget unchanged; rejection preserved.',measurement_validated=False))
    print('Independent own-A/E identity and two-stage named mixture gate passed.',flush=True)


def read(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}


def fresh():
    rows=[]
    for j,ctx in enumerate([28,29]):
        values={}
        for label in ['A','E']:
            f=load(RUN/f'native-inputs/{label}/phrase_{j:03}.json');v=load(RUN/f'native-inputs/{label}/variance_{j:03}.json');rep=[]
            for suffix in ['', '_repeat']:
                folder=RUN/f'fresh/context{ctx}/{label}{suffix}';x={k:read(folder/(k+'.npz')) for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']};x['wave']=np.load(folder/'raw.npy',allow_pickle=False)
                na,nv=tensors(f['tensors']),tensors(v['tensors']);n=na['f0'].size
                assert all(np.array_equal(x['inputs'][k],value) for k,value in na.items() if k not in CHANNELS)
                assert all(np.array_equal(x['variance-inputs'][k],value) for k,value in nv.items())
                assert np.array_equal(x['inputs']['probe_noise'],gaussian_frame_noise(101,1,128,n))
                assert np.array_equal(x['variance-inputs']['probe_noise'],gaussian_frame_noise(11,3,24,n))
                assert np.array_equal(x['vocoder-f0']['f0'],np.asarray(f['vocoder_f0'],np.float32)[None,:])
                clip={}
                for ch in CHANNELS:
                    raw=x['predictions'][ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:];lo,hi=(-10,10) if ch=='tension' else (-96,0)
                    assert np.array_equal(x['inputs'][ch],np.clip(raw,lo,hi));clip[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)))
                assert x['wave'].dtype==np.float32 and len(x['wave'])==n*512 and np.isfinite(x['wave']).all();rep.append(x)
            one,two=rep;assert np.array_equal(one['wave'],two['wave'])
            for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:assert all(np.array_equal(one[k][q],two[k][q]) for q in one[k])
            if label=='A':
                assert np.array_equal(one['wave'],np.load(BASE/f'synthesis/phrase_{ctx:03}.npy',allow_pickle=False))
                with np.load(BASE/f'synthesis/state_{ctx:03}.npz',allow_pickle=False) as old:
                    for ch in CHANNELS:
                        assert np.array_equal(one['predictions'][ch+'_pred'],old[ch]);assert np.array_equal(one['inputs'][ch],old['final_'+ch])
            values[label]=one;rows.append(dict(context=ctx,variant=label,feature_clipping=clip,repeat_exact=True,own_A_exact_historical_state_PCM=label=='A'))
        a,e=values['A'],values['E'];changed=[k for k in a['inputs'] if not np.array_equal(a['inputs'][k],e['inputs'][k])]
        assert 'spk_embed' in changed and set(changed).issubset({'spk_embed',*CHANNELS})
        assert all(np.array_equal(a['variance-inputs'][k],e['variance-inputs'][k]) for k in a['variance-inputs'] if k!='spk_embed')
        assert np.array_equal(a['vocoder-f0']['f0'],e['vocoder-f0']['f0'])
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),new_waveforms=8,independent_contexts=2,measurement_validated=False))
    print('Independent own-A reproduction, A/E repeats and speaker dependencies passed.',flush=True)


if __name__=='__main__':{'native':native,'fresh':fresh}[sys.argv[1]]()
