"""v1 vs v2 同口径对比：旋律身份 / 字腹 / 时值 / 模板化 / 呼吸 / 发声层。"""
import json
import pathlib
import sys
from collections import Counter

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
TICK = 1.0416666666666667e-3
V1 = pathlib.Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
V2 = pathlib.Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-v2-20261028")


def load(run):
    zf = np.load(run / "observation" / "fcpe.npz")
    zr = np.load(run / "observation" / "rmvpe.npz")
    t_f, f0_f = zf["times"].astype(float), zf["f0_hz"].astype(float)
    t_r, f0_r = zr["times"].astype(float), zr["f0_hz"].astype(float)
    c_f = np.where(f0_f > 0, 6900 + 1200 * np.log2(np.maximum(f0_f, 1e-6) / 440), np.nan)
    c_r = np.where(f0_r > 0, 6900 + 1200 * np.log2(np.maximum(f0_r, 1e-6) / 440), np.nan)
    rf = np.interp(t_f, t_f, c_f)
    rr = np.interp(t_f, t_r, c_r)
    agree = np.isfinite(rf) & np.isfinite(rr) & (np.abs(rf - rr) <= 120)
    c_all = np.where(agree, (rf + rr) / 2, np.nan)
    pitch = json.loads((run / "compiled" / "pitch.json").read_text(encoding="utf-8"))["phrases"]
    score = yaml.safe_load((run / "design" / "score.ustx").read_text(encoding="utf-8"))
    plan = json.loads((run / "design" / "plan.json").read_text(encoding="utf-8"))
    invp = run / "design" / "review-inventory.json"
    if not invp.exists():
        invp = run / "design" / "inventory.json"
    inv = json.loads(invp.read_text(encoding="utf-8"))
    return dict(t=t_f, c=c_all, agree=agree, pitch=pitch, score=score, plan=plan, inv=inv)


def analyze(tag, run, D):
    t, c, agree = D["t"], D["c"], D["agree"]
    devs, spans, tiny, comps, peaks, notes_total, sung_total = [], [], 0, 0, Counter(), 0, 0
    zero_slope = nodes_total = 0
    breath = 0
    for pi, vp in enumerate(D["score"]["voice_parts"]):
        pp = vp["position"]
        for n in vp["notes"]:
            notes_total += 1
            if n["lyric"] in ("SP", "AP"):
                breath += 1
                continue
            sung_total += 1
            a = (pp + n["position"]) * TICK
            b = a + n["duration"] * TICK
            if b - a < 0.10:
                tiny += 1
            m = (t >= a + 0.2 * (b - a)) & (t <= b - 0.2 * (b - a)) & agree
            if m.sum() >= 3:
                devs.append(float(np.median(c[m])) - n["tone"] * 100.0)
    for ph in D["plan"]["phrases"]:
        d = ph["design"]
        nodes = np.asarray(d["center_nodes"], float)
        nodes_total += len(nodes)
        zero_slope += int(np.count_nonzero(nodes[:, 2] == 0))
        for cc in d["components"]:
            comps += 1
            if cc["family"] == "finite_return":
                peaks[round(cc["peak_c"], 1)] += 1
    # 字腹：源 vs 设计的逐单元跨度
    for u in D["inv"]["units"]:
        a, b = u["support_s"]
        m = (t >= a + 0.01) & (t <= b - 0.01) & agree
        if m.sum() < 3:
            continue
        v = c[m]
        best = 0.0
        lo = hi = v[0]
        prev = t[m][0]
        for tt, vv in zip(t[m][1:], v[1:]):
            if tt - prev > 0.06:
                best = max(best, hi - lo)
                lo = hi = vv
            else:
                lo = min(lo, vv)
                hi = max(hi, vv)
            prev = tt
        spans.append(max(best, hi - lo))
    ad = np.array([abs(x) for x in devs])
    top = peaks.most_common(4)
    return dict(tag=tag, notes=notes_total, sung=sung_total, breath=breath, tiny=tiny,
                dev_med=round(float(np.median(ad)), 1), dev_p90=round(float(np.percentile(ad, 90)), 1),
                dev_over50=int((ad > 50).sum()), dev_over100=int((ad > 100).sum()), dev_n=len(devs),
                src_body_med=round(float(np.median(spans)), 1) if spans else None,
                components=comps, zero_slope=zero_slope, nodes=nodes_total,
                peak_top=top, peak52=peaks[52.0] + peaks[-52.0], peak32=peaks[32.0] + peaks[-32.0])


rows = []
for tag, run in (("v1", V1), ("v2", V2)):
    D = load(run)
    rows.append(analyze(tag, run, D))

print(f"{'指标':26s} {'v1':>12s} {'v2':>12s}")
keys = [("唱字音符数", "sung"), ("呼吸音符", "breath"), ("极短唱字(<0.10s)", "tiny"),
        ("音符级偏差中位(c)", "dev_med"), ("偏差p90(c)", "dev_p90"), ("偏差>50c", "dev_over50"),
        ("偏差>100c", "dev_over100"), ("源字腹跨度中位(c)", "src_body_med"),
        ("动作组件数", "components"), ("|peak|=52 的组件", "peak52"), ("|peak|=32 的组件", "peak32"),
        ("零斜率中心节点", "zero_slope"), ("中心节点总数", "nodes")]
for name, k in keys:
    print(f"{name:26s} {str(rows[0][k]):>12s} {str(rows[1][k]):>12s}")
print()
for r in rows:
    print(r["tag"], "top peak values:", r["peak_top"])
json.dump(rows, open(r"E:\project\agent2utau\scratch\v1_v2_compare.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
