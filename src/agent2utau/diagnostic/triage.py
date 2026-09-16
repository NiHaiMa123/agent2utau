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
PLATEAU_MATCH_CENTS = 60.0     # plateau center vs extractor center
SAFE_MIN_ERR_CENTS = 300.0     # both extractors must oppose GAME by this


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


def interior_center(times: np.ndarray, struct: np.ndarray,
                    t0: float, t1: float) -> float | None:
    """Median of the structural contour over the note's interior 60% —
    robust against onset/offset transition smear that inflates the
    full-window median error in vibrato/legato regions."""
    span = t1 - t0
    lo, hi = t0 + 0.2 * span, t1 - 0.2 * span
    m = (times >= lo) & (times < hi)
    sv = struct[m]
    sv = sv[np.isfinite(sv)]
    return float(np.median(sv)) if len(sv) >= 3 else None


def dual_structure_evidence(rmvpe_pl: list[dict], fcpe_pl: list[dict]
                            ) -> dict:
    """Plan §18: dual-extractor structure agreement for a window."""
    n_r, n_f = len(rmvpe_pl), len(fcpe_pl)
    ev = {"rmvpe_plateaus": rmvpe_pl, "fcpe_plateaus": fcpe_pl,
          "plateau_count_agreement": n_r == n_f,
          "plateau_pitch_agreement": None,
          "changepoint_time_delta_ms": None}
    if n_r and n_r == n_f:
        diffs = [abs(a["center_midi"] - b["center_midi"]) * 100
                 for a, b in zip(rmvpe_pl, fcpe_pl)]
        ev["plateau_pitch_agreement"] = bool(
            max(diffs) <= PLATEAU_MATCH_CENTS)
        if n_r >= 2:
            cr = [rmvpe_pl[i]["start"] for i in range(1, n_r)]
            cf = [fcpe_pl[i]["start"] for i in range(1, n_f)]
            ev["changepoint_time_delta_ms"] = round(
                max(abs(a - b) for a, b in zip(cr, cf)) * 1000, 1)
    return ev


def safe_retune_gate(packet: dict, plateaus: list[dict],
                     neighbours: list[dict]) -> dict:
    """Plan §15 SAFE_RETUNE_CANDIDATE gate. Gates 14/15 (render preview,
    human listening) are produced downstream and marked 'pending'."""
    cons = packet.get("consensus") or {}
    dual = packet.get("dual_f0") or {}
    rmv, fcp = packet.get("rmvpe") or {}, packet.get("fcpe") or {}
    plat_centers = [p["center_midi"] for p in plateaus]
    tone = packet["game_tone"]
    gates = {
        "presence_5of5": cons.get("presence_rate", 0) >= 1.0,
        "tone_agreement_high": cons.get("tone_agreement", 0) >= 0.8,
        "no_structure_ambiguity": not cons.get("structure_varies", True),
        "aligned_identity_clear": cons.get("stability") == "GAME_STABLE",
        "extractor_centers_close": dual.get("extractors_agree", False),
        "rmvpe_iqr_low": (rmv.get("iqr_cents") or 1e9) <= STABLE_IQR_CENTS,
        "fcpe_iqr_low": (fcp.get("iqr_cents") or 1e9) <= STABLE_IQR_CENTS,
        "both_oppose_game_strong": dual.get("both_oppose_game", False)
            and min(abs(dual.get("game_vs_rmvpe_cents") or 0),
                    abs(dual.get("game_vs_fcpe_cents") or 0))
            >= SAFE_MIN_ERR_CENTS,
        "single_stable_plateau": len(plateaus) == 1,
        "plateau_matches_extractors": bool(
            plat_centers and rmv.get("center_midi") is not None
            and abs(plat_centers[0] - rmv["center_midi"]) * 100
            <= PLATEAU_MATCH_CENTS),
        # neighbours must not sit at the extractor pitch — otherwise the
        # 'error' may be a legit melodic skip GAME heard correctly
        "neighbours_no_alternative": all(
            abs(nb["game_tone"] - (rmv.get("center_midi") or tone))
            > 0.5 for nb in neighbours),
        "pitch_only_edit": True,  # retune touches tone only, by design
        "render_preview": "pending",
        "human_listening": "pending",
    }
    hard = [k for k, v in gates.items()
            if v is False and k not in ("render_preview",
                                       "human_listening")]
    return {"gates": gates, "failed": hard,
            "eligible": not hard,
            "status": ("awaiting_render_and_listening" if not hard
                       else "rejected")}


def classify(packet: dict, plateaus: list[dict],
             interior: float | None = None) -> str:
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
            return "STRUCTURE_CANDIDATE"
        if dual.get("extractors_agree") and n_pl == 1:
            # GAME splits a region F0 says is one plateau
            if max(c for c in cons.get("run_note_counts", [1])) >= 2:
                return "STRUCTURE_CANDIDATE"
        return "AMBIGUOUS_ORNAMENT"

    if "wrong_pitch" in flags or "possible_octave_error" in flags:
        # §20: re-judge via plateau/interior center, not the full-window
        # median — vibrato/transition smear inflates err_cents.
        center = None
        if plateaus:
            # plateau nearest the GAME tone
            center = min(plateaus,
                         key=lambda p: abs(p["center_midi"]
                                           - packet["game_tone"])
                         )["center_midi"]
        elif interior is not None:
            center = interior
        if center is not None:
            if abs(center - packet["game_tone"]) * 100 \
                    <= PLATEAU_MATCH_CENTS:
                return "GAME_LIKELY_CORRECT"   # median was smeared
            if dual.get("extractors_agree") \
                    and abs(center - packet["game_tone"]) * 100 \
                    > PITCH_SUSP_CENTS:
                return "NEEDS_LISTENING_REVIEW"
        return "AMBIGUOUS_ORNAMENT"
    if flags & {"weak_f0_evidence"} and cons.get("stability") == (
            "GAME_UNSTABLE"):
        return "AMBIGUOUS_ORNAMENT"
    if flags - {"high_dispersion"}:
        return "NEEDS_LISTENING_REVIEW"
    if cons.get("stability") == "GAME_UNSTABLE":
        return "AMBIGUOUS_ORNAMENT"
    return "GAME_LIKELY_CORRECT"
