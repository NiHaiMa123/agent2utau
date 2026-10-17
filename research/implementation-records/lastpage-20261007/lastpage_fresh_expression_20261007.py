"""Explicit current-source decisions and native function compilation."""
from lastpage_fresh_design_20261007 import *
from agent2utau.openutau.ustx import load_ustx,save_ustx

def geometry():
    raw=read(OUT/'baseline_phones.json');notes=[];phrases=[];offset=0
    for part in raw['parts']:
        for n in part['notes']:notes.append({**n,'note_index':n['note_index']+offset,'primary_index':n['primary_index']+offset})
        for p in part['phrases']:
            phones=[{**q,'owner_note_indices':[i+offset for i in q['owner_note_indices']],'owner_primary_indices':[i+offset for i in q['owner_primary_indices']]} for q in p['phones']]
            phrases.append({**p,'part_position':part['part_position'],'phones':phones})
        offset+=len(part['notes'])
    return notes,phrases

def audit():
    guarded();words=read(OUT/'chosen_score.json')['words'];bindings=read(OUT/'note_bindings.json');notes,phrases=geometry();rows=[]
    consonants={'b','p','m','f','d','t','n','l','g','k','h','j','q','x','zh','ch','sh','r','z','c','s','y','y0','w'}
    for w in words:
        indices=[b['note_index'] for b in bindings if b['kind']=='sung' and b['word']==w['word']]
        phones=[q for p in phrases for q in p['phones'] if set(q['owner_note_indices'])&set(indices)]
        vowels=[q for q in phones if q['phoneme'].split('/')[-1] not in consonants|{'AP','SP'}]
        assert vowels,(w,phones)
        a=min(q['start_ms'] for q in vowels)/1000;b=max(q['end_ms'] for q in vowels)/1000
        row=dict(word=w['word'],char=w['char'],line=w['line'],native_vowel=[a,b],source_vowel=[w['vowel']['start'],w['vowel']['end']],music=[w['music_start'],w['music_end']],phones=phones,indices=indices)
        rows.append(row)
    dump('native_word_geometry.json',rows)
    for line in range(38):
        print(f'{line:02} '+ ' | '.join(f"{r['word']}{r['char']} V{r['native_vowel'][0]:.3f}-{r['native_vowel'][1]:.3f} d{(r['native_vowel'][1]-r['native_vowel'][0])*1000:.0f}" for r in rows if r['line']==line),flush=True)
    print('MIN_VOWELS',sorted([(round((r['native_vowel'][1]-r['native_vowel'][0])*1000),r['word'],r['char']) for r in rows])[:20],flush=True)

def q(u):
    u=np.clip(u,0.,1.);return u*u*u*(10+u*(-15+6*u))

def hermite(nodes,t):
    n=np.asarray(nodes);t=np.asarray(t);i=np.clip(np.searchsorted(n[:,0],t,side='right')-1,0,len(n)-2)
    a=n[i];b=n[i+1];dt=b[:,0]-a[:,0] if t.ndim else b[0]-a[0]
    x=(t-a[...,0])/dt;x=np.clip(x,0,1)
    return a[...,1]+(-2*x**3+3*x*x)*(b[...,1]-a[...,1])+(x**3-2*x*x+x)*dt*a[...,2]+(x**3-x*x)*dt*b[...,2]

def finite(c,t):
    a,p,b,h=c;return np.where((t>a)&(t<b),h*np.where(t<=p,q((t-a)/(p-a)),1-q((t-p)/(b-p))),0.)

def periodic(c,t):
    a,at,rel,b,d0,dm,d1,f0,f1,phase=c
    depth=d0+(dm-d0)*q((t-a)/(rel-a));depth=np.where(t>rel,dm+(d1-dm)*q((t-rel)/(b-rel)),depth)
    z=np.clip(t-a,0,b-a);theta=phase+2*np.pi*(f0*z+(f1-f0)*z*z/(2*(b-a)))
    env=q((t-a)/(at-a))*q((b-t)/(b-rel));return np.where((t>a)&(t<b),env*depth*np.sin(theta),0.)

