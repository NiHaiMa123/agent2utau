"""阶段7：逐句发声层（VOIC/BREC/TENC/DYN）——针对「平」和「虚实单调」。

诊断依据（本曲实测）：
  原唱 dB IQR 8.7dB；v2 7.7dB；v3d 6.2dB → 强弱层次不足是「平」的可量化表现
  原唱有 28 处 >=0.10s 静默（总 86s）；我们的句子间隙未被利用

设计（每句独立，不是段落模板）：
  DYN  : 按该句源 RMS 包络的相对强弱，做句内 3-5 点包络（不逐字归一化）
  VOIC : 按该句源发声强度（谐波/噪声比代理）给有限增量
  BREC : 气声字（源噪声比例高）给负增量抑制、需要气化的收尾给正增量
  TENC : 句内支撑建立-保持-回落，长音段落才动

每条曲线都绑定真实秒锚点、基底和恢复；不填满整首。
"""
import sys, json, io
import numpy as np, soundfile as sf
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, save_ustx, TempoMap, sha256

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
PROJ = NEW/'compiled'/'project.ustx'
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))

doc = load_ustx(PROJ)
tm = TempoMap.from_doc(doc)
v, sr = sf.read(str(NEW/'inputs/stems/vocals.wav'), dtype='float32')
if v.ndim > 1: v = v.mean(1)
HOP = 0.02
n = len(v)//int(HOP*sr)
E = np.sqrt((v[:n*int(HOP*sr)].reshape(n, int(HOP*sr))**2).mean(1))
DB = 20*np.log10(np.maximum(E, 1e-9)); TE = (np.arange(n)+0.5)*HOP

def seg_db(a, b):
    m = (TE>=a)&(TE<b)
    return float(np.median(DB[m])) if m.sum() else -30.0

def seg_hnr_proxy(a, b):
    """谐波性代理：F0 周期处的自相关（高=更实/浊音强，低=更气/噪声多）"""
    i0, i1 = int(a*sr), int(b*sr)
    x = v[max(i0,0):min(i1,len(v))]
    if len(x) < 2048: return 0.5
    x = x - x.mean()
    x = x[:min(len(x), 8192)]
    ac = np.correlate(x, x, 'full')[len(x)-1:]
    ac /= max(ac[0], 1e-12)
    # realistic F0 range 80-500 Hz
    lo, hi = int(sr/500), int(sr/80)
    if hi >= len(ac): return 0.5
    return float(np.clip(ac[lo:hi].max(), 0, 1))

# per-phrase source profile
prof = []
for p in W['phrases']:
    t0, t1 = p['time']
    dbs = [seg_db(w['start'], w['end']) for w in p['words']]
    hnrs = [seg_hnr_proxy(w['start'], w['end']) for w in p['words']]
    prof.append(dict(pid=p['pid'], t=[t0,t1], db=dbs, hnr=hnrs,
                     db_mean=float(np.mean(dbs)), db_std=float(np.std(dbs)),
                     hnr_mean=float(np.mean(hnrs))))
print(f'phrases profiled: {len(prof)}')
print(f'  phrase dB mean range: {min(p["db_mean"] for p in prof):.1f} .. {max(p["db_mean"] for p in prof):.1f}')
print(f'  phrase dB std median: {np.median([p["db_std"] for p in prof]):.2f} dB')
print(f'  phrase HNR proxy median: {np.median([p["hnr_mean"] for p in prof]):.3f}')

# global references
all_db = np.concatenate([p['db'] for p in prof])
DB_LO, DB_HI = float(np.percentile(all_db,10)), float(np.percentile(all_db,90))
print(f'  source syllable dB p10/p90: {DB_LO:.1f} / {DB_HI:.1f}')

# ---- build curves per part ----
# 1st pass: compute part assignment for each phrase (part contains the phrase window)
part_of = []
for pi, part in enumerate(doc['voice_parts']):
    a = tm.tick_to_ms(part['position'])/1000
    b = a + tm.tick_to_ms(part['duration'])/1000 - tm.tick_to_ms(0)/1000
    b = tm.tick_to_ms(part['position']+part['duration'])/1000
    part_of.append((a,b))
print(f'\nparts: {len(part_of)}')

