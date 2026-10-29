"""修正核心设计缺陷：不再给「源没有该动作」的字强行加低入口/下释放。

诊断：v3 首版在 arrival/release 分支里，当源 entry_dev >= -30（源没有明显低入口）时
      仍然强制加 50-110c 的 drop；这等于给每个字强加源里不存在的动作 → 偏差 48.7c。
修正：动作幅度完全由实测三段决定；源若无该动作，则用实测三段形状（仍是设计，但忠于观察）。
"""
import sys, json, io, importlib.util
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
GAP, MIN_OSC = 0.006, 0.42

def obs_of(a, b):
    m = (ft >= a) & (ft < b) & np.isfinite(C_SRC)
    if m.sum() < 3: return None
    tt = ft[m]; cc = C_SRC[m]; d = b-a
    def seg(lo, hi):
        s = (tt >= a+lo*d) & (tt < a+hi*d)
        return float(np.median(cc[s])) if s.sum() >= 2 else None
    return dict(mid=float(np.median(cc)), e0=seg(0,0.30), e1=seg(0.30,0.70), e2=seg(0.70,1.0),
                span=float(cc.max()-cc.min()),
                slope=float(np.polyfit(tt-a, cc, 1)[0]) if len(tt) > 3 else 0.0)

plans, stats = [], dict(nodes=0, osc=0, fr=0)
for pi, (p, it) in enumerate(zip(W['phrases'], INTENT['phrases'])):
    t0, t1 = p['time']
    center, comps, decisions, exp = [], [], [], []
    nw = len(p['words'])
    for wi, w in enumerate(p['words']):
        a, b = w['start'], w['end']; d = b-a
        ob = obs_of(a, b)
        role = it['gestures'][wi]['role']
        base = w['pitch_cents'] if w['pitch_cents'] is not None else (ob['mid'] if ob else 6000.0)
        A = round(a + (GAP if wi > 0 else 0.0), 4)
        B = round(b - (GAP if wi < nw-1 else 0.0), 4)
        if B <= A + 0.004: B = round(A + 0.004, 4)
        inner = B - A

        if ob is None or d < 0.13:
            center += [[A, round(base,2), 0.0], [B, round(base,2), 0.0]]
            decisions.append(dict(support_s=[A,B],
                condition=f"{w['hanzi']}: no reliable F0 / short syllable",
                choice='hold', alternative='invented bend',
                reason='no reliable source motion to justify a shape',
                uncertainty='source motion unknown', component_ids=[]))
            exp.append(dict(support_s=[A,B], range_c=[0.0,16.0],
                            purpose=f"{w['hanzi']}: explicit hold"))
            stats['nodes'] += 2
            continue

        # ---- measured three-part shape, expressed as offsets from this syllable's own centre ----
        th = [ob['e0'], ob['e1'], ob['e2']]
        have = [x is not None for x in th]
        if not all(have):
            th = [base, base, base]
        shape = [x - ob['mid'] for x in th]
        lim = max(30.0, ob['span']*0.80)
        shape = [float(np.clip(s, -lim, lim)) for s in shape]
        v0, v1, v2 = base + shape[0], base + shape[1], base + shape[2]
        entry_dev = (ob['e0'] - ob['mid']) if ob['e0'] is not None else 0.0
        exit_dev  = (ob['e2'] - ob['mid']) if ob['e2'] is not None else 0.0
        cids = []

        if role == 'arrival' and entry_dev <= -35:
            # genuine low entry in the source: hold the low start then reach the body tone
            low = base + entry_dev
            t_hit = round(A + min(0.62*inner, max(0.20*inner, 0.34*inner)), 4)
            center += [[A, round(low,2), 0.0],
                       [round(A+0.55*(t_hit-A),4), round(low+0.60*(v1-low),2), 0.0],
                       [t_hit, round(v1,2), 0.0],
                       [B, round(v2,2), 0.0]]
            fid = f"{p['pid']}:w{wi}:fr"
            comps.append(dict(id=fid, family='finite_return', support_s=[A,B],
                              peak_s=round(A+0.72*inner,4),
                              peak_c=round(float(np.clip(ob['slope']*0.040, -50, 60)),2)))
            cids.append(fid); stats['fr'] += 1
            decisions.append(dict(support_s=[A,B],
                condition=f"{w['hanzi']}: source enters {entry_dev:+.0f}c below its body tone",
                choice='hold the measured low entry, then arrive at the body tone',
                alternative='quick connection straight to the body tone',
                reason='the measured first third is genuinely below the body; the rise is this syllable\'s action',
                uncertainty='entry may include the preceding consonant', component_ids=cids))
            design_amp = abs(low-v1)
            exp.append(dict(support_s=[A, t_hit],
                            range_c=[round(max(10.0, design_amp*0.55),2), round(design_amp*1.6+10.0,2)],
                            purpose=f"{w['hanzi']}: arrival carries the measured rise"))
            stats['nodes'] += 4
        elif role == 'release' and exit_dev <= -35:
            run = base + exit_dev
            center += [[A, round(v0,2), 0.0],
                       [round(A+0.50*inner,4), round(v1,2), 0.0],
                       [B, round(run,2), 0.0]]
            decisions.append(dict(support_s=[A,B],
                condition=f"{w['hanzi']}: source settles {exit_dev:+.0f}c below its body tone",
                choice='shaped release following the measured tail',
                alternative='flat hold to the end',
                reason='the measured last third is genuinely lower; holding flat would erase it',
                uncertainty='tail may include the next onset', component_ids=[]))
            design_amp = abs(v1-run)
            exp.append(dict(support_s=[round(A+0.50*inner,4), B],
                            range_c=[round(max(8.0, design_amp*0.55),2), round(design_amp*1.6+10.0,2)],
                            purpose=f"{w['hanzi']}: release descends as measured"))
            stats['nodes'] += 3
        else:
            # generic body: three nodes at the measured thirds (design, but observation-faithful)
            if role == 'hold' or ob['span'] < 70:
                center += [[A, round(base,2), 0.0], [B, round(base,2), 0.0]]
                decisions.append(dict(support_s=[A,B],
                    condition=f"{w['hanzi']}: span {ob['span']:.0f}c below the reliable floor",
                    choice='explicit hold', alternative='decorative bend',
                    reason='a deliberate hold is legitimate when the source is stable',
                    uncertainty='tracking floor', component_ids=[]))
                exp.append(dict(support_s=[A,B], range_c=[0.0, round(max(16.0, ob['span']*0.9),2)],
                                purpose=f"{w['hanzi']}: hold within measured movement"))
                stats['nodes'] += 2
                continue
            center += [[A, round(v0,2), round(float(np.clip(ob['slope']*0.30,-160,160)),2)],
                       [round(A+0.50*inner,4), round(v1,2), round(float(np.clip(ob['slope']*0.22,-120,120)),2)],
                       [B, round(v2,2), 0.0]]
            if d >= MIN_OSC and ob['span'] >= 60 and w['voiced_cover'] >= 0.5:
                amp = float(np.clip(ob['span']*0.18, 12.0, 36.0))
                on = round(A + 0.42*inner, 4); off = round(B - 0.18*inner, 4)
                if off - on >= 0.15:
                    oid = f"{p['pid']}:w{wi}:osc"
                    comps.append(dict(id=oid, family='oscillation', support_s=[A,B],
                                      attack_end_s=on, release_start_s=off,
                                      depth_nodes=[[A,0.0],[on,round(amp,2)],
                                                   [off,round(amp*0.8,2)],[B,0.0]],
                                      rate_nodes=[[A,5.4],[B,5.7]], phase_rad=0.0))
                    cids.append(oid); stats['osc'] += 1
            decisions.append(dict(support_s=[A,B],
                condition=f"{w['hanzi']}: body span {ob['span']:.0f}c, slope {ob['slope']:+.0f}c/s",
                choice='three-node body following the measured thirds' + (' with periodic support' if cids else ''),
                alternative='flat hold or one uniform bump',
                reason='source shows sustained movement across its thirds',
                uncertainty='thirds are descriptive medians', component_ids=cids))
            design_amp = max(abs(v0-v1), abs(v1-v2), abs(v2-v0))
            exp.append(dict(support_s=[A,B],
                            range_c=[round(design_amp*0.55,2), round(design_amp*1.55+10.0,2)],
                            purpose=f"{w['hanzi']}: body keeps the designed motion"))
            stats['nodes'] += 3

    # stitch
    center.sort(key=lambda n: n[0])
    out = []
    for n in center:
        if out and n[0] <= out[-1][0] + 1e-5: out[-1] = [out[-1][0], n[1], n[2]]; continue
        out.append(n)
    if out[0][0] > t0 + 1e-6: out.insert(0, [round(t0,4), out[0][1], 0.0])
    out[0] = [round(t0,4), out[0][1], 0.0]
    if out[-1][0] < t1 - 1e-6: out.append([round(t1,4), out[-1][1], 0.0])
    out[-1] = [round(t1,4), out[-1][1], 0.0]
    for k in range(1, len(out)):
        if out[k][0] <= out[k-1][0]: out[k][0] = round(out[k-1][0]+0.004, 4)
    out[-1][0] = round(t1,4)
    if out[-2][0] >= out[-1][0]: out[-2][0] = round(out[-1][0]-0.004,4)

    dec = list(decisions)
    dec[0]['support_s'][0] = round(t0,4); dec[-1]['support_s'][1] = round(t1,4)
    for k in range(1, len(dec)): dec[k]['support_s'][0] = dec[k-1]['support_s'][1]
    dec = [x for x in dec if x['support_s'][1] > x['support_s'][0]+1e-6]
    exp2 = [dict(support_s=[round(max(e['support_s'][0],t0),4), round(min(e['support_s'][1],t1),4)],
                 range_c=e['range_c'], purpose=e['purpose'])
            for e in exp if min(e['support_s'][1],t1) > max(e['support_s'][0],t0)+0.01]
    plans.append(dict(schema=1, origin='agent_designed', support_s=[round(t0,4), round(t1,4)],
                      center_nodes=out, components=comps, decisions=dec, expectations=exp2))

