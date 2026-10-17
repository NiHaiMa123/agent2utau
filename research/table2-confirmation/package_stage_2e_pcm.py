"""Fixed-gain independent context/focus PCM and frozen-order listening pairs."""
import math
from pathlib import Path
import numpy as np
import soundfile as sf
from freeze_stage_2d import ROOT,HERE,OUT,load,sha
from prepare_stage_2e_execution import save
from shfc_path_runner import load_sealed_protocol
from shfc_pcm_checks import interval_indices,require_finite_subfull
from check_stage_2e_current_native import records

def main():
    run=ROOT/load(HERE/'stage_2e_execution_baseline_binding.json')['run']
    check=load(run/'raw-independent-check.json'); assert check['status']=='passed'
    assert not (run/'pcm-packaging.json').exists() and not (run/'delivery').exists()
    p=load_sealed_protocol(); files=[]; rows=[]; pairs=[]
    source=ROOT/'runs/lastpage_loudness_skill_v02_20261007/stems/source_(other)_vocals_mel_band_roformer.wav'
    expected='47db8f46c596c921f54d2ea16777266ae18986e587ea2c83915bb2839faf7ccc'
    manifest=load(ROOT/'runs/lastpage_loudness_skill_v02_20261007/completion_manifest.json')
    assert manifest['files'][str(source)]==expected and sha(source)==expected
    info=sf.info(source); assert info.samplerate==44100
    def write(path,values,subtype='PCM_24'):
        require_finite_subfull(values); path.parent.mkdir(parents=True,exist_ok=True); assert not path.exists()
        sf.write(path,values,44100,subtype=subtype)
        reopened,sr=sf.read(path,dtype='float64',always_2d=values.ndim==2)
        assert sr==44100 and reopened.shape==values.shape;require_finite_subfull(reopened)
        bound=2**-23 if subtype=='PCM_24' else 2**-24
        assert np.max(np.abs(reopened-values))<=bound+8*np.finfo(np.float64).eps
        files.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),samples=len(values),
            channels=1 if values.ndim==1 else values.shape[1],subtype=subtype,peak=float(np.max(np.abs(reopened))),
            max_encoding_error=float(np.max(np.abs(reopened-values)))))
    for case,row in zip(p['cases'],check['conditions']):
        cid=case['condition']['id'];a,_=records(run,case,'A');origin=row['native_origin_s'];n=row['waveform_samples']
        requested=case['listener_focus_s']; focus=interval_indices(requested,origin,n)
        phone_ix=next(r for r in load(run/'native-current-check.json')['conditions'] if r['condition_id']==cid)['identity']['target_phone_indices']
        required=a['phones'][max(0,phone_ix[0]-1):min(len(a['phones']),phone_ix[1]+2)]
        complete=focus is not None and all(requested[0]<=q['positionMs']/1000 and requested[1]>=q['endMs']/1000 for q in required)
        if not complete: focus=(0,n)
        focus_interval=[origin+focus[0]/44100,origin+focus[1]/44100]
        backing_start=math.ceil(origin*44100)
        with sf.SoundFile(source) as f:
            f.seek(backing_start);backing=f.read(n,dtype='float64',always_2d=True)
        assert len(backing)==n
        mapping=p['listening']['anonymous_code_map'][f'word{case["condition"]["word"]}'];inverse={v:k for k,v in mapping.items()}
        values={}; versions=[]
        for label in ['A','S','D','P']:
            wave=np.fromfile(run/'dynamics'/cid/f'{label}-r0.f32',dtype='<f4')
            repeat=np.fromfile(run/'dynamics'/cid/f'{label}-r1.f32',dtype='<f4');assert np.array_equal(wave,repeat)
            vocal=wave.astype(np.float64)*1.5;mix=vocal[:,None]+backing*.7
            values[label]=dict(vocal=vocal,mix=mix)
            for rep in [0,1]:write(run/'pcm'/cid/f'{label}-r{rep}.wav',vocal.astype(np.float32),'FLOAT')
            code=inverse[label]; entry=dict(label=label,code=code)
            for stage,ix in [('full',(0,n)),('focus',focus)]:
                for kind,data in values[label].items():
                    path=run/'delivery'/stage/kind/f'{cid}-{code}.wav'; write(path,data[slice(*ix)])
                    entry[stage+'_'+kind]=path.relative_to(ROOT).as_posix()
            versions.append(entry)
        for order,direction in enumerate(p['listening']['presentation_order'],1):
            first,second=direction.split('-'); codes=[inverse[first],inverse[second]]
            pair=dict(condition_id=cid,order=order,direction=direction,codes=codes,
                segment_samples=focus[1]-focus[0],gap_samples=26460,second_start_s=(focus[1]-focus[0]+26460)/44100)
            for kind in ['vocal','mix']:
                x,y=[values[label][kind][slice(*focus)] for label in [first,second]]
                silence=np.zeros((26460,)+x.shape[1:],np.float64)
                path=run/'delivery/pairs'/kind/f'{cid}-{order:02}-{codes[0]}-{codes[1]}.wav'
                write(path,np.concatenate([x,silence,y]));pair[kind]=path.relative_to(ROOT).as_posix()
            pairs.append(pair)
        rows.append(dict(condition_id=cid,word=case['condition']['word'],origin_s=origin,
            source_pcm_clock='sample j at native_origin_s+j/44100; ceil of relative time*sr for cuts',
            backing_start_sample=backing_start,backing_origin_s=backing_start/44100,
            backing_grid_rounding_s=backing_start/44100-origin,
            samples=n,requested_focus_s=requested,focus_complete=complete,focus_samples=focus,
            actual_focus_interval_s=focus_interval,focus_role='requested_focus' if complete else 'whole_phrase_fallback_no_zero_padding',
            target_in_full_file_s=[case['condition']['native_phones'][0]['start_ms']/1000-origin,case['condition']['native_phones'][1]['start_ms']/1000-origin,case['condition']['native_phones'][1]['end_ms']/1000-origin],
            versions=versions))
    assert sha(source)==expected
    delivery=[x for x in files if '/delivery/' in x['path']]
    assert len(files)==88 and len(delivery)==72
    save(run/'pcm-packaging.json',dict(conditions=rows,pairs=pairs,files=files,delivery_files=72,
        diagnostic_FLOAT_files=16,seeded_waveforms=16,unique_first_repeat_variants=8,
        gains=dict(vocal=1.5,backing=.7),gain_arithmetic='float64 fixed multiplication; FLOAT diagnostics float32; PCM_24 all deliveries',
        backing=dict(path=source.relative_to(ROOT).as_posix(),sha256=expected,original_channels=info.channels),
        no_normalization=True,no_compression=True,no_posthoc_compensation=True,
        pair_gap_s=.6,pair_gap_role='presentation separation only, never fills missing focus boundaries',
        auditory_feedback='pending',agent_heard=False,delivery_gate='pending_observation_and_final_audit'))
    print('16 FLOAT diagnostics + 72 independent context/focus/fixed-order PCM files prepared')

if __name__=='__main__':main()
