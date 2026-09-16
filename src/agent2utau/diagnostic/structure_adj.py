"""M2.3.2C: automatic structure adjudication.

Goal is NOT to rewrite the score — only to answer reliably: should this
region be one note, two notes, merged, portamento, grace, or artifact?

Stage 1 produces adjudication results only — no automatic split/merge/
boundary repair. Candidate 0 is never touched.

Inputs (§7.1):
  A. existing structure lanes (consensus.structure_varies / routing need)
  B. independent discovery over ALL baseline notes — a GAME-stable
     one-note with dual-F0 two-plateau agreement must still enter C.

Evidence uses the same group-fusion discipline as B: RMVPE fields are
one family, FCPE fields are one family, acoustic boundary features are
one family — raw feature counts never vote directly.
"""

from __future__ import annotations

import numpy as np

CHANGEPOINT_AGREE_S = 0.08      # rmvpe/fcpe boundary within 80ms
LONG_NOTE_S = 1.0               # "suspiciously merged long note"
SHORT_NOTE_S = 0.07             # "suspiciously short neighbouring note"
MIN_SPLIT_DUR_S = 0.05          # a split producing <50ms notes is implausible
PLATEAU_MATCH_ST = 0.5
BOUNDARY_DIP_RATIO = 0.55       # energy dip at boundary <= 55% of note mean
GROUP_THR = 0.2
MIN_MARGIN = 0.15
MIN_GROUPS = 2


def discover_structure(packets: list[dict], times: np.ndarray,
                       energy: np.ndarray) -> dict[str, list[str]]:
    """Independent discovery scan over ALL baseline packets (§7.1B/7.2).

    Returns {packet_id: [reasons]}. A packet may already carry a
    structure need — discovery reasons are recorded regardless so the
    adjudicator sees why it entered C.
    """
    out: dict[str, list[str]] = {}
    for i, p in enumerate(packets):
        reasons = []
        pl_r = p.get("plateaus") or []
        pl_f = p.get("fcpe_plateaus") or []

        # dual-F0 multi-plateau agreement inside ONE GAME note
        if len(pl_r) >= 2 and len(pl_f) >= 2:
            reasons.append("dual_f0_multi_plateau")
            # cross-extractor changepoint agreement (first boundary)
            if abs(pl_r[1]["start"] - pl_f[1]["start"]) \
                    <= CHANGEPOINT_AGREE_S:
                reasons.append("cross_extractor_changepoint")
        # strong voiced-to-voiced pitch transition (>=1st) in both
        elif len(pl_r) >= 2 or len(pl_f) >= 2:
            pls = pl_r if len(pl_r) >= 2 else pl_f
            if abs(pls[1]["center_midi"] - pls[0]["center_midi"]) >= 1.0:
                reasons.append("single_extractor_transition")

        # voiced gap / re-attack: energy dip inside the note window
        t0, t1 = p["start"], p["start"] + p["dur"]
        m = (times >= t0) & (times < t1)
        if m.sum() >= 4:
            e = energy[m]
            if e.mean() > 1e-4 and e.min() < BOUNDARY_DIP_RATIO * e.mean():
                reasons.append("voiced_gap_or_energy_dip")

        # suspiciously merged long note
        if p["dur"] > LONG_NOTE_S and (len(pl_r) >= 2 or len(pl_f) >= 2):
            reasons.append("long_note_multi_plateau")

        # suspiciously short neighbouring notes -> merge suspicion
        if p["dur"] < SHORT_NOTE_S:
            reasons.append("very_short_note")

        if reasons:
            out[p["id"]] = reasons
    return out


def _boundary_time(pl_r, pl_f, t0, t1):
    """Best changepoint estimate: median of second-plateau starts."""
    cands = [pl[1]["start"] for pl in (pl_r, pl_f) if len(pl) >= 2]
    if not cands:
        return None
    b = float(np.median(cands))
    return b if t0 + MIN_SPLIT_DUR_S <= b <= t1 - MIN_SPLIT_DUR_S else None


def _energy_boundary_support(times, energy, b, t0, t1):
    """Local energy minimum near boundary b relative to note mean."""
    m = (times >= t0) & (times < t1)
    e_all = energy[m]
    if e_all.size < 4 or e_all.mean() <= 1e-4:
        return 0.0
    mb = (times >= b - 0.05) & (times <= b + 0.05)
    if not mb.any():
        return 0.0
    dip = 1.0 - float(energy[mb].min() / (e_all.mean() + 1e-12))
    return round(float(np.clip(dip / (1 - BOUNDARY_DIP_RATIO), 0, 1)), 3)


