"""L7 Round-A waveform voicing evidence for extractor-disputed spans.

When the two F0 families disagree on whether a detected SOURCE gesture is
voiced (e.g. fcpe-voiced / rmvpe-unvoiced "disputed" frames), a third-F0
non-detection cannot adjudicate: missing/low-confidence extractor output
is weak observability, never opposition (diagnostic.adjudicate contract).

This module measures the disputed span DIRECTLY on the waveform —
positive physical measurements, not extractor absence:

- per-frame best normalized ACF over 80..1000 Hz (periodicity profile)
- harmonic-band power at the claimed f0 — real phonation must carry
  energy at k>=2 harmonics; a bare single-bin resonance cannot
- median-frame RMS (a phonated gesture sustains near context level)

Every measurement is calibrated against the SAME recording: a
both-extractors-voiced reference span inside the event window and (when
available) a both-unvoiced reference span inside the phrase window.  The
disputed span is also measured on the pre-separation mix: a vocal comb
destroyed by the separator would still be visible there, while a
remnant resonance keeps its single-bin no-comb signature.

classification:
    phonated              sustained periodicity + comb + context RMS
                          -> the disputed span is real voiced signal
    non_phonated_remnant  energy collapse AND claimed-f0 harmonics
                          at/below the unvoiced floor — positive
                          counter-evidence that the detected gesture
                          has no phonated source
    inconclusive          measurements cannot decide either way
"""
from __future__ import annotations

import numpy as np

FRAME_WIN_S = 0.025
FRAME_HOP_S = 0.010
F_LO_HZ, F_HI_HZ = 80.0, 1000.0

PHONATED_DROP_DB = 12.0       # span RMS may sit this far below context
REMNANT_DROP_DB = 15.0        # and still be a gesture; beyond = release
PHONATED_H2P_DROP_DB = 15.0   # h2+ level vs voiced reference
REMNANT_H2P_DROP_DB = 18.0    # h2+ this far below voiced ref = no comb
REMNANT_H2P_FLOOR_DB = 6.0    # or within 6 dB of the unvoiced floor
ACF_VOICED_MED = 0.60         # sustained periodicity floor for phonation
CLAIM_TOL_CENTS = 80.0        # measured best-lag vs claimed contour
MIN_SPAN_S = 0.030            # shorter than this cannot be measured
RELIABLE_ACF = 0.50           # per-frame floor for the f0 comparison


def _acf_frame(seg: np.ndarray, sr: int,
               f_lo: float = F_LO_HZ, f_hi: float = F_HI_HZ):
    """Best normalized ACF + best f0 of one frame over [f_lo, f_hi]."""
    seg = seg - seg.mean()
    if float(np.sqrt(np.mean(seg * seg))) < 1e-7:
        return 0.0, None
    r = np.correlate(seg, seg, "full")[len(seg) - 1:]
    if r[0] <= 0:
        return 0.0, None
    r = r / r[0]
    lo = max(2, int(sr / f_hi))
    hi = min(len(r) - 1, int(sr / f_lo))
    if lo >= hi:
        return 0.0, None
    lag = lo + int(np.argmax(r[lo:hi]))
    return float(r[lag]), float(sr / lag)


def _acf_at_lag(seg: np.ndarray, sr: int, lag_samp: float) -> float:
    """Normalized ACF in a +-3% window around a specific lag."""
    seg = seg - seg.mean()
    if float(np.sqrt(np.mean(seg * seg))) < 1e-7:
        return 0.0
    r = np.correlate(seg, seg, "full")[len(seg) - 1:]
    if r[0] <= 0:
        return 0.0
    r /= r[0]
    lo = max(2, int(lag_samp * 0.97))
    hi = min(len(r) - 1, int(np.ceil(lag_samp * 1.03)))
    if lo >= hi:
        return 0.0
    return float(r[lo:hi].max())


