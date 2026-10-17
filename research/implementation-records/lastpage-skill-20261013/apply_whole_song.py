"""Explicit current-song revision; never an automatic new-song template."""
import copy,json,math,subprocess,sys
from pathlib import Path
import numpy as np
import yaml
from prepare_feedback_and_skill import ROOT,RUN,J,SKILL,INSTALLED
sys.path.insert(0,str(ROOT/'research/table2-confirmation'))
from assemble_lastpage_accepted_baseline_20261011 import load,save,sha,ref,check
from agent2utau.knowledge import collect_context,check_plan_knowledge
from agent2utau.openutau.ustx import TempoMap
from agent2utau.resources.config import load_config
from agent2utau.evaluation.controlled_probe import tensors
from agent2utau.expression.variance_expectation import gaussian_frame_noise
from shfc_path_backend import model_feed

BASE=ROOT/'runs/lastpage_loudness_skill_v02_20261007'
CURRENT=ROOT/'runs/production/lastpage-accepted-baseline-20261011'
MODELS=ROOT/'runs/experiments/lastpage-author-pitch-ablation-20261011/fresh/models'
CHANNELS=['breathiness','voicing','tension']
COLORS=['cl01','cl02','cl03','cl04','cl05']
# Agent-selected current-source hypotheses, not every lower GAME event.
# word: lower center, beginning of rise, arrival, reconnection, preparation.
GESTURES={
 13:(63.1,20.325,20.400,20.465,.030),
 30:(64.6,30.690,30.785,30.870,.035),
 94:(67.0,75.925,76.015,76.095,.045),
 100:(64.2,79.335,79.430,79.515,.050),
 118:(66.0,89.635,89.730,89.810,.045),
 124:(65.0,93.105,93.200,93.285,.035),
 148:(63.3,133.765,133.860,133.945,.030),
 165:(64.6,144.105,144.200,144.280,.035),
 174:(59.2,149.565,149.650,149.705,.025),
 179:(64.4,152.110,152.200,152.290,.030),
 221:(67.0,180.045,180.140,180.225,.035),
 235:(65.0,189.065,189.160,189.245,.040),
 253:(67.0,199.325,199.420,199.500,.040),
 259:(64.5,202.740,202.840,202.930,.040),
 307:(64.5,230.645,230.740,230.825,.040),
}

