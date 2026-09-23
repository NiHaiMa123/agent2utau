"""L7 discriminating portamento probe (plan.md §12 "Required
discriminating portamento probe").

For every currently-blocking event-shape event (P2 note4 / P2 note8 /
P3 note9) this builds LOCAL event candidates on top of the committed v1
curve — outside the event window the candidate is byte-identical to v1:

  dense : inside [s,e] the PITD command is the measured SOURCE
          trajectory expressed in written-pitch coordinates,
          src_cents(t) - written(t), emitted as dense 10 ms points;
          generic simplification is bypassed inside the event.
  step  : inside [s,e] a deliberately different control shape — a
          piecewise-constant command that steps at the note boundary
          (flat departure level -> flat arrival level).  Both probes
          share the source endpoints; only the interior shape differs.
  inv   : inverse-response calibration probe, run ONLY when the source
          target is extractor-stable and `dense` failed to clear the
          gate: pitd_inv = pitd_dense + clip(src - resp_dense, +-300c)
          inside the window.  A response channel that is alive but
          miscalibrated is separated from a true capability limit.
  pdata : native pitch.data carrier probe, run ONLY when evidence is
          stable and `dense` did not clear the gate.  The measured
          SOURCE slide is encoded as negative-X pitch points on the
          TARGET note (snap_first=false so the first point is not
          overwritten to the previous tone), PITD inside the event is
          flattened to 0 so the note-level carrier is isolated.

Each candidate is real-rendered through the bridge and judged by the
SAME absolute event-shape gate as the phrase run, plus a
command-vs-response record.  Verdict rules (deterministic):

  source target unstable across extractors and the
    third family is also unvoiced/low-confidence       -> FAIL_EVIDENCE
  third family positively confirms the FCPE gesture
    that RMVPE rejected -> evidence rescued, candidates decide

Important evidence rule: a third extractor's missing/unvoiced/low-
confidence output is weak observability, not positive counter-evidence.
It may keep a target UNKNOWN but cannot by itself prove that an FCPE
gesture is an extraction artifact.  Automatic
EVIDENCE_ADJUDICATED_ARTIFACT therefore requires a separate positive
counter-evidence path — provided here by the direct waveform battery
(expression.voicing_evidence): measured energy collapse plus a missing
harmonic comb at the claimed f0 positively characterize the disputed
span as a non-phonated remnant, which is a measurement, not a
non-detection.
  dense probe clears the blocking shape             -> FAIL_FIXABLE
  materially different commands render to the same
    smoothed/incorrect shape                        -> FAIL_CAPABILITY
  otherwise                                         -> INCONCLUSIVE

`EVIDENCE_ADJUDICATED_ARTIFACT` is the explicit evidence adjudication
required by plan §12: a committed, hash-bound finding that the detected
SOURCE event is an extraction artifact, not a real gesture.

Artifacts per event under
runs/expr-20260921/probe_portamento/<phrase>_n<from_note>/.

Usage:
    .venv/Scripts/python.exe tools/l7_portamento_probe.py [P2_slides ...]
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l7_phrase_gate as drv                      # noqa: E402

from agent2utau.analysis.f0 import extract_f0     # noqa: E402
from agent2utau.analysis.rmvpe import infer_rmvpe  # noqa: E402
from agent2utau.diagnostic.adjudicate import (  # noqa: E402
    midi_to_hz, third_f0_pyin)
from agent2utau.expression import contour_qa as cq  # noqa: E402
from agent2utau.expression.contour import build_contour_signal  # noqa: E402
from agent2utau.expression.pitch_residual import TICK_MS  # noqa: E402
from agent2utau.expression.voicing_evidence import (  # noqa: E402
    _longest_run, span_voicing_evidence)
from agent2utau.openutau.ustx import (              # noqa: E402
    load_ustx, save_ustx, semantic_notes_sha256, sha256)
from agent2utau.resources.config import load_config  # noqa: E402

PROBE_DIR = drv.RUN_DIR / "probe_portamento"
HOP_S = 0.010

# verdict thresholds (normalized units of the source span)
EXTRACTOR_AGREE_RMSE = 0.25   # fcpe-vs-rmvpe source profile agreement
MIN_SRC_COVERAGE = 0.80       # same bound as source_irregular gate
DISTORTION_RMSE = 0.35        # contour_qa blocking threshold
MATERIAL_GAIN = 0.60          # probe must reach <=60% of v1 rmse
CMD_DIV_MIN = 0.30            # normalized rmse between the two commands
RESP_RATIO = 0.35             # resp_div <= RESP_RATIO*cmd_div -> same out
# third-family (librosa pYIN) evidence thresholds
# Low/non-voiced pYIN is NOT negative evidence (diagnostic.adjudicate
# contract); it can only leave the target unresolved.  pYIN can resolve
# disagreement automatically only through positive voiced contour support.
PYIN_RESCUE_COV = 0.80        # pYIN coverage needed to confirm a gesture
PYIN_PROB_MIN = 0.5           # voicing-probability floor


def _pyin_window(ctx, s, e):
    """Third-family (librosa pYIN) evidence inside [s,e] on SOURCE."""
    py = ctx.get("pyin")
    if py is None:
        return None
    t, midi, prob = py["times"], py["midi"], py["voiced_prob"]
    m = (t >= s) & (t <= e)
    if not m.sum():
        return {"coverage": 0.0, "n_frames": 0}
    voiced = np.isfinite(midi[m]) & (prob[m] >= PYIN_PROB_MIN)
    out = {"coverage": round(float(voiced.mean()), 3),
           "n_frames": int(m.sum()),
           "provenance": py["provenance"]}
    if voiced.sum() >= 3:
        cents = 100.0 * (midi[m][voiced] - 69.0)
        out["median_cents_rel_a4"] = round(float(np.median(cents)), 1)
    # disputed frames: fcpe voiced but rmvpe unvoiced inside the window
    fs, fv = ctx["src_sig"].times, ctx["src_sig"].voiced
    bs, bv = ctx["src_sig_b"].times, ctx["src_sig_b"].voiced
    fv_i = np.interp(t, fs, fv.astype(float), left=0.0, right=0.0) > 0.5
    bv_i = np.interp(t, bs, bv.astype(float), left=0.0, right=0.0) > 0.5
    disp = m & fv_i & ~bv_i
    if disp.sum() >= 3:
        dv = np.isfinite(midi[disp]) & (prob[disp] >= PYIN_PROB_MIN)
        out["disputed_frames"] = int(disp.sum())
        out["disputed_voiced_rate"] = round(float(dv.mean()), 3)
        if dv.sum() >= 3:
            dc = 100.0 * (midi[disp][dv] - 69.0)
            out["disputed_median_cents_rel_a4"] = round(
                float(np.median(dc)), 1)
    return out


def _written_cents(t, notes):
    """Carrier-note written pitch in cents; gap frames take the nearer
    side's tone (gap <=80ms by detector contract)."""
    out = np.full(len(t), np.nan)
    for i, n in enumerate(notes):
        s, e = n["abs_start_s"], n["abs_start_s"] + n["dur_s"]
        out[(t >= s) & (t < e)] = n["tone"] * 100.0
    # gap frames: assign the temporally nearer note's tone
    edges = []
    for i in range(len(notes) - 1):
        a_e = notes[i]["abs_start_s"] + notes[i]["dur_s"]
        b_s = notes[i + 1]["abs_start_s"]
        if b_s > a_e:
            edges.append((a_e, b_s, notes[i]["tone"] * 100.0,
                          notes[i + 1]["tone"] * 100.0))
    for a_e, b_s, ta, tb in edges:
        mid = 0.5 * (a_e + b_s)
        g = (t >= a_e) & (t < b_s)
        out[g & (t < mid)] = ta
        out[g & (t >= mid)] = tb
    return out