def target(plan,t,center_only=False):
    t=np.asarray(t);v=hermite(plan['center_nodes'],t)
    if not center_only:
        for c in plan['finite']:v+=finite(c,t)
        for c in plan['periodic']:v+=periodic(c,t)
    return v

def control(plan,t,abbr):
    t=np.asarray(t);v=np.full(t.shape,100. if abbr=='voic' else 0.)
    for e in plan['controls']:
        if e['abbr']!=abbr:continue
        a,at,rel,b,h=e['parameters'];v+=h*q((t-a)/(at-a))*q((b-t)/(b-rel))
    return v

# Explicit body choices for every current lyric line. Signed numbers select a
# finite excursion in cents; 'vNN' selects independently enveloped periodic
# development. These are Agent choices, not source-F0 samples or author rows.
BODY=[
 [18,24,-12,14,22,-16,'v28'],[-15,27,12,-10,21,-18,'v24'],
 [15,18,-14,20,-13,22,'v23',-12,24,'v34'],[16,25,-11,18,23,-15,'v29'],
 [-14,21,13,25,-16,20,'v27'],[17,21,-15,18,'v25',-17,22,'v36'],
 [20,-14,'v27',17,13,'v24',-18,15,'v25',12,20,'v33'],
 [18,-12,'v26',15,-20,'v28',22,'v35'],
 [21,-13,'v24',18,-15,23,-20,17,'v29',12,20,25],
 [21,28,'v26',-17,26,17,20,24,'v38'],
 [18,23,28,24,-12,23,32,24,'v33'],[25,-17,24,27,26,'v32'],
 [26,-16,22,30,18,13,-16,26,'v40'],[17,24,29,22,-15,25,33,23,20],
 [24,-15,22,31,26,20],[25,-18,21,18,-16,29,24,-18,'v37'],
 [20,26,-14,18,25,-16,'v31'],[-17,30,14,-12,24,-20,29],
 [18,22,-17,21,-14,24,27,-16,27,'v37'],[20,29,-13,20,27,-18,'v33'],
 [-18,25,14,29,-18,23,'v34'],[20,25,-18,20,'v29',-20,27,'v38'],
 [24,-17,'v30',21,15,'v28',-21,17,'v29',14,23,'v37'],
 [22,-15,'v30',18,-24,'v32',25,'v40'],
 [25,-15,'v29',21,-18,27,-23,20,'v33',14,23,28],
 [25,32,'v30',-20,29,20,24,27,'v42'],
 [22,27,32,28,-14,26,36,28,'v37'],[28,-20,27,31,30,'v36'],
 [30,-19,25,35,21,15,-18,29,'v44'],[20,27,33,26,-18,29,37,27,'v30'],
 [28,-18,26,36,30,'v30'],[29,-21,24,21,-18,33,28,-20,'v41'],
 [20,25,30,26,-13,25,34,26,'v35'],[27,-19,25,29,28,'v35'],
 [28,-18,24,33,20,14,-17,28,'v42'],[18,26,31,24,-16,27,35,25,'v29'],
 [26,-17,24,34,28,'v29'],[27,-20,23,20,-17,31,26,-19,'v39']]

# Every selected bearing has its own vowel-relative hold, residual, and arrival.
BEARING={1:(.064,165,.155),4:(.054,110,.145),8:(.052,180,.164),15:(.069,170,.174),
25:(.058,175,.162),28:(.046,112,.132),32:(.065,180,.169),34:(.063,115,.168),
79:(.058,175,.169),89:(.047,175,.149),93:(.077,165,.216),96:(.049,180,.154),
99:(.069,155,.212),102:(.066,165,.183),105:(.090,145,.236),109:(.043,112,.161),
113:(.031,145,.095),117:(.089,170,.230),120:(.063,170,.181),123:(.094,153,.242),
136:(.058,173,.153),139:(.069,110,.173),143:(.061,176,.174),150:(.069,180,.178),
160:(.062,180,.175),163:(.056,110,.147),167:(.073,180,.189),169:(.069,120,.181),
214:(.073,180,.196),224:(.048,180,.151),228:(.083,164,.228),231:(.057,180,.170),
234:(.078,160,.226),237:(.072,170,.196),240:(.102,152,.258),244:(.060,114,.191),
248:(.034,150,.106),252:(.093,173,.241),255:(.071,177,.202),258:(.098,162,.253),
272:(.038,166,.125),276:(.085,152,.219),279:(.056,170,.168),282:(.073,153,.210),
285:(.066,162,.187),288:(.098,148,.249),292:(.052,110,.184),296:(.077,182,.224),
300:(.095,176,.249),303:(.072,173,.203),306:(.102,160,.252)}

