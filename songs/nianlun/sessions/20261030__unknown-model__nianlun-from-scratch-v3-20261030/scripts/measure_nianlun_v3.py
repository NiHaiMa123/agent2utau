"""年轮 v3：渲染后与源逐音符数值对比（渲染 -> 测量 -> 回改的依据）。

比较口径与源侧一致：
  * 音高：FCPE 提取渲染人声的 F0，与源的双检测器一致迹线逐音符比中位/p90 偏差；
  * 能量：逐音符 RMS（dB）差；
  * 声色：逐音符 HNR（dB）与谱重心差。
本脚本只做测量，不做判断；自然度/听感仍为 unknown。
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scratch"))

from agent2utau.analysis.f0 import extract_f0
from nianlun_v3_source import Source, filled_track

V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
DESIGN = V3 / "design"
RENDER = V3 / "render"
SRC = Source(V3)

vocal = RENDER / "vocal_vocal.wav"
if not vocal.exists():
    vocal = RENDER / "vocal.wav"
print("measuring:", vocal)

f0 = extract_f0(str(vocal))
t_r = np.asarray(f0["times"], float)
hz_r = np.asarray(f0["f0_hz"], float)
c_r = np.where(hz_r > 0, 6900.0 + 1200.0 * np.log2(np.maximum(hz_r, 1e-6) / 440.0), np.nan)
np.savez_compressed(RENDER / "rendered_f0.npz", times=t_r, cents=c_r)
print("rendered F0 frames:", len(t_r))

aud, sr = sf.read(str(vocal), dtype="float32")
if aud.ndim > 1:
    aud = aud.mean(axis=1)


def rms_db(a, b):
    i0, i1 = int(a * sr), int(b * sr)
    seg = aud[i0:i1]
    if len(seg) < 200:
        return None
    return float(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12))


def hnr_db(a, b):
    i0, i1 = int(a * sr), int(b * sr)
    seg = aud[i0:i1]
    n = int(sr * 0.04)
    if len(seg) < n * 2:
        return None
    hop = int(sr * 0.01)
    vals = []
    for s in range(0, len(seg) - n, hop):
        fr = seg[s:s + n]
        if np.sqrt((fr ** 2).mean()) < 1e-4:
            continue
        m = 1 << int(np.ceil(np.log2(2 * n)))
        sp = np.fft.rfft(fr, m)
        acf = np.fft.irfft(np.abs(sp) ** 2, m)[:n]
        if acf[0] <= 0:
            continue
        r = acf / acf[0]
        f0v = np.interp((i0 + s + n / 2) / sr, t_r, c_r, left=np.nan, right=np.nan)
        if not np.isfinite(f0v):
            continue
        lag = sr / (440.0 * 2 ** ((f0v - 6900.0) / 1200.0))
        lo = max(2, int(lag * 0.75))
        hi = min(n - 2, int(lag * 1.30) + 2)
        if hi <= lo:
            continue
        rmax = float(np.max(r[lo:hi]))
        rmax = min(max(rmax, 1e-4), 0.999)
        vals.append(10 * math.log10(rmax / (1 - rmax)))
    return float(np.median(vals)) if vals else None


def centroid(a, b):
    i0, i1 = int(a * sr), int(b * sr)
    seg = aud[i0:i1]
    n = int(sr * 0.04)
    if len(seg) < n * 2:
        return None
    hop = int(sr * 0.01)
    win = np.hanning(n)
    cens = []
    for s in range(0, len(seg) - n, hop):
        fr = seg[s:s + n] * win
        if np.sqrt((fr ** 2).mean()) < 1e-4:
            continue
        sp = np.abs(np.fft.rfft(fr))
        fq = np.fft.rfftfreq(n, 1.0 / sr)
        cens.append(float((sp * fq).sum() / (sp.sum() + 1e-12)))
    return float(np.median(cens)) if cens else None


feat = json.loads((DESIGN / "note_features.json").read_text(encoding="utf-8"))["notes"]
rows = []
for f in feat:
    a, b = f["start"], f["end"]
    tr = SRC.track(a, b)
    src_ft = filled_track(SRC, a, b)
    src_vals = src_ft[1] if src_ft else None
    # 渲染侧同窗
    m = (t_r >= a) & (t_r < b) & np.isfinite(c_r)
    if m.sum() >= 3:
        got = np.interp(t_r[m], t_r[m], c_r[m])
        ref = np.interp(t_r[m], t_r[m], np.interp(t_r[m], src_ft[0], src_ft[1])) if src_ft else None
    else:
        got, ref = None, None
    row = dict(part_index=f["part_index"], note_index=f["note_index"], lyric=f["lyric"],
               start=a, end=b, dur=f["dur"])
    if got is not None and ref is not None:
        d = got - ref
        row["f0_median_err_c"] = float(np.median(d))
        row["f0_abs_median_c"] = float(np.median(np.abs(d)))
        row["f0_abs_p90_c"] = float(np.percentile(np.abs(d), 90))
        row["f0_frames"] = int(m.sum())
    r_rms = rms_db(a, b)
    s_rms = f["rms_db"]
    if r_rms is not None and s_rms is not None:
        row["rms_render_db"] = round(r_rms, 2)
        row["rms_src_db"] = s_rms
        row["rms_diff_db"] = round(r_rms - s_rms, 2)
    r_h = hnr_db(a, b)
    if r_h is not None and f["hnr_db"] is not None:
        row["hnr_render_db"] = round(r_h, 2)
        row["hnr_src_db"] = f["hnr_db"]
        row["hnr_diff_db"] = round(r_h - f["hnr_db"], 2)
    r_c = centroid(a, b)
    if r_c is not None and f["centroid_hz"] is not None:
        row["centroid_render_hz"] = round(r_c, 1)
        row["centroid_src_hz"] = f["centroid_hz"]
    rows.append(row)

(RENDER / "measurements.json").write_text(json.dumps(dict(notes=rows), ensure_ascii=False, indent=1),
                                           encoding="utf-8")
absmed = [r["f0_abs_median_c"] for r in rows if "f0_abs_median_c" in r]
absp90 = [r["f0_abs_p90_c"] for r in rows if "f0_abs_p90_c" in r]
rmsd = [r["rms_diff_db"] for r in rows if "rms_diff_db" in r]
hnrd = [r["hnr_diff_db"] for r in rows if "hnr_diff_db" in r]
print("notes measured:", len(rows))
if absmed:
    print("F0 |err| median per note: median %.1fc  p90 %.1fc" %
          (np.median(absmed), np.percentile(absmed, 90)))
    print("F0 |err| p90 per note:    median %.1fc" % np.median(absp90))
if rmsd:
    print("RMS diff: median %.2f dB  (p10 %.2f p90 %.2f)" %
          (np.median(rmsd), np.percentile(rmsd, 10), np.percentile(rmsd, 90)))
if hnrd:
    print("HNR diff: median %.2f dB" % np.median(hnrd))
print("measurements written")