def _src_at(sig, t):
    """Source filtered cents at absolute t (nan when unvoiced)."""
    c = np.interp(t, sig.times, sig.cents, left=np.nan, right=np.nan)
    v = np.interp(t, sig.times, sig.voiced.astype(float),
                  left=0.0, right=0.0) > 0.5
    return np.where(v & ~np.isnan(c), c, np.nan)


def _curve_abs(curve, part_pos_tick):
    """pitd curve -> (abs_seconds, cents) arrays."""
    xs = np.asarray(curve["xs"], dtype=float) * TICK_MS / 1000.0 \
        + part_pos_tick * TICK_MS / 1000.0
    return xs, np.asarray(curve["ys"], dtype=float)


def _to_curve(xs_abs, ys, part_pos_tick):
    xn = np.round(np.asarray(xs_abs) * 1000.0 / TICK_MS
                  - part_pos_tick).astype(int)
    yn = np.clip(np.round(np.asarray(ys)), -1150, 1150).astype(int)
    o = np.argsort(xn, kind="stable")
    xn, yn = xn[o], yn[o]
    keep = np.concatenate([[True], np.diff(xn) > 0])
    return {"abbr": "pitd", "xs": xn[keep].tolist(),
            "ys": yn[keep].tolist()}


def build_probe_curve(curve_v1, part_pos_tick, notes, src_sig, s, e,
                      boundary_s, kind, inv_corr=None):
    """v1 outside [s,e]; inside, the probe command in written coords.

    inv_corr: optional (times, cents) additive correction sampled on the
    window grid — the inverse-response variant compensates the dense
    command by the dense render's measured residual.
    """
    xs_v, ys_v = _curve_abs(curve_v1, part_pos_tick)
    keep = (xs_v < s - 1e-9) | (xs_v > e + 1e-9)
    xs = list(xs_v[keep])
    ys = list(ys_v[keep])

    g = s + np.arange(int(round((e - s) / HOP_S)) + 1) * HOP_S
    w = _written_cents(g, notes)
    src = _src_at(src_sig, g)

    if kind in ("dense", "inv"):
        ok = ~np.isnan(src) & ~np.isnan(w)
        px, py = g[ok], src[ok] - w[ok]
        if kind == "inv" and inv_corr is not None:
            ct, cv = inv_corr
            py = py + np.interp(px, ct, cv, left=0.0, right=0.0)
        # anchor both edges to the nearest measured target so the command
        # covers the whole window even when edge frames are unvoiced
        if len(px):
            if px[0] > s + 1e-9:
                px = np.concatenate([[s], px])
                py = np.concatenate([[py[0]], py])
            if px[-1] < e - 1e-9:
                px = np.concatenate([px, [e]])
                py = np.concatenate([py, [py[-1]]])
    elif kind == "step":
        ok = ~np.isnan(src)
        if ok.sum() < 2:
            px = py = np.array([])
        else:
            c0 = float(src[ok][0])
            c1 = float(src[ok][-1])
            bnd = min(max(boundary_s, s), e)
            # one hop before the boundary still belongs to the departure
            # side; the two points stay >=1 tick apart after rounding
            b_pre = max(s, bnd - HOP_S)
            wb = _written_cents(np.array([s, b_pre, bnd, e]), notes)
            px = np.array([s, b_pre, bnd, e])
            py = np.array([c0 - wb[0], c0 - wb[1],
                           c1 - wb[2], c1 - wb[3]])
    else:
        raise ValueError(kind)

    xs.extend(px.tolist())
    ys.extend(py.tolist())
    return _to_curve(xs, ys, part_pos_tick)


