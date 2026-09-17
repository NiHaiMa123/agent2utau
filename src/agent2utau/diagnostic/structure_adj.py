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


def _one_note_support(pls: list[dict]) -> float:
    """§8.5 (C2 patch): explicit one-note support — never
    `1 - split_support`. Missing/low-confidence extractor = neutral 0."""
    if not pls:
        return 0.0                        # missing -> neutral
    if len(pls) == 1:
        p0 = pls[0]
        dur_s = min(1.0, p0["dur"] / 0.12)
        iqr = p0.get("iqr_cents")
        stab = 1.0 - min(1.0, (iqr if iqr is not None else 100) / 200.0)
        return round(dur_s * (0.6 + 0.4 * stab), 3)
    # >=2 plateaus can still mean one written note when the delta is
    # not meaningful (vibrato/segmentation artifact)
    ev = _extractor_evidence(pls)
    mag = abs(ev["pitch_delta_st"])
    if mag < MIN_STRUCTURE_DELTA_ST:
        return round(0.3 + 0.7 * (1 - mag / MIN_STRUCTURE_DELTA_ST), 3)
    return 0.0


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
    boundary (explicit member spans), i.e. GAME itself merged i+j.
    Member lists are unioned across p and its neighbours — the
    crossing note may be grouped into the neighbour's consensus
    event rather than p's."""
    spans: dict[str, list] = {}
    for src in [p, *(neighbors or [])]:
        for rid, ms in ((src.get("consensus") or {})
                        .get("member_notes") or {}).items():
            spans.setdefault(rid, []).extend(ms)
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
                     for s, e, _t in ms))
    return round(hit / max(1, n_runs), 3)


# ---------------------------------------------------------------------
# §8.2/8.5: operation-aware virtual GAME correspondence
# ---------------------------------------------------------------------
#
# A real GAME run may only cast a pitch vote for a virtual child when
# that run itself produced a note with the child's identity. Time
# overlap with the virtual span is NOT identity: a long note spanning
# the candidate split boundary means "this run did not split" — it is
# anti-split STRUCTURE evidence and must not vote for either child.
# For merge the semantics invert: a note spanning the removed internal
# boundary IS the merged identity. The stochastic denominator is always
# the total GAME run count — never the matched subset.

VCORR_RULE = "c2-identity-correspondence-1"
CORR_EDGE_TOL_S = 0.08     # member edge vs virtual/combined edge
CORR_CROSS_S = 0.04        # extending past a candidate boundary = crossing
CORR_MATCH_COVER = 0.6     # coverage needed for child identity match
CORR_PARTIAL_COVER = 0.25  # below -> absent, above -> ambiguous


def _corr_classify_run(op: str, s: float, e: float,
                       ms: list[list[float]],
                       boundary: float | None) -> tuple:
    """Classify one run's real member notes vs a virtual note identity.

    Returns (class, member_index, detail). Only `child_identity_match`
    may contribute a GAME pitch vote; `parent_spanning_note` is evidence
    that the run kept the pre-change structure (anti-split for split,
    anti-merge for merge); `ambiguous`/`absent` are neutral.
    """
    span = max(1e-9, e - s)

    def _ov(m):
        return max(0.0, min(e, m[1]) - max(s, m[0]))

    if not ms:
        return "absent", None, "no_member_in_region"
    best = max(range(len(ms)), key=lambda i: _ov(ms[i]))
    if op == "merge":
        # merged identity = one member spanning the removed boundary
        # and matching both combined-span edges within tolerance
        if boundary is not None:
            spanning = [i for i, m in enumerate(ms)
                        if m[0] < boundary - CORR_CROSS_S
                        and m[1] > boundary + CORR_CROSS_S]
            for i in spanning:
                if (abs(ms[i][0] - s) <= CORR_EDGE_TOL_S
                        and abs(ms[i][1] - e) <= CORR_EDGE_TOL_S):
                    return ("child_identity_match", i,
                            "member_spans_removed_boundary")
            if spanning:
                return ("ambiguous", spanning[0],
                        "spanning_member_edge_mismatch")
            for i in range(len(ms) - 1):
                edge = (ms[i][1] + ms[i + 1][0]) / 2.0
                if abs(edge - boundary) <= CORR_EDGE_TOL_S:
                    return ("parent_spanning_note", None,
                            "internal_boundary_kept")
        if _ov(ms[best]) >= CORR_PARTIAL_COVER * span:
            return "ambiguous", best, "partial_span_overlap"
        return "absent", None, "no_member_in_region"
    # split / boundary_shift: identity = one member matching the child
    # span without crossing the candidate boundary. Priority: a run
    # whose OWN internal boundary is compatible with the candidate
    # boundary produced real child identities — the member on the
    # child's side of that internal edge is the correspondence, even
    # when its far edge differs within tolerance (§8.2).
    if boundary is not None:
        edges = [(ms[i][1] + ms[i + 1][0]) / 2.0
                 for i in range(len(ms) - 1)]
        compat = [x for x in edges if abs(x - boundary)
                  <= CORR_EDGE_TOL_S]
        if compat:
            b2 = min(compat, key=lambda x: abs(x - boundary))
            if e <= b2 + CORR_EDGE_TOL_S:      # child before boundary
                side = [i for i, m in enumerate(ms)
                        if m[1] <= b2 + CORR_EDGE_TOL_S]
                mi = max(side, key=lambda i: ms[i][1]) if side else None
            else:                              # child after boundary
                side = [i for i, m in enumerate(ms)
                        if m[0] >= b2 - CORR_EDGE_TOL_S]
                mi = min(side, key=lambda i: ms[i][0]) if side else None
            if mi is None:
                return "absent", None, "no_member_on_child_side"
            if _ov(ms[mi]) >= CORR_MATCH_COVER * span:
                return ("child_identity_match", mi,
                        "internal_boundary_compatible")
            return "ambiguous", mi, "run_subdivided_child"
        crossing = [i for i, m in enumerate(ms)
                    if m[0] < boundary - CORR_CROSS_S
                    and m[1] > boundary + CORR_CROSS_S]
        if crossing:
            return ("parent_spanning_note", crossing[0],
                    "member_crosses_candidate_boundary")
    # fallback: a member matching the child span directly (e.g. the
    # run's note simply ends at the boundary with nothing after it)
    if (_ov(ms[best]) >= CORR_MATCH_COVER * span
            and abs(ms[best][0] - s) <= CORR_EDGE_TOL_S
            and abs(ms[best][1] - e) <= CORR_EDGE_TOL_S):
        return "child_identity_match", best, "span_matched"
    if _ov(ms[best]) >= CORR_PARTIAL_COVER * span:
        return "ambiguous", best, "partial_or_edge_mismatch"
    return "absent", None, "no_member_in_region"


