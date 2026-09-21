"""Fixed-time dense PITD residual (plan.md Stage D, revised 2026-09-21).

No DTW / lag search / HFA warp: SOURCE and the Yousa neutral render share
the same absolute project timeline by construction, so residual is
computed at identical t on both signals:

    residual_cents(t) = 1200 * log2(F0_source(t) / F0_neutral(t))

Each 10ms frame gets a state (§7.3) and only PITD-eligible frames enter
the dense residual. Dense artifacts are saved before any simplification.
"""

from __future__ import annotations

import numpy as np

TICK_MS = 60.0 / 120.0 / 480.0 * 1000.0

# frame states (plan §7.3)
SAME_NOTE_BOTH_VOICED = 0
SOURCE_ONLY_VOICED = 1
NEUTRAL_ONLY_VOICED = 2
BOTH_UNVOICED = 3
EXTRACTOR_CONFLICT = 4
NOTE_TRANSITION = 5
GAP = 6

CONFLICT_CENTS = 300.0      # fcpe-vs-rmvpe raw-F0 disagreement (octave gate)
CONSENSUS_CENTS = 80.0      # residual-family disagreement gate (plan §8.1)
TRANSITION_MS = 60.0        # distance to note boundary flagged transition
MAX_RESID_CENTS = 800.0     # beyond this is treated as conflict regardless


def _midi(f0):
    from agent2utau.analysis.f0 import hz_to_midi
    return np.asarray(f0["times"]), hz_to_midi(np.asarray(f0["f0_hz"])), \
        np.asarray(f0["voiced"], dtype=bool)


def _sample(grid_s, times_s, midi, voiced):
    v = np.interp(grid_s, times_s, midi, left=np.nan, right=np.nan)
    ok = np.interp(grid_s, times_s, voiced.astype(float),
                   left=0.0, right=0.0) > 0.5
    v[~ok] = np.nan
    return v, ok