# Clause-specific phonation actions. Magnitudes are current candidate deltas,
# not universal descriptors of comfort/effort. Actual feeds are verified later.
SUPPORT={1:8,4:9,11:8,22:10,28:9,34:9,42:8,48:9,51:8,54:10,57:8,60:8,63:9,65:8,
71:8,74:10,79:11,82:10,86:8,89:15,90:11,93:17,99:16,102:14,105:17,109:13,113:15,117:17,120:15,123:18,126:14,131:12,
136:9,139:10,146:9,157:11,163:10,169:10,177:9,183:11,186:10,189:12,192:10,195:10,198:11,200:10,
206:10,209:12,214:13,217:12,221:10,224:18,225:14,228:20,234:19,237:17,240:20,244:16,248:18,252:20,255:18,258:21,261:17,266:15,
272:16,273:12,276:18,282:17,285:15,288:18,292:14,296:17,300:19,303:17,306:20,309:16,314:14}
RELEASE={23:(-5,7),45:(-6,9),65:(-4,6),86:(-5,8),95:(-4,5),101:(-6,8),110:(-8,11),134:(-7,10),
158:(-6,8),172:(-5,7),180:(-7,10),200:(-5,7),221:(-6,9),230:(-5,6),236:(-7,9),245:(-9,12),269:(-8,11),278:(-5,6),284:(-7,9),293:(-8,11),317:(-9,12)}

