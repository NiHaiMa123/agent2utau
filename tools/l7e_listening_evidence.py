"""L7-E listening evidence: objective blind-spot quantification.

Human listening verdict (recorded by reviewer, 2026-09-23):
    P1_sustain PASS;  P2_slides FAIL;  P3_vibrato FAIL.
Reported failure mode: pitch instability / wobble + audio noise.

Machine acceptance passed all 10 terms on all phrases, so the failure
is a metric blind spot.  This tool measures candidate quantities that
the frozen gate does NOT cover:

  * frame-to-frame F0 jitter of the real render vs SOURCE vs the
    neutral C0 render (clean-synth floor);
  * detrended F0 residual RMS (70 ms median) — micro-wobble amplitude;
  * written PITD curve jaggedness — direction-reversal rate and
    second-difference energy of the committed curve;
  * voiced-frame harmonic purity (ACF peak at F0 lag) and high-band
    spectral flatness — noise/artifact proxies.

Output: runs/expr-20260921/listening/l7e_listening_evidence.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l7_phrase_gate as drv                      # noqa: E402
from agent2utau.analysis.f0 import extract_f0     # noqa: E402
from agent2utau.openutau.ustx import load_ustx    # noqa: E402
from agent2utau.expression.pitch_residual import TICK_MS  # noqa: E402

OUT = drv.RUN_DIR / "listening" / "l7e_listening_evidence.json"


def _sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _jitter_stats(f0, t0=None, t1=None):
    """Frame-to-frame |Δcents| over consecutive voiced frames, plus
    detrended-residual RMS inside voiced runs >= 200 ms."""
    times, hz, voiced = f0["times"], f0["f0_hz"], f0["voiced"]
    if t0 is not None:
        m = (times >= t0) & (times <= t1)
        times, hz, voiced = times[m], hz[m], voiced[m]
    dc = []
    run_c, run_resid = [], []
    i = 0
    while i < len(times):
        if not voiced[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(times) and voiced[j + 1] \
                and times[j + 1] - times[j] < 0.015:
            j += 1
        seg = 1200.0 * np.log2(np.maximum(hz[i:j + 1], 1e-6) / 440.0) \
            - 6900.0
        if len(seg) >= 2:
            dc.extend(np.abs(np.diff(seg)).tolist())
        if len(seg) >= 20:   # >= ~200 ms run -> detrended residual
            k = 7            # ~70 ms median window at 10 ms hop
            med = np.array([np.median(seg[max(0, n - k // 2):
                                          n + k // 2 + 1])
                            for n in range(len(seg))])
            run_resid.extend((seg - med).tolist())
        i = j + 1
    dc = np.asarray(dc)
    run_resid = np.asarray(run_resid)
    n_voiced = int(voiced.sum())
    return {
        "n_frames": len(times),
        "voiced_frac": round(n_voiced / max(1, len(times)), 3),
        "dcent_med": round(float(np.median(dc)), 1) if len(dc) else None,
        "dcent_p90": round(float(np.percentile(dc, 90)), 1)
        if len(dc) else None,
        "dcent_gt30_frac": round(float((dc > 30).mean()), 3)
        if len(dc) else None,
        "detrended_rms_c": round(float(np.sqrt(np.mean(run_resid ** 2))), 1)
        if len(run_resid) else None,
        "n_voiced_frames": n_voiced,
    }


def _curve_jaggedness(ustx_path, part_pos_tick):
    """Jaggedness of the committed PITD curve: resample to a uniform
    10 ms grid, then direction-reversal rate + second-diff RMS."""
    doc = load_ustx(ustx_path)
    part = doc["voice_parts"][0]
    cur = next((c for c in part.get("curves", [])
                if c.get("abbr") == "pitd"), None)
    if not cur or len(cur.get("xs", [])) < 3:
        return {"n_points": 0}
    xs = np.asarray(cur["xs"], dtype=float) * TICK_MS / 1000.0
    ys = np.asarray(cur["ys"], dtype=float)
    t = np.arange(0.0, xs[-1] + 1e-9, 0.010)
    y = np.interp(t, xs, ys)
    d1 = np.diff(y)
    d2 = np.diff(y, 2)
    signs = np.sign(d1[np.abs(d1) > 0.5])   # ignore sub-cent steps
    rev = float(np.mean(signs[1:] * signs[:-1] < 0)) if len(signs) > 1 else 0.0
    return {
        "n_points": int(len(xs)),
        "dur_s": round(float(xs[-1]), 2),
        "reversal_per_s": round(float(rev) / 0.010, 1),
        "d2_rms_c": round(float(np.sqrt(np.mean(d2 ** 2))), 1),
        "abs_d1_med_c": round(float(np.median(np.abs(d1))), 1),
        "abs_d1_p95_c": round(float(np.percentile(np.abs(d1), 95)), 1),
    }


def _defects(wav_path, f0, t0, t1, src_f0, src_wav, src_off):
    """Concrete perceptual defects the frozen gate does not see:

    - single-frame pitch dips >300c from local median (voicing-break
      glitches — audible cracks);
    - render unvoiced runs >=80 ms that overlap voiced source
      (phonation dropouts);
    - render energy collapse: 200 ms bins < -38 dBFS while source
      > -30 dBFS (breathy/lost slide transitions).
    """
    times, hz, voiced = f0["times"], f0["f0_hz"], f0["voiced"]
    m = (times >= t0) & (times <= t1)
    tt, hh, vv = times[m], hz[m], voiced[m]
    c = np.where(vv, 1200.0 * np.log2(np.maximum(hh, 1e-6) / 440.0)
                 - 6900.0, np.nan)
    dips = []
    for i in range(1, len(c) - 1):
        if np.isfinite(c[i]) and np.isfinite(c[i - 1]) \
                and np.isfinite(c[i + 1]):
            dev = c[i] - (c[i - 1] + c[i + 1]) / 2.0
            if abs(dev) > 300.0:
                dips.append({"t": round(float(tt[i]), 3),
                             "dev_c": round(float(dev), 0)})
    st, sh, sv = src_f0["times"], src_f0["f0_hz"], src_f0["voiced"]
    dropouts = []
    i = 0
    while i < len(tt):
        if vv[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(tt) and not vv[j + 1]:
            j += 1
        dur = tt[j] - tt[i] + 0.010
        if dur >= 0.080:
            sm = (st >= tt[i] + src_off) & (st <= tt[j] + src_off)
            src_v = float(sv[sm].mean()) if sm.any() else 0.0
            dropouts.append({"t": [round(float(tt[i]), 3),
                                   round(float(tt[j]), 3)],
                             "dur_ms": round(float(dur) * 1000, 0),
                             "src_voiced_frac": round(src_v, 2)})
        i = j + 1
    wav, sr = sf.read(str(wav_path), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    swav, ssr = sf.read(str(src_wav), dtype="float32")
    if swav.ndim > 1:
        swav = swav.mean(axis=1)
    collapses = []
    t = t0
    while t < t1 - 0.2:
        seg = wav[int(t * sr): int((t + 0.2) * sr)]
        sseg = swav[int((t + src_off) * ssr):
                    int((t + src_off + 0.2) * ssr)]
        if len(seg) and len(sseg):
            r = 20 * np.log10(max(np.sqrt(np.mean(seg ** 2)), 1e-9))
            s_r = 20 * np.log10(max(np.sqrt(np.mean(sseg ** 2)), 1e-9))
            if r < -38.0 and s_r > -30.0:
                collapses.append({"t": round(float(t), 2),
                                  "render_dbfs": round(float(r), 1),
                                  "source_dbfs": round(float(s_r), 1)})
        t += 0.1
    return {"pitch_dips_gt300c": dips, "unvoiced_dropouts": dropouts,
            "energy_collapses": collapses}


def _note_gesture_table(ustx_path, f0, src_f0, src_off, w0):
    """Per-note gesture fidelity: source pitch range vs render pitch
    range inside each note body, plus median offset.  Flattened or
    off-centre gestures are audible but invisible to turn counts."""
    doc = load_ustx(ustx_path)
    part = doc["voice_parts"][0]
    pos = part["position"]
    st, sh, sv = src_f0["times"], src_f0["f0_hz"], src_f0["voiced"]
    rt, rh, rv = f0["times"], f0["f0_hz"], f0["voiced"]

    def _stats(times, hz, vv, a, b):
        m = (times >= a) & (times < b) & vv
        if m.sum() < 3:
            return None, None
        cc = 1200.0 * np.log2(np.maximum(hz[m], 1e-6) / 440.0)
        return float(np.median(cc)), float(np.ptp(cc))

    rows = []
    for i, n in enumerate(part["notes"]):
        a = (pos + n["position"]) * TICK_MS / 1000.0
        d = n["duration"] * TICK_MS / 1000.0
        # 30 ms edge guard: measure the note body, not boundaries
        sm, sr_ = _stats(st, sh, sv,
                         a + src_off + 0.03, a + d + src_off - 0.03)
        rm, rr = _stats(rt, rh, rv, a + 0.03, a + d - 0.03)
        if sm is None or rm is None:
            continue
        rows.append({"note": i, "t_s": round(float(a), 2),
                     "offset_c": round(float(rm - sm), 0),
                     "src_range_c": round(float(sr_), 0),
                     "render_range_c": round(float(rr), 0),
                     "range_ratio": round(float(rr / max(sr_, 1.0)), 2)})
    return rows


def _quality_stats(wav_path, f0, t0=None, t1=None):
    """Voiced-frame harmonic purity (ACF at F0 lag) + high-band spectral
    flatness on the render WAV itself."""
    wav, sr = sf.read(str(wav_path), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    times, hz, voiced = f0["times"], f0["f0_hz"], f0["voiced"]
    win = 2048
    acf_peaks, flats = [], []
    for t, f, v in zip(times, hz, voiced):
        if t0 is not None and not (t0 <= t <= t1):
            continue
        if not v or f <= 0:
            continue
        c = int(t * sr)
        a = wav[max(0, c - win // 2): c + win // 2]
        if len(a) < win:
            continue
        a = a - a.mean()
        a = a * np.hanning(len(a))
        lag = int(round(sr / f))
        if lag < 8 or lag >= len(a) // 2:
            continue
        ac = np.correlate(a, a, "full")[len(a) - 1:]
        denom = ac[0] if ac[0] > 0 else 1e-12
        lo, hi = max(8, lag - 4), min(len(ac), lag + 5)
        acf_peaks.append(float(np.max(ac[lo:hi]) / denom))
        sp = np.abs(np.fft.rfft(a))
        fr = np.fft.rfftfreq(len(a), 1 / sr)
        band = sp[(fr >= 2000) & (fr <= 8000)]
        if len(band):
            flats.append(float(np.exp(np.mean(np.log(band + 1e-12)))
                             / (np.mean(band) + 1e-12)))
    acf_peaks = np.asarray(acf_peaks)
    flats = np.asarray(flats)
    return {
        "n_frames_used": int(len(acf_peaks)),
        "acf_peak_med": round(float(np.median(acf_peaks)), 3)
        if len(acf_peaks) else None,
        "spec_flat_2_8k_med": round(float(np.median(flats)), 3)
        if len(flats) else None,
    }


def _load(path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() \
        else None


def eval_phrase(name):
    w0, w1 = drv.PHRASES[name]
    pdir = drv.PHRASE_DIR / name
    man = _load(pdir / "run_manifest.json") or {}
    acc_wav = man.get("render_wav_path")
    acc_ustx = man.get("ustx_path")
    part_pos = None
    if acc_ustx and Path(acc_ustx).is_file():
        part_pos = load_ustx(acc_ustx)["voice_parts"][0].get("position")

    sigs = {"source": pdir / "SOURCE.wav",
            "neutral_C0": pdir / f"{name}_C0_vocal.wav",
            "accepted": acc_wav}
    # extra context: rejected stage renders, if present
    for tag in ("C3_v1", "C3v2", "C3v3"):
        p = pdir / f"{name}_{tag}_vocal.wav"
        if p.is_file() and acc_wav and \
                p.resolve() != Path(acc_wav).resolve():
            sigs[f"alt_{tag}"] = p

    out = {"window_s": [w0, w1], "signals": {}, "curve": {}}
    src_f0 = extract_f0(sigs["source"]) if sigs["source"].is_file() \
        else None
    # SOURCE.wav starts at w0 - PAD_S (driver convention), so source
    # time = song time - w0 + PAD_S  =>  src_off = pad - w0
    src_off = drv.PAD_S - w0
    for tag, p in sigs.items():
        if p is None or not Path(p).is_file():
            continue
        f0 = src_f0 if tag == "source" else extract_f0(p)
        if tag == "source":
            t0, t1 = None, None       # SOURCE.wav already window-bounded
        else:
            t0, t1 = w0, w1
        rec = {"path": str(p), "sha256": _sha256(p)[:16],
               "jitter": _jitter_stats(f0, t0, t1),
               "quality": _quality_stats(p, f0, t0, t1)}
        if tag != "source" and src_f0 is not None:
            rec["defects"] = _defects(p, f0, w0, w1, src_f0,
                                      sigs["source"], src_off)
            if tag == "accepted" and acc_ustx and \
                    Path(acc_ustx).is_file():
                rec["note_gesture_table"] = _note_gesture_table(
                    acc_ustx, f0, src_f0, src_off, w0)
        out["signals"][tag] = rec
        print(f"   {name}/{tag}: f0 done", flush=True)
    if acc_ustx and Path(acc_ustx).is_file():
        out["curve"]["accepted_pitd"] = {
            "path": str(acc_ustx),
            **_curve_jaggedness(acc_ustx, part_pos)}
    return out


def main():
    rep = {
        "tool": "tools/l7e_listening_evidence.py",
        "purpose": "quantify perceptual blind spot behind L7-E "
                   "P2/P3 listening FAIL (pitch wobble + noise)",
        "human_verdict": {
            "P1_sustain": "PASS",
            "P2_slides": "FAIL",
            "P3_vibrato": "FAIL",
            "reported_modes": ["pitch_instability_wobble",
                               "audio_quality_noise"]},
        "phrases": {},
    }
    for name in drv.PHRASES:
        print(f"== {name}", flush=True)
        rep["phrases"][name] = eval_phrase(name)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
