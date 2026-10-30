"""阶段7（修正）：曲线 xs 必须是 part 相对 tick。

bug：我用 tm.ms_to_tick(绝对秒) 得到绝对 tick，未减 part['position']，
     导致 xs 从 480 起而 part.position=17501 → OpenUtau 反序列化失败。
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
    m = (TE>=a)&(TE<b); return float(np.median(DB[m])) if m.sum() else -30.0
def seg_hnr(a,b):
    i0,i1 = int(a*sr), int(b*sr)
    x = v[max(i0,0):min(i1,len(v))]
    if len(x) < 2048: return 0.5
    x = (x-x.mean())[:min(len(x),8192)]
    ac = np.correlate(x,x,'full')[len(x)-1:]
    ac /= max(ac[0],1e-12)
    lo,hi = int(sr/500), int(sr/80)
    return float(np.clip(ac[lo:hi].max(),0,1)) if hi<len(ac) else 0.5

prof = []
for p in W['phrases']:
    prof.append(dict(t=p['time'],
                     db=[seg_db(w['start'],w['end']) for w in p['words']],
                     hnr=[seg_hnr(w['start'],w['end']) for w in p['words']]))

all_db = np.concatenate([np.array(x['db']) for x in prof])
DB_LO, DB_HI = float(np.percentile(all_db,10)), float(np.percentile(all_db,90))

def ptick(part, sec):
    """part-relative tick from absolute seconds."""
    return int(round(tm.ms_to_tick(sec*1000))) - int(part['position'])

changed = 0
cnt = {}
for pi, part in enumerate(doc['voice_parts']):
    pa = tm.tick_to_ms(part['position'])/1000
    pb = tm.tick_to_ms(part['position']+part['duration'])/1000
    words = []
    for k,pr in enumerate(prof):
        if pr['t'][0] < pb-0.05 and pr['t'][1] > pa+0.05:
            ph = W['phrases'][k]
            for wi,w in enumerate(ph['words']):
                if w['end'] > pa-0.02 and w['start'] < pb+0.02:
                    words.append(dict(s=(w['start'],w['end']),
                                      db=pr['db'][wi] if wi<len(pr['db']) else -25.0,
                                      hnr=pr['hnr'][wi] if wi<len(pr['hnr']) else 0.5))
    if not words: continue
    words.sort(key=lambda x: x['s'][0])
    part['curves'] = [c for c in part.get('curves',[]) if c['abbr'] not in ('dyn','voic','brec','tenc')]

    def emit(abbr, pts):
        # pts: [(part-relative tick, value)] -> clamp to [0, duration], strictly increasing.
        # NOTE: USTX curve ys must be INTEGERS; float ys make OpenUtau's YAML
        # deserializer throw "Exception during deserialization" (verified by isolation test).
        out = []
        for t_,v_ in pts:
            t_ = int(max(0, min(int(t_), int(part['duration']))))
            if out and t_ <= out[-1][0]: t_ = out[-1][0]+5
            if t_ > int(part['duration']): continue
            out.append((t_, int(round(v_))))
        if len(out) >= 2:
            part['curves'].append(dict(abbr=abbr, xs=[o[0] for o in out], ys=[o[1] for o in out]))
            cnt[abbr] = cnt.get(abbr,0)+1

    # DYN
    dn = []
    for w in words:
        rel = (w['db']-DB_LO)/max(DB_HI-DB_LO,1e-6)
        dn.append((ptick(part,w['s'][0]), float(np.clip(-60.0+90.0*rel,-90,30))))
    if len(dn) >= 3:
        vals = np.array([d[1] for d in dn]); sm = vals.copy()
        for i in range(1,len(vals)-1): sm[i]=np.mean(vals[max(0,i-1):i+2])
        dn = [(dn[i][0], float(sm[i])) for i in range(len(dn))]
    emit('dyn', dn)
    # VOIC
    emit('voic', [(ptick(part,w['s'][0]), float(np.clip(100+(w['hnr']-0.55)*26.0,88,112))) for w in words])
    # BREC
    emit('brec', [(ptick(part,w['s'][0]), float(np.clip((0.55-w['hnr'])*30.0,-14,14))) for w in words])
    # TENC only on a real loudness arc
    if len(words) >= 4:
        dbs = np.array([w['db'] for w in words])
        if dbs.max()-dbs.min() >= 6.0:
            h = int(np.argmax(dbs))
            emit('tenc', [(ptick(part,words[0]['s'][0]), 4.0),
                          (ptick(part,words[h]['s'][0]), 12.0),
                          (ptick(part,words[-1]['s'][1]), 2.0)])
    changed += 1

# validate every curve starts at 0 or later and within part duration
prob = []
for pi,part in enumerate(doc['voice_parts']):
    for c in part.get('curves',[]):
        if not c['xs']: prob.append((pi,c['abbr'],'empty')); continue
        if c['xs'][0] < 0: prob.append((pi,c['abbr'],f"neg {c['xs'][0]}"))
        if c['xs'][-1] > part['duration']+5: prob.append((pi,c['abbr'],f"exceeds dur {c['xs'][-1]}>{part['duration']}"))
        if any(b<=a for a,b in zip(c['xs'],c['xs'][1:])): prob.append((pi,c['abbr'],'not increasing'))
print(f'parts {changed}, curve counts {cnt}')
print(f'format problems: {len(prob)}')
for x in prob[:8]: print('  ',x)

OUT = NEW/'compiled'/'project_voiced.ustx'
save_ustx(doc, OUT)
print(f'wrote {OUT}')
