"""Independent own I stage support, native arithmetic and fresh F dependencies."""
import copy
from pathlib import Path
import sys
import numpy as np
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check
from lastpage_own_li_tenc_stages_20261012 import RUN,F,CHANNELS

from check_lastpage_own_bright_cute_20261012 import read,native_mix
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from agent2utau.openutau.ustx import TempoMap
from agent2utau.knowledge import check_plan_knowledge

def reconstruct_tension(project,a,part_index):
    part=project['voice_parts'][part_index];curve=next(c for c in part['curves'] if c['abbr']=='tenc')
    xs,ys=curve['xs'],curve['ys'];assert all(b-a==5 for a,b in zip(xs,xs[1:]))
    period=float(np.float32(a['frame_ms']));origin=a['position_ms']-a['head_frames']*period
    tm=TempoMap.from_doc(project);out=[]
    for j in range(tensors(a['tensors'])['f0'].size):
        tick=round(tm.ms_to_tick(origin+j*period))-part['position']
        if tick<=xs[0]:value=ys[0]
        elif tick>=xs[-1]:value=ys[-1]
        else:
            k=(tick-xs[0])//5;value=ys[k]+(ys[k+1]-ys[k])*(tick-xs[k])/5
        out.append(np.float32(np.float32(value)/np.float32(20)))
    return np.asarray(out,np.float32)


def native():
    plan=load(RUN/'design/protocol.json');
    meta=load(ROOT/'runs/research/table2-2e-native-check-20261010/core-metadata.json')
    il=next(m['il'] for t in meta['types'] if t['name']=='OpenUtau.Core.DiffSinger.DiffSingerUtils+<>c' for m in t['methods'] if m['name']=='<.cctor>b__31_3')
    assert [i['opcode'] for i in il]==['ldarg.1','ldarg.2','ldc.r4','div','add','ret'] and il[2]['operand']==20
    check([plan['baseline_score'],plan['candidate'],plan['native_score']]+plan['model_adapters'])
    _,receipt=check_plan_knowledge(plan,RUN/'design/protocol.json');assert receipt==load(RUN/'evaluation/knowledge_receipt.json')
    f=yaml.safe_load((ROOT/plan['baseline_score']['path']).read_text(encoding='utf-8-sig'))
    g=yaml.safe_load((ROOT/plan['candidate']['path']).read_text(encoding='utf-8-sig'));restore=copy.deepcopy(g)
    orig=next(c for c in f['voice_parts'][28]['curves'] if c['abbr']=='tenc')
    new=next(c for c in g['voice_parts'][28]['curves'] if c['abbr']=='tenc');assert new['xs']==orig['xs']
    next(c for c in restore['voice_parts'][28]['curves'] if c['abbr']=='tenc')['ys']=orig['ys'];assert restore==f
    tm=TempoMap.from_doc(g);nodes=plan['gesture']['UI_nodes_s'];s,e=nodes[0][0],nodes[-1][0]
    expected=[]
    for x in new['xs']:
        t=tm.tick_to_ms(g['voice_parts'][28]['position']+x)/1000;v=0
        for (lo,a),(hi,b) in zip(nodes,nodes[1:]):
            if lo<=t<=hi:
                u=(t-lo)/(hi-lo);v=a*(2*u**3-3*u**2+1)+b*(-2*u**3+3*u**2);break
        expected.append(int(np.rint(v)))
    assert expected==new['ys'] and max(expected)==10 and min(expected)==0
    rt=yaml.safe_load((RUN/'native-inputs/I-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    native=yaml.safe_load((RUN/'score/native_I.ustx').read_text(encoding='utf-8-sig'))
    assert rt['expressions']['tenc']==native['expressions']['tenc']
    assert rt['voice_parts'][0]['curves']==native['voice_parts'][0]['curves']
    assert rt['voice_parts'][1]['curves']==native['voice_parts'][1]['curves']
    assert load(RUN/'native-inputs/I-phones.json')['parts']==load(F/'native-inputs/F-phones.json')['parts']
    assert load(RUN/'native-inputs/I-pitch.json')['phrases']==load(F/'native-inputs/F-pitch.json')['phrases']
    rows=[]
    for j,ctx in enumerate([28,29]):
        a,b,va,vb=[load(p) for p in [F/f'native-inputs/F/phrase_{j:03}.json',RUN/f'native-inputs/I/phrase_{j:03}.json',
            F/f'native-inputs/F/variance_{j:03}.json',RUN/f'native-inputs/I/variance_{j:03}.json']]
        ac,bc,av,bv=[tensors(r['tensors']) for r in [a,b,va,vb]]
        assert b['native_acoustic_cache_verified'] and vb['native_variance_cache_verified']
        assert all(np.array_equal(av[k],bv[k]) for k in av)
        assert all(np.array_equal(ac[k],bc[k]) for k in ac if k!='tension')
        for k in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','vocoder_f0','tone_shift_cents','singer_location','acoustic_model','vocoder_model']:
            assert a[k]==b[k],(ctx,k)
        for record,inp,key in [(b,bc,'singer_location'),(vb,bv,'variance_speaker_root')]:
            mix,_=native_mix(Path(record[key]),'E',b['phones']);assert np.array_equal(inp['spk_embed'],np.broadcast_to(mix,inp['spk_embed'].shape))
        for ch in CHANNELS:assert a['native_variance_predictions'][ch]==b['native_variance_predictions'][ch]
        assert a['expression_deltas']['voicing']==b['expression_deltas']['voicing'] and a['expression_deltas']['breathiness']==b['expression_deltas']['breathiness']
        delta=np.asarray(b['expression_deltas']['tension'],np.float32)
        assert np.array_equal(delta,reconstruct_tension(g,b,ctx))
        t=(b['position_ms']+(np.arange(len(delta))-b['head_frames'])*b['frame_ms'])/1000
        changed=delta!=0
        if ctx==28:assert changed.any() and np.all(delta>=0) and np.all(~changed|((t>=s)&(t<=e)))
        else:assert not changed.any() and all(np.array_equal(ac[k],bc[k]) for k in ac)
        for ch in CHANNELS:
            pred=np.asarray(b['native_variance_predictions'][ch],np.float32)[None,:]+np.asarray(b['expression_deltas'][ch],np.float32)[None,:]
            assert np.array_equal(bc[ch],np.clip(pred,*((-10,10) if ch=='tension' else (-96,0))))
        rows.append(dict(context=ctx,frames=len(delta),changed_tension_frames=int(changed.sum()),
            max_TENC_model_increment=float(delta.max()),native_TENC_sampling_exact=True,
            phones_full_pitch_both_speaker_variance_exact_F=True,only_li_vowel_support=True))
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),
        arithmetic_source=ref(ROOT/'runs/research/table2-2e-native-check-20261010/core-metadata.json'),knowledge_receipt=ref(RUN/'evaluation/knowledge_receipt.json'),measurement_validated=False))
    print('Native I: full identity, knowledge and finite li-only TENC support passed.',flush=True)

