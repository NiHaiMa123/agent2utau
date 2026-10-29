from __future__ import annotations

import numpy as np


def note_core_window(note):
    a = float(note["abs_start_s"])
    b = a + float(note["dur_s"])
    dur = b - a
    guard_l = min(0.12, max(0.025, 0.20 * dur))
    guard_r = min(0.10, max(0.025, 0.18 * dur))
    c0, c1 = a + guard_l, b - guard_r
    if c1 <= c0:
        half = max(0.01, 0.20 * dur)
        mid = (a + b) / 2.0
        c0, c1 = mid - half, mid + half
    return max(a, c0), min(b, c1)


def _p90_abs(x):
    return float(np.percentile(np.abs(x), 90)) if len(x) else float("inf")


def fit_body_model(times, trend_cents, voiced, confidence, note,
                   min_confidence=5.0 / 6.0):
    t = np.asarray(times, dtype=float)
    y = np.asarray(trend_cents, dtype=float)
    v = np.asarray(voiced, dtype=bool)
    conf = np.asarray(confidence, dtype=float)
    c0, c1 = note_core_window(note)
    window = (t >= c0) & (t <= c1)
    valid = window & v & np.isfinite(y) & (conf >= min_confidence)
    expected = max(1, int(round((c1 - c0) / 0.01)) + 1)
    coverage = float(valid.sum() / expected)
    rec = {
        "reliable": False,
        "window_s": [round(c0, 3), round(c1, 3)],
        "n": int(valid.sum()),
        "coverage": round(coverage, 3),
    }
    if valid.sum() < 5 or coverage < 0.5:
        rec["reason"] = "insufficient_consensus_core"
        return rec

    tt = t[valid]
    rel = y[valid] - float(note["tone"]) * 100.0
    med = float(np.median(rel))
    mad = float(np.median(np.abs(rel - med)))
    rec.update({"raw_center_c": round(med, 1), "mad_c": round(mad, 1)})
    if abs(med) > 100.0 or mad > 60.0:
        rec["reason"] = "core_incompatible_with_written_note"
        return rec

    centre = float(np.clip(med, -50.0, 50.0))
    shifted = rel + (centre - med)
    const = np.full(len(tt), centre)
    const_err = _p90_abs(shifted - const)
    model = "constant"
    knots = [(float(tt[0]), centre), (float(tt[-1]), centre)]
    selected_err = const_err

    x0 = float(tt.mean())
    slope, intercept = np.polyfit(tt - x0, shifted, 1)
    linear_pred = intercept + slope * (tt - x0)
    linear_span = float(slope * (tt[-1] - tt[0]))
    linear_err = _p90_abs(shifted - linear_pred)
    linear_ok = (30.0 <= abs(linear_span) <= 120.0
                 and abs(slope) <= 300.0
                 and const_err - linear_err >= 8.0)
    if linear_ok:
        model = "linear"
        knots = [(float(tt[0]), float(linear_pred[0])),
                 (float(tt[-1]), float(linear_pred[-1]))]
        selected_err = linear_err

    edges = np.linspace(tt[0], tt[-1], 4)
    kt, ky = [], []
    for j in range(3):
        m = (tt >= edges[j]) & (tt <= edges[j + 1])
        if m.any():
            kt.append(float(np.median(tt[m])))
            ky.append(float(np.median(shifted[m])))
    if len(kt) == 3:
        d = np.diff(ky)
        monotonic = d[0] * d[1] >= 0
        three_pred = np.interp(tt, kt, ky)
        three_err = _p90_abs(shifted - three_pred)
        base_err = linear_err if linear_ok else const_err
        three_ok = (monotonic and max(abs(np.asarray(ky))) <= 100.0
                    and abs(ky[-1] - ky[0]) <= 150.0
                    and base_err - three_err >= 8.0)
        if three_ok:
            model = "three_knot"
            knots = list(zip(kt, ky))
            selected_err = three_err

    rec.update({
        "reliable": True,
        "model": model,
        "centre_c": round(centre, 1),
        "knots": [[round(x, 3), round(y0, 1)] for x, y0 in knots],
        "constant_p90_c": round(const_err, 1),
        "linear_p90_c": round(linear_err, 1),
        "selected_p90_c": round(selected_err, 1),
        "linear_slope_c_s": round(float(slope), 1),
        "linear_span_c": round(linear_span, 1),
    })
    return rec


def body_value(model, time_s):
    if not model.get("reliable"):
        return 0.0
    knots = model["knots"]
    xs = np.asarray([p[0] for p in knots], dtype=float)
    ys = np.asarray([p[1] for p in knots], dtype=float)
    return float(np.interp(float(time_s), xs, ys, left=ys[0], right=ys[-1]))


def structural_transition(prev_note, note, portamento=None):
    a = float(note["abs_start_s"])
    prev_end = float(prev_note["abs_start_s"] + prev_note["dur_s"])
    leap = int(note["tone"] - prev_note["tone"])
    gap = a - prev_end
    if leap == 0 or gap >= 0.08:
        return None

    dep, arr = a - 0.04, a
    norm = None
    arrival_offset = 0.0
    if portamento is not None:
        dep = float(portamento.start_s)
        arr = float(portamento.end_s)
        dep = max(prev_note["abs_start_s"], min(dep, a + note["dur_s"] - 0.02))
        arr = max(dep + 0.02, min(arr, a + note["dur_s"] - 0.01))
        norm = portamento.params.get("norm_traj")
        arrival_offset = float(portamento.params.get("arrival_offset_c", 0.0))

    start_y = -10.0 * leap
    end_y = arrival_offset / 10.0
    points = [{"x": int(round((dep - a) * 1000.0)),
               "y": int(round(start_y)), "shape": "io"}]
    if norm and len(norm) >= 3:
        mid_norm = float(np.interp(0.5, np.linspace(0.0, 1.0, len(norm)), norm))
        mid_t = (dep + arr) / 2.0
        mid_y = start_y + (end_y - start_y) * mid_norm
        points.append({"x": int(round((mid_t - a) * 1000.0)),
                       "y": int(round(mid_y)), "shape": "io"})
    points.append({"x": int(round((arr - a) * 1000.0)),
                   "y": int(round(end_y)), "shape": "io"})
    return {
        "pitch": {"data": points, "snap_first": True},
        "departure_s": dep,
        "arrival_s": arr,
        "source_supported": portamento is not None,
    }


def pitd_curve(knots, part_pos_tick, tick_ms):
    grouped = {}
    for knot in knots:
        tick = int(round(float(knot["time_s"]) * 1000.0 / tick_ms
                         - part_pos_tick))
        grouped.setdefault(tick, []).append(knot)
    xs, ys, audit = [], [], []
    for tick in sorted(grouped):
        group = grouped[tick]
        priority = max(int(k["priority"]) for k in group)
        owners = [k for k in group if int(k["priority"]) == priority]
        values = np.asarray([float(k["value_c"]) for k in owners])
        if values.max() - values.min() > 1.0:
            raise ValueError(f"conflicting PITD ownership at tick {tick}: {owners}")
        value = float(values.mean())
        xs.append(tick)
        ys.append(int(np.clip(round(value), -1150, 1150)))
        audit.append({"tick": tick, "value_c": round(value, 1),
                      "owner": owners[0]["owner"], "priority": priority})
    return {"abbr": "pitd", "xs": xs, "ys": ys}, audit
