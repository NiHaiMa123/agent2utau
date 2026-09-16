"""M2.3.2B: automatic pitch/octave adjudication.

Evidence-based hypothesis scoring — never majority voting, never binary
GAME evidence. Each candidate hypothesis is scored across independent
families:

  GAME run distribution (continuous, per-run tones)
  RMVPE center (weighted by reliability)
  FCPE center (weighted by reliability)
  third-F0 (pYIN) center (weighted by reliability)
  periodicity (normalized ACF at the hypothesized lag)
  subharmonic support (energy at f0/2 penalizes upper-octave hyps)
  harmonic-series fit (spectrum energy at k*f0)
  local melodic continuity (leap size vs neighbours)

Separation sensitivity is a confidence penalty only — it can never
decide the winner (plan §9.2).
"""

from __future__ import annotations

import numpy as np

SUPPORT_ST = 0.5          # |center - hyp| <= 0.5st counts as support
MIN_MARGIN = 0.12         # winner margin over runner-up (score units)
MIN_FAMILIES = 2          # independent families must support winner
CONFLICT_CENTS = 100.0    # extractor disagreement threshold
COUNTER_PERIODICITY = 0.25  # winner ACF below this = strong counter-evidence

# family weights — GAME is the transcription baseline but not truth;
# each extractor family counts once regardless of how many fields agree
W_GAME, W_EXT, W_THIRD, W_PERIOD, W_HARM, W_CONT = 1.0, 1.0, 1.0, 1.0, 1.0, 0.5


def midi_to_hz(m: float) -> float:
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0)


def third_f0_pyin(wav: np.ndarray, sr: int,
                  hop: int | None = None) -> dict:
    """librosa pYIN on the separated vocal — the third F0 family.

    Returns per-frame midi (nan = unvoiced), voicing probability and full
    provenance. Failure/low-confidence frames are evidence of *weak
    reliability*, never evidence against a hypothesis."""
    import librosa
    hop = hop or int(0.010 * sr)   # 10 ms
    fmin, fmax = librosa.note_to_hz("E2"), librosa.note_to_hz("C7")
    f0, vflag, vprob = librosa.pyin(
        wav, fmin=fmin, fmax=fmax, sr=sr, frame_length=2048,
        hop_length=hop)
    midi = librosa.hz_to_midi(f0)
    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr,
                                   hop_length=hop)
    return {"times": np.asarray(times), "midi": np.asarray(midi),
            "voiced_prob": np.asarray(vprob),
            "provenance": {"implementation": "librosa.pyin",
                           "version": librosa.__version__,
                           "fmin_hz": float(fmin), "fmax_hz": float(fmax),
                           "frame_length": 2048, "hop_length": hop,
                           "frame_period_s": round(hop / sr, 6),
                           "sr": sr}}


def third_f0_window(third: dict, t0: float, t1: float,
                    min_prob: float = 0.5) -> dict:
    """Aggregate third-F0 inside a note window."""
    m = (third["times"] >= t0) & (third["times"] < t1)
    midi, prob = third["midi"][m], third["voiced_prob"][m]
    ok = np.isfinite(midi) & (prob >= min_prob)
    if ok.sum() < 3:
        return {"center_midi": None, "iqr_cents": None,
                "coverage": round(float(ok.mean()) if len(ok) else 0.0, 3),
                "n_voiced": int(ok.sum())}
    sel = midi[ok]
    return {"center_midi": round(float(np.median(sel)), 3),
            "iqr_cents": round(float(np.percentile(sel, 75)
                                     - np.percentile(sel, 25)) * 100, 1),
            "coverage": round(float(ok.mean()), 3),
            "n_voiced": int(ok.sum())}