def hypotheses_structure(p: dict) -> dict:
    """H0 current structure, H1 split, H2 merge, H3 portamento — as
    available from plateau/run evidence. Returns {name: {...}}."""
    pl_r, pl_f = p.get("plateaus") or [], p.get("fcpe_plateaus") or []
    t0, t1 = p["start"], p["start"] + p["dur"]
    b = _boundary_time(pl_r, pl_f, t0, t1)
    hyps = {"H0": {"kind": "keep", "notes": [
        {"start": t0, "end": t1, "tone": p["game_tone"]}]}}
    if b is not None:
        hyps["H1"] = {"kind": "split", "boundary": round(b, 4),
                      "notes": [{"start": t0, "end": b},
                                {"start": b, "end": t1}]}
    hyps["H3"] = {"kind": "portamento"}   # one note with pitch glide
    return hyps


def _merge_evidence(p: dict, neighbors: list[dict]) -> tuple[float, dict | None]:
    """Plateau continuity across a shared boundary suggests two GAME
    notes are really one. Returns (support, merged_span)."""
    if p["dur"] >= SHORT_NOTE_S:
        return 0.0, None
    pl = p.get("plateaus") or []
    if not pl:
        return 0.0, None
    for nb in neighbors or []:
        npl = nb.get("plateaus") or []
        if not npl:
            continue
        # this note's last plateau meets neighbour's first plateau with
        # matching centers -> one underlying note split by GAME
        if (abs(pl[-1]["end"] - nb["start"]) < 0.05
                and abs(pl[-1]["center_midi"] - npl[0]["center_midi"])
                < PLATEAU_MATCH_ST):
            span = {"start": p["start"],
                    "end": nb["start"] + nb["dur"],
                    "merge_with": nb["id"]}
            return 1.0, span
    return 0.0, None


