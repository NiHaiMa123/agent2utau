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
def _cycle_runs(t, mm, ok, f0_hz, rate_range_hz, min_depth_c):
    """Valid half-cycles on detrended modulation `mm`.

    A half-cycle is one extremum -> opposite extremum step. Valid when
    the implied full period sits inside 1/rate_range (relaxed ±35%),
    excursion amplitude >= min_depth_c, and every frame is voiced +
    confident. Returns list of (j0, j1, half_period_s, amp_c) and the
    extrema index list.
    """
    ext = _peaks_troughs(mm)
    anchors = [j for j in np.where(ext != 0)[0]]
    half_lo = 0.5 / rate_range_hz[1] * 0.65
    half_hi = 0.5 / rate_range_hz[0] * 1.35
    halfs = []
    for a in range(len(anchors) - 1):
        j0, j1 = anchors[a], anchors[a + 1]
        hp = t[j1] - t[j0]
        amp = abs(mm[j1] - mm[j0]) / 2.0
        if not (half_lo <= hp <= half_hi) or amp < min_depth_c:
            continue
        if not ok[j0:j1 + 1].all():
            continue
        halfs.append((j0, j1, hp, amp))
    return halfs, anchors


def detect_vibrato_events(contour: ContourSignal, notes,
                          rate_range_hz=(4.0, 8.5), min_cycles=2.5,
                          min_depth_c=12.0, max_gap_cycles=0):
    """Vibrato = longest run of consecutive valid cycles on the detrended
    signal. Event start/end are the run's real boundaries (first valid
    cycle's first extremum -> last valid cycle's last extremum), never
    derived from a fixed note fraction."""
    trend, mod = robust_pitch_trend(contour, cutoff_hz=3.0)
    events = []
    for i, n in enumerate(notes):
        if n["dur_s"] < 0.40:
            continue
        s = n["abs_start_s"]
        e = n["abs_start_s"] + n["dur_s"]
        m = (contour.times >= s) & (contour.times <= e)
        t = contour.times[m]
        mm = mod[m]
        ok = (~np.isnan(mm) & contour.voiced[m]
              & (contour.confidence[m] > 0.5))
        if ok.sum() < int(0.30 / HOP_S):
            continue
        mm = np.where(ok, mm, np.nan)
        ok_i = np.where(ok)[0]
        mmf = np.interp(np.arange(len(mm)), ok_i, mm[ok_i])
        # Keep the original validity mask. Interpolating identity indices
        # makes every interior evidence hole look valid.
        okf = ok.copy()

        # candidate frequency via FFT on the detrended segment
        spec = np.abs(np.fft.rfft(mmf * np.hanning(len(mmf))))
        freqs = np.fft.rfftfreq(len(mmf), HOP_S)
        band = (freqs >= rate_range_hz[0]) & (freqs <= rate_range_hz[1])
        band_pow = float(spec[band].max()) if band.any() else 0.0
        if not band.any() or band_pow < 3.0:
            continue
        f0_hz = float(freqs[band][np.argmax(spec[band])])

        # extrema must be found on the filled signal; ok-state taken from
        # the original mask so cycles can't run through unvoiced holes
        halfs, anchors = _cycle_runs(
            np.arange(len(mmf)) * HOP_S + t[0], mmf, okf,
            f0_hz, rate_range_hz, min_depth_c)
        if not halfs:
            continue
        # longest run of consecutive half-cycles (anchor chains must be
        # contiguous: each half-cycle starts where the previous ended)
        runs, cur = [], [halfs[0]]
        for h in halfs[1:]:
            if h[0] == cur[-1][1]:
                cur.append(h)
            else:
                runs.append(cur)
                cur = [h]
        runs.append(cur)
        run_raw = max(runs, key=len)
        n_cycles = len(run_raw) / 2.0
        if n_cycles < min_cycles:
            continue
        # Trim leading/trailing half-cycles whose amplitude collapsed:
        # detrend-filter ringing decays sharply (>20% per half-cycle),
        # while real vibrato amplitude fluctuates around its level.
        # The min_cycles gate above uses the raw chain — onset/offset
        # ramps still prove the event; trimming only moves boundaries.
        run = run_raw
        while len(run) > 1 and run[0][3] < 0.8 * run[1][3]:
            run = run[1:]
        while len(run) > 1 and run[-1][3] < 0.8 * run[-2][3]:
            run = run[:-1]
        if not run:
            run = run_raw
        n_cycles = len(run) / 2.0
        i0, i1 = run[0][0], run[-1][1]
        periods = np.array([run[k][2] + run[k + 1][2]
                            for k in range(0, len(run) - 1, 2)])
        depths = np.array([(run[k][3] + run[k + 1][3]) / 2.0
                           for k in range(0, len(run) - 1, 2)])
        if len(periods) == 0:
            periods = np.array([run[0][2] * 2])
            depths = np.array([run[0][3]])
        measured_rate = float(1.0 / periods.mean())
        # FFT is candidate discovery only; accepted measured cycles must
        # themselves obey the declared vibrato-rate contract.
        if not (rate_range_hz[0] <= measured_rate <= rate_range_hz[1]):
            continue
        period_cv = float(np.std(periods) / periods.mean()) \
            if len(periods) > 1 else 0.0
        depth_c = float(depths.mean())
        depth_cv = float(np.std(depths) / depth_c) if len(depths) > 1 \
            and depth_c > 0 else 0.0
        # Event bounds = first/last extremum ± quarter-period return to
        # zero (declared constant, NOT data-following: ringing after a
        # stopped oscillation would otherwise fake a longer event).
        qr = 0.25 / measured_rate
        ev_s = float(max(t[i0] - qr, t[0]))
        ev_e = float(min(t[i1] + qr, t[-1]))
        seg_t = (np.arange(i0, i1 + 1) - i0) * HOP_S   # phase origin = ev_s
        seg_m = mmf[i0:i1 + 1]
        # Fit phase with the same measured frequency emitted below.
        w = 2 * np.pi * measured_rate
        X = np.column_stack([np.sin(w * seg_t), np.cos(w * seg_t)])
        coef, *_ = np.linalg.lstsq(X, seg_m, rcond=None)
        phase = float(np.arctan2(coef[1], coef[0]))
        resid = seg_m - X @ coef
        snr = float(np.sum(seg_m ** 2) / max(np.sum(resid ** 2), 1e-9))
        drift = float(np.polyfit(t[ok], trend[m][ok], 1)[0]) \
            if ok.sum() > 5 else 0.0
        cover = float(ok[i0:i1 + 1].mean())
        conf = max(0.0, min(1.0,
                   0.20 * min(snr / 8.0, 1.0)
                   + 0.20 * (1 - min(period_cv, 0.5) * 2)
                   + 0.15 * (1 - min(depth_cv, 0.6) / 0.6)
                   + 0.15 * min(n_cycles / 6.0, 1.0)
                   + 0.15 * cover
                   + 0.15 * float(np.mean(contour.confidence[m][ok]))))
        events.append(PitchEvent(
            "vibrato", [i], ev_s, ev_e, round(conf, 3),
            params={"rate_hz": round(measured_rate, 2),
                    "fft_bin_hz": round(f0_hz, 2),
                    "depth_c": round(depth_c, 1),
                    "phase_rad": round(phase, 3),
                    "phase_origin_s": round(float(t[i0]), 3),
                    "periods_ms": [round(float(x) * 1000, 1)
                                   for x in periods],
                    "depth_envelope_c": [round(float(x), 1)
                                         for x in depths],
                    "stable_cycle_count": round(n_cycles, 1),
                    "period_cv": round(period_cv, 3),
                    "depth_cv": round(depth_cv, 3),
                    "drift_c_per_s": round(drift, 1),
                    "mod_snr": round(snr, 2),
                    "voiced_coverage": round(cover, 3)},
            evidence={"extractor": contour.extractor}))
    return events