def build_pdata_points(notes, from_note, src_sig, s, e):
    """Encode the measured SOURCE slide as pitch.data on the TARGET note.

    x is ms relative to the target note's start (negative = into the
    predecessor's span — the native cross-note portamento carrier), y is
    pitch offset from the target tone in 0.1-semitone units.  Anchors are
    sampled from the measured source contour at ~20ms spacing over
    [s-30ms, e+60ms] wherever the source is voiced; snap_first must be
    false or UNote.Validate rewrites data[0].y to the previous tone.
    """
    tgt = notes[from_note + 1]
    pos_s = tgt["abs_start_s"]
    tone_c = tgt["tone"] * 100.0
    g = np.arange(s - 0.030, e + 0.060 + 1e-9, 0.020)
    c = _src_at(src_sig, g)
    pts = []
    last_x = None
    for t, cc in zip(g, c):
        if np.isnan(cc):
            continue
        x_ms = (t - pos_s) * 1000.0
        if last_x is not None and x_ms - last_x < 5.0:
            continue                      # keep >=5ms spacing
        pts.append({"x": round(float(x_ms), 1),
                    "y": round(float((cc - tone_c) / 10.0), 2),
                    "shape": "io"})
        last_x = x_ms
    if len(pts) < 2:
        return None
    return {"data": pts, "snap_first": False}


def _flat_pitd(curve_v1, part_pos_tick, s, e):
    """v1 curve outside [s-30ms, e+160ms]; inside, deviation pinned to 0
    so the pitch.data carrier is measured without a PITD assist."""
    a, b = s - 0.030, e + 0.160
    xs_v, ys_v = _curve_abs(curve_v1, part_pos_tick)
    keep = (xs_v < a - 1e-9) | (xs_v > b + 1e-9)
    xs = list(xs_v[keep]); ys = list(ys_v[keep])
    for t, y in [(a - 0.012, np.interp(a - 0.012, xs_v, ys_v)),
                 (a, 0.0), (b, 0.0),
                 (b + 0.012, np.interp(b + 0.012, xs_v, ys_v))]:
        xs.append(t); ys.append(y)
    return _to_curve(np.asarray(xs), np.asarray(ys), part_pos_tick)


def _load_render(wav, notes, t0, t1, nuc=None):
    f = extract_f0(wav)
    r = infer_rmvpe(wav)
    sig = build_contour_signal(f, r, notes, t0_s=t0, t1_s=t1,
                               extractor="fcpe", source="render")
    sig_b = build_contour_signal(r, f, notes, t0_s=t0, t1_s=t1,
                                 extractor="rmvpe", source="render")
    return {"wav": Path(wav), "sig": sig, "sig_b": sig_b,
            "events": drv.detect_all(sig, notes, nuc or {}),
            "events_b": drv.detect_all(sig_b, notes, nuc or {})}


def _cn(sig, s, e, c0, span):
    return cq._cn_profile(sig, s, e, c0, span)


def _own_cn(sig, s, e):
    p = cq._traj_profile(sig.times,
                         np.where(sig.voiced, sig.cents, np.nan), s, e)
    if p is None:
        return None
    return np.interp(np.linspace(0.0, 1.0, 33),
                     np.linspace(0.0, 1.0, len(p["cn"])), p["cn"])


def _event_row(es, from_note):
    for r in es.get("events", []):
        if r["from_note"] == from_note:
            return r
    return None


