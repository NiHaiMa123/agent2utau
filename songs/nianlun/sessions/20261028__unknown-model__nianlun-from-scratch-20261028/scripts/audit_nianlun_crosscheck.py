"""第四轮：双检测器一致口径的音符级偏差 + 时值 + 呼吸 + 长字展开。"""
import json
import pathlib
import sys

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
RUN = pathlib.Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
TICK_MS = 1.0416666666666667


def rj(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def load_npz(name):
    z = np.load(RUN / "observation" / name, allow_pickle=True)
    f0 = z["f0_hz"].astype(np.float64)
    t = z["times"].astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.where(f0 > 0, 1200.0 * np.log2(f0 / 440.0) + 6900.0, np.nan)
    return c, t, np.isfinite(c)


fcpe, t_f, ok_f = load_npz("fcpe.npz")
rmvpe, t_r, ok_r = load_npz("rmvpe.npz")
pitch = rj(RUN / "compiled/pitch.json")
project = yaml.safe_load((RUN / "compiled/project.ustx").read_text(encoding="utf-8"))
game = rj(RUN / "observation/game.json")
plan = rj(RUN / "design/plan.json")
hfa = rj(RUN / "hfa/hfa_summary.json")
parts = project["voice_parts"]
final_phrases = pitch["phrases"]


def med_in(c, ok, t, a, b):
    m = ok & (t >= a) & (t < b)
    if m.sum() < 4:
        return None
    return float(np.median(c[m])), int(m.sum())


print("== 1. 音符级：两检测器一致且与设计偏离 >100c 的音符 ==")
print("   (窗口取音符中部 60%，避开前后滑音；需两检测器都有 >=4 帧)")
real_bad, uncertain, ok_cnt = [], [], 0
for i, vp in enumerate(parts):
    fp = final_phrases[i]
    ft = np.array(fp["times_ms"]) / 1000.0
    fc = np.array(fp["final_cents"], dtype=float)
    for n in vp["notes"]:
        if n["lyric"] in ("SP", "AP", "+"):
            continue
        a = (vp["position"] + n["position"]) * TICK_MS / 1000.0
        d = n["duration"] * TICK_MS / 1000.0
        a2, b2 = a + 0.2 * d, a + 0.8 * d
        m = (ft >= a2) & (ft < b2)
        if m.sum() < 3:
            continue
        dmed = float(np.median(fc[m]))
        f = med_in(fcpe, ok_f, t_f, a2, b2)
        r = med_in(rmvpe, ok_r, t_r, a2, b2)
        if not f or not r:
            continue
        if abs(f[0] - r[0]) > 120:      # 两检测器互相矛盾 -> unknown
            uncertain.append((i, n["lyric"], round(a, 2), round(dmed), round(f[0]), round(r[0])))
            continue
        src = (f[0] + r[0]) / 2
        dev = dmed - src
        if abs(dev) > 100:
            real_bad.append((i, n["lyric"], round(a, 2), round(dmed), round(src), round(dev),
                             round(f[0]), round(r[0]), round(d, 2)))
        else:
            ok_cnt += 1
print(f"两检测器一致且设计偏差<=100c: {ok_cnt} 个音符")
print(f"两检测器一致但设计偏差>100c : {len(real_bad)} 个音符")
for x in sorted(real_bad, key=lambda r: -abs(r[5]))[:26]:
    print(f"  p{x[0]:02d} '{x[1]}' {x[2]:7.2f}s 设计{x[3]:6d}c 源(FCPE{x[6]},RMVPE{x[7]})→{x[4]:6d}c 差{x[5]:+6d}c  时值{x[8]}s")
print(f"两检测器互相矛盾(unknown): {len(uncertain)} 个音符")
for x in uncertain[:8]:
    print(f"  p{x[0]:02d} '{x[1]}' {x[2]:7.2f}s 设计{x[3]} FCPE{x[4]} RMVPE{x[5]}")

print("\n== 2. 时值：设计 vs GAME ==")
rows = []
for i, vp in enumerate(parts):
    for n in vp["notes"]:
        if n["lyric"] in ("SP", "AP", "+"):
            continue
        a = (vp["position"] + n["position"]) * TICK_MS / 1000.0
        b = a + n["duration"] * TICK_MS / 1000.0
        cand = [g for g in game["notes"] if g["start"] < b and g["start"] + g["dur"] > a]
        if not cand:
            continue
        g = max(cand, key=lambda x: min(x["start"] + x["dur"], b) - max(x["start"], a))
        rows.append((i, n["lyric"], n["duration"] * TICK_MS / 1000.0, g["dur"], a))
rat = [r[2] / r[3] for r in rows if r[3] > 0.15]
print(f"可比音符 {len(rows)}  时值比中位 {np.median(rat):.2f}  <0.7: {sum(1 for x in rat if x<0.7)}  >1.3: {sum(1 for x in rat if x>1.3)}")
for r in sorted([r for r in rows if r[3] > 0.15 and r[2] / r[3] < 0.6], key=lambda r: r[2] / r[3])[:10]:
    print(f"  p{r[0]:02d} '{r[1]}' {r[4]:7.2f}s 设计 {r[2]:.2f}s vs 源 {r[3]:.2f}s ({r[2]/r[3]:.2f})")

print("\n== 3. 呼吸 ==")
eng = {i: [n["lyric"] for n in vp["notes"] if n["lyric"] in ("SP", "AP")] for i, vp in enumerate(parts)}
eng = {k: v for k, v in eng.items() if v}
hb = sum(1 for p in hfa["phrases"] for w in p["words"] if w["mark"] in ("SP", "AP"))
print(f"工程 SP/AP 音符 {sum(len(v) for v in eng.values())} 个（{len(eng)} 句） vs HFA 观测呼吸 {hb} 个")
gaps = []
for i, vp in enumerate(parts):
    notes = vp["notes"]
    for k in range(len(notes) - 1):
        g = (notes[k + 1]["position"] - (notes[k]["position"] + notes[k]["duration"])) * TICK_MS / 1000.0
        if g > 0.4:
            gaps.append((i, notes[k]["lyric"], round(g, 2)))
print(f"音符间 >0.4s 静默: {len(gaps)} 处；其中前音为 SP/AP 的 {sum(1 for g in gaps if g[1] in ('SP','AP'))} 处")
for g in gaps[:12]:
    print(f"  p{g[0]:02d} 前音 '{g[1]}' 间隔 {g[2]}s")

print("\n== 4. 长字展开 ==")
ln = []
for i, vp in enumerate(parts):
    comps = plan["phrases"][i]["design"]["components"]
    for n in vp["notes"]:
        if n["lyric"] in ("SP", "AP", "+"):
            continue
        d = n["duration"] * TICK_MS / 1000.0
        if d < 0.45:
            continue
        a = (vp["position"] + n["position"]) * TICK_MS / 1000.0
        b = a + d
        cov = [c for c in comps if c["support_s"][0] >= a - 0.06 and c["support_s"][1] <= b + 0.06]
        osc = [c for c in cov if c["family"] == "oscillation"]
        ratio = (cov[-1]["support_s"][1] - cov[0]["support_s"][0]) / d if cov else 0
        ln.append((i, n["lyric"], round(d, 2), len(cov), len(osc), round(ratio, 2)))
print(f"时长>=0.45s 唱字 {len(ln)} 个；组件覆盖>=90% 的 {sum(1 for x in ln if x[5]>=0.9)} 个，"
      f"含 oscillation 的 {sum(1 for x in ln if x[5]>=0.9 and x[4]>0)} 个")
for x in sorted(ln, key=lambda x: -x[2])[:14]:
    print(f"  p{x[0]:02d} '{x[1]}' {x[2]}s 组件{x[3]} 振荡{x[4]} 覆盖比{x[5]}")