# ------------------------------------------------- §9.5 onset scoop/overshoot
def _settle_time(t, dev, ei, tol_c=15.0, hold_ms=60):
    """First time after extremum where |dev| stays inside tolerance."""
    need = max(1, int(round(hold_ms / 1000.0 / HOP_S)))
    run = 0
    for j in range(ei, len(t)):
        if np.isnan(dev[j]) or abs(dev[j]) >= tol_c:
            run = 0
            continue
        run += 1
        if run >= need:
            return float(t[j - need + 1])
    return None


def _gesture_start_time(t, dev, ei, tol_c=15.0, hold_ms=30):
    """Last sustained baseline stay before the onset extremum.

    Returns the first frame after that stay; falls back to first valid frame.
    """
    need = max(1, int(round(hold_ms / 1000.0 / HOP_S)))
    inside = (~np.isnan(dev)) & (np.abs(dev) < tol_c)
    runs = _sustained(inside[:max(ei, 1)], need)
    if runs:
        j = min(runs[-1][1], len(t) - 1)
        return float(t[j])
    valid = np.flatnonzero(~np.isnan(dev[:ei + 1]))
    return float(t[valid[0]]) if len(valid) else float(t[0])


def _count_turns_valid(y):
    """Count extrema without converting missing frames to zero."""
    n = 0
    valid = ~np.isnan(y)
    for lo, hi in _sustained(valid, 1):
        if hi - lo >= 3:
            n += int(np.sum(_peaks_troughs(y[lo:hi]) != 0))
    return n


