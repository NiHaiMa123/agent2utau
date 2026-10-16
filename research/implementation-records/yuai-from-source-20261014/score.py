"""Current Yuai observations, explicit musical ledger and independent score."""
from source import ROOT,RUN,load,save,sha,ref
from pathlib import Path
import numpy as np
import yaml,subprocess,shutil,sys,os

def isolate():
    from agent2utau.resources.config import load_config
    original=Path(load_config()['openutau_dir']);out=RUN/'native-runtime';out.mkdir(exist_ok=False)
    resources=[]
    # Current installed executable/libraries/configuration only. No generated
    # cache, log, project, audio, historical helper output or author data.
    for p in original.iterdir():
        if p.is_file() and (p.suffix.lower() in ['.dll','.json','.exe','.config'] or p.name=='portable') and not p.name.startswith('a2u-'):
            shutil.copyfile(p,out/p.name);resources.append(dict(name=p.name,sha256=sha(p)))
    for name in ['Singers','Dependencies','Resamplers']:
        if (original/name).exists():
            q=subprocess.run(['cmd','/c','mklink','/J',str(out/name),str(original/name)],capture_output=True);assert q.returncode==0,q.stdout
    for name in ['a2u-bridge.exe','a2u-bridge.dll','a2u-bridge.runtimeconfig.json','a2u-bridge.deps.json']:
        shutil.copyfile(original/name,out/name);resources.append(dict(name=name,sha256=sha(original/name)))
    result=subprocess.run([str(out/'a2u-bridge.exe'),'doctor'],cwd=out,capture_output=True,encoding='utf8',errors='replace')
    (out/'doctor.log').write_text(result.stdout+result.stderr,encoding='utf8');r=json_last(result.stdout)
    assert r['ok'] and Path(r['cache_path']).is_relative_to(RUN),r
    assert 'YousaV1.65c' in r['singers_found'],r
    save(RUN/'inputs/native-runtime.json',dict(original_current_install=str(original),isolated=str(out),cache_path=r['cache_path'],
        resources=resources,resource_links=['Singers','Dependencies','Resamplers'],old_cache_copied=False,old_generated_data_read=False,doctor=r))
    print('New native cache:',r['cache_path'],flush=True)

def json_last(s):
    import json
    return json.loads(s.strip().splitlines()[-1])

def observe():
    hfa=load(RUN/'observations/HFA.json')['words'];lyrics=load(RUN/'observations/lyric-judgement.json');game=load(RUN/'inputs/game.json')
    english=load(RUN/'observations/HFA-English-joint.json')['rows']
    f0s=[np.load(RUN/f'observations/{name}.npz') for name in ['FCPE','RMVPE']]
    rows=[]
    for w,h in zip(lyrics['words'],hfa):
        phones=h['phones'];nucleus=phones[-1] if w['language']=='zh' else phones[1]
        start=nucleus['start'];end=h['end'];flags=[]
        if w['word'] in [107,108,109,270,271,272]:
            j=0 if w['word']<200 else 1;es=english[j]['words'];rainie=next(z for z in es if z['text']=='rainie');love=next(z for z in es if z['text']=='love')
            label={'Rai':'ey','nie':'iy','Love':'ah'}[w['char']];p=next(z for z in (love if w['char']=='Love' else rainie)['phones'] if z['label']==label)
            start=p['start'];end=p['end'];flags.append('joint-English observation replaces split clock, raw retained')
            # Source voiced music sustains past short HFA iy; independent word
            # continuation retained until following /l/ preparation, not 15ms.
            if w['word']==271:end=184.9;flags.append('iy 15ms HFA unresolved; chosen nucleus continues into current GAME 184.75-184.99 stage')
        if end-start<.055:flags.append('HFA nucleus too short: music boundary reviewed separately')
        next_h=hfa[w['word']+1] if w['word']+1<len(hfa) else None
        if next_h and lyrics['words'][w['word']+1]['line']==w['line']:
            nh=next_h['phones'];end=max(end,nh[-1]['start']) if end-start<.055 else end
        candidates=[dict(index=i,**n) for i,n in enumerate(game) if n['voiced'] and n['start']+n['dur']>start+.025 and n['start']<end-.025]
        stats={}
        for name,z in zip(['FCPE','RMVPE'],f0s):
            mask=(z['times']>=start+.025)&(z['times']<=end-.025)&z['voiced']&(z['f0_hz']>0)
            tones=69+12*np.log2(z['f0_hz'][mask]/440)
            stats[name]=dict(frames=len(tones),median_midi=float(np.median(tones)) if len(tones) else None,
                range_midi=[float(np.percentile(tones,10)),float(np.percentile(tones,90))] if len(tones) else None)
        rows.append(dict(**w,HFA=h,music_nucleus_observation_s=[start,end],GAME=candidates,F0=stats,flags=flags))
    save(RUN/'observations/music-evidence.json',rows)
    for line in lyrics['lines']:
        z=[w for w in rows if w['line']==line['line']]
        print(line['line'],line['text'],':',' '.join(f"{w['word']}{w['char']}[{w['music_nucleus_observation_s'][0]:.2f}/{w['music_nucleus_observation_s'][1]-w['music_nucleus_observation_s'][0]:.2f}:"+','.join(f"{q['tone']:.0f}@{q['start']:.2f}" for q in w['GAME'])+f";F{w['F0']['RMVPE']['median_midi']}]" for w in z),flush=True)

