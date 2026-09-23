"""L7 Round F — P2 'wo de ben' periodic-ownership causal A/B.

Hypothesis under test (plan.md Round F): the accepted P2 tail note "ben"
(n11) carries BOTH full-length native vibrato (~7.07 Hz / 74 c, out=0)
AND an oscillatory PITD component over the same interval, so the same
periodic gesture is rendered twice -> piercing / excessively shaky.

Discriminating A/B:
    A = frozen v165c baseline (already rendered in Round E)
    B = identical bytes except PITD ys inside native-vibrato-owned
        intervals: the periodic component at the native vibrato rate is
        removed via windowed least-squares sinusoid subtraction; trend
        and non-periodic local residual are preserved.

Verdict classes (fixed by round contract):
    PASS_CAUSAL / FAIL_CAPABILITY / FAIL_STRATEGY / FAIL_EVIDENCE.

Output: runs/expr-20260921/rebaseline/P2_slides/round_f/
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l7_phrase_gate as drv                          # noqa: E402
import l7e_listening_evidence as lev                  # noqa: E402
from agent2utau.analysis.f0 import extract_f0         # noqa: E402
from agent2utau.openutau.ustx import load_ustx, save_ustx, sha256  # noqa: E402
from agent2utau.resources.config import load_config   # noqa: E402
from agent2utau.expression.pitch_residual import TICK_MS  # noqa: E402

PHRASE = "P2_slides"
BASE_USTX = (drv.RUN_DIR / "rebaseline" / PHRASE /
             "P2_slides_C3v2_v165c.ustx")
BASE_WAV = (drv.RUN_DIR / "rebaseline" / PHRASE /
            "P2_slides_C3v2_v165c_vocal.wav")
OUT_DIR = drv.RUN_DIR / "rebaseline" / PHRASE / "round_f"
REPORT = OUT_DIR / "l7f_periodic_ownership_report.json"
LISTEN_USTX = OUT_DIR / "agent2utau_L7F_P2_AB.ustx"

TARGET_NOTES = (8, 9, 10, 11)          # "wo de ben" span per Round F
GRID_S = 0.005                          # 5 ms analysis grid
TAPER_S = 0.040                         # subtraction edge taper
RATE_TOL = 0.20                         # residual rate ~= native rate
EXPLAINED_MIN = 0.30                    # periodic share of residual var
DEPTH_MIN_C = 20.0                      # min periodic depth to matter


def _tick_s(part, tick):
    return (part["position"] + tick) * TICK_MS / 1000.0


def _vibrato_owned_intervals(part):
    """Native-vibrato-owned intervals: vibrato occupies the TAIL
    `length`% of the note (OpenUtau semantics)."""
    out = []
    for i, n in enumerate(part["notes"]):
        v = n.get("vibrato") or {}
        ln = float(v.get("length") or 0.0)
        if ln <= 0:
            continue
        a = _tick_s(part, n["position"])
        d = n["duration"] * TICK_MS / 1000.0
        start = a + d * (1.0 - ln / 100.0)
        out.append({"note": i, "start_s": round(start, 4),
                    "end_s": round(a + d, 4),
                    "vibrato": dict(v),
                    "rate_hz": round(1000.0 / float(v["period"]), 3)})
    return out


def _pitd_series(part):
    cur = next(c for c in part["curves"] if c["abbr"] == "pitd")
    xs = (np.asarray(cur["xs"], float) + part["position"]) \
        * TICK_MS / 1000.0
    return cur, xs, np.asarray(cur["ys"], float)


def _detrend(t, y, win_s):
    """Median detrend over `win_s` (linear interp grid)."""
    k = max(3, int(round(win_s / (t[1] - t[0]))))
    if k % 2 == 0:
        k += 1
    med = np.array([np.median(y[max(0, i - k // 2): i + k // 2 + 1])
                    for i in range(len(y))])
    return y - med, med


def _dominant_rate(t, r, f_lo=4.0, f_hi=10.0):
    """Peak frequency of residual in the vibrato band via DFT."""
    if len(r) < 16:
        return None, 0.0
    w = np.hanning(len(r))
    sp = np.abs(np.fft.rfft(r * w))
    fr = np.fft.rfftfreq(len(r), t[1] - t[0])
    m = (fr >= f_lo) & (fr <= f_hi)
    if not m.any() or sp[m].max() <= 0:
        return None, 0.0
    i = np.argmax(sp[m])
    freqs = fr[m]
    return float(freqs[i]), float(sp[m][i])


def _periodic_estimate(t, r, f_vib):
    """Windowed least-squares a*sin+b*cos at f_vib, Hann windows of
    two periods, 50% overlap, overlap-add normalised."""
    win = 2.0 / f_vib
    step = win / 2.0
    p = np.zeros_like(r)
    wsum = np.zeros_like(r)
    tc = t[0] + win / 2.0
    while tc <= t[-1] - win / 2.0 + 1e-9:
        m = (t >= tc - win / 2.0) & (t < tc + win / 2.0)
        if m.sum() >= 8:
            tt = t[m]
            w = np.hanning(m.sum())
            s = np.sin(2 * np.pi * f_vib * tt)
            c = np.cos(2 * np.pi * f_vib * tt)
            A = np.column_stack([s * w, c * w])
            coef, *_ = np.linalg.lstsq(A, r[m], rcond=None)
            p[m] += (coef[0] * s + coef[1] * c) * w
            wsum[m] += w
        tc += step
    nz = wsum > 1e-6
    p[nz] /= wsum[nz]
    return p


def _modulation(f0, t0, t1, f_vib, src_off=0.0):
    """Detrended modulation stats of an F0 track inside [t0,t1]."""
    times, hz, vv = f0["times"], f0["f0_hz"], f0["voiced"]
    m = (times >= t0 + src_off) & (times <= t1 + src_off) & vv
    if m.sum() < 16:
        return {"n_voiced": int(m.sum())}
    tt = times[m]
    cc = 1200.0 * np.log2(np.maximum(hz[m], 1e-6) / 440.0) - 6900.0
    # resample to uniform 5 ms for a consistent LS/detrend basis
    tg = np.arange(tt[0], tt[-1], GRID_S)
    cg = np.interp(tg, tt, cc)
    r, _ = _detrend(tg, cg, 1.5 / f_vib)
    p = _periodic_estimate(tg, r, f_vib)
    rate, _ = _dominant_rate(tg, r)
    depth = float(2.0 * np.sqrt(2.0) * np.std(p))
    resid_depth = float(2.0 * np.sqrt(2.0) * np.std(r - p))
    return {"n_voiced": int(m.sum()),
            "voiced_frac": round(float(m.mean()), 2),
            "mod_rate_hz": round(rate, 2) if rate else None,
            "periodic_depth_c": round(depth, 1),
            "nonperiodic_rms_c": round(
                float(np.sqrt(np.mean((r - p) ** 2))), 1),
            "depth_env_c": _depth_envelope(tg, p, f_vib)}


def _depth_envelope(tg, p, f_vib):
    """Cycle-by-cycle peak-to-peak-ish depth (per ~period window)."""
    win = max(3, int(round(1.0 / f_vib / GRID_S)))
    env = []
    for i in range(0, len(p) - win + 1, win // 2 or 1):
        seg = p[i:i + win]
        env.append({"t": round(float(tg[i + win // 2]), 3),
                    "p2p_c": round(float(seg.max() - seg.min()), 1)})
    return env


def _taper(t, t0, t1):
    e = np.clip((t - t0) / TAPER_S, 0.0, 1.0)
    x = np.clip((t1 - t) / TAPER_S, 0.0, 1.0)
    return np.minimum(e, x)


def main():
    head = drv._require_clean_worktree("l7f_periodic_ownership")
    cfg = load_config()
    assert "dpV2" in cfg["openutau_dir"]
    assert cfg.get("default_singer") == "YousaV1.65c"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    doc = load_ustx(BASE_USTX)
    part = doc["voice_parts"][0]
    w0, w1 = drv.PHRASES[PHRASE]
    src_wav = drv.PHRASE_DIR / PHRASE / "SOURCE.wav"
    src_off = drv.PAD_S - w0
    src_f0 = extract_f0(src_wav)

    owned = _vibrato_owned_intervals(part)
    cur, xs, ys = _pitd_series(part)
    span = {"target_notes": list(TARGET_NOTES),
            "note_span_s": [round(_tick_s(part,
                            part["notes"][TARGET_NOTES[0]]
                            ["position"]), 3),
                            round(_tick_s(part,
                            part["notes"][TARGET_NOTES[-1]]
                            ["position"])
                            + part["notes"][TARGET_NOTES[-1]]
                            ["duration"] * TICK_MS / 1000.0, 3)]}

    decomp = []
    new_ys = ys.copy()
    for iv in owned:
        t0, t1 = iv["start_s"], iv["end_s"]
        fv = iv["rate_hz"]
        m = (xs >= t0) & (xs <= t1)
        if m.sum() < 5:
            decomp.append({**iv, "skipped": "few curve points"})
            continue
        tg = np.arange(t0, t1 + 1e-9, GRID_S)
        yg = np.interp(tg, xs, ys)
        r, trend = _detrend(tg, yg, 1.5 / fv)
        rate, _ = _dominant_rate(tg, r)
        p = _periodic_estimate(tg, r, fv)
        var_r = float(np.var(r))
        var_p = float(np.var(p))
        explained = var_p / var_r if var_r > 0 else 0.0
        depth_c = 2.0 * np.sqrt(2.0) * np.std(p)
        dup = (rate is not None
               and abs(rate - fv) / fv <= RATE_TOL
               and explained >= EXPLAINED_MIN
               and depth_c >= DEPTH_MIN_C)
        sub = np.interp(xs[m], tg, p) * _taper(xs[m], t0, t1)
        new_ys[m] = ys[m] - sub
        decomp.append({**iv,
                       "n_curve_pts": int(m.sum()),
                       "residual_rate_hz": round(rate, 2)
                       if rate else None,
                       "periodic_depth_c": round(depth_c, 1),
                       "periodic_share_of_residual":
                           round(explained, 3),
                       "duplicate_periodic": bool(dup)})
    changed = np.abs(new_ys - ys) > 1e-9
    first_i = int(np.argmax(changed)) if changed.any() else len(ys)
    outside_same = bool((np.abs(new_ys[:first_i] - ys[:first_i]) < 1e-9)
                        .all())

    b_doc = copy.deepcopy(doc)
    bpart = b_doc["voice_parts"][0]
    bcur = next(c for c in bpart["curves"] if c["abbr"] == "pitd")
    # USTX pitd ys are ints — YamlDotNet rejects "-40.0" for List<int>.
    bcur["ys"] = [int(round(v)) for v in new_ys]
    bpart["name"] = part["name"] + "_ownfix"
    b_ustx = OUT_DIR / "P2_slides_C3v2_v165c_ownfix.ustx"
    save_ustx(b_doc, b_ustx)
    b_wav = drv.render(cfg, b_ustx, OUT_DIR / "P2_slides_C3v2_v165c_ownfix")

    # ---- measurement -------------------------------------------------
    fv_ref = owned[-1]["rate_hz"] if owned else 7.0
    o0, o1 = owned[-1]["start_s"], owned[-1]["end_s"]
    sigs = {"A_baseline": BASE_WAV, "B_ownfix": b_wav}
    meas = {}
    for tag, wav in sigs.items():
        f0 = extract_f0(wav)
        meas[tag] = {
            "wav": str(wav), "sha256": sha256(wav),
            "owned_interval_mod": _modulation(f0, o0, o1, fv_ref),
            "jitter": lev._jitter_stats(f0, w0, w1),
            "quality": lev._quality_stats(wav, f0, w0, w1),
            "defects": lev._defects(wav, f0, w0, w1, src_f0,
                                    src_wav, src_off),
            "note_gesture_table": lev._note_gesture_table(
                BASE_USTX if tag == "A_baseline" else b_ustx,
                f0, src_f0, src_off, w0)}
    meas["SOURCE_owned_interval"] = _modulation(
        src_f0, o0, o1, fv_ref, src_off=src_off)

    # ---- verdict -----------------------------------------------------
    src_mod = meas["SOURCE_owned_interval"]
    a_mod = meas["A_baseline"]["owned_interval_mod"]
    b_mod = meas["B_ownfix"]["owned_interval_mod"]
    dup_ok = any(d.get("duplicate_periodic") for d in decomp)
    if src_mod.get("voiced_frac", 0) < 0.5 or not src_mod.get("mod_rate_hz"):
        verdict, why = "FAIL_EVIDENCE", \
            "SOURCE periodic structure unmeasurable in owned interval"
    elif not dup_ok:
        verdict, why = "FAIL_STRATEGY", \
            "no duplicate periodic component met the rate/variance/depth" \
            " criteria in the owned interval"
    else:
        da = abs(a_mod.get("periodic_depth_c", 1e9)
                 - src_mod["periodic_depth_c"])
        db = abs(b_mod.get("periodic_depth_c", 1e9)
                 - src_mod["periodic_depth_c"])
        reduced = b_mod.get("periodic_depth_c", 1e9) <= \
            0.8 * a_mod.get("periodic_depth_c", 0)
        no_new = (len(meas["B_ownfix"]["defects"]["pitch_dips_gt300c"])
                  <= len(meas["A_baseline"]["defects"]
                            ["pitch_dips_gt300c"])
                  and len(meas["B_ownfix"]["defects"]["unvoiced_dropouts"])
                  <= len(meas["A_baseline"]["defects"]
                            ["unvoiced_dropouts"])
                  and outside_same)
        if db < da and reduced and no_new:
            verdict, why = "PASS_CAUSAL", \
                "removing duplicate periodic PITD moved render depth " \
                "toward SOURCE without new defects"
        elif reduced and no_new:
            verdict, why = "FAIL_CAPABILITY", \
                "duplicate removed but fixed vibrato still cannot " \
                "reproduce the SOURCE rate/depth envelope"
        else:
            verdict, why = "FAIL_STRATEGY", \
                "periodic-PITD removal did not materially improve the " \
                "local modulation"

    report = {
        "tool": "tools/l7f_periodic_ownership.py",
        "round": "L7 Round F — P2 periodic-ownership causal A/B",
        "evaluated_head": head,
        "worktree_clean_at_generation": True,
        "baseline": {"ustx": str(BASE_USTX), "ustx_sha256": sha256(BASE_USTX),
                     "wav": str(BASE_WAV), "wav_sha256": sha256(BASE_WAV)},
        "b_variant": {"ustx": str(b_ustx), "ustx_sha256": sha256(b_ustx),
                      "wav": str(b_wav), "wav_sha256": sha256(b_wav)},
        "human_fail_span": span,
        "vibrato_owned_intervals": owned,
        "decomposition": decomp,
        "pitd_points_changed": int(changed.sum()),
        "pitd_unchanged_before_first_edit": outside_same,
        "measurements": meas,
        "verdict": verdict,
        "verdict_reason": why,
    }
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"verdict={verdict}: {why}")
    print(f"wrote {REPORT}")

    if verdict == "PASS_CAUSAL":
        # P2-only A/B listening project: track0 = A, track1 = B.
        lp = copy.deepcopy(load_ustx(
            drv.RUN_DIR / "listening" /
            "agent2utau_L7E_P1_P3_P2.ustx"))
        tr_a = lp["tracks"][0]
        tr_b = copy.deepcopy(tr_a)
        tr_b["track_name"] = "vocal B ownfix"
        lp["tracks"] = [tr_a, tr_b, lp["tracks"][1]]
        pa = next(p for p in lp["voice_parts"]
                  if p["name"] == "P2_slides_C3")
        pa["track_no"] = 0
        pa["name"] = "P2_A_baseline"
        pb = copy.deepcopy(load_ustx(b_ustx)["voice_parts"][0])
        pb["track_no"] = 1
        pb["name"] = "P2_B_ownfix"
        lp["voice_parts"] = [pa, pb]
        for wp in lp.get("wave_parts", []):
            wp["track_no"] = 2
        lp["name"] = "agent2utau L7-F P2 ownfix A/B"
        save_ustx(lp, LISTEN_USTX)
        print(f"wrote {LISTEN_USTX}")


if __name__ == "__main__":
    main()
