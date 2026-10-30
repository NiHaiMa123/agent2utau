"""逐句分级：按 Skill 复检口径给 51 句定级与问题标签。"""
import json
import pathlib
import sys
from collections import Counter

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
RUN = pathlib.Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
TICK = 1.0416666666666667


def rj(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def load(name):
    z = np.load(RUN / "observation" / name, allow_pickle=True)
    f0 = z["f0_hz"].astype(np.float64)
    t = z["times"].astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.where(f0 > 0, 1200.0 * np.log2(f0 / 440.0) + 6900.0, np.nan)
    return c, t, np.isfinite(c)


fcpe, t_f, ok_f = load("fcpe.npz")
rmvpe, t_r, ok_r = load("rmvpe.npz")
audit = rj(r"E:\project\agent2utau\scratch\audit_nianlun_phrases.json")
pitch = rj(RUN / "compiled/pitch.json")
project = yaml.safe_load((RUN / "compiled/project.ustx").read_text(encoding="utf-8"))
parts = project["voice_parts"]
final_phrases = pitch["phrases"]
ph_data = {p["part_index"]: p for p in audit["phrases"]}

per_pi_bad = {}
per_pi_unc = {}
for i, vp in enumerate(parts):
    fp = final_phrases[i]
    ft = np.array(fp["times_ms"]) / 1000.0
    fc = np.array(fp["final_cents"], dtype=float)
    bad, unc = [], []
    for n in vp["notes"]:
        if n["lyric"] in ("SP", "AP", "+"):
            continue
        a = (vp["position"] + n["position"]) * TICK / 1000.0
        d = n["duration"] * TICK / 1000.0
        a2, b2 = a + 0.2 * d, a + 0.8 * d
        m = (ft >= a2) & (ft < b2)
        mf = ok_f & (t_f >= a2) & (t_f < b2)
        mr = ok_r & (t_r >= a2) & (t_r < b2)
        if m.sum() < 3 or mf.sum() < 4 or mr.sum() < 4:
            continue
        dmed = float(np.median(fc[m]))
        f = float(np.median(fcpe[mf]))
        r = float(np.median(rmvpe[mr]))
        if abs(f - r) > 120:
            unc.append((n["lyric"], round(dmed), round(f), round(r)))
            continue
        dev = dmed - (f + r) / 2
        if abs(dev) > 100:
            bad.append((n["lyric"], round(dev)))
    per_pi_bad[i] = bad
    per_pi_unc[i] = unc

print("句 | 时间窗 | 坏音(两检测器一致) | 压平元音 | 极短字 | 轮廓r | 长字未展开 | 级别 | 标签")
r_by_pi = {}
for i, ph in enumerate(final_phrases):
    pass
# 轮廓相关
for i, p in enumerate(plan_phrases := rj(RUN / "design/plan.json")["phrases"]):
    a, b = p["design"]["support_s"]
    fp = final_phrases[i]
    ft = np.array(fp["times_ms"]) / 1000.0
    fc = np.array(fp["final_cents"], dtype=float)
    grid = np.arange(a, b, 0.02)
    s = np.interp(grid, t_f, fcpe)
    d = np.interp(grid, ft, fc)
    v = ok_f[np.clip(np.searchsorted(t_f, grid), 0, len(t_f) - 1)]
    if v.sum() >= 10:
        r_by_pi[i] = float(np.corrcoef(s[v], d[v])[0, 1])

long_uncovered = {}
for i, vp in enumerate(parts):
    comps = rj(RUN / "design/plan.json")["phrases"][i]["design"]["components"]
    cnt = 0
    for n in vp["notes"]:
        if n["lyric"] in ("SP", "AP", "+"):
            continue
        d = n["duration"] * TICK / 1000.0
        if d < 0.45:
            continue
        a = (vp["position"] + n["position"]) * TICK / 1000.0
        b = a + d
        cov = [c for c in comps if c["support_s"][0] >= a - 0.06 and c["support_s"][1] <= b + 0.06]
        ratio = (cov[-1]["support_s"][1] - cov[0]["support_s"][0]) / d if cov else 0
        if ratio < 0.9:
            cnt += 1
    long_uncovered[i] = cnt

rows = []
for i, p in enumerate(plan_phrases):
    a, b = p["design"]["support_s"]
    d = ph_data[i]
    bad = per_pi_bad[i]
    unc = per_pi_unc[i]
    tiny = [n["lyric"] for n in parts[i]["notes"]
            if n["lyric"] not in ("SP", "AP", "+") and n["duration"] * TICK / 1000 < 0.10]
    r = r_by_pi.get(i)
    tags = []
    if bad:
        tags.append(f"旋律偏{len(bad)}音")
    if unc:
        tags.append(f"源不确定{len(unc)}音")
    if d["n_flattened"]:
        tags.append(f"字腹压平{d['n_flattened']}")
    if tiny:
        tags.append(f"极短字{len(tiny)}{''.join(tiny)}")
    if r is not None and r < 0.6:
        tags.append(f"轮廓脱形r={r:.2f}")
    if long_uncovered[i]:
        tags.append(f"长字未展开{long_uncovered[i]}")
    if d["eng_breath"] == [] and d["hfa_breath"]:
        tags.append("无呼吸标记")
    # 定级
    if len(bad) >= 2 or tiny or (r is not None and r < 0.4):
        lvl = "P0"
    elif bad or d["n_flattened"] >= 3 or (r is not None and r < 0.7) or long_uncovered[i] >= 2:
        lvl = "P1"
    elif d["n_flattened"] or long_uncovered[i] or d["n_osc"] == 0:
        lvl = "P2"
    else:
        lvl = "P3"
    rows.append((i, a, b, lvl, tags, bad, unc, tiny, r, d["n_flattened"], long_uncovered[i]))

for i, a, b, lvl, tags, bad, unc, tiny, r, flat, lu in rows:
    print(f"p{i:02d} {a:6.1f}-{b:6.1f} {lvl} | " + "; ".join(tags))
    if bad:
        print("      坏音: " + ", ".join(f"'{l}'{dv:+d}c" for l, dv in bad))
    if unc:
        print("      源不确定: " + ", ".join(f"'{l}' 设计{d}/FCPE{f}/RMVPE{r2}" for l, d, f, r2 in unc))

print("\n级别统计:", Counter(x[3] for x in rows))
json.dump([dict(part_index=i, support_s=[a, b], level=lvl, tags=tags,
                 bad_notes=bad, uncertain=unc, tiny=tiny,
                 contour_r=r, flattened=flat, long_uncovered=lu)
            for i, a, b, lvl, tags, bad, unc, tiny, r, flat, lu in rows],
          open(r"E:\project\agent2utau\scratch\audit_nianlun_grading.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
