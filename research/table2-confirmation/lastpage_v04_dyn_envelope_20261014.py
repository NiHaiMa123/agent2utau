"""One explicit post-vocoder envelope revision; reuse bound current raw waves."""
import copy,json,math,subprocess,sys
from pathlib import Path
import numpy as np
import soundfile as sf
import yaml
from review_lastpage_v03_volume_20261014 import ROOT,RUN,V03,BASE,KNOW,REPORT,load,save,ref,sha,check
from agent2utau.knowledge import collect_context,check_plan_knowledge
from agent2utau.openutau.ustx import TempoMap
from agent2utau.resources.config import load_config

# Seconds/UI0.1dB. Different curves reflect declared phrase roles, not inverse RMS.
NODES={
 11:[[86.32,0],[86.60,25],[86.93,30],[87.33,30],[87.62,23],[88.08,20],[88.40,0]],
 22:[[182.65,0],[183.00,15],[183.38,40],[183.59,40],[183.88,25],[184.50,30],
     [184.85,25],[185.08,18],[185.52,30],[186.15,35],[186.68,20],[186.81,0]],
 23:[[187.527,0],[187.655,18],[188.075,20],[188.365,32],[188.645,32],
     [189.10,22],[189.65,20],[190.10,15],[190.2583,0]],
 25:[[196.199,0],[196.41,25],[196.70,30],[197.00,26],[197.26,15],
     [197.61,12],[198.10,12],[198.42,5],[198.62,0]],
}
INTENT={11:'Carry the new ru/guo phrase entrance; gradually return before already strong hou/de, not boost every syllable.',
 22:'Most emotional chorus: build through ba, locally carry weak ni, retain bao timbre, ease on naturally strong ti, carry li/mian then release before non-singing tail.',
 23:'Continue emotional phrase after clear bu; carry gan/rang/weak ni, keep kan delivery and recede through jian; avoid boosting leading AP/SP.',
 25:'Carry second ru/guo entrance, reduce support through already stronger zhe/shi/hou/de rather than maintaining a flat loud platform.'}

def shape(t,nodes):
    if t<=nodes[0][0] or t>=nodes[-1][0]:return 0.
    for (a,x),(b,y) in zip(nodes,nodes[1:]):
        if a<=t<=b:
            u=(t-a)/(b-a);v=u*u*u*(10+u*(-15+6*u));return x+(y-x)*v
    raise ValueError(t)

def runtime():
    plan=load(RUN/'design/protocol.json');check_plan_knowledge(plan,RUN/'design/protocol.json')
    check(plan['baseline']+plan['raw_sources']+plan['runtime'])

def freeze():
    assert not (RUN/'design/protocol.json').exists()
    analysis=load(RUN/'observations/envelope-review.json');assert len(analysis['words'])==318
    q=load(RUN/'design/knowledge_context.json')['request'];q['parameters'].append('PARAM:C13.01')
    packet=collect_context(**q);save(RUN/'design/execution-knowledge_context.json',packet)
    decisions=copy.deepcopy(load(RUN/'design/review-protocol.json')['knowledge_context']['decisions'])
    decisions.append(dict(id='PARAM:C13.01',decision='reject',reason='TENC does not encode loudness; old I dose did not improve perceived force. Keep final model phonation exact in this envelope-only candidate.',
        condition_match='Current user identifies voice-volume drop; force remains a separate perceptual target.',limitations='Reject this intervention here, not all tension expression in all contexts.'))
    old=yaml.safe_load((V03/'delivery/lastpage_J_method_whole_song_v03_playback.ustx').read_text(encoding='utf8'))
    doc=copy.deepcopy(old);tm=TempoMap.from_doc(doc);traces=[]
    for ctx,nodes in NODES.items():
        p=doc['voice_parts'][ctx];curve=next(c for c in p['curves'] if c['abbr']=='dyn');assert all(y==0 for y in curve['ys']) and all(x%5==0 for x in curve['xs'])
        before=copy.deepcopy(curve['ys']);rows=[]
        for i,x in enumerate(curve['xs']):
            t=tm.tick_to_ms(p['position']+x)/1000;ui=int(np.rint(shape(t,nodes)));curve['ys'][i]=ui
            if ui!=before[i]:rows.append(dict(grid_index=i,tick=p['position']+x,time_s=t,UI=ui))
        assert max(curve['ys'])<=40 and min(curve['ys'])==0
        traces.append(dict(context=ctx,UI_nodes_s=nodes,shape='independent quintic interpolation at existing5tick grid, native integer UI encoding',purpose=INTENT[ctx],
            alternative='Per-word equal RMS, force-dose increase, BGM rebalance or global gain raise rejected',changed_rows=rows))
    (RUN/'score').mkdir();full=RUN/'score/lastpage_J_method_volume_v04.ustx';full.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False),encoding='utf8')
    native=copy.deepcopy(doc);native['wave_parts']=[];native['tracks']=[native['tracks'][0]];native['tracks'][0].update(volume=0,pan=-100,mute=False,solo=False)
    (RUN/'score/native_v04.ustx').write_text(yaml.safe_dump(native,allow_unicode=True,sort_keys=False),encoding='utf8')
    rawrefs=[ref(V03/f'fresh/context{ctx:02}/v03/raw.npy') for ctx in range(34)]
    ou=Path(load_config()['openutau_dir']);runtime_refs=[dict(path=str(p),sha256=sha(p)) for p in [ou/('a2u-levelprobe-v15'+s) for s in ['.exe','.dll','.deps.json','.runtimeconfig.json']]]
    runtime_refs+= [dict(path=p,sha256=h) for p,h in load(ROOT/'runs/lastpage_shfc_onset_probe_20261008/frozen_runtime.json').items()]
    save(RUN/'design/compiled-DYN.json',traces)
    plan=dict(schema_version=2,scope='four_context_native_DYN_only_with_whole_song_review',
        authorization=ref(RUN/'feedback/v03-volume.json'),analysis=ref(RUN/'observations/envelope-review.json'),
        baseline=[ref(V03/'delivery/lastpage_J_method_whole_song_v03_playback.ustx'),ref(V03/'delivery/lastpage_J_method_whole_song_v03_vocal.wav')],
        candidate=ref(full),native_candidate=ref(RUN/'score/native_v04.ustx'),
        knowledge_context=dict(path='execution-knowledge_context.json',sha256=sha(RUN/'design/execution-knowledge_context.json'),decisions=decisions),
        gestures=ref(RUN/'design/compiled-DYN.json'),changed_contexts=list(NODES),raw_sources=rawrefs,runtime=runtime_refs,
        fixed=dict(vocal_gain=1.5,original_backing=True,common_mix_margin=.9,notes_pitch_phones_speaker_phonation_exact=True),
        budget=dict(new_variance_calls=0,new_acoustic_vocoder_waveforms=0,processed_primary_contexts=34,repeat_contexts=list(NODES),unity_probes=34,parameter_sweep=False),
        limits='Output prominence candidate only, not restoration of harmonic source strength or proof of emotional singing. Do not adopt until user listening.',
        status='frozen_before_native_execution',agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'design/protocol.json',plan);_,receipt=check_plan_knowledge(plan,RUN/'design/protocol.json');save(RUN/'evaluation/execution-knowledge-receipt.json',receipt)
    runtime();print('Frozen four phrase-specific DYN curves,maximum4dB;all raw/model conditions reused exactly.',flush=True)