def detect_onset_events(contour: ContourSignal, notes, nucleus_times,
                        pre_ms=80, post_ms=180, exclude_events=None):
    """Nucleus-anchored onset gestures. nucleus_times: {note_i: t_s}.

    Baseline is taken from the note's stable body (60-70% region, minus
    known vibrato/ornament event spans). Settle requires a CONTINUOUS
    hold_ms inside tolerance — not all remaining frames. Single-frame
    extremum spikes never trigger an event.
    """
    out = []
    for i, n in enumerate(notes):
        nuc = (nucleus_times or {}).get(i)
        if nuc is None:
            continue
        # stable-body baseline: 55-90% of the note, minus excluded events
        bs = n["abs_start_s"] + 0.55 * n["dur_s"]
        be = n["abs_start_s"] + 0.90 * n["dur_s"]
        bm = (contour.times >= bs) & (contour.times <= be) & \
             (contour.note_idx == i) & contour.voiced
        for ev in (exclude_events or []):
            if i in ev.note_indices:
                bm &= ~((contour.times >= ev.start_s)
                        & (contour.times <= ev.end_s))
        bc = contour.cents[bm]
        bc = bc[~np.isnan(bc)]
        if len(bc) < 5:
            continue
        base = float(np.median(bc))

        w0 = nuc - pre_ms / 1000.0
        # settle may take longer than post_ms; the classification window
        # is short, but the settle search extends into the note body
        w_settle = nuc + max(post_ms, 400) / 1000.0
        w1 = min(w_settle, n["abs_start_s"] + n["dur_s"])
        m = (contour.times >= w0) & (contour.times <= w1)
        t, c = contour.times[m], contour.cents[m]
        ok = ~np.isnan(c) & contour.voiced[m]
        if ok.sum() < 8:
            continue
        dev = np.where(ok, c - base, np.nan)
        # extremum must be a real local turn, not a single-frame spike:
        # require the value to persist >=2 frames (median-3 agreement);
        # extremum search restricted to the onset window (nuc+0.12s)
        med3 = dev.copy()
        for k in range(1, len(dev) - 1):
            w = dev[k - 1:k + 2]
            w = w[~np.isnan(w)]
            med3[k] = np.median(w) if len(w) else np.nan
        early = med3.copy()
        early[t > nuc + 0.12] = np.nan
        if np.isnan(early).all():
            continue
        dmin_i = int(np.nanargmin(early))
        dmax_i = int(np.nanargmax(early))
        dmin, dmax = med3[dmin_i], med3[dmax_i]
        typ = None
        # Early negative approach is a scoop; a later negative excursion
        # after the nucleus is an undershoot. Keep them distinct.
        if dmin < -30 and t[dmin_i] <= nuc + 0.06:
            typ = "scoop"
        elif dmin < -30 and t[dmin_i] <= nuc + 0.12:
            typ = "undershoot"
        elif dmax > 40 and t[dmax_i] <= nuc + 0.08:
            typ = "overshoot"
        if typ is None:
            continue
        ei = dmin_i if typ in ("scoop", "undershoot") else dmax_i
        depth = float(-dmin if typ in ("scoop", "undershoot") else dmax)
        peak_ms = float((t[ei] - nuc) * 1000)
        settle_s = _settle_time(t, med3, ei)
        ev_end = settle_s if settle_s is not None else float(t[-1])
        post = dev[ei:]
        post = post[~np.isnan(post)]
        recover_sign = 1 if typ in ("scoop", "undershoot") else -1
        mono = float(np.mean(np.diff(post) * recover_sign > -5)) \
            if len(post) > 1 else 1.0
        n_turn = _count_turns_valid(med3)
        shape = "irregular" if n_turn > 3 else \
            ("linear" if mono > 0.8 else "ease")
        ev_start = _gesture_start_time(t, med3, ei)
        conf = min(1.0, 0.3 + depth / 200.0 + ok.mean() * 0.3)
        out.append(PitchEvent(
            typ, [i], float(ev_start), float(ev_end),
            round(conf, 3),
            params={"anchor_nucleus_s": round(float(nuc), 3),
                    "depth_c": round(depth, 1),
                    "peak_time_ms": round(peak_ms, 1),
                    "settle_time_ms": (round((settle_s - nuc) * 1000, 1)
                                       if settle_s is not None else None),
                    "baseline_c": round(base, 1),
                    "direction": ("down-up" if typ in ("scoop", "undershoot")
                                  else "up-down"),
                    "monotonicity": round(mono, 2), "shape": shape},
            evidence={"extractor": contour.extractor}))
    return out


