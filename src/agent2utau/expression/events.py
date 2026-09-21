"""Pitch event detectors (plan §9.3-9.10).

Every detector runs on ONE ContourSignal (source or neutral separately);
matching happens afterwards in match_pitch_events. Detectors emit
structured PitchEvent with confidence — never PITD points.
"""

from __future__ import annotations

import numpy as np

from .contour import ContourSignal, PitchEvent, robust_pitch_trend

HOP_S = 0.010


def _note_window(sig, n, pad_s=0.0):
    s = n["abs_start_s"] - pad_s
    e = n["abs_start_s"] + n["dur_s"] + pad_s
    return (sig.times >= s) & (sig.times <= e)


def _peaks_troughs(y):
    """Indices of local extrema: peaks>0, troughs<0, else 0."""
    sgn = np.zeros(len(y), dtype=int)
    if len(y) < 3:
        return sgn
    d1 = np.diff(y)
    sgn[1:-1][(d1[:-1] > 0) & (d1[1:] <= 0)] = 1
    sgn[1:-1][(d1[:-1] < 0) & (d1[1:] >= 0)] = -1
    return sgn


# ------------------------------------------------------------- §9.3 vibrato
def detect_vibrato_events(contour: ContourSignal, notes,
                          rate_range_hz=(4.0, 8.5), min_cycles=2.5,
                          min_depth_c=12.0):
    """Vibrato from per-cycle peak/trough structure, not autocorr alone."""
    trend, mod = robust_pitch_trend(contour, cutoff_hz=3.0)
    events = []
    for i, n in enumerate(notes):
        if n["dur_s"] < 0.45:
            continue
        s = n["abs_start_s"] + min(0.15, n["dur_s"] * 0.2)
        e = n["abs_start_s"] + n["dur_s"] - 0.02
        m = (contour.times >= s) & (contour.times <= e)
        t, mm = contour.times[m], mod[m]
        vv = contour.voiced[m]
        cc = contour.confidence[m]
        ok = ~np.isnan(mm) & vv & (cc > 0.5)
        if ok.sum() < int(0.30 / HOP_S):
            continue
        mmf = np.interp(t, t[ok], mm[ok])

        # candidate frequency via FFT on detrended segment
        spec = np.abs(np.fft.rfft(mmf * np.hanning(len(mmf))))
        freqs = np.fft.rfftfreq(len(mmf), HOP_S)
        band = (freqs >= rate_range_hz[0]) & (freqs <= rate_range_hz[1])
        if not band.any() or spec[band].max() < 3.0:
            continue
        f0_hz = freqs[band][np.argmax(spec[band])]

        # real stability: consecutive peak-to-peak periods
        ext = _peaks_troughs(mmf)
        pk = np.where(ext == 1)[0]
        tr = np.where(ext == -1)[0]
        if len(pk) < 2 or len(tr) < 2:
            continue
        periods = np.diff(t[pk])          # seconds
        periods = periods[periods > 0.05]
        if len(periods) < 2:
            continue
        period_cv = float(np.std(periods) / np.mean(periods))
        # per-cycle depth: peak - nearest troughs
        depths = []
        for k in range(len(pk) - 1):
            lo = tr[(tr > pk[k]) & (tr < pk[k + 1])]
            if len(lo):
                depths.append(float(mmf[pk[k]] - mmf[lo].min()) / 2.0)
        depth_c = float(np.mean(depths)) if depths else 0.0
        depth_cv = float(np.std(depths) / depth_c) if len(depths) > 1 \
            and depth_c > 0 else 1.0
        n_cycles = (t[pk[-1]] - t[pk[0]]) * f0_hz if len(pk) > 1 else 0.0
        if n_cycles < min_cycles or depth_c < min_depth_c:
            continue
        # span: first to last extremum actually sustaining the band
        ev_s, ev_e = float(t[pk[0]]), float(t[pk[-1]])
        drift = float(np.polyfit(t[ok], trend[m][ok], 1)[0]) \
            if ok.sum() > 5 else 0.0
        # periodicity diagnostic (NOT called stability): autocorr at period
        ac = np.correlate(mmf - mmf.mean(), mmf - mmf.mean(),
                          mode="full")[len(mmf) - 1:]
        ac /= ac[0]
        lag = int(round(1.0 / f0_hz / HOP_S))
        pscore = float(ac[lag]) if lag < len(ac) else 0.0
        phase = float(np.arctan2(
            np.sum(mmf * np.cos(2 * np.pi * f0_hz * t)),
            np.sum(mmf * np.sin(2 * np.pi * f0_hz * t))))
        conf = max(0.0, min(1.0,
                   0.5 * pscore + 0.3 * (1 - min(period_cv, 0.5) * 2)
                   + 0.2 * min(n_cycles / 6.0, 1.0)))
        events.append(PitchEvent(
            "vibrato", [i], ev_s, ev_e, round(conf, 3),
            params={"rate_hz": round(float(f0_hz), 2),
                    "depth_c": round(depth_c, 1),
                    "phase_rad": round(phase, 3),
                    "periods_ms": [round(float(x) * 1000, 1)
                                   for x in periods],
                    "period_cv": round(period_cv, 3),
                    "cycle_depths_c": [round(d, 1) for d in depths],
                    "depth_cv": round(depth_cv, 3),
                    "drift_c_per_s": round(drift, 1),
                    "periodicity_score": round(pscore, 3)},
            evidence={"extractor": contour.extractor}))
    return events


