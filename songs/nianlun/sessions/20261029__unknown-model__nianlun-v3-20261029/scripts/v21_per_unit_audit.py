"""修正逐单元审计：body dev 只在「本单元归属的音符」内计算。

之前的错误：单元支撑可能横跨多个音符（melisma 延续），
用整个支撑的中位数与单元起始音符比较，得到 -685c 这类假缺陷。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')
from agent2utau.openutau.ustx import load_ustx, TempoMap

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
pf = json.load(io.open(NEW/'compiled'/'pitch_final.json', encoding='utf-8'))
inv = json.load(io.open(NEW/'design'/'review-inventory.json', encoding='utf-8'))
doc = load_ustx(NEW/'compiled'/'project_final.ustx')
tm = TempoMap.from_doc(doc)

t = np.concatenate([np.asarray(x['times_ms'],float)/1000 for x in pf['phrases']])
c = np.concatenate([np.asarray(x['final_cents'],float) for x in pf['phrases']])
o=np.argsort(t); t,c=t[o],c[o]

# note index per part with absolute times
notes_by_part = {}
for pi,part in enumerate(doc['voice_parts']):
    ns=[]
    for n in part['notes']:
        if n['lyric'] in ('AP','SP'): continue
        a=tm.tick_to_ms(part['position']+n['position'])/1000
        b=tm.tick_to_ms(part['position']+n['position']+n['duration'])/1000
        ns.append(dict(a=a,b=b,tone=n['tone'],lyric=n['lyric']))
    ns.sort(key=lambda x:x['a'])
    notes_by_part[pi]=ns

records=[]
for u in inv['units']:
    s0,s1 = u['support_s']
    pi = u['part_index']
    stages = u.get('musical_stages') or []
    tone = stages[0].get('tone') if stages else None
    T=np.arange(s0,s1,0.005)
    if len(T) < 8:
        records.append(dict(id=u['id'], lyric=u['lyric'], verdict='unknown',
                            reason='too short', dur=round(s1-s0,3)))
        continue
    C=np.interp(T,t,c)
    span=float(C.max()-C.min())
    # --- 只在该单元「归属音符」内测 body dev ---
    # 找与本单元起始对齐的音符
    nn = notes_by_part.get(pi, [])
    own = next((n for n in nn if abs(n['a']-s0) < 0.06), None)
    if own is None:
        own = next((n for n in nn if n['a']-0.06 <= s0 < n['b']), None)
    body_dev=None
    if own is not None:
        d0 = max(own['a'], s0); d1 = min(own['b'], s1)
        if d1 - d0 > 0.05:
            m=(T>=d0+0.25*(d1-d0))&(T<=d1-0.25*(d1-d0))
            if m.sum()>=3:
                body_dev = float(np.median(C[m])) - own['tone']*100.0
    W=8
    steep=float(np.max(np.abs(C[W:]-C[:-W]))) if len(C)>W else 0.0
    # reversal before a large leap (only if this unit ends at a leap)
    rev=0
    if own is not None:
        i = nn.index(own)
        if i+1 < len(nn):
            nxt=nn[i+1]; jump=nxt['tone']-own['tone']
            if abs(jump)>=4:
                m=(T>=own['b']-0.12)&(T<=own['b']+0.12)
                if m.sum()>=4:
                    dif=np.diff(C[m])
                    rev = int((dif<-15).sum()) if jump>0 else int((dif>15).sum())
    flags=[]
    if body_dev is not None and abs(body_dev)>60: flags.append(f'body {body_dev:+.0f}c')
    if steep>500: flags.append(f'steep {steep:.0f}c/40ms')
    if rev>2: flags.append(f'{rev} reversals')
    records.append(dict(id=u['id'], lyric=u['lyric'], tone=tone, t0=round(s0,2),
                        dur=round(s1-s0,3), span=round(span,0),
                        body_dev=round(body_dev,0) if body_dev is not None else None,
                        steep40ms=round(steep,0), reversals=rev,
                        verdict='watch' if flags else 'keep', flags=flags))

from collections import Counter
cnt=Counter(r['verdict'] for r in records)
print(f'units: {len(records)}  verdicts: {dict(cnt)}')
watch=[r for r in records if r['verdict']=='watch']
print(f'\nwatch {len(watch)}:')
for r in sorted(watch, key=lambda x:-(abs(x.get('body_dev') or 0))):
    print(f"  {r['id']:12s} {r['lyric']} bodydev={r['body_dev']} steep={r['steep40ms']} rev={r['reversals']} {r['flags']}")

bd=np.array([abs(r['body_dev']) for r in records if r.get('body_dev') is not None])
print(f'\n|body_dev|: median {np.median(bd):.1f}  p90 {np.percentile(bd,90):.1f}  max {bd.max():.0f}  >60: {(bd>60).sum()}')
rv=np.array([r['reversals'] for r in records if 'reversals' in r])
print(f'reversals>2: {(rv>2).sum()}')

out=dict(schema_version=1,
  method='per-unit audit; body deviation measured only inside the unit\'s own note',
  coverage=dict(units=len(records), contact_sheet_pages=30, contact_sheet_units=349,
                individually_opened=['p0:f0:v0','p2:f0:v6','p18:f0:v3','p0:f0:v5','p24:f0:v0']),
  verdicts=dict(cnt), records=records)
(NEW/'evaluation'/'per_unit_audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('wrote evaluation/per_unit_audit.json')