# -------------------------------------------------------- §9.6 portamento
def _sustained(mask, need):
    """Boolean runs of length >= need -> list of (lo,hi) index spans."""
    out, i = [], 0
    while i < len(mask):
        if not mask[i]:
            i += 1
            continue
        j = i
        while j < len(mask) and mask[j]:
            j += 1
        if j - i >= need:
            out.append((i, j))
        i = j
    return out


def _traj_type(cn, slope, curv):
    """Classify normalized trajectory (cn: 0->1) shape."""
    if len(cn) < 6:
        return "linear"
    # steps first: plateau stretches inside the trajectory (flat-top
    # extrema would otherwise masquerade as s_curve turns)
    plateau = np.abs(np.diff(cn)) < 0.03
    if _sustained(plateau, max(2, int(0.25 * len(cn)))):
        return "stepped"
    turns = int(np.sum(_peaks_troughs(cn) != 0))
    monotonic = float(np.mean(np.diff(cn) > -0.02))
    if turns >= 2 and monotonic < 0.9:
        return "irregular"
    # Monotonic S-curves have an inflection, not pitch extrema.
    core = np.asarray(curv[1:-1], dtype=float) if len(curv) > 2 else np.array([])
    if monotonic >= 0.9 and len(core):
        scale = float(np.percentile(np.abs(core), 75))
        if scale > 0.1:
            pos = np.mean(core > 0.20 * scale)
            neg = np.mean(core < -0.20 * scale)
            if pos >= 0.15 and neg >= 0.15:
                return "s_curve"
    if turns >= 2:
        return "s_curve"
    m = float(np.mean(cn))       # linear mean=0.5; trimmed span shifts it
    if m > 0.55:
        return "convex"          # fast early then flatten
    if m < 0.45:
        return "concave"         # slow then fast
    return "linear"