def virtual_game_correspondence(op: str, s: float, e: float,
                                member_runs: dict[str, list],
                                n_total: int, boundary: float | None,
                                virtual_id: str | None = None,
                                parent_ids: list[str] | None = None,
                                seed: float | None = None) -> dict:
    """Per-run GAME correspondence for a C-constructed virtual note.

    member_runs: {run_id: [[start,end,tone], ...]} REAL per-run GAME
    notes overlapping the operation's parent region — never synthesized
    consensus medians. n_total is ALWAYS the total stochastic run
    count; the child pitch support consumed by frozen B is
    present-tone matches / n_total (identity presence × conditional
    pitch agreement), never renormalized over matched runs.
    """
    per_run, tones = {}, []
    for ri in range(max(1, int(n_total))):
        ms = sorted(member_runs.get(str(ri)) or [], key=lambda m: m[0])
        cls, mi, det = _corr_classify_run(op, s, e, ms, boundary)
        mem = ms[mi] if mi is not None else None
        per_run[str(ri)] = {
            "class": cls,
            "member_ref": (f"run{ri}[{mi}]" if mi is not None else None),
            "member": ([round(float(v), 3) for v in mem]
                       if mem is not None else None),
            "detail": det}
        if cls == "child_identity_match":
            tones.append(round(float(mem[2]), 2))
    n_present = len(tones)
    presence = round(n_present / max(1, int(n_total)), 3)
    cond = (round(float(np.mean(np.abs(np.array(tones) - seed)
                                <= 0.5)), 3)
            if tones and seed is not None else None)
    return {"rule": VCORR_RULE, "operation": op,
            "virtual_id": virtual_id,
            "parent_ids": parent_ids or [],
            "span": [round(s, 3), round(e, 3)],
            "candidate_written_pitch": seed,
            "candidate_boundary": boundary,
            "n_total_runs": int(n_total),
            "n_present": n_present,
            "per_run": per_run,
            "present_tones": tones,
            "child_presence_rate": presence,
            "conditional_tone_support": cond,
            "effective_game_support":
                round(presence * (cond if cond is not None else 0.0), 3)}


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

    # non-F0 boundary family (§8.4B/8.5): TRULY independent mechanisms
    # only — boundary-local energy dip+recovery (onset/flux proxies can
    # join later). RMVPE voiced-mask drop is part of the RMVPE family,
    # so it boosts sup_r below but can NEVER satisfy the independent
    # non-F0 requirement (§8.3 final patch).
    be = (_boundary_energy(times, energy, b, t0, t1)
          if b is not None
          else {"dip_prominence": 0.0, "recovery": 0.0, "support": 0.0})
    vdrop = (_boundary_voiced_drop(times, voiced, b)
             if b is not None else 0.0)
    sup_r = round(min(1.0, sup_r + 0.25 * vdrop), 3)   # same family
    nonf0 = be["support"]

    game_one = (sum(1 for c in counts if c == 1) / n_runs
                if n_runs else 1.0)
    game_split = (sum(1 for c in counts if c >= 2) / n_runs
                  if n_runs else 0.0)

    # --- scores -------------------------------------------------------
    # §8.5: explicit one-note support — missing extractor is neutral,
    # never free evidence for H0 or opposition to H1.
    one_r = _one_note_support(pl_r)
    one_f = _one_note_support(pl_f)
    dur_plaus_h0 = 0.0 if p["dur"] < SHORT_NOTE_S else 1.0
    scored = {"H0": {"score": round(game_one + one_r + one_f
                                  + (1 - nonf0) + 0.5 * dur_plaus_h0, 3),
                     "groups": {"game": round(game_one, 3),
                                "rmvpe": one_r,
                                "fcpe": one_f,
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