def compute_dense(ref_f0, neu_f0, ref_f0_b, neu_f0_b, notes,
                  t0_s, t1_s, hop_s=0.010):
    """Same-time dense residual over [t0_s,t1_s].

    notes: list of {'abs_start_s','dur_s','tone','lyric'}.
    Returns dict with grid, state[], residual_cents[], per-source arrays.
    """
    g = t0_s + np.arange(int(round((t1_s - t0_s) / hop_s)) + 1) * hop_s
    rt, rm, rv = _midi(ref_f0)
    nt, nm, nv = _midi(neu_f0)
    bt, bm, bv = _midi(ref_f0_b)
    ut, um, uv = _midi(neu_f0_b)

    R, Rok = _sample(g, rt, rm, rv)
    N, Nok = _sample(g, nt, nm, nv)
    RB, RBok = _sample(g, bt, bm, bv)
    NB, NBok = _sample(g, ut, um, uv)

    # extractor conflict: the two F0 families disagree on the same signal
    conf_src = np.abs(R - RB) * 100.0 > CONFLICT_CENTS
    conf_src &= Rok & RBok
    conf_neu = np.abs(N - NB) * 100.0 > CONFLICT_CENTS
    conf_neu &= Nok & NBok
    conflict = conf_src | conf_neu

    # carrier: which note owns each frame; distance to nearest boundary
    note_idx = np.full(len(g), -1)
    edge_dist = np.full(len(g), np.inf)
    for i, n in enumerate(notes):
        s, e = n["abs_start_s"], n["abs_start_s"] + n["dur_s"]
        m = (g >= s) & (g < e)
        note_idx[m] = i
        edge_dist[m] = np.minimum(edge_dist[m],
                                  np.minimum(g[m] - s, e - g[m]) * 1000.0)
        # a boundary also shadows the 60ms before the note starts
        pre = (g >= s - TRANSITION_MS / 1000.0) & (g < s) & (note_idx == -1)
        edge_dist[pre] = np.minimum(edge_dist[pre],
                                    (s - g[pre]) * 1000.0)

    state = np.full(len(g), BOTH_UNVOICED)
    state[Rok & ~Nok] = SOURCE_ONLY_VOICED
    state[~Rok & Nok] = NEUTRAL_ONLY_VOICED
    state[Rok & Nok] = SAME_NOTE_BOTH_VOICED
    state[note_idx < 0] = GAP
    trans = edge_dist < TRANSITION_MS
    state[(state == SAME_NOTE_BOTH_VOICED) & trans] = NOTE_TRANSITION
    state[conflict] = EXTRACTOR_CONFLICT

    resid = np.where(state == SAME_NOTE_BOTH_VOICED, (R - N) * 100.0, np.nan)
    resid_t = np.where(state == NOTE_TRANSITION, (R - N) * 100.0, np.nan)
    # residual beyond sanity range is extractor junk even if states agree
    bad = np.abs(np.nan_to_num(resid, nan=0.0)) > MAX_RESID_CENTS
    bad |= np.abs(np.nan_to_num(resid_t, nan=0.0)) > MAX_RESID_CENTS
    state[bad & (state != GAP)] = EXTRACTOR_CONFLICT
    resid[bad] = np.nan
    resid_t[bad] = np.nan

    # plan §8.1 residual consensus: compare what each extractor family
    # says the correction should be — not raw F0 agreement
    r_rmvpe = np.where(RBok & NBok, (RB - NB) * 100.0, np.nan)
    eligible = (state == SAME_NOTE_BOTH_VOICED) | (state == NOTE_TRANSITION)
    r_fcpe = np.where(eligible, np.where(~np.isnan(resid), resid,
                                         resid_t), np.nan)
    disagree = np.abs(r_fcpe - r_rmvpe)
    consistent = (~np.isnan(r_fcpe)) & (~np.isnan(r_rmvpe)) \
        & (disagree <= CONSENSUS_CENTS)
    consensus = np.where(consistent,
                         np.nanmean(np.stack([r_fcpe, r_rmvpe]), axis=0),
                         np.nan)

    return {"times": g, "residual": resid, "residual_transition": resid_t,
            "state": state, "note_idx": note_idx, "edge_dist_ms": edge_dist,
            "src_midi": np.where(Rok, R, np.nan),
            "neu_midi": np.where(Nok, N, np.nan),
            "src_voiced": Rok, "neu_voiced": Nok,
            "r_fcpe": r_fcpe, "r_rmvpe": r_rmvpe,
            "resid_disagree": disagree, "resid_consensus": consensus,
            "resid_consistent": consistent}


# ---------------------------------------------------------------- C0
def compile_C0(dense, part_pos_tick):
    """Dense residual, no simplification: every eligible 10ms frame.

    Eligible = same_note_both_voiced AND note_transition (kept, not forced
    to zero — transitions are real residual evidence per plan §10.2).
    """
    g = dense["times"]
    r = np.where(dense["state"] == SAME_NOTE_BOTH_VOICED,
                 dense["residual"], np.nan)
    rt = np.where(dense["state"] == NOTE_TRANSITION,
                  dense["residual_transition"], np.nan)
    vals = np.where(~np.isnan(r), r, rt)
    ok = ~np.isnan(vals)
    xs = np.round(g[ok] * 1000.0 / TICK_MS - part_pos_tick).astype(int)
    ys = np.clip(np.round(vals[ok]), -1150, 1150).astype(int)
    keep = np.concatenate([[True], np.diff(xs) > 0])
    return {"abbr": "pitd", "xs": xs[keep].tolist(),
            "ys": ys[keep].tolist()}


# ---------------------------------------------------------------- C1
def _vertical_simplify(t, y, max_err_c, protect_mask=None):
    """Greedy insertion: keep points until linear interp error <= max_err_c.

    Error is measured in cents vertically — not a mixed-unit distance.
    protect_mask marks indices that must be kept (event keypoints).
    """
    keep = np.zeros(len(t), dtype=bool)
    keep[0] = keep[-1] = True
    if protect_mask is not None:
        keep |= protect_mask
    while True:
        idx = np.where(keep)[0]
        interp = np.interp(t, t[idx], y[idx])
        err = np.abs(interp - y)
        err[keep] = 0.0
        i = int(np.argmax(err))
        if err[i] <= max_err_c:
            break
        keep[i] = True
    return keep