def detect_portamento_events(contour: ContourSignal, notes,
                             search_ms=350, tol_c=30.0, hold_ms=50):
    """Cross-boundary continuous trajectories between adjacent notes.

    departure = end of the last sustained stay inside from-tone±tol
    before the boundary; arrival = start of the first sustained stay
    inside to-tone±tol after it. duration/span come from that real
    trajectory, never from the analysis window.
    """
    out = []
    hold = max(2, int(round(hold_ms / 1000.0 / HOP_S)))
    for i in range(len(notes) - 1):
        a, b = notes[i], notes[i + 1]
        a_e = a["abs_start_s"] + a["dur_s"]
        gap = b["abs_start_s"] - a_e
        if gap > 0.08:
            continue
        s = a_e - search_ms / 1000.0
        e = b["abs_start_s"] + search_ms / 1000.0
        m = (contour.times >= s) & (contour.times <= e)
        t, c = contour.times[m], contour.cents[m]
        ok = ~np.isnan(c) & contour.voiced[m]
        if ok.sum() < 10:
            continue
        tone_a = a["tone"] * 100.0
        tone_b = b["tone"] * 100.0
        if abs(tone_b - tone_a) < 80:
            continue                     # near-unison: not a slide event
        in_a = ok & (np.abs(c - tone_a) <= tol_c)
        in_b = ok & (np.abs(c - tone_b) <= tol_c)
        stays_a = _sustained(in_a & (t < a_e), hold)
        stays_b = _sustained(in_b & (t >= b["abs_start_s"]), hold)
        if not stays_a or not stays_b:
            continue
        dep_i = stays_a[-1][1] - 1       # last frame still in tone_a
        arr_i = stays_b[0][0]            # first frame settled in tone_b
        if arr_i <= dep_i:
            continue
        tt, cc = t[dep_i:arr_i + 1], c[dep_i:arr_i + 1]
        okk = ok[dep_i:arr_i + 1]
        if okk.mean() < 0.5 or np.isnan(cc).all():
            continue
        # trajectory on the real span only; interpolate interior holes
        idx = np.flatnonzero(~np.isnan(cc))
        cf = np.interp(np.arange(len(cc)), idx, cc[idx])
        span = float(cf[-1] - cf[0])
        tn = (tt - tt[0]) / max(tt[-1] - tt[0], 1e-6)
        # Signed span already maps both upward and downward slides 0 -> 1.
        cn = (cf - cf[0]) / span if abs(span) > 1e-6 \
            else np.zeros_like(cf)
        slope = np.gradient(cn, np.maximum(tn, 1e-6))
        curv = np.gradient(slope, np.maximum(tn, 1e-6))
        traj = _traj_type(cn, slope, curv)
        out.append(PitchEvent(
            "portamento", [i, i + 1], float(t[dep_i]), float(t[arr_i]),
            round(float(0.4 + 0.4 * okk.mean() + 0.2 *
                        min(abs(span) / 300.0, 1.0)), 3),
            params={"from_note": i, "to_note": i + 1,
                    "departure_rel_prev_end_ms":
                        round(float((t[dep_i] - a_e) * 1000), 1),
                    "arrival_rel_next_start_ms":
                        round(float((t[arr_i] - b["abs_start_s"]) * 1000), 1),
                    "span_cents": round(span, 1),
                    "duration_ms": round(float(t[arr_i] - t[dep_i])
                                         * 1000, 1),
                    "direction": "up" if span > 0 else "down",
                    "trajectory_type": traj,
                    "boundary_ms": round(gap * 1000, 1),
                    "voiced_coverage": round(float(okk.mean()), 2),
                    "slope_profile": [round(float(x), 3) for x in slope],
                    "curv_profile": [round(float(x), 3) for x in curv],
                    "norm_traj": [round(float(x), 3) for x in cn]},
            evidence={"extractor": contour.extractor}))
    return out


