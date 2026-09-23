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
        seg = y[lo:hi].copy()
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

    def _edge_confident(turns, m, k=2):
        """A local extremum needs >=k valid frames on each side to be a
        confirmed direction change.  An extremum within k-1 frames of a
        run boundary rests on one-sided evidence: whether the curve
        actually turns is hidden inside the unvoiced gap, so its counted
        visibility flips on sub-frame jitter of the minimum's position
        (observed on real renders: an identical dip counted as a turn at
        run-edge-1 but invisible at the edge frame).  Such boundary
        extrema are excluded from topology counts on BOTH sides, but are
        NOT silently dropped: they are returned separately for audit."""
        n = len(m)
        kept, excluded = [], []
        for t in turns:
            ok = (t[0] - k >= 0 and t[0] + k < n
                  and m[t[0] - k:t[0] + k + 1].all())
            (kept if ok else excluded).append(t)
        return kept, excluded

    ts, ts_uncertain = _edge_confident(_turning_list(source, sm), sm)
    tr, tr_uncertain = _edge_confident(_turning_list(render, rm), rm)
    used = set()
    matched_src = set()
    matched, t_err, a_err, p_err = [], [], [], []
    for s_idx, (i_s, k_s, v_s, p_s) in enumerate(ts):
        best, bd = None, max_match_ms / 1000.0 / HOP_S
        for j, (i_r, k_r, v_r, p_r) in enumerate(tr):
            if j in used or k_r != k_s:
                continue
            if abs(i_r - i_s) < bd:
                best, bd = j, abs(i_r - i_s)
        if best is not None:
            used.add(best)
            matched_src.add(s_idx)
            matched.append((i_s, tr[best][0]))
            t_err.append(abs(i_s - tr[best][0]) * HOP_S * 1000)
            a_err.append(abs(v_s - tr[best][2]))
            p_err.append(abs(p_s - tr[best][3]))
    missing_rows = [
        {"frame_idx": int(i), "kind": k, "value_c": round(v, 1),
         "prominence_c": round(p, 1)}
        for s_idx, (i, k, v, p) in enumerate(ts)
        if s_idx not in matched_src
    ]
    extra_rows = [
        {"frame_idx": int(i), "kind": k, "value_c": round(v, 1),
         "prominence_c": round(p, 1)}
        for r_idx, (i, k, v, p) in enumerate(tr)
        if r_idx not in used
    ]
    missing = len(missing_rows)
    extra = len(extra_rows)
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
           "sequence_edit_distance": int(_levenshtein(seq_s, seq_r)),
           # Exact rows come from the same matcher that produced the counts.
           # Downstream attribution must consume these instead of
           # re-discovering missing turns with a second ad-hoc pass.
           "missing_turn_details": missing_rows,
           "extra_turn_details": extra_rows,
           # Audit trail: extrema excluded by the edge-evidence rule are
           # still reported (never silently dropped) so a reviewer can
           # verify the confirmed-only gate did not hide real turns.
           "edge_uncertain_turn_details": {
               "source": [{"frame_idx": int(i), "kind": k,
                           "value_c": round(v, 1),
                           "prominence_c": round(p, 1),
                           "reason": "insufficient_two_sided_evidence"}
                          for i, k, v, p in ts_uncertain],
               "render": [{"frame_idx": int(i), "kind": k,
                           "value_c": round(v, 1),
                           "prominence_c": round(p, 1),
                           "reason": "insufficient_two_sided_evidence"}
                          for i, k, v, p in tr_uncertain]}}
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
    if k < 2 or len(y) < 3:
        return y
    k = min(k, len(y))
    if k % 2 == 0:
        k = max(1, k - 1)
    if k < 2:
        return y
    pad = k // 2
    padded = np.pad(y, (pad, pad), mode="edge")
    return np.convolve(padded, np.ones(k) / k, mode="valid")


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


def _cn_profile(sig, s, e, c0, span, n=33, glitch_c=None):
    """Normalized trajectory sampled on a uniform 0..1 grid, expressed in
    the SOURCE event's coordinate frame (c0/span from the source event) —
    comparing shapes in a shared frame keeps a faithful render that copies
    a source-side dip from looking like an 'overshoot'.

    glitch_c: when given, frames whose raw cents deviate from the smoothed
    trend by more than this are dropped before profiling — a single-frame
    extraction spike is not shape evidence."""
    cents = sig.cents
    if glitch_c is not None:
        from agent2utau.expression.contour import robust_pitch_trend
        tr, _ = robust_pitch_trend(sig)
        cents = np.where(np.abs(sig.cents - tr) > glitch_c,
                         np.nan, sig.cents)
    m = (sig.times >= s) & (sig.times <= e) & ~np.isnan(cents) \
        & sig.voiced
    if m.sum() < 4:
        return None
    t, c = sig.times[m], cents[m]
    tn = (t - t[0]) / max(t[-1] - t[0], 1e-6)
    cn = (c - c0) / span
    return np.interp(np.linspace(0.0, 1.0, n), tn, cn)


