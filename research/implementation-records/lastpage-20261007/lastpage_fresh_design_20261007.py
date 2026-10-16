"""Current MP3-only score, native geometry, and independently designed functions."""
from pathlib import Path
import sys,json,re,hashlib,subprocess,os
import numpy as np
import soundfile as sf
ROOT=Path('E:/project/agent2utau');OUT=ROOT/'runs/lastpage_fresh_source_20261007'
OU=Path('E:/software/OpenUtau-win-x64_dpV2/OpenUtau-win-x64')
sys.path.insert(0,str(ROOT/'src'))
from lastpage_fresh_source_20261007 import guarded,sha
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(name,d):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def tg(path):
    tiers={}
    for chunk in re.split(r'\bitem \[\d+\]:',Path(path).read_text(encoding='utf-8'))[1:]:
        name=re.search(r'name = "(.*?)"',chunk).group(1);rows=[]
        for q in re.split(r'intervals \[\d+\]:',chunk)[1:]:
            rows.append(dict(start=float(re.search(r'xmin = ([\d.e+-]+)',q).group(1)),end=float(re.search(r'xmax = ([\d.e+-]+)',q).group(1)),label=re.search(r'text = "(.*?)"',q).group(1)))
        tiers[name]=rows
    return tiers
def observations():
    guarded();fc=np.load(OUT/'fcpe.npz');rm=np.load(OUT/'rmvpe.npz');game=read(OUT/'fresh_game.json')['notes'];lines=read(OUT/'lyric_scaffold.json');words=[]
    for ln in lines:
        tiers=tg(OUT/f'hfa/TextGrid/line_{ln["line"]:02}.TextGrid')
        lexical=[r for r in tiers['words'] if r['label'] not in ('','AP','SP','EP')]
        assert [r['label'] for r in lexical]==ln['pinyin'],ln
        for j,(p,ch) in enumerate(zip(lexical,ln['text'])):
            phones=[dict(start=q['start']+ln['start'],end=q['end']+ln['start'],label=q['label']) for q in tiers['phones'] if q['start']>=p['start']-1e-6 and q['end']<=p['end']+1e-6 and q['label'] not in ('','AP','SP','EP')]
            assert phones,(ln['line'],j)
            v=phones[-1];stats={}
            for name,f in [('fcpe',fc),('rmvpe',rm)]:
                mask=(f['times']>=v['start'])&(f['times']<v['end'])&f['voiced'];m=69+12*np.log2(f['f0_hz'][mask]/440)
                stats[name]=dict(n=len(m),median=float(np.median(m)) if len(m) else None,range=np.quantile(m,[.1,.9]).tolist() if len(m) else None)
            candidates=[dict(index=k,start=max(v['start'],g['start']),end=min(v['end'],g['start']+g['dur']),tone=g['tone'],voiced=g['voiced']) for k,g in enumerate(game) if min(v['end'],g['start']+g['dur'])-max(v['start'],g['start'])>.025]
            unknown=bool(min(s['n'] for s in stats.values())<5 or abs((stats['fcpe']['median'] or 0)-(stats['rmvpe']['median'] or 0))>1.5)
            words.append(dict(word=len(words),line=ln['line'],index=j,char=ch,pinyin=p['label'],start=p['start']+ln['start'],end=p['end']+ln['start'],phones=phones,vowel=v,stats=stats,game=candidates,unknown=unknown))
        row=[r for r in words if r['line']==ln['line']]
        print(f"{ln['line']:02} {ln['text']}: "+' | '.join(f"{w['word']}:{w['char']} {w['start']:.3f}-{w['end']:.3f} V{w['vowel']['start']:.3f} F{w['stats']['fcpe']['median'] or 0:.1f}/{w['stats']['rmvpe']['median'] or 0:.1f} G"+','.join(f"{g['tone']:.1f}@{g['start']:.2f}:{g['end']-g['start']:.2f}" for g in w['game'] if g['voiced']) for w in row),flush=True)
    dump('source_observations.json',dict(words=words,lines=lines,provenance='New ASR/current lexical choices/new HFA/unconstrained GAME/dual F0; no historical project'))
    print('WORDS',len(words),'UNKNOWN',sum(w['unknown'] for w in words),flush=True)