def hypotheses(packet: dict, third_center: float | None) -> list[float]:
    """Candidate tone set: H0 = written GAME pitch, octave shifts, and
    any extractor center that differs meaningfully (>0.5st)."""
    g = packet["game_tone"]
    hyps = [g, g - 12.0, g + 12.0]
    cons = packet.get("consensus") or {}
    # §9.1 (B2): on structure-ambiguous events, aggregate run_tones are
    # medians across split/merge members — not real written notes —
    # so they must not seed hypotheses.
    if not cons.get("structure_varies"):
        # GAME's own alternative answers are hypotheses too (202s case:
        # runs answered 65.3 vs 72.4 — adjudication must choose)
        for t in cons.get("run_tones") or []:
            hyps.append(float(t))
    for fam in ("rmvpe", "fcpe"):
        c = (packet.get(fam) or {}).get("center_midi")
        if c is not None:
            hyps.append(c)
    if third_center is not None:
        hyps.append(third_center)
    # dedupe within 0.5st, H0 first
    out = []
    for h in hyps:
        if all(abs(h - o) > SUPPORT_ST for o in out):
            out.append(round(float(h), 2))
    return out


def _acf_scores(seg: np.ndarray, sr: int, hyps: list[float]) -> dict:
    """Normalized ACF at each hypothesis's lag WITH double-period
    discrimination (§9.2): a real period T also correlates at 2T, so a
    raw ACF(T) cannot prove octave identity. Per-hyp score is penalized
    when the double period (2T) or half period (T/2) correlates better —
    that means the truth sits an octave away from the hypothesis."""
    if len(seg) < 512:
        return {}
    seg = seg - seg.mean()
    seg = seg * np.hanning(len(seg))
    n = int(2 ** np.ceil(np.log2(len(seg) * 2)))
    r = np.fft.irfft(np.abs(np.fft.rfft(seg, n)) ** 2)[: len(seg)]
    if r[0] <= 0:
        return {}
    r /= r[0]

    def _peak(lag: float) -> float:
        lo, hi = max(8, int(lag * 0.97)), min(len(r) - 1,
                                            int(np.ceil(lag * 1.03)))
        return float(r[lo:hi].max()) if lo < hi else 0.0

    out = {}
    for h in hyps:
        lag = sr / midi_to_hz(h)
        r_t = _peak(lag)
        r_2t = _peak(2 * lag)        # true period 2T => h is octave HIGH
        r_ht = _peak(lag / 2)        # true period T/2 => h is octave LOW
        score = r_t - 0.5 * max(0.0, r_2t - r_t) \
            - 0.5 * max(0.0, r_ht - r_t)
        out[h] = round(max(0.0, score), 3)
    return out


def _harmonic_fit(seg: np.ndarray, sr: int, hyp: float,
                  n_harm: int = 8) -> float:
    """Octave-discriminative harmonic score (§9.2): naive sum over k*f0
    bins is biased toward the LOWER candidate (its harmonic set is a
    superset). Debiased score = matched-fit * odd-harmonic ratio —
    if the truth is 2*hyp, the odd harmonics of hyp (f,3f,5f…) carry no
    energy, halving the score; if truth is hyp, odd harmonics are real
    spectral content."""
    if len(seg) < 512:
        return 0.0
    seg = seg * np.hanning(len(seg))
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(len(seg), 1 / sr)
    total = spec.sum() + 1e-12
    f0 = midi_to_hz(hyp)
    half_bw = f0 * 0.02
    matched = odd = even = 0.0
    for k in range(1, n_harm + 1):
        f = k * f0
        if f > sr / 2:
            break
        e = float(spec[(freqs >= f - half_bw) & (freqs <= f + half_bw)]
                  .sum())
        matched += e
        if k % 2:
            odd += e
        else:
            even += e
    fit = matched / total
    odd_ratio = odd / (odd + even + 1e-12)
    return round(float(fit * (0.5 + 0.5 * odd_ratio)), 3)


def _subharmonic_support(seg: np.ndarray, sr: int, hyp: float) -> float:
    """Energy at hyp/2 relative to hyp — strong support at f/2 means the
    true fundamental is likely the LOWER octave (counter-evidence for
    an upper-octave hypothesis)."""
    if len(seg) < 512:
        return 0.0
    seg = seg * np.hanning(len(seg))
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(len(seg), 1 / sr)

    def band(f):
        if f <= 0 or f > sr / 2:
            return 0.0
        bw = max(5.0, f * 0.03)
        return float(spec[(freqs >= f - bw) & (freqs <= f + bw)].sum())

    f0 = midi_to_hz(hyp)
    sub, fund = band(f0 / 2), band(f0)
    return round(sub / (sub + fund + 1e-12), 3)


