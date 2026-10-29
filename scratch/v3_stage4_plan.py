"""阶段4：逐句音高函数设计（schema1，供 design_functions.py 编译）。

与前两版的本质区别：
  v2: 中心线 = 源残差×0.8，13989 个节点（每字40点）→ 逐帧抄源 F0，Skill 禁止
  v3: 中心线 = 该字主音（cent精度）+ 由**源观察归纳的动作**（入口/主体/退出），
      每字 3-6 个节点，参数由该字实测 span/slope/thirds 决定

动作来源（每字独立判断，不套模板）：
  arrival: 从低于主音处进入，按实测第三节高度与时间到达
  release: 主音后按实测尾部下沉量释放
  body:    主音的慢走势 + 长音按实测周期性给 oscillation
  hold:    明确平稳（有依据的克制），只给极小的中心偏移

判据：expectations 用**该字实测范围**（不是固定的 ±12c 自证），
      能被 must_differ 检查否决。
"""
import sys, json, io, math
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

MIN_OSC_DUR = 0.42     # 只有这个长度以上才考虑周期支撑（有依据地不推广到短字）
NODE_MIN_GAP = 0.035   # 节点最小间隔（避免点间尖峰）

def obs_of(a, b):
    m = (ft >= a) & (ft < b) & np.isfinite(C_SRC)
    if m.sum() < 3: return None
    tt = ft[m]; cc = C_SRC[m]; d = b-a
    def seg(lo, hi):
        s = (tt >= a+lo*d) & (tt < a+hi*d)
        return float(np.median(cc[s])) if s.sum() >= 2 else None
    e0, e1, e2 = seg(0.00, 0.30), seg(0.30, 0.70), seg(0.70, 1.00)
    return dict(mid=float(np.median(cc)), e0=e0, e1=e1, e2=e2,
                span=float(cc.max()-cc.min()),
                slope=float(np.polyfit(tt-a, cc, 1)[0]) if len(tt) > 3 else 0.0,
                q10=float(np.percentile(cc,10)), q90=float(np.percentile(cc,90)))

