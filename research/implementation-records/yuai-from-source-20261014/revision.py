"""Current production breath-budget correction; prior current candidates kept."""
from source import ROOT,RUN,load,save,ref
from design import export,design
import copy,yaml,sys
from agent2utau.openutau.build import sec_to_tick

def prepare():
    ledger=load(RUN/'design/word-ledger.json');ledger[140]['end']=87.16;ledger[140]['timing_uncertainty'].append('源GAME停86.75/0.37支持主体至87.12；独立选择87.16释放而非87.33混响延展，给87.50雨留换气')
    save(RUN/'design/word-ledger-breath-final.json',ledger)
    doc=yaml.safe_load((RUN/'score/agent-score-breath.ustx').read_text(encoding='utf8'));part=doc['voice_parts'][5]
    finalnote=next(n for n in part['notes'] if abs((n['position']+part['position'])/960-86.75)<.002);finalnote['duration']=sec_to_tick(87.16)-part['position']-finalnote['position']
    events=[(6,87.20,87.36,87.50,59),(13,198.18,198.35,198.49,59),(15,222.217,222.317,222.46,59)]
    for pi,a,b,c,tone in events:
        part=doc['voice_parts'][pi];prev_anchor=part['position'];new_anchor=sec_to_tick(a-.10)
        if new_anchor<prev_anchor:
            delta=prev_anchor-new_anchor;part['position']=new_anchor
            for n in part['notes']:n['position']+=delta
            for curve in part['curves']:curve['xs']=[x+delta for x in curve['xs']]
            part['duration']+=delta
        n=copy.deepcopy(part['notes'][0]);n.update(position=sec_to_tick(a)-part['position'],duration=sec_to_tick(b)-sec_to_tick(a),lyric='AP',tone=tone);n['pitch']=dict(snap_first=False,data=[dict(x=-40,y=0,shape='io'),dict(x=40,y=0,shape='io')]);part['notes'].append(n)
        n2=copy.deepcopy(n);n2.update(position=sec_to_tick(b)-part['position'],duration=sec_to_tick(c)-sec_to_tick(b),lyric='SP');part['notes'].append(n2);part['notes'].sort(key=lambda n:n['position'])
    p=RUN/'score/agent-score-breath-final.ustx';p.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=10**6),encoding='utf8')
    save(RUN/'design/breath-budget-final-revision.json',dict(previous=ref(RUN/'design/breath-budget.json'),new_events=events,
        finalword140_original_end_s=87.33,selected_release_s=87.16,source_basis='Current original GAME voiced停 ends87.12; HFA end87.33 included uncertain tail',
        original_song_clock_retained=True,goal='Remove >24s continuous-singing burdens while preserving all 371 syllables and every retained melodic stage',historical_data_used=False))
    phones=RUN/'native-input/breath-final-phones.json';pitch=RUN/'native-input/breath-final-pitch.json';export('export-phonemes',p,phones);export('export-pitch',p,pitch)
    design(p,phones,pitch,RUN/'design/word-ledger-breath-final.json','-breath-final')

def level():
    # Re-resolve the independently chosen musical envelope on the NEW actual
    # nuclei; do not transplant a previous candidate's sampled DYN arrays.
    import envelope
    # The original builder is explicit about its current paths. A private
    # current-production staging tree contains ONLY allowed/new inputs.
    stage=RUN/'final-stage';stage.mkdir();import shutil
    for name in ['inputs','observations','score','design','native-input','evaluation']:
        (stage/name).mkdir()
    def cp(src,dest):shutil.copyfile(RUN/src,stage/dest)
    (stage/'compiled').mkdir();shutil.copyfile(RUN/'compiled-breath-final/project.ustx',stage/'compiled/project.ustx')
    for name in ['pitch.json','phones.json']:shutil.copyfile(RUN/f'compiled-breath-final/{name}',stage/f'compiled/{name}')
    for src,dest in [('design/native-word-decisions-breath-final.json','design/native-word-decisions.json'),('design/word-ledger-breath-final.json','design/word-ledger.json'),('design/functions-breath-final.json','design/functions.json'),('design/knowledge_context.json','design/knowledge_context.json'),('design/knowledge-decisions.json','design/knowledge-decisions.json'),('evaluation/whole-vowel-energy-raw-final.json','evaluation/whole-vowel-energy-raw.json')]:cp(src,dest)
    # Context sources and bound raw source paths remain the original new RUN;
    # no copies of source audio/models/old outputs are needed for this pass.
    envelope.RUN=stage
    # Compile outputs stay in final-stage; native cfg remains original isolated
    # cache. Adjust score-path removal for the source plan before compilation.
    plan=load(stage/'design/functions.json');plan['input_hashes'].pop(str(RUN/'score/agent-functions-base-breath-final.ustx'))
    plan['input_hashes'][str(stage/'score/agent-functions-base.ustx')]=plan['input_hashes'].get(str(stage/'score/agent-functions-base.ustx'),'unused')
    (stage/'design/functions.json').write_text(__import__('json').dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
    envelope.build()
    import subprocess
    r=subprocess.run(['cmd','/c','mklink','/J',str(stage/'native-runtime'),str(RUN/'native-runtime')],capture_output=True);assert r.returncode==0
    envelope.render('level-final',RUN/'design/native-word-decisions-breath-final.json')
    print('Final stage built',stage,flush=True)

if __name__=='__main__':{'prepare':prepare,'level':level}[sys.argv[1]]()