def adjudicate_structure(p: dict, times: np.ndarray,
                       energy: np.ndarray,
                       discovery_reasons: list[str],
                       neighbors: list[dict] | None = None) -> dict:
    """Score structure hypotheses for one packet (§7.3/7.4).

    Groups: game_structure | rmvpe | fcpe | acoustic_boundary |
    duration_plausibility(soft) | context(soft).
    """
    cons = p.get("consensus") or {}
    pl_r, pl_f = p.get("plateaus") or [], p.get("fcpe_plateaus") or []
    counts = cons.get("run_note_counts") or []
    n_runs = len(counts)
    t0, t1 = p["start"], p["start"] + p["dur"]
    b = _boundary_time(pl_r, pl_f, t0, t1)
    two_plateau_r, two_plateau_f = len(pl_r) >= 2, len(pl_f) >= 2

    sup_r = 1.0 if two_plateau_r else 0.0
    sup_f = 1.0 if two_plateau_f else 0.0
    changepoint_agree = (two_plateau_r and two_plateau_f
                         and abs(pl_r[1]["start"] - pl_f[1]["start"])
                         <= CHANGEPOINT_AGREE_S)
    boundary_ev = (_energy_boundary_support(times, energy, b, t0, t1)
                   if b is not None else 0.0)
    acoustic = round(0.5 * float(changepoint_agree)
                     + 0.5 * boundary_ev, 3)
    dur_pen_split = 1.0 if (b is None or
                            (b - t0 >= MIN_SPLIT_DUR_S
                             and t1 - b >= MIN_SPLIT_DUR_S)) else 0.0

    merge_sup, merge_span = _merge_evidence(p, neighbors or [])

    def _score(notes_n: int, split: bool) -> dict:
        g_game = (sum(1 for c in counts if c == notes_n) / n_runs
                  if n_runs else (1.0 if notes_n == 1 else 0.0))
        g_rmv = sup_r if split else max(0.0, 1.0 - sup_r - merge_sup)
        g_fcp = sup_f if split else max(0.0, 1.0 - sup_f - merge_sup)
        g_aco = acoustic if split else max(0.0, 1.0 - acoustic)
        if split:
            g_dur = dur_pen_split
        else:
            # a <70ms note standing alone is itself implausible
            g_dur = 0.0 if p["dur"] < SHORT_NOTE_S else 1.0
        score = (g_game + g_rmv + g_fcp + g_aco + 0.5 * g_dur)
        groups = {"game": round(g_game, 3), "rmvpe": round(g_rmv, 3),
                  "fcpe": round(g_fcp, 3),
                  "acoustic_boundary": round(g_aco, 3),
                  "duration": round(g_dur, 3)}
        return {"score": round(score, 3), "groups": groups}

    scored = {"H0": _score(1, split=False)}
    hyps = hypotheses_structure(p)
    if "H1" in hyps:
        scored["H1"] = _score(2, split=True)

    if merge_sup > 0:
        g_game_m = (sum(1 for c in counts if c == 0) / n_runs
                    if n_runs else 0.0)
        g_fcp_m = 0.0
        for nb in neighbors or []:
            if merge_span and nb["id"] == merge_span["merge_with"]:
                nfpl = nb.get("fcpe_plateaus") or []
                if (nfpl and pl_f
                        and abs(pl_f[-1]["center_midi"]
                                - nfpl[0]["center_midi"])
                        < PLATEAU_MATCH_ST):
                    g_fcp_m = 1.0
        g_aco_m = max(0.0, 1.0 - acoustic)
        hyps["H2"] = {"kind": "merge", "span": merge_span}
        scored["H2"] = {"score": round(g_game_m + merge_sup + g_fcp_m
                                     + 0.5 * g_aco_m, 3),
                        "groups": {"game": round(g_game_m, 3),
                                   "rmvpe": merge_sup,
                                   "fcpe": round(g_fcp_m, 3),
                                   "acoustic_boundary": round(g_aco_m, 3)}}

    # ornament case: GAME splits but acoustics say one note with glide
    ornament_like = (two_plateau_r or two_plateau_f) and not changepoint_agree
    if ornament_like:
        g_game = (sum(1 for c in counts if c == 1) / n_runs
                  if n_runs else 0.5)
        g_aco = max(0.0, 1.0 - acoustic)
        scored["H3"] = {"score": round(g_game + g_aco + 0.5, 3),
                        "groups": {"game": g_game,
                                   "acoustic_boundary": g_aco}}

    ranked = sorted(scored.items(), key=lambda kv: -kv[1]["score"])
    win_name, win = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else (None, {"score": 0.0})
    margin = round(win["score"] - runner[1]["score"], 3)
    hard_groups = [g for g, v in win["groups"].items()
                   if g != "duration" and v > GROUP_THR]

    reasons = []
    if len(hard_groups) < MIN_GROUPS:
        reasons.append("insufficient_structure_evidence")
    if margin < MIN_MARGIN:
        reasons.append("margin_too_small")

    # classification
    if reasons:
        cls, status = "UNRESOLVED_STRUCTURE", "unresolved"
    elif win_name == "H0":
        cls, status = ("ONE_NOTE_WITH_PORTAMENTO"
                       if (two_plateau_r or two_plateau_f)
                       else "RESOLVED_KEEP"), "resolved_keep"
    elif win_name == "H1":
        cls, status = "TRUE_SPLIT_CANDIDATE", "resolved_change_candidate"
    elif win_name == "H2":
        cls, status = "TRUE_MERGE_CANDIDATE", "resolved_change_candidate"
    elif win_name == "H3":
        cls, status = ("GRACE_OR_ORNAMENT" if ornament_like
                       else "ONE_NOTE_WITH_PORTAMENTO"), "resolved_keep"
    else:
        cls, status = "UNRESOLVED_STRUCTURE", "unresolved"

    # artifact checks override weak winners
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
            "all_scores": {k: v["score"] for k, v in scored.items()},
            "boundary": hyps.get("H1", {}).get("boundary")}


def apply_structure(rec: dict, adj: dict,
                    b_gate: dict | None = None) -> None:
    """§8 lifecycle: route a packet after C ran. Mutates rec['state'].

    - resolved_keep            -> structure need cleared; provisional B
                                finalized (provisional flag dropped, the
                                already-computed pitch result stands)
    - resolved_change_candidate-> structure need cleared; old B result
                                INVALIDATED; decision ->
                                needs_pitch_adjudication is NOT set —
                                new-note B is a future repair-stage job;
                                mark phrase_review eligibility instead
    - unresolved               -> structure need cleared (no C loop),
                                phrase_review eligibility
    """
    st = rec["state"]
    needs = st["routing_needs"]
    needs["structure_adjudication"] = False    # C ran once — no loop

    if adj["status"] == "resolved_keep":
        b = rec.get("pitch_adjudication") or {}
        if b.get("provisional"):
            b["provisional"] = False
            b["finalized_by"] = "structure_resolved_keep"
        # §8.1: note identity is fixed — the provisional B result is
        # now FINAL and must be routed, not left dangling:
        #   resolved_keep   -> auto_resolved
        #   resolved_change -> cannot repair without the frozen repair
        #                      gate re-check -> demote to unresolved +
        #                      phrase_review
        #   unresolved      -> phrase_review
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
        needs["phrase_review"] = True          # repair-stage job
        rec["structure_change_candidate"] = adj.get("hypothesis_detail")
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
