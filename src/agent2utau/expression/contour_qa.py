"""Contour-shape QA (plan §9.11/§15.2-15.4, R2.1-J).

All metrics are same-time on the shared project grid; source and render
are cents arrays already sampled onto a common grid (nan = invalid).

R2.1-J contract:
- every metric honours a voiced-segment-local / event-local mask;
- nothing interpolates across unvoiced or artifact gaps;
- turning-point comparison reports count/type/relative timing/
  prominence/ordering separately;
- modulation is computed inside event windows (rate/depth/bandwidth/
  periodicity), not as one dominant FFT bin over the whole phrase;
- every report carries valid-frame coverage and artifact exclusion.
"""

from __future__ import annotations

import numpy as np

HOP_S = 0.010


def _seg_runs(mask):
    """Contiguous True runs of `mask` -> [(lo, hi)) index spans."""
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    breaks = np.where(np.diff(idx) > 1)[0]
    lo = np.concatenate([[0], breaks + 1])
    hi = np.concatenate([breaks + 1, [len(idx)]])
    return [(int(idx[a]), int(idx[b - 1]) + 1) for a, b in zip(lo, hi)]


def _fill_runs(y, mask):
    """Interpolate interior holes inside each valid run only."""
    out = y.copy()
    for lo, hi in _seg_runs(mask):
        seg = y[lo:hi]
        ok = ~np.isnan(seg)
        if ok.sum() >= 2:
            seg[~ok] = np.interp(np.flatnonzero(~ok),
                                 np.flatnonzero(ok), seg[ok])
        out[lo:hi] = seg
    return out


def _smooth_runs(y, mask, ms):
    """Moving-average smoothing inside contiguous valid runs only."""
    out = np.full(len(y), np.nan)
    k = max(1, int(round(ms / 1000.0 / HOP_S)))
    for lo, hi in _seg_runs(mask & ~np.isnan(y)):
        seg = np.asarray(y[lo:hi], dtype=float)
        if k <= 1 or len(seg) < 3:
            out[lo:hi] = seg
            continue
        kk = min(k, len(seg))
        if kk % 2 == 0:
            kk = max(1, kk - 1)
        if kk <= 1:
            out[lo:hi] = seg
            continue
        pad = kk // 2
        padded = np.pad(seg, (pad, pad), mode="edge")
        out[lo:hi] = np.convolve(padded, np.ones(kk) / kk,
                                 mode="valid")
    return out


def _coverage(source, render, mask):
    valid = mask & ~np.isnan(source) & ~np.isnan(render)
    return {"valid_frames": int(valid.sum()),
            "coverage": round(float(valid.sum() / max(mask.sum(), 1)), 3)}


def contour_position_metrics(source, render, mask):
    m = mask & ~np.isnan(source) & ~np.isnan(render)
    d = np.abs(render - source)[m]
    out = _coverage(source, render, mask)
    if not len(d):
        out.update({"n": 0})
        return out
    out.update({"n": int(len(d)),
                "med_c": round(float(np.median(d)), 1),
                "p90_c": round(float(np.percentile(d, 90)), 1),
                "p95_c": round(float(np.percentile(d, 95)), 1)})
    return out


def contour_slope_metrics(source, render, mask, smooth_ms=30):
    m = mask & ~np.isnan(source) & ~np.isnan(render)
    sf = _smooth_runs(source, m, smooth_ms)
    rf = _smooth_runs(render, m, smooth_ms)
    ds = np.diff(sf)
    dr = np.diff(rf)
    ok = m[:-1] & m[1:] & ~np.isnan(ds) & ~np.isnan(dr)
    e = np.abs(dr - ds)[ok]
    out = _coverage(source, render, mask)
    if not len(e):
        out.update({"n": 0})
        return out
    out.update({"n": int(len(e)),
                "med_c_per10ms": round(float(np.median(e)), 1),
                "p90_c_per10ms": round(float(np.percentile(e, 90)), 1)})
    return out


def contour_curvature_metrics(source, render, mask, smooth_ms=40):
    m = mask & ~np.isnan(source) & ~np.isnan(render)
    sf = _smooth_runs(source, m, smooth_ms)
    rf = _smooth_runs(render, m, smooth_ms)
    cs = np.diff(sf, 2)
    cr = np.diff(rf, 2)
    ok = m[:-2] & m[1:-1] & m[2:] & ~np.isnan(cs) & ~np.isnan(cr)
    e = np.abs(cr - cs)[ok]
    out = _coverage(source, render, mask)
    if not len(e):
        out.update({"n": 0})
        return out
    out.update({"n": int(len(e)),
                "med_c_per10ms2": round(float(np.median(e)), 1),
                "p90_c_per10ms2": round(float(np.percentile(e, 90)), 1)})
    return out


