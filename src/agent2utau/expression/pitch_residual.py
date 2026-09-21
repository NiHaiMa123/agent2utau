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

CONFLICT_CENTS = 300.0      # fcpe-vs-rmvpe disagreement threshold
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

    return {"times": g, "residual": resid, "residual_transition": resid_t,
            "state": state, "note_idx": note_idx, "edge_dist_ms": edge_dist,
            "src_midi": np.where(Rok, R, np.nan),
            "neu_midi": np.where(Nok, N, np.nan),
            "src_voiced": Rok, "neu_voiced": Nok}


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


def state_summary(dense):
    from collections import Counter
    names = {0: "both_voiced", 1: "src_only", 2: "neu_only", 3: "unvoiced",
             4: "extractor_conflict", 5: "note_transition", 6: "gap"}
    c = Counter(dense["state"].tolist())
    return {names[k]: v for k, v in sorted(c.items())}