def curve_value(t,nodes):
    for (a,x,dx),(b,y,dy) in zip(nodes,nodes[1:]):
        if a<=t<=b:
            u=(t-a)/(b-a);h=b-a
            return (2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*h*dx+(-2*u**3+3*u*u)*y+(u**3-u*u)*h*dy
    raise ValueError(t)

def resources():
    for reg in [J/'native-inputs/runtime.json',ROOT/'runs/lastpage_shfc_onset_probe_20261008/frozen_runtime.json']:
        for name,h in load(reg).items():assert sha(Path(name))==h,name
    p=load(RUN/'design/protocol.json');check(p['model_adapters']+p['source_bindings']+p['skill_bindings'])
    check_plan_knowledge(p,RUN/'design/protocol.json')
    for relative in ['SKILL.md','references/local-acceptance-to-whole-song-phonation.md']:
        assert sha(SKILL/relative)==sha(INSTALLED/relative)

def prepare():
    assert not (RUN/'design/protocol.json').exists()
    request=load(J/'design/knowledge_context.json')['request']
    request['responses'].append('RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01')
    packet=collect_context(**request);save(RUN/'design/knowledge_context.json',packet)
    decisions=[]
    for r in packet['records']:
        ident=r['id'];kind=r['kind'];choice='use';reason='Use object/mechanism definitions to distinguish musical actions, predicted phonation and PCM gain.'
        match='Current Yousa1.65c own whole-song revision; actual consumer and clock checked separately.'
        if kind=='response':
            choice='reject';reason='Retain negative/group-limited evidence; no automatic VOIC/TENC/BREC escalation or author contour transfer.'
            if ident=='RESP:LASTPAGE-OWN-LI-ENTRY-PITCH-01':
                choice='extrapolate';reason='Explicitly accepted J locally; use source-stage-first method and this song candidate voice baseline, keep accepted J exact.'
            elif ident=='RESP:LASTPAGE-OWN-CONTROL-NEUTRAL-01':
                choice='extrapolate';reason='F working baseline and subsequent J acceptance justify a provisional manual-neutral baseline; other phrases untested.'
            elif ident.startswith('OBS:'):
                choice='use';reason='Review actual stage omissions and conflicting source observations, not only vowel median.'
            match='J itself retained; all other new whole-song contexts are explicit within-song extrapolations, not local acceptances.'
        decisions.append(dict(id=ident,decision=choice,reason=reason,condition_match=match,
            limitations='Source unknown and prior negatives retained; withdrawn transition issue not repaired; feature/level response is not force or texture truth; no general rule validated.'))
    source_names=['source_observations.json','fcpe.npz','rmvpe.npz','fresh_game.json','chosen_score.json',
        'native_word_geometry.json','agent_word_decisions.json','agent_function_plans.json','delivery_native_pitch.json']
    source_refs=[ref(BASE/n) for n in source_names]
    protected={r['path']:r['sha256'] for r in load(RUN/'protected-before.json')}
    for r in source_refs:assert protected[r['path']]==r['sha256'],r['path']
    obs=load(BASE/'source_observations.json')['words'];old_dec=load(BASE/'agent_word_decisions.json')
    geom=load(BASE/'native_word_geometry.json');chosen=load(BASE/'chosen_score.json')['words']
    doc=yaml.safe_load((J/'delivery/lastpage_own_li_entry_pitch_J.ustx').read_text(encoding='utf8'))
    candidate=copy.deepcopy(doc);pitch=load(BASE/'delivery_native_pitch.json')['phrases'];tm=TempoMap.from_doc(doc)
    gestures=[];changes=[]
    for word,(lower,turn,arrival,rejoin,prep) in GESTURES.items():
        ctx=old_dec[word]['context'];q=pitch[ctx];part=candidate['voice_parts'][ctx]
        a=geom[word]['native_vowel'][0]-prep;b=rejoin
        ts=np.asarray(q['times_ms'],float)/1000;ys=np.asarray(q['final_cents'],float)
        def own_value(t):return float(np.interp(t,ts,ys))
        def slope(t):return (own_value(t+.005)-own_value(t-.005))/.010
        on=geom[word]['native_vowel'][0]+.025
        assert a<on<turn<arrival<rejoin<=geom[word]['native_vowel'][1]
        main=chosen[word]['stages'][0][1]*100
        nodes=[[a,own_value(a),slope(a)],[on,lower*100,0],[turn,lower*100,0],
            [arrival,main,0],[b,own_value(b),slope(b)]]
        curve=next(c for c in part['curves'] if c['abbr']=='pitd');rows=[]
        for i,x in enumerate(curve['xs']):
            tick=part['position']+x;t=tm.tick_to_ms(tick)/1000
            assert tick==q['pitch_start_tick']+5*i
            if a<=t<=b:
                target=curve_value(t,nodes);value=int(np.rint(target-q['before_pitd_cents'][i]))
                rows.append(dict(grid_index=i,time_s=t,target_cents=target,old=curve['ys'][i],new=value));curve['ys'][i]=value
        gestures.append(dict(word=word,char=obs[word]['char'],context=ctx,support_s=[a,b],center_nodes=nodes,
            purpose='Restore current-source-supported lower entry before existing own sustained center; retain subsequent body and descent',
            alternative='Immediate sustained-center arrival rejected because own final line omitted this short source-supported stage',
            uncertainty='No causal force/texture conclusion; note tone/phone selection unchanged; new whole-song listening pending',rows=rows))
    for i,part in enumerate(candidate['voice_parts']):
        old=doc['voice_parts'][i]
        if i!=22:
            end=max(c['xs'][-1] for c in part['curves']);xs=[0,end]
            for abbr,value in zip(COLORS,[40,60,0,0,0]):
                c=next((c for c in part['curves'] if c['abbr']==abbr),None)
                if c is None:part['curves'].append(dict(abbr=abbr,xs=xs,ys=[value,value]))
                else:c['ys']=[value]*len(c['ys'])
            for abbr,value in [('tenc',0),('brec',0),('voic',100),('shfc',0)]:
                c=next((c for c in part['curves'] if c['abbr']==abbr),None)
                if c is not None:c['ys']=[value]*len(c['ys'])
        assert part['notes']==old['notes']
        assert [c for c in part['curves'] if c['abbr']=='dyn']==[c for c in old['curves'] if c['abbr']=='dyn']
        changes.append(dict(context=i,notes=len(part['notes']),intent=old_dec[next(d['word'] for d in old_dec if d['context']==i)]['intent'],
            voice='Retain accepted bao C whole context with old Normal75/Classic25 and SHFC' if i==22 else 'J candidate Bright40/Cute60; predicted basis with neutral manual TENC/BREC/VOIC',
            changed=part!=old,pitch_words=[g['word'] for g in gestures if g['context']==i],
            DYN='Retain own prior native envelope, including existing context8 gain; inspect actual new output',
            alternative='Per-word increased VOIC/TENC or blanket BREC reduction rejected by existing negatives',
            auditory_status='accepted exact retained J' if i in [28,29] else 'old accepted local bao scope retained' if i==22 else 'new condition pending listening'))
    assert candidate['voice_parts'][22]==doc['voice_parts'][22]
    assert candidate['voice_parts'][28:30]==doc['voice_parts'][28:30]
    (RUN/'score').mkdir();full=RUN/'score/lastpage_J_method_whole_song_v03.ustx'
    full.write_text(yaml.safe_dump(candidate,allow_unicode=True,sort_keys=False),encoding='utf8')
    native=copy.deepcopy(candidate);native['wave_parts']=[];native['tracks']=[native['tracks'][0]]
    native['tracks'][0].update(volume=0,pan=-100,mute=False,solo=False)
    (RUN/'score/native_v03.ustx').write_text(yaml.safe_dump(native,allow_unicode=True,sort_keys=False),encoding='utf8')
    arrays={}
    for name in ['fcpe','rmvpe']:
        with np.load(BASE/(name+'.npz'),allow_pickle=False) as z:arrays[name]={k:z[k].copy() for k in z.files}
    words=[]
    for w,d,g in zip(obs,old_dec,geom):
        stages=[]
        for event in w['game']:
            summary={}
            for name,z in arrays.items():
                m=(z['times']>=event['start'])&(z['times']<event['end'])&z['voiced']&(z['f0_hz']>0)
                a=69+12*np.log2(z['f0_hz'][m]/440)
                summary[name]=dict(voiced_frames=len(a),median_note=float(np.median(a)) if len(a) else None)
            stages.append(dict(game=event,dual_F0=summary))
        selected=next((x for x in gestures if x['word']==w['word']),None)
        ctx=d['context'];reason='Retain own current center/body/periodic actions and phoneme clock; no reliable unimplemented entry selected.'
        if selected:reason=selected['purpose']
        elif w['word'] in [29,112,152]:reason='GAME short-entry candidate conflicts with local F0/voiced support; do not install a low-note recipe.'
        elif ctx==22:reason='Preserve entire already accepted bao context to avoid changing its accepted condition; other source stage candidate not executed here.'
        elif ctx in [28,29]:reason='Preserve exactly the explicitly accepted J two-phrase condition; no ti gain or withdrawn transition repair.'
        elif w['unknown']:reason='Source unknown retained; prior own artistic design is an explicit interpretation, not newly verified source music.'
        words.append(dict(word=w['word'],char=w['char'],line=w['line'],context=ctx,source_unknown=w['unknown'],
            source_stages=stages,native_geometry=g,previous_own_decision=d,
            choice='new lower-entry function' if selected else 'retain own pitch',reason=reason,
            voice_decision=changes[ctx]['voice'],strength='Retain musical body/release and prediction differences; no per-word equalization or monotone force target',
            alternative=selected['alternative'] if selected else 'Blanket low entry or generic phonation-strength boost rejected',
            musical_stage_accepted=False,new_auditory_labels=0))
    save(RUN/'design/word-decisions.json',words);save(RUN/'design/phrase-decisions.json',changes);save(RUN/'design/pitch-gestures.json',gestures)
    plan=dict(schema_version=2,scope='whole_song_revision',project=ref(full),native_project=ref(RUN/'score/native_v03.ustx'),
        source_audio=ref(BASE/'source.wav'),accepted_J=ref(J/'delivery/lastpage_own_li_entry_pitch_J.ustx'),
        source_bindings=source_refs,model_adapters=[ref(MODELS/'variance.onnx'),ref(MODELS/'acoustic.onnx')],
        skill_bindings=[ref(SKILL/'SKILL.md'),ref(SKILL/'references/local-acceptance-to-whole-song-phonation.md')],
        knowledge_context=dict(path='knowledge_context.json',sha256=sha(RUN/'design/knowledge_context.json'),decisions=decisions),
        word_decisions=ref(RUN/'design/word-decisions.json'),phrase_decisions=ref(RUN/'design/phrase-decisions.json'),pitch_gestures=ref(RUN/'design/pitch-gestures.json'),
        retained_own_functions=ref(BASE/'agent_function_plans.json'),whole_song_redraw_claim=False,
        execution_authorization=ref(RUN/'feedback/J-acceptance.json'),
        budget=dict(primary_fresh_contexts=34,repeat_contexts=[0,22,28],max_fresh_waveforms=37,seeds=[11,101],parameter_search=False),
        mix=dict(fixed_vocal_gain=1.5,BGM_change=False,normalization=False,compression=False),
        exclusions=['author curves/arrays','source F0 fitted as target','unaccepted force-dose escalation','withdrawn connection repair'],
        status='frozen_before_native_and_models',agent_heard=False,measurement_validated=False,general_rule_validated=False)
    save(RUN/'design/protocol.json',plan);_,receipt=check_plan_knowledge(plan,RUN/'design/protocol.json');save(RUN/'evaluation/knowledge_receipt.json',receipt)
    resources();print('Frozen:318 word decisions,34 contexts,15 independently selected pitch gestures; J/bao exceptions exact.',flush=True)

def call(name,args,exe):
    out=RUN/'logs'/(name+'.log');result=RUN/'native-inputs'/(name+'-result.json')
    if result.exists():return load(result)
    assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True)
    print('Native',name,flush=True)
    p=subprocess.run([str(exe),*args],cwd=exe.parent,capture_output=True,encoding='utf8',errors='replace',timeout=1800)
    out.write_text(p.stdout+p.stderr,encoding='utf8')
    assert p.returncode==0,(name,p.returncode,p.stdout[-1000:],p.stderr[-1000:])
    r=json.loads(p.stdout.strip().splitlines()[-1]);assert not r.get('errors') and r.get('ok',True);save(result,r);return r