def call(name,args,exe):
    result=RUN/'native-inputs'/(name+'-result.json');log=RUN/'logs'/(name+'.log')
    if result.exists():return load(result)
    assert not log.exists();log.parent.mkdir(parents=True,exist_ok=True)
    print('Native',name,flush=True);p=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf8',errors='replace',timeout=1200)
    log.write_text(p.stdout+p.stderr,encoding='utf8');assert p.returncode==0,(name,p.returncode,p.stderr[-1000:])
    r=json.loads(p.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(result,r);return r

def native():
    runtime();ou=Path(load_config()['openutau_dir']);p=str(RUN/'score/native_v04.ustx')
    for name,args in [
        ('roundtrip',['roundtrip','--project',p,'--out',str(RUN/'native-inputs/v04-roundtrip.ustx')]),
        ('pitch',['export-pitch','--project',p,'--out',str(RUN/'native-inputs/v04-pitch.json')]),
        ('phones',['export-phonemes','--project',p,'--out',str(RUN/'native-inputs/v04-phones.json')]),
        ('DYN',['export-dynamics','--project',p,'--out',str(RUN/'native-inputs/v04-dynamics.json')])]:
        call(name,args,ou/('a2u-levelprobe-v15.exe' if name=='DYN' else 'a2u-shfcprobe-20261008.exe'))
    runtime();print('Native pitch/phones and DYN exported;no model rendering.',flush=True)

def process():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed';runtime()
    ledger=load(V03/'evaluation/assembly-check.json')['contributions'];manifests={k:[] for k in ['raw','unity','repeat']}
    for p in ledger:
        ctx=p['context'];f=load(V03/f'native-inputs/v03/phrase_{ctx:03}.json');w=np.load(V03/f'fresh/context{ctx:02}/v03/raw.npy',allow_pickle=False)
        clock=dict(phrase=ctx,position_ms=f['position_ms'],leading_ms=f['position_ms']-p['origin_s']*1000)
        for label in ['raw','unity']+(['repeat'] if ctx in NODES else []):
            path=RUN/f'dynamics-inputs/{label}_{ctx:03}.f32';assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True)
            (np.ones_like(w) if label=='unity' else w).astype('<f4').tofile(path);manifests[label].append(dict(**clock,input_f32=str(path)))
    ou=Path(load_config()['openutau_dir'])
    for label,rows in manifests.items():
        mf=RUN/f'design/dynamics-{label}-manifest.json';save(mf,rows)
        call('apply-'+label,['apply-dynamics','--project',str(RUN/'score/native_v04.ustx'),'--manifest',str(mf),'--out',str(RUN/f'dynamics/{label}')],ou/'a2u-levelprobe-v15.exe')
    save(RUN/'evaluation/process-counts.json',dict(primary=34,unity=34,repeated=4,new_variance_calls=0,new_acoustic_vocoder_waveforms=0))
    runtime();print('34 Core DYN contributions,34 unity probes and4 repeated processed outputs completed.',flush=True)

if __name__=='__main__':{'freeze':freeze,'native':native,'process':process}[sys.argv[1]]()

