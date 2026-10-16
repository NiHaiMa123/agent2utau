"""Independent DYN-only dependencies, native curve and Core processing checks."""
import copy
import math
from pathlib import Path
import sys
import numpy as np
import yaml
from assemble_lastpage_accepted_baseline_20261011 import ROOT,load,save,ref,check
from lastpage_own_li_dyn_20261012 import RUN,F,BASE
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.openutau.ustx import TempoMap
from agent2utau.knowledge import check_plan_knowledge
from shfc_pcm_checks import dynamic_gain,require_dynamics

def native():
    plan=load(RUN/'design/protocol.json');check([plan['baseline_score'],plan['candidate'],plan['native_score']]+plan['raw_sources'])
    _,receipt=check_plan_knowledge(plan,RUN/'design/protocol.json');assert receipt==load(RUN/'evaluation/knowledge_receipt.json')
    f=yaml.safe_load((ROOT/plan['baseline_score']['path']).read_text(encoding='utf-8-sig'))
    h=yaml.safe_load((ROOT/plan['candidate']['path']).read_text(encoding='utf-8-sig'));restored=copy.deepcopy(h)
    old=next(c for c in f['voice_parts'][28]['curves'] if c['abbr']=='dyn');new=next(c for c in h['voice_parts'][28]['curves'] if c['abbr']=='dyn')
    assert old['xs']==new['xs'];next(c for c in restored['voice_parts'][28]['curves'] if c['abbr']=='dyn')['ys']=old['ys'];assert restored==f
    nodes=plan['gesture']['UI_nodes_s'];tm=TempoMap.from_doc(h);ys=[]
    for x in new['xs']:
        t=tm.tick_to_ms(h['voice_parts'][28]['position']+x)/1000;v=0
        for (a,u),(b,z) in zip(nodes,nodes[1:]):
            if a<=t<=b:
                q=(t-a)/(b-a);v=u*(2*q**3-3*q*q+1)+z*(-2*q**3+3*q*q);break
        ys.append(int(np.rint(v)))
    assert ys==new['ys'] and min(ys)==-40 and max(ys)==15
    native=yaml.safe_load((RUN/'score/native_H.ustx').read_text(encoding='utf-8-sig'))
    rt=yaml.safe_load((RUN/'native-inputs/H-roundtrip.ustx').read_text(encoding='utf-8-sig'))
    assert native['expressions']['dyn']==rt['expressions']['dyn']
    assert all(a['curves']==b['curves'] for a,b in zip(native['voice_parts'],rt['voice_parts']))
    assert load(RUN/'native-inputs/H-phones.json')['parts']==load(F/'native-inputs/F-phones.json')['parts']
    assert load(RUN/'native-inputs/H-pitch.json')['phrases']==load(F/'native-inputs/F-pitch.json')['phrases']
    rows=[]
    for j,ctx in enumerate([28,29]):
        a,b,va,vb=[load(p) for p in [F/f'native-inputs/F/phrase_{j:03}.json',RUN/f'native-inputs/H/phrase_{j:03}.json',
            F/f'native-inputs/F/variance_{j:03}.json',RUN/f'native-inputs/H/variance_{j:03}.json']]
        for x,y in [(a,b),(va,vb)]:
            tx,ty=tensors(x['tensors']),tensors(y['tensors']);assert tx.keys()==ty.keys() and all(np.array_equal(tx[k],ty[k]) for k in tx)
        assert b['native_acoustic_cache_verified'] and vb['native_variance_cache_verified']
        for k in ['position_ms','frame_ms','head_frames','tail_frames','sample_rate','phones','vocoder_f0','expression_deltas','tone_shift_cents','native_variance_predictions','singer_location']:
            assert a[k]==b[k],(ctx,k)
        ph=load(RUN/'native-inputs/H-dynamics.json')['phrases'][j]
        curve=next(c for c in h['voice_parts'][ctx]['curves'] if c['abbr']=='dyn')
        values=np.asarray(ph['dynamics'],np.float32);start=ph['position']-ph['leading'];expected=[]
        for i in range(len(values)):
            tick=start+i*5-h['voice_parts'][ctx]['position'];ui=np.float32(np.interp(tick,curve['xs'],curve['ys']))
            expected.append(np.float32(0 if ui==h['expressions']['dyn']['min'] else math.pow(10,float(ui)*.1/20)))
        expected=np.asarray(expected,np.float32)
        assert np.array_equal(expected,values),(ctx,'native DYN amplitude mismatch',float(np.max(np.abs(expected-values))))
        assert np.min(values)>0 and np.isfinite(values).all()
        if ctx==29:assert np.all(values==1)
        rows.append(dict(context=ctx,all_model_inputs_predictions_manual_features_speaker_pitch_phones_exact_F=True,
            native_DYN_curve_reconstructed_exact=True,native_curve_points=len(values),amplitude_min=float(values.min()),amplitude_max=float(values.max())))
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/native-independent-check.json',dict(status='passed',rows=rows,checker=ref(Path(__file__)),
        knowledge_receipt=ref(RUN/'evaluation/knowledge_receipt.json'),new_fixed_seeded_model_calls=0,measurement_validated=False))
    print('H native DYN-only score/amplitudes and all F model dependencies passed.',flush=True)

def processed():
    layout=load(RUN/'processed/layout.json');gain=np.fromfile(RUN/'processed/gain/phrase_000.f32',dtype='<f4')
    assert np.array_equal(gain,dynamic_gain(layout))
    raws=[np.load(F/f'fresh/context28/{l}/raw.npy',allow_pickle=False) for l in ['F','F_repeat']]
    actual=[np.fromfile(RUN/f'processed/{l}/phrase_000.f32',dtype='<f4') for l in ['H','H_repeat']]
    for a,b in zip(raws,actual):require_dynamics(a,b,gain)
    assert np.array_equal(raws[0],raws[1]) and np.array_equal(actual[0],actual[1])
    assert np.isfinite(actual[0]).all() and np.max(np.abs(actual[0].astype(np.float64)*1.5))<1
    changed=gain!=1;assert changed.any();indices=np.flatnonzero(changed);origin=layout['raw_origin_s']
    span=[origin+indices[0]/44100,origin+(indices[-1]+1)/44100]
    plan=load(RUN/'design/protocol.json');s,e=plan['gesture']['support_s']
    assert span[0]>=s-.011 and span[1]<=e+.011
    outside=np.ones(len(gain),bool);outside[indices[0]:indices[-1]+1]=False;assert np.array_equal(raws[0][outside],actual[0][outside])
    check(load(RUN/'protected-before.json'));save(RUN/'evaluation/processed-independent-check.json',dict(status='passed',checker=ref(Path(__file__)),
        native_Core_gain_and_independent_gain_exact=True,raw_times_gain_f32_and_repeated_output_exact=True,
        actual_gain_change_span_s=span,changed_samples=int(changed.sum()),gain_min=float(gain.min()),gain_max=float(gain.max()),
        support_policy='report native sample interpolation support; bound to design within one5tick segment per edge, no hidden crop',
        new_fixed_seeded_model_calls=0,new_processed_repeats=2,measurement_validated=False))
    print('H actual Core DYN/sample gain/multiplication/repeat passed.',flush=True)

if __name__=='__main__':{'native':native,'processed':processed}[sys.argv[1]]()
