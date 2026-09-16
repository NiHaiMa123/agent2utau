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


def _op_cost(op, A, B, pitch_w: float = 0.15) -> float:
    if op[0] == "m":
        return _mcost(A[op[1]], B[op[2]], pitch_w)
    if op[0] in ("ga", "gb"):
        return GAP
    if op[0] == "s":
        return SPLIT_MERGE_PEN + _mcost(A[op[1]],
                                        _merged_pair(B, op[2]), pitch_w)
    return SPLIT_MERGE_PEN + _mcost(_merged_pair(A, op[1]), B[op[2]],
                                    pitch_w)


def _merged_pair(seq, idx):
    from .seqalign import _merged
    return _merged(seq[idx[0]], seq[idx[1]])


def pick_baseline(runs: list[list[dict]], pitch_w: float = 0.15) -> dict:
    """Medoid run: minimal summed pairwise-alignment cost across all runs.
    pitch_w=0 -> structure-only medoid (plan §5.7 sensitivity check).
    Returns {'index': int, 'total_cost': float, 'costs': [...]}."""
    n = len(runs)
    costs = np.zeros(n)
    for i in range(n):
        for j in range(i + 1, n):
            ops, A, B = align_pair(runs[i], runs[j], pitch_w=pitch_w)
            c = sum(_op_cost(op, A, B, pitch_w) for op in ops)
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
        # frame-inclusive: N frames cover N*frame_period; end = start+dur
        # so end-start == dur (plan §5.1 — overlap ratio depends on it)
        frame_p = float(ts[1] - ts[0]) if len(ts) > 1 else 0.01
        dur = (j - i + 1) * frame_p
        if dur >= MIN_PLATEAU_S:
            seg = vs[i:j + 1]
            plats.append({"start": round(float(ts[i]), 3),
                          "end": round(float(ts[i]) + dur, 3),
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


def _target_plateau(plateaus: list[dict], target_midi: float) -> dict | None:
    """The plateau (if any) whose center supports `target_midi`."""
    for p in plateaus:
        if abs(p["center_midi"] - target_midi) * 100 <= PLATEAU_MATCH_CENTS:
            return p
    return None


def safe_retune_gate(packet: dict, rmvpe_plateaus: list[dict],
                     fcpe_plateaus: list[dict],
                     neighbours: list[dict],
                     target_midi: float | None = None) -> dict:
    """Plan §15 SAFE_RETUNE_CANDIDATE gate (M2.3.1), with §5.3/5.4 fix:
    the plateau support must come from TWO INDEPENDENT extractors —
    an RMVPE plateau + RMVPE center is one evidence family, not two.

    §9.6 (B2): `target_midi` is EXPLICIT — when called after a B
    resolved_change it must be pitch_adjudication.winning_hypothesis,
    not an implicit RMVPE-derived target. The gate then verifies that
    BOTH extractors' plateaus support that exact target."""
    cons = packet.get("consensus") or {}
    dual = packet.get("dual_f0") or {}
    rmv, fcp = packet.get("rmvpe") or {}, packet.get("fcpe") or {}
    target = (target_midi if target_midi is not None
              else rmv.get("center_midi"))
    rp = _target_plateau(rmvpe_plateaus, target) if target else None
    fp = _target_plateau(fcpe_plateaus, target) if target else None
    plateau_overlap = None
    if rp and fp:
        ov = (min(rp["end"], fp["end"]) - max(rp["start"], fp["start"]))
        union = max(rp["end"], fp["end"]) - min(rp["start"], fp["start"])
        plateau_overlap = round(ov / max(1e-9, union), 3)
    delta = (round(abs(rp["center_midi"] - fp["center_midi"]) * 100, 1)
             if rp and fp else None)
    tone = packet["game_tone"]
    gates = {
        "presence_5of5": cons.get("presence_rate", 0) >= 1.0,
        "tone_agreement_high": cons.get("tone_agreement", 0) >= 0.8,
        # §8.7 (C2): the FINALIZED C result owns this gate — a confident
        # C resolved_keep must not be permanently blocked by the raw
        # historical structure_varies flag (kept in audit).
        "no_structure_ambiguity":
            packet.get("final_structure_clear", False)
            or not cons.get("structure_varies", True),
        "aligned_identity_clear": cons.get("stability") == "GAME_STABLE",
        "extractor_centers_close": dual.get("extractors_agree", False),
        "rmvpe_iqr_low": (rmv.get("iqr_cents") or 1e9) <= STABLE_IQR_CENTS,
        "fcpe_iqr_low": (fcp.get("iqr_cents") or 1e9) <= STABLE_IQR_CENTS,
        "both_oppose_game_strong": dual.get("both_oppose_game", False)
            and min(abs(dual.get("game_vs_rmvpe_cents") or 0),
                    abs(dual.get("game_vs_fcpe_cents") or 0))
            >= SAFE_MIN_ERR_CENTS,
        # §5.2: BOTH extractors must have a unique stable plateau
        "single_stable_plateau": (len(rmvpe_plateaus) == 1
                                  and len(fcpe_plateaus) == 1),
        "rmvpe_plateau_supports": rp is not None,
        "fcpe_plateau_supports": fp is not None,
        "dual_plateau_agree": (delta is not None
                               and delta <= PLATEAU_MATCH_CENTS),
        # §5.2: the two plateaus must actually overlap in time — merely
        # both containing the target pitch somewhere isn't agreement
        "plateau_temporal_overlap": (plateau_overlap is not None
                                    and plateau_overlap >= 0.5),
        "neighbours_no_alternative": all(
            abs(nb["game_tone"] - (target or tone))
            > 0.5 for nb in neighbours),
        "pitch_only_edit": True,
        "render_preview": "pending",
        "human_listening": "pending",
    }
    hard = [k for k, v in gates.items()
            if v is False and k not in ("render_preview",
                                       "human_listening")]
    return {"gates": gates, "failed": hard,
            "rmvpe_target_plateau": rp, "fcpe_target_plateau": fp,
            "plateau_center_delta_cents": delta,
            "plateau_overlap_ratio": plateau_overlap,
            "eligible": not hard,
            "status": ("awaiting_render_and_listening" if not hard
                       else "rejected")}


def orthogonal_states(packet: dict) -> dict:
    """§5.4: a region can be simultaneously pitch-conflicted AND
    structure-unstable — one `triage` label hid that. Orthogonal states
    + a routing `decision`; legacy `triage` stays as a compat summary."""
    cons = packet.get("consensus") or {}
    sep = packet.get("separation") or {}

    pitch = pitch_state_from_evidence(packet)

    if cons.get("structure_varies"):
        structure = ("candidate" if packet.get("structure_evidence")
                     else "split_merge_variable")
    else:
        structure = "stable"

    # A4: identity_state reflects GAME's TONE answer stability only —
    # split/merge variation belongs to structure_state, not identity.
    # (202.52s: runs answer 65.3 vs 72.4 -> tone_agreement<1 -> variable.)
    identity = ("variable" if cons.get("tone_agreement", 1.0) < 1.0
                else "stable")

    separation = ("sensitive" if sep.get("separation_sensitive")
                  else ("normal" if sep else "unknown"))

    # §5.2 (A4): orthogonal routing needs — a region can need pitch AND
    # structure adjudication at once; `decision` is only the next step.
    # phrase_review is reserved for B/C-unresolved outcomes; nothing in
    # the A stage may route straight to human review.
    needs = {
        "pitch_adjudication": pitch in ("extractor_conflict", "suspicious",
                                        "unresolved")
                              or identity == "variable",
        "structure_adjudication": structure in ("split_merge_variable",
                                                "candidate"),
        "phrase_review": bool(packet.get("b_c_unresolved")),
    }

    # §5.3 (A3): SAFE gate passed = eligible for adjudication, NOT auto
    # repair — third-F0/harmonic layer (M2.3.2B) must confirm first.
    if (packet.get("safe_gate") or {}).get("eligible"):
        decision = "candidate_pending_adjudication"
    elif needs["pitch_adjudication"]:
        decision = "needs_pitch_adjudication"
    elif needs["structure_adjudication"]:
        decision = "needs_structure_adjudication"
    elif needs["phrase_review"]:
        decision = "needs_phrase_review"
    else:
        decision = "keep_baseline"

    return {"pitch_state": pitch, "structure_state": structure,
            "identity_state": identity, "separation_state": separation,
            "routing_needs": needs, "decision": decision}


def pitch_state_from_evidence(packet: dict) -> str:
    """§5.3 (A4): pitch_state is derived from raw + calibrated evidence —
    never from the legacy `triage` enum. Raw full-window flags are
    re-judged here via plateau/interior centers (same calibration
    `classify` uses), so a stale `wrong_pitch` cannot resurrect a
    suspicious state on an already-cleared note."""
    dual = packet.get("dual_f0") or {}
    flags = set(packet.get("flags") or [])
    plats = packet.get("plateaus") or []
    interior = packet.get("interior_center_midi")

    if dual and abs(dual.get("rmvpe_vs_fcpe_cents") or 0) \
            > DUAL_F0_CONFLICT_CENTS:
        return "extractor_conflict"
    if (dual.get("both_oppose_game")
            and (packet.get("rmvpe") or {}).get("iqr_cents", 1e9)
            <= STABLE_IQR_CENTS
            and (packet.get("fcpe") or {}).get("iqr_cents", 1e9)
            <= STABLE_IQR_CENTS):
        return "suspicious"
    if flags & {"wrong_pitch", "possible_octave_error"}:
        center = None
        if plats:
            center = min(plats,
                         key=lambda p: abs(p["center_midi"]
                                           - packet["game_tone"])
                         )["center_midi"]
        elif interior is not None:
            center = interior
        if center is not None:
            delta_c = abs(center - packet["game_tone"]) * 100
            if delta_c <= PLATEAU_MATCH_CENTS:
                return "stable"          # median was smeared, calibrated
            if dual.get("extractors_agree") and delta_c > PITCH_SUSP_CENTS:
                return "suspicious"
        return "unresolved"
    if "weak_f0_evidence" in flags:
        return "unresolved"
    return "stable"


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

    # structure ambiguity gates FIRST: an unstable-identity region can
    # never be pitch-hard regardless of F0 stability (plan §5.1)
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

    # both extractors jointly oppose GAME with stable evidence
    if (dual.get("both_oppose_game")
            and (packet.get("rmvpe") or {}).get("iqr_cents", 1e9)
            <= STABLE_IQR_CENTS
            and (packet.get("fcpe") or {}).get("iqr_cents", 1e9)
            <= STABLE_IQR_CENTS):
        return "PITCH_HARD_SUSPICIOUS"

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