# Agent decisions after reviewing all 60 lines and the current-source conflicts.
# No detector-residual array is used to construct the designed contour.
CLOCK={25:(35.20,35.39),88:(62.75,63.35),140:(86.75,87.33),164:(124.65,125.03),172:(131.22,131.45),173:(131.45,131.77),271:(184.62,184.99),274:(186.53,186.70),370:(234.48,237.45)}
TONES={25:59,76:66,99:66,131:64,164:64,172:64,173:68,197:61,242:64,270:72,273:68,278:68,283:68,296:64,300:68,311:64,315:68,358:66}
SUPPRESS_STAGE={62,78,99,131,141,149,150,173,197,211,215,253,257,271,296,305,309,311,322,337,349,353,357,358,370}
# Stages deliberately retained/reinterpreted after comparison with the fresh
# dual detectors; 370's 65 passing stage is a turn, not another sustained note.
STAGES={2:[(17.45,61),(17.59,63)],7:[(21.78,67),(21.93,68)],12:[(24.13,64),(24.28,66)],13:[(24.59,61),(24.72,63)],19:[(29.38,61),(29.50,63)],
95:[(66.86,71),(67.69,64)],101:[(69.90,68),(70.35,61)],103:[(71.01,64),(71.33,63)],107:[(72.85,72),(73.21,71)],132:[(83.22,66),(83.31,68)],
142:[(87.84,71),(88.68,64)],153:[(93.91,68),(94.33,61)],161:[(98.34,64),(98.69,63)],166:[(125.39,61),(125.52,63)],175:[(132.13,64),(132.25,66)],176:[(132.57,61),(132.73,63)],
258:[(177.86,71),(178.79,64)],264:[(180.89,68),(181.32,61)],270:[(183.86,72),(184.30,71)],271:[(184.62,69),(184.75,71)],
305:[(198.87,71),(199.76,64)],316:[(204.91,68),(205.35,61)],324:[(209.35,64),(209.73,63)],349:[(222.88,71),(223.76,64)],360:[(228.90,68),(229.33,61)],368:[(233.36,64),(233.72,63)],370:[(234.48,66),(235.20,64)]}
# Independent musical choices. Each line has its focal syllables, final-nucleus
# action, depth and physical frequency; repeated lyrics have distinct choices.
LINE_CHOICES=[
 ('天气','late',19,4.7),('多变表情','return',11,0),('下雨','settle',8,0),('雨哭泣','late',23,4.9),('看清','return',14,0),('不想看清','early',18,5.0),
 ('离开','return',9,0),('安静抽离','settle',7,0),('不忍揭晓剧情','return',11,0),('泪心里','return',12,0),('学会放弃','late',25,5.1),
 ('声音','return',10,0),('清晰','return',12,0),('呼吸渗爱里','late',19,5.05),('真希望不停','return',13,0),('想念继续','return',12,0),('爱透明','settle',8,0),('勇气','return',11,0),('Love','late',24,4.85),
 ('雨滴','return',11,0),('累积','return',12,0),('湿气储存记忆','return',13,0),('真希望不停','return',15,0),('雨爱秘密','settle',8,0),('一直延续','return',12,0),('相信看到','return',13,0),('彩虹美丽','two',27,4.95),
 ('冷空气','late',21,4.85),('窒息','return',12,0),('无法呼吸','early',18,4.9),('距离','late',24,5.0),('彻底','return',13,0),('消失无息','late',20,4.95),
 ('离开','return',10,0),('安静抽离','settle',8,0),('不忍揭晓剧情','return',12,0),('泪心里','return',13,0),('学会放弃','late',27,5.1),
 ('声音','return',12,0),('清晰','return',13,0),('呼吸渗爱里','late',23,5.15),('真希望不停','return',15,0),('想念继续','return',13,0),('爱透明','settle',10,0),('勇气','return',13,0),('Love','early',27,5.1),
 ('雨滴','return',12,0),('累积','return',14,0),('湿气储存记忆','return',15,0),('真希望不停','return',16,0),('雨爱秘密','settle',10,0),('一直延续','return',14,0),('相信看到','return',15,0),('彩虹美丽','two',29,5.05),
 ('湿气储存记忆','return',16,0),('真希望不停','return',17,0),('雨爱秘密','settle',9,0),('一直延续','return',13,0),('相信看到','return',13,0),('彩虹美丽','two',26,4.85)]