def probe_event(phrase, from_note, ctx, cfg, head):
    pdir = PROBE_DIR / f"{phrase}_n{from_note}"
    pdir.mkdir(parents=True, exist_ok=True)
    notes = ctx["notes"]
    ev = ctx["src_event_by_from"].get(from_note)
    if ev is None:
        # The detector no longer reports a SOURCE portamento at this
        # index (e.g. re-detection after a fix).  If the committed row is
        # non-blocking and the lane owns it, the issue is resolved in
        # production; otherwise the evidence stays unresolved.
        committed = ctx["committed_rows"].get(from_note) or {}
        return {"phrase": phrase, "from_note": from_note,
                "verdict": ("RESOLVED"
                            if committed and not committed.get("blocking")
                            else "FAIL_EVIDENCE"),
                "reasons": ["source portamento event not detected on "
                            "rerun"],
                "committed_event": committed}
    s, e = ev.start_s, ev.end_s
    bnd = notes[from_note + 1]["abs_start_s"] \
        if from_note + 1 < len(notes) else 0.5 * (s + e)

    # committed blocking-evidence binding: window must match the
    # recorded event-shape row (detector rerun drift is reported, not
    # silently accepted)
    committed = ctx["committed_rows"].get(from_note) or {}
    win_drift_ms = None
    if committed.get("window_s"):
        win_drift_ms = round(max(
            abs(committed["window_s"][0] - s),
            abs(committed["window_s"][1] - e)) * 1000.0, 1)

    # --- step 1: target observability across extractor families ------
    ms = (ctx["src_sig"].times >= s) & (ctx["src_sig"].times <= e) \
        & ctx["src_sig"].voiced & ~np.isnan(ctx["src_sig"].cents)
    win_b = (ctx["src_sig_b"].times >= s) & (ctx["src_sig_b"].times <= e)
    src_cov_b = float(ctx["src_sig_b"].voiced[win_b].mean()) \
        if win_b.sum() else 0.0
    src_cov = float(ctx["src_sig"].voiced[
        (ctx["src_sig"].times >= s) & (ctx["src_sig"].times <= e)].mean())
    pa_own = _own_cn(ctx["src_sig"], s, e)
    pb_own = _own_cn(ctx["src_sig_b"], s, e)
    ext_rmse = float(np.sqrt(np.mean((pa_own - pb_own) ** 2))) \
        if pa_own is not None and pb_own is not None else None
    evidence_stable = (ext_rmse is not None
                       and ext_rmse <= EXTRACTOR_AGREE_RMSE
                       and src_cov >= MIN_SRC_COVERAGE)

    # --- third-family evidence (committed librosa pYIN) --------------
    pyin = _pyin_window(ctx, s, e)
    adjudication = None
    adjudication_basis = None
    rescued = False
    third_family_non_detection = False
    if not evidence_stable and pyin is not None:
        disp_n = pyin.get("disputed_frames", 0)
        disp_v = pyin.get("disputed_voiced_rate")
        third_family_non_detection = (
            disp_n >= 3 and disp_v is not None and disp_v < 0.30)
        # Per diagnostic.adjudicate, non-detection / low confidence is
        # weak reliability, never opposition.  pYIN may RESCUE FCPE by
        # positively tracing the same voiced contour, but it may not
        # turn UNKNOWN into "artifact" merely by being unvoiced.
        if pyin["coverage"] >= PYIN_RESCUE_COV:
            cents = np.where(
                np.isfinite(ctx["pyin"]["midi"])
                & (ctx["pyin"]["voiced_prob"] >= PYIN_PROB_MIN),
                ctx["pyin"]["midi"] * 100.0, np.nan)
            from types import SimpleNamespace
            psig = SimpleNamespace(
                times=ctx["pyin"]["times"], cents=cents,
                voiced=np.isfinite(cents))
            pc = _own_cn(psig, s, e)
            if pc is not None and pa_own is not None and \
                    float(np.sqrt(np.mean((pc - pa_own) ** 2))) \
                    <= EXTRACTOR_AGREE_RMSE:
                rescued = True
                evidence_stable = True

    # --- waveform voicing battery (positive evidence, plan §12 R-A) ---
    # Runs only when the two F0 families still disagree after the pYIN
    # rescue attempt.  It measures the disputed (fcpe-voiced /
    # rmvpe-unvoiced) span directly: energy, periodicity and the
    # harmonic comb at the claimed f0, calibrated against the window's
    # own both-voiced and both-unvoiced spans.  A non-phonated remnant
    # result is POSITIVE counter-evidence (measured, not absent data)
    # and adjudicates the detected event as an extraction artifact.
    waveform = None
    waveform_resolved = None
    if not evidence_stable and ctx.get("voc") is not None:
        fs, fv = ctx["src_sig"].times, ctx["src_sig"].voiced
        bs, bv = ctx["src_sig_b"].times, ctx["src_sig_b"].voiced
        tg = np.arange(s, e + 1e-9, HOP_S)
        f_v = np.interp(tg, fs, fv.astype(float)) > 0.5
        b_v = np.interp(tg, bs, bv.astype(float)) > 0.5
        disp_t = tg[f_v & ~b_v]
        ref_v = _longest_run(f_v & b_v, tg)
        tg_all = np.arange(ctx["t0"], ctx["t1"] + 1e-9, HOP_S)
        f_all = np.interp(tg_all, fs, fv.astype(float)) > 0.5
        b_all = np.interp(tg_all, bs, bv.astype(float)) > 0.5
        ref_u = _longest_run(~f_all & ~b_all, tg_all)
        if len(disp_t) >= 3 and ref_v is not None:
            claimed_c = np.nanmedian(_src_at(ctx["src_sig"], disp_t))
            claimed = midi_to_hz(claimed_c / 100.0) \
                if np.isfinite(claimed_c) else None
            alt_t = tg[b_v]
            alt_c = np.nanmedian(_src_at(ctx["src_sig_b"], alt_t)) \
                if len(alt_t) else np.nan
            alt = midi_to_hz(alt_c / 100.0) if np.isfinite(alt_c) else None
            rel = lambda ab: (ab[0] - ctx["t0"], ab[1] - ctx["t0"]) \
                if ab else None
            waveform = span_voicing_evidence(
                ctx["voc"]["seg"], ctx["voc"]["sr"],
                disputed=rel((float(disp_t[0]) - 0.005,
                            float(disp_t[-1]) + 0.005)),
                ref_voiced=rel(ref_v), ref_unvoiced=rel(ref_u),
                claimed_f0_hz=claimed, alt_f0_hz=alt,
                mix_seg=(ctx.get("mix") or {}).get("seg"),
                mix_sr=(ctx.get("mix") or {}).get("sr"))
            waveform["vocal_sha256"] = ctx["voc"]["sha256"]
            if ctx.get("mix"):
                waveform["mix_path"] = ctx["mix"]["path"]
                waveform["mix_sha256"] = ctx["mix"]["sha256"]
            if waveform["classification"] == "phonated":
                if waveform["consistent_with"] == "claimed":
                    evidence_stable = True
                    waveform_resolved = "fcpe"
                elif waveform["consistent_with"] == "alt":
                    waveform_resolved = "rmvpe"
            elif waveform["classification"] == "non_phonated_remnant":
                adjudication = "artifact"
                adjudication_basis = "positive_counterevidence"

    c0 = float(ctx["src_sig"].cents[ms][0]) if ms.sum() else 0.0
    span = float(ctx["src_sig"].cents[ms][-1] - c0) if ms.sum() else 1e-6
    if abs(span) < 1e-6:
        span = 1e-6

    v1_curve = next(c for c in ctx["v1_part"]["curves"]
                    if c["abbr"] == "pitd")
    es_v1 = cq.event_shape_gate(ctx["src_events"], ctx["v1"]["events"],
                                ctx["neu_sig"], ctx["src_sig"],
                                ctx["v1"]["sig"])
    row_v1 = _event_row(es_v1, from_note)

    report = {"phrase": phrase, "from_note": int(from_note),
              "window_s": [round(s, 3), round(e, 3)],
              "boundary_s": round(bnd, 3),
              "committed_window_s": committed.get("window_s"),
              "window_drift_ms": win_drift_ms,
              "v1_event": row_v1,
              "evidence": {
                  "src_coverage": round(src_cov, 3),
                  "extractor_cn_rmse": (round(ext_rmse, 3)
                                       if ext_rmse is not None else None),
                  "src_coverage_rmvpe": round(src_cov_b, 3),
                  "third_f0_pyin": pyin,
                  "waveform": waveform,
                  "waveform_resolved": waveform_resolved,
                  "adjudication": adjudication,
                  "adjudication_basis": adjudication_basis,
                  "third_family_non_detection": third_family_non_detection,
                  "rescued_by_pyin": rescued,
                  "stable": bool(evidence_stable)},
              "candidates": {}}

    # --- fast paths that need no renders -------------------------------
    if adjudication == "artifact":
        report["verdict"] = "EVIDENCE_ADJUDICATED_ARTIFACT"
        report["reasons"] = [
            "positive waveform counter-evidence: the fcpe-voiced/"
            "rmvpe-unvoiced span is a non-phonated remnant — rms %s dB "
            "below the both-voiced reference and the claimed-f0 harmonic "
            "band %s dB below it (floor-level); the detected gesture has "
            "no sung-pitch source"
            % ((waveform or {}).get("energy_drop_db"),
               (waveform or {}).get("h2p_drop_db"))]
        return report
    if waveform_resolved == "rmvpe":
        report["verdict"] = "EVIDENCE_RESOLVED_RMVPE"
        report["reasons"] = [
            "waveform battery: disputed span is phonated but its "
            "measured period (%s Hz) follows the rmvpe contour, not the "
            "fcpe event"
            % (waveform or {}).get("measured_f0_med_hz")]
        return report
    if from_note not in ctx["blocking_set"]:
        if not evidence_stable:
            report["verdict"] = "FAIL_EVIDENCE"
            report["reasons"] = [
                "source target not extractor-consistent "
                "(ext_rmse=%s, coverage=%.3f)" % (ext_rmse, src_cov)]
        else:
            c_row = committed or {}
            report["verdict"] = "FAIL_FIXABLE"
            report["reasons"] = [
                "resolved in production: committed event-shape row is "
                "non-blocking (class=%s cn_rmse=%s) under the native "
                "pitch.data lane" % (c_row.get("class"),
                                     c_row.get("cn_rmse_clean"))]
        return report

    resp_by_kind = {}
    cmd_by_kind = {}
    # dense runs first; when the source target is extractor-stable but
    # dense does not clear the gate, the inverse-response probe is built
    # from the dense render's measured residual.  When evidence is
    # unstable the inv probe is skipped — tuning against unknown truth
    # is not a discriminating experiment.
    kinds = ["dense", "step"]
    if evidence_stable:
        kinds += ["inv", "pdata"]
    inv_corr = None
    pdata_pitch = (build_pdata_points(notes, from_note, ctx["src_sig"],
                                    s, e)
                   if evidence_stable and from_note + 1 < len(notes)
                   else None)
    for kind in kinds:
        if kind in ("inv", "pdata"):
            d_rmse_pre = (report["candidates"]["dense"]
                          .get("event_row") or {}).get("cn_rmse_clean")
            if d_rmse_pre is not None and d_rmse_pre <= DISTORTION_RMSE:
                continue                  # dense already cleared it
            if kind == "inv" and inv_corr is None:
                continue
            if kind == "pdata" and pdata_pitch is None:
                continue
        if kind == "pdata":
            curve = _flat_pitd(v1_curve, ctx["part_pos"], s, e)
        else:
            curve = build_probe_curve(v1_curve, ctx["part_pos"], notes,
                                      ctx["src_sig"], s, e, bnd, kind,
                                      inv_corr=inv_corr)
        doc = copy.deepcopy(ctx["v1_doc"])
        for i, c in enumerate(doc["voice_parts"][0]["curves"]):
            if c["abbr"] == "pitd":
                doc["voice_parts"][0]["curves"][i] = curve
        if kind == "pdata" and pdata_pitch is not None:
            tgt_tick = notes[from_note + 1]["_abs_tick"] - ctx["part_pos"]
            for n in doc["voice_parts"][0]["notes"]:
                if n["position"] == tgt_tick:
                    n["pitch"] = pdata_pitch
        ustx = pdir / f"{phrase}_n{from_note}_{kind}.ustx"
        save_ustx(doc, ustx)
        rec = _load_render(drv.render(cfg, ustx,
                                      pdir / f"{phrase}_n{from_note}_{kind}"),
                           notes, ctx["t0"], ctx["t1"], ctx["nuc"])
        es = cq.event_shape_gate(ctx["src_events"], rec["events"],
                                 ctx["neu_sig"], ctx["src_sig"], rec["sig"])
        row = _event_row(es, from_note)

        g = s + np.arange(int(round((e - s) / HOP_S)) + 1) * HOP_S
        w = _written_cents(g, notes)
        cx, cy = _curve_abs(curve, ctx["part_pos"])
        cmd_pitd = np.interp(g, cx, cy, left=np.nan, right=np.nan)
        cmd_target = w + cmd_pitd
        r_at = np.interp(g, rec["sig"].times, rec["sig"].cents,
                         left=np.nan, right=np.nan)
        rv = np.interp(g, rec["sig"].times,
                       rec["sig"].voiced.astype(float),
                       left=0.0, right=0.0) > 0.5
        src_at = _src_at(ctx["src_sig"], g)
        shared = rv & ~np.isnan(r_at) & ~np.isnan(cmd_target)
        cmd_resp_rmse_c = float(np.sqrt(np.mean(
            (r_at[shared] - cmd_target[shared]) ** 2))) \
            if shared.sum() >= 3 else None
        cmd_n = (cmd_target - c0) / span
        resp_n = (r_at - c0) / span
        resp_by_kind[kind] = resp_n
        cmd_by_kind[kind] = cmd_n
        if kind == "dense":
            # inverse-response correction for a follow-up probe:
            # additive model residual, clipped, only where both the
            # source target and the dense render are observed.
            res = np.clip(src_at - r_at, -300.0, 300.0)
            okr = ~np.isnan(res)
            inv_corr = (g[okr], res[okr])

        control = {
            "times_s": np.round(g, 3).tolist(),
            "written_cents": np.round(w, 1).tolist(),
            "pitd_cmd_cents": np.round(cmd_pitd, 1).tolist(),
            "command_target_cents": np.round(cmd_target, 1).tolist(),
            "render_cents": np.round(r_at, 1).tolist(),
            "render_voiced": rv.tolist(),
            "src_cents": np.round(src_at, 1).tolist(),
            "command_norm_srcframe": np.round(cmd_n, 3).tolist(),
            "response_norm_srcframe": np.round(resp_n, 3).tolist(),
            "cmd_resp_rmse_c": (round(cmd_resp_rmse_c, 1)
                                if cmd_resp_rmse_c is not None else None)}
        drv._dump(control, pdir / f"control_response_{kind}.json")
        drv._dump(es, pdir / f"event_shape_{kind}.json")
        report["candidates"][kind] = {
            "ustx": ustx.name, "ustx_sha256": sha256(ustx),
            "wav": rec["wav"].name, "wav_sha256": sha256(rec["wav"]),
            "event_row": row,
            "cmd_resp_rmse_c": control["cmd_resp_rmse_c"],
            "n_blocking_total": es["n_blocking"],
            "gate_passed": es["gate_passed"]}

    # --- discrimination between the two commands --------------------
    cmd_div = resp_div = None
    if "dense" in cmd_by_kind and "step" in cmd_by_kind:
        ok = ~np.isnan(cmd_by_kind["dense"]) \
            & ~np.isnan(cmd_by_kind["step"])
        cmd_div = float(np.sqrt(np.mean(
            (cmd_by_kind["dense"][ok] - cmd_by_kind["step"][ok]) ** 2))) \
            if ok.sum() >= 3 else None
        okr = ok & ~np.isnan(resp_by_kind["dense"]) \
            & ~np.isnan(resp_by_kind["step"])
        resp_div = float(np.sqrt(np.mean(
            (resp_by_kind["dense"][okr]
             - resp_by_kind["step"][okr]) ** 2))) \
            if okr.sum() >= 3 else None
    report["discrimination"] = {
        "cmd_divergence_norm": (round(cmd_div, 3)
                                if cmd_div is not None else None),
        "resp_divergence_norm": (round(resp_div, 3)
                                 if resp_div is not None else None)}

    # --- verdict ------------------------------------------------------
    v1_rmse = (row_v1 or {}).get("cn_rmse_clean")
    d_row = report["candidates"]["dense"]["event_row"] or {}
    d_rmse = d_row.get("cn_rmse_clean")
    i_row = (report["candidates"].get("inv") or {}).get("event_row") or {}
    i_rmse = i_row.get("cn_rmse_clean")
    p_row = (report["candidates"].get("pdata") or {}).get("event_row") or {}
    p_rmse = p_row.get("cn_rmse_clean")
    reasons = []

    def _cleared(rmse, row):
        return rmse is not None and (
            rmse <= DISTORTION_RMSE
            or (v1_rmse is not None and rmse <= MATERIAL_GAIN * v1_rmse
                and row.get("class") != "distortion"))

    if not evidence_stable:
        verdict = "FAIL_EVIDENCE"
        reasons.append("source target not extractor-consistent "
                       "(ext_rmse=%s, coverage=%.3f)"
                       % (ext_rmse, src_cov))
        if third_family_non_detection:
            reasons.append(
                "pYIN is also unvoiced/low-confidence on the disputed "
                "frames; under the evidence contract this confirms weak "
                "observability, not that the FCPE gesture is false")
    elif _cleared(d_rmse, d_row):
        verdict = "FAIL_FIXABLE"
        reasons.append("dense written-coords candidate clears the "
                       "blocking shape (v1 %.3f -> probe %.3f)"
                       % (v1_rmse or -1, d_rmse))
    elif _cleared(p_rmse, p_row):
        verdict = "FAIL_FIXABLE"
        reasons.append("native pitch.data carrier clears the blocking "
                       "shape (v1 %.3f -> dense %.3f -> pdata %.3f, "
                       "class=%s) — implement the portamento lane on "
                       "note pitch.data"
                       % (v1_rmse or -1, d_rmse or -1, p_rmse,
                          p_row.get("class")))
    elif _cleared(i_rmse, i_row):
        verdict = "FAIL_FIXABLE"
        reasons.append("inverse-response candidate clears the blocking "
                       "shape (v1 %.3f -> dense %.3f -> inv %.3f); the "
                       "channel is alive but miscalibrated"
                       % (v1_rmse or -1, d_rmse or -1, i_rmse))
    elif (cmd_div is not None and cmd_div >= CMD_DIV_MIN
          and resp_div is not None
          and resp_div <= RESP_RATIO * cmd_div):
        verdict = "FAIL_CAPABILITY"
        reasons.append("command divergence %.3f renders to response "
                       "divergence %.3f (ratio %.2f) — different local "
                       "curves produce the same smoothed output"
                       % (cmd_div, resp_div, resp_div / cmd_div))
    elif i_rmse is not None:
        verdict = "FAIL_CAPABILITY"
        reasons.append("dense (%.3f) and inverse-response (%.3f) both "
                       "stay blocked — the renderer cannot express the "
                       "verified 40ms-scale target through PITD"
                       % (d_rmse or -1, i_rmse))
    else:
        verdict = "INCONCLUSIVE"
        reasons.append("probe moved the shape but neither cleared it nor "
                       "showed a flat response channel")
    report["verdict"] = verdict
    report["reasons"] = reasons
    return report