# ------------------------------------------------- §9.5 onset scoop/overshoot
def detect_onset_events(contour: ContourSignal, notes, nucleus_times,
                        pre_ms=80, post_ms=180):
    """Nucleus-anchored onset gestures. nucleus_times: {note_i: t_s}."""
    out = []
    for i, n in enumerate(notes):
        nuc = (nucleus_times or {}).get(i)
        if nuc is None:
            continue
        w0, w1 = nuc - pre_ms / 1000.0, nuc + post_ms / 1000.0
        m = (contour.times >= w0) & (contour.times <= w1)
        t, c = contour.times[m], contour.cents[m]
        ok = ~np.isnan(c) & contour.voiced[m]
        if ok.sum() < 8:
            continue
        # settled baseline: 150-350ms after nucleus inside the note
        bm = (contour.times >= nuc + post_ms / 1000.0) & \
             (contour.times <= nuc + (post_ms + 200) / 1000.0) & \
             (contour.note_idx == i)
        bc = contour.cents[bm]
        bc = bc[~np.isnan(bc)]
        if len(bc) < 5:
            continue
        base = float(np.median(bc))
        dev = c - base
        dev[~ok] = np.nan
        dmin_i = int(np.nanargmin(dev))
        dmax_i = int(np.nanargmax(dev))
        dmin, dmax = dev[dmin_i], dev[dmax_i]
        typ = None
        if dmin < -30 and t[dmin_i] <= nuc + 0.06:
            typ = "scoop"
        elif dmax > 40 and t[dmax_i] <= nuc + 0.08:
            typ = "overshoot"
        if typ is None:
            continue
        ei = dmin_i if typ == "scoop" else dmax_i
        depth = float(-dmin if typ == "scoop" else dmax)
        peak_ms = float((t[ei] - nuc) * 1000)
        # settle: first time after extremum staying within 15c of base
        settle_ms = None
        for j in range(ei, len(t)):
            if np.all(np.abs(dev[j:]) < 15):
                settle_ms = float((t[j] - nuc) * 1000)
                break
        post = dev[ei:]
        post = post[~np.isnan(post)]
        mono = float(np.mean(np.diff(post) * (1 if typ == "scoop" else -1)
                             > -5)) if len(post) > 1 else 1.0
        n_turn = int(np.sum(_peaks_troughs(np.nan_to_num(dev)) != 0))
        shape = "irregular" if n_turn > 3 else \
            ("linear" if mono > 0.8 else "ease")
        conf = min(1.0, 0.3 + depth / 200.0 + ok.mean() * 0.3)
        out.append(PitchEvent(
            typ, [i], float(t[0]), float(t[min(ei + 8, len(t) - 1)]),
            round(conf, 3),
            params={"anchor_nucleus_s": round(float(nuc), 3),
                    "depth_c": round(depth, 1),
                    "peak_time_ms": round(peak_ms, 1),
                    "settle_time_ms": (round(settle_ms, 1)
                                       if settle_ms is not None else None),
                    "direction": "down-up" if typ == "scoop" else "up-down",
                    "monotonicity": round(mono, 2), "shape": shape},
            evidence={"extractor": contour.extractor}))
    return out