def _turning_list(y, mask, min_prominence_c=15.0):
    """[(idx, kind, value_c, prominence_c)] inside valid runs only —
    never across an unvoiced/artifact gap."""
    out = []
    for lo, hi in _seg_runs(mask & ~np.isnan(y)):
        seg = y[lo:hi]
        for i in range(1, len(seg) - 1):
            kind = None
            if seg[i] > seg[i - 1] and seg[i] >= seg[i + 1]:
                kind = "peak"
            elif seg[i] < seg[i - 1] and seg[i] <= seg[i + 1]:
                kind = "trough"
            if kind is None:
                continue
            ctx = np.concatenate([seg[max(0, i - 25):i],
                                  seg[i + 1:i + 26]])
            prom = abs(seg[i] - np.median(ctx)) if len(ctx) else 0.0
            if prom >= min_prominence_c:
                out.append((lo + i, kind, float(seg[i]), float(prom)))
    return out


def turning_point_metrics(source, render, mask=None, max_match_ms=80.0):
    """Topology QA per voiced segment.

    Reports matched/missing/extra turns with timing, prominence and
    amplitude errors, plus sequence edit distance — computed per segment
    so turns are never joined across a gap.
    """
    if mask is None:
        mask = ~np.isnan(source)
    sm = mask & ~np.isnan(source)
    rm = mask & ~np.isnan(render)
    ts = _turning_list(source, sm)
    tr = _turning_list(render, rm)
    used = set()
    matched, t_err, a_err, p_err = [], [], [], []
    for i_s, k_s, v_s, p_s in ts:
        best, bd = None, max_match_ms / 1000.0 / HOP_S
        for j, (i_r, k_r, v_r, p_r) in enumerate(tr):
            if j in used or k_r != k_s:
                continue
            if abs(i_r - i_s) < bd:
                best, bd = j, abs(i_r - i_s)
        if best is not None:
            used.add(best)
            matched.append((i_s, tr[best][0]))
            t_err.append(abs(i_s - tr[best][0]) * HOP_S * 1000)
            a_err.append(abs(v_s - tr[best][2]))
            p_err.append(abs(p_s - tr[best][3]))
    missing = len(ts) - len(matched)
    extra = len(tr) - len(used)
    seq_s = "".join("p" if k == "peak" else "v" for _, k, _, _ in ts)
    seq_r = "".join("p" if k == "peak" else "v" for _, k, _, _ in tr)
    out = {"matched_turns": len(matched), "missing_turns": missing,
           "extra_turns": extra,
           "source_turns": len(ts), "render_turns": len(tr),
           "turn_timing_err_ms_med": round(float(np.median(t_err)), 1)
           if t_err else None,
           "turn_amplitude_err_c_med": round(float(np.median(a_err)), 1)
           if a_err else None,
           "turn_prominence_err_c_med": round(float(np.median(p_err)), 1)
           if p_err else None,
           "sequence_edit_distance": int(_levenshtein(seq_s, seq_r))}
    out.update(_coverage(source, render, mask))
    return out


