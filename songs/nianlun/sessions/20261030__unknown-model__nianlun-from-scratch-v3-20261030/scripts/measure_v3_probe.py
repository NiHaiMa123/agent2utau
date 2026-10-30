"""直接测量探针已渲染的 12 个变体（不再重新渲染），得出逐参数敏感度。"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
PROBE = ROOT / "scratch" / "v3_param_probe"

LEVELS = {"voic": [90, 114, 138], "brec": [-20, 0, 20], "tenc": [-20, 0, 20], "dyn": [-40, 0, 40]}


def measure(path):
    aud, sr = sf.read(str(path), dtype="float32")
    if aud.ndim > 1:
        aud = aud.mean(axis=1)
    n = int(sr * 0.04)
    hop = int(sr * 0.01)
    win = np.hanning(n)
    hnrs, cens, rmss = [], [], []
    for s in range(0, max(0, len(aud) - n), hop):
        fr = aud[s:s + n]
        if np.sqrt((fr ** 2).mean()) < 1e-4:
            continue
        rmss.append(float(np.sqrt((fr ** 2).mean())))
        sp = np.abs(np.fft.rfft(fr * win))
        fq = np.fft.rfftfreq(n, 1.0 / sr)
        cens.append(float((sp * fq).sum() / (sp.sum() + 1e-12)))
        m = 1 << int(np.ceil(np.log2(2 * n)))
        acf = np.fft.irfft(np.abs(np.fft.rfft(fr, m)) ** 2, m)[:n]
        if acf[0] <= 0:
            continue
        r_ = acf / acf[0]
        lo, hi = int(sr / 600.0), min(int(sr / 80.0), n - 2)
        if hi <= lo:
            continue
        rm = float(np.max(r_[lo:hi]))
        rm = min(max(rm, 1e-4), 0.999)
        hnrs.append(10 * math.log10(rm / (1 - rm)))
    if not rmss:
        return None
    return dict(hnr_db=round(float(np.median(hnrs)), 3) if hnrs else None,
                centroid_hz=round(float(np.median(cens)), 1) if cens else None,
                rms_db=round(float(20 * np.log10(np.mean(rmss) + 1e-12)), 3))


results = {}
for abbr, levels in LEVELS.items():
    rows = []
    for lv in levels:
        p = PROBE / f"{abbr}_{lv}_vocal.wav"
        if not p.exists():
            p = PROBE / f"{abbr}_{lv}_vocal_vocal.wav"
        if not p.exists():
            continue
        m = measure(p)
        if m:
            m["level"] = lv
            rows.append(m)
    if not rows:
        continue
    xs = np.array([r["level"] for r in rows], float)
    entry = dict(rows=rows, levels=levels)
    for key in ("hnr_db", "centroid_hz", "rms_db"):
        ys = np.array([r[key] for r in rows], float)
        if np.all(np.isfinite(ys)):
            entry[key + "_per_unit"] = round(float(np.polyfit(xs, ys, 1)[0]), 6)
    results[abbr] = entry

out = dict(part_index=20,
           purpose="逐参数单独改档、只改一个参数，测渲染端敏感度（数值版的'分遍精调'）",
           note="渲染产物已由 probe_v3_params.py 生成；本脚本只做测量",
           results=results)
(V3 / "design" / "param_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in results.items():
    print(k, {kk: vv for kk, vv in v.items() if kk not in ("rows", "levels")})
    for r in v["rows"]:
        print("   ", r)
