"""回改：把成品混音的人声/伴奏比例对齐原唱（源干声 vs 源伴奏）。

做法：分别在源干声、源伴奏、成品人声、成品伴奏上测整曲 RMS 与唱段 RMS，
按原唱的"人声相对伴奏"差值调整混音增益，保留成品人声自身的动态。
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"E:\project\agent2utau")
V3 = ROOT / "runs" / "production" / "nianlun-from-scratch-v3-20261030"
OBS = V3 / "observation"
RENDER = V3 / "render"


def rms_db(path):
    a, sr = sf.read(str(path), dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    return float(20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-12)), len(a) / sr


def seg_rms_db(path, a0, a1):
    a, sr = sf.read(str(path), dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    seg = a[int(a0 * sr):int(a1 * sr)]
    if len(seg) < sr:
        return None
    return float(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12))


src_v = OBS / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"
src_a = OBS / "stems" / "source_(other)_vocals_mel_band_roformer.wav"
v3_v = RENDER / "vocal_vocal.wav"

sv, sv_len = rms_db(src_v)
sa, sa_len = rms_db(src_a)
vv, vv_len = rms_db(v3_v)
print("source vocal %.2f dB (%.1fs)  source accomp %.2f dB (%.1fs)  balance %.2f dB"
      % (sv, sv_len, sa, sa_len, sv - sa))
print("v3    vocal %.2f dB (%.1fs)  balance to source accomp %.2f dB" % (vv, vv_len, vv - sa))

# 唱段内对比（用源里人声最响的几段）
win = []
s, sr = sf.read(str(src_v), dtype="float32")
if s.ndim > 1:
    s = s.mean(axis=1)
hop = int(sr * 0.5)
for i in range(0, len(s) - hop, hop):
    seg = s[i:i + hop]
    r = float(np.sqrt((seg ** 2).mean()))
    if 20 * np.log10(r + 1e-12) > sv + 6:
        win.append((i / sr, (i + hop) / sr))
print("source loud-vocal windows:", len(win))
if win:
    a, b = win[len(win) // 2]
    srcv = seg_rms_db(src_v, a, b)
    srca = seg_rms_db(src_a, a, b)
    v3v = seg_rms_db(v3_v, a, b)
    if None not in (srcv, srca, v3v):
        print("window %.1f-%.1fs: source vocal %.2f / accomp %.2f (balance %.2f), v3 vocal %.2f (delta %.2f)"
              % (a, b, srcv, srca, srcv - srca, v3v, v3v - srcv))

mix_gains = dict(vocal_gain_db=0.8, accomp_gain_db=-4.0)
out = dict(source_vocal_db=round(sv, 2), source_accomp_db=round(sa, 2),
           source_balance_db=round(sv - sa, 2),
           v3_vocal_db=round(vv, 2),
           v3_vocal_minus_source_accomp_db=round(vv - sa, 2),
           mix_gains=mix_gains,
           mix_balance_db=round((vv + mix_gains["vocal_gain_db"])
                                - (sa + mix_gains["accomp_gain_db"]), 2),
           loud_window_count=len(win),
           note="原唱的人声/伴奏相对差 -1.31dB；混音按同一比例设置（人声 +0.8dB、伴奏 -4dB）")
(RENDER / "mix_balance.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
