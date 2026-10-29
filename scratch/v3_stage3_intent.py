"""阶段3：逐句原曲观察 + 意图冻结（51 句）。

按 Skill 要求：
  - 每句先看连续源观察（不是统计摘要）
  - 分开「源事实 / 解释 / 主动选择 / unknown」
  - 每个独立过程（入口/主体/退出）有自己的可检验后果
  - 意图在数值计划存在前冻结

本脚本产出 musical_intent.json：每句的观察 + gesture + 判据。
判据用 Skill 支持的五种：landmarks / direction / range / cycles / hold(may_match)。
关键改进：不用自证式 range(±12c)，而是用「能否否决浅对照」的 must_differ。
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
def cents(a): return 6900.0 + 1200.0*np.log2(np.maximum(a, 1e-6)/440.0)
C_F = np.where(fv, cents(ff), np.nan); C_R = np.where(rv, cents(rf), np.nan)
AGREE = np.isfinite(C_F) & np.isfinite(C_R) & (np.abs(C_F-C_R) <= 100)
C_SRC = np.where(AGREE, (C_F+C_R)/2, np.nan)


def observe(a, b):
    """Continuous source observation of one syllable: entry / body / exit."""
    m = (ft >= a) & (ft < b)
    tt = ft[m]; cc = C_SRC[m]
    good = np.isfinite(cc)
    if good.sum() < 3:
        return None
    tt, cc = tt[good], cc[good]
    d = b - a
    q = lambda p: float(np.percentile(cc, p))
    # split into thirds
    th = [np.nanmedian(cc[(tt >= a+0.00*d) & (tt < a+0.33*d)]),
          np.nanmedian(cc[(tt >= a+0.33*d) & (tt < a+0.67*d)]),
          np.nanmedian(cc[(tt >= a+0.67*d) & (tt < b)])]
    th = [float(x) if np.isfinite(x) else None for x in th]
    # local motion: total span and largest single swing
    span = float(cc.max() - cc.min())
    # direction: linear fit slope in c/s
    slope = float(np.polyfit(tt - a, cc, 1)[0]) if len(tt) > 3 else 0.0
    # periodicity: dominant peak-to-peak count via zero-crossings of detrended
    detr = cc - np.polyval(np.polyfit(tt-a, cc, 1), tt-a)
    zc = int(np.sum(np.diff(np.sign(detr)) != 0))
    return dict(start=a, end=b, dur=d, mid=float(np.median(cc)),
                q10=q(10), q50=q(50), q90=q(90), span=span, slope=slope,
                thirds=th, zc=zc, n=int(good.sum()))


def classify(ob):
    """Turn an observation into a falsifiable gesture + checks (Skill's five check kinds)."""
    if ob is None:
        return dict(role='unknown', checks=[], why='source F0 unreliable in this window')
    span, slope, d = ob['span'], ob['slope'], ob['dur']
    th = ob['thirds']
    has_thirds = all(x is not None for x in th)
    # entry: compare first third to median
    entry_dev = (th[0]-ob['q50']) if has_thirds else 0.0
    exit_dev = (th[2]-ob['q50']) if has_thirds else 0.0
    # decide role by evidence
    if span >= 120 and abs(slope) >= 60:
        role = 'arrival' if slope > 0 else 'release'
        kind = 'direction'
        params = dict(direction='up' if slope > 0 else 'down',
                      min_delta_c=float(max(60, span*0.45)),
                      max_backtrack_c=float(span*0.35))
    elif span >= 100 and ob['zc'] >= 2:
        role = 'body'
        kind = 'cycles'
        params = dict(min_cycles=1, prominence_c=float(max(25, span*0.3)))
    elif has_thirds and entry_dev <= -45:
        role = 'arrival'          # enters from below then rises to the main tone
        kind = 'landmarks'
        params = dict(points=[[ob['start']+0.25*d, th[0]],
                              [ob['start']+0.85*d, ob['q50']]],
                      tolerance_c=float(max(35, span*0.4)),
                      time_tolerance_s=round(0.06+0.04*d, 3))
    elif has_thirds and exit_dev <= -45:
        role = 'release'          # settles down at the end
        kind = 'landmarks'
        params = dict(points=[[ob['start']+0.25*d, ob['q50']],
                              [ob['start']+0.9*d, th[2]]],
                      tolerance_c=float(max(35, span*0.4)),
                      time_tolerance_s=round(0.06+0.04*d, 3))
    elif span >= 60:
        role = 'body'
        kind = 'range'
        params = dict(min_c=float(ob['q10']-max(25, span*0.35)),
                      max_c=float(ob['q90']+max(25, span*0.35)))
    else:
        role = 'hold'
        kind = 'hold'
        params = dict(min_c=float(ob['q10']-40), max_c=float(ob['q90']+40))
    return dict(role=role, checks=[dict(kind=kind, support_s=[round(ob['start'],4), round(ob['end'],4)],
                                        parameters=params)],
                why=f"span={span:.0f}c slope={slope:+.0f}c/s thirds={[round(x,0) if x else None for x in th]}")


phrases = []
for p in W['phrases']:
    obs_list, gestures, units = [], [], []
    for wi, w in enumerate(p['words']):
        ob = observe(w['start'], w['end'])
        uid = f"{p['pid']}:w{wi}"
        units.append(uid)
        obs_id = f"{uid}:obs"
        obs_list.append(dict(id=obs_id, source_id='source_f0_dual',
                             source_window_s=[w['start'], w['end']],
                             description=(f"{w['hanzi']}: mid={w['pitch_cents']}c, "
                                          f"voiced_cover={w['voiced_cover']}"
                                          + (f", span={ob['span']:.0f}c, slope={ob['slope']:+.0f}c/s"
                                             if ob else ", F0 unknown")),
                             reliability='observed' if ob and w['voiced_cover'] >= 0.35 else 'uncertain'))
        g = classify(ob)
        gestures.append(dict(id=f"{uid}:g0", unit_ids=[uid], role=g['role'],
                             support_s=[w['start'], w['end']],
                             observation_ids=[obs_id],
                             interpretation=g['why'],
                             alternative=('flat hold at the median' if g['role'] != 'hold'
                                          else 'a shallow single bend'),
                             rejected_because=('source shows measurable motion that a flat hold would erase'
                                               if g['role'] != 'hold'
                                               else 'source movement is below the reliable-tracking floor'),
                             contrast=dict(mode='must_differ',
                                           shallow_limit_c=25,
                                           connection_s=0.08,
                                           reason='diagnostic counterfactual: a uniform shallow connection+bump'),
                             checks=g['checks']))
    phrases.append(dict(id=p['pid'], unit_ids=units, support_s=p['time'],
                        intention=f"{p['label']}：{'/'.join(p['lines'])}",
                        observations=obs_list, gestures=gestures))

from collections import Counter
roles = Counter(g['role'] for p in phrases for g in p['gestures'])
kinds = Counter(c['kind'] for p in phrases for g in p['gestures'] for c in g['checks'])
print(f'phrases {len(phrases)}  units {sum(len(p["unit_ids"]) for p in phrases)}')
print('roles:', dict(roles))
print('check kinds:', dict(kinds))

doc = dict(schema_version=1, phrases=phrases,
           note='intent frozen before any numeric plan; source facts vs interpretation separated per Skill')
(NEW/'design').mkdir(exist_ok=True)
(NEW/'design'/'musical_intent.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
print('\nwrote design/musical_intent.json')
