"""年轮 v3：源观测与逐音符特征（共享模块）。

口径与既有约定一致：
  * 音高一律 FCPE∧RMVPE 双检测器一致（差 >120c 记 unknown），10ms 栅格，单位 cent。
  * 辅音静默处 F0 失锁不算字腹；字腹统计只用最长连续有声段。
  * 声学特征（HNR/亮度/RMS）在分离人声干声上按 40ms 帧测。

v3 与 v2 的差别：特征粒度从"句"降到"音符"，并新增原唱 F0 涟漪（颤音）的
频率/幅度/相位估计，供逐音符画线使用。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf

TICK_S = 60.0 / (120.0 * 480)
RIPPLE_BAND = (3.0, 8.5)      # 原唱颤音搜索带（Hz）
RIPPLE_MIN_AMP = 12.0         # 小于该幅度不当作颤音（cent）


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


class Source:
    """源观测：双检测器 F0 + 干声波形。"""

    def __init__(self, run: Path):
        self.run = Path(run)
        obs = self.run / "observation"
        zf = np.load(obs / "fcpe.npz")
        zr = np.load(obs / "rmvpe.npz")
        self.t = zf["times"].astype(float)
        f0f = zf["f0_hz"].astype(float)
        f0r = zr["f0_hz"].astype(float)
        self.dt = float(np.mean(np.diff(self.t))) if len(self.t) > 1 else 0.01
        cf = np.where(f0f > 0, 6900.0 + 1200.0 * np.log2(np.maximum(f0f, 1e-6) / 440.0), np.nan)
        cr = np.where(f0r > 0, 6900.0 + 1200.0 * np.log2(np.maximum(f0r, 1e-6) / 440.0), np.nan)
        rf = np.interp(self.t, self.t, cf)
        rr = np.interp(self.t, zr["times"].astype(float), cr)
        self.agree = np.isfinite(rf) & np.isfinite(rr) & (np.abs(rf - rr) <= 120)
        self.c = np.where(self.agree, (rf + rr) / 2.0, np.nan)
        self.f0_hz = np.where(self.agree, 440.0 * 2 ** ((self.c - 6900.0) / 1200.0), np.nan)
        stem, self.sr = sf.read(str(obs / "stems" / "source_(vocals)_vocals_mel_band_roformer.wav"),
                                dtype="float32")
        if stem.ndim > 1:
            stem = stem.mean(axis=1)
        self.stem = stem
        # 20ms 帧 RMS（dB），用于帧级能量曲线
        self.frame = int(self.sr * 0.02)
        nfr = len(self.stem) // self.frame
        rms = np.sqrt((self.stem[: nfr * self.frame].reshape(nfr, self.frame) ** 2).mean(axis=1)) + 1e-12
        self.rms_db_frames = 20 * np.log10(rms)
        self.t_rms = (np.arange(nfr) + 0.5) * 0.02

    # ---------- 音高 ----------

    def track(self, a, b):
        """窗口内双检测器一致的 F0 迹线（时间, cents）。"""
        m = (self.t >= a) & (self.t < b) & self.agree
        if m.sum() < 3:
            return None
        return self.t[m], self.c[m]

    def level_at(self, t):
        """任意时刻的一致 F0（线性插值，无声处 NaN）。"""
        good = np.isfinite(self.c)
        if good.sum() < 3:
            return np.nan
        return float(np.interp(t, self.t[good], self.c[good]))

    def runs(self, a, b, gap=0.06, min_len=2):
        """窗口内连续有声段（索引区间）。"""
        tr = self.track(a, b)
        if tr is None:
            return []
        tt = tr[0]
        out, s0 = [], 0
        for j in range(1, len(tt) + 1):
            if j == len(tt) or tt[j] - tt[j - 1] > gap:
                if j - s0 >= min_len:
                    out.append((s0, j))
                s0 = j
        return out

    def core(self, a, b):
        """最长连续有声段（中位/跨度/帧数）。"""
        tr = self.track(a, b)
        if tr is None:
            return None
        tt, vv = tr
        rs = self.runs(a, b)
        if not rs:
            return None
        i0, i1 = max(rs, key=lambda r: r[1] - r[0])
        return dict(level=float(np.median(vv[i0:i1])),
                    span=float(vv[i0:i1].max() - vv[i0:i1].min()),
                    frames=int(i1 - i0),
                    t=tt[i0:i1], v=vv[i0:i1],
                    full_span=float(vv.max() - vv.min()))

    # ---------- 声学 ----------

    def hnr_db(self, a, b):
        """帧级归一自相关 HNR（dB）与谐波占比中位数。"""
        i0, i1 = int(a * self.sr), int(b * self.sr)
        seg = self.stem[i0:i1]
        n = int(self.sr * 0.04)
        if len(seg) < n * 2:
            return None
        hop = int(self.sr * 0.01)
        vals, harms = [], []
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
            f0 = self.level_at((i0 + s + n / 2) / self.sr)
            if not np.isfinite(f0):
                continue
            lag = self.sr / (440.0 * 2 ** ((f0 - 6900.0) / 1200.0))
            lo = max(2, int(lag * 0.75))
            hi = min(n - 2, int(lag * 1.30) + 2)
            if hi <= lo:
                continue
            rmax = float(np.max(r[lo:hi]))
            rmax = min(max(rmax, 1e-4), 0.999)
            vals.append(10 * math.log10(rmax / (1 - rmax)))
            harms.append(rmax)
        if not vals:
            return None
        return dict(hnr_db=float(np.median(vals)), harmonic_ratio=float(np.median(harms)),
                    frames=len(vals))

    def centroid(self, a, b):
        """谱重心（Hz）与高频能量比（>4kHz / 总）。"""
        i0, i1 = int(a * self.sr), int(b * self.sr)
        seg = self.stem[i0:i1]
        n = int(self.sr * 0.04)
        if len(seg) < n * 2:
            return None
        hop = int(self.sr * 0.01)
        cens, hfs = [], []
        win = np.hanning(n)
        for s in range(0, len(seg) - n, hop):
            fr = seg[s:s + n] * win
            if np.sqrt((fr ** 2).mean()) < 1e-4:
                continue
            sp = np.abs(np.fft.rfft(fr))
            fq = np.fft.rfftfreq(n, 1.0 / self.sr)
            tot = sp.sum() + 1e-12
            cens.append(float((sp * fq).sum() / tot))
            hfs.append(float(sp[fq > 4000].sum() / tot))
        if not cens:
            return None
        return dict(centroid_hz=float(np.median(cens)), hf_ratio=float(np.median(hfs)),
                    frames=len(cens))

    def rms_db(self, a, b):
        i0, i1 = int(a * self.sr), int(b * self.sr)
        seg = self.stem[i0:i1]
        if len(seg) < 100:
            return None
        return float(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12))

    # ---------- 原唱涟漪（颤音） ----------

    def ripple(self, a, b, level=None):
        """去趋势后残差里的主周期（Hz）、幅度（cent）与相位（rad，相对 a）。

        用最小二乘拟合 A·sin(2πf(t-a)+φ)，在 3.0-8.5Hz 内逐 0.05Hz 扫描取幅度最大者。
        """
        tr = self.track(a, b)
        if tr is None:
            return None
        tt, vv = tr
        if len(tt) < 12:
            return None
        x = tt - tt.mean()
        trend = np.polyval(np.polyfit(x, vv, 2), x)
        res = vv - trend
        if res.std() < 3.0:
            return None
        best = None
        for f in np.arange(RIPPLE_BAND[0], RIPPLE_BAND[1] + 1e-9, 0.05):
            w = 2 * np.pi * f * (tt - a)
            cm = np.cos(w).mean()
            sm = np.sin(w).mean()
            cc = float(((np.cos(w) - cm) * (res - res.mean())).sum() / len(res))
            ss = float(((np.sin(w) - sm) * (res - res.mean())).sum() / len(res))
            amp = math.hypot(cc, ss)
            if best is None or amp > best["amp"]:
                best = dict(freq=float(f), amp=amp, phase=float(math.atan2(ss, cc) - math.pi / 2))
        if best is None or best["amp"] < RIPPLE_MIN_AMP:
            return None
        return best

    # ---------- 音素边界的源侧依据 ----------

    def onset_offset(self, a, b):
        """用短时能量找字内"辅音->元音"过渡点（能量上升越过中位阈值的时刻）。"""
        i0, i1 = int(a * self.sr), int(b * self.sr)
        if i1 - i0 < 200:
            return None
        db = self.rms_db_frames
        t0 = i0 / self.sr
        idx = np.where((self.t_rms >= t0) & (self.t_rms <= i1 / self.sr))[0]
        if len(idx) < 4:
            return None
        seg = db[idx]
        med = float(np.median(seg))
        hi = idx[seg >= med + 2.0]
        if len(hi) == 0:
            return None
        return float(self.t_rms[hi[0]])


def smooth_series(x, sigma_frames=6.0):
    """高斯平滑（时间轴等距）。"""
    if len(x) < 3:
        return np.asarray(x, float)
    rad = max(1, int(3 * sigma_frames))
    k = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sigma_frames) ** 2)
    k /= k.sum()
    return np.convolve(np.asarray(x, float), k, mode="same")


def local_detrend(v, half=12):
    """局部线性去趋势（滑动最小二乘），把旋律趋势去掉、只留快速起伏。"""
    v = np.asarray(v, float)
    n = len(v)
    out = np.empty_like(v)
    x = np.arange(-half, half + 1, dtype=float)
    sxx = (x ** 2).sum()
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        xs = np.arange(lo, hi, dtype=float) - i
        ys = v[lo:hi]
        if len(ys) < 4:
            out[i] = 0.0
            continue
        sx = xs.sum()
        sxy = float((xs * ys).sum())
        sy = float(ys.sum())
        slope = (len(ys) * sxy - sx * sy) / (len(ys) * sxx - sx * sx)
        inter = (sy - slope * sx) / len(ys)
        out[i] = v[i] - (slope * 0.0 + inter)
    return out


def clean_frames(tt, vv, jump=120.0):
    """去掉孤立单帧尖刺（与前后两帧都相差超过 jump，无论方向）。

    连续滑音的中间点会因此被去掉——补齐后仍是同一条直线，不损失信息。
    """
    tt = np.asarray(tt, float)
    vv = np.asarray(vv, float)
    keep = []
    n = len(tt)
    for i in range(n):
        if 0 < i < n - 1:
            d1 = vv[i] - vv[i - 1]
            d2 = vv[i + 1] - vv[i]
            if abs(d1) > jump and abs(d2) > jump:
                continue
        keep.append(i)
    return tt[keep], vv[keep]


def filled_track(src, a, b, step=0.01):
    """把窗口内的一致 F0 帧去尖刺后线性补齐成均匀栅格。

    双检测器分歧处会出现空档（例如快速滑音时两个检测器打架）。若直接丢掉这些空档，
    中值滤波会把滑音端点当成尖刺抹平；按线性滑音补齐才能保住原唱的走音。
    返回 (grid, values, info)；info 记录帧数与最长缺口。
    """
    tr = src.track(a, b)
    if tr is None:
        return None
    tt, vv = clean_frames(*tr)
    if len(tt) < 2:
        return None
    grid = np.arange(a, b, step)
    if len(grid) < 2:
        return None
    vals = np.interp(grid, tt, vv)
    gaps = np.diff(tt)
    info = dict(frames=int(len(tt)),
                max_gap_s=float(gaps.max()) if len(gaps) else 0.0,
                gaps_over_60ms=int((gaps > 0.06).sum()) if len(gaps) else 0)
    return grid, vals, info