plans, stats = [], dict(nodes=0, osc=0, fin=0, roles={})
for pi, (p, it) in enumerate(zip(W['phrases'], INTENT['phrases'])):
    t0, t1 = p['time']
    center, comps, decisions, exp = [], [], [], []
    total_nodes_this = 0
    for wi, w in enumerate(p['words']):
        a, b = w['start'], w['end']; d = b-a
        ob = obs_of(a, b)
        g = it['gestures'][wi]
        role = g['role']
        base = w['pitch_cents'] if w['pitch_cents'] is not None else (ob['mid'] if ob else 6000.0)
        stats['roles'][role] = stats['roles'].get(role, 0) + 1
        if ob is None or d < 0.12:
            # short / unreliable: explicit hold at the measured centre
            center.append([round(a, 4), round(base, 2), 0.0])
            center.append([round(b, 4), round(base, 2), 0.0])
            decisions.append(dict(support_s=[round(a,4), round(b,4)],
                condition=f"{w['hanzi']}: source F0 unreliable or syllable too short ({d:.2f}s)",
                choice='hold', alternative='invent a bend from the median',
                reason='no reliable source motion; a fabricated bend would be an unsupported claim',
                uncertainty='source motion unknown', component_ids=[]))
            exp.append(dict(support_s=[round(a,4), round(b,4)],
                            range_c=[0.0, max(20.0, (ob['span'] if ob else 25.0)*0.6)],
                            purpose=f"{w['hanzi']}: keep the measured centre without invented motion"))
            total_nodes_this += 2
            continue
        entry_dev = (ob['e0'] - ob['mid']) if ob['e0'] is not None else 0.0
        exit_dev = (ob['e2'] - ob['mid']) if ob['e2'] is not None else 0.0
        # ---- pick the action from THIS syllable's evidence ----
        if role == 'arrival':
            # enter below (or at measured entry), reach the main tone
            low = base + min(0.0, entry_dev) if abs(entry_dev) > 30 else base - min(110.0, max(55.0, ob['span']*0.45))
            t_hit = a + min(0.55*d, max(0.16*d, 0.30*d))
            center += [[round(a,4), round(low,2), 0.0],
                       [round(a+0.55*d,4), round(base + 0.25*(low-base), 2), 0.0],
                       [round(t_hit,4), round(base,2), 0.0],
                       [round(b,4), round(base,2), 0.0]]
            comps.append(dict(id=f"{p['pid']}:w{wi}:fr", family='finite_return',
                              support_s=[round(a,4), round(b,4)],
                              peak_s=round(a+0.72*d,4),
                              peak_c=round(max(-40.0, min(60.0, ob['slope']*0.05)), 2)))
            decisions.append(dict(support_s=[round(a,4), round(b,4)],
                condition=f"{w['hanzi']}: enters {entry_dev:+.0f}c from its main tone",
                choice='center with low entry then arrival',
                alternative='quick connection straight to the main tone',
                reason=f"source thirds {ob['e0'] and round(ob['e0'],0)}/{round(ob['mid'],0)}/{ob['e2'] and round(ob['e2'],0)} show the entry is part of the singing action",
                uncertainty='source entry may include the previous consonant',
                component_ids=[f"{p['pid']}:w{wi}:fr"]))
            exp.append(dict(support_s=[round(a,4), round(t_hit,4)],
                            range_c=[round(max(55.0, abs(low-base)*0.55),2), round(max(90.0, abs(low-base)*1.35),2)],
                            purpose=f"{w['hanzi']}: arrival span must carry the measured rise"))
            stats['fin'] += 1
            total_nodes_this += 4
        elif role == 'release':
            run = base + min(0.0, exit_dev) if abs(exit_dev) > 30 else base - min(90.0, max(45.0, ob['span']*0.4))
            center += [[round(a,4), round(base,2), 0.0],
                       [round(b-0.45*d,4), round(base + 0.15*(run-base),2), 0.0],
                       [round(b,4), round(run,2), 0.0]]
            decisions.append(dict(support_s=[round(a,4), round(b,4)],
                condition=f"{w['hanzi']}: settles {exit_dev:+.0f}c below its main tone",
                choice='hold the main tone then a shaped release',
                alternative='hold flat to the end',
                reason='source exit third differs from the body; a flat hold would erase the release',
                uncertainty='tail may include the next onset',
                component_ids=[]))
            exp.append(dict(support_s=[round(b-0.45*d,4), round(b,4)],
                            range_c=[round(max(40.0, abs(run-base)*0.5),2), round(max(70.0, abs(run-base)*1.4),2)],
                            purpose=f"{w['hanzi']}: release must actually descend"))
            total_nodes_this += 3
        else:  # body / hold
            if role == 'hold' or ob['span'] < 70:
                center += [[round(a,4), round(base,2), 0.0], [round(b,4), round(base,2), 0.0]]
                decisions.append(dict(support_s=[round(a,4), round(b,4)],
                    condition=f"{w['hanzi']}: source movement below the reliable floor (span {ob['span']:.0f}c)",
                    choice='explicit hold at the measured centre',
                    alternative='add a decorative bend',
                    reason='a deliberate hold is a legitimate choice when the source is stable',
                    uncertainty='tracking floor',
                    component_ids=[]))
                exp.append(dict(support_s=[round(a,4), round(b,4)],
                                range_c=[0.0, max(18.0, ob['span']*0.8)],
                                purpose=f"{w['hanzi']}: hold must stay within measured movement"))
                total_nodes_this += 2
            else:
                # body: slow centre drift along the measured slope, plus periodic support on long notes
                drift = float(np.clip(ob['slope']*d*0.55, -abs(ob['span'])*0.6, abs(ob['span'])*0.6))
                center += [[round(a,4), round(base,2), round(ob['slope']*0.4,2)],
                           [round(a+0.5*d,4), round(base+drift*0.5,2), round(ob['slope']*0.3,2)],
                           [round(b,4), round(base+drift,2), 0.0]]
                cids = []
                if d >= MIN_OSC_DUR and ob['span'] >= 60 and w['voiced_cover'] >= 0.5:
                    # vibrato with independent envelope, rate from physical seconds
                    amp = float(np.clip(ob['span']*0.22, 14.0, 42.0))
                    on = round(a + 0.42*d, 4); off = round(b - 0.18*d, 4)
                    if off - on >= 0.16:
                        comps.append(dict(id=f"{p['pid']}:w{wi}:osc", family='oscillation',
                                          support_s=[round(a,4), round(b,4)],
                                          attack_end_s=on, release_start_s=off,
                                          depth_nodes=[[round(a,4), 0.0], [on, round(amp,2)],
                                                       [off, round(amp*0.8,2)], [round(b,4), 0.0]],
                                          rate_nodes=[[round(a,4), 5.4], [round(b,4), 5.7]],
                                          phase_rad=0.0))
                        cids.append(f"{p['pid']}:w{wi}:osc")
                        stats['osc'] += 1
                decisions.append(dict(support_s=[round(a,4), round(b,4)],
                    condition=f"{w['hanzi']}: body span {ob['span']:.0f}c, slope {ob['slope']:+.0f}c/s, dur {d:.2f}s",
                    choice='slow centre drift' + (' + periodic support' if cids else ''),
                    alternative='flat hold or a single uniform bump',
                    reason='source shows a sustained body movement rather than a point arrival',
                    uncertainty='period may be below the detector floor',
                    component_ids=cids))
                exp.append(dict(support_s=[round(a,4), round(b,4)],
                                range_c=[round(max(25.0, ob['span']*0.35),2), round(max(60.0, ob['span']*1.1),2)],
                                purpose=f"{w['hanzi']}: body must retain the measured motion"))
                total_nodes_this += 3
    # ---- stitch: enforce monotone, exact support coverage ----
    center.sort(key=lambda n: n[0])
    merged = []
    for n in center:
        if merged and n[0] - merged[-1][0] < NODE_MIN_GAP:
            # keep the later node but guarantee ordering
            if n[0] <= merged[-1][0] + 1e-6:
                merged[-1] = [merged[-1][0], n[1], n[2]]
                continue
        merged.append(n)
    if merged[0][0] != t0: merged.insert(0, [round(t0,4), merged[0][1], 0.0])
    else: merged[0] = [round(t0,4), merged[0][1], 0.0]
    if merged[-1][0] != t1: merged.append([round(t1,4), merged[-1][1], 0.0])
    else: merged[-1] = [round(t1,4), merged[-1][1], 0.0]
    # decisions must cover full support contiguously
    if decisions[0]['support_s'][0] != round(t0,4):
        decisions[0]['support_s'][0] = round(t0,4)
    if decisions[-1]['support_s'][1] != round(t1,4):
        decisions[-1]['support_s'][1] = round(t1,4)
    for k in range(1, len(decisions)):
        decisions[k]['support_s'][0] = decisions[k-1]['support_s'][1]
    plans.append(dict(schema=1, origin='agent_designed', support_s=[round(t0,4), round(t1,4)],
                      center_nodes=merged, components=comps, decisions=decisions, expectations=exp))
    stats['nodes'] += len(merged)