def _reliability(center, iqr_cents, coverage) -> float:
    """Continuous reliability for an extractor opinion: penalize wide
    IQR and sparse voicing. Missing center => 0 (not opposition)."""
    if center is None:
        return 0.0
    iqr = iqr_cents if iqr_cents is not None else 100.0
    cov = coverage if coverage is not None else 0.5
    return float(np.clip(1.0 - iqr / 200.0, 0.0, 1.0)
                 * np.clip(cov, 0.0, 1.0))


def adjudicate(packet: dict, wav: np.ndarray, sr: int,
               third: dict | None, neighbours: list[dict]) -> dict:
    """Score all hypotheses for one pitch-adjudication packet.

    Returns the §9.3/§9.6 result block:
      status: resolved_keep | resolved_change | unresolved
      winning_hypothesis, confidence, margin, evidence_families,
      opposing_families, reason, hypotheses[]
    """
    t0, t1 = packet["start"], packet["start"] + packet["dur"]
    s0, s1 = int(t0 * sr), int(t1 * sr)
    seg = wav[s0:s1]

    third_win = third_f0_window(third, t0, t1) if third else \
        {"center_midi": None, "coverage": 0.0}
    third_c = third_win.get("center_midi")
    hyps = hypotheses(packet, third_c)
    acf = _acf_scores(seg, sr, hyps)

    cons = packet.get("consensus") or {}
    run_tones = cons.get("run_tones") or []
    dual = packet.get("dual_f0") or {}
    rmv, fcp = packet.get("rmvpe") or {}, packet.get("fcpe") or {}
    sep_sensitive = bool((packet.get("separation") or {})
                         .get("separation_sensitive"))
    nb_tones = [nb["game_tone"] for nb in neighbours
                if nb.get("game_tone") is not None]
    cont_ref = float(np.median(nb_tones)) if nb_tones else None

    scored = []
    for h in hyps:
        fam_support, fam_oppose = {}, {}

        # --- GAME run distribution (continuous — 4/5 vs 3/5 differ) ---
        if run_tones:
            gsup = float(np.mean(
                np.abs(np.array(run_tones) - h) <= SUPPORT_ST))
        else:
            gsup = 1.0 if abs(h - packet["game_tone"]) <= SUPPORT_ST else 0.0
        (fam_support if gsup > 0 else fam_oppose)["game"] = round(gsup, 3)

        # --- extractor families (each counts once, reliability-weighted)
        for name, blk in (("rmvpe", rmv), ("fcpe", fcp)):
            rel = _reliability(blk.get("center_midi"), blk.get("iqr_cents"),
                             blk.get("voiced_coverage"))
            if blk.get("center_midi") is None:
                continue  # missing data is not opposition
            if abs(blk["center_midi"] - h) <= SUPPORT_ST:
                fam_support[name] = round(rel, 3)
            else:
                fam_oppose[name] = round(rel, 3)

        # --- third F0 (low confidence = weak opinion, not opposition) ---
        if third_c is not None:
            rel = _reliability(third_c, third_win.get("iqr_cents"),
                               third_win.get("coverage"))
            if abs(third_c - h) <= SUPPORT_ST:
                fam_support["third_f0"] = round(rel, 3)
            elif rel > 0.3:   # only a reliable dissent counts as oppose
                fam_oppose["third_f0"] = round(rel, 3)

        # --- periodicity / subharmonic / harmonic-series --------------
        per = acf.get(h, 0.0)
        if per >= COUNTER_PERIODICITY:
            fam_support["periodicity"] = per
        elif per > 0:
            fam_oppose["periodicity"] = round(
                COUNTER_PERIODICITY - per, 3)

        sub = _subharmonic_support(seg, sr, h)
        if sub > 0.6:            # spectrum prefers the lower octave
            fam_oppose["subharmonic"] = round(sub - 0.5, 3)
        harm = _harmonic_fit(seg, sr, h)
        if harm > 0.05:
            fam_support["harmonic_series"] = harm

        # --- local melodic continuity --------------------------------
        if cont_ref is not None:
            leap = abs(h - cont_ref)
            cont = round(float(1.0 / (1.0 + leap / 12.0)), 3)
            fam_support["continuity"] = cont

        # --- group-level fusion (§7.2, B3) ------------------------------
        # Correlated features inside one mechanism group must not inflate
        # the final score: waveform members are fused to a BOUNDED group
        # score (max member — adding correlated features cannot stack
        # votes), and only group scores enter the final sum.
        wf_support = max(
            (fam_support.get(k, 0.0)
             for k in ("third_f0", "periodicity", "harmonic_series")),
            default=0.0)
        wf_oppose = max(
            (fam_oppose.get(k, 0.0)
             for k in ("third_f0", "periodicity", "subharmonic")),
            default=0.0)
        group_scores = {
            "game": round(gsup, 3),
            "rmvpe": round(fam_support.get("rmvpe", 0.0)
                           - fam_oppose.get("rmvpe", 0.0), 3),
            "fcpe": round(fam_support.get("fcpe", 0.0)
                          - fam_oppose.get("fcpe", 0.0), 3),
            "waveform": round(max(0.0, wf_support - 0.5 * wf_oppose), 3),
            "context": round(fam_support.get("continuity", 0.0), 3),
        }
        score = (W_GAME * group_scores["game"]
                 + W_EXT * (group_scores["rmvpe"] + group_scores["fcpe"])
                 + W_THIRD * group_scores["waveform"]
                 + W_CONT * group_scores["context"])
        if sep_sensitive:
            score *= 0.8      # sensitivity lowers confidence, not truth
        scored.append({"hypothesis": h, "score": round(score, 3),
                       "game_support_ratio": round(gsup, 3),
                       "periodicity": per, "subharmonic": sub,
                       "harmonic_fit": harm,
                       "group_scores": group_scores,
                       "supporting": fam_support, "opposing": fam_oppose})

    scored.sort(key=lambda x: -x["score"])
    win = scored[0]
    runner = scored[1] if len(scored) > 1 else None
    margin = round(win["score"] - (runner["score"] if runner else 0.0), 3)

    # §7.2 (B3 patch): supporting/opposing groups are derived ONLY from
    # the finalized net group_scores — a raw feature value can never
    # bypass group-level semantics. Evidence chain is one-way:
    # features -> group fusion -> group_scores -> groups -> gates.
    groups, opposing_groups = _groups_from_scores(
        win["group_scores"], win["opposing"], has_run_tones=bool(run_tones))
    # hard families = feature-level audit trail only (no gate use)
    hard_fams = [k for k in win["supporting"]
                 if k != "continuity" and win["supporting"][k] > 0.2]

    # --- resolution gates (§9.5) --------------------------------------
    reasons = []
    if len(groups) < MIN_FAMILIES:
        reasons.append("insufficient_independent_families")
    if margin < MIN_MARGIN:
        reasons.append("margin_too_small")
    if win["periodicity"] < COUNTER_PERIODICITY:
        reasons.append("periodicity_counter")
    if sep_sensitive and win["opposing"]:
        reasons.append("separation_sensitive_conflict")
    would_change = abs(win["hypothesis"] - packet["game_tone"]) \
        > SUPPORT_ST
    if would_change and "waveform" not in groups:
        # an automatic pitch CHANGE needs octave-discriminative waveform
        # evidence, not just extractor agreement
        reasons.append("change_requires_waveform_support")
    extractor_conflict = (dual and abs(dual.get("rmvpe_vs_fcpe_cents")
                                       or 0) > CONFLICT_CENTS)
    if extractor_conflict:
        # stricter still: waveform convergence AND at least one
        # non-GAME extractor on the winner
        if "waveform" not in groups \
                or not ({"rmvpe", "fcpe"} & set(groups)):
            reasons.append("extractor_conflict_unresolved_by_waveform")

    if reasons:
        status = "unresolved"
    else:
        status = ("resolved_keep" if not would_change
                  else "resolved_change")

    return {"status": status,
            "winning_hypothesis": win["hypothesis"],
            "confidence": win["score"],
            "margin": margin,
            "evidence_families": hard_fams,
            "supporting_features": {k: win["supporting"][k]
                                    for k in sorted(win["supporting"])},
            "supporting_independence_groups": groups,
            "opposing_independence_groups": opposing_groups,
            "group_scores": win["group_scores"],
            "opposing_families": sorted(win["opposing"]),
            "reason": "+".join(reasons) if reasons else "converged",
            "extractor_conflict": bool(extractor_conflict),
            "separation_sensitive": sep_sensitive,
            "hypotheses": scored}


