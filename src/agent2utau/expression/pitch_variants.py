"""PITD candidate generators for the phrase A/B/C/D experiment (plan.md §18).

All generators return {'abbr':'pitd','xs':[part-relative ticks],
'ys':[cents]} for ONE phrase part, plus an audit dict.

Time convention: audio_ms == project_tick * TICK_MS (wave part anchored at
project 0, verified on 年轮/花海). part-relative tick = abs_tick - part_pos.

Variants:
  A  legacy absolute-F0 transcription (analysis.pitchcurve)
  B  Expressive-style global FastDTW alignment + residual, spline smoothing
  C  residual per-note anchor alignment + bounded lag + RDP simplification
  D  neutral (no pitd) — handled by caller
"""

from __future__ import annotations

import numpy as np

from agent2utau.analysis.pitchcurve import build_pitd as build_pitd_A

TICK_MS = 60.0 / 120.0 / 480.0 * 1000.0  # 1.0417 ms/tick @120bpm


def _f0_midi(f0: dict):
    from agent2utau.analysis.f0 import hz_to_midi
    return np.asarray(f0["times"]), hz_to_midi(np.asarray(f0["f0_hz"])), \
        np.asarray(f0["voiced"], dtype=bool)


def _frame_grid(t0_s, t1_s, hop_s=0.010):
    n = int(round((t1_s - t0_s) / hop_s))
    return t0_s + np.arange(n + 1) * hop_s


def _sample_series(grid_s, times_s, vals, voiced):
    """Linear-interp vals onto grid; nan where source unvoiced / outside."""
    out = np.interp(grid_s, times_s, vals, left=np.nan, right=np.nan)
    ok = np.interp(grid_s, times_s, voiced.astype(float), left=0, right=0) > 0.5
    out[~ok] = np.nan
    return out


def _rdp(t, y, eps):
    """Ramer-Douglas-Peucker on (t,y); returns kept index mask."""
    keep = np.zeros(len(t), dtype=bool)
    keep[0] = keep[-1] = True

    def rec(i0, i1):
        if i1 - i0 < 2:
            return
        x0, y0, x1, y1 = t[i0], y[i0], t[i1], y[i1]
        den = np.hypot(y1 - y0, x1 - x0)
        if den == 0:
            d = np.abs(y[i0 + 1:i1] - y0)
        else:
            d = np.abs((y1 - y0) * t[i0 + 1:i1] - (x1 - x0) * y[i0 + 1:i1]
                       + x1 * y0 - y1 * x0) / den
        k = int(np.argmax(d)) + i0 + 1
        if d[k - i0 - 1] > eps:
            keep[k] = True
            rec(i0, k)
            rec(k, i1)

    rec(0, len(t) - 1)
    return keep


def _series_to_pitd(part_pos_tick, xs_abs_s, ys_c):
    xs = np.round(xs_abs_s * 1000.0 / TICK_MS - part_pos_tick).astype(int)
    ys = np.clip(np.round(ys_c), -1150, 1150).astype(int)
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]
    keep = np.concatenate([[True], np.diff(xs) > 0])
    return {"abbr": "pitd", "xs": xs[keep].tolist(), "ys": ys[keep].tolist()}


# ---------------------------------------------------------------- A
def variant_A(ref_f0, phrase_notes, part_pos_tick):
    """Legacy: absolute F0 vs written tone, ~20pts/s, clamp ±600c."""
    notes = [{"start": n["abs_start_s"], "dur": n["dur_s"], "tone": n["tone"]}
             for n in phrase_notes]
    part_start_s = part_pos_tick * TICK_MS / 1000.0
    pitd = build_pitd_A(ref_f0, notes, part_start_s,
                        sec_to_tick=lambda s: s * 1000.0 / TICK_MS)
    if pitd is not None:
        xs = np.round(np.asarray(pitd["xs"], dtype=float)).astype(int)
        keep = np.concatenate([[True], np.diff(xs) > 0])
        pitd["xs"] = xs[keep].tolist()
        pitd["ys"] = np.asarray(pitd["ys"], dtype=float)[keep]
        pitd["ys"] = np.round(pitd["ys"]).astype(int).tolist()
    return pitd, {"variant": "A"}


