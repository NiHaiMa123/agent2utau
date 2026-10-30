"""用局部线性去趋势重做涟漪频谱检测，统计各判据的接受率与阈值敏感度。"""
import math
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scratch"))
from agent2utau.openutau.ustx import load_ustx
from nianlun_v3_source import Source, filled_track, local_detrend

V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
src = Source(V3)
doc = load_ustx(V3 / "design" / "score.ustx")
TICK_S = 60.0 / (120.0 * 480)


def spectrum_fit(tt, vv, a, b):
    n = len(tt)
    if n < 24:
        return None
    dt = float(np.mean(np.diff(tt)))
    res = local_detrend(vv, half=12)
    if res.std() < 3.0:
        return None
    win = np.hanning(n)
    sp = np.abs(np.fft.rfft(res * win)) ** 2
    fr = np.fft.rfftfreq(n, dt)
    band = (fr >= 3.0) & (fr <= 8.5)
    if band.sum() < 4:
        return None
    bp = sp[band]
    idx = int(np.argmax(bp))
    f = float(fr[band][idx])
    peak, med, total = float(bp[idx]), float(np.median(bp)), float(bp.sum())
    if med <= 0 or total <= 0:
        return None
    sharp, dom = peak / med, peak / total
    best = None
    for ff in np.arange(max(3.0, f - 0.4), min(8.5, f + 0.4) + 1e-9, 0.02):
        w = 2 * np.pi * ff * (tt - a)
        cm, sm = np.cos(w).mean(), np.sin(w).mean()
        cc = float(((np.cos(w) - cm) * (res - res.mean())).sum() / len(res))
        ss = float(((np.sin(w) - sm) * (res - res.mean())).sum() / len(res))
        amp = math.hypot(cc, ss)
        if best is None or amp > best[1]:
            best = (float(ff), amp, float(math.atan2(ss, cc) - math.pi / 2))
    return dict(f=best[0], amp=best[1], sharp=sharp, dom=dom, dur=b - a,
                span=float(vv.max() - vv.min()))


rows = []
for pi in range(51):
    part = doc["voice_parts"][pi]
    base = part["position"] * TICK_S
    for ni, n in enumerate(part["notes"]):
        if str(n["lyric"]) in ("AP", "SP"):
            continue
        a = base + n["position"] * TICK_S
        b = base + (n["position"] + n["duration"]) * TICK_S
        ft = filled_track(src, a, b)
        if ft is None:
            continue
        r = spectrum_fit(ft[0], ft[1], a, b)
        if r:
            r["dur_ok"] = r["dur"] >= 2.5 / r["f"]
            r["amp_ok"] = r["amp"] >= 18 and r["amp"] <= 0.35 * max(r["span"], 40)
            rows.append(r)
print("notes with spectrum:", len(rows))
for sh in (2.0, 2.5, 3.0, 4.0):
    for dm in (0.20, 0.25, 0.30, 0.35):
        ok = [r for r in rows if r["sharp"] >= sh and r["dom"] >= dm and r["dur_ok"] and r["amp_ok"]]
        print(f"  sharp>={sh} dom>={dm}: {len(ok)} notes, "
              f"amp p50 {np.median([r['amp'] for r in ok]) if ok else 0:.0f}c, "
              f"freq p50 {np.median([r['f'] for r in ok]) if ok else 0:.2f}Hz")
