"""v3k：修正字头起音过柔（v3 1.5dB vs 原唱 3.5dB）。

根因：为了让音高连续，我在字间几乎没有留下辅音/起音的「重新起声」空间，
      DYN 曲线也是逐字平滑，导致字头爆发感被抹平。

修正（Skill「元音核与局部释放」/「字头到达」）：
  1) 每个字的**起音点**加一个短促的 DYN 抬升（30-60ms），给辅音/起音留出能量
  2) 抬升幅度由该字源起音的实测 dB 上升量决定，不统一给常数
  3) 只作用在字头，字腹与字尾保持原设计
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
HOP = 0.005
n = len(v)//int(HOP*sr)
E = np.sqrt((v[:n*int(HOP*sr)].reshape(n, int(HOP*sr))**2).mean(1))
SDB = 20*np.log10(np.maximum(E, 1e-9)); STE = (np.arange(n)+0.5)*HOP

def onset_rise(a, ms=0.030):
    i0 = int(a/HOP); i1 = i0 + int(ms/HOP)
    if i1 >= len(SDB) or i0 < 2: return 0.0
    seg = SDB[max(i0-2,0):i1]
    return float(seg.max()-seg.min()) if len(seg) >= 3 else 0.0

# ---- reference dynamics from the source, per syllable ----
def seg_db(a,b):
    m=(STE>=a)&(STE<b); return float(np.median(SDB[m])) if m.sum() else -30.0
prof=[]
for p in W['phrases']:
    prof.append(dict(t=p['time'],
                     db=[seg_db(w['start'],w['end']) for w in p['words']],
                     rise=[onset_rise(w['start']) for w in p['words']],
                     hnr=None))
all_db=np.concatenate([np.array(x['db']) for x in prof])
DB_LO,DB_HI=float(np.percentile(all_db,5)),float(np.percentile(all_db,95))
SPAN=DB_HI-DB_LO
all_rise=np.concatenate([np.array(x['rise']) for x in prof])
print(f'source onset rise: median {np.median(all_rise):.1f}dB  p90 {np.percentile(all_rise,90):.1f}dB')

def hnr(a,b):
    i0,i1=int(a*sr),int(b*sr); x=v[max(i0,0):min(i1,len(v))]
    if len(x)<2048: return 0.5
    x=(x-x.mean())[:min(len(x),8192)]
    ac=np.correlate(x,x,'full')[len(x)-1:]; ac/=max(ac[0],1e-12)
    lo,hi=int(sr/500),int(sr/80)
    return float(np.clip(ac[lo:hi].max(),0,1)) if hi<len(ac) else 0.5
for k,p in enumerate(W['phrases']):
    prof[k]['hnr']=[hnr(w['start'],w['end']) for w in p['words']]

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
                    words.append(dict(s=w['start'], e=w['end'],
                                      db=pr['db'][wi] if wi<len(pr['db']) else -25.,
                                      rise=pr['rise'][wi] if wi<len(pr['rise']) else 0.,
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
            cnt[abbr]=cnt.get(abbr,0)+1

    dbs=np.array([w['db'] for w in words])
    rel=(dbs-DB_LO)/max(SPAN,1e-6)
    dynw=dbs-dbs.mean(); scatter=float(np.std(dynw))
    gain = 1.0 if scatter<2.0 else min(2.2, 3.5/max(scatter,0.5))

    # ---- DYN: base phrase shape + per-syllable onset lift ----
    pts=[]
    for i,w in enumerate(words):
        base = -20.0 + rel[i]*150.0 + (dynw[i]-dynw.mean())*(gain-1.0)*6.0
        # onset: add a short lift proportional to the measured source rise
        lift = float(np.clip((w['rise']-2.0)*2.6, 0.0, 22.0))   # 0..22 DYN units = 0..2.2 dB
        t_head = ptick(w['s'])
        t_back = ptick(min(w['s']+0.055, (w['s']+w['e'])/2))
        pts.append((t_head, base+lift))
        pts.append((t_back, base))
    # ensure strictly increasing globally
    pts=[(int(t),float(v_)) for t,v_ in pts]
    pts.sort(key=lambda x:x[0])
    dedup=[]
    for t_,v_ in pts:
        if dedup and t_<=dedup[-1][0]: t_=dedup[-1][0]+3
        dedup.append((t_,v_))
    emit('dyn',[(t, float(np.clip(v_,-140,60))) for t,v_ in dedup])
    emit('voic',[(ptick(w['s']), float(np.clip(100+(w['hnr']-0.55)*30.0,86,114))) for w in words])
    emit('brec',[(ptick(w['s']), float(np.clip((0.55-w['hnr'])*34.0,-16,16))) for w in words])
    if len(words)>=4 and (dbs.max()-dbs.min())>=5.0:
        h=int(np.argmax(dbs))
        emit('tenc',[(ptick(words[0]['s']),3.0),(ptick(words[h]['s']),14.0),
                     (ptick(words[-1]['e']),2.0)])
    changed+=1

print(f'parts {changed}  curves {cnt}')
OUT=NEW/'compiled'/'project_voiced.ustx'
save_ustx(doc,OUT)
print(f'wrote {OUT}')
