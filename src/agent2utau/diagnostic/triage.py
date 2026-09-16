"""M2.3 residual-error triage.

1. pick_baseline: medoid GAME run (min total pairwise-alignment cost)
   — a REAL run, Candidate 0 for all later repair.
2. detect_plateaus: stable structural-F0 plateaus inside a note window
   (contiguous finite runs with <=50c internal steps).
3. classify: per-note triage into
   GAME_LIKELY_CORRECT / F0_EXTRACTOR_CONFLICT / PITCH_HARD_SUSPICIOUS /
   STRUCTURE_HARD_SUSPICIOUS / AMBIGUOUS_ORNAMENT / NEEDS_LISTENING_REVIEW
"""

from __future__ import annotations

import numpy as np

from .seqalign import align_pair, GAP, SPLIT_MERGE_PEN, _mcost, _voiced

PLATEAU_STEP_CENTS = 50.0      # intra-plateau frame-to-frame step
MIN_PLATEAU_S = 0.08           # plateaus shorter than this are transitions
PLATEAU_MERGE_GAP_S = 0.03
PITCH_SUSP_CENTS = 100.0
DUAL_F0_CONFLICT_CENTS = 100.0
STABLE_IQR_CENTS = 40.0


def _op_cost(op, A, B) -> float:
    if op[0] == "m":
        return _mcost(A[op[1]], B[op[2]])
    if op[0] in ("ga", "gb"):
        return GAP
    if op[0] == "s":
        return SPLIT_MERGE_PEN + _mcost(A[op[1]],
                                        _merged_pair(B, op[2]))
    return SPLIT_MERGE_PEN + _mcost(_merged_pair(A, op[1]), B[op[2]])


def _merged_pair(seq, idx):
    from .seqalign import _merged
    return _merged(seq[idx[0]], seq[idx[1]])


def pick_baseline(runs: list[list[dict]]) -> dict:
    """Medoid run: minimal summed pairwise-alignment cost across all runs.
    Returns {'index': int, 'total_cost': float, 'costs': [...]}."""
    n = len(runs)
    costs = np.zeros(n)
    for i in range(n):
        for j in range(i + 1, n):
            ops, A, B = align_pair(runs[i], runs[j])
            c = sum(_op_cost(op, A, B) for op in ops)
            costs[i] += c
            costs[j] += c
    best = int(np.argmin(costs))
    return {"index": best, "total_cost": round(float(costs[best]), 3),
            "costs": [round(float(c), 3) for c in costs]}


def detect_plateaus(times: np.ndarray, struct: np.ndarray,
                    t0: float, t1: float) -> list[dict]:
    """Stable pitch plateaus within [t0,t1] on the structural contour.
    A plateau = contiguous voiced run whose internal step stays
    <= PLATEAU_STEP_CENTS; runs shorter than MIN_PLATEAU_S are dropped
    (transitions), neighbours separated by < PLATEAU_MERGE_GAP_S merge."""
    m = (times >= t0) & (times < t1)
    ts, vs = times[m], struct[m]
    fin = np.isfinite(vs)
    plats: list[dict] = []
    i = 0
    while i < len(vs):
        if not fin[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(vs) and fin[j + 1] and \
                abs(vs[j + 1] - vs[j]) * 100 <= PLATEAU_STEP_CENTS:
            j += 1
        dur = float(ts[j] - ts[i])
        if dur >= MIN_PLATEAU_S:
            seg = vs[i:j + 1]
            plats.append({"start": round(float(ts[i]), 3),
                          "end": round(float(ts[j]), 3),
                          "dur": round(dur, 3),
                          "center_midi": round(float(np.median(seg)), 2),
                          "iqr_cents": round(float(
                              (np.percentile(seg, 75)
                               - np.percentile(seg, 25)) * 100), 1)})
        i = j + 1
    merged: list[dict] = []
    for p in plats:
        if (merged and p["start"] - merged[-1]["end"] < PLATEAU_MERGE_GAP_S
                and abs(p["center_midi"] - merged[-1]["center_midi"]) < 0.5):
            q = merged[-1]
            w = q["dur"] + p["dur"]
            q["center_midi"] = round(
                (q["center_midi"] * q["dur"] + p["center_midi"] * p["dur"])
                / w, 2)
            q["end"], q["dur"] = p["end"], round(w, 3)
        else:
            merged.append(dict(p))
    return merged


def classify(packet: dict, plateaus: list[dict]) -> str:
    """packet: evidence packet (flags, rmvpe/fcpe blocks, dual_f0,
    consensus). plateaus: plateau list inside the note window."""
    cons = packet.get("consensus") or {}
    dual = packet.get("dual_f0") or {}
    flags = set(packet["flags"])
    rmv_ok = (packet.get("rmvpe") or {}).get("center_midi") is not None
    fcp_ok = (packet.get("fcpe") or {}).get("center_midi") is not None

    # extractor-vs-extractor conflict (e.g. 189.84s octave jump)
    if dual and abs(dual.get("rmvpe_vs_fcpe_cents") or 0) \
            > DUAL_F0_CONFLICT_CENTS:
        return "F0_EXTRACTOR_CONFLICT"

    # both extractors jointly oppose GAME with stable evidence
    if (dual.get("both_oppose_game")
            and (packet.get("rmvpe") or {}).get("iqr_cents", 1e9)
            <= STABLE_IQR_CENTS
            and (packet.get("fcpe") or {}).get("iqr_cents", 1e9)
            <= STABLE_IQR_CENTS):
        return "PITCH_HARD_SUSPICIOUS"

    # structure disagreement + clear plateau evidence either way
    if cons.get("structure_varies"):
        n_pl = len(plateaus)
        spread = (max(p["center_midi"] for p in plateaus)
                  - min(p["center_midi"] for p in plateaus)) \
            if len(plateaus) >= 2 else 0.0
        if n_pl >= 2 and spread > 1.0 and rmv_ok and fcp_ok:
            return "STRUCTURE_HARD_SUSPICIOUS"
        if dual.get("extractors_agree") and n_pl == 1:
            # GAME splits a region F0 says is one plateau
            if max(c for c in cons.get("run_note_counts", [1])) >= 2:
                return "STRUCTURE_HARD_SUSPICIOUS"
        return "AMBIGUOUS_ORNAMENT"

    if "wrong_pitch" in flags or "possible_octave_error" in flags:
        # flagged by one extractor but not dual-confirmed
        return "NEEDS_LISTENING_REVIEW"
    if flags & {"weak_f0_evidence"} and cons.get("stability") == (
            "GAME_UNSTABLE"):
        return "AMBIGUOUS_ORNAMENT"
    if flags - {"high_dispersion"}:
        return "NEEDS_LISTENING_REVIEW"
    if cons.get("stability") == "GAME_UNSTABLE":
        return "AMBIGUOUS_ORNAMENT"
    return "GAME_LIKELY_CORRECT"