def design():
    guarded();score=read(OUT/'chosen_score.json');words=score['words'];geo=read(OUT/'native_word_geometry.json');bindings=read(OUT/'note_bindings.json');notes,phrases=geometry();plans=[];decisions=[]
    for pi,ph in enumerate(phrases):
        own=[b for b in bindings if b['part_index']==pi];sung=[b for b in own if b['kind']=='sung'];first=sung[0];last=sung[-1]
        lo=min(q['start_ms'] for q in ph['phones'])/1000-.25;hi=max(q['end_ms'] for q in ph['phones'])/1000+.3
        nodes=[[lo,first['tone']*100-35,0.]];entries=[]
        for k,b in enumerate(sung):
            w=words[b['word']];g=geo[b['word']];a=b['start'];end=min(b['end'],g['native_vowel'][1]);tone=b['tone']*100
            prev=sung[k-1] if k else None;pt=prev['tone']*100 if prev else tone-35
            connected=bool(prev and a-prev['end']<.18);delta=tone-pt
            prep=min(.10,max(.034,(a-(geo[prev['word']]['native_vowel'][0] if prev else a-.3))*.18))
            x=max(nodes[-1][0]+.008,a-prep);vprev=nodes[-1][1]
            if x<a-.003:nodes.append([x,vprev,0.])
            duration=max(.025,end-a);family='short_direct';uncert='Current source attribution is an observation; acoustic realization/listening pending.'
            if b['word'] in BEARING and b['lyric']!='+' and duration>.12:
                hold,res,arr=BEARING[b['word']];arr=min(arr,duration-.030);hold=min(hold,arr*.65)
                lead=tone-res
                nodes.extend([[a,lead,0.],[a+hold,lead+8,100.],[a+arr,tone,0.]])
                family='bearing_then_push';arrival=a+arr
            else:
                arr=min(.105 if abs(delta)>=300 else .067,duration*.32);arr=max(.016,arr)
                residual=min(110 if abs(delta)>=300 else 45,abs(delta)*.22)
                sign=1 if delta>0 else -1
                onset=tone-sign*residual if connected else tone-32
                slope=(tone-onset)/arr*.85 if connected and 0<abs(delta)<500 else 0.
                nodes.extend([[a,onset,slope],[a+arr,tone,0.]])
                family='continuous_velocity' if slope else 'short_direct';arrival=a+arr
            # Leave a separate body and release before the following entrance.
            bodyend=max(arrival+.005,min(end-.032,b['end']-.115))
            if bodyend>arrival+.008:nodes.append([bodyend,tone,0.])
            entries.append(dict(note=b['note_index'],word=b['word'],family=family,arrival=arrival,body_end=bodyend,onset=a,tone=tone,interval_c=delta,connected=connected,
                condition=dict(native_vowel=g['native_vowel'],source_dual=w['stats'],source_unknown=w['unknown'],music_stage=b),
                purpose='Retain the current lyrical attack and develop an interval without an instantaneous step',
                alternative='A longer low bearing at every entry was rejected where it would consume the short nucleus or blur a small interval',uncertainty=uncert))
        if nodes[-1][0]<hi:nodes.append([hi,last['tone']*100-18,0.])
        assert all(b[0]>a[0] for a,b in zip(nodes,nodes[1:])),(pi,nodes)
        plan=dict(context=pi,support=[lo,hi],center_nodes=nodes,entries=entries,finite=[],periodic=[],controls=[])
        for wi in sorted(set(b['word'] for b in sung)):
            w=words[wi];g=geo[wi];e=[e for e in entries if e['word']==wi];a=max(g['native_vowel'][0]+.012,e[0]['arrival']+.012);b=g['native_vowel'][1]-.025
            # The chosen ending of a stage constrains body placement. One vowel
            # with continuations receives separate finite stage gestures.
            choice=BODY[w['line']][w['index']];components=[]
            if isinstance(choice,str):
                depth=float(choice[1:]);width=b-a
                if width>.19:
                    at=a+min(.13,width*.22);rel=b-min(.14,width*.20)
                    c=[a,at,rel,b,depth*.62,depth,depth*.42,5.05 if w['line']<16 else 5.20,5.55 if w['line']<32 else 5.32,.35]
                    plan['periodic'].append(c);components.append(dict(family='variable_periodic',parameters=c))
                else:
                    c=[a,a+(b-a)*.43,b,depth*.7];plan['finite'].append(c);components.append(dict(family='finite_return',parameters=c,reason='Current actual nucleus cannot hold the selected periodic development; use a single excursion'))
            else:
                for j,entry in enumerate(e):
                    x=max(a,entry['arrival']+.008);y=min(b,e[j+1]['onset']-.115 if j+1<len(e) else b)
                    if y>x+.022:
                        c=[x,x+(y-x)*(.44 if choice>0 else .57),y,float(choice)*(1 if j==0 else .72)]
                        plan['finite'].append(c);components.append(dict(family='finite_return',parameters=c))
            if wi in SUPPORT:
                x=g['native_vowel'][0]+.010;y=g['native_vowel'][1]-.012;dt=y-x
                ev=dict(word=wi,abbr='tenc',parameters=[x,x+min(.085,dt*.24),y-min(.09,dt*.25),y,SUPPORT[wi]],purpose='Stage bounded support of current semantic/high-register emphasis; no claim positive means comfortable')
                plan['controls'].append(ev)
                if w['chosen_tone']>=71:
                    plan['controls'].append(dict(word=wi,abbr='brec',parameters=[x,x+min(.085,dt*.24),y-min(.09,dt*.25),y,-3],purpose='Keep high-word core less airy, restore native prediction at both boundaries'))
            if wi in RELEASE:
                te,br=RELEASE[wi];x=max(g['native_vowel'][0]+.10,g['native_vowel'][1]-.38);y=g['native_vowel'][1]-.008;dt=y-x
                for ab,h in [('tenc',te),('brec',br)]:plan['controls'].append(dict(word=wi,abbr=ab,parameters=[x,x+dt*.26,y-dt*.25,y,h],purpose='Finite cadence release with carried vowel retained, no voicing truncation'))
            decisions.append(dict(word=wi,char=w['char'],line=w['line'],context=pi,source_condition=w['stats'],source_unknown=w['unknown'],native_geometry=g['native_vowel'],entry_actions=e,body=components,
                intent='Restrained first verse' if w['line']<10 else 'Carried melodic emphasis and a finite cadence' if w['line']<16 else 'Renew the repeated clause with its own greater body excursion' if w['line']<32 else 'Conclude without abruptly increasing periodic width',
                rejected_alternative='Automatic source-F0 smoothing or a constant body/vibrato template would erase the chosen finite/periodic contrast',
                expectation='Finite excursion returns to the center before preparation; periodic envelope develops then recedes inside the available nucleus',
                controls=[ev for ev in plan['controls'] if ev['word']==wi],voic_choice=100,dyn_choice=0,
                nonpitch_reason='Keep predicted voicing throughout sung core; reserve DYN revision for actual current-wave energy evidence',
                uncertain='No perceptual validation; source HFA/GAME/F0 agreement does not certify lexical identity or exact vowel onset'))
        plans.append(plan)
    assert sorted(d['word'] for d in decisions)==list(range(318))
    dump('agent_function_plans.json',plans);dump('agent_word_decisions.json',sorted(decisions,key=lambda d:d['word']))
    print('DESIGNED',len(decisions),'entries',sum(len(p['entries']) for p in plans),'finite',sum(len(p['finite']) for p in plans),'periodic',sum(len(p['periodic']) for p in plans),'controls',sum(len(p['controls']) for p in plans),flush=True)

