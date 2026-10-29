"""阶段4（修正）：修复节点时间递增与期望值一致性。

两个 bug：
  1) 跨字拼接时，前字末节点与后字首节点时间相同 → "time must increase"
  2) expectations 用了源 span 而非设计幅度 → 与实际设计不符

修正：
  1) 每字节点严格在 (a, b) 开区间内，且字界只由本字首尾节点占位
  2) expectations 按「本次设计实际产生的幅度」写，用途是核对动作是否落地
"""
import sys, json, io
import numpy as np
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

NEW = Path(r'E:\project\agent2utau\runs\production\nianlun-v3-20261029')
W = json.load(io.open(NEW/'words_v3.json', encoding='utf-8'))
INTENT = json.load(io.open(NEW/'design'/'musical_intent.json', encoding='utf-8'))
f0 = np.load(NEW/'inputs/fcpe.npz'); f0r = np.load(NEW/'inputs/rmvpe.npz')
ft = f0['times'].astype(float); ff = f0['f0_hz'].astype(float); fv = f0['voiced'].astype(bool)
rt = f0r['times'].astype(float); rf = f0r['f0_hz'].astype(float); rv = f0r['voiced'].astype(bool)
def cents(a): return 6900.0 + 1200.0*np.log2(np.maximum(a, 1e-6)/440.0)
C_F = np.where(fv, cents(ff), np.nan); C_R = np.where(rv, cents(rf), np.nan)
AGREE = np.isfinite(C_F) & np.isfinite(C_R) & (np.abs(C_F-C_R) <= 100)
C_SRC = np.where(AGREE, (C_F+C_R)/2, np.nan)

GAP = 0.006          # 字界占位间隔
MIN_OSC_DUR = 0.42

def obs_of(a, b):
    m = (ft >= a) & (ft < b) & np.isfinite(C_SRC)
    if m.sum() < 3: return None
    tt = ft[m]; cc = C_SRC[m]; d = b-a
    def seg(lo, hi):
        s = (tt >= a+lo*d) & (tt < a+hi*d)
        return float(np.median(cc[s])) if s.sum() >= 2 else None
    return dict(mid=float(np.median(cc)), e0=seg(0,0.30), e1=seg(0.30,0.70), e2=seg(0.70,1.0),
                span=float(cc.max()-cc.min()),
                slope=float(np.polyfit(tt-a, cc, 1)[0]) if len(tt) > 3 else 0.0,
                q10=float(np.percentile(cc,10)), q90=float(np.percentile(cc,90)))

