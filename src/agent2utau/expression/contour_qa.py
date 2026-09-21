"""Contour-shape QA (plan §9.11/§15.2-15.4).

All metrics are same-time on the shared project grid; source and render
are ContourSignal-like arrays already sampled onto a common grid.
"""

from __future__ import annotations

import numpy as np

HOP_S = 0.010


def _fill(y, g):
    ok = ~np.isnan(y)
    return np.interp(g, g[ok], y[ok]) if ok.sum() > 3 else y


def _smooth_ms(y, g, ms):
    k = max(1, int(round(ms / 1000.0 / HOP_S)))
    if k < 2:
        return y
    ker = np.ones(k) / k
    return np.convolve(y, ker, mode="same")


def contour_position_metrics(source, render, mask):
    d = np.abs(render - source)
    d = d[mask & ~np.isnan(d)]
    if not len(d):
        return {"n": 0}
    return {"n": int(len(d)),
            "med_c": round(float(np.median(d)), 1),
            "p90_c": round(float(np.percentile(d, 90)), 1),
            "p95_c": round(float(np.percentile(d, 95)), 1)}


def contour_slope_metrics(source, render, mask, smooth_ms=30):
    s = _smooth_ms(_fill(source, np.arange(len(source)) * HOP_S),
                   np.arange(len(source)) * HOP_S, smooth_ms)
    r = _smooth_ms(_fill(render, np.arange(len(render)) * HOP_S),
                   np.arange(len(render)) * HOP_S, smooth_ms)
    ds = np.diff(s)
    dr = np.diff(r)
    e = np.abs(dr - ds)[mask[:-1] & ~np.isnan(ds) & ~np.isnan(dr)]
    if not len(e):
        return {"n": 0}
    return {"n": int(len(e)),
            "med_c_per10ms": round(float(np.median(e)), 1),
            "p90_c_per10ms": round(float(np.percentile(e, 90)), 1)}


def contour_curvature_metrics(source, render, mask, smooth_ms=40):
    g = np.arange(len(source)) * HOP_S
    s = _smooth_ms(_fill(source, g), g, smooth_ms)
    r = _smooth_ms(_fill(render, g), g, smooth_ms)
    cs = np.diff(s, 2)
    cr = np.diff(r, 2)
    e = np.abs(cr - cs)[mask[:-2] & ~np.isnan(cs) & ~np.isnan(cr)]
    if not len(e):
        return {"n": 0}
    return {"n": int(len(e)),
            "med_c_per10ms2": round(float(np.median(e)), 1),
            "p90_c_per10ms2": round(float(np.percentile(e, 90)), 1)}


def _turning_list(y, min_prominence_c=15.0):
    """Return [(idx, kind, value_c)] with prominence filter."""
    idx = []
    for i in range(1, len(y) - 1):
        if y[i] > y[i - 1] and y[i] >= y[i + 1]:
            idx.append((i, "peak"))
        elif y[i] < y[i - 1] and y[i] <= y[i + 1]:
            idx.append((i, "trough"))
    out = []
    for i, k in idx:
        lo = max(0, i - 25)
        hi = min(len(y), i + 26)
        if hi > lo + 1:
            prom = abs(y[i] - np.median(np.concatenate([y[lo:i], y[i + 1:hi]])))
        else:
            prom = 0
        if prom >= min_prominence_c:
            out.append((i, k, float(y[i])))
    return out


def turning_point_metrics(source, render, event_windows=None,
                          max_match_ms=80.0):
    """Matched/missing/extra turns + timing/amplitude errors + edit dist."""
    g = np.arange(len(source)) * HOP_S
    S = _fill(source, g)
    R = _fill(render, g)
    ts = _turning_list(S)
    tr = _turning_list(R)
    used = set()
    matched, t_err, a_err = [], [], []
    for i_s, k_s, v_s in ts:
        best, bd = None, max_match_ms / 1000.0 / HOP_S
        for j, (i_r, k_r, v_r) in enumerate(tr):
            if j in used or k_r != k_s:
                continue
            if abs(i_r - i_s) < bd:
                best, bd = j, abs(i_r - i_s)
        if best is not None:
            used.add(best)
            matched.append((i_s, tr[best][0]))
            t_err.append(abs(i_s - tr[best][0]) * HOP_S * 1000)
            a_err.append(abs(v_s - tr[best][2]))
    missing = len(ts) - len(matched)
    extra = len(tr) - len(used)
    seq_s = "".join("p" if k == "peak" else "v" for _, k, _ in ts)
    seq_r = "".join("p" if k == "peak" else "v" for _, k, _ in tr)
    edit = _levenshtein(seq_s, seq_r)
    return {"matched_turns": len(matched), "missing_turns": missing,
            "extra_turns": extra,
            "turn_timing_err_ms_med": round(float(np.median(t_err)), 1)
            if t_err else None,
            "turn_amplitude_err_c_med": round(float(np.median(a_err)), 1)
            if a_err else None,
            "sequence_edit_distance": int(edit)}


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


def modulation_metrics(source, render, event_windows=None,
                       band_hz=(3.0, 12.0)):
    """Modulation spectrum comparison: dominant rate/depth per window."""
    g = np.arange(len(source)) * HOP_S
    out = {}
    for tag, y in (("source", source), ("render", render)):
        yy = _fill(y, g)
        tr = _smooth_ms(yy, g, 250)
        r = yy - tr
        spec = np.abs(np.fft.rfft(r * np.hanning(len(r))))
        fr = np.fft.rfftfreq(len(r), HOP_S)
        band = (fr >= band_hz[0]) & (fr <= band_hz[1])
        if band.any() and spec[band].max() > 0:
            i = int(np.argmax(spec[band]))
            out[tag] = {"dom_rate_hz": round(float(fr[band][i]), 2),
                        "band_power": round(float(spec[band].max()
                                                  / len(r)), 2)}
        else:
            out[tag] = None
    return out


def vibrato_metrics(source_events, render_events):
    """Per matched vibrato event: rate/depth/start/end/cv deltas."""
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
        for k in ("rate_hz", "depth_c", "period_cv", "depth_cv"):
            if k in se.params and k in re_.params:
                d[f"delta_{k}"] = round(se.params[k] - re_.params[k], 3)
        d["delta_start_ms"] = round((se.start_s - re_.start_s) * 1000, 1)
        d["delta_end_ms"] = round((se.end_s - re_.end_s) * 1000, 1)
        out.append(d)
    return out


def portamento_metrics(source_events, render_events):
    """Per matched portamento: trajectory/slope/curvature deltas."""
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
        out.append({"from_note": se.params["from_note"], "state": "matched",
                    "traj_match": se.params["trajectory_type"]
                    == re_.params["trajectory_type"],
                    "delta_span_c": round(se.params["span_cents"]
                                          - re_.params["span_cents"], 1)})
    return out