def compile_C1(dense, notes, part_pos_tick, max_err_c=10.0):
    """Event-aware compiled residual.

    - eligible frames: both-voiced body + transition residual evidence;
    - forced-zero anchors REMOVED (plan §10.2): curve only exists where
      residual evidence exists — no note-boundary reset;
    - keypoint protection: local extrema and sign changes inside each
      note's transition zone are preserved through simplification;
    - vertical-cents error-bounded simplifier (plan §10.1).
    """
    g, st = dense["times"], dense["state"]
    r = np.where(st == SAME_NOTE_BOTH_VOICED, dense["residual"], np.nan)
    rt = np.where(st == NOTE_TRANSITION,
                  dense["residual_transition"], np.nan)
    vals = np.where(~np.isnan(r), r, rt)

    xs_all, ys_all = [], []
    # contiguous eligible segments
    ok = ~np.isnan(vals)
    i = 0
    while i < len(g):
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(g) and ok[j + 1] and g[j + 1] - g[j] < 0.015:
            j += 1
        seg_t, seg_y = g[i:j + 1], vals[i:j + 1]
        if len(seg_t) >= 3:
            # protect extrema + steep points inside the segment
            d1 = np.diff(seg_y)
            ext = np.zeros(len(seg_y), dtype=bool)
            ext[1:-1] = (d1[:-1] * d1[1:] < 0)
            steep = np.zeros(len(seg_y), dtype=bool)
            steep[1:] = np.abs(d1) > 40.0
            steep[:-1] |= np.abs(d1) > 40.0
            keep = _vertical_simplify(seg_t, seg_y, max_err_c,
                                      protect_mask=ext | steep)
            xs_all.extend(seg_t[keep])
            ys_all.extend(seg_y[keep])
        elif len(seg_t) > 0:
            xs_all.extend(seg_t)
            ys_all.extend(seg_y)
        i = j + 1

    xs = np.round(np.asarray(xs_all) * 1000.0 / TICK_MS
                  - part_pos_tick).astype(int)
    ys = np.clip(np.round(np.asarray(ys_all)), -1150, 1150).astype(int)
    order = np.argsort(xs, kind="stable")
    xs, ys = xs[order], ys[order]
    keep = np.concatenate([[True], np.diff(xs) > 0])
    return {"abbr": "pitd", "xs": xs[keep].tolist(),
            "ys": ys[keep].tolist()}