# ---------------------------------------------------------------- B
def variant_B(ref_f0, neu_f0, ref_wav, neu_wav, phrase_notes,
              part_pos_tick, win_s):
    """Expressive-style: global FastDTW of multi-features, then residual."""
    from fastdtw import fastdtw
    from scipy.interpolate import interp1d
    from scipy.ndimage import gaussian_filter1d
    from scipy.stats import zscore
    import librosa, soundfile as sf

    hop = 0.010
    grid = _frame_grid(win_s[0], win_s[1], hop)

    def feats(wav_path, f0):
        wav, sr = sf.read(wav_path, dtype="float32")
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        if sr != 16000:
            wav = librosa.resample(wav, orig_sr=sr, target_sr=16000)
        i0, i1 = int(win_s[0] * 16000), int(win_s[1] * 16000)
        seg = wav[i0:i1]
        n = len(grid)

        def fixlen(a):
            a = np.asarray(a, dtype=float)
            if len(a) >= n:
                return a[:n]
            return np.pad(a, (0, n - len(a)), mode="edge")

        rms = fixlen(librosa.feature.rms(
            y=seg, frame_length=400, hop_length=160, center=False)[0])
        mfcc = librosa.feature.mfcc(y=seg, sr=16000, n_mfcc=6,
                                    n_fft=400, hop_length=160,
                                    center=False)
        mfcc = np.vstack([fixlen(mfcc[i]) for i in range(6)])
        t, m, v = _f0_midi(f0)
        pitch = _sample_series(grid, t, m, v)
        # zero-center each feature over the window (DTW wants comparable
        # shapes; voiced gating happens later on pitch itself)
        def zc(a):
            a = np.asarray(a, dtype=float)
            a = np.nan_to_num(a, nan=np.nanmedian(a))
            return zscore(a) if np.std(a) > 1e-9 else a * 0.0
        cols = [zc(pitch), zc(rms)] + [zc(mfcc[i]) for i in range(mfcc.shape[0])]
        return np.vstack(cols).T, pitch

    ref_feats, ref_pitch = feats(ref_wav, ref_f0)
    neu_feats, neu_pitch = feats(neu_wav, neu_f0)
    _, path = fastdtw(list(map(tuple, ref_feats)),
                      list(map(tuple, neu_feats)), radius=1)
    path = np.asarray(path)
    # ref→neu warp curve; for each neu index collect ref pitch (median)
    warp = interp1d(path[:, 1], path[:, 0], kind="nearest",
                    bounds_error=False, fill_value=(path[0, 0], path[-1, 0]))
    ref_idx = np.clip(np.round(warp(np.arange(len(neu_feats)))).astype(int),
                      0, len(ref_pitch) - 1)
    ref_on_neu = ref_pitch[ref_idx]
    both = ~np.isnan(ref_on_neu) & ~np.isnan(neu_pitch)
    delta = np.full(len(neu_pitch), np.nan)
    delta[both] = (ref_on_neu[both] - neu_pitch[both]) * 100.0

    # smoothing: gauss sigma=2 frames, then light spline (their pipeline)
    filled = delta.copy()
    ok = ~np.isnan(filled)
    if ok.sum() > 8:
        filled = np.interp(grid[:len(filled)], grid[:len(filled)][ok],
                           filled[ok])
        smooth = gaussian_filter1d(filled, sigma=2.0)
        smooth[~ok] = np.nan
    else:
        smooth = delta

    t, ys = grid[:len(smooth)], np.clip(smooth, -800, 800)
    keep = ~np.isnan(ys)
    pitd = _series_to_pitd(part_pos_tick, t[keep], ys[keep])
    return pitd, {"variant": "B", "dtw_pairs": int(len(path)),
                  "voiced_frac": float(both.mean())}


# ---------------------------------------------------------------- C
def _build_anchor_warp(phrase_notes, char_nucleus):
    """Piecewise-linear map written-time -> ref-time from HFA anchors.

    Anchors: (note_start -> char w0) and (written nucleus -> ref nucleus)
    for every lyric-matched note; slope-1 extension outside the anchor
    range keeps the map monotonic and bounded.
    """
    pairs, ci = [], 0
    for n in phrase_notes:
        if ci < len(char_nucleus) and n["lyric"] == char_nucleus[ci]["char"]:
            c = char_nucleus[ci]
            ci += 1
            s, d = n["abs_start_s"], n["dur_s"]
            span = max(c["w1"] - c["w0"], 1e-3)
            r = min(max((c["nuc"] - c["w0"]) / span, 0.0), 1.0)
            pairs.append((s, c["w0"]))
            pairs.append((s + r * d, c["nuc"]))
    if len(pairs) < 2:
        return None
    wt = np.asarray([p[0] for p in pairs])
    rt = np.asarray([p[1] for p in pairs])
    off0, off1 = rt[0] - wt[0], rt[-1] - wt[-1]

    def warp(t):
        t = np.asarray(t, dtype=float)
        y = np.interp(t, wt, rt)
        y = np.where(t < wt[0], t + off0, y)
        y = np.where(t > wt[-1], t + off1, y)
        return y

    warp.pairs = pairs
    return warp


