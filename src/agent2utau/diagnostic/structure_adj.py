"""M2.3.2C2: automatic structure adjudication — correctness/calibration.

Stage 1 produces adjudication results ONLY — no automatic split/merge/
boundary repair. Candidate 0 is never touched.

C2 corrections over C1 (plan2 §8):
  - two plateaus != split support: per-extractor evidence carries
    pre/post center, pitch delta, boundary time, stability; dual-F0
    agreement is computed on RELATIVE deltas (octave-offset invariant)
  - TRUE_SPLIT needs (A) strong GAME split support + acoustic
    confirmation, or (B) dual-F0 relative-delta agreement + >=1
    non-F0 boundary family. F0-only changepoint cannot auto-split.
  - energy evidence is candidate-boundary-local, not whole-note min/mean
  - merge support comes from explicit per-run member spans crossing
    the shared boundary — never from run_note_counts == 0
  - C resolved_change_candidate -> virtual notes -> frozen B rerun
    (handled by run.py via the returned hypothesis_detail)
  - C resolved_keep sets final_structure_clear; the finalized result
    owns downstream gates, raw structure_varies stays in audit.
"""

from __future__ import annotations

import numpy as np

# --- parametrized thresholds (§8.3: no scattered magic numbers) -------
MIN_STRUCTURE_DELTA_ST = 0.7        # meaningful written-note pitch step
DELTA_FULL_SUPPORT_ST = 1.5         # delta giving full extractor support
DELTA_MAGNITUDE_AGREE_ST = 1.0      # cross-extractor |delta| tolerance
CHANGEPOINT_AGREE_S = 0.08          # boundary-time agreement window
LONG_NOTE_S = 1.0
SHORT_NOTE_S = 0.07
MIN_SPLIT_DUR_S = 0.05
PLATEAU_MATCH_ST = 0.5
GAME_SPLIT_STRONG = 0.4             # >=40% runs split -> strong support
BOUNDARY_HALF_WIN_S = 0.06          # boundary-local window half-width
BOUNDARY_CTX_S = 0.20               # pre/post reference context width
NONF0_BOUNDARY_THR = 0.3            # non-F0 family support threshold
GROUP_THR = 0.2
MIN_MARGIN = 0.15
MIN_GROUPS = 2


# ---------------------------------------------------------------------
# §8.3 per-extractor structure evidence
# ---------------------------------------------------------------------

def _extractor_evidence(pls: list[dict]) -> dict | None:
    """First two plateaus -> structured evidence object."""
    if len(pls) < 2:
        return None
    return {"pre_plateau_center": pls[0]["center_midi"],
            "post_plateau_center": pls[1]["center_midi"],
            "pitch_delta_st": round(pls[1]["center_midi"]
                                    - pls[0]["center_midi"], 3),
            "boundary_time": pls[1]["start"],
            "pre_dur": pls[0]["dur"], "post_dur": pls[1]["dur"],
            "pre_iqr_cents": pls[0].get("iqr_cents"),
            "post_iqr_cents": pls[1].get("iqr_cents")}


def _dual_delta(ev_r: dict | None, ev_f: dict | None) -> dict:
    """Cross-extractor relative-delta agreement — octave-offset
    invariant: deltas are relative, so +3.0st vs +3.1st agree even if
    the extractors are an octave apart globally."""
    if not ev_r or not ev_f:
        return {}
    dr, df = ev_r["pitch_delta_st"], ev_f["pitch_delta_st"]
    return {
        "delta_rmvpe_st": dr, "delta_fcpe_st": df,
        "direction_agreement": (dr > 0) == (df > 0),
        "magnitude_difference_st": round(abs(abs(dr) - abs(df)), 3),
        "boundary_time_delta_ms":
            round(abs(ev_r["boundary_time"] - ev_f["boundary_time"])
                  * 1000, 1),
    }


def _split_support(ev: dict | None) -> float:
    """Graded extractor split support: meaningful delta + both plateaus
    stable & long enough. Two plateaus alone -> 0."""
    if ev is None:
        return 0.0
    mag = abs(ev["pitch_delta_st"])
    if mag < MIN_STRUCTURE_DELTA_ST:
        return 0.0
    mag_s = min(1.0, mag / DELTA_FULL_SUPPORT_ST)
    dur_s = min(1.0, min(ev["pre_dur"], ev["post_dur"]) / 0.12)
    iqrs = [i for i in (ev["pre_iqr_cents"], ev["post_iqr_cents"])
            if i is not None]
    stab_s = (max(0.0, 1.0 - max(iqrs) / 200.0) if iqrs else 0.5)
    return round(mag_s * (0.4 + 0.6 * dur_s) * (0.6 + 0.4 * stab_s), 3)