def run_phrase(phrase, cfg, base_doc, caches, head):
    w0, w1 = drv.PHRASES[phrase]
    t0, t1 = w0 - drv.PAD_S, w1 + drv.PAD_S
    pdir = drv.PHRASE_DIR / phrase
    man = json.loads((pdir / "run_manifest.json").read_text("utf-8"))
    committed_es = json.loads(
        (pdir / "qa" / "event_shape_metrics.json").read_text("utf-8"))
    blocking = {r["from_note"] for r in committed_es["events"]
                if r.get("blocking")}
    # Evidence authority must cover every event the previous probe
    # report classified, not only the currently-blocking set — a
    # FAIL_EVIDENCE note keeps its UNKNOWN status in the evaluator until
    # a clean-head report re-adjudicates it.
    prev_p = PROBE_DIR / f"{phrase}_probe_report.json"
    prev = drv._jsonable(json.loads(prev_p.read_text("utf-8"))) \
        if prev_p.exists() else {}
    targets = sorted(blocking |
                     {int(r["from_note"]) for r in prev.get("events", [])
                      if r.get("from_note") is not None})
    if not targets:
        print(f"== {phrase}: no blocking events, skipped", flush=True)
        return None
    print(f"== {phrase}: probe targets {targets} "
          f"(blocking {sorted(blocking)})", flush=True)

    base_part, notes = drv.phrase_notes(base_doc, w0, w1)
    part_pos = notes[0]["_abs_tick"] - 480
    nuc = drv.nucleus_times(notes)

    src_sig = build_contour_signal(caches["src_fcpe"], caches["src_rmvpe"],
                                   notes, t0_s=t0, t1_s=t1,
                                   extractor="fcpe", source="source")
    src_sig_b = build_contour_signal(caches["src_rmvpe"],
                                     caches["src_fcpe"], notes,
                                     t0_s=t0, t1_s=t1,
                                     extractor="rmvpe", source="source")
    neu_sig = build_contour_signal(caches["neu_fcpe"], caches["neu_rmvpe"],
                                   notes, t0_s=t0, t1_s=t1,
                                   extractor="fcpe", source="neutral")
    src_events = drv.detect_all(src_sig, notes, nuc)

    v1_ustx = pdir / f"{phrase}_C3.ustx"
    v1_doc = load_ustx(v1_ustx)
    v1_part = v1_doc["voice_parts"][0]
    assert int(v1_part["position"]) == part_pos, \
        (v1_part["position"], part_pos)
    v1_wav = Path(man["render_wav_path"])
    assert v1_wav.exists(), v1_wav
    v1 = _load_render(v1_wav, notes, t0, t1, nuc)

    # Third extractor family on the SOURCE vocal, once per phrase.
    import soundfile as sf
    wav, sr = sf.read(str(drv.SRC_VOCAL), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    seg = wav[int(t0 * sr):int(t1 * sr)]
    pyin = third_f0_pyin(seg, sr)
    pyin["times"] = pyin["times"] + t0
    print(f"   pyin: {int(pyin['voiced_prob'].shape[0])} frames "
          f"@ {pyin['provenance']['frame_period_s']*1000:.0f}ms",
          flush=True)

    # Waveform-battery inputs: the separated vocal segment (above) plus
    # the pre-separation mix for corroboration — a comb destroyed by the
    # separator would still show on the mix, a remnant resonance does
    # not change character.
    voc = {"seg": seg, "sr": sr, "path": str(drv.SRC_VOCAL),
           "sha256": sha256(drv.SRC_VOCAL)}
    mix_path = drv.SRC_VOCAL.with_name("original.wav")
    mix = None
    if mix_path.is_file():
        mw, msr = sf.read(str(mix_path), dtype="float32")
        if mw.ndim > 1:
            mw = mw.mean(axis=1)
        mix = {"seg": mw[int(t0 * msr):int(t1 * msr)], "sr": msr,
               "path": str(mix_path), "sha256": sha256(mix_path)}

    ctx = {"notes": notes, "part_pos": part_pos, "t0": t0, "t1": t1,
           "nuc": nuc,
           "src_sig": src_sig, "src_sig_b": src_sig_b,
           "neu_sig": neu_sig, "src_events": src_events,
           "pyin": pyin,
           "voc": voc, "mix": mix,
           "blocking_set": blocking,
           "src_event_by_from": {
               e.params["from_note"]: e for e in src_events
               if e.type == "portamento"},
           "committed_rows": {r["from_note"]: r
                              for r in committed_es["events"]},
           "v1_doc": v1_doc, "v1_part": v1_part, "v1": v1}

    reports = [probe_event(phrase, fn, ctx, cfg, head)
               for fn in targets]
    out = {"phrase": phrase, "generator_code_head": head,
           "qa_code_head": drv._git_head(),
           "worktree_clean_at_generation": True,
           "base_file_sha256": sha256(drv.BASE_USTX),
           "base_semantic_sha256": semantic_notes_sha256(base_doc),
           "v1_ustx_sha256": sha256(v1_ustx),
           "v1_wav_sha256": sha256(v1_wav),
           "v1_manifest_variant": man["variant"],
           "events": reports}
    drv._dump(out, PROBE_DIR / f"{phrase}_probe_report.json")
    for r in reports:
        print(f"   note{r['from_note']}: {r['verdict']} — "
              f"{'; '.join(r['reasons'])}", flush=True)
    return out


def main():
    head = drv._require_clean_worktree("l7_portamento_probe")
    cfg = load_config()
    which = sys.argv[1:] or list(drv.PHRASES)
    base_doc = load_ustx(drv.BASE_USTX)
    caches = {"src_fcpe": drv._npz_f0(drv.SRC_FCPE),
              "src_rmvpe": drv._npz_f0(drv.SRC_RMVPE),
              "neu_fcpe": drv._npz_f0(drv.NEU_FCPE),
              "neu_rmvpe": drv._npz_f0(drv.NEU_RMVPE)}
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    for phrase in which:
        run_phrase(phrase, cfg, base_doc, caches, head)


if __name__ == "__main__":
    main()