def center_compile():
    guarded();doc=load_ustx(OUT/'fresh_score.ustx');plans=read(OUT/'agent_function_plans.json');bindings=read(OUT/'note_bindings.json');idx=0
    for pi,part in enumerate(doc['voice_parts']):
        p=plans[pi]
        for n in part['notes']:
            b=bindings[idx];idx+=1;a=b['start'];z=b['end']
            e=next((e for e in p['entries'] if e['note']==b['note_index']),None)
            finish=e['arrival'] if e else a+.040
            start=max(p['support'][0],a-.10)
            # Each native note owns only its incoming bend. Extending the
            # complete future contour over neighbors causes native additions
            # to count the same outgoing interval twice.
            ts=np.unique(np.r_[np.arange(start,finish,.005),a,finish]);val=target(p,ts,True)
            n['pitch']=dict(snap_first=False,data=[dict(x=float((t-a)*1000),y=float((v-n['tone']*100)/10),shape='l') for t,v in zip(ts,val)])
    save_ustx(doc,OUT/'fresh_center.ustx');bridge('export-pitch',['--project',str(OUT/'fresh_center.ustx'),'--out',str(OUT/'center_pitch.json')],'center_pitch_export')
    print('CENTER_WRITTEN',idx,flush=True)

def preserve_compile_draft():
    import shutil
    dest=OUT/'initial_compile_draft';dest.mkdir(exist_ok=False)
    for name in ['fresh_center.ustx','lastpage_fresh.ustx','center_pitch.json','final_pitch.json','final_phones.json','native_function_validation.json']:
        shutil.copyfile(OUT/name,dest/name)
    dump('compile_repairs.json',dict(initial_absolute_curve_ticks=True,corrected_part_relative_ticks=True,initial_native_center_overlap_max_c=1000,incoming_bend_only_repair=True,no_audio_from_failed_draft=True))