def fresh():
    f=load(RUN/'native-inputs/I/phrase_000.json');v=load(RUN/'native-inputs/I/variance_000.json');old={k:read(F/f'fresh/context28/F/{k}.npz') for k in ['inputs','variance-inputs','predictions','vocoder-f0']}
    values=[];clip={}
    for label in ['I','I_repeat']:
        d=RUN/f'fresh/context28/{label}';data={k:read(d/(k+'.npz')) for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']};data['wave']=np.load(d/'raw.npy',allow_pickle=False)
        ac,va=tensors(f['tensors']),tensors(v['tensors']);n=ac['f0'].size
        assert all(np.array_equal(data['variance-inputs'][k],va[k]) for k in va)
        assert all(np.array_equal(data['inputs'][k],ac[k]) for k in ac if k in ['f0','spk_embed'] or k not in CHANNELS)
        assert np.array_equal(data['variance-inputs']['probe_noise'],gaussian_frame_noise(11,3,24,n))
        assert np.array_equal(data['inputs']['probe_noise'],gaussian_frame_noise(101,1,128,n))
        for k in ['variance-inputs','predictions','vocoder-f0']:assert all(np.array_equal(data[k][q],old[k][q]) for q in old[k])
        for ch in CHANNELS:
            lo,hi=(-10,10) if ch=='tension' else (-96,0);raw=data['predictions'][ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
            assert np.array_equal(data['inputs'][ch],np.clip(raw,lo,hi));clip[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)))
        changed=[k for k in old['inputs'] if not np.array_equal(data['inputs'][k],old['inputs'][k])];assert changed==['tension']
        assert data['wave'].dtype==np.float32 and len(data['wave'])==n*512 and np.isfinite(data['wave']).all();values.append(data)
    a,b=values;assert np.array_equal(a['wave'],b['wave'])
    for k in ['inputs','variance-inputs','predictions','mel','vocoder-f0']:assert all(np.array_equal(a[k][q],b[k][q]) for q in a[k])
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/fresh-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        rows=[dict(context=28,repeat_exact=True,variance_inputs_predictions_exact_F=True,changed_vs_F=['tension'],feature_clipping=clip)],
        new_waveforms=2,context29='sealed F reuse, no new model execution; native all feeds verified exact',measurement_validated=False))
    print('Fresh I repeat exact F predictions; only final TENC changed.',flush=True)

if __name__=='__main__':{'native':native,'fresh':fresh}[sys.argv[1]]()