# ---------------------------------------------------------------------
# §8.5 boundary-local acoustic evidence
# ---------------------------------------------------------------------

def _boundary_energy(times: np.ndarray, energy: np.ndarray, b: float,
                     t0: float, t1: float) -> dict:
    """Local minimum prominence + pre/post recovery around candidate
    boundary b. Without a candidate boundary there is no evidence."""
    h, c = BOUNDARY_HALF_WIN_S, BOUNDARY_CTX_S
    pre = energy[(times >= b - c - h) & (times < b - h)]
    post = energy[(times > b + h) & (times <= b + c + h)]
    loc = energy[(times >= b - h) & (times <= b + h)]
    if len(pre) < 3 or len(post) < 3 or len(loc) < 2:
        return {"dip_prominence": 0.0, "recovery": 0.0, "support": 0.0}
    ref = float(max(pre.mean(), post.mean()))
    if ref <= 1e-4:
        return {"dip_prominence": 0.0, "recovery": 0.0, "support": 0.0}
    dip = max(0.0, 1.0 - float(loc.min()) / ref)
    rec = float(min(pre.mean(), post.mean())) / ref
    sup = float(np.clip(dip * rec / 0.45, 0.0, 1.0))
    return {"dip_prominence": round(dip, 3), "recovery": round(rec, 3),
            "support": round(sup, 3)}


def _boundary_voiced_drop(times: np.ndarray, voiced: np.ndarray,
                          b: float) -> float:
    """Voiced-probability drop at the boundary (voiced->unvoiced->
    voiced re-attack evidence)."""
    if voiced is None:
        return 0.0
    m = (times >= b - BOUNDARY_HALF_WIN_S) & (times <= b
                                              + BOUNDARY_HALF_WIN_S)
    if not m.any():
        return 0.0
    return round(float(1.0 - voiced[m].mean()), 3)


# ---------------------------------------------------------------------
# discovery (§7.1B/7.2 + §8.5: wide but recorded; energy boundary-local)
# ---------------------------------------------------------------------

def discover_structure(packets: list[dict], times: np.ndarray,
                       energy: np.ndarray) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in packets:
        reasons = []
        pl_r, pl_f = p.get("plateaus") or [], p.get("fcpe_plateaus") or []
        ev_r, ev_f = _extractor_evidence(pl_r), _extractor_evidence(pl_f)

        if ev_r and ev_f:
            reasons.append("dual_f0_multi_plateau")
            if abs(ev_r["boundary_time"] - ev_f["boundary_time"]) \
                    <= CHANGEPOINT_AGREE_S:
                reasons.append("cross_extractor_changepoint")
        elif ev_r or ev_f:
            ev = ev_r or ev_f
            if abs(ev["pitch_delta_st"]) >= 1.0:
                reasons.append("single_extractor_transition")

        # boundary-local energy dip only when a candidate boundary exists
        b = _boundary_time(pl_r, pl_f, p["start"], p["start"] + p["dur"])
        if b is not None:
            be = _boundary_energy(times, energy, b, p["start"],
                                  p["start"] + p["dur"])
            if be["support"] > 0.25:
                reasons.append("boundary_energy_dip")

        if p["dur"] > LONG_NOTE_S and (ev_r or ev_f):
            reasons.append("long_note_multi_plateau")
        if p["dur"] < SHORT_NOTE_S:
            reasons.append("very_short_note")
        if reasons:
            out[p["id"]] = reasons
    return out


def _boundary_time(pl_r, pl_f, t0, t1):
    cands = [pl[1]["start"] for pl in (pl_r, pl_f) if len(pl) >= 2]
    if not cands:
        return None
    b = float(np.median(cands))
    return b if t0 + MIN_SPLIT_DUR_S <= b <= t1 - MIN_SPLIT_DUR_S else None


def hypotheses_structure(p: dict) -> dict:
    pl_r, pl_f = p.get("plateaus") or [], p.get("fcpe_plateaus") or []
    t0, t1 = p["start"], p["start"] + p["dur"]
    b = _boundary_time(pl_r, pl_f, t0, t1)
    hyps = {"H0": {"kind": "keep", "notes": [
        {"start": t0, "end": t1, "tone": p["game_tone"]}]}}
    if b is not None:
        hyps["H1"] = {"kind": "split", "boundary": round(b, 4),
                      "notes": [{"start": t0, "end": b},
                                {"start": b, "end": t1}]}
    hyps["H3"] = {"kind": "portamento"}
    return hyps


