"""v9 最终组装：编译后的工程 + 音色层(clr/clNN) + 发声层(dyn/voic/brec/tenc)。"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
doc = load_ustx(NEW/'compiled'/'project.ustx')
tm = TempoMap.from_doc(doc)

# ---------- 音色层 ----------
COLORS=['Yousa_Bright','Yousa_Classic','Yousa_Cute','Yousa_Normal','Yousa_Whisper']
MIX=dict(cl01=26, cl02=6, cl03=34, cl05=34)
clr=doc['expressions'].setdefault('clr',{})
clr.update(dict(name=clr.get('name','voice color'),abbr='clr',type='Options',
                min=0,max=len(COLORS)-1,default_value=0,options=COLORS[:]))
doc['tracks'][0]['voice_color_names']=COLORS[:]
n_clr=0
for part in doc['voice_parts']:
    for note in part['notes']:
        pe=[x for x in (note.get('phoneme_expressions') or []) if x.get('abbr')!='clr']
        for j in range(8): pe.append(dict(index=j,abbr='clr',value=0))
        note['phoneme_expressions']=pe; n_clr+=1
for abbr in ('cl01','cl02','cl03','cl04','cl05'):
    doc['expressions'].setdefault(abbr,dict(name=f'{abbr} mix',abbr=abbr,type='Curve',min=0,max=100,default_value=0))
n_mix=0
for part in doc['voice_parts']:
    part['curves']=[c for c in part.get('curves',[]) if not c['abbr'].startswith('cl')]
    dur=int(part['duration'])
    for a_,v_ in MIX.items():
        part['curves'].append(dict(abbr=a_,xs=[0,dur],ys=[v_,v_])); n_mix+=1
print(f'voice layer: clr on {n_clr} notes, {n_mix} clNN curves, mix {MIX}')

# ---------- 发声层 ----------
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim>1: v=v.mean(1)
HOP=0.02; n=len(v)//int(HOP*sr)
E=np.sqrt((v[:n*int(HOP*sr)].reshape(n,int(HOP*sr))**2).mean(1))
DB=20*np.log10(np.maximum(E,1e-9)); TE=(np.arange(n)+0.5)*HOP
def seg_db(a,b):
    m=(TE>=a)&(TE<b); return float(np.median(DB[m])) if m.sum() else -30.0
def seg_hnr(a,b):
    i0,i1=int(a*sr),int(b*sr); x=v[max(i0,0):min(i1,len(v))]
    if len(x)<2048: return 0.5
    x=(x-x.mean())[:min(len(x),8192)]
    ac=np.correlate(x,x,'full')[len(x)-1:]; ac/=max(ac[0],1e-12)
    lo,hi=int(sr/500),int(sr/80)
    return float(np.clip(ac[lo:hi].max(),0,1)) if hi<len(ac) else 0.5
def hnr(a,b):  # alias used above
    return seg_hnr(a,b)
prof=[]
for p in W['phrases']:
    prof.append(dict(t=p['time'], db=[seg_db(w['start'],w['end']) for w in p['words']],
                     hnr=[seg_hnr(w['start'],w['end']) for w in p['words']]))
all_db=np.concatenate([np.array(x['db']) for x in prof])
DB_LO,DB_HI=float(np.percentile(all_db,5)),float(np.percentile(all_db,95)); SPAN=DB_HI-DB_LO

n_cur=0
for pi,part in enumerate(doc['voice_parts']):
    pa=tm.tick_to_ms(part['position'])/1000
    pb=tm.tick_to_ms(part['position']+part['duration'])/1000
    words=[]
    for k,pr in enumerate(prof):
        if pr['t'][0]<pb-0.05 and pr['t'][1]>pa+0.05:
            ph=W['phrases'][k]
            for wi,w in enumerate(ph['words']):
                if w['end']>pa-0.02 and w['start']<pb+0.02:
                    words.append(dict(s=w['start'],e=w['end'],
                                      db=pr['db'][wi] if wi<len(pr['db']) else -25.,
                                      hnr=pr['hnr'][wi] if wi<len(pr['hnr']) else .5))
    if not words: continue
    words.sort(key=lambda x:x['s'])
    part['curves']=[c for c in part.get('curves',[]) if c['abbr'] not in ('dyn','voic','brec','tenc')]
    def ptick(sec): return int(round(tm.ms_to_tick(sec*1000)))-int(part['position'])
    def emit(abbr,pts):
        out=[]
        for t_,v_ in pts:
            t_=int(max(0,min(int(t_),int(part['duration']))))
            if out and t_<=out[-1][0]: t_=out[-1][0]+3
            if t_>int(part['duration']): continue
            out.append((t_,int(round(v_))))
        if len(out)>=2:
            part['curves'].append(dict(abbr=abbr,xs=[o[0] for o in out],ys=[o[1] for o in out]))
            return 1
        return 0
    dbs=np.array([w['db'] for w in words])
    rel=(dbs-DB_LO)/max(SPAN,1e-6); dynw=dbs-dbs.mean(); sc=float(np.std(dynw))
    gain=1.0 if sc<2.0 else min(2.2,3.5/max(sc,0.5))
    n_cur+=emit('dyn',[(ptick(words[i]['s']), -20.0+rel[i]*150.0+(dynw[i]-dynw.mean())*(gain-1.0)*6.0)
                       for i in range(len(words))])
    n_cur+=emit('voic',[(ptick(w['s']), float(np.clip(100+(w['hnr']-0.55)*30.0,86,114))) for w in words])
    n_cur+=emit('brec',[(ptick(w['s']), float(np.clip((0.55-w['hnr'])*34.0,-16,16))) for w in words])
    if len(words)>=4 and (dbs.max()-dbs.min())>=5.0:
        h=int(np.argmax(dbs))
        n_cur+=emit('tenc',[(ptick(words[0]['s']),3.0),(ptick(words[h]['s']),14.0),(ptick(words[-1]['e']),2.0)])
print(f'phonation curves emitted: {n_cur}')

OUT=NEW/'compiled'/'project_v9.ustx'
save_ustx(doc,OUT)
cnt={}
for p in doc['voice_parts']:
    for c in p.get('curves',[]): cnt[c['abbr']]=cnt.get(c['abbr'],0)+1
print('curve counts:', cnt)
print(f'wrote {OUT}')