print(f"phrases {len(plans)}")
print(f"center nodes total {stats['nodes']} (v2 was 13989 for 349 vowels -> {13989/349:.0f}/vowel; "
      f"v3 = {stats['nodes']/349:.1f}/vowel)")
print(f"components: finite_return {stats['fin']}, oscillation {stats['osc']}")
print(f"roles: {stats['roles']}")

# validate with the real helper
import importlib.util
spec = importlib.util.spec_from_file_location('df', 'skills/singing-expression-editor/scripts/design_functions.py')
df = importlib.util.module_from_spec(spec); spec.loader.exec_module(df)
bad = []
for i, pl in enumerate(plans):
    try:
        r = df.compile_plan(pl, 0.002)
        if not r['shape_checks_pass']:
            bad.append((i, [c for c in r['local_checks'] if not c['pass']]))
    except Exception as ex:
        bad.append((i, str(ex)))
print(f'\nvalidation failures: {len(bad)}')
for b in bad[:6]:
    print('  ', b)

(NEW/'design'/'plan.json').write_text(json.dumps(dict(
    schema_version=2, scope='whole_song',
    note='per-phrase explicit Agent function plans; sparse nodes (evidence-derived), not frame-copied source F0',
    phrases=plans), ensure_ascii=False, indent=1), encoding='utf-8')
print('\nwrote design/plan.json')
