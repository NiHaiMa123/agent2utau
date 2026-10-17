"""Agent-chosen whole-song functions on fresh native clocks, source-only inputs."""
from source import ROOT,RUN,load,save,sha,ref
from score import LINE_CHOICES
import numpy as np,yaml,sys,copy,importlib.util
from pathlib import Path

def cfg():
    from agent2utau.resources.config import load_config
    c=load_config();c['openutau_dir']=str(RUN/'native-runtime');return c

def export(op,p,out):
    from agent2utau.openutau.bridge import run_bridge
    r=run_bridge(cfg(),[op,'--project',str(p),'--out',str(out)]);save(out.with_suffix('.receipt.json'),r);assert r['ok'],r;return load(out)

def breathing():
    from agent2utau.openutau.build import sec_to_tick
    src=RUN/'score/agent-score.ustx';doc=yaml.safe_load(src.read_text(encoding='utf8'));ledger=load(RUN/'design/word-ledger.json');selected={0,3,9,13,16,21,24,27,29,30,32,35,36,40,43,48,51,54,57};events=[]
    for i,w in enumerate(ledger[:-1]):
        nxt=ledger[i+1];a=w['end'];b=nxt['start'];gap=b-a
        if w['line'] not in selected or not w['final'] or gap<.29 or w['context']!=nxt['context']:continue
        part=doc['voice_parts'][w['context']];lo=b-min(.42,gap-.035);hi=b-.14
        if hi-lo<.1:continue
        n=copy.deepcopy(part['notes'][0]);n.update(position=sec_to_tick(lo)-part['position'],duration=sec_to_tick(hi)-sec_to_tick(lo),tone=nxt['stages'][0]['tone'],lyric='AP');n['pitch']=dict(snap_first=False,data=[dict(x=-40,y=0,shape='io'),dict(x=40,y=0,shape='io')]);part['notes'].append(n)
        # Avoid false musical notes in non-singing gaps; no isolated breath
        # splice. The AP and following consonant share phonemizer context.
        n2=copy.deepcopy(n);n2.update(position=sec_to_tick(hi)-part['position'],duration=sec_to_tick(b)-sec_to_tick(hi),lyric='SP');part['notes'].append(n2);part['notes'].sort(key=lambda n:n['position'])
        events.append(dict(after_line=w['line'],span_s=[lo,hi],next_word=nxt['word'],purpose='语义结束后的补气；承载字不截短，预留下一辅音'))
    p=RUN/'score/agent-score-breath.ustx';p.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=10**6),encoding='utf8');save(RUN/'design/breath-budget.json',dict(initial=load(RUN/'score/score.json')['breaths'],additional=events,source_breath_truth=False,consecutive_groups_reviewed=True,artistic_placement=True))
    export('export-phonemes',p,RUN/'native-input/breath-phones.json');export('export-pitch',p,RUN/'native-input/breath-pitch.json')
    print('Additional semantic breaths',len(events),flush=True)