def build():
    from agent2utau.openutau.build import build_project,sec_to_tick
    rows=load(RUN/'observations/music-evidence.json');ly=load(RUN/'observations/lyric-judgement.json');ledger=[]
    for w in rows:
        i=w['word'];a,b=CLOCK.get(i,w['music_nucleus_observation_s']);events=[n for n in w['GAME'] if n['start']>=a-.075 and n['start']<b-.03]
        if events:
            a=events[0]['start'] if abs(events[0]['start']-a)<.065 else a
            tone=TONES.get(i,round(events[0]['tone']))
        else:
            tone=TONES.get(i,round(w['F0']['RMVPE']['median_midi'] or 68))
        stages=STAGES.get(i,[(a,tone)])
        # Ledger uses explicitly reviewed retained musical stages; no raw F0
        # target sampling, profile selection or imported speaker recipe.
        assert all(t>=a-.075 and a<=t<b for t,p in stages[1:]);stages[0]=(a,stages[0][1]);b=max(b,a+.075)
        nextrow=rows[i+1] if i+1<len(rows) else None
        if nextrow and nextrow['line']==w['line']:
            na=CLOCK.get(i+1,nextrow['music_nucleus_observation_s'])[0]
            es=[n for n in nextrow['GAME'] if abs(n['start']-na)<.065]
            if es:na=min(es,key=lambda n:abs(n['start']-na))['start']
            if na-b<.24:b=na
            b=min(b,na)
        focal,mode,depth,hz=LINE_CHOICES[w['line']];is_final=not nextrow or nextrow['line']!=w['line']
        ledger.append(dict(word=i,char=w['char'],line=w['line'],context=w['context'],language=w['language'],pinyin=w['pinyin'],
            source_evidence=ref(RUN/'observations/music-evidence.json'),start=a,end=b,stages=[dict(start=t,tone=p) for t,p in stages],
            identity_decision='Retain reviewed GAME melodic stages and source key; correct collapsed HFA clocks independently where declared.',
            timing_uncertainty=w['flags']+(['Agent clock correction; source HFA retained'] if i in CLOCK else []),
            detector_conflict='GAME retained as musical identity; two detectors remain fallible observations' if w['F0']['RMVPE']['median_midi'] and abs(w['F0']['RMVPE']['median_midi']-stages[0][1])>1.1 else 'no major first-stage conflict',
            role='focal' if w['char'] in focal else 'link',final=is_final,
            body_action=mode if is_final else 'return' if w['char'] in focal else 'carry',
            depth_c=depth if is_final else 9 if w['char'] in focal else 4,rate_hz=hz if is_final else 0,
            reason=f"{ly['lines'][w['line']]['text']}: "+('最后元音收住并接下一句/留余韵' if is_final else '语义重心建立清晰元音，随后回收' if w['char'] in focal else '短连接字承接主音，避免另起完整周期'),
            alternative='整字恒速同深颤音/依源残差逐帧跟随',rejection='当前字的承载、词内转音和下一入口需要独立安排，残差不等于演唱目标',
            phonation='Normal70/Bright30 current independent hypothesis; model base retained on short links, finite TENC only on selected sustained focal nuclei; VOIC/BREC/SHFC held at defaults pending actual outputs'))
    save(RUN/'design/word-ledger.json',ledger)
    segments=[];breaths=[]
    for c in ly['contexts']:
        units=[w for w in ledger if w['context']==c['context']];notes=[]
        first=units[0]['start'];prev=ledger[units[0]['word']-1]['end'] if units[0]['word'] else 0
        if first-prev>.38:
            apstart=max(prev+.09,first-.46);apend=first-.13
            notes.append(dict(start=apstart,end=apend,dur=apend-apstart,tone=units[0]['stages'][0]['tone'],lyric='AP'))
            notes.append(dict(start=apend,end=first,dur=first-apend,tone=units[0]['stages'][0]['tone'],lyric='SP'))
            breaths.append(dict(context=c['context'],span_s=[apstart,apend],purpose='本句吸气和下一辅音准备，同上下文；主动选择，非HFA吸气真值'))
        for w in units:
            for j,s in enumerate(w['stages']):
                end=w['stages'][j+1]['start'] if j+1<len(w['stages']) else w['end']
                text=w['pinyin'] if w['language']=='zh' else {'Rai':'Rai[en/r en/ey]','nie':'nie[en/n en/iy]','Love':'Love[en/l en/ah en/v]'}[w['char']]
                notes.append(dict(start=s['start'],end=end,dur=end-s['start'],tone=s['tone'],lyric=text if j==0 else '+',word=w['word']))
        notes.sort(key=lambda n:n['start'])
        segments.append(dict(start_sec=notes[0]['start'],part_start_sec=max(0,notes[0]['start']-.15),notes=notes))
    p=RUN/'score/agent-score.ustx';build_project('雨爱 / independent source design 20261014',segments,p)
    doc=yaml.safe_load(p.read_text(encoding='utf8'));colors=['','Yousa_Bright','Yousa_Cute','Yousa_Normal','Yousa_Whisper','Yousa_Classic'];doc['expressions']['clr'].update(options=colors,max=5,default_value=3);doc['tracks'][0]['voice_color_names']=colors
    doc['cache_dir']=str(RUN/'native-runtime/Cache');doc['comment']='New source-only musical judgement; no author or historical expression data. Engineering clock 120 BPM, not estimated music tempo.'
    for part,seg in zip(doc['voice_parts'],segments):
        prevtone=part['notes'][0]['tone']
        for n,raw in zip(part['notes'],seg['notes']):
            n['phoneme_expressions']=[dict(index=i,abbr='clr',value=3) for i in range(8)]
            a=raw['start'];p0=prevtone*100;p1=n['tone']*100;gap=abs(p1-p0)
            entry=.12 if gap>=700 else .065 if gap>=200 else .045
            n['pitch']=dict(snap_first=False,data=[dict(x=-70,y=(p0-p1)/10,shape='io'),dict(x=entry*1000,y=0,shape='io')]);prevtone=n['tone']
        part['curves']=[dict(abbr=abbr,xs=[-500,part['duration']+500],ys=[value,value]) for abbr,value in [('cl01',30),('cl03',70)]]
    p.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=10**6),encoding='utf8')
    save(RUN/'score/score.json',dict(tempo_source='fixed engineering 120 BPM',original_key=True,segments=segments,breaths=breaths,
        sung_units=len(ledger),notes=sum(len(s['notes']) for s in segments),voice_choice=dict(Normal=70,Bright=30),history_or_author_used=False,score=ref(p)))
    print('New score',len(ledger),'units',sum(len(s['notes']) for s in segments),'notes',len(breaths),'AP contexts',flush=True)

if __name__=='__main__':{'isolate':isolate,'observe':observe,'build':build}[sys.argv[1]]()