# ---------------------------------------------------------- §9.7 ornament
def detect_ornament_events(contour: ContourSignal, notes,
                           exclude_events=None, win_ms=380,
                           min_excursion_c=40.0, min_extrema=2):
    """Short multi-extremum gestures anywhere in the note body.

    Excluded event spans remain real gaps: the detector works on contiguous
    eligible runs and never compresses time across a removed vibrato/onset.
    """
    trend, _ = robust_pitch_trend(contour, cutoff_hz=2.0)
    residual = contour.cents - trend
    out = []
    win = int(round(win_ms / 1000.0 / HOP_S))
    for i, n in enumerate(notes):
        s = n["abs_start_s"] + min(0.10, n["dur_s"] * 0.15)
        e = n["abs_start_s"] + n["dur_s"] - 0.04
        eligible = (contour.times >= s) & (contour.times <= e) & \
                   contour.voiced & ~np.isnan(residual)
        for ev in (exclude_events or []):
            if i in ev.note_indices:
                eligible &= ~((contour.times >= ev.start_s)
                              & (contour.times <= ev.end_s))

        for lo, hi in _sustained(eligible, 1):
            if hi - lo < 10:
                continue
            t = contour.times[lo:hi]
            cf = residual[lo:hi]
            ext = _peaks_troughs(cf)
            idx = np.where(ext != 0)[0]
            big = [j for j in idx if abs(cf[j]) >= min_excursion_c]
            if len(big) < min_extrema:
                continue
            groups, cur = [], [big[0]]
            for j in big[1:]:
                if j - cur[0] <= win:
                    cur.append(j)
                else:
                    groups.append(cur)
                    cur = [j]
            groups.append(cur)
            for grp in groups:
                if len(grp) < min_extrema:
                    continue
                excur = [float(cf[j]) for j in grp]
                signs = np.sign(excur)
                altern = int(np.sum(signs[1:] * signs[:-1] < 0))
                after = min(grp[-1] + 3, len(cf) - 1)
                returns = abs(cf[after]) < min_excursion_c
                ev = PitchEvent(
                    "ornament", [i], float(t[grp[0]]), float(t[grp[-1]]),
                    round(float(min(1.0, 0.35 + 0.1 * len(grp)
                                    + 0.15 * altern)), 3),
                    params={"excursions_c": [round(x, 1) for x in excur],
                            "extrema_rel_ms": [
                                round(float(t[j] - t[grp[0]]) * 1000, 1)
                                for j in grp],
                            "n_extrema": int(len(grp)),
                            "alternations": int(altern),
                            "duration_ms": round(
                                float(t[grp[-1]] - t[grp[0]]) * 1000, 1),
                            "returns_to_baseline": bool(returns)},
                    evidence={"extractor": contour.extractor})
                if not returns and abs(cf[-1]) > 80:
                    ev.evidence["structure_review_required"] = True
                    ev.evidence["blocker_lane"] = True
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
                            spike_c=150.0, octave_lo=900, octave_hi=1500):
    """Extractor artifacts as typed regions.

    Flags per frame: extractor_disagreement (low primary-vs-secondary
    confidence), octave_flip (raw far from segment median by ~1 octave),
    spike (isolated 1-2 frame excursion), hf_jitter (aperiodic fast
    modulation inside a 150ms window). Contiguous flagged frames
    (<30ms apart) merge into one region event.
    """
    out = []
    c, t = contour.cents, contour.times
    conf = contour.confidence
    valid = contour.voiced & ~np.isnan(c)
    seg = contour.segment_id
    if seg is None:
        from .contour import segment_ids
        seg = segment_ids(t, valid)
    trend, mod = robust_pitch_trend(contour, cutoff_hz=3.0)

    for sid in np.unique(seg[seg >= 0]):
        sm = seg == sid
        tt = t[sm]
        cc = c[sm]
        mm = mod[sm]
        vv = valid[sm]
        kk = conf[sm]
        ok = vv & ~np.isnan(cc)
        if ok.sum() < 5:
            continue
        # segmented rolling median (5-frame, same-segment only)
        med = np.full(len(cc), np.nan)
        for k in range(len(cc)):
            w = cc[max(0, k - 2):k + 3]
            w = w[~np.isnan(w)]
            med[k] = np.median(w) if len(w) else np.nan
        dev = np.abs(cc - med)
        flags = {
            "extractor_disagreement": ok & (kk < 0.35),
            "voiced_conflict": ok & (kk <= 0.45) & (kk > 0.0),
            "octave_flip": ok & (dev >= octave_lo) & (dev <= octave_hi),
            "spike": ok & (dev > spike_c) & (dev < octave_lo),
        }
        # hf jitter: windowed zero-crossing rate of modulation, aperiodic
        jit = np.zeros(len(cc), dtype=bool)
        w_n = int(round(0.15 / HOP_S))
        modok = ~np.isnan(mm)
        for k0 in range(0, len(cc) - w_n, max(1, w_n // 3)):
            w = mm[k0:k0 + w_n]
            wo = modok[k0:k0 + w_n]
            if wo.sum() < w_n * 0.7:
                continue
            ww = w[wo] - np.nanmean(w[wo])
            zc = int(np.sum(ww[1:] * ww[:-1] < 0))
            if zc >= 6:                  # >=3 sign flips per 75ms = jitter
                jit[k0:k0 + w_n] |= wo
        flags["hf_jitter"] = jit & ok
        bad = np.zeros(len(cc), dtype=bool)
        for f in flags.values():
            bad |= f
        idx = np.where(bad & ok)[0]
        if not len(idx):
            continue
        # merge frames closer than 30ms
        groups, cur = [], [idx[0]]
        for j in idx[1:]:
            if tt[j] - tt[cur[-1]] < 0.03:
                cur.append(j)
            else:
                groups.append(cur)
                cur = [j]
        groups.append(cur)
        note_set = sorted({int(x) for x in contour.note_idx[sm] if x >= 0})
        for grp in groups:
            kinds = [name for name, f in flags.items()
                     if f[grp].any()]
            out.append(PitchEvent(
                "artifact", note_set or [0],
                float(tt[grp[0]]), float(tt[grp[-1]]), 0.45,
                params={"n_frames": int(len(grp)),
                        "artifact_kinds": kinds,
                        "mean_conf": round(float(np.mean(kk[grp])), 2)},
                evidence={"extractor": contour.extractor}))
    return out


def artifact_mask(contour: ContourSignal, artifact_events):
    """Boolean mask of frames to EXCLUDE from compile/QA (R2.1-H)."""
    bad = np.zeros(len(contour.times), dtype=bool)
    for ev in artifact_events:
        bad |= (contour.times >= ev.start_s) & (contour.times <= ev.end_s)
    return bad


def detect_residual_artifact_regions(dense, notes=None,
                                     disagree_c=80.0,
                                     octave_lo=900.0, octave_hi=1500.0):
    """Artifact regions from disagreement between residual extractor families.

    This is deliberately separate from raw-F0 contour artifacts: two
    extractors may each look plausible yet disagree on the correction that
    should be applied. Such frames must not enter expression compilation.
    """
    g = np.asarray(dense["times"], dtype=float)
    r1 = np.asarray(dense.get("r_fcpe"), dtype=float)
    r2 = np.asarray(dense.get("r_rmvpe"), dtype=float)
    if r1.shape != g.shape or r2.shape != g.shape:
        return []
    valid = ~np.isnan(r1) & ~np.isnan(r2)
    d = np.abs(r1 - r2)
    bad = valid & (d > disagree_c)
    if not bad.any():
        return []
    kinds = {
        "residual_disagreement": valid & (d > disagree_c),
        "residual_octave_split": valid & (d >= octave_lo) & (d <= octave_hi),
    }
    idx = np.where(bad)[0]
    groups, cur = [], [idx[0]]
    for j in idx[1:]:
        if g[j] - g[cur[-1]] <= 0.03:
            cur.append(j)
        else:
            groups.append(cur)
            cur = [j]
    groups.append(cur)
    note_idx = np.asarray(dense.get("note_idx", np.full(len(g), -1)))
    out = []
    for grp in groups:
        ns = sorted({int(note_idx[j]) for j in grp if note_idx[j] >= 0})
        ks = [name for name, mask in kinds.items() if mask[grp].any()]
        out.append(PitchEvent(
            "artifact", ns or [0], float(g[grp[0]]), float(g[grp[-1]]),
            0.8, params={"n_frames": len(grp), "artifact_kinds": ks,
                         "max_residual_disagree_c":
                             round(float(np.nanmax(d[grp])), 1)},
            evidence={"extractor": "residual_family"}))
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
             "neutral_vibrato": (n0.params if n0 else None),
             "source_span_s": ([round(s0.start_s, 3), round(s0.end_s, 3)]
                               if s0 else None),
             "neutral_span_s": ([round(n0.start_s, 3), round(n0.end_s, 3)]
                                if n0 else None)}
        if s0 and n0:
            for k in ("rate_hz", "depth_c", "drift_c_per_s"):
                d[f"delta_{k}"] = round(
                    s0.params[k] - n0.params[k], 3)
        # note-vibrato fields can only express a tail-anchored sine;
        # mid-note events must stay in dense PITD
        periodic = s0 and s0.params.get("period_cv", 1) < 0.15 \
            and s0.params.get("depth_cv", 1) < 0.4
        # Note-vibrato is tail anchored and cannot stop early.
        tail_gap = (n["abs_start_s"] + n["dur_s"] - s0.end_s) if s0 else 1e9
        tail_end_tol = max(0.03, min(0.08, 0.05 * n["dur_s"]))
        tail_anchored = s0 and abs(tail_gap) <= tail_end_tol
        if state == "neutral_only":
            rep = "suppress_neutral"
        elif periodic and tail_anchored:
            rep = "note_vibrato"
        elif s0:
            rep = "irregular_pitd"
        else:
            rep = "none"
        d["recommended_representation"] = rep
        out.append(d)
    return out


def _event_score(se, ne, notes, nucleus_times):
    """Semantic match score in [0,1] for same-type events.

    Components: note carrier overlap, nucleus/note-relative position,
    temporal overlap, direction agreement, trajectory similarity,
    parameter compatibility. Returns (score, detail_dict).
    """
    det = {}
    shared = set(se.note_indices) & set(ne.note_indices)
    if not shared:
        return 0.0, {"reason": "no_shared_note"}
    ni = sorted(shared)[0]
    n = notes[ni]
    det["note_iou"] = len(shared) / len(set(se.note_indices)
                                        | set(ne.note_indices))
    ov = min(se.end_s, ne.end_s) - max(se.start_s, ne.start_s)
    union = max(se.end_s, ne.end_s) - min(se.start_s, ne.start_s)
    det["time_iou"] = max(0.0, ov) / max(union, 1e-6)
    nuc = (nucleus_times or {}).get(ni)
    if nuc is not None:
        rs = (se.start_s - nuc) / n["dur_s"]
        rn = (ne.start_s - nuc) / n["dur_s"]
        det["nuc_pos"] = max(0.0, 1.0 - abs(rs - rn))
    else:
        rs = (se.start_s - n["abs_start_s"]) / n["dur_s"]
        rn = (ne.start_s - n["abs_start_s"]) / n["dur_s"]
        det["note_pos"] = max(0.0, 1.0 - abs(rs - rn))
    ds, dn = se.params.get("direction"), ne.params.get("direction")
    det["direction"] = 1.0 if (ds is None or dn is None or ds == dn) else 0.0
    ts_, tn_ = se.params.get("trajectory_type"), ne.params.get("trajectory_type")
    det["trajectory"] = 1.0 if (ts_ is None or tn_ is None or ts_ == tn_) \
        else 0.4
    # parameter compatibility for vibrato/portamento
    compat = 1.0
    if se.type == "vibrato" and "rate_hz" in se.params \
            and "rate_hz" in ne.params:
        compat = max(0.0, 1.0 - abs(se.params["rate_hz"]
                                    - ne.params["rate_hz"]) / 1.5)
    det["param_compat"] = compat
    pos = det.get("nuc_pos", det.get("note_pos", 0.5))
    score = (0.25 * det["time_iou"] + 0.20 * det["note_iou"]
             + 0.20 * pos + 0.15 * det["direction"]
             + 0.10 * det["trajectory"] + 0.10 * det["param_compat"])
    # hard gate: zero temporal overlap AND far note-relative position
    # means these are different gestures on the same note, not a match
    if det["time_iou"] <= 0.0 and pos < 0.7:
        score = min(score, 0.25)
    # opposite direction is a different event, not a fuzzy match
    if det["direction"] == 0.0:
        score = min(score, 0.15)
    return score, det


def match_pitch_events(source_events, neutral_events, notes,
                       nucleus_times=None, accept=0.45, ambiguous=0.30):
    """Semantic matching with candidate scores.

    Returns matched / source_only / neutral_only / ambiguous — a pair
    scoring between `ambiguous` and `accept` is reported as ambiguous,
    never forced.
    """
    matched, src_only, used_neu, amb = [], [], set(), []
    for se in source_events:
        cands = []
        for j, ne in enumerate(neutral_events):
            if j in used_neu or ne.type != se.type:
                continue
            score, det = _event_score(se, ne, notes, nucleus_times)
            if score > 0:
                cands.append((score, j, det))
        cands.sort(reverse=True, key=lambda x: x[0])
        if cands and cands[0][0] >= accept:
            score, j, det = cands[0]
            used_neu.add(j)
            matched.append({"source": se, "neutral": neutral_events[j],
                            "score": round(score, 3), "detail": det,
                            "state": "matched"})
        elif cands and cands[0][0] >= ambiguous:
            amb.append({"source": se,
                        "candidates": [{"neutral_index": j,
                                        "score": round(s, 3)}
                                       for s, j, _ in cands[:3]],
                        "state": "ambiguous"})
        else:
            src_only.append(se)
    neu_only = [e for j, e in enumerate(neutral_events) if j not in used_neu]
    return {"matched": matched, "source_only": src_only,
            "neutral_only": neu_only, "ambiguous": amb}


def event_to_json(e: PitchEvent):
    return {"type": e.type, "note_indices": e.note_indices,
            "start_s": round(e.start_s, 3), "end_s": round(e.end_s, 3),
            "confidence": e.confidence, "params": e.params,
            "evidence": e.evidence}