def _levenshtein(a, b):
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def modulation_metrics(source, render, mask=None, event_windows=None,
                       band_hz=(3.0, 12.0)):
    """Modulation QA inside event windows (or each voiced segment when no
    windows given): dominant rate, depth (p2p/2), bandwidth, periodicity.

    event_windows: iterable of (start_idx, end_idx) frame spans.
    """
    if mask is None:
        mask = ~np.isnan(source)
    spans = event_windows if event_windows is not None else \
        _seg_runs(mask)
    rows = []
    for (lo, hi) in spans:
        row = {"window_frames": [int(lo), int(hi)]}
        local_mask = mask[lo:hi]
        row["coverage"] = round(float(local_mask.sum() / max(hi - lo, 1)), 3)
        for tag, y in (("source", source), ("render", render)):
            seg = y[lo:hi]
            ok = local_mask & ~np.isnan(seg)
            runs = _seg_runs(ok)
            if not runs:
                row[tag] = None
                continue
            # Never bridge an artifact/unvoiced gap inside an event window.
            rlo, rhi = max(runs, key=lambda x: x[1] - x[0])
            if rhi - rlo < int(0.25 / HOP_S):
                row[tag] = None
                continue
            yy = np.asarray(seg[rlo:rhi], dtype=float)
            tr = _smooth_ms(yy, np.arange(len(seg)) * HOP_S, 250)
            r = yy - tr
            spec = np.abs(np.fft.rfft(r * np.hanning(len(r))))
            fr = np.fft.rfftfreq(len(r), HOP_S)
            band = (fr >= band_hz[0]) & (fr <= band_hz[1])
            if not band.any() or spec[band].max() <= 0:
                row[tag] = None
                continue
            i = int(np.argmax(spec[band]))
            # bandwidth at half power around the peak bin
            peak = spec[band][i]
            bidx = np.where(band)[0]
            above = bidx[spec[band] >= peak * 0.5]
            bw = float(fr[above[-1]] - fr[above[0]]) if len(above) else 0.0
            period = int(round(1.0 / fr[band][i] / HOP_S))
            ac = np.correlate(r - r.mean(), r - r.mean(), "full")
            ac = ac[len(ac) // 2:] / ac[len(ac) // 2]
            periodicity = float(ac[period]) if period < len(ac) else 0.0
            row[tag] = {
                "dom_rate_hz": round(float(fr[band][i]), 2),
                "depth_c": round(float(
                    (np.percentile(r, 95) - np.percentile(r, 5)) / 2.0), 1),
                "bandwidth_hz": round(bw, 2),
                "periodicity": round(periodicity, 3)}
        rows.append(row)
    return {"windows": rows}


def _smooth_ms(y, g, ms):
    k = max(1, int(round(ms / 1000.0 / HOP_S)))
    if k < 2:
        return y
    ker = np.ones(k) / k
    return np.convolve(y, ker, mode="same")


def vibrato_metrics(source_events, render_events):
    """Per matched vibrato event: rate/depth/start/end/phase/cv deltas."""
    out = []
    for se in source_events:
        if se.type != "vibrato":
            continue
        cand = [e for e in render_events if e.type == "vibrato"
                and set(e.note_indices) & set(se.note_indices)]
        if not cand:
            out.append({"note": se.note_indices[0], "state": "missing"})
            continue
        re_ = cand[0]
        d = {"note": se.note_indices[0], "state": "matched"}
        for k in ("rate_hz", "depth_c", "period_cv", "depth_cv",
                  "stable_cycle_count"):
            if k in se.params and k in re_.params:
                d[f"delta_{k}"] = round(se.params[k] - re_.params[k], 3)
        if "phase_rad" in se.params and "phase_rad" in re_.params:
            w = 2 * np.pi * se.params["rate_hz"]
            pa = se.params["phase_rad"] - w * se.params["phase_origin_s"]
            pb = re_.params["phase_rad"] - w * re_.params["phase_origin_s"]
            dp = (pa - pb) % (2 * np.pi)
            d["delta_phase_rad"] = round(min(dp, 2 * np.pi - dp), 3)
        d["delta_start_ms"] = round((se.start_s - re_.start_s) * 1000, 1)
        d["delta_end_ms"] = round((se.end_s - re_.end_s) * 1000, 1)
        out.append(d)
    return out


def _traj_profile(sig_times, sig_cents, s, e):
    m = (sig_times >= s) & (sig_times <= e) & ~np.isnan(sig_cents)
    if m.sum() < 4:
        return None
    t, c = sig_times[m], sig_cents[m]
    # normalized trajectory: 0..1 by time and by pitch span
    tn = (t - t[0]) / max(t[-1] - t[0], 1e-6)
    span = c[-1] - c[0]
    cn = (c - c[0]) / span if abs(span) > 1e-6 else np.zeros_like(c)
    slope = np.gradient(cn, tn)
    curv = np.gradient(slope, tn)
    return {"dur_ms": (t[-1] - t[0]) * 1000, "span_c": c[-1] - c[0],
            "slope_profile": slope, "curv_profile": curv, "cn": cn}


def portamento_metrics(source_events, render_events):
    """Per matched portamento: start/end/span/trajectory/slope/curvature."""
    out = []
    for se in source_events:
        if se.type != "portamento":
            continue
        cand = [e for e in render_events if e.type == "portamento"
                and e.params.get("from_note") == se.params.get("from_note")]
        if not cand:
            out.append({"from_note": se.params.get("from_note"),
                        "state": "missing"})
            continue
        re_ = cand[0]
        d = {"from_note": se.params["from_note"], "state": "matched",
             "traj_match": se.params["trajectory_type"]
             == re_.params["trajectory_type"],
             "delta_span_c": round(se.params["span_cents"]
                                   - re_.params["span_cents"], 1),
             "delta_start_ms": round((se.start_s - re_.start_s) * 1000, 1),
             "delta_end_ms": round((se.end_s - re_.end_s) * 1000, 1)}
        def _resample_profile(a, n=64):
            a = np.asarray(a, dtype=float)
            if len(a) < 2:
                return None
            x = np.linspace(0.0, 1.0, len(a))
            return np.interp(np.linspace(0.0, 1.0, n), x, a)

        sp, rp = se.params.get("slope_profile"), re_.params.get("slope_profile")
        if sp is not None and rp is not None:
            sa, ra = _resample_profile(sp), _resample_profile(rp)
            if sa is not None and ra is not None:
                d["slope_profile_rmse"] = round(float(np.sqrt(
                    np.mean((sa - ra) ** 2))), 3)
        cp, cr = se.params.get("curv_profile"), re_.params.get("curv_profile")
        if cp is not None and cr is not None:
            ca, cra = _resample_profile(cp), _resample_profile(cr)
            if ca is not None and cra is not None:
                d["curv_profile_rmse"] = round(float(np.sqrt(
                    np.mean((ca - cra) ** 2))), 3)
        out.append(d)
    return out
