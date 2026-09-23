"""L7 Round F2 — localize the P2 'wo de ben' perceptual failure.

Evidence/localization round (NOT a repair round).  Segments the human-
fail span by committed note boundaries:

    S1 = note8  "wo"   onset + transition
    S2 = notes9-10 "de"+sustain  pre-vibrato region
    S3 = note11 "ben"  vibrato-owned tail

For SOURCE and the frozen 1.65c baseline render, per segment:

  * F0 geometry: spikes >300c, slope/accel/jerk, reversal density,
    note-centre offset, gesture-range ratio;
  * periodic structure: dominant rate, periodic depth envelope,
    cycle-to-cycle p2p variation, waveform residual after removing the
    dominant periodic component;
  * phonation/render quality: voiced continuity, dropouts, energy
    collapses, ACF purity, spectral flatness (l7e metrics, segmented);
  * motion-grammar label + implausibility flags (diagnostic only —
    no global PASS/FAIL thresholds).

Controls: P1 v165c (positive), P3 v165c (resolved), old 1.65b P3 v1
render (contains the known 29.26-29.28s hard glitch), SOURCE windows.

Routing classes: F0_LOCAL_DEFECT / VIBRATO_CAPABILITY /
PHONATION_RENDER_DEFECT / MIXED_DEFECT / FAIL_EVIDENCE.

Output: runs/expr-20260921/rebaseline/P2_slides/round_f2/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l7_phrase_gate as drv                          # noqa: E402
import l7e_listening_evidence as lev                  # noqa: E402
import l7f_periodic_ownership as own                  # noqa: E402
from agent2utau.analysis.f0 import extract_f0         # noqa: E402
from agent2utau.openutau.ustx import load_ustx, sha256  # noqa: E402
from agent2utau.expression.pitch_residual import TICK_MS  # noqa: E402

PHRASE = "P2_slides"
RB = drv.RUN_DIR / "rebaseline"
BASE_USTX = RB / PHRASE / "P2_slides_C3v2_v165c.ustx"
BASE_WAV = RB / PHRASE / "P2_slides_C3v2_v165c_vocal.wav"
OUT_DIR = RB / PHRASE / "round_f2"
REPORT = OUT_DIR / "l7f2_localization_report.json"

# signals: path + song->file time offset (0 for render files that are
# window-aligned; PAD_S-w0 for window-bounded SOURCE.wav)
def _sig_path(name):
    p = {
        "P2_base": BASE_WAV,
        "P1_base": RB / "P1_sustain" / "P1_sustain_C3v2_v165c_vocal.wav",
        "P3_new": RB / "P3_vibrato" / "P3_vibrato_C3_v165c_vocal.wav",
        "P3_old_glitch": drv.PHRASE_DIR / "P3_vibrato" /
        "P3_vibrato_C3_v1_vocal.wav",
        "P2_source": drv.PHRASE_DIR / PHRASE / "SOURCE.wav",
    }[name]
    return p


def _cents(f0, t0, t1, off=0.0):
    """Voiced cents samples + their times inside [t0,t1] (song time)."""
    times, hz, vv = f0["times"], f0["f0_hz"], f0["voiced"]
    m = (times >= t0 + off) & (times <= t1 + off) & vv
    tt = times[m]
    cc = 1200.0 * np.log2(np.maximum(hz[m], 1e-6) / 440.0) - 6900.0
    return tt, cc, int(((times >= t0 + off) & (times <= t1 + off)).sum())


def _geometry(tt, cc, n_window):
    """F0 trajectory geometry on voiced samples (~10ms hop)."""
    if len(cc) < 4:
        return {"n_voiced": len(cc), "window_frames": n_window}
    dt = np.diff(tt)
    ok = dt > 0
    d1 = np.diff(cc)[ok] / dt[ok]            # cents/s
    acc = np.diff(cc, 2)                    # cents per frame^2 (10ms)
    spikes = []
    for i in range(1, len(cc) - 1):
        dev = cc[i] - (cc[i - 1] + cc[i + 1]) / 2.0
        if abs(dev) > 300.0:
            spikes.append({"t": round(float(tt[i]), 3),
                           "dev_c": round(float(dev), 0)})
    big = np.abs(d1) > 0.5 * 100.0          # >50c/s meaningful motion
    signs = np.sign(d1[big])
    rev = int(np.sum(signs[1:] * signs[:-1] < 0)) if len(signs) > 1 else 0
    dur = tt[-1] - tt[0] if len(tt) > 1 else 0.0
    return {
        "n_voiced": len(cc), "window_frames": n_window,
        "voiced_frac": round(len(cc) / max(1, n_window), 2),
        "range_c": round(float(np.ptp(cc)), 0),
        "slope_med_cs": round(float(np.median(np.abs(d1))), 0),
        "slope_p95_cs": round(float(np.percentile(np.abs(d1), 95)), 0),
        "accel_rms_c": round(float(np.sqrt(np.mean(acc ** 2))), 0),
        "spikes_gt300c": spikes,
        "reversals_per_s": round(rev / max(dur, 1e-6), 1),
        "max_abs_d1_cs": round(float(np.abs(d1).max()), 0),
    }


def _periodic(tt, cc):
    """Periodic structure: detrend, dominant 4-10Hz rate, LS depth
    envelope, cycle-to-cycle variation, shape residual."""
    if len(cc) < 30:
        return {}
    tg = np.arange(tt[0], tt[-1], 0.005)
    cg = np.interp(tg, tt, cc)
    # find dominant rate on a coarsely detrended residual first
    r0, _ = own._detrend(tg, cg, 0.30)
    f_dom, _ = own._dominant_rate(tg, r0)
    if not f_dom:
        return {"dominant_rate_hz": None}
    r, _ = own._detrend(tg, cg, 1.5 / f_dom)
    p = own._periodic_estimate(tg, r, f_dom)
    var_r, var_p = float(np.var(r)), float(np.var(p))
    env = own._depth_envelope(tg, p, f_dom)
    p2p = [e["p2p_c"] for e in env]
    resid = r - p
    return {
        "dominant_rate_hz": round(f_dom, 2),
        "periodic_depth_c": round(2.0 * np.sqrt(2.0)
                                  * float(np.std(p)), 1),
        "periodic_share": round(var_p / var_r, 3) if var_r > 0 else None,
        "shape_resid_rms_c": round(float(np.sqrt(np.mean(resid ** 2))), 1),
        "depth_env_c": p2p,
        "depth_env_cv": round(float(np.std(p2p) / np.mean(p2p)), 3)
        if p2p and np.mean(p2p) > 0 else None,
        "depth_env_slope_c_per_s": round(
            float(np.polyfit(range(len(p2p)), p2p, 1)[0])
            / (0.005 * (len(p2p) and
               int(round(1.0 / f_dom / 0.005)) // 2 or 1)), 1)
        if len(p2p) > 2 else None,
    }


def _phonation(wav_path, f0, t0, t1, src_f0, src_wav, src_off):
    q = lev._quality_stats(wav_path, f0, t0, t1)
    d = lev._defects(wav_path, f0, t0, t1, src_f0, src_wav, src_off) \
        if src_f0 is not None else {}
    # local energy profile
    wav, sr = sf.read(str(wav_path), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    bins = []
    t = t0
    while t < t1 - 0.05:
        seg = wav[int(t * sr): int((t + 0.1) * sr)]
        if len(seg):
            bins.append(round(20 * np.log10(
                max(np.sqrt(np.mean(seg ** 2)), 1e-9)), 1))
        t += 0.1
    return {"acf_peak_med": q.get("acf_peak_med"),
            "spec_flat_2_8k_med": q.get("spec_flat_2_8k_med"),
            "n_dips_gt300c": len(d.get("pitch_dips_gt300c") or []),
            "dropouts": d.get("unvoiced_dropouts") or [],
            "energy_collapses": d.get("energy_collapses") or [],
            "energy_dbfs_bins": bins,
            "energy_min_dbfs": min(bins) if bins else None}


def _grammar(geom, per):
    """Diagnostic-only motion label + implausibility flags."""
    flags = []
    if geom.get("spikes_gt300c"):
        flags.append("spike_gt300c")
    if (geom.get("reversals_per_s") or 0) > 15:
        flags.append("rapid_reversal_density")
    if (geom.get("max_abs_d1_cs") or 0) > 800:
        flags.append("extreme_slope")
    share = per.get("periodic_share") or 0
    if share > 0.5 and 4 <= (per.get("dominant_rate_hz") or 0) <= 9:
        label = "vibrato"
    elif (geom.get("range_c") or 0) > 300 and \
            (geom.get("reversals_per_s") or 0) > 8:
        label = "zigzag_transition"
        flags.append("unsupported_zigzag")
    elif (geom.get("range_c") or 0) > 150:
        label = "transition"
    else:
        label = "sustain_or_settling"
    return {"label": label, "flags": flags}


def eval_segments(name, wav, f0, segments, src_f0, src_wav, off=0.0):
    out = {}
    for seg, (t0, t1) in segments.items():
        tt, cc, nwin = _cents(f0, t0, t1, off)
        g = _geometry(tt, cc, nwin)
        p = _periodic(tt, cc)
        ph = _phonation(wav, f0, t0, t1, src_f0, src_wav, off) \
            if name != "P2_source" else {}
        out[seg] = {"span_s": [t0, t1], "geometry": g,
                    "periodic": p, "phonation": ph,
                    "grammar": _grammar(g, p)}
    return out


def main():
    head = drv._require_clean_worktree("l7f2_localize")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    doc = load_ustx(BASE_USTX)
    part = doc["voice_parts"][0]
    notes = part["notes"]

    def _nb(i):
        a = (part["position"] + notes[i]["position"]) \
            * TICK_MS / 1000.0
        return a, a + notes[i]["duration"] * TICK_MS / 1000.0
    s1 = _nb(8)
    s2a, _ = _nb(9)
    _, s2b = _nb(10)
    s3 = _nb(11)
    segments = {"S1_onset_transition": [round(s1[0], 3), round(s1[1], 3)],
                "S2_previbrato": [round(s2a, 3), round(s2b, 3)],
                "S3_vibrato_tail": [round(s3[0], 3), round(s3[1], 3)]}

    w0, w1 = drv.PHRASES[PHRASE]
    src_wav = drv.PHRASE_DIR / PHRASE / "SOURCE.wav"
    src_f0 = extract_f0(src_wav)
    src_off = drv.PAD_S - w0

    signals = {}
    for name, path in [("P2_base", BASE_WAV),
                       ("P2_source", src_wav)]:
        print(f"== {name}", flush=True)
        f0 = src_f0 if name == "P2_source" else extract_f0(path)
        signals[name] = {"path": str(path), "sha256": sha256(path),
                         "segments": eval_segments(
                             name, path, f0, segments,
                             src_f0 if name != "P2_source" else None,
                             src_wav, src_off if name == "P2_source"
                             else 0.0)}

    # controls: whole-window diagnostics on other phrases
    controls = {}
    for name, pdir_wav, phr in [
            ("P1_base_control",
             RB / "P1_sustain" / "P1_sustain_C3v2_v165c_vocal.wav",
             "P1_sustain"),
            ("P3_new_control",
             RB / "P3_vibrato" / "P3_vibrato_C3_v165c_vocal.wav",
             "P3_vibrato"),
            ("P3_old_glitch_abnormal",
             drv.PHRASE_DIR / "P3_vibrato" / "P3_vibrato_C3_v1_vocal.wav",
             "P3_vibrato")]:
        cw0, cw1 = drv.PHRASES[phr]
        print(f"== control {name}", flush=True)
        f0 = extract_f0(pdir_wav)
        tt, cc, nwin = _cents(f0, cw0, cw1, 0.0)
        controls[name] = {
            "path": str(pdir_wav), "sha256": sha256(pdir_wav),
            "window_s": [cw0, cw1],
            "geometry": _geometry(tt, cc, nwin),
            "periodic": _periodic(tt, cc),
            "phonation": lev._quality_stats(pdir_wav, f0, cw0, cw1),
        }
    # glitch-window control: old P3 around the known 29.26-29.28 defect
    f0g = extract_f0(controls["P3_old_glitch_abnormal"]["path"])
    tt, cc, nwin = _cents(f0g, 29.15, 29.45, 0.0)
    controls["P3_old_glitch_abnormal"]["glitch_window_29.15_29.45"] = {
        "geometry": _geometry(tt, cc, nwin)}

    # ---- feature-separation sanity -----------------------------------
    sep = {}
    for feat in ("spikes_gt300c", "reversals_per_s", "max_abs_d1_cs",
                 "accel_rms_c", "slope_p95_cs"):
        g = controls["P3_old_glitch_abnormal"]["glitch_window_29.15_29.45"]["geometry"]
        gv = g.get(feat)
        gv = len(gv) if isinstance(gv, list) else gv
        nv = {}
        for cn in ("P1_base_control", "P3_new_control"):
            v = controls[cn]["geometry"].get(feat)
            nv[cn] = len(v) if isinstance(v, list) else v
        sep[feat] = {"abnormal_P3old": gv, **nv,
                     "separates": gv is not None and all(
                         v is not None and gv > v * 2
                         for v in nv.values())}
    # ---- routing classification --------------------------------------
    p2 = signals["P2_base"]["segments"]
    f0_flags = {s: p2[s]["grammar"]["flags"] for s in p2}
    abnormal_f0 = [s for s, f in f0_flags.items() if f]
    ph_bad = []
    for s, d in p2.items():
        ph = d["phonation"]
        if ph.get("dropouts") or ph.get("energy_collapses") \
                or (ph.get("acf_peak_med") or 1) < 0.85:
            ph_bad.append(s)
    if abnormal_f0 and ph_bad:
        cls = "MIXED_DEFECT"
    elif abnormal_f0:
        cls = "F0_LOCAL_DEFECT"
    elif ph_bad:
        cls = "PHONATION_RENDER_DEFECT"
    else:
        cls = "FAIL_EVIDENCE"

    report = {
        "tool": "tools/l7f2_localize.py",
        "round": "L7 Round F2 — P2 perceptual-failure localization",
        "evaluated_head": head,
        "worktree_clean_at_generation": True,
        "baseline": {"ustx": str(BASE_USTX),
                     "ustx_sha256": sha256(BASE_USTX),
                     "wav": str(BASE_WAV),
                     "wav_sha256": sha256(BASE_WAV)},
        "segments": segments,
        "signals": signals,
        "controls": controls,
        "feature_separation_check": sep,
        "flags_by_segment": f0_flags,
        "abnormal_f0_segments": abnormal_f0,
        "abnormal_phonation_segments": ph_bad,
        "classification": cls,
    }
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"classification={cls}")
    print(f"abnormal_f0={abnormal_f0} abnormal_phonation={ph_bad}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
