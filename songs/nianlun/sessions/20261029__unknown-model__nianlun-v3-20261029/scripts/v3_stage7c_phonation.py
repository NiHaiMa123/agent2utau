"""阶段7c：加强动态层次（当前 IQR 7.5 vs 源 8.7dB，还不够）。

诊断：DYN 映射 -60..30 跨 90 单位(=9dB) 覆盖源 12.5dB 的 p10-p90 区间，
      实际传递效率只有 7.5/8.7 = 86%。
修正：把 DYN 跨度提高到覆盖源动态的全量，并允许更强的句内起伏。
"""
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
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
HOP = 0.02
n = len(v)//int(HOP*sr)
E = np.sqrt((v[:n*int(HOP*sr)].reshape(n, int(HOP*sr))**2).mean(1))
DB = 20*np.log10(np.maximum(E, 1e-9)); TE = (np.arange(n)+0.5)*HOP

def seg_db(a,b):
    m=(TE>=a)&(TE<b); return float(np.median(DB[m])) if m.sum() else -30.0
def seg_hnr(a,b):
    i0,i1=int(a*sr),int(b*sr); x=v[max(i0,0):min(i1,len(v))]
    if len(x)<2048: return 0.5
    x=(x-x.mean())[:min(len(x),8192)]
    ac=np.correlate(x,x,'full')[len(x)-1:]; ac/=max(ac[0],1e-12)
    lo,hi=int(sr/500),int(sr/80)
    return float(np.clip(ac[lo:hi].max(),0,1)) if hi<len(ac) else 0.5

prof=[]
for p in W['phrases']:
    prof.append(dict(t=p['time'],
                     db=[seg_db(w['start'],w['end']) for w in p['words']],
                     hnr=[seg_hnr(w['start'],w['end']) for w in p['words']]))
all_db=np.concatenate([np.array(x['db']) for x in prof])
DB_LO,DB_HI=float(np.percentile(all_db,5)),float(np.percentile(all_db,95))
SPAN = DB_HI-DB_LO
print(f'source syllable dB p5/p95: {DB_LO:.1f}/{DB_HI:.1f}  span {SPAN:.1f}dB')

# DYN unit = 0.1 dB. Use the full source span so the layer does not flatten it.
AIM_RANGE = 150          # units -> 15 dB of DYN authority
changed=0; cnt={}
for pi,part in enumerate(doc['voice_parts']):
    pa=tm.tick_to_ms(part['position'])/1000
    pb=tm.tick_to_ms(part['position']+part['duration'])/1000
    words=[]
    for k,pr in enumerate(prof):
        if pr['t'][0]<pb-0.05 and pr['t'][1]>pa+0.05:
            ph=W['phrases'][k]
            for wi,w in enumerate(ph['words']):
                if w['end']>pa-0.02 and w['start']<pb+0.02:
                    words.append(dict(s=(w['start'],w['end']),
                                      db=pr['db'][wi] if wi<len(pr['db']) else -25.,
                                      hnr=pr['hnr'][wi] if wi<len(pr['hnr']) else .5))
    if not words: continue
    words.sort(key=lambda x:x['s'][0])
    part['curves']=[c for c in part.get('curves',[]) if c['abbr'] not in ('dyn','voic','brec','tenc')]
    def ptick(sec): return int(round(tm.ms_to_tick(sec*1000))) - int(part['position'])
    def emit(abbr,pts):
        out=[]
        for t_,v_ in pts:
            t_=int(max(0,min(int(t_),int(part['duration']))))
            if out and t_<=out[-1][0]: t_=out[-1][0]+5
            if t_>int(part['duration']): continue
            out.append((t_,int(round(v_))))
        if len(out)>=2:
            part['curves'].append(dict(abbr=abbr,xs=[o[0] for o in out],ys=[o[1] for o in out]))
            cnt[abbr]=cnt.get(abbr,0)+1

    dbs=np.array([w['db'] for w in words])
    # DYN: map the phrase's own dynamic spread onto most of AIM_RANGE,
    # anchored so the phrase mean sits near a common reference (no per-word normalisation).
    rel=(dbs-DB_LO)/max(SPAN,1e-6)                  # 0..1 across the whole song
    dyn=dbs-dbs.mean()                               # within-phrase deviation
    scatter=float(np.std(dyn))
    gain = 1.0 if scatter < 2.0 else min(2.2, 3.5/max(scatter,0.5))
    vals = -20.0 + rel*AIM_RANGE + (dyn-dyn.mean())*(gain-1.0)*6.0
    pts=[(ptick(words[i]['s'][0]), float(vals[i])) for i in range(len(words))]
    # light smoothing (keeps phrase shape, kills single-syllable spikes)
    if len(pts)>=5:
        vv=np.array([p[1] for p in pts]); sm=vv.copy()
        for i in range(2,len(vv)-2): sm[i]=np.mean(vv[i-1:i+2])
        pts=[(pts[i][0],float(sm[i])) for i in range(len(pts))]
    emit('dyn',[(t, float(np.clip(val,-140,60))) for t,val in pts])
    emit('voic',[(ptick(w['s'][0]), float(np.clip(100+(w['hnr']-0.55)*30.0,86,114))) for w in words])
    emit('brec',[(ptick(w['s'][0]), float(np.clip((0.55-w['hnr'])*34.0,-16,16))) for w in words])
    if len(words)>=4 and (dbs.max()-dbs.min())>=5.0:
        h=int(np.argmax(dbs))
        emit('tenc',[(ptick(words[0]['s'][0]),3.0),
                     (ptick(words[h]['s'][0]),14.0),
                     (ptick(words[-1]['s'][1]),2.0)])
    changed+=1

print(f'parts {changed}, curves {cnt}')
OUT=NEW/'compiled'/'project_voiced.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