def source_atlas():
    guarded()
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc');plt.rcParams['font.family']='Microsoft YaHei'
    obs=read(OUT/'source_observations.json');fc=np.load(OUT/'fcpe.npz');rm=np.load(OUT/'rmvpe.npz');windows=[]
    for ln in obs['lines']:
        ws=[w for w in obs['words'] if w['line']==ln['line']]
        lo=ws[0]['start']-.15;hi=ws[-1]['end']+.15
        for a in np.arange(lo,hi,1.08):windows.append((float(a),float(a+1.1),ln['line']))
    (OUT/'source_atlas').mkdir(exist_ok=True)
    for page in range((len(windows)+4)//5):
        bounds=[]
        for a,b,line in windows[page*5:page*5+5]:
            values=[]
            for f in [fc,rm]:
                m=(f['times']>=a)&(f['times']<=b)&f['voiced'];values.extend((69+12*np.log2(f['f0_hz'][m]/440)).tolist())
            lo=np.floor(min(values)-.5) if values else 60;hi=np.ceil(max(values)+.5) if values else 64
            bounds.append((lo,hi))
        heights=[(hi-lo)*.44 for lo,hi in bounds];height=sum(heights)+.55*len(heights)+.4
        fig=plt.figure(figsize=(18,height),dpi=100);top=height-.4
        for (a,b,line),(lo,hi),hh in zip(windows[page*5:page*5+5],bounds,heights):
            top-=hh;ax=fig.add_axes([.06,top/height,.88,hh/height]);top-=.55
            mids=[]
            for name,f,color in [('FCPE',fc,'#448cc7'),('RMVPE',rm,'#dc8052')]:
                m=(f['times']>=a)&(f['times']<=b)&f['voiced'];y=69+12*np.log2(f['f0_hz'][m]/440);mids.extend(y.tolist());ax.plot(f['times'][m],y,'.',color=color,ms=2,label=name)
            for w in obs['words']:
                if w['end']<a or w['start']>b:continue
                v=w['vowel'];ax.axvspan(max(a,v['start']),min(b,v['end']),color='green',alpha=.06)
                for g in w['game']:
                    if g['voiced'] and g['end']>=a and g['start']<=b:ax.plot([max(a,g['start']),min(b,g['end'])],[g['tone']]*2,color='gray',alpha=.5,lw=1)
                ax.text(max(a,w['start']),.98,f"{w['word']} {w['char']}",transform=ax.get_xaxis_transform(),va='top',fontsize=9)
            ax.set_ylim(lo,hi);ax.set_xlim(a,b);ax.grid(alpha=.2);ax.set_title(f'Source line {line:02} | current MP3 evidence',fontsize=9)
        fig.savefig(OUT/f'source_atlas/page_{page:02}.png');plt.close(fig)
    dump('source_atlas_manifest.json',dict(pages=(len(windows)+4)//5,windows=windows,scale_x_px_per_s=1440,scale_y_px_per_st=44,source_only=True))
    print('SOURCE_PAGES',(len(windows)+4)//5,flush=True)
def bridge(command,args,tag):
    exe=OU/('a2u-sourceonly-diag.exe' if command=='export-render-probe' else 'a2u-bridge.exe')
    proc=subprocess.run([str(exe),command,*args],cwd=OU,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=1500)
    (OUT/(tag+'.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8')
    result=json.loads(proc.stdout.strip().splitlines()[-1]);result['exit_code']=proc.returncode;dump(tag+'.json',result)
    assert result.get('ok') is not False and proc.returncode==0,result
    return result
def tick(t):return round(t*960)
def expression(a,lo,hi,default,typ='Curve',**kw):
    return dict(name=a,abbr=a,type=typ,min=lo,max=hi,default_value=default,is_flag=False,flag='',skip_output_if_default=False,**kw)
def score():
    guarded();obs=read(OUT/'source_observations.json');words=obs['words']
    tones=[
      [59,64,66,66,68,61,66],[59,64,66,66,68,59,64],[59,64,63,61,63,64,63,64,68,68],
      [59,64,66,66,68,61,66],[59,64,66,68,66,66,64],[59,61,63,64,63,64,66,64],
      [64,63,64,63,64,66,63,61,59,56,63,64],[64,63,64,64,63,61,63,64],
      [64,63,64,63,64,66,63,61,59,59,66,64],[64,69,68,64,69,68,64,66,68],
      [59,64,71,71,68,71,73,68,66],[71,68,71,73,66,64],[71,68,71,73,64,66,68,71,68],
      [59,64,71,71,68,71,73,68,66],[71,68,71,73,66,64],[71,69,68,64,59,69,68,64,64],
      [59,64,66,66,68,61,66],[59,64,66,66,68,59,64],[59,64,63,61,63,64,63,64,68,68],
      [59,64,66,66,68,61,66],[59,64,66,68,66,66,64],[59,61,63,64,63,64,66,64],
      [64,63,64,63,64,66,63,61,59,56,63,64],[64,63,64,64,63,61,63,64],
      [64,63,64,63,64,66,63,61,59,59,66,64],[64,69,68,64,69,68,64,66,68],
      [59,64,71,71,68,71,73,68,66],[71,68,71,73,66,64],[71,68,71,73,64,66,68,71,68],
      [59,64,71,71,68,71,73,68,66],[71,68,71,73,66,64],[71,69,68,64,59,69,68,64,64],
      [59,64,71,71,68,71,73,68,66],[71,68,71,73,66,64],[71,68,71,73,64,66,68,71,68],
      [59,64,71,71,68,71,73,68,66],[71,68,71,73,66,64],[71,69,68,64,59,69,68,64,64]]
    # These are current-recording musical selections. Small fractional GAME
    # approaches remain designed entrances, rather than separate lyric onsets.
    continuations={36:[(33.72,64)],44:[(38.98,64)],94:[(76.38,66)],100:[(79.80,64)],118:[(90.14,66)],124:[(93.51,64)],
      171:[(147.20,64)],229:[(186.12,66)],235:[(189.52,64)],253:[(199.81,66)],259:[(203.16,64)],
      277:[(213.53,66)],283:[(216.95,64)],307:[(231.07,64)]}
    choices=[]
    for w in words:
        assert len(tones[w['line']])==len(obs['lines'][w['line']]['text'])
        w['chosen_tone']=tones[w['line']][w['index']];w['music_start']=w['vowel']['start']
        if w['char']=='重':
            choices.append(dict(word=w['word'],old_pinyin=w['pinyin'],new_pinyin='chong',reason='Current semantic repetition in chong yan/chong xie requires chong, not the automatic isolated-character zhong reading',source_HFA_pinyin_preserved=True))
            w['pinyin']='chong'
        if w['word']==106:
            w['music_start']=82.56
            choices.append(dict(word=106,old_vowel=[w['vowel']['start'],w['end']],new_music_start=82.56,
                reason='16ms HFA mei nucleus conflicts with complete repeated mei luo phrase and current low GAME segment; choose a full mei note from current contextual acoustic onset hypothesis',source_timing_verified=False))
        w['stages']=[(w['music_start'],w['chosen_tone'])]+continuations.get(w['word'],[])
        w['center_reason']='Current dual F0/GAME ordered music, Agent-selected written center; fractional approach is separately designed, no source contour fit.'
    for i,w in enumerate(words):
        w['music_end']=words[i+1]['music_start'] if i+1<len(words) and words[i+1]['start']-w['end']<.18 else w['end']
        if w['word']==106:w['music_end']=words[107]['music_start']
        if w['word']==148:
            choices.append(dict(word=148,old_music_end=w['music_end'],new_music_end=134.13,
                reason='Choose a finite release of the second verse cadence to make room for a linked preparatory inhale before the next full sentence; source HFA labels retained',source_timing_verified=False))
            w['music_end']=134.13
        if w['word'] in (221,269):
            end={221:181.99,269:209.49}[w['word']]
            choices.append(dict(word=w['word'],old_music_end=w['music_end'],new_music_end=end,
                reason='Current source atlas shows the same preceding sustained center continuing beyond the ASR-limited HFA clip; preserve its carried nucleus and leave the next clause breath/consonant slot',source_timing_verified=False,source_unknown_retained=True))
            w['music_end']=end
        assert w['music_end']>w['music_start'],w
    groups=[]
    for line in range(38):
        if line in (1,4,17,20):groups[-1].append(line)
        else:groups.append([line])
    # Individually chosen first-pass preparatory inhalations; no fixed cap,
    # no source NLL blob interpreted as physiological truth.
    breath_lengths=[.29,.24,.27,.31,.22,.26,.20,.28,.16,.18,.27,.19,.22,.25,.28,.30,.24,.26,.19,.31,.21,.23,.17,.20,.29,.18,.23,.25,.21,.17,.28,.19,.22,.26]
    assert len(groups)==len(breath_lengths)
    parts=[];bindings=[];breaths=[]
    def note(a,b,tone,lyric,word,kind,part_index,anchor):
        assert tick(b)>tick(a),(a,b,lyric,word)
        bindings.append(dict(note_index=len(bindings),part_index=part_index,word=word,kind=kind,start=tick(a)/960,end=tick(b)/960,tone=tone,lyric=lyric))
        return dict(position=tick(a)-anchor,duration=tick(b)-tick(a),tone=tone,lyric=lyric,
            pitch=dict(snap_first=False,data=[dict(x=0.,y=0.,shape='l'),dict(x=10.,y=0.,shape='l')]),
            vibrato=dict(length=0,period=175,depth=25,**{'in':10,'out':10},shift=0,drift=0,vol_link=0),
            tuning=0,phoneme_expressions=[],phoneme_overrides=[])
    for gi,(lines,length) in enumerate(zip(groups,breath_lengths)):
        ws=[w for w in words if w['line'] in lines];first=ws[0];previous=words[first['word']-1] if first['word'] else None
        consonant_start=first['music_start']-min(.17,max(.055,first['music_start']-first['start']))
        be=consonant_start-.045;ba=be-length
        if previous and ba<previous['music_end']+.025:ba=previous['music_end']+.025
        assert be-ba>.06,(gi,ba,be,first)
        anchor=tick(ba)-480;own=[note(ba,be,first['chosen_tone'],'AP',first['word'],'breath',gi,anchor)]
        breaths.append(dict(context=gi,start=ba,end=be,before_word=first['word'],after_word=previous['word'] if previous else None,
            purpose='Prepare the next semantic clause without cutting its preceding carried nucleus',confirmed_source_inhale=False))
        for w in ws:
            a=w['music_start']
            gap=tick(a)-(anchor+own[-1]['position']+own[-1]['duration'])
            assert gap>=0,(w,gap)
            if gap:own.append(note((anchor+own[-1]['position']+own[-1]['duration'])/960,a,w['chosen_tone'],'SP',w['word'],'silence',gi,anchor))
            stages=w['stages']
            for j,(t,tone) in enumerate(stages):
                end=stages[j+1][0] if j+1<len(stages) else w['music_end']
                own.append(note(t,end,tone,w['pinyin'] if j==0 else '+',w['word'],'sung',gi,anchor))
        last=own[-1]['position']+own[-1]['duration']
        parts.append(dict(name='phrase_'+str(gi),comment='Fresh source-only semantic context, preparatory AP linked to following sung clause',track_no=0,position=anchor,duration=last+480,notes=own,
            curves=[dict(abbr=a,xs=[-1920,last+1920],ys=[v,v]) for a,v in [('cl03',75),('cl05',25)]]))
    names=['','Yousa_Bright','Yousa_Cute','Yousa_Normal','Yousa_Whisper','Yousa_Classic']
    ex={a:expression(a,l,h,d) for a,l,h,d in [('pitd',-1200,1200,0),('dyn',-240,120,0),('tenc',-100,100,0),('brec',-100,100,0),('voic',0,100,100),('shfc',-12,12,0)]}
    ex['clr']=expression('clr',0,5,0,'Options',options=names)
    for i in range(1,6):ex[f'cl{i:02}']=expression(f'cl{i:02}',0,100,0)
    doc=dict(name='最后一页 · 原曲重新制作 · 独立函数设计',comment='New from MP3; no historical LastPage or author project read; original key and recording timeline',
        ustx_version='0.9',bpm=120,resolution=480,beat_per_bar=4,beat_unit=4,tempos=[dict(position=0,bpm=120)],time_signatures=[dict(bar_position=0,beat_per_bar=4,beat_unit=4)],expressions=ex,
        tracks=[dict(singer='YousaV1.65c',phonemizer='OpenUtau.Core.DiffSinger.DiffSingerChinesePhonemizer',renderer_settings=dict(renderer='DIFFSINGER',resampler='',wavtool=''),track_name='Fresh lead',track_color='#669DC7',volume=0,pan=0,mute=False,solo=False,voice_color_names=names)],voice_parts=parts,wave_parts=[])
    from agent2utau.openutau.ustx import save_ustx
    save_ustx(doc,OUT/'fresh_score.ustx');dump('note_bindings.json',bindings)
    dump('chosen_score.json',dict(words=words,groups=groups,lines=obs['lines'],music_choices=choices,breaths=breaths,source_unknowns=[w['word'] for w in words if w['unknown']],
        default_tempo_clock='120 BPM / 480 ticks is a millisecond storage clock, not estimated song tempo',speaker={'Yousa_Normal':75,'Yousa_Classic':25},
        speaker_reason='New ballad choice: Normal articulation with a limited Classic component to retain weight in restrained phrases and avoid a full Bright high register; candidate not listening accepted'))
    print('SCORE_READY',len(words),len(bindings),len(parts),flush=True)
def native():
    guarded()
    for command,name in [('export-phonemes','baseline_phones'),('export-pitch','baseline_pitch')]:
        bridge(command,['--project',str(OUT/'fresh_score.ustx'),'--out',str(OUT/(name+'.json'))],name+'_export')
    print('NATIVE_CLOCK_READY',len(read(OUT/'baseline_pitch.json')['phrases']),flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