# ---------------------------------------------------------------------
# §8.6 merge evidence — explicit span correspondence only
# ---------------------------------------------------------------------

def _merge_evidence(p: dict, neighbors: list[dict]) -> tuple[float, dict | None]:
    """(acoustic_support, merged_span). Plateau continuity across the
    shared boundary suggests one underlying note."""
    if p["dur"] >= SHORT_NOTE_S:
        return 0.0, None
    pl = p.get("plateaus") or []
    if not pl:
        return 0.0, None
    for nb in neighbors or []:
        npl = nb.get("plateaus") or []
        if not npl:
            continue
        if (abs(pl[-1]["end"] - nb["start"]) < 0.05
                and abs(pl[-1]["center_midi"] - npl[0]["center_midi"])
                < PLATEAU_MATCH_ST):
            return 1.0, {"start": p["start"],
                         "end": nb["start"] + nb["dur"],
                         "merge_with": nb["id"]}
    return 0.0, None


def _game_merge_support(p: dict, neighbors: list[dict]) -> float:
    """Fraction of runs whose REAL GAME note crosses the shared
    boundary (explicit member spans), i.e. GAME itself merged i+j."""
    spans = (p.get("consensus") or {}).get("member_spans") or {}
    if not spans:
        return 0.0
    n_runs = int((p.get("consensus") or {}).get("n_runs")
                 or len(spans))
    boundary = None
    for nb in neighbors or []:
        if nb["start"] >= p["start"] + p["dur"] - 0.01:
            boundary = nb["start"]
            break
    if boundary is None:
        return 0.0
    hit = sum(1 for ms in spans.values()
              if any(s < boundary - 0.04 and e > boundary + 0.04
                     for s, e in ms))
    return round(hit / max(1, n_runs), 3)


# ---------------------------------------------------------------------
# adjudication (§7.3/7.4 + §8.3/8.4/8.5)
# ---------------------------------------------------------------------