# ---------------------------------------------------------------- events
def detect_vibrato(dense, notes, min_note_s=0.55, tail_frac=0.45,
                   rate_lo=4.0, rate_hi=8.5, min_depth_c=15.0,
                   min_cycles=3):
    """Detect stable periodic vibrato on long notes from consensus residual.

    Returns list of event dicts; each is compiled to note `vibrato` params
    rather than PITD points (plan §9.5/§18.4-P3).
    """
    g = dense["times"]
    y = np.where(dense["resid_consistent"], dense["resid_consensus"],
                 dense["residual"])
    events = []
    for i, n in enumerate(notes):
        s, e = n["abs_start_s"], n["abs_start_s"] + n["dur_s"]
        if n["dur_s"] < min_note_s:
            continue
        v0 = s + n["dur_s"] * (1.0 - tail_frac) * 0.5  # start search mid-note
        m = (g >= v0) & (g <= e - 0.03)
        t, seg = g[m], y[m]
        ok = ~np.isnan(seg)
        if ok.sum() < 30:
            continue
        seg = np.interp(t, t[ok], seg[ok])
        # detrend slow intonation, keep 4-8Hz band content
        k = max(3, int(0.25 / 0.010))          # 250ms median-ish trend
        trend = np.convolve(seg, np.ones(k) / k, mode="same")
        res = seg - trend
        res[:k] = res[-k:] = 0.0
        # periodicity via autocorrelation on the tail half
        tail = res[len(res) // 3:]
        if np.std(tail) < 5.0:
            continue
        ac = np.correlate(tail - tail.mean(), tail - tail.mean(),
                          mode="full")[len(tail) - 1:]
        ac /= ac[0]
        lo, hi = int(1.0 / rate_hi / 0.010), int(1.0 / rate_lo / 0.010)
        if hi >= len(ac):
            continue
        lag = int(np.argmax(ac[lo:hi])) + lo
        period_s = lag * 0.010
        if ac[lag] < 0.45:                      # weak periodicity
            continue
        depth = float(np.percentile(np.abs(tail), 90))   # cents half-amp
        if depth < min_depth_c:
            continue
        n_cycles = (len(tail) * 0.010) / period_s
        if n_cycles < min_cycles:
            continue
        vib_start = v0 + (len(res) - len(tail)) * 0.010
        events.append({
            "type": "vibrato", "note_index": i, "lyric": n["lyric"],
            "start_s": round(float(vib_start), 3),
            "end_s": round(float(e), 3),
            "rate_hz": round(1.0 / period_s, 2),
            "depth_c": round(depth, 1),
            "period_stability": round(float(ac[lag]), 3),
            "confidence": "medium" if ac[lag] > 0.6 else "low",
        })
    return events


def compile_C2(dense, notes, part_pos_tick, events, max_err_c=10.0):
    """Residual-consensus + event-aware compiler (plan §18.4 C2).

    - only residual-consistent frames (both extractors agree on the
      correction within CONSENSUS_CENTS) enter PITD;
    - detected vibrato events are NOT drawn as PITD — returned in
      `vibrato_marks` for the caller to set note vibrato params;
    - vertical-cents simplifier only, no blind extrema/steep protection;
    - no forced-zero note boundaries.
    Returns (pitd_curve, vibrato_marks {note_index: params}).
    """
    g, st = dense["times"], dense["state"]
    vals = np.where(dense["resid_consistent"], dense["resid_consensus"],
                    np.nan)

    vibrato_marks = {}
    vib_mask = np.zeros(len(g), dtype=bool)
    for ev in events:
        if ev["type"] != "vibrato":
            continue
        i = ev["note_index"]
        n = notes[i]
        # note vibrato: length = fraction of note covered, period ms,
        # depth cents — OpenUtau semantics
        length_pct = min(100.0, max(5.0,
                         (ev["end_s"] - ev["start_s"]) / n["dur_s"] * 100.0))
        vibrato_marks[i] = {"length": round(length_pct, 1),
                            "period": round(1000.0 / ev["rate_hz"], 1),
                            "depth": round(ev["depth_c"], 1),
                            "in": 10, "out": 10, "shift": 0,
                            "drift": 0, "volLink": 0}
        vib_mask |= (g >= ev["start_s"]) & (g <= ev["end_s"])
    vals = np.where(vib_mask, np.nan, vals)

    xs_all, ys_all = [], []
    ok = ~np.isnan(vals)
    i = 0
    while i < len(g):
        if not ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(g) and ok[j + 1] and g[j + 1] - g[j] < 0.015:
            j += 1
        seg_t, seg_y = g[i:j + 1], vals[i:j + 1]
        if len(seg_t) >= 3:
            keep = _vertical_simplify(seg_t, seg_y, max_err_c)
            xs_all.extend(seg_t[keep])
            ys_all.extend(seg_y[keep])
        else:
            xs_all.extend(seg_t)
            ys_all.extend(seg_y)
        i = j + 1

    xs = np.round(np.asarray(xs_all) * 1000.0 / TICK_MS
                  - part_pos_tick).astype(int)
    ys = np.clip(np.round(np.asarray(ys_all)), -1150, 1150).astype(int)
    order = np.argsort(xs, kind="stable")
    xs, ys = xs[order], ys[order]
    keep = np.concatenate([[True], np.diff(xs) > 0])
    return {"abbr": "pitd", "xs": xs[keep].tolist(),
            "ys": ys[keep].tolist()}, vibrato_marks


def state_summary(dense):
    from collections import Counter
    names = {0: "both_voiced", 1: "src_only", 2: "neu_only", 3: "unvoiced",
             4: "extractor_conflict", 5: "note_transition", 6: "gap"}
    c = Counter(dense["state"].tolist())
    return {names[k]: v for k, v in sorted(c.items())}