def design(input_score=None,phonefile=None,pitchfile=None,ledgerfile=None,output_name=''):
    from agent2utau.openutau.build import sec_to_tick
    from agent2utau.workflow import design_math
    helper=design_math();ledger=load(ledgerfile or RUN/'design/word-ledger.json');doc=yaml.safe_load((input_score or RUN/'score/agent-score-breath.ustx').read_text(encoding='utf8'));phoneparts=load(phonefile or RUN/'native-input/breath-phones.json')['parts'];pitch=load(pitchfile or RUN/'native-input/breath-pitch.json')['phrases'];phrases=[];controls=[];wordaudit=[]
    for part in doc['voice_parts']:part['curves']=[c for c in part['curves'] if c['abbr'] not in ['pitd','dyn','tenc']]
    # Native ownership -> explicit syllable identity. Auxiliary AP/SP do not
    # receive vocal-nucleus functions or musical F0 truth.
    mapping={}
    for pi,(part,ph) in enumerate(zip(doc['voice_parts'],phoneparts)):
        for ni,n in enumerate(part['notes']):
            if n['lyric'] in ['AP','SP','+']:continue
            time=(part['position']+n['position'])/960
            matches=[w for w in ledger if w['context']==pi and abs(w['start']-time)<.0011];assert len(matches)==1,(pi,ni,time)
            mapping[(pi,ni)]=matches[0]
    phraseindex=0
    for pi,(part,pp) in enumerate(zip(doc['voice_parts'],phoneparts)):
      partcontrol={};parttraces=[]
      for ph in pp['phrases']:
        native=pitch[phraseindex];phraseindex+=1;a=native['times_ms'][0]/1000;b=native['times_ms'][-1]/1000
        notes=[n for n in pp['notes'] if n['start_ms']/1000<b and n['end_ms']/1000>a]
        phoneword={};ordered=[]
        for p in ph['phones']:
            owners=p['owner_note_indices'];w=next((mapping[(pi,ni)] for ni in owners if (pi,ni) in mapping),None)
            if w and w['word'] not in phoneword:ordered.append(w);phoneword[w['word']]=[]
            if w:phoneword[w['word']].append(p)
        # Independent centers, explicitly supplied music stages and arrival
        # times; native before-PITD is only read by the compiler for encoding.
        nodes={a:float(notes[0]['tone']*100),b:float(notes[-1]['tone']*100)};previous=notes[0]['tone']*100
        for n in notes:
            t=n['start_ms']/1000;tone=n['tone']*100;dur=(n['end_ms']-n['start_ms'])/1000
            entry=min(.12 if abs(tone-previous)>=700 else .065 if abs(tone-previous)>=200 else .045,max(.026,dur*.35))
            lo=max(a,t-.07);hi=min(b,t+entry)
            if lo>max(nodes):pass
            nodes[lo]=float(previous);nodes[hi]=float(tone);previous=tone
        comps=[];expect=[]
        for w in ordered:
            phones=phoneword[w['word']];vowel=next((p for p in phones if p['phoneme'].split('/')[-1] not in ['b','p','m','f','d','t','n','l','g','k','h','j','q','x','zh','ch','sh','r','z','c','s','w','y','y0','v0']),None)
            assert vowel,(w,phones)
            va=vowel['start_ms']/1000;vb=vowel['end_ms']/1000
            # Same-vowel extenders are owned by the initial lyric group and
            # already included in native vowel interval.
            start=max(a,va+.07);end=min(b,vb-.055);duration=end-start;mode=w['body_action'];ids=[]
            if duration>.07 and mode in ['return','carry','settle']:
                amp=w['depth_c']*(1 if mode=='return' else -.75 if mode=='settle' else .55);ident=f"w{w['word']}-body"
                comps.append(dict(id=ident,family='finite_return',support_s=[start,end],peak_s=min(end-.02,start+max(.025,duration*.43)),peak_c=amp));ids.append(ident)
                expect.append(dict(support_s=[start,end],range_c=[0,1600],purpose='主体有限回收/承接；换音幅度与主体动作分开记录'))
            elif duration>.20 and mode in ['late','early','two']:
                chunks=[]
                if mode=='two' and duration>1.25:
                    split=start+duration*.45;chunks=[(start,split-.09,.8),(split+.10,end,1)]
                else:chunks=[(start+min(.23,duration*.25) if mode=='late' else start,end,1)]
                for j,(x,y,factor) in enumerate(chunks):
                    if y-x<.15:continue
                    ident=f"w{w['word']}-cycle{j}";attack=x+min(.10,(y-x)*.22);release=y-min(.14,(y-x)*.25)
                    comps.append(dict(id=ident,family='oscillation',support_s=[x,y],attack_end_s=attack,release_start_s=release,
                        depth_nodes=[[x,w['depth_c']*.4*factor],[attack,w['depth_c']*.72*factor],[release,w['depth_c']*factor],[y,w['depth_c']*.48*factor]],
                        rate_nodes=[[x,w['rate_hz']-.35],[y,w['rate_hz']+.15 if j==0 else w['rate_hz']-.18]],phase_rad=.3 if j==0 else 1.15));ids.append(ident)
                    expect.append(dict(support_s=[x,y],range_c=[1,1700],purpose='延迟展开/重新展开的主体周期，退出独立；不是源F0缩幅'))
            # Actual final frames, not merely XML declarations, audited later.
            # Establish on a few meaningful sustained focal nuclei only;
            # defaults preserve consonants, short links and independent B/V.
            event=None
            if w['role']=='focal' and vb-va>.65 and w['char'] not in ['的','上']:
                peak=10 if w['line']<27 else 14 if w['line']>=38 else 8
                x=va+.055;y=vb-.045;r=x+min(.18,(y-x)*.3);s=y-min(.24,(y-x)*.32)
                event=dict(word=w['word'],channel='tenc',support_s=[x,y],nodes=[[x,0],[r,peak],[s,peak-3],[y,0]],purpose=w['reason']+'；先建立后回收，非音量补丁')
                for tick in range(int(np.floor(x*960))-part['position']-5,int(np.ceil(y*960))-part['position']+6,5):
                    t=(tick+part['position'])/960;val=float(np.interp(t,[x,r,s,y],[0,peak,peak-3,0],left=0,right=0));partcontrol[tick]=round(val)
                parttraces.append(event);controls.append(event)
            wordaudit.append(dict(word=w['word'],char=w['char'],line=w['line'],native_nucleus_s=[va,vb],actual_phones=phones,components=ids,
                body_choice=mode if ids else '主音到达与下一字准备占用短核，明确保持；不塞整周期',reason=w['reason'],
                alternative=w['alternative'],uncertainty=w['timing_uncertainty'],TENC=event or 'retain current model prediction',BREC='retain current model prediction, delta0',VOIC='retain current model prediction, UI100 delta0',SHFC='0, source key retained',DYN='review actual fresh waveform before selecting output support'))
        assert ordered
        # Full-clock decision stages cover head/consonants, every nucleus and
        # trailing carrier, without assigning unvoiced intervals singing truth.
        boundaries=[a]+[max(a,min(b,phoneword[w['word']][0]['start_ms']/1000)) for w in ordered[1:]]+[b]
        decisions=[]
        for j,w in enumerate(ordered):
            x,y=boundaries[j:j+2];assert y>x
            decisions.append(dict(support_s=[x,y],condition=f"word{w['word']} {w['char']}, {len(w['stages'])} melody stages; native nucleus and neighboring syllables explicitly owned",
                choice=f"Own center with finite arrival; {w['body_action']} at native nucleus; non-singing padded carrier held",
                alternative=w['alternative'],reason=w['reason'],uncertainty='Agent has not listened; source timing/detector uncertainties retained; no historical audible evidence',
                component_ids=[c['id'] for c in comps if c['id'].startswith(f"w{w['word']}-")]))
        xs=sorted(nodes);center=[[t,nodes[t],0] for t in xs]
        if not expect:expect=[dict(support_s=[a,b],range_c=[0,1900],purpose='完整入口/主音与退出，短主体明确保持')]
        d=dict(schema=1,origin='agent_designed',support_s=[a,b],center_nodes=center,components=comps,decisions=decisions,expectations=expect);helper.validate(d)
        assert helper.compile_plan(d)['shape_checks_pass'];phrases.append(dict(part_index=pi,position=native['position'],design=d))
      if partcontrol:
        xs=sorted(partcontrol);part['curves'].append(dict(abbr='tenc',xs=xs,ys=[partcontrol[t] for t in xs]))
    assert len(wordaudit)==371 and len({w['word'] for w in wordaudit})==371
    project=RUN/f'score/agent-functions-base{output_name}.ustx';project.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=10**6),encoding='utf8')
    plan=dict(schema_version=2,project=str(project),source_audio=str(RUN/'inputs/source_vocals.wav'),input_hashes={str(p):sha(p) for p in [project,RUN/'inputs/source_vocals.wav',RUN/'inputs/game.json',RUN/'observations/HFA.json',RUN/'observations/FCPE.npz',RUN/'observations/RMVPE.npz']},scope='whole_song',phrases=phrases,
        knowledge_context=dict(path=str(RUN/'design/knowledge_context.json'),sha256=sha(RUN/'design/knowledge_context.json'),decisions=load(RUN/'design/knowledge-decisions.json')))
    save(RUN/f'design/functions{output_name}.json',plan);save(RUN/f'design/native-word-decisions{output_name}.json',wordaudit);save(RUN/f'design/phonation-events{output_name}.json',controls)
    print(len(phrases),'native phrases,371 actual nuclei,',sum(len(p['design']['components']) for p in phrases),'own components',len(controls),'finite TENC choices',flush=True)
    from agent2utau.workflow import compile_functions
    result=compile_functions(RUN/f'design/functions{output_name}.json',RUN/f'compiled{output_name}',cfg());print(result['stage'],result['native_max_error_c'],flush=True)

if __name__=='__main__':{'breathing':breathing,'design':design}[sys.argv[1]]()