def adjudicate_structure(p: dict, times: np.ndarray,
                       energy: np.ndarray,
                       discovery_reasons: list[str],
                       neighbors: list[dict] | None = None,
                       voiced: np.ndarray | None = None) -> dict:
    cons = p.get("consensus") or {}
    pl_r, pl_f = p.get("plateaus") or [], p.get("fcpe_plateaus") or []
    counts = cons.get("run_note_counts") or []
    n_runs = len(counts)
    t0, t1 = p["start"], p["start"] + p["dur"]

    ev_r, ev_f = _extractor_evidence(pl_r), _extractor_evidence(pl_f)
    dual = _dual_delta(ev_r, ev_f)
    sup_r, sup_f = _split_support(ev_r), _split_support(ev_f)
    b = _boundary_time(pl_r, pl_f, t0, t1)

    # dual-F0 relative-delta agreement (octave-offset invariant)
    dual_delta_agree = bool(
        dual and dual["direction_agreement"]
        and dual["magnitude_difference_st"] <= DELTA_MAGNITUDE_AGREE_ST
        and dual["boundary_time_delta_ms"] <= CHANGEPOINT_AGREE_S * 1000)

    # non-F0 boundary family (§8.4B/8.5): boundary-local energy
    # dip+recovery and/or voiced-probability drop
    be = (_boundary_energy(times, energy, b, t0, t1)
          if b is not None
          else {"dip_prominence": 0.0, "recovery": 0.0, "support": 0.0})
    vdrop = (_boundary_voiced_drop(times, voiced, b)
             if b is not None else 0.0)
    nonf0 = round(max(be["support"], vdrop), 3)

    game_one = (sum(1 for c in counts if c == 1) / n_runs
                if n_runs else 1.0)
    game_split = (sum(1 for c in counts if c >= 2) / n_runs
                  if n_runs else 0.0)

    # --- scores -------------------------------------------------------
    dur_plaus_h0 = 0.0 if p["dur"] < SHORT_NOTE_S else 1.0
    scored = {"H0": {"score": round(game_one + (1 - sup_r) + (1 - sup_f)
                                  + (1 - nonf0) + 0.5 * dur_plaus_h0, 3),
                     "groups": {"game": round(game_one, 3),
                                "rmvpe": round(1 - sup_r, 3),
                                "fcpe": round(1 - sup_f, 3),
                                "acoustic_boundary":
                                    round(1 - nonf0, 3)}}}
    hyps = hypotheses_structure(p)
    if "H1" in hyps:
        scored["H1"] = {"score": round(game_split + sup_r + sup_f
                                     + nonf0 + 0.5, 3),
                        "groups": {"game": round(game_split, 3),
                                   "rmvpe": sup_r, "fcpe": sup_f,
                                   "acoustic_boundary": nonf0}}
    # H3 portamento/ornament competes whenever pitch motion is real
    # (dual delta agree or any extractor delta) but boundary may be fake
    if ev_r or ev_f:
        scored["H3"] = {"score": round(game_one + (1 - nonf0) + 0.5
                                     + 0.5 * min(sup_r, sup_f), 3),
                        "groups": {"game": round(game_one, 3),
                                   "acoustic_boundary":
                                       round(1 - nonf0, 3)}}

    merge_sup, merge_span = _merge_evidence(p, neighbors or [])
    if merge_sup > 0:
        g_game_m = _game_merge_support(p, neighbors or [])
        g_fcp_m = 0.0
        for nb in neighbors or []:
            if merge_span and nb["id"] == merge_span["merge_with"]:
                nfpl = nb.get("fcpe_plateaus") or []
                if (nfpl and pl_f
                        and abs(pl_f[-1]["center_midi"]
                                - nfpl[0]["center_midi"])
                        < PLATEAU_MATCH_ST):
                    g_fcp_m = 1.0
        hyps["H2"] = {"kind": "merge", "span": merge_span}
        scored["H2"] = {"score": round(g_game_m + merge_sup + g_fcp_m
                                     + 0.5 * (1 - nonf0), 3),
                        "groups": {"game": round(g_game_m, 3),
                                   "rmvpe": merge_sup,
                                   "fcpe": round(g_fcp_m, 3),
                                   "acoustic_boundary":
                                       round(1 - nonf0, 3)}}
        # merge continuity also weakens the keep hypothesis
        scored["H0"]["score"] = round(
            scored["H0"]["score"] - merge_sup - g_fcp_m, 3)

    ranked = sorted(scored.items(), key=lambda kv: -kv[1]["score"])
    win_name, win = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else (None, {"score": 0.0})
    margin = round(win["score"] - runner[1]["score"], 3)
    hard_groups = [g for g, v in win["groups"].items() if v > GROUP_THR]

    # --- gates ---------------------------------------------------------
    reasons = []
    if len(hard_groups) < MIN_GROUPS:
        reasons.append("insufficient_structure_evidence")
    if margin < MIN_MARGIN:
        reasons.append("margin_too_small")
    # §8.4: TRUE_SPLIT requires (A) strong GAME split support +
    # acoustic confirmation, or (B) dual-F0 delta agreement + >=1
    # non-F0 boundary family. F0-only changepoint cannot auto-split.
    split_gate = ((game_split >= GAME_SPLIT_STRONG
                   and (dual_delta_agree or nonf0 > NONF0_BOUNDARY_THR))
                  or (dual_delta_agree and nonf0 > NONF0_BOUNDARY_THR))

    if reasons:
        cls, status = "UNRESOLVED_STRUCTURE", "unresolved"
    elif win_name == "H0":
        cls, status = ("ONE_NOTE_WITH_PORTAMENTO" if (ev_r or ev_f)
                       else "RESOLVED_KEEP"), "resolved_keep"
    elif win_name == "H1":
        if split_gate:
            cls, status = "TRUE_SPLIT_CANDIDATE", \
                "resolved_change_candidate"
        else:
            cls, status = "UNRESOLVED_STRUCTURE", "unresolved"
            reasons.append("split_gate_failed:no_independent_boundary")
    elif win_name == "H2":
        cls, status = "TRUE_MERGE_CANDIDATE", "resolved_change_candidate"
    elif win_name == "H3":
        cls = ("ONE_NOTE_WITH_PORTAMENTO"
               if min(sup_r, sup_f) > GROUP_THR else "GRACE_OR_ORNAMENT")
        status = "resolved_keep"
    else:
        cls, status = "UNRESOLVED_STRUCTURE", "unresolved"

    if status != "unresolved":
        if not pl_r and not pl_f and cons.get("structure_varies"):
            cls, status = "ALIGNMENT_ARTIFACT", "unresolved"
        elif not pl_r and not pl_f and not cons.get("structure_varies"):
            cls, status = "F0_ARTIFACT", "unresolved"

    return {"status": status, "classification": cls,
            "winning_hypothesis": win_name,
            "hypothesis_detail": hyps.get(win_name),
            "score": win["score"], "margin": margin,
            "supporting_groups": hard_groups,
            "reason": "+".join(reasons) if reasons else "converged",
            "discovery_reasons": discovery_reasons,
            "extractor_evidence": {"rmvpe": ev_r, "fcpe": ev_f,
                                   "dual_delta": dual,
                                   "dual_delta_agreement":
                                       dual_delta_agree},
            "boundary_evidence": {"energy": be,
                                  "voiced_drop": vdrop,
                                  "non_f0_support": nonf0},
            "game_structure": {"one_note_ratio": round(game_one, 3),
                               "split_ratio": round(game_split, 3)},
            "all_scores": {k: v["score"] for k, v in scored.items()},
            "boundary": hyps.get("H1", {}).get("boundary")}