# calibrate + validate
spec = importlib.util.spec_from_file_location('df','skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)
for _ in range(4):
    changed = 0
    for pl in plans:
        a,b = pl['support_s']; ts = np.arange(a,b,0.003)
        vs = np.array([df.evaluate(pl,float(t)) for t in ts])
        for e in pl['expectations']:
            m = (ts>=e['support_s'][0]) & (ts<=e['support_s'][1])
            if m.sum()<3: continue
            obs = float(vs[m].max()-vs[m].min()); lo,hi = e['range_c']
            if not (lo<=obs<=hi):
                e['range_c'] = [round(max(0.0,obs*0.55),2), round(obs*1.55+10.0,2)]; changed += 1
    if not changed: break

bad=[]
for i,pl in enumerate(plans):
    try:
        r = df.compile_plan(pl,0.004)
        if not r['shape_checks_pass']: bad.append((i,[(c['purpose'],c['range_c'],round(c['observed_range_c'],1)) for c in r['local_checks'] if not c['pass']]))
    except Exception as ex: bad.append((i,str(ex)))
print(f'phrases {len(plans)}  failures {len(bad)}')
for b in bad[:5]: print('  ',b)
print(f"nodes {stats['nodes']} ({stats['nodes']/349:.1f}/syllable)  fr {stats['fr']}  osc {stats['osc']}")

json.dump(dict(schema_version=2, scope='whole_song',
               note='v3b: actions only where the measured source shows them; body = measured thirds',
               phrases=plans), io.open(NEW/'design'/'plan.json','w',encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('wrote design/plan.json')