def variant_C(ref_f0, neu_f0, phrase_notes, part_pos_tick,
              eps_c=8.0, max_lag_frames=4, min_cov=0.30,
              lag_mode="anchor", char_nucleus=None):
    """Residual PITD: anchor alignment + bounded lag + RDP simplification.

    lag_mode 'global': one robust lag for the whole phrase (ref→neutral),
    estimated over all both-voiced frames — per-note lag proved unstable.
    """
    rt, rm, rv = _f0_midi(ref_f0)
    nt, nm, nv = _f0_midi(neu_f0)
    xs_all, ys_all, audit = [], [], []

    # global lag: seconds, ref sampled at t+lag to match neutral at t
    lag_s = 0.0
    warp = None
    if lag_mode == "anchor":
        warp = _build_anchor_warp(phrase_notes, char_nucleus or [])
        if warp is None:
            lag_mode = "global"
    elif lag_mode == "global":
        best = (0.0, np.inf)
        for lag in np.arange(-0.10, 0.101, 0.010):
            errs = []
            for n in phrase_notes:
                s = n["abs_start_s"]
                e = s + n["dur_s"]
                g = _frame_grid(s, e)
                r = _sample_series(g + lag, rt, rm, rv)
                u = _sample_series(g, nt, nm, nv)
                b = ~np.isnan(r) & ~np.isnan(u)
                if b.sum() > 4:
                    errs.append(np.abs((r - u)[b]))
            if errs:
                err = float(np.median(np.concatenate(errs)))
                if err < best[1]:
                    best = (float(lag), err)
        lag_s = best[0]

    EDGE_IN, EDGE_OUT, TAPER = 0.090, 0.040, 0.040
    for n in phrase_notes:
        s, e = n["abs_start_s"], n["abs_start_s"] + n["dur_s"]
        g = _frame_grid(s, e)
        ref_t = warp(g) if warp is not None else g + lag_s
        r = _sample_series(ref_t, rt, rm, rv)
        u = _sample_series(g, nt, nm, nv)
        both = ~np.isnan(r) & ~np.isnan(u)
        cov = both.mean()
        if cov < min_cov:
            audit.append({"lyric": n["lyric"], "state": "low_coverage",
                          "cov": round(float(cov), 2)})
            continue
        best_lag = 0
        if lag_mode == "note":
            best_lag, best_err = 0, np.inf
            for lag in range(-max_lag_frames, max_lag_frames + 1):
                rr = _sample_series(g + lag * 0.010, rt, rm, rv)
                b = ~np.isnan(rr) & ~np.isnan(u)
                if b.sum() < 4:
                    continue
                err = np.nanmedian(np.abs((rr - u)[b])) * 100.0
                if err < best_err:
                    best_err, best_lag = err, lag
            r = _sample_series(g + best_lag * 0.010, rt, rm, rv)
        resid = (r - u) * 100.0
        resid[~both] = np.nan
        # drop octave-conflict frames (>800c residual — extractor conflict)
        resid[np.abs(resid) > 800.0] = np.nan
        # body-only: residual is meaningless while neutral is mid-transition
        body = (g >= s + EDGE_IN) & (g <= e - EDGE_OUT)
        resid[~body] = np.nan
        ok = ~np.isnan(resid)
        xs_all.extend([s, e])
        ys_all.extend([0.0, 0.0])          # boundary anchors -> neutral
        if body.sum() < 8 or np.isnan(resid[body]).all():
            audit.append({"lyric": n["lyric"], "state": "short_or_unvoiced"})
            continue
        filled = np.interp(g, g[ok], resid[ok])
        filled[~ok] = np.nan
        # taper to 0 across TAPER at body edges so interior gestures survive
        # but the curve still reaches 0 at note boundaries
        bi = np.where(body)[0]
        b0, b1 = bi[0], bi[-1]
        for i in bi:
            dt = min(g[i] - g[b0], g[b1] - g[i])
            if dt < TAPER and not np.isnan(filled[i]):
                filled[i] *= max(dt, 0.0) / TAPER
        ok = ~np.isnan(filled)
        keep = _rdp(g[ok], filled[ok], eps_c)
        xs_all.extend(g[ok][keep])
        ys_all.extend(filled[ok][keep])
        if warp is not None:
            lag_ms = int(round((warp(np.array([s]))[0] - s) * 1000))
        elif lag_mode == "global":
            lag_ms = int(round(lag_s * 1000))
        else:
            lag_ms = int(best_lag * 10)
        audit.append({"lyric": n["lyric"], "state": "ok", "lag_ms": lag_ms,
                      "cov": round(float(cov), 2),
                      "pts": int(keep.sum()),
                      "resid_med_c": round(float(np.nanmedian(resid)), 1)})

    pitd = _series_to_pitd(part_pos_tick, np.asarray(xs_all),
                           np.asarray(ys_all))
    return pitd, {"variant": "C", "notes": audit}