def expression_compile():
    guarded();doc=load_ustx(OUT/'fresh_center.ustx');plans=read(OUT/'agent_function_plans.json');raw=read(OUT/'center_pitch.json');errors=[];resid=[]
    for pi,part in enumerate(doc['voice_parts']):
        ph=[p for p in raw['phrases'] if p['part_position']==part['position']];assert len(ph)==1,ph
        ph=ph[0];t=np.asarray(ph['times_ms'])/1000;base=np.asarray(ph['before_pitd_cents']);p=plans[pi];y=target(p,t);delta=np.rint(y-base).astype(int)
        assert max(abs(delta))<=1200
        xs=(ph['pitch_start_tick']-part['position']+5*np.arange(len(t))).astype(int).tolist()
        part['curves']=[c for c in part['curves'] if c['abbr'].startswith('cl')]+[dict(abbr='pitd',xs=xs,ys=delta.tolist())]
        for ab in ['tenc','brec','voic','dyn']:part['curves'].append(dict(abbr=ab,xs=xs,ys=np.rint(control(p,t,ab)).astype(int).tolist()))
        errors.append(float(max(abs(y-base-delta))));resid.append(int(max(abs(delta))))
    save_ustx(doc,OUT/'lastpage_fresh.ustx')
    for cmd,name in [('export-pitch','final_pitch'),('export-phonemes','final_phones')]:bridge(cmd,['--project',str(OUT/'lastpage_fresh.ustx'),'--out',str(OUT/(name+'.json'))],name+'_export')
    final=read(OUT/'final_pitch.json');native=[]
    for ph,p in zip(final['phrases'],plans):
        err=np.asarray(ph['final_cents'])-target(p,np.asarray(ph['times_ms'])/1000);native.append(float(max(abs(err))));assert max(abs(err))<=.501
    # Pitch/control curves may not change validated phoneme clocks or ownership.
    old=read(OUT/'baseline_phones.json');new=read(OUT/'final_phones.json')
    for a,b in zip(old['parts'],new['parts']):
        assert a['notes']==b['notes']
        for x,y in zip(a['phrases'],b['phrases']):assert x['phones']==y['phones']
    dump('native_function_validation.json',dict(rounding_error_c=max(errors),native_error_c=max(native),max_residual_c=max(resid),all_412_notes_redrawn=True,phoneme_clock_exact=True,source_unknowns=[106],agent_perception=False,naturalness_accepted=False))
    print('FINAL_NATIVE',max(native),'residual',max(resid),flush=True)

def phase():
    import copy
    guarded();doc=load_ustx(OUT/'lastpage_fresh.ustx');plans=read(OUT/'agent_function_plans.json');reports=[]
    for shift in [-2,1,3]:
        d=copy.deepcopy(doc)
        for part in d['voice_parts']:part['position']+=shift
        path=OUT/f'phase_{shift:+}.ustx';save_ustx(d,path)
        dest=OUT/f'phase_{shift:+}.json';bridge('export-pitch',['--project',str(path),'--out',str(dest)],f'phase_export_{shift:+}')
        es=[]
        for ph,p in zip(read(dest)['phrases'],plans):
            t=np.asarray(ph['times_ms'])/1000-shift/960;err=abs(np.asarray(ph['final_cents'])-target(p,t));es.append(float(max(err)))
        reports.append(dict(shift_ticks=shift,max_error_c=max(es),context_errors=es));dump('native_phase_validation.json',reports)
        assert max(es)<3.,reports[-1]
        print('PHASE',shift,max(es),flush=True)

def failure_locations():
    raw=read(OUT/'final_pitch.json');plans=read(OUT/'agent_function_plans.json');worst=[]
    for i,(ph,p) in enumerate(zip(raw['phrases'],plans)):
        t=np.asarray(ph['times_ms'])/1000;y=np.asarray(ph['final_cents']);e=y-target(p,t);inds=np.argsort(abs(e))[-5:]
        worst.extend([(float(abs(e[k])),i,float(t[k]),float(y[k]),float(target(p,np.array([t[k]]))[0])) for k in inds])
    dump('initial_native_failure.json',sorted(worst,reverse=True));print(sorted(worst,reverse=True)[:20])
    for name in ['center_pitch','final_pitch']:
        ph=read(OUT/(name+'.json'))['phrases'][13];t=np.asarray(ph['times_ms'])/1000;k=np.argmin(abs(t-96.806))
        print(name,{key:(v[k] if isinstance(v,list) and len(v)==len(t) else v) for key,v in ph.items() if key not in ['times_ms','notes']})
    doc=load_ustx(OUT/'lastpage_fresh.ustx');part=doc['voice_parts'][13];print('CURVES',[(c['abbr'],min(c['ys']),max(c['ys'])) for c in part['curves']], 'EX',doc['expressions']['pitd'])

if __name__=='__main__':globals()[sys.argv[1]]()
