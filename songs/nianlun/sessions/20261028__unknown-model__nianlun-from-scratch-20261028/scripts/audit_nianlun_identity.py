"""第二轮：音符级旋律身份 + 整句轮廓相关 + 声明意图对照。"""
import json
import pathlib
import sys
from collections import Counter

import numpy as np
import yaml

sys.stdout.reconfigure(encoding="utf-8")
RUN = pathlib.Path(r"E:\project\agent2utau\runs\production\nianlun-from-scratch-20261028")
TICK_MS = 1.0416666666666667


def rj(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


plan = rj(RUN / "design/plan.json")
intent = rj(RUN / "design/musical_intent.json")
game = rj(RUN / "observation/game.json")
pitch = rj(RUN / "compiled/pitch.json")
inventory = rj(RUN / "design/inventory.json")
project = yaml.safe_load((RUN / "compiled/project.ustx").read_text(encoding="utf-8"))

z = np.load(RUN / "observation/fcpe.npz", allow_pickle=True)
f0 = z["f0_hz"].astype(np.float64)
voiced = z["voiced"].astype(bool)
times = z["times"].astype(np.float64)
with np.errstate(divide="ignore", invalid="ignore"):
    cents = np.where(f0 > 0, 1200.0 * np.log2(f0 / 440.0), np.nan)
cents = cents + 6900.0
src_ok = voiced & np.isfinite(cents)

game_notes = game["notes"]
parts = project["voice_parts"]
final_phrases = pitch["phrases"]

# ---------- 1. 音符级旋律身份: USTX tone vs GAME tone ----------
print("== 音符级：USTX 音高 vs GAME 转谱音高 (同时间窗) ==")
rows = []
for i, vp in enumerate(parts):
    pp = final_phrases[i]
    part_pos = vp["position"]
    for n in vp["notes"]:
        if n["lyric"] in ("SP", "AP", "+"):
            continue
        a = (part_pos + n["position"]) * TICK_MS / 1000.0
        b = (part_pos + n["position"] + n["duration"]) * TICK_MS / 1000.0
        m = (game_notes and np.array([g["start"] < b and g["start"] + g["dur"] > a for g in game_notes]))
        cand = [g for g, keep in zip(game_notes, m) if keep and g.get("voiced")]
        if not cand:
            cand = [g for g, keep in zip(game_notes, m) if keep]
        if not cand:
            continue
        g = max(cand, key=lambda x: min(x["start"] + x["dur"], b) - max(x["start"], a))
        g_c = g["tone"] * 100.0
        d_c = n["tone"] * 100.0
        rows.append(dict(pi=i, lyric=n["lyric"], t=round(a, 2),
                         ustx_c=d_c, game_c=round(g_c, 1), diff_c=round(d_c - g_c, 1),
                         dur=round(n["duration"] * TICK_MS / 1000.0, 2),
                         game_dur=round(g["dur"], 2)))
diffs = [abs(r["diff_c"]) for r in rows]
print(f"音符数 {len(rows)}  |diff| 中位 {np.median(diffs):.0f}c  p90 {np.percentile(diffs,90):.0f}c  "
      f">50c {sum(1 for d in diffs if d>50)}  >100c {sum(1 for d in diffs if d>100)}  "
      f">200c {sum(1 for d in diffs if d>200)}  >600c {sum(1 for d in diffs if d>600)}")
worst = sorted(rows, key=lambda r: -abs(r["diff_c"]))[:18]
for r in worst:
    print(f"  p{r['pi']:02d} {r['t']:7.2f}s '{r['lyric']}' USTX {r['ustx_c']:.0f} vs GAME {r['game_c']:.0f} "
          f"→ {r['diff_c']:+.0f}c   时值 {r['dur']}s / 源 {r['game_dur']}s")

# 每句 |diff| 统计
per_pi = {}
for r in rows:
    per_pi.setdefault(r["pi"], []).append(abs(r["diff_c"]))
print("\n每句音符级偏差(相对GAME, cents):")
for pi in sorted(per_pi):
    v = per_pi[pi]
    print(f"  p{pi:02d}: n{len(v):2d} 中位{np.median(v):6.0f} 最大{max(v):6.0f} >100c:{sum(1 for x in v if x>100)}")

# ---------- 2. 整句轮廓相关 ----------
print("\n== 整句轮廓相关（源 FCPE vs 设计最终线，10ms 重采样） ==")
for i, ph in enumerate(plan["phrases"]):
    a, b = ph["design"]["support_s"]
    fp = final_phrases[i]
    ft = np.array(fp["times_ms"]) / 1000.0
    fc = np.array(fp["final_cents"], dtype=float)
    grid = np.arange(a, b, 0.02)
    s = np.interp(grid, times, cents)
    d = np.interp(grid, ft, fc)
    sm = src_ok[np.clip(np.searchsorted(times, grid), 0, len(times) - 1)]
    valid = sm & np.isfinite(s)
    if valid.sum() < 10:
        print(f"  p{i:02d}: 源有���段不足")
        continue
    r = float(np.corrcoef(s[valid], d[valid])[0, 1])
    # 源线相对其自身整句中位趋势的残差 vs 设计残差
    smed = np.median(s[valid])
    dmed = np.median(d[valid])
    sr = s[valid] - smed
    dr = d[valid] - dmed
    print(f"  p{i:02d}: r={r:+.2f}  源残差RMS={float(np.sqrt((sr**2).mean())):6.1f}c "
          f"设计残差RMS={float(np.sqrt((dr**2).mean())):6.1f}c  源中位{smed:7.1f} 设计中位{dmed:7.1f} "
          f"整体差{dmed-smed:+7.1f}c")

# ---------- 3. 声明意图 ----------
print("\n== musical_intent 前 2 句的声明 ==")
ip = intent.get("phrases", [])
for p_ in ip[:2]:
    print(json.dumps(p_, ensure_ascii=False, indent=1)[:2200])
print("intent 顶层键:", list(intent.keys()))
print("phrase 数:", len(ip), " phonation:", json.dumps(intent.get("phonation"), ensure_ascii=False)[:400])