def _harmonic_band(seg: np.ndarray, sr: int, f0: float,
                   kmax: int = 6, bw: float = 0.02):
    """Per-harmonic power (dBFS) at k*f0 via Parseval on the windowed
    rfft.  A direct measurement of comb content at a hypothesized f0."""
    n = len(seg)
    if n < 256 or f0 is None or f0 <= 0:
        return None
    w = np.hanning(n)
    spec = np.fft.rfft(seg * w)
    fr = np.fft.rfftfreq(n, 1.0 / sr)
    w2 = float(np.mean(w * w))
    out = []
    for k in range(1, kmax + 1):
        f = k * f0
        if f > sr / 2:
            break
        m = (fr >= f * (1 - bw)) & (fr <= f * (1 + bw))
        p = 2.0 * float(np.sum(np.abs(spec[m]) ** 2)) / (n * n * w2)
        out.append(10.0 * np.log10(p + 1e-15))
    return out


def span_features(seg: np.ndarray, sr: int,
                  claimed_f0_hz: float | None = None,
                  hop_s: float = FRAME_HOP_S,
                  win_s: float = FRAME_WIN_S) -> dict:
    """Direct waveform measurements of one span (energy, periodicity,
    harmonic comb at the claimed f0).  All values are measurements —
    missing data stays None, never 0."""
    seg = np.asarray(seg, dtype=float)
    n_w = max(32, int(round(win_s * sr)))
    n_h = max(16, int(round(hop_s * sr)))
    rms, acf, f0t, acf_claim = [], [], [], []
    for a in range(0, max(1, len(seg) - n_w + 1), n_h):
        fr = seg[a:a + n_w]
        rms.append(20.0 * np.log10(np.sqrt(np.mean(fr * fr)) + 1e-12))
        c, f0 = _acf_frame(fr, sr)
        acf.append(c)
        f0t.append(f0)
        if claimed_f0_hz:
            acf_claim.append(_acf_at_lag(fr, sr, sr / claimed_f0_hz))
    f0_arr = [f for f in f0t if f is not None]
    feats = {
        "n_frames": len(acf),
        "rms_dbfs_med": (round(float(np.median(rms)), 1) if rms else None),
        "rms_dbfs_max": (round(float(np.max(rms)), 1) if rms else None),
        "acf_med": (round(float(np.median(acf)), 3) if acf else None),
        "acf_p90": (round(float(np.percentile(acf, 90)), 3)
                    if acf else None),
        "acf_track": [round(c, 3) for c in acf],
        "acf_at_claim_med": (round(float(np.median(acf_claim)), 3)
                             if acf_claim else None),
        "f0_best_track_hz": [round(f, 1) if f is not None else None
                             for f in f0t],
        "claimed_f0_hz": (round(float(claimed_f0_hz), 1)
                          if claimed_f0_hz else None),
    }
    f0_med = float(np.median(f0_arr)) if f0_arr else None
    feats["f0_best_med_hz"] = round(f0_med, 1) if f0_med else None
    hb = _harmonic_band(seg, sr, claimed_f0_hz or f0_med)
    if hb:
        feats["harmonic_band_dbfs"] = [round(x, 1) for x in hb]
        feats["h1_dbfs"] = round(hb[0], 1)
        if len(hb) > 1:
            h2p = float(sum(10.0 ** (x / 10.0) for x in hb[1:]))
            feats["h2p_max_dbfs"] = round(max(hb[1:]), 1)
            feats["h2p_sum_dbfs"] = round(10.0 * np.log10(h2p), 1)
            feats["comb_ratio_h2p_h1"] = round(
                h2p / max(10.0 ** (hb[0] / 10.0), 1e-15), 4)
    return feats


