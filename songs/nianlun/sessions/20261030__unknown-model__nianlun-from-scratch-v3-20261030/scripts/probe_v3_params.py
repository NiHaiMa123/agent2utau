"""v3 参数剂量-响应探针（B 站流程里"按维度分遍精调"的数值版）。

做法：取一个已成句的 part，逐个参数分别改档位（其它参数不动），
渲染后测 HNR / RMS / 谱重心，得到"每单位参数值"的敏感度，
用于把逐音符取值校准到源的实测水平（渲染->测量->回改闭环）。

输出：design/param_probe.json
"""
import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
COMPILED = V3 / "compiled"
PROBE = ROOT / "scratch" / "v3_param_probe"
PROBE.mkdir(parents=True, exist_ok=True)
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")

PART = 20          # 副歌段的一句
LEVELS = {"voic": [90, 114, 138], "brec": [-20, 0, 20], "tenc": [-20, 0, 20], "dyn": [-40, 0, 40]}

doc = yaml.safe_load((COMPILED / "project.ustx").read_text(encoding="utf-8"))
part = doc["voice_parts"][PART]
notes = part["notes"]
# 该 part 的演唱时间窗
TICK_S = 60.0 / (120.0 * 480)
base = part["position"] * TICK_S
sung = [n for n in notes if str(n["lyric"]) not in ("AP", "SP")]
a = base + min(n["position"] for n in sung) * TICK_S
b = base + max(n["position"] + n["duration"] for n in sung) * TICK_S
print("probe part", PART, "window %.2f-%.2f" % (a, b))


def build_variant(tag, abbr, level):
    d = copy.deepcopy(doc)
    p = d["voice_parts"][PART]
    p["curves"] = [c for c in p["curves"] if c["abbr"] != abbr]
    p["curves"].append(dict(abbr=abbr, xs=list(range(0, 4096, 64)), ys=[int(level)] * 64))
    d["voice_parts"] = [p]
    d["name"] = "probe_" + tag
    out = PROBE / f"{tag}.ustx"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=10 ** 6)
    return out


def render_and_measure(ustx, tag):
    wav = PROBE / f"{tag}_vocal.wav"
    if not wav.exists():
        wav = PROBE / f"{tag}.wav"
    if wav.exists():
        wav.unlink()
    for stale in PROBE.glob(f"{tag}*.review.json"):
        stale.unlink()
    r = subprocess.run([PY, "-m", "agent2utau.cli", "render-project", "--project", str(ustx),
                        "--out", str(wav)], capture_output=True, text=True, cwd=str(ROOT))
    if r.returncode != 0 or not wav.exists():
        print("  render failed:", (r.stderr or "")[-400:])
        return None
    aud, sr = sf.read(str(wav), dtype="float32")
    if aud.ndim > 1:
        aud = aud.mean(axis=1)
    # 迷你工程只含这一句，整段音频即为该句
    seg = aud
    if len(seg) < sr * 0.1:
        return None
    n = int(sr * 0.04)
    hop = int(sr * 0.01)
    hnrs, cens, rmss = [], [], []
    win = np.hanning(n)
    for s in range(0, len(seg) - n, hop):
        fr = seg[s:s + n]
        if np.sqrt((fr ** 2).mean()) < 1e-4:
            continue
        rmss.append(float(np.sqrt((fr ** 2).mean())))
        sp = np.abs(np.fft.rfft(fr * win))
        fq = np.fft.rfftfreq(n, 1.0 / sr)
        cens.append(float((sp * fq).sum() / (sp.sum() + 1e-12)))
        acf = np.fft.irfft(np.abs(np.fft.rfft(fr, 1 << int(np.ceil(np.log2(2 * n))))) ** 2,
                           1 << int(np.ceil(np.log2(2 * n))))[:n]
        if acf[0] <= 0:
            continue
        r_ = acf / acf[0]
        lo, hi = int(sr / 600.0), int(sr / 80.0)
        hi = min(hi, n - 2)
        if hi <= lo:
            continue
        rm = float(np.max(r_[lo:hi]))
        rm = min(max(rm, 1e-4), 0.999)
        hnrs.append(10 * math.log10(rm / (1 - rm)))
    return dict(hnr_db=round(float(np.median(hnrs)), 3) if hnrs else None,
                centroid_hz=round(float(np.median(cens)), 1) if cens else None,
                rms_db=round(float(20 * math.log10(np.mean(rmss) + 1e-12)), 3) if rmss else None)


results = {}
for abbr, levels in LEVELS.items():
    base_curve = next((c for c in part["curves"] if c["abbr"] == abbr), None)
    base_val = float(np.median(base_curve["ys"])) if base_curve else 0.0
    rows = []
    for lv in levels:
        ustx = build_variant(f"{abbr}_{lv}", abbr, lv)
        m = render_and_measure(ustx, f"{abbr}_{lv}")
        if m:
            m["level"] = lv
            rows.append(m)
            print(f"  {abbr}={lv}: {m}")
    if len(rows) >= 2:
        xs = np.array([r["level"] for r in rows], float)
        for key in ("hnr_db", "centroid_hz", "rms_db"):
            ys = np.array([r[key] for r in rows], float)
            if np.all(np.isfinite(ys)):
                k = float(np.polyfit(xs, ys, 1)[0])
                results.setdefault(abbr, {})[key + "_per_unit"] = round(k, 6)
    results.setdefault(abbr, {})["base_value"] = base_val
    results.setdefault(abbr, {})["rows"] = rows

out = dict(part_index=PART, window_s=[round(a, 3), round(b, 3)],
            purpose="逐参数单独改档，测渲染端敏感度（不同时改多个参数）",
            results=results)
(DESIGN / "param_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in results.items()},
                 ensure_ascii=False, indent=1))