def event_shape_gate(source_events, render_events, neutral_sig,
                     source_sig, render_sig, source_core_bounds=None):
    """Absolute event-shape gate (plan R3/L7): for every matched
    portamento event, overlay the normalized SOURCE/NEUTRAL/RENDER
    trajectories in the source frame and classify the mismatch BEFORE
    trusting traj_match flags.

    Classes (checked in order):
      render_voicing_loss  render unvoiced over >=40% of [s-50ms, e]
                           while neutral remains voiced — audible synthesis
                           regression, blocks.
      shared_voicing_gap    render and neutral both lose voicing over the
                           same event window — not attributable to the
                           candidate curve, non-blocking shape evidence.
      source_irregular     source coverage <80% in-window or |cn_src|
                           exceeds 1.5 — extraction-noise region, too
                           little reliable evidence to judge shape.
      distortion           cn_rmse > 0.35 on CLEAN evidence — a real
                           trajectory divergence (blocks listening).
      extraction_artifact  raw rmse > 0.35 but rmse drops below it once
                           single-frame extraction spikes (|raw-trend| >
                           150c) are excluded — the divergence lives in
                           glitch frames, not in the sung contour.
      label_mismatch       trajectory_type differs but shape is close —
                           classifier granularity, not a shape defect.
      boundary_shift       start/end estimate differs by >80ms while the
                           shape is close — detector boundary estimate.
      match                label and shape both consistent.
    """
    rows = []
    source_core_bounds = source_core_bounds or {}
    for se in source_events:
        if se.type != "portamento":
            continue
        fn = se.params.get("from_note")
        cand = [e for e in render_events if e.type == "portamento"
                and e.params.get("from_note") == fn]
        if not cand:
            continue                      # missing handled elsewhere
        re_ = cand[0]
        raw_s, raw_e = se.start_s, se.end_s
        core_spec = source_core_bounds.get(fn)
        if core_spec is None:
            core_spec = source_core_bounds.get(str(fn))
        core_meta = core_spec if isinstance(core_spec, dict) else {}
        core = (core_meta.get("reliable_core_s")
                if isinstance(core_spec, dict) else core_spec)
        core_applied = False
        s, e = raw_s, raw_e
        if core is not None and len(core) == 2:
            cs, ce = float(core[0]), float(core[1])
            ns, ne = max(raw_s, cs), min(raw_e, ce)
            # Never let an external evidence packet collapse the event
            # to a trivial sliver.  Edge uncertainty is useful only when
            # a substantive observable core remains.
            if ne - ns >= 0.04:
                s, e = ns, ne
                core_applied = (s > raw_s + 1e-6 or e < raw_e - 1e-6)

        # Keep the full-window clean mismatch for audit.  The core window
        # may be used for acceptance only when a committed evidence packet
        # explicitly marks a low-salience uncertain edge.
        raw_cn_rmse_clean = None
        if core_applied:
            raw_ms = ((source_sig.times >= raw_s)
                      & (source_sig.times <= raw_e)
                      & ~np.isnan(source_sig.cents) & source_sig.voiced)
            if raw_ms.sum() >= 4:
                raw_c0 = float(source_sig.cents[raw_ms][0])
                raw_span = float(source_sig.cents[raw_ms][-1] - raw_c0)
                raw_span = raw_span if abs(raw_span) > 1e-6 else 1e-6
                raw_ps_c = _cn_profile(source_sig, raw_s, raw_e,
                                       raw_c0, raw_span, glitch_c=150.0)
                raw_pr_c = _cn_profile(render_sig, raw_s, raw_e,
                                       raw_c0, raw_span, glitch_c=150.0)
                if raw_ps_c is not None and raw_pr_c is not None:
                    raw_cn_rmse_clean = float(np.sqrt(
                        np.mean((raw_ps_c - raw_pr_c) ** 2)))

        ms_all = (source_sig.times >= s) & (source_sig.times <= e)
        ms = ms_all & ~np.isnan(source_sig.cents) & source_sig.voiced
        me = (render_sig.times >= s - 0.05) & (render_sig.times <= e)
        mn = (neutral_sig.times >= s - 0.05) & (neutral_sig.times <= e)
        src_cov = float(np.mean(source_sig.voiced[ms_all])) \
            if ms_all.sum() else 0.0
        rend_cov = float(np.mean(render_sig.voiced[me])) if me.sum() else 0.0
        neu_cov = float(np.mean(neutral_sig.voiced[mn])) if mn.sum() else 0.0
        c0 = float(source_sig.cents[ms][0]) if ms.sum() else 0.0
        span = float(source_sig.cents[ms][-1] - c0) if ms.sum() else 0.0
        span = span if abs(span) > 1e-6 else 1e-6
        ps = _cn_profile(source_sig, s, e, c0, span)
        pn_ = _cn_profile(neutral_sig, s, e, c0, span)
        pr_ = _cn_profile(render_sig, s, e, c0, span)
        cn_rmse = (float(np.sqrt(np.mean((ps - pr_) ** 2)))
                   if ps is not None and pr_ is not None else None)
        # clean evidence: same profiles with extraction spikes excluded
        ps_c = _cn_profile(source_sig, s, e, c0, span, glitch_c=150.0)
        pr_c = _cn_profile(render_sig, s, e, c0, span, glitch_c=150.0)
        cn_rmse_clean = (float(np.sqrt(np.mean((ps_c - pr_c) ** 2)))
                         if ps_c is not None and pr_c is not None else None)
        src_exc = float(np.abs(ps).max()) if ps is not None else None
        d_start = (se.start_s - re_.start_s) * 1000.0
        d_end = (se.end_s - re_.end_s) * 1000.0
        label_src = se.params.get("trajectory_type")
        label_rend = re_.params.get("trajectory_type")

        if rend_cov < 0.60:
            # A render-only dropout is an audible synthesis regression and
            # must block.  It is non-shape evidence only when the neutral
            # baseline loses voicing in the same window as well.
            cls = "shared_voicing_gap" if neu_cov < 0.60 \
                else "render_voicing_loss"
        elif src_cov < 0.80 or (src_exc is not None and src_exc > 1.5):
            cls = "source_irregular"
        elif cn_rmse_clean is not None and cn_rmse_clean > 0.35:
            cls = "distortion"
        elif cn_rmse is not None and cn_rmse > 0.35:
            cls = "extraction_artifact"
        elif core_applied:
            # The source event is real, but one low-salience edge is not
            # reliably observable across extractors.  The reliable core
            # itself passed absolute-shape QA, so retain the uncertainty
            # explicitly without turning it into a false distortion.
            cls = "source_edge_uncertain"
        elif label_src != label_rend:
            cls = "label_mismatch"
        elif abs(d_start) > 80.0 or abs(d_end) > 80.0:
            cls = "boundary_shift"
        else:
            cls = "match"
        rows.append({
            "from_note": fn, "class": cls,
            "blocking": cls in ("distortion", "render_voicing_loss"),
            "traj_src": label_src, "traj_render": label_rend,
            "cn_rmse": round(cn_rmse, 3) if cn_rmse is not None else None,
            "cn_rmse_clean": round(cn_rmse_clean, 3)
                if cn_rmse_clean is not None else None,
            "src_excursion": round(src_exc, 3) if src_exc is not None else None,
            "src_coverage": round(src_cov, 3),
            "neutral_coverage_ext": round(neu_cov, 3),
            "rend_coverage_ext": round(rend_cov, 3),
            "delta_start_ms": round(d_start, 1),
            "delta_end_ms": round(d_end, 1),
            "window_s": [round(s, 3), round(e, 3)],
            "raw_window_s": [round(raw_s, 3), round(raw_e, 3)],
            "reliable_core_s": ([round(s, 3), round(e, 3)]
                                if core_applied else None),
            "edge_uncertain_side": (core_meta.get("side")
                                    if core_applied else None),
            "trimmed_start_ms": (round((s - raw_s) * 1000.0, 1)
                                 if core_applied else 0.0),
            "trimmed_end_ms": (round((raw_e - e) * 1000.0, 1)
                               if core_applied else 0.0),
            "raw_cn_rmse_clean": (
                round(raw_cn_rmse_clean, 3)
                if raw_cn_rmse_clean is not None else None),
            "overlay_src": np.round(ps, 3).tolist() if ps is not None else None,
            "overlay_neu": np.round(pn_, 3).tolist() if pn_ is not None else None,
            "overlay_render": np.round(pr_, 3).tolist() if pr_ is not None else None})
    n_block = sum(1 for r in rows if r["blocking"])
    return {"events": rows, "n_events": len(rows),
            "n_blocking": n_block,
            "by_class": {c: sum(1 for r in rows if r["class"] == c)
                         for c in {r["class"] for r in rows}},
            "gate_passed": n_block == 0}


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
        d = {"from_note": se.params["from_note"],
             "state": "matched_relaxed" if re_.params.get("arrival_relaxed")
                      else "matched",
             "arrival_relaxed": bool(re_.params.get("arrival_relaxed")),
             "arrival_offset_c": re_.params.get("arrival_offset_c", 0.0),
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