# -------------------------------------------------------- §9.6 portamento
def detect_portamento_events(contour: ContourSignal, notes,
                             boundary_window_ms=220):
    """Cross-boundary continuous trajectories between adjacent notes."""
    out = []
    for i in range(len(notes) - 1):
        a, b = notes[i], notes[i + 1]
        a_e = a["abs_start_s"] + a["dur_s"]
        gap = b["abs_start_s"] - a_e
        if gap > 0.08:                          # breath gap, not portamento
            continue
        s = a_e - boundary_window_ms / 2000.0
        e = b["abs_start_s"] + boundary_window_ms / 2000.0
        m = (contour.times >= s) & (contour.times <= e)
        t, c = contour.times[m], contour.cents[m]
        ok = ~np.isnan(c) & contour.voiced[m]
        if ok.sum() < 10 or ok.mean() < 0.5:
            continue
        tone_a = a["tone"] * 100.0
        tone_b = b["tone"] * 100.0
        dev_a = np.abs(c - tone_a)
        dev_b = np.abs(c - tone_b)
        # departure: last frame before boundary still near tone_a
        pre = t < a_e
        post = t >= b["abs_start_s"]
        if not pre.any() or not post.any():
            continue
        dep_rel = None
        for j in np.where(pre)[0][::-1]:
            if ok[j] and dev_a[j] > 30:
                dep_rel = float((t[j] - a_e) * 1000)
                break
            if ok[j] and dev_a[j] <= 30 and dep_rel is None:
                dep_rel = float((t[j] - a_e) * 1000)
                break
        arr_rel = None
        for j in np.where(post)[0]:
            if ok[j] and dev_b[j] <= 30:
                arr_rel = float((t[j] - b["abs_start_s"]) * 1000)
                break
        if dep_rel is None and arr_rel is None:
            continue
        c_ok = np.where(ok, c, np.nan)
        i_lo = int(np.nanargmin(c_ok)) if np.isfinite(c_ok).any() else 0
        i_hi = int(np.nanargmax(c_ok))
        span = float(c_ok[i_hi] - c_ok[i_lo])
        curv = np.nanmean(np.diff(np.where(ok, c, np.nan), 2))
        traj = "linear"
        if abs(curv) > 8:
            traj = "convex" if curv > 0 else "concave"
        if np.sum(_peaks_troughs(np.nan_to_num(c_ok)) != 0) > 2:
            traj = "s_curve"
        out.append(PitchEvent(
            "portamento", [i, i + 1], float(s), float(e), 0.6,
            params={"from_note": i, "to_note": i + 1,
                    "start_rel_prev_end_ms": dep_rel,
                    "end_rel_next_start_ms": arr_rel,
                    "span_cents": round(span, 1),
                    "duration_ms": round((e - s) * 1000, 1),
                    "direction": "up" if b["tone"] > a["tone"] else "down",
                    "trajectory_type": traj,
                    "boundary_ms": round(gap * 1000, 1)},
            evidence={"extractor": contour.extractor}))
    return out


# ---------------------------------------------------------- §9.7 ornament
def detect_ornament_events(contour: ContourSignal, notes,
                           max_duration_ms=350, min_excursion_c=40.0):
    """Short multi-extremum gestures inside a note body."""
    trend, mod_unused = robust_pitch_trend(contour, cutoff_hz=2.0)
    out = []
    for i, n in enumerate(notes):
        body_s = n["abs_start_s"] + min(0.12, n["dur_s"] * 0.25)
        body_e = n["abs_start_s"] + n["dur_s"] - 0.05
        if body_e - body_s > max_duration_ms / 1000.0:
            body_e = body_s + max_duration_ms / 1000.0
        m = (contour.times >= body_s) & (contour.times <= body_e)
        t = contour.times[m]
        c = contour.cents[m] - trend[m] if trend is not None else \
            contour.cents[m]
        ok = ~np.isnan(c) & contour.voiced[m]
        if ok.sum() < 8:
            continue
        cf = np.interp(t, t[ok], c[ok])
        ext = _peaks_troughs(cf)
        idx = np.where(ext != 0)[0]
        if len(idx) < 2:
            continue
        excur = [float(cf[j]) for j in idx]
        big = [x for x in excur if abs(x) >= min_excursion_c]
        if len(big) < 2:
            continue
        signs = np.sign(big)
        altern = int(np.sum(signs[1:] * signs[:-1] < 0))
        returns = abs(cf[-1]) < min_excursion_c
        typ = "ornament"
        ev = PitchEvent(
            typ, [i], float(t[idx[0]]), float(t[idx[-1]]), 0.5,
            params={"excursions_c": [round(x, 1) for x in big],
                    "n_extrema": int(len(big)),
                    "alternations": int(altern),
                    "duration_ms": round(float(t[idx[-1]] - t[idx[0]])
                                         * 1000, 1),
                    "returns_to_baseline": bool(returns)},
            evidence={"extractor": contour.extractor})
        # looks like a real written split instead of an ornament?
        if not returns and abs(cf[-1]) > 80:
            ev.evidence["structure_review_required"] = True
        out.append(ev)
    return out


