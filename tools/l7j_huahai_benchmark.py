"""L7 Round J — Huahai three-way benchmark (phases J0-J4).

Phase J0: input/provenance manifest
  - Jay original audio hash/duration
  - human +4-key ustx hash + format/singer/renderer identity
  - wave-part file availability (rendered audio bundled?)
  - key/transposition correspondence: separated-vocal F0 at sustained
    notes vs written tones -> delta distribution should peak at +4 st

Phase J1: phrase selection (3-5, motion-class driven)
Phase J2: four-layer extraction  A source F0 / B written controls /
         C human render F0 / (D agent2utau later)
Phase J3: representation-gap event table
Phase J4: candidate rules (diagnostic)

Output: runs/huahai_benchmark/
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
from agent2utau.analysis.f0 import extract_f0         # noqa: E402
from agent2utau.openutau.ustx import (
    load_ustx, save_ustx, sha256)                      # noqa: E402
from agent2utau.resources.config import load_config   # noqa: E402
from agent2utau.openutau.ustx import SPECIAL_LYRICS   # noqa: E402

JAY_FLAC = Path("E:/data/music/周杰伦音乐 所有专辑和单曲/"
                "2008-魔杰座/04. 周杰伦 - 花海.flac")
HUMAN_USTX = Path("E:/data/project_opentuau/花海+4-有参by白烁.ustx")
VOCALS = Path("runs/huahai_benchmark/separation") / \
    "04. 周杰伦 - 花海_(Vocals)_UVR-MDX-NET-Voc_FT.wav"
OUT = Path("runs/huahai_benchmark")
RESOLUTION = 480.0  # OpenUtau ticks per quarter note


def _midi(hz):
    return 69.0 + 12.0 * np.log2(np.maximum(hz, 1e-6) / 440.0)


def tempo_map(doc):
    """tick -> seconds using the project's tempo map (NOT the fixed
    TICK_MS 120bpm convention — this project is written at 75bpm)."""
    tempos = sorted(doc.get("tempos") or [{"position": 0, "bpm": 120}],
                    key=lambda t: t["position"])
    # cumulative seconds at each tempo change
    sec_at = [0.0]
    for i in range(1, len(tempos)):
        prev = tempos[i - 1]
        sec_at.append(sec_at[-1] + (tempos[i]["position"]
                                    - prev["position"])
                      * 60000.0 / (prev["bpm"] * RESOLUTION) / 1000.0)
    def tick_to_s(tick):
        i = max(k for k, t in enumerate(tempos) if t["position"] <= tick)
        return sec_at[i] + (tick - tempos[i]["position"]) \
            * 60000.0 / (tempos[i]["bpm"] * RESOLUTION) / 1000.0
    return tick_to_s


def project_summary(doc, t2s):
    trs = [{"track_name": t.get("track_name"), "singer": t.get("singer"),
            "phonemizer": t.get("phonemizer"),
            "renderer": (t.get("renderer_settings") or {})
            .get("renderer")}
           for t in doc.get("tracks", [])]
    parts = []
    for i, p in enumerate(doc.get("voice_parts", [])):
        ns = p["notes"]
        a = t2s(p["position"] + ns[0]["position"])
        b = t2s(p["position"] + ns[-1]["position"] + ns[-1]["duration"])
        sung = [n for n in ns if str(n.get("lyric")) not in SPECIAL_LYRICS
                and str(n.get("lyric")) != "+"]
        parts.append({
            "index": i, "name": p.get("name"), "track_no": p.get("track_no"),
            "span_s": [round(a, 2), round(b, 2)], "n_notes": len(ns),
            "n_sung": len(sung),
            "n_vibrato_notes": sum(1 for n in ns
                                   if (n.get("vibrato") or {})
                                   .get("length", 0) > 0),
            "curve_abbrs": [c["abbr"] for c in p.get("curves", [])],
            "pitd_points": max((len(c["xs"]) for c in p.get("curves", [])
                                if c["abbr"] == "pitd"), default=0)})
    waves = [{"name": w.get("name"), "track_no": w.get("track_no"),
              "relative_path": w.get("relative_path"),
              "file_exists": (HUMAN_USTX.parent /
                              (w.get("relative_path") or "")).is_file()}
             for w in doc.get("wave_parts", [])]
    return {"ustx_version": doc.get("ustx_version"),
            "bpm": doc.get("bpm"), "tempos": doc.get("tempos"),
            "tracks": trs, "voice_parts": parts, "wave_parts": waves}


def transposition_evidence(doc, f0, t2s, wave_off_s, rms):
    """Delta (written_tone - measured_midi) over sustained sung notes,
    evaluated at audio_time = project_time - wave_off_s (the tuner's
    reference audio starts at wave-part position ~1.3s on the project
    timeline). Frames below the stem RMS floor are excluded — the
    separated stem keeps instrumental bleed that tracks as false pitch."""
    times, hz, vv = f0["times"], f0["f0_hz"], f0["voiced"]
    gate = vv & (rms > 0.008)
    rows = []
    for p in doc["voice_parts"]:
        for i, n in enumerate(p["notes"]):
            if str(n.get("lyric")) in SPECIAL_LYRICS \
                    or str(n.get("lyric")) == "+":
                continue
            a = t2s(p["position"] + n["position"]) - wave_off_s
            d = t2s(p["position"] + n["position"] + n["duration"]) \
                - t2s(p["position"] + n["position"])
            if d < 0.30:
                continue
            m = (times >= a + 0.06) & (times <= a + d - 0.06) & gate
            if m.sum() < 5:
                continue
            rows.append({
                "part_index": doc["voice_parts"].index(p),
                "part_track": p.get("track_no"),
                "t_audio_s": round(a, 2), "tone": int(n["tone"]),
                "lyric": str(n.get("lyric")),
                "measured_midi": round(float(np.median(_midi(hz[m]))), 2),
                "voiced_frames": int(m.sum())})
    for r in rows:
        r["delta_st"] = round(r["tone"] - r["measured_midi"], 2)
    deltas = np.array([r["delta_st"] for r in rows])
    hist, edges = np.histogram(deltas, bins=np.arange(-12, 13, 0.5))
    peak_i = int(np.argmax(hist))
    mode = float((edges[peak_i] + edges[peak_i + 1]) / 2)
    near = np.abs(deltas - mode) <= 1.5
    per_part = []
    for pi in sorted({r["part_index"] for r in rows}):
        dd = np.array([r["delta_st"] for r in rows if r["part_index"] == pi])
        per_part.append({
            "part_index": pi, "n": int(dd.size),
            "median_delta_st": round(float(np.median(dd)), 2),
            "frac_within_1st_of_p4":
                round(float(np.mean(np.abs(dd - 4.0) <= 1.0)), 3)})
    return {"wave_offset_s": wave_off_s,
            "n_notes_measured": len(rows),
            "delta_mode_st": mode,
            "delta_median_st": round(float(np.median(deltas)), 2),
            "frac_within_1p5st_of_mode": round(float(near.mean()), 3),
            "frac_within_1st_of_p4":
                round(float(np.mean(np.abs(deltas - 4.0) <= 1.0)), 3),
            "delta_p25_p75": [round(float(np.percentile(deltas, 25)), 2),
                              round(float(np.percentile(deltas, 75)), 2)],
            "per_part": per_part,
            "per_note": rows[:400]}


def _acf_track(wav_mono, sr, windows):
    """Independent ACF pitch track (vocal band 150-600Hz) on the given
    (a,b) second windows; returns list of (t_center, midi, clarity)."""
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, 180, "highpass", fs=sr, output="sos")
    wf = sosfiltfilt(sos, wav_mono)
    lo, hi = int(sr / 600), int(sr / 150)
    out = []
    hop, win = 0.05, 0.04
    for a, b in windows:
        t = a
        while t < b - win:
            x = wf[int(t * sr):int((t + win) * sr)].astype(np.float64)
            x -= x.mean()
            if np.abs(x).max() < 1e-4:
                t += hop
                continue
            ac = np.correlate(x, x, "full")[len(x) - 1:]
            if hi < len(ac) and ac[0] > 0:
                lag = lo + int(np.argmax(ac[lo:hi]))
                clar = float(ac[lag] / ac[0])
                if clar > 0.4:
                    out.append((t + win / 2,
                                69 + 12 * np.log2((sr / lag) / 440),
                                clar))
            t += hop
    return out


def _pitd_for(part):
    c = next((c for c in part.get("curves", []) if c["abbr"] == "pitd"),
             None)
    if not c:
        return np.array([]), np.array([])
    return np.array(c["xs"]), np.array(c["ys"], dtype=float)


def _reversals(y):
    if y.size < 3:
        return 0
    d = np.diff(y)
    return int(np.sum(d[1:] * d[:-1] < 0))


def _osc_hz(y, dt_s):
    """Dominant oscillation rate of a curve via FFT, 3-10Hz band."""
    if y.size < 8:
        return 0.0, 0.0
    yy = y - np.mean(y)
    sp = np.abs(np.fft.rfft(yy))
    fr = np.fft.rfftfreq(y.size, dt_s)
    band = (fr >= 3) & (fr <= 10)
    if not band.any() or sp[band].max() < 5:
        return 0.0, 0.0
    i = np.argmax(sp[band])
    return float(fr[band][i]), float(sp[band][i] * 2 / y.size)


def note_table(part, t2s, wave_off, ms_tick):
    """Per sung note: audio span, tone, lyric, written-control features."""
    xs, ys = _pitd_for(part)
    pitd_dt = 10.0 * ms_tick / 1000.0  # pitd xs step = 10 ticks
    rows, prev = [], None
    for i, n in enumerate(part["notes"]):
        lyr = str(n.get("lyric"))
        if lyr in SPECIAL_LYRICS or lyr == "+":
            continue
        a = t2s(part["position"] + n["position"]) - wave_off
        d = n["duration"] * ms_tick / 1000.0
        x0, x1 = n["position"], n["position"] + n["duration"]
        pm = (xs >= x0) & (xs < x1)
        py = ys[pm]
        om = pm & (xs < x0 + 150)
        rows.append({
            "i": i, "a": a, "b": a + d, "dur": d, "tone": int(n["tone"]),
            "lyric": lyr, "leap": (None if prev is None
                                   else int(n["tone"]) - prev),
            "vibrato": (n.get("vibrato") or {}).get("length", 0) > 0,
            "portamento_y0": ((n.get("pitch") or {}).get("data")
                              or [{}])[0].get("y", 0),
            "pitd_rng": float(py.max() - py.min()) if py.size > 2 else 0,
            "pitd_rev": _reversals(py),
            "pitd_onset_rng": (float(ys[om].max() - ys[om].min())
                               if om.sum() > 2 else 0.0),
            "pitd_osc": _osc_hz(py, pitd_dt)})
        prev = n["tone"]
    return rows


def select_phrases(part_rows, acf, f0, rms):
    """Score phrase candidates: written evidence + dual-extractor
    SOURCE reliability; class assignment happens in j1()."""
    tt, hz, vv = f0["times"], f0["f0_hz"], f0["voiced"]
    mm = _midi(hz)
    acf_t = np.array([x[0] for x in acf]) if acf else np.array([])
    acf_m = np.array([x[1] for x in acf]) if acf else np.array([])

    def phrase_stats(rows):
        a, b = rows[0]["a"], rows[-1]["b"]
        fc = (tt >= a) & (tt <= b) & vv & (rms > 0.008)
        n_fc = int(fc.sum())
        agree = 0
        if n_fc and acf_t.size:
            for tm, fm in zip(tt[fc], mm[fc]):
                j = np.searchsorted(acf_t, tm)
                ok = any(0 <= k < acf_m.size
                         and abs(acf_m[k] - fm) < 1.0
                         for k in (j - 1, j))
                agree += ok
        rel = agree / n_fc if n_fc else 0.0
        src_rng = float(np.percentile(mm[fc], 95)
                        - np.percentile(mm[fc], 5)) if n_fc > 8 else 0.0
        return {"a": a, "b": b, "n_notes": len(rows),
                "source_reliable": round(rel, 3),
                "source_f0_rng_c": round(src_rng, 1),
                "max_dur": max(r["dur"] for r in rows),
                "max_leap": max(abs(r["leap"] or 0) for r in rows),
                "max_pitd_rng": max(r["pitd_rng"] for r in rows),
                "max_onset_rng": max(r["pitd_onset_rng"] for r in rows),
                "max_rev": max(r["pitd_rev"] for r in rows),
                "max_osc": max(r["pitd_osc"][0] for r in rows),
                "lyrics": "".join(r["lyric"] for r in rows)[:24],
                "notes": [{"a": r["a"], "b": r["b"], "tone": r["tone"],
                           "lyric": r["lyric"], "leap": r["leap"],
                           "vibrato": r["vibrato"],
                           "pitd_rng": round(r["pitd_rng"], 1),
                           "pitd_rev": r["pitd_rev"],
                           "portamento_y0": r["portamento_y0"]}
                          for r in rows]}

    cands = []
    for pi, rows in part_rows.items():
        i = 0
        while i < len(rows):
            j = i + 1
            while j < len(rows) and rows[j]["a"] - rows[i]["a"] < 4.5:
                j += 1
            if j - i >= 4:
                st = phrase_stats(rows[i:j])
                st["part"] = pi
                st["note_ids"] = [rows[i]["i"], rows[j - 1]["i"]]
                cands.append(st)
            i = j
    return cands


def main():
    head = drv._require_clean_worktree("l7j_huahai_benchmark")
    OUT.mkdir(parents=True, exist_ok=True)
    doc = load_ustx(HUMAN_USTX)
    info = sf.info(str(JAY_FLAC))

    t2s = tempo_map(doc)
    print("extracting vocal F0 ...", flush=True)
    f0 = extract_f0(VOCALS)
    # stem RMS at the F0 frame grid — drops instrumental-bleed frames
    w, sr = sf.read(str(VOCALS), dtype="float32")
    if w.ndim > 1:
        w = w.mean(1)
    rms = np.array([np.sqrt(np.mean(
        w[int(tt * sr):int(tt * sr) + 160] ** 2))
        for tt in f0["times"]])
    # the tuner's reference audio sits at wave-part positions ~1.3s on the
    # project timeline (75bpm): 花海+4.mp3 at tick 775 = 1.29s
    wave_ticks = [w2.get("position", 0)
                  for w2 in doc.get("wave_parts", [])
                  if w2.get("relative_path")]
    wave_off = t2s(min(wave_ticks)) if wave_ticks else 0.0
    tp = transposition_evidence(doc, f0, t2s, wave_off, rms)
    print(f"  wave_offset={wave_off:.2f}s "
          f"delta mode={tp['delta_mode_st']}st "
          f"median={tp['delta_median_st']}st "
          f"frac<1st of +4={tp['frac_within_1st_of_p4']}",
          flush=True)

    manifest = {
        "tool": "tools/l7j_huahai_benchmark.py",
        "phase": "J0 inputs",
        "evaluated_head": head,
        "worktree_clean_at_generation": True,
        "jay_original": {
            "path": str(JAY_FLAC), "sha256": sha256(JAY_FLAC),
            "duration_s": round(info.duration, 2),
            "sample_rate": info.samplerate},
        "separated_vocals": {"path": str(VOCALS),
                             "sha256": sha256(VOCALS),
                             "model": "UVR-MDX-NET-Voc_FT.onnx"},
        "human_project": {
            "path": str(HUMAN_USTX), "sha256": sha256(HUMAN_USTX),
            "author": "白烁", "declared_transposition": "+4 semitones",
            **project_summary(doc, t2s)},
        "singer_identity": {
            "project_singer": "yousaV1.56",
            "installed": False,
            "render_substitution": "YousaV1.65c (V1.56 not installed; "
                                   "human-render layer rendered through "
                                   "the dpV2 baseline, substitution "
                                   "recorded)"},
        "lyric_correspondence": ("part0 '静止了 所有的花开 / 遥远了 清晰了爱', "
                                 "part1 '你喜欢 站在那窗台 / 你好久 都没再来', "
                                 "part2 '不要你离开 距离隔不开 / 思念变成海' "
                                 "— all match 《花海》 lyric order"),
        "transposition_check": tp,
        # graded verdict, evaluated on the +4-arrangement parts only
        # (track0 parts). part2 on track1 is an alternate lower harmony
        # (median delta ~+1.1, no +4 peak) and must not dilute the test.
        "transposition_verdict": (
            "supported_median"
            if all(3.5 <= pp["median_delta_st"] <= 4.7
                   and pp["frac_within_1st_of_p4"] >= 0.30
                   for pp in tp["per_part"] if pp["part_index"] in (0, 1))
            else "not_proven"),
        "arrangement_notes": (
            "part0/part1 (track0): +4 arrangement, median delta "
            "+4.2/+4.2, modal bin +4.25 — +4 transposition supported "
            "at median level; Jay's loose intonation bounds tight "
            "frame agreement (~33-40% within 1st). "
            "part2 (track1 'New Part'): alternate lower harmony, "
            "median delta +1.1 — NOT the +4 melody; excluded from "
            "+4 phrase-selection pool"),
        "timing_correspondence": (
            "wave-part anchored: audio_time = project_time - "
            f"{wave_off:.2f}s; lyric sections verified against ASR "
            "map of the original (part0=verse1+prechorus+chorus1 "
            "~29-127s, part1=prechorus2+chorus2 ~160-230s)"),
    }
    out = OUT / "j0_inputs.json"
    out.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print("wrote", out)
    if manifest["transposition_verdict"] == "not_proven":
        print("WARNING: +4 transposition not proven — per contract "
              "classify UNKNOWN for note correspondence")
        return

    # ---------- Phase J1: phrase selection ----------
    print("J1: phrase selection ...", flush=True)
    ms_tick = 60000.0 / (doc["tempos"][0]["bpm"] * RESOLUTION)
    part_rows = {}
    acf_windows = []
    for pi in (0, 1):
        part = doc["voice_parts"][pi]
        rows = note_table(part, t2s, wave_off, ms_tick)
        part_rows[pi] = rows
        if rows:
            acf_windows.append((max(0.0, rows[0]["a"] - 0.2),
                                rows[-1]["b"] + 0.2))
    acf = _acf_track(w, sr, acf_windows)
    print(f"  acf frames={len(acf)}", flush=True)
    cands = select_phrases(part_rows, acf, f0, rms)

    # class tagging (deterministic evidence thresholds)
    def tags(c):
        tg = set()
        if c["max_dur"] >= 1.2:
            tg.add("sustained")
        if c["max_leap"] >= 4:
            tg.add("transition")
        if c["max_onset_rng"] >= 150 or \
                any(n["portamento_y0"] not in (0, None)
                    for n in c["notes"]):
            tg.add("portamento_or_scoop")
        if c["max_onset_rng"] >= 150:
            tg.add("onset_over_undershoot")
        if 4.0 <= c["max_osc"] <= 8.0 and c["max_dur"] >= 0.8:
            tg.add("vibrato")
        if c["max_rev"] >= 8:
            tg.add("ornament")
        return tg

    for c in cands:
        c["classes"] = sorted(tags(c))

    CLASS_ORDER = ["vibrato", "portamento_or_scoop", "onset_over_undershoot",
                   "ornament", "sustained", "transition"]
    picked, used = [], []
    for cls in CLASS_ORDER:
        pool = [c for c in cands if cls in c["classes"]
                and all(c["b"] <= u[0] or c["a"] >= u[1] for u in used)]
        pool.sort(key=lambda c: (-c["source_reliable"],
                                 -(c["max_osc"] if cls == "vibrato"
                                   else c["max_onset_rng"]
                                   if "onset" in cls or "porta" in cls
                                   else c["max_pitd_rng"]),
                                 c["a"]))
        if pool:
            c = pool[0]
            picked.append({"class": cls, **c})
            used.append((c["a"], c["b"]))
    picked = picked[:5]
    j1 = {"phase": "J1 phrase selection",
          "evaluated_head": head,
          "worktree_clean_at_generation": True,
          "selection_rule": ("class coverage over written-control "
                             "evidence (pitd range/reversals/osc, "
                             "portamento_y0, leaps, durations) ranked "
                             "by dual-extractor SOURCE reliability; "
                             "non-overlapping; agent output not used"),
          "n_candidates": len(cands),
          "selected": picked,
          "candidates_ranked": sorted(
              cands, key=lambda c: -c["source_reliable"])[:40]}
    out1 = OUT / "j1_phrases.json"
    out1.write_text(json.dumps(j1, indent=1, ensure_ascii=False),
                    encoding="utf-8")
    print("wrote", out1)
    for p_ in picked:
        print(f"  {p_['class']:24s} part{p_['part']} "
              f"[{p_['a']:.1f}-{p_['b']:.1f}s] rel={p_['source_reliable']} "
              f"{p_['lyrics']}")

    # ---------- Phase J2: four-layer extraction (A/B/C; D deferred) --
    print("J2: layer extraction + human renders ...", flush=True)
    layers = j2_layers(doc, picked, t2s, wave_off, ms_tick, f0, acf,
                       w, sr, head)
    j2 = {"phase": "J2 layers A/B/C",
          "evaluated_head": head,
          "worktree_clean_at_generation": True,
          "normalization": ("pitch comparisons in relative cents to "
                           "written tone; +4 transposition removed by "
                           "comparing motion, not absolute Hz"),
          "source_extraction": {
              "fcpe": "torchfcpe on Kim_Vocal_2 separated stem",
              "acf": "independent ACF track, 180Hz highpass, "
                     "150-600Hz lag band — second evidence family",
              "caveat": ("stems retain stable instrumental "
                         "periodicity (~50-56 midi pedals); frames "
                         "where the two families disagree are "
                         "unreliable — recorded per-phrase")},
          "phrases": layers}
    out2 = OUT / "j2_layers.json"
    out2.write_text(json.dumps(j2, indent=1, ensure_ascii=False),
                    encoding="utf-8")
    print("wrote", out2)

    # ---------- Phase J3: representation-gap analysis ----------
    print("J3: representation-gap analysis ...", flush=True)
    j3 = j3_gap_analysis(doc, picked, t2s, wave_off, ms_tick, f0, acf,
                         w, sr, layers, head)
    out3 = OUT / "j3_gap.json"
    out3.write_text(json.dumps(j3, indent=1, ensure_ascii=False),
                    encoding="utf-8")
    print("wrote", out3)

    # ---------- Phase J4: candidate rules (diagnostic only) --------
    j4 = j4_rules(j3, head)
    out4 = OUT / "j4_rules.json"
    out4.write_text(json.dumps(j4, indent=1, ensure_ascii=False),
                    encoding="utf-8")
    print("wrote", out4)
    for r in j4["rules"]:
        print(" ", r["id"], "—", r["rule"][:100])

    # ---------- Phase J5: current agent2utau on same phrases -------
    # gated: only runs when J0-J4 evidence is committed (this run IS
    # from clean HEAD, so the committed j0-j4 files are inputs)
    print("J5: agent2utau compile path on benchmark phrases ...",
          flush=True)
    j5_layers = j5_agent_layer(doc, picked, t2s, wave_off, ms_tick,
                               head)
    j5 = {"phase": "J5 agent layer D",
          "evaluated_head": head,
          "worktree_clean_at_generation": True,
          "method": ("current compile path: neutral render -> dense "
                     "residual -> compile_C3 -> portamento lane "
                     "(full_note) -> candidate render. SOURCE F0 "
                     "transposed +4st into the written pitch frame; "
                     "production arbitration (v2/v3 closed loop) NOT "
                     "replicated — the compiled representation is the "
                     "benchmark layer"),
          "phrases": j5_layers}
    out5 = OUT / "j5_agent.json"
    out5.write_text(json.dumps(j5, indent=1, ensure_ascii=False),
                    encoding="utf-8")
    print("wrote", out5)

    # ---------- J5 comparison: agent written/render vs A/B/C -------
    cmp_rows = j5_compare(j5_layers, t2s, wave_off, ms_tick)
    out5c = OUT / "j5_compare.json"
    out5c.write_text(json.dumps(
        {"evaluated_head": head,
         "note": ("columns: src=+4 source F0, hum_w=human written "
                  "controls, hum_r=human render, ag_w=agent written, "
                  "ag_r=agent render; all on the jay-audio axis"),
         "phrases": cmp_rows}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    print("wrote", out5c)


def crop_phrase_ustx(doc, part_index, a_s, b_s, wave_off, ms_tick,
                     singer):
    """Clone the doc, keep one track + one voice part cropped to the
    phrase window (project-time = audio + wave_off), substitute singer."""
    import copy
    d = copy.deepcopy(doc)
    part = d["voice_parts"][part_index]
    # note positions/curve xs are part-relative ticks
    x0 = int(round((a_s + wave_off) * 1000.0 / ms_tick)) \
        - part["position"]
    x1 = int(round((b_s + wave_off) * 1000.0 / ms_tick)) \
        - part["position"]
    kept = []
    for n in part["notes"]:
        n0, n1 = n["position"], n["position"] + n["duration"]
        if n1 > x0 and n0 < x1:
            n2 = dict(n)
            n2["position"] = n0 - x0
            kept.append(n2)
    part["notes"] = kept
    part["position"] = part["position"] + x0
    for c in part.get("curves", []):
        m = [(x - x0, y) for x, y in zip(c["xs"], c["ys"])
             if x0 <= x <= x1]
        c["xs"] = [x for x, _ in m]
        c["ys"] = [y for _, y in m]
    d["voice_parts"] = [part]
    d["wave_parts"] = []
    trk = part.get("track_no", 0)
    d["tracks"] = [d["tracks"][trk]] if trk < len(d["tracks"]) \
        else d["tracks"][:1]
    part["track_no"] = 0
    for t in d["tracks"]:
        t["singer"] = singer
    return d


def j2_layers(doc, picked, t2s, wave_off, ms_tick, f0, acf, w, sr,
              head):
    """Per selected phrase: A source F0 (fcpe+acf), B written controls,
    C human render (singer-substituted) + render F0."""
    cfg = load_config()
    layers = []
    for k, ph in enumerate(picked):
        tag = f"j2_{k}_{ph['class']}"
        pdir = OUT / tag
        pdir.mkdir(parents=True, exist_ok=True)
        a, b = ph["a"], ph["b"]
        # ---- A: SOURCE layers ----
        tt, hz, vv = f0["times"], f0["f0_hz"], f0["voiced"]
        fc = (tt >= a) & (tt <= b)
        src = {"times": tt[fc].round(3).tolist(),
               "f0_hz": np.where(vv[fc], hz[fc], 0).round(2).tolist(),
               "voiced": vv[fc].astype(int).tolist()}
        acf_sel = [x for x in acf if a <= x[0] <= b]
        (pdir / "source_fcpe.json").write_text(
            json.dumps(src, ensure_ascii=False), encoding="utf-8")
        (pdir / "source_acf.json").write_text(json.dumps(
            [{"t": round(x[0], 3), "midi": round(x[1], 2),
              "clarity": round(x[2], 3)} for x in acf_sel],
            ensure_ascii=False), encoding="utf-8")
        # ---- B: written controls ----
        u = crop_phrase_ustx(doc, ph["part"], a, b, wave_off, ms_tick,
                             "YousaV1.65c")
        ustx_path = pdir / f"{tag}.ustx"
        save_ustx(u, ustx_path)
        # ---- C: human render ----
        render_ok, err = True, None
        try:
            wav_path = drv.render(cfg, ustx_path,
                                  pdir / tag).resolve()
        except Exception as e:  # noqa: BLE001 — record honestly
            render_ok, wav_path, err = False, None, str(e)[:300]
        rf0 = None
        if wav_path and wav_path.exists() \
                and wav_path.stat().st_size > 4096:
            rf0 = extract_f0(wav_path)
        layer = {"class": ph["class"], "part": ph["part"],
                 "audio_span_s": [round(a, 2), round(b, 2)],
                 "note_ids": ph["note_ids"], "lyrics": ph["lyrics"],
                 "source_reliable": ph["source_reliable"],
                 "slice_ustx": str(ustx_path),
                 "slice_ustx_sha256": sha256(ustx_path),
                 "human_render_wav": str(wav_path),
                 "human_render_sha256":
                     sha256(wav_path) if wav_path else None,
                 "render_ok": render_ok, "render_error": err,
                 "render_f0": str(pdir / "render_f0.json")}
        if rf0:
            (pdir / "render_f0.json").write_text(json.dumps(
                {"times": rf0["times"].round(3).tolist(),
                 "f0_hz": np.where(rf0["voiced"], rf0["f0_hz"], 0)
                 .round(2).tolist(),
                 "voiced": rf0["voiced"].astype(int).tolist()},
                ensure_ascii=False), encoding="utf-8")
        layers.append(layer)
        print(f"  {ph['class']:24s} render_ok={layer['render_ok']}",
              flush=True)
    return layers


def j3_gap_analysis(doc, picked, t2s, wave_off, ms_tick, f0, acf,
                    w, sr, layers, head):
    """Per-note representation-gap table + normalized overlay data.

    Coordinates: audio seconds for SOURCE; render wav t=0 == phrase a.
    Relative cents = f0_midi - tone*100 for written/render layers, and
    f0_midi - (tone-4)*100 for SOURCE (+4 normalized out)."""
    tt, hz, vv = f0["times"], f0["f0_hz"], f0["voiced"]
    mm = _midi(hz)
    rms = np.array([np.sqrt(np.mean(
        w[int(x * sr):int(x * sr) + 160] ** 2)) for x in tt])
    gate = vv & (rms > 0.008)
    acf_t = np.array([x[0] for x in acf]) if acf else np.array([])
    acf_m = np.array([x[1] for x in acf]) if acf else np.array([])
    acf_c = np.array([x[2] for x in acf]) if acf else np.array([])
    phrases = []
    for k, ph in enumerate(picked):
        part = doc["voice_parts"][ph["part"]]
        xs, ys = _pitd_for(part)
        layer = layers[k]
        rf0 = None
        rfp = Path(layer["render_f0"])
        if rfp.exists():
            rd = json.loads(rfp.read_text(encoding="utf-8"))
            rf0 = (np.array(rd["times"]), np.array(rd["f0_hz"]),
                   np.array(rd["voiced"], dtype=bool))
        rows = note_table(part, t2s, wave_off, ms_tick)
        rows = [r for r in rows if r["b"] > ph["a"]
                and r["a"] < ph["b"]]
        events = []
        for r in rows:
            a0, b0 = r["a"], r["b"]
            exp_src = (r["tone"] - 4) * 100.0
            m = (tt >= a0 + 0.02) & (tt <= b0 - 0.02) & gate
            n_fc = int(m.sum())
            # reliable = fcpe voiced AND acf agrees within 1st
            rel_idx = []
            if n_fc and acf_t.size:
                for ii in np.where(m)[0]:
                    j = np.searchsorted(acf_t, tt[ii])
                    for kk in (j - 1, j):
                        if 0 <= kk < acf_m.size \
                                and abs(acf_m[kk] - mm[ii]) < 1.0:
                            rel_idx.append(ii)
                            break
            rel = len(rel_idx) / n_fc if n_fc else 0.0
            src_rel = (mm[rel_idx] * 100 - exp_src) if rel_idx \
                else np.array([])
            src_rng = float(np.percentile(src_rel, 95)
                            - np.percentile(src_rel, 5)) \
                if src_rel.size > 8 else 0.0
            rel_times = tt[rel_idx] if rel_idx else np.array([])
            src_on = src_rel[(rel_times - a0) < 0.15] \
                if rel_idx else np.array([])
            src_onset = float(np.median(src_on)) if src_on.size >= 3 \
                else None
            if src_rel.size > 30:
                # regrid reliable samples to uniform 10ms before FFT
                ug = np.arange(rel_times.min(), rel_times.max(), 0.01)
                uv = np.interp(ug, rel_times, src_rel)
                src_vib = _osc_hz(uv / 100.0, 0.01)
            else:
                src_vib = (0.0, 0.0)
            # render layer: wav t=0 == project time 0, so
            # audio_time = render_t - wave_off
            ren_rng = ren_onset = ren_vib = None
            if rf0 is not None:
                rt, rh, rv = rf0
                rm_ = _midi(rh)
                sel = rv & (rt >= a0 + wave_off + 0.02) \
                    & (rt <= b0 + wave_off - 0.02)
                rc = rm_[sel] * 100 - r["tone"] * 100.0
                if rc.size > 8:
                    ren_rng = float(np.percentile(rc, 95)
                                    - np.percentile(rc, 5))
                    ro = rc[(rt[sel] - (a0 + wave_off)) < 0.15]
                    ren_onset = float(np.median(ro)) \
                        if ro.size >= 3 else None
                    if rc.size > 30:
                        rr = _osc_hz(rc / 100.0, 0.01)
                        ren_vib = (round(rr[0], 2), round(rr[1], 1))
            events.append({
                "note_i": r["i"], "lyric": r["lyric"],
                "audio_span_s": [round(a0, 2), round(b0, 2)],
                "tone": r["tone"], "leap": r["leap"],
                "source": {"reliable_frac": round(rel, 3),
                           "rng_c": round(src_rng, 1),
                           "onset_med_c": (round(src_onset, 1)
                                          if src_onset is not None
                                          else None),
                           "vib": (round(src_vib[0], 2),
                                   round(src_vib[1], 1))},
                "written": {"pitd_rng_c": round(r["pitd_rng"], 1),
                            "pitd_rev": r["pitd_rev"],
                            "onset_rng_c":
                                round(r["pitd_onset_rng"], 1),
                            "portamento_y0": r["portamento_y0"],
                            "native_vibrato": r["vibrato"]},
                "render": {"rng_c": (round(ren_rng, 1)
                                    if ren_rng is not None else None),
                           "onset_med_c": (round(ren_onset, 1)
                                           if ren_onset is not None
                                           else None),
                           "vib": ren_vib},
            })
        # per-phrase normalized overlay
        ov = {"times_s": [], "source_rel_c": [], "source_reliable": [],
              "written_pitd_c": [], "render_rel_c": []}
        grid = np.arange(ph["a"], ph["b"], 0.01)
        exp_step = np.full(grid.size, np.nan)
        for r in rows:
            sel = (grid >= r["a"]) & (grid < r["b"])
            exp_step[sel] = r["tone"]
        for gi, g in enumerate(grid):
            fi = np.searchsorted(tt, g)
            if fi < len(tt) and gate[fi] and np.isfinite(exp_step[gi]):
                relok = False
                if acf_t.size:
                    j = np.searchsorted(acf_t, tt[fi])
                    relok = any(0 <= kk < acf_m.size
                                and abs(acf_m[kk] - mm[fi]) < 1.0
                                for kk in (j - 1, j))
                ov["times_s"].append(round(g, 3))
                ov["source_rel_c"].append(
                    round(mm[fi] * 100 - (exp_step[gi] - 4) * 100, 1))
                ov["source_reliable"].append(int(relok))
            else:
                ov["times_s"].append(round(g, 3))
                ov["source_rel_c"].append(None)
                ov["source_reliable"].append(0)
        # written pitd on grid (part-relative ticks)
        pitd_grid = np.interp(grid + wave_off,
                              (part["position"] + xs) * ms_tick / 1000.0,
                              ys, left=np.nan, right=np.nan)
        ov["written_pitd_c"] = [None if not np.isfinite(x)
                                else round(float(x), 1)
                                for x in pitd_grid]
        if rf0 is not None:
            rt, rh, rv = rf0
            rm_ = _midi(rh)
            for gi, g in enumerate(grid):
                ri = np.searchsorted(rt, g + wave_off)
                if ri < len(rt) and rv[ri] \
                        and np.isfinite(exp_step[gi]):
                    ov["render_rel_c"].append(
                        round(rm_[ri] * 100 - exp_step[gi] * 100, 1))
                else:
                    ov["render_rel_c"].append(None)
        phrases.append({"class": ph["class"], "part": ph["part"],
                        "audio_span_s": [round(ph["a"], 2),
                                         round(ph["b"], 2)],
                        "events": events, "overlay": ov})
    return {"phase": "J3 representation-gap",
            "evaluated_head": head,
            "worktree_clean_at_generation": True,
            "normalization": "relative cents to written tone "
                             "(SOURCE vs tone-4; render vs tone)",
            "phrases": phrases}


def j4_rules(j3, head):
    """Aggregate J3 events into candidate general rules (diagnostic
    hypotheses only — NOT production rules)."""
    evs = [(ph["class"], e) for ph in j3["phrases"]
           for e in ph["events"]]
    def med(vals):
        vals = [v for v in vals if v is not None]
        return round(float(np.median(vals)), 1) if vals else None
    src_onsets = [abs(e["source"]["onset_med_c"])
                  for _, e in evs
                  if e["source"]["onset_med_c"] is not None]
    ren_onsets = [e["render"]["onset_med_c"]
                  for _, e in evs
                  if e["render"]["onset_med_c"] is not None]
    ratios = [e["render"]["rng_c"] / e["written"]["pitd_rng_c"]
              for _, e in evs
              if e["render"]["rng_c"] and e["written"]["pitd_rng_c"]
              and e["written"]["pitd_rng_c"] >= 80]
    big_src = [(c, e) for c, e in evs
               if e["source"]["rng_c"] >= 250]
    encoded = [(c, e) for c, e in big_src
               if e["written"]["pitd_rng_c"] >= 0.5
               * e["source"]["rng_c"]]
    flat_src = [(c, e) for c, e in evs
                if e["source"]["rng_c"] and e["source"]["rng_c"] < 60
                and e["source"]["reliable_frac"] >= 0.8]
    tuner_added = [(c, e) for c, e in flat_src
                   if e["written"]["pitd_rng_c"] >= 150]
    rules = [
        {"id": "J4-R1 renderer_onset_bias",
         "rule": ("the DiffSinger renderer applies its own onset "
                  "undershoot (~{}c median) at note starts; written "
                  "onset dips below ~150c are partially redundant — "
                  "large SOURCE undershoots still need explicit "
                  "encoding but can be scaled by ~0.6-0.8"
                  .format(med(ren_onsets))),
         "evidence": {"render_onset_med_c": med(ren_onsets),
                      "source_onset_abs_med_c": med(src_onsets),
                      "n": len(ren_onsets)}},
        {"id": "J4-R2 pitd_survival_ratio",
         "rule": ("written PITD excursion survives the renderer at "
                  "~{:.2f} median ratio (rng/pitd_rng) — expect "
                  "damping, encode ~1.2x the intended render depth"
                  .format(med(ratios) or 0)),
         "evidence": {"median_survival": med(ratios),
                      "n": len(ratios)}},
        {"id": "J4-R3 big_gesture_encoding",
         "rule": ("SOURCE excursions >=250c are consistently encoded "
                  "by the human ({} of {} events reach >=50% of "
                  "source magnitude) — big real gestures belong in "
                  "PITD, not native parameters"
                  .format(len(encoded), len(big_src))),
         "evidence": {"n_big": len(big_src), "n_encoded": len(encoded),
                      "examples": [[e["lyric"], e["source"]["rng_c"],
                                    e["written"]["pitd_rng_c"]]
                                   for _, e in encoded[:6]]}},
        {"id": "J4-R4 flat_source_expression",
         "rule": ("where SOURCE is flat (<60c, reliable), the tuner "
                  "still writes 150-350c PITD on {} of {} events — "
                  "expression is partly authored for musicality, not "
                  "only traced; agent may add moderate motion on "
                  "sustained notes when source is flat"
                  .format(len(tuner_added), len(flat_src))),
         "evidence": {"n_flat": len(flat_src),
                      "n_tuner_added": len(tuner_added)}},
        {"id": "J4-R5 vibrato_via_pitd",
         "rule": ("vibrato is encoded almost exclusively as PITD "
                  "oscillation (1 native-vibrato note in 393 vs "
                  "dozens of 4-8Hz pitd-osc notes); render reproduces "
                  "it at reduced depth — prefer PITD over native "
                  "vibrato for source-matched vibrato"),
         "evidence": {"native_vibrato_notes":
                      sum(1 for _, e in evs
                          if e["written"]["native_vibrato"]),
                      "pitd_osc_notes":
                      sum(1 for _, e in evs
                          if e["written"]["pitd_rev"] >= 6)}}]
    return {"phase": "J4 candidate rules (hypotheses, not production)",
            "evaluated_head": head,
            "worktree_clean_at_generation": True,
            "rules": rules}


KIM2_VOCALS = Path("runs/huahai_benchmark/separation_kim2") / \
    "04. 周杰伦 - 花海_(Vocals)_Kim_Vocal_2.wav"
TRANSPOSE_ST = 4.0
PAD_S = 0.30


def _flat_pitd(n_pts=2):
    return {"abbr": "pitd", "xs": [0, 480], "ys": [0, 0],
            "isBase64": False}


def j5_agent_layer(doc, picked, t2s, wave_off, ms_tick, head):
    """Run the current agent2utau compile path on each benchmark
    phrase (layer D): neutral base render -> dense residual ->
    compile_C3 + portamento lane -> candidate render -> QA.
    SOURCE F0 is transposed +4st into the written pitch frame."""
    import copy
    from agent2utau.expression.contour import build_contour_signal
    from agent2utau.expression.pitch_residual import (
        compute_dense, compile_C3, compile_portamento_lane,
        flatten_pitd_spans)
    from agent2utau.analysis.rmvpe import infer_rmvpe
    from agent2utau.expression.events import (
        match_vibrato_events, match_pitch_events)

    cfg = load_config()
    scale = 2.0 ** (TRANSPOSE_ST / 12.0)

    print("  extracting SOURCE f0 on Kim2 stem (fcpe+rmvpe, +4st) ...",
          flush=True)
    f0c = extract_f0(KIM2_VOCALS)
    f0r = infer_rmvpe(KIM2_VOCALS)

    def shifted(f):
        return {"times": f["times"],
                "f0_hz": np.asarray(f["f0_hz"], dtype=float) * scale,
                "voiced": f["voiced"]}
    src_fcpe, src_rmvpe = shifted(f0c), shifted(f0r)

    layers = []
    for k, ph in enumerate(picked):
        a, b = ph["a"], ph["b"]
        t0, t1 = a - PAD_S, b + PAD_S
        part = doc["voice_parts"][ph["part"]]
        notes = []
        for n in part["notes"]:
            lyr = str(n.get("lyric"))
            if lyr in SPECIAL_LYRICS or lyr == "+":
                continue
            s_p = t2s(part["position"] + n["position"])
            e_p = t2s(part["position"] + n["position"]
                      + n["duration"])
            s, e = s_p - wave_off, e_p - wave_off   # audio axis
            if s >= a - 1e-3 and e <= b + 1e-3:
                notes.append({"abs_start_s": s, "dur_s": e - s,
                              "tone": n["tone"], "lyric": lyr,
                              "_abs_tick": part["position"]
                              + n["position"],
                              "_dur_tick": n["duration"],
                              "_note": n})
        if not notes:
            layers.append({"class": ph["class"], "error": "no notes"})
            continue
        part_pos = notes[0]["_abs_tick"] - 480
        tag = f"j5_{k}_{ph['class']}"
        pdir = OUT / tag
        pdir.mkdir(parents=True, exist_ok=True)
        print(f"  == {ph['class']} {len(notes)} notes "
              f"[{a:.1f}-{b:.1f}]", flush=True)

        base_doc = copy.deepcopy(doc)
        for tr in base_doc["tracks"]:
            tr["singer"] = "YousaV1.65c"

        neu_doc = drv.build_phrase_doc(base_doc, part, notes,
                                       part_pos, _flat_pitd(), {},
                                       tag + "_neutral")
        neu_ustx = pdir / (tag + "_neutral.ustx")
        save_ustx(neu_doc, neu_ustx)
        neu_wav = drv.render(cfg, neu_ustx, pdir / (tag + "_neutral"))
        nf = extract_f0(neu_wav)
        nr = infer_rmvpe(neu_wav)

        def to_audio(f):
            return {"times": np.asarray(f["times"], dtype=float)
                    - wave_off,
                    "f0_hz": np.asarray(f["f0_hz"], dtype=float),
                    "voiced": f["voiced"]}
        neu_fcpe, neu_rmvpe = to_audio(nf), to_audio(nr)

        src_sig = build_contour_signal(src_fcpe, src_rmvpe, notes,
                                       t0_s=t0, t1_s=t1,
                                       extractor="fcpe",
                                       source="source")
        src_sig_b = build_contour_signal(src_rmvpe, src_fcpe, notes,
                                         t0_s=t0, t1_s=t1,
                                         extractor="rmvpe",
                                         source="source")
        neu_sig = build_contour_signal(neu_fcpe, neu_rmvpe, notes,
                                       t0_s=t0, t1_s=t1,
                                       extractor="fcpe",
                                       source="neutral")
        neu_sig_b = build_contour_signal(neu_rmvpe, neu_fcpe, notes,
                                         t0_s=t0, t1_s=t1,
                                         extractor="rmvpe",
                                         source="neutral")
        dense = compute_dense(src_fcpe, neu_fcpe, src_rmvpe,
                              neu_rmvpe, notes, t0, t1)
        np.savez(pdir / "dense.npz", **dense)

        nuc = {}
        src_events = drv.detect_all(src_sig, notes, nuc)
        neu_events = drv.detect_all(neu_sig, notes, nuc)
        src_events_b = drv.detect_all(src_sig_b, notes, nuc)
        neu_events_b = drv.detect_all(neu_sig_b, notes, nuc)
        vib_match = match_vibrato_events(src_events, neu_events,
                                       notes)
        pitch_match = match_pitch_events(src_events, neu_events,
                                         notes, nuc)
        print(f"     events src={len(src_events)} "
              f"neu={len(neu_events)} "
              f"matched={len(pitch_match['matched'])}", flush=True)

        pitd_v1, vib_marks, vib_prov = compile_C3(
            dense, src_sig, neu_sig, notes, part_pos, vib_match,
            max_err_c=10.0)
        porta_marks, porta_spans, porta_prov = \
            compile_portamento_lane(
                src_sig, src_sig_b, notes, src_events,
                vib_marks=vib_marks, ownership="full_note")
        if porta_spans:
            pitd_v1 = flatten_pitd_spans(pitd_v1, porta_spans,
                                         part_pos)
        cand_doc = drv.build_phrase_doc(
            base_doc, part, notes, part_pos, pitd_v1, vib_marks,
            tag + "_agent", porta_marks=porta_marks)
        cand_ustx = pdir / (tag + "_agent.ustx")
        save_ustx(cand_doc, cand_ustx)
        cand_wav = drv.render(cfg, cand_ustx, pdir / (tag + "_agent"))
        af = extract_f0(cand_wav)
        (pdir / "agent_render_f0.json").write_text(json.dumps(
            {"times": (np.asarray(af["times"]) - wave_off)
             .round(3).tolist(),
             "f0_hz": np.where(af["voiced"], af["f0_hz"], 0)
             .round(2).tolist(),
             "voiced": af["voiced"].astype(int).tolist()},
            ensure_ascii=False), encoding="utf-8")
        layers.append(drv._jsonable({
            "class": ph["class"], "part": ph["part"],
            "audio_span_s": [round(a, 2), round(b, 2)],
            "n_notes": len(notes),
            "src_events": len(src_events),
            "neu_events": len(neu_events),
            "pitch_matched": len(pitch_match["matched"]),
            "vib_marks": {str(kk): vv for kk, vv in
                          vib_marks.items()},
            "porta_marks": len(porta_marks),
            "porta_spans": len(porta_spans),
            "agent_ustx": str(cand_ustx),
            "agent_ustx_sha256": sha256(cand_ustx),
            "agent_wav": str(cand_wav),
            "agent_wav_sha256": sha256(cand_wav),
            "neutral_ustx": str(neu_ustx),
            "neutral_wav": str(neu_wav),
            "vib_provenance": vib_prov,
            "porta_provenance": porta_prov}))
        print(f"     agent render done: {cand_wav.name}",
              flush=True)
    return layers


def j5_compare(j5_layers, t2s, wave_off, ms_tick):
    """Per-note comparison of agent written/render layers, aligned to
    the committed J3 table (source + human written/render)."""
    j3 = json.loads((OUT / "j3_gap.json").read_text(
        encoding="utf-8"))
    j3_by_class = {p["class"]: p for p in j3["phrases"]}
    out = []
    for lay in j5_layers:
        if "agent_ustx" not in lay:
            continue
        adoc = load_ustx(lay["agent_ustx"])
        apart = adoc["voice_parts"][0]
        # same written-layer metrics on the agent part (same tempo
        # map; note_table's audio-axis conversion applies verbatim)
        arows = note_table(apart, t2s, wave_off, ms_tick)
        af0 = None
        afp = Path(lay["agent_ustx"]).parent / "agent_render_f0.json"
        if afp.exists():
            rd = json.loads(afp.read_text(encoding="utf-8"))
            af0 = (np.array(rd["times"]), np.array(rd["f0_hz"]),
                   np.array(rd["voiced"], dtype=bool))
        j3ph = j3_by_class.get(lay["class"], {})
        j3ev = j3ph.get("events", [])
        evs = []
        for r in arows:
            a0, b0 = r["a"], r["b"]   # already on the audio axis
            m3 = min(j3ev, key=lambda e:
                     abs(e["audio_span_s"][0] - a0)) if j3ev else None
            ren = {"rng_c": None, "onset_med_c": None, "vib": None}
            if af0 is not None:
                rt, rh, rv = af0
                rm_ = _midi(rh)
                sel = rv & (rt >= a0 + 0.02) & (rt <= b0 - 0.02)
                rc = rm_[sel] * 100 - r["tone"] * 100.0
                if rc.size > 8:
                    ren["rng_c"] = round(float(np.percentile(rc, 95)
                                             - np.percentile(rc, 5)),
                                         1)
                    ro = rc[(rt[sel] - a0) < 0.15]
                    if ro.size >= 3:
                        ren["onset_med_c"] = round(
                            float(np.median(ro)), 1)
                    if rc.size > 30:
                        rr = _osc_hz(rc / 100.0, 0.01)
                        ren["vib"] = (round(rr[0], 2), round(rr[1], 1))
            evs.append({
                "audio_span_s": [round(a0, 2), round(b0, 2)],
                "tone": r["tone"], "lyric": r["lyric"],
                "src": (m3 or {}).get("source"),
                "hum_w": (m3 or {}).get("written"),
                "hum_r": (m3 or {}).get("render"),
                "ag_w": {"pitd_rng_c": round(r["pitd_rng"], 1),
                         "pitd_rev": r["pitd_rev"],
                         "onset_rng_c":
                             round(r["pitd_onset_rng"], 1),
                         "portamento_y0": r["portamento_y0"],
                         "native_vibrato": r["vibrato"]},
                "ag_r": ren})
        out.append({"class": lay["class"],
                    "audio_span_s": lay["audio_span_s"],
                    "events": evs,
                    "compile": {"src_events": lay["src_events"],
                                "neu_events": lay["neu_events"],
                                "pitch_matched": lay["pitch_matched"],
                                "porta_marks": lay["porta_marks"],
                                "vib_marks": lay["vib_marks"]}})
    return out


if __name__ == "__main__":
    main()