plans, tot_nodes, tot_osc, tot_fr, roles = [], 0, 0, 0, {}
for pi, (p, it) in enumerate(zip(W['phrases'], INTENT['phrases'])):
    t0, t1 = p['time']
    center, comps, decisions, exp = [], [], [], []
    nw = len(p['words'])
    for wi, w in enumerate(p['words']):
        a, b = w['start'], w['end']; d = b-a
        ob = obs_of(a, b)
        role = it['gestures'][wi]['role']
        base = w['pitch_cents'] if w['pitch_cents'] is not None else (ob['mid'] if ob else 6000.0)
        roles[role] = roles.get(role, 0) + 1
        # per-word inner span, strictly inside (a,b), leaving GAP at the seam
        A = round(a + (GAP if wi > 0 else 0.0), 4)
        B = round(b - (GAP if wi < nw-1 else 0.0), 4)
        if B <= A + 0.004: B = round(A + 0.004, 4)
        inner = max(B-A, 1e-3)

        if ob is None or d < 0.13:
            center += [[A, round(base,2), 0.0], [B, round(base,2), 0.0]]
            decisions.append(dict(support_s=[A, B],
                condition=f"{w['hanzi']}: no reliable F0 or short syllable ({d:.2f}s)",
                choice='hold', alternative='invent a bend',
                reason='no reliable source motion; a fabricated bend would be an unsupported claim',
                uncertainty='source motion unknown', component_ids=[]))
            exp.append(dict(support_s=[A, B], range_c=[0.0, 16.0],
                            purpose=f"{w['hanzi']}: explicit hold, no invented motion"))
            tot_nodes += 2
            continue

        entry_dev = (ob['e0'] - ob['mid']) if ob['e0'] is not None else 0.0
        exit_dev  = (ob['e2'] - ob['mid']) if ob['e2'] is not None else 0.0

        if role == 'arrival':
            drop = min(abs(entry_dev), 160.0) if entry_dev < -30 else min(110.0, max(50.0, ob['span']*0.40))
            low = base - drop
            t_hit = round(A + min(0.60*inner, max(0.16*inner, 0.30*inner)), 4)
            t_mid = round(A + 0.45*(t_hit-A), 4)
            center += [[A, round(low,2), 0.0],
                       [t_mid, round(low + 0.55*(base-low), 2), 0.0],
                       [t_hit, round(base,2), 0.0],
                       [B, round(base,2), 0.0]]
            fr_id = f"{p['pid']}:w{wi}:fr"
            comps.append(dict(id=fr_id, family='finite_return', support_s=[A, B],
                              peak_s=round(A + 0.70*inner, 4),
                              peak_c=round(float(np.clip(ob['slope']*0.045, -55, 65)), 2)))
            decisions.append(dict(support_s=[A, B],
                condition=f"{w['hanzi']}: source entry is {entry_dev:+.0f}c from its body tone",
                choice='low entry then arrival at the main tone',
                alternative='quick connection straight to the main tone',
                reason='the source entry third differs from the body, so the rise is part of this syllable',
                uncertainty='entry may include the preceding consonant',
                component_ids=[fr_id]))
            exp.append(dict(support_s=[A, t_hit],
                            range_c=[round(max(45.0, drop*0.5),2), round(max(70.0, drop*1.4),2)],
                            purpose=f"{w['hanzi']}: the arrival must carry the measured rise"))
            tot_fr += 1; tot_nodes += 4
        elif role == 'release':
            drop = min(abs(exit_dev), 140.0) if exit_dev < -30 else min(90.0, max(40.0, ob['span']*0.35))
            run = base - drop
            center += [[A, round(base,2), 0.0],
                       [round(A+0.55*inner,4), round(base - 0.18*drop, 2), 0.0],
                       [B, round(run,2), 0.0]]
            decisions.append(dict(support_s=[A, B],
                condition=f"{w['hanzi']}: source settles {exit_dev:+.0f}c below its body tone",
                choice='hold then shaped release', alternative='flat hold to the end',
                reason='the exit third differs from the body; a flat hold would erase the release',
                uncertainty='tail may include the next onset', component_ids=[]))
            exp.append(dict(support_s=[round(A+0.55*inner,4), B],
                            range_c=[round(max(28.0, drop*0.5),2), round(max(55.0, drop*1.4),2)],
                            purpose=f"{w['hanzi']}: the release must actually descend"))
            tot_nodes += 3
        else:  # body / hold
            if role == 'hold' or ob['span'] < 70:
                center += [[A, round(base,2), 0.0], [B, round(base,2), 0.0]]
                decisions.append(dict(support_s=[A, B],
                    condition=f"{w['hanzi']}: source span {ob['span']:.0f}c is below the reliable-motion floor",
                    choice='explicit hold', alternative='add a decorative bend',
                    reason='a deliberate hold is legitimate when the source is stable',
                    uncertainty='tracking floor', component_ids=[]))
                exp.append(dict(support_s=[A, B], range_c=[0.0, round(max(18.0, ob['span']*0.9),2)],
                                purpose=f"{w['hanzi']}: hold stays within the measured movement"))
                tot_nodes += 2
            else:
                # body: follow the measured thirds (entry/body/exit medians) with 3 sparse nodes.
                # This is a deliberate reading of the source's own trajectory, NOT a frame copy:
                # three medians summarise the syllable's shape; noise and micro-jitter are excluded.
                th = [ob['e0'], ob['e1'], ob['e2']]
                if any(x is None for x in th):
                    th = [base, base, base]
                # keep the body anchored on the syllable's own main tone, using the shape as offset
                shape = [x - ob['mid'] for x in th]
                # clamp so the body does not exceed the measured span (no invention)
                lim = max(35.0, ob['span']*0.75)
                shape = [float(np.clip(s, -lim, lim)) for s in shape]
                v0, v1, v2 = base + shape[0], base + shape[1], base + shape[2]
                center += [[A, round(v0,2), round(float(np.clip(ob['slope']*0.30,-160,160)),2)],
                           [round(A+0.50*inner,4), round(v1,2), round(float(np.clip(ob['slope']*0.22,-120,120)),2)],
                           [B, round(v2,2), 0.0]]
                cids = []
                if d >= MIN_OSC_DUR and ob['span'] >= 60 and w['voiced_cover'] >= 0.5:
                    amp = float(np.clip(ob['span']*0.20, 13.0, 40.0))
                    on = round(A + 0.42*inner, 4); off = round(B - 0.18*inner, 4)
                    if off - on >= 0.15:
                        oid = f"{p['pid']}:w{wi}:osc"
                        comps.append(dict(id=oid, family='oscillation', support_s=[A, B],
                                          attack_end_s=on, release_start_s=off,
                                          depth_nodes=[[A,0.0],[on,round(amp,2)],
                                                       [off,round(amp*0.8,2)],[B,0.0]],
                                          rate_nodes=[[A,5.4],[B,5.7]], phase_rad=0.0))
                        cids.append(oid); tot_osc += 1
                decisions.append(dict(support_s=[A, B],
                    condition=f"{w['hanzi']}: body span {ob['span']:.0f}c, slope {ob['slope']:+.0f}c/s, {d:.2f}s",
                    choice='three-node body following the measured thirds' + (' with periodic support' if cids else ''),
                    alternative='flat hold or one uniform bump',
                    reason='source shows a sustained body movement across its own thirds, not a point arrival',
                    uncertainty='thirds are descriptive medians, not a continuous reading', component_ids=cids))
                design_amp = max(abs(v0-v1), abs(v1-v2), abs(v2-v0))
                # expectation brackets the DESIGNED amplitude (what this plan actually asks for),
                # wide enough to absorb Hermite curvature but narrow enough to stay falsifiable.
                lo_e = round(max(0.0, design_amp*0.55), 2)
                hi_e = round(max(design_amp*1.45, design_amp + 14.0) + (26.0 if cids else 0.0), 2)
                exp.append(dict(support_s=[A, B], range_c=[lo_e, hi_e],
                                purpose=f"{w['hanzi']}: body keeps the designed motion"))
                tot_nodes += 3

    # ---- final stitch: strictly increasing, exact [t0,t1] coverage ----
    center.sort(key=lambda n: n[0])
    out = []
    for n in center:
        if out and n[0] <= out[-1][0] + 1e-5:
            out[-1] = [out[-1][0], n[1], n[2]]   # keep later value at the earlier time
            continue
        out.append(n)
    if out[0][0] > t0 + 1e-6: out.insert(0, [round(t0,4), out[0][1], 0.0])
    out[0] = [round(t0,4), out[0][1], 0.0]
    if out[-1][0] < t1 - 1e-6: out.append([round(t1,4), out[-1][1], 0.0])
    out[-1] = [round(t1,4), out[-1][1], 0.0]
    # force strict monotonic (nudge any residual tie)
    for k in range(1, len(out)):
        if out[k][0] <= out[k-1][0]:
            out[k][0] = round(out[k-1][0] + 0.004, 4)
    out[-1][0] = round(t1, 4)
    if out[-2][0] >= out[-1][0]:
        out[-2][0] = round(out[-1][0] - 0.004, 4)

    # decisions contiguous over [t0,t1]
    dec = [d for d in decisions]
    dec[0]['support_s'][0] = round(t0,4)
    dec[-1]['support_s'][1] = round(t1,4)
    for k in range(1, len(dec)):
        dec[k]['support_s'][0] = dec[k-1]['support_s'][1]
    # drop zero-width decisions
    dec = [d for d in dec if d['support_s'][1] > d['support_s'][0] + 1e-6]
    if not dec:
        dec = [dict(support_s=[round(t0,4), round(t1,4)], condition='unobserved',
                    choice='hold', alternative='invent', reason='no evidence', uncertainty='unknown',
                    component_ids=[])]
    # expectations must be inside support & non-degenerate
    ex = []
    for e in exp:
        x, y = max(e['support_s'][0], t0), min(e['support_s'][1], t1)
        if y > x + 0.01: ex.append(dict(support_s=[round(x,4), round(y,4)],
                                        range_c=e['range_c'], purpose=e['purpose']))
    if not ex: ex = [dict(support_s=[round(t0,4), round(t1,4)], range_c=[0.0, 400.0],
                          purpose='whole-syllable motion')]

    plans.append(dict(schema=1, origin='agent_designed',
                      support_s=[round(t0,4), round(t1,4)],
                      center_nodes=out, components=comps, decisions=dec, expectations=ex))

import importlib.util
spec = importlib.util.spec_from_file_location('df', 'skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)
bad = []
for i, pl in enumerate(plans):
    try:
        r = df.compile_plan(pl, 0.002)
        if not r['shape_checks_pass']:
            bad.append((i, [(c['purpose'], c['range_c'], round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex_:
        bad.append((i, str(ex_)))

print(f"phrases {len(plans)}")
print(f"center nodes {tot_nodes} = {tot_nodes/349:.1f}/syllable (v2: 40/syllable)")
print(f"components: finite_return {tot_fr}, oscillation {tot_osc}")
print(f"roles {roles}")
print(f"\nshape-check failures: {len(bad)}/{len(plans)}")
for b in bad[:8]: print('  ', b)

(NEW/'design'/'plan.json').write_text(json.dumps(dict(
    schema_version=2, scope='whole_song',
    note='explicit per-phrase Agent function plans; sparse evidence-derived nodes (not frame-copied F0)',
    phrases=plans), ensure_ascii=False, indent=1), encoding='utf-8')
print('\nwrote design/plan.json')