# ---------------------------------------------------------------------
# §8 lifecycle (C2: change candidates spawn virtual notes + B rerun in
# run.py; here we only route state)
# ---------------------------------------------------------------------

def apply_structure(rec: dict, adj: dict,
                    b_gate: dict | None = None,
                    virtual_b: list[dict] | None = None) -> None:
    """Route a packet after C ran. Mutates rec['state'].

    resolved_keep             -> final_structure_clear=True; provisional
                               B finalized and its final result routed
                               (auto_resolved / gate-rechecked repair /
                               phrase_review).
    resolved_change_candidate -> old B invalidated; virtual notes and
                               their fresh B results recorded by caller;
                               phrase_review ONLY if any virtual B is
                               still unresolved (§8.1).
    unresolved                -> pending cleared (no C loop), review.
    """
    st = rec["state"]
    needs = st["routing_needs"]
    needs["structure_adjudication"] = False    # C ran once — no loop

    if adj["status"] == "resolved_keep":
        rec["final_structure_clear"] = True
        b = rec.get("pitch_adjudication") or {}
        if b.get("provisional"):
            b["provisional"] = False
            b["finalized_by"] = "structure_resolved_keep"
        if needs["pitch_adjudication"]:
            needs["pitch_adjudication"] = False
            bs = b.get("status", "")
            if bs == "resolved_change":
                if b_gate and b_gate.get("eligible"):
                    rec["repair_gate"] = b_gate
                    st["decision"] = "repair_candidate"
                    return
                b["status"] = "unresolved"
                b["reason"] = (b.get("reason", "")
                               + "+finalized_change_needs_gate")
                needs["phrase_review"] = True
            elif bs == "unresolved":
                needs["phrase_review"] = True
            elif bs.startswith("resolved"):
                st["decision"] = "auto_resolved"
                return
    elif adj["status"] == "resolved_change_candidate":
        b = rec.get("pitch_adjudication") or {}
        if b.get("status") and b["status"] != "not_needed":
            b["invalidated_by_structure"] = True
            b["old_winning_hypothesis"] = b.pop("winning_hypothesis", None)
            b["status"] = "invalidated"
        needs["pitch_adjudication"] = False    # old span B is void
        rec["structure_change_candidate"] = adj.get("hypothesis_detail")
        if virtual_b is not None:
            rec["virtual_note_adjudication"] = virtual_b
            # §8.1: phrase_review only if a virtual-note B is still
            # unresolved — machine lanes must finish first
            if any(v.get("status") == "unresolved" for v in virtual_b):
                needs["phrase_review"] = True
            else:
                st["decision"] = "resolved_change_candidate"
                return
        else:
            needs["phrase_review"] = True
    elif adj["status"] == "unresolved":
        needs["phrase_review"] = True
        b = rec.get("pitch_adjudication") or {}
        if b.get("provisional"):
            b["provisional"] = False
            b["blocked_by_unresolved_structure"] = True
        needs["pitch_adjudication"] = False

    if needs["pitch_adjudication"]:
        st["decision"] = "needs_pitch_adjudication"
    elif needs["structure_adjudication"]:
        st["decision"] = "needs_structure_adjudication"
    elif needs["phrase_review"]:
        st["decision"] = "needs_phrase_review"
    elif (rec.get("pitch_adjudication") or {}).get("status", "") \
            .startswith("resolved"):
        st["decision"] = "auto_resolved"
    else:
        st["decision"] = "keep_baseline"