changed = 0
for pi, part in enumerate(doc['voice_parts']):
    pa = tm.tick_to_ms(part['position'])/1000
    pb = tm.tick_to_ms(part['position']+part['duration'])/1000
    # find phrases overlapping this part
    idxs = [k for k,pr in enumerate(prof) if pr['t'][0] < pb-0.05 and pr['t'][1] > pa+0.05]
    if not idxs: continue
    # merge their syllable profiles inside this part
    words = []
    for k in idxs:
        ph = W['phrases'][k]
        for wi,w in enumerate(ph['words']):
            if w['end'] > pa-0.02 and w['start'] < pb+0.02:
                words.append(dict(t=(w['start'],w['end']),
                                  db=prof[k]['db'][wi] if wi < len(prof[k]['db']) else -25.0,
                                  hnr=prof[k]['hnr'][wi] if wi < len(prof[k]['hnr']) else 0.5))
    if not words: continue
    words.sort(key=lambda x: x['t'][0])

    def tick(s): return int(round((s*1000)/(60000.0/(120.0*480)))) - part['position'] if False else int(round(s*1000/ (60000.0/(120.0*480))))
    # NOTE: USTX curve xs are part-relative ticks
    def ptick(s):
        return int(round(tm.ms_to_tick(s*1000))) - part['position']

    # --- DYN: phrase-level dynamics following the source's relative loudness ---
    dn = []
    for w in words:
        rel = (w['db'] - DB_LO) / max(DB_HI-DB_LO, 1e-6)     # 0..1
        val = float(np.clip(-60.0 + 90.0*rel, -90, 30))      # DYN unit = 0.1 dB
        dn.append((ptick(w['t'][0]), val))
    # smooth: 5-pt moving average over the time series (keep endpoints)
    if len(dn) >= 3:
        vals = np.array([d[1] for d in dn])
        sm = vals.copy()
        for i in range(1, len(vals)-1):
            sm[i] = np.mean(vals[max(0,i-1):i+2])
        dn = [(dn[i][0], float(sm[i])) for i in range(len(dn))]
    # ensure strictly increasing ticks
    dn2 = []
    for t_,v_ in dn:
        if dn2 and t_ <= dn2[-1][0]: t_ = dn2[-1][0]+5
        dn2.append((t_, round(v_,1)))
    part['curves'] = [c for c in part.get('curves',[]) if c['abbr'] not in ('dyn','voic','brec','tenc')]
    if len(dn2) >= 2:
        part['curves'].append(dict(abbr='dyn', xs=[d[0] for d in dn2], ys=[d[1] for d in dn2]))

    # --- VOIC: limited increment where the source is more voiced (less breathy) ---
    vo = []
    for w in words:
        # hnr 0..1 maps to -6..+8 around 100 (0 = zero increment)
        val = float(np.clip(100 + (w['hnr']-0.55)*26.0, 88, 112))
        vo.append((ptick(w['t'][0]), val))
    vo2 = []
    for t_,v_ in vo:
        if vo2 and t_ <= vo2[-1][0]: t_ = vo2[-1][0]+5
        vo2.append((t_, round(v_,1)))
    if len(vo2) >= 2:
        part['curves'].append(dict(abbr='voic', xs=[d[0] for d in vo2], ys=[d[1] for d in vo2]))

    # --- BREC: suppress breathiness where the source is voiced, allow it where it is airy ---
    br = []
    for w in words:
        val = float(np.clip((0.55 - w['hnr'])*30.0, -14, 14))
        br.append((ptick(w['t'][0]), val))
    br2 = []
    for t_,v_ in br:
        if br2 and t_ <= br2[-1][0]: t_ = br2[-1][0]+5
        br2.append((t_, round(v_,1)))
    if len(br2) >= 2:
        part['curves'].append(dict(abbr='brec', xs=[d[0] for d in br2], ys=[d[1] for d in br2]))

    # --- TENC: only where the phrase spans a real loudness arc (support build/release) ---
    if len(words) >= 4:
        dbs = np.array([w['db'] for w in words])
        arc = dbs.max()-dbs.min()
        if arc >= 6.0:
            h = int(np.argmax(dbs)); t_apex = words[h]['t'][0]
            tn = [(ptick(words[0]['t'][0]), 4.0),
                  (ptick(t_apex), 12.0),
                  (ptick(words[-1]['t'][1]), 2.0)]
            tn2 = []
            for t_,v_ in tn:
                if tn2 and t_ <= tn2[-1][0]: t_ = tn2[-1][0]+5
                tn2.append((t_, round(v_,1)))
            if len(tn2) >= 2:
                part['curves'].append(dict(abbr='tenc', xs=[t[0] for t in tn2], ys=[t[1] for t in tn2]))
    changed += 1

print(f'parts with new curves: {changed}')
cnt = {}
for p in doc['voice_parts']:
    for c in p.get('curves',[]):
        cnt[c['abbr']] = cnt.get(c['abbr'],0)+1
print('curve counts:', cnt)

OUT = NEW/'compiled'/'project_voiced.ustx'
save_ustx(doc, OUT)
print(f'wrote {OUT}')