GROUP_SUPPORT_THR = 0.2


def _groups_from_scores(group_scores: dict, opposing_features: dict,
                        has_run_tones: bool = True):
    """Derive supporting/opposing independence groups from FINALIZED net
    group scores only (B3 patch §7.2). `context` is soft and never counts.
    Returns (supporting_groups, opposing_groups)."""
    sup = [g for g in ("game", "rmvpe", "fcpe", "waveform")
           if group_scores.get(g, 0.0) > GROUP_SUPPORT_THR]
    opp_nets = {"game": (1.0 - group_scores.get("game", 0.0))
                if has_run_tones else 0.0,
                "rmvpe": -group_scores.get("rmvpe", 0.0),
                "fcpe": -group_scores.get("fcpe", 0.0),
                "waveform": 0.0}
    for k in ("third_f0", "periodicity", "subharmonic"):
        opp_nets["waveform"] = max(opp_nets["waveform"],
                                   opposing_features.get(k, 0.0))
    opp = [g for g, v in opp_nets.items() if v > GROUP_SUPPORT_THR]
    return sup, opp


def apply_adjudication(rec: dict, adj: dict,
                       repair_gate: dict | None) -> None:
    """Route a packet after B ran (§9.6). Mutates rec["state"].

    - resolved_keep   -> clear pitch need (structure need untouched)
    - resolved_change -> repair_candidate ONLY if the repair gate is
                         eligible; otherwise demoted to unresolved and
                         phrase_review-eligible
    - unresolved      -> clear pitch need (B must not re-run on it) and
                         mark phrase_review eligibility
    Decision is recomputed from remaining routing_needs. Candidate 0
    (`game_tone`) is never overwritten by a B result.
    """
    st = rec["state"]
    needs = st["routing_needs"]

    # §9.1 (B2): pitch+structure concurrency — note identity is not yet
    # fixed, so this B result is PROVISIONAL and C runs first. The pitch
    # need stays set: after a structure change the packet must be
    # regenerated and B re-run.
    if needs["structure_adjudication"]:
        adj["provisional"] = True
        st["decision"] = "needs_structure_adjudication"
        return

    needs["pitch_adjudication"] = False          # B ran once — no loop

    if adj["status"] == "resolved_change":
        if repair_gate and repair_gate.get("eligible"):
            rec["repair_gate"] = repair_gate
            st["decision"] = "repair_candidate"
            return
        adj["status"] = "unresolved"
        failed = (repair_gate or {}).get("failed") or []
        adj["reason"] = (adj.get("reason", "resolved_change")
                         + "+repair_gate_failed:" + ",".join(failed))
        needs["phrase_review"] = True
    elif adj["status"] == "unresolved":
        needs["phrase_review"] = True

    if needs["pitch_adjudication"]:
        st["decision"] = "needs_pitch_adjudication"
    elif needs["structure_adjudication"]:
        st["decision"] = "needs_structure_adjudication"
    elif needs["phrase_review"]:
        st["decision"] = "needs_phrase_review"
    elif adj["status"].startswith("resolved"):
        st["decision"] = "auto_resolved"
    else:
        st["decision"] = "keep_baseline"