def native():
    resources();ou=Path(load_config()['openutau_dir']);exe=ou/'a2u-shfcprobe-20261008.exe';p=str(RUN/'score/native_v03.ustx')
    for name,args in [
        ('roundtrip',['roundtrip','--project',p,'--out',str(RUN/'native-inputs/v03-roundtrip.ustx')]),
        ('phones',['export-phonemes','--project',p,'--out',str(RUN/'native-inputs/v03-phones.json')]),
        ('pitch',['export-pitch','--project',p,'--out',str(RUN/'native-inputs/v03-pitch.json')]),
        ('dynamics',['export-dynamics','--project',p,'--out',str(RUN/'native-inputs/v03-dynamics.json')]),
        ('render',['render','--project',p,'--out',str(RUN/'native-render/v03-technical.wav'),'--mixdown','--timeout','25']),
        ('probe',['export-render-probe','--project',p,'--out',str(RUN/'native-inputs/v03'),'--indices',','.join(map(str,range(34)))])]:
        call(name,args,ou/'a2u-levelprobe-v15.exe' if name=='dynamics' else exe)
    resources()

def execute():
    assert load(RUN/'evaluation/native-independent-check.json')['status']=='passed';resources()
    import onnxruntime as ort
    opt=ort.SessionOptions();opt.intra_op_num_threads=opt.inter_op_num_threads=1;opt.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    f=load(RUN/'native-inputs/v03/phrase_000.json')
    sessions=[ort.InferenceSession(str(p),sess_options=opt,providers=['CPUExecutionProvider']) for p in [MODELS/'variance.onnx',MODELS/'acoustic.onnx',f['vocoder_model']]]
    variance,acoustic,vocoder=sessions;rows=[]
    if not (RUN/'fresh/start.json').exists():save(RUN/'fresh/start.json',dict(protocol=ref(RUN/'design/protocol.json'),seeds=[11,101],max_fresh_waveforms=37,ort=ort.__version__))
    for ctx in range(34):
        f=load(RUN/f'native-inputs/v03/phrase_{ctx:03}.json');v=load(RUN/f'native-inputs/v03/variance_{ctx:03}.json')
        for label in (['v03','repeat'] if ctx in [0,22,28] else ['v03']):
            d=RUN/f'fresh/context{ctx:02}/{label}'
            if (d/'result.json').exists():rows.append(load(d/'result.json'));continue
            assert not d.exists();ac,va=tensors(f['tensors']),tensors(v['tensors']);n=ac['f0'].size
            va['probe_noise']=gaussian_frame_noise(11,3,24,n);names=[o.name for o in variance.get_outputs()]
            pred=dict(zip(names,variance.run(names,model_feed(variance,va))));clip={}
            for ch in CHANNELS:
                lo,hi=(-10,10) if ch=='tension' else (-96,0);raw=pred[ch+'_pred']+np.asarray(f['expression_deltas'][ch],np.float32)[None,:]
                clip[ch]=int(np.count_nonzero((raw<lo)|(raw>hi)));ac[ch]=np.clip(raw,lo,hi).astype(np.float32)
            ac['probe_noise']=gaussian_frame_noise(101,1,128,n);mel=acoustic.run(['mel'],model_feed(acoustic,ac))[0];vm=mel.copy()
            if f['acoustic_mel_base']!=f['vocoder_mel_base']:vm*=np.log(10) if f['acoustic_mel_base']=='10' else 1/np.log(10)
            vf=np.asarray(f['vocoder_f0'],np.float32)[None,:];wave=vocoder.run(None,model_feed(vocoder,dict(mel=vm,f0=vf)))[0].reshape(-1)
            assert np.isfinite(wave).all() and len(wave)==n*512
            d.mkdir(parents=True);np.save(d/'raw.npy',wave)
            for name,x in [('inputs',ac),('variance-inputs',va),('predictions',pred),('mel',dict(mel=mel)),('vocoder-f0',dict(f0=vf))]:np.savez_compressed(d/(name+'.npz'),**x)
            row=dict(context=ctx,variant=label,frames=n,samples=len(wave),feature_clipping=clip,
                wave_start_s=f['position_ms']/1000-f['head_frames']*float(np.float32(f['frame_ms']))/1000,raw_peak=float(np.max(abs(wave))))
            save(d/'result.json',row);rows.append(row);print('Fresh context',ctx,label,'done',flush=True)
    save(RUN/'fresh/execution.json',dict(rows=rows,variance_calls=len(rows),acoustic_vocoder_waveforms=len(rows),repeat_contexts=[0,22,28],agent_heard=False))
    resources()

if __name__=='__main__':{'prepare':prepare,'native':native,'execute':execute}[sys.argv[1]]()