# ------------------------------------------------------- §9.8 stable trend
def detect_stable_trend(contour: ContourSignal, notes, excluded_events):
    """Slow intonation on voiced body minus all detected event regions."""
    trend, _ = robust_pitch_trend(contour, cutoff_hz=1.5)
    out = []
    for i, n in enumerate(notes):
        s, e = n["abs_start_s"], n["abs_start_s"] + n["dur_s"]
        mask = (contour.times >= s + 0.05) & (contour.times <= e - 0.05) & \
               (contour.note_idx == i) & contour.voiced
        for ev in excluded_events:
            if i in ev.note_indices:
                mask &= ~((contour.times >= ev.start_s)
                          & (contour.times <= ev.end_s))
        t, tr = contour.times[mask], trend[mask]
        ok = ~np.isnan(tr)
        if ok.sum() < 6:
            continue
        tt, yy = t[ok], tr[ok]
        drift = float(np.polyfit(tt, yy, 1)[0]) if len(tt) > 3 else 0.0
        out.append(PitchEvent(
            "stable", [i], float(tt[0]), float(tt[-1]),
            round(float(min(1.0, ok.mean() + 0.2)), 3),
            params={"start_c": round(float(yy[0]), 1),
                    "end_c": round(float(yy[-1]), 1),
                    "max_dev_c": round(float(np.max(np.abs(
                        yy - np.median(yy)))), 1),
                    "drift_c_per_s": round(drift, 1)},
            evidence={"extractor": contour.extractor}))
    return out


# ------------------------------------------------------- §9.9 artifacts
def detect_artifact_regions(contour: ContourSignal, notes,
                            spike_c=150.0):
    """Extractor artifacts: disagreement + isolated spikes."""
    out = []
    c, t = contour.cents, contour.times
    conf = contour.confidence
    for i, n in enumerate(notes):
        m = _note_window(contour, n)
        tt, cc, kk = t[m], c[m], conf[m]
        ok = ~np.isnan(cc)
        if ok.sum() < 5:
            continue
        med = np.convolve(np.where(ok, cc, np.nan), np.ones(5) / 5,
                          mode="same")
        spike = np.abs(cc - med) > spike_c
        bad = (kk < 0.35) | spike
        idx = np.where(bad & ok)[0]
        if len(idx):
            out.append(PitchEvent(
                "artifact", [i], float(tt[idx[0]]), float(tt[idx[-1]]),
                0.4, params={"n_frames": int(len(idx)),
                             "mean_conf": round(float(np.mean(kk[idx])), 2)},
                evidence={"extractor": contour.extractor}))
    return out


# ------------------------------------------------------ §9.4/§9.10 match
def match_vibrato_events(source_events, neutral_events, notes):
    """Match vibrato by note identity; report param deltas."""
    out = []
    for i, n in enumerate(notes):
        se = [e for e in source_events
              if e.type == "vibrato" and i in e.note_indices]
        ne = [e for e in neutral_events
              if e.type == "vibrato" and i in e.note_indices]
        if not se and not ne:
            continue
        s0, n0 = (se[0] if se else None), (ne[0] if ne else None)
        if s0 and n0:
            state = "matched"
        elif s0:
            state = "source_only"
        else:
            state = "neutral_only"
        d = {"note_index": i, "match_state": state,
             "source_vibrato": (s0.params if s0 else None),
             "neutral_vibrato": (n0.params if n0 else None)}
        if s0 and n0:
            for k in ("rate_hz", "depth_c", "drift_c_per_s"):
                d[f"delta_{k}"] = round(
                    s0.params[k] - n0.params[k], 3)
        d["recommended_representation"] = (
            "note_vibrato" if (s0 and s0.params.get("period_cv", 1) < 0.15
                               and s0.params.get("depth_cv", 1) < 0.4)
            else "irregular_pitd" if s0 else "suppress_neutral")
        out.append(d)
    return out


def match_pitch_events(source_events, neutral_events, notes,
                       nucleus_times=None):
    """Generic event matching: same type + overlapping note carrier."""
    matched, src_only, used_neu = [], [], set()
    for se in source_events:
        best, best_ov = None, 0.0
        for j, ne in enumerate(neutral_events):
            if j in used_neu or ne.type != se.type:
                continue
            if not set(se.note_indices) & set(ne.note_indices):
                continue
            ov = min(se.end_s, ne.end_s) - max(se.start_s, ne.start_s)
            if ov > best_ov:
                best, best_ov = j, ov
        if best is not None:
            used_neu.add(best)
            matched.append({"source": se, "neutral": neutral_events[best],
                            "overlap_s": round(best_ov, 3),
                            "state": "matched"})
        else:
            src_only.append(se)
    neu_only = [e for j, e in enumerate(neutral_events) if j not in used_neu]
    return {"matched": matched, "source_only": src_only,
            "neutral_only": neu_only}


def event_to_json(e: PitchEvent):
    return {"type": e.type, "note_indices": e.note_indices,
            "start_s": round(e.start_s, 3), "end_s": round(e.end_s, 3),
            "confidence": e.confidence, "params": e.params,
            "evidence": e.evidence}