def _longest_run(mask: np.ndarray, grid: np.ndarray):
    """(start, end) seconds of the longest True run on a time grid."""
    best = cur = None
    for t, ok in zip(grid, mask):
        if ok and cur is None:
            cur = t
        if not ok and cur is not None:
            if best is None or t - cur > best[1] - best[0]:
                best = (cur, t)
            cur = None
    if cur is not None:
        t = float(grid[-1]) + (grid[1] - grid[0] if len(grid) > 1 else 0.0)
        if best is None or t - cur > best[1] - best[0]:
            best = (cur, t)
    return best


def span_voicing_evidence(voc_seg: np.ndarray, sr: int, *,
                          disputed: tuple[float, float],
                          ref_voiced: tuple[float, float],
                          ref_unvoiced: tuple[float, float] | None = None,
                          claimed_f0_hz: float | None = None,
                          alt_f0_hz: float | None = None,
                          mix_seg: np.ndarray | None = None,
                          mix_sr: int | None = None) -> dict:
    """Waveform voicing battery for one extractor-disputed span.

    Spans are (a, b) seconds relative to the start of voc_seg/mix_seg.
    `claimed_f0_hz` is the disputed extractor's f0 on the span (e.g.
    fcpe); `alt_f0_hz` is the opposing extractor's f0 where it is voiced
    (e.g. rmvpe) — used only for the `consistent_with` attribution.

    Returns a dict with per-span features, calibrated comparisons and a
    `classification` in {phonated, non_phonated_remnant, inconclusive}.
    """
    def cut(seg, srx, ab):
        if seg is None or ab is None:
            return None
        return seg[int(ab[0] * srx):int(ab[1] * srx)]

    out = {"schema": "voicing-evidence-1",
           "disputed_span_s": [round(disputed[0], 3),
                              round(disputed[1], 3)],
           "ref_voiced_s": ([round(ref_voiced[0], 3),
                             round(ref_voiced[1], 3)]
                            if ref_voiced else None),
           "ref_unvoiced_s": ([round(ref_unvoiced[0], 3),
                               round(ref_unvoiced[1], 3)]
                              if ref_unvoiced else None),
           "claimed_f0_hz": (round(float(claimed_f0_hz), 1)
                             if claimed_f0_hz else None),
           "alt_f0_hz": (round(float(alt_f0_hz), 1)
                         if alt_f0_hz else None)}
    if disputed[1] - disputed[0] < MIN_SPAN_S or ref_voiced is None:
        out["classification"] = "inconclusive"
        out["reason"] = "disputed span too short or no voiced reference"
        return out

    d = span_features(cut(voc_seg, sr, disputed), sr, claimed_f0_hz)
    v = span_features(cut(voc_seg, sr, ref_voiced), sr)
    u = span_features(cut(voc_seg, sr, ref_unvoiced), sr,
                      claimed_f0_hz) if ref_unvoiced else None
    md = span_features(cut(mix_seg, mix_sr, disputed), mix_sr,
                       claimed_f0_hz) if mix_seg is not None else None
    out["disputed"] = d
    out["ref_voiced"] = v
    out["ref_unvoiced"] = u
    out["mix_disputed"] = md

    drop = (v["rms_dbfs_med"] - d["rms_dbfs_med"]
            if v["rms_dbfs_med"] is not None
            and d["rms_dbfs_med"] is not None else None)
    h2p_drop = (v["h2p_max_dbfs"] - d["h2p_max_dbfs"]
                if v.get("h2p_max_dbfs") is not None
                and d.get("h2p_max_dbfs") is not None else None)
    u_floor = u.get("h2p_max_dbfs") if u else None
    out["energy_drop_db"] = round(drop, 1) if drop is not None else None
    out["h2p_drop_db"] = (round(h2p_drop, 1)
                          if h2p_drop is not None else None)
    out["h2p_vs_unvoiced_floor_db"] = (
        round(d["h2p_max_dbfs"] - u_floor, 1)
        if d.get("h2p_max_dbfs") is not None and u_floor is not None
        else None)

    # Periodicity is POSITIVE evidence and must be evaluated before a
    # low-level span can be called "non-phonated".  Absolute harmonic
    # power falls with amplitude, so h2+ being quiet in dBFS cannot by
    # itself distinguish a quiet voiced release from a passive resonance.
    reliable = [
        (f, a) for f, a in zip(d["f0_best_track_hz"], d["acf_track"])
        if f is not None and a >= RELIABLE_ACF
    ]
    periodic_fraction = (len(reliable) / max(1, d["n_frames"]))
    out["periodic_fraction"] = round(periodic_fraction, 3)

    def _close(a, b):
        return (a is not None and b is not None
                and abs(1200.0 * np.log2(a / b)) <= CLAIM_TOL_CENTS)

    claim_support = [
        f for f, _ in reliable if _close(f, claimed_f0_hz)
    ]
    alt_support = [
        f for f, _ in reliable if _close(f, alt_f0_hz)
    ]
    out["claim_support_fraction"] = round(
        len(claim_support) / max(1, d["n_frames"]), 3)
    out["alt_support_fraction"] = round(
        len(alt_support) / max(1, d["n_frames"]), 3)

    meas = [f for f, _ in reliable]
    meas_med = float(np.median(meas)) if meas else None
    out["measured_f0_med_hz"] = (round(meas_med, 1)
                                 if meas_med is not None else None)
    out["measured_f0_n_reliable"] = len(meas)

    if meas_med is not None and _close(meas_med, claimed_f0_hz):
        out["consistent_with"] = "claimed"
    elif meas_med is not None and _close(meas_med, alt_f0_hz):
        out["consistent_with"] = "alt"
    else:
        out["consistent_with"] = "none"

    # Compare COMB SHAPE after normalizing out the fundamental level.
    # A true single-bin remnant should lose h2+ relative to h1; simply
    # lowering the whole voiced spectrum is not counter-evidence.
    d_ratio = d.get("comb_ratio_h2p_h1")
    v_ratio = v.get("comb_ratio_h2p_h1")
    comb_rel_db = None
    if d_ratio is not None and v_ratio is not None             and d_ratio > 0 and v_ratio > 0:
        comb_rel_db = 10.0 * np.log10(d_ratio / v_ratio)
    out["comb_ratio_relative_db"] = (
        round(float(comb_rel_db), 1) if comb_rel_db is not None else None)

    # Positive phonation: either context-level sustained periodicity, or
    # a quiet span with a sustained reliable periodic track that follows
    # one of the competing F0 hypotheses.  Low amplitude alone must not
    # disqualify phonation.
    follows_hypothesis = out["consistent_with"] in ("claimed", "alt")
    phonated = (
        (drop is not None and drop <= PHONATED_DROP_DB
         and (d["acf_med"] or 0.0) >= ACF_VOICED_MED)
        or (periodic_fraction >= 0.50 and follows_hypothesis)
    )

    # Positive non-phonation is deliberately conservative.  It requires
    # an energy collapse PLUS absence of material periodic support.  If
    # a measurable periodic track survives, especially near a claimed
    # F0, the correct result is UNKNOWN/inconclusive rather than artifact.
    no_material_periodicity = (
        periodic_fraction < 0.20
        and out["claim_support_fraction"] < 0.10
        and out["alt_support_fraction"] < 0.10
    )
    normalized_comb_collapse = (
        comb_rel_db is not None and comb_rel_db <= -10.0
    )
    floor_like = (
        u_floor is not None
        and d.get("h2p_max_dbfs") is not None
        and d["h2p_max_dbfs"] <= u_floor + REMNANT_H2P_FLOOR_DB
    )
    non_phonated = (
        drop is not None and drop >= REMNANT_DROP_DB
        and no_material_periodicity
        and (normalized_comb_collapse or floor_like)
    )

    if phonated:
        cls = "phonated"
    elif non_phonated:
        cls = "non_phonated_remnant"
    else:
        cls = "inconclusive"
    out["classification"] = cls
    return out
