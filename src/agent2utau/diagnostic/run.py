"""M2.1.1 GAME diagnostic — corrected per plan2 Part B.

Fixes vs the first pass:
- dispersion/IQR reported in CENTS (not semitones)
- variant comparison uses time-overlap matching, never index zip
- structural F0 only bridges unvoiced gaps <= SHORT_GAP_MS
- GAME `known_boundaries` init follows official d3pm (init=known)
- suspicious/evidence packets run on GAME RAW (variant A) first
- lyric boundaries are matched/snapped as evidence, never forced
- forced-boundary output is experimental-only (`game_forced_boundaries.*`)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

NEUTRAL_LYRIC = "a"  # valid zh pinyin; diagnostics check melody, not words
SHORT_GAP_MS = 40.0          # structural F0 must not bridge longer silence
WRONG_PITCH_CENTS = 100.0
OCTAVE_BAND_CENTS = (1050.0, 1350.0)   # |err| near +-1200
DISPERSION_FLAG_CENTS = 60.0
MATCH_MS = 80.0
SNAP_MS = 300.0


def _notes_to_segments(notes: list[dict]) -> list[dict]:
    sung = [n for n in notes if n["voiced"] and n["dur"] > 0.01]
    out = [{"lyric": NEUTRAL_LYRIC, "start": round(n["start"], 4),
            "end": round(n["start"] + n["dur"], 4), "dur": round(n["dur"], 4),
            "tone": int(round(n["tone"])), "conf": "game",
            "game_score": round(n["tone"], 3)} for n in sung]
    return [{"notes": out, "start_sec": out[0]["start"],
             "part_start_sec": out[0]["start"]}] if out else []


def _structural_f0(f0: dict) -> np.ndarray:
    """Vibrato/spike-suppressed midi contour.

    Fills ONLY unvoiced gaps <= SHORT_GAP_MS (jitter); longer silences stay
    NaN — interpolating across them would fake continuous slides between
    separated notes. Median filter ~70ms keeps real note platforms.
    """
    from scipy.ndimage import median_filter
    from ..analysis.f0 import hz_to_midi
    midi = np.where(f0["voiced"], hz_to_midi(f0["f0_hz"]), np.nan)
    filled = midi.copy()
    idx = np.arange(len(midi))
    frame_s = float(f0["times"][1] - f0["times"][0])
    max_gap = int(round(SHORT_GAP_MS / 1000.0 / frame_s))
    valid = np.isfinite(midi)
    # fill short internal unvoiced runs only
    i = 0
    while i < len(midi):
        if valid[i]:
            i += 1
            continue
        j = i
        while j < len(midi) and not valid[j]:
            j += 1
        if i > 0 and j < len(midi) and (j - i) <= max_gap:
            filled[i:j] = np.linspace(midi[i - 1], midi[j], j - i + 2)[1:-1]
        i = j
    width = max(3, int(round(0.07 / frame_s)) | 1)
    # voiced-island filtering: median-filter each contiguous finite island
    # separately — NaN must NOT be zero-filled first (that would smear
    # silence edges into neighbouring voiced frames).
    sm = np.full_like(filled, np.nan)
    fin = np.isfinite(filled)
    i = 0
    while i < len(filled):
        if not fin[i]:
            i += 1
            continue
        j = i
        while j < len(filled) and fin[j]:
            j += 1
        w = min(width, (j - i) | 1)
        sm[i:j] = median_filter(filled[i:j], size=w, mode="nearest")
        i = j
    return sm


def _track_stats(times: np.ndarray, midi: np.ndarray, voiced: np.ndarray,
                 t0: float, t1: float) -> dict:
    """Per-F0-track stats over [t0,t1): stable center, IQR (cents), coverage.
    `midi` here is a RAW midi contour (NaN where unvoiced), not structural."""
    m = (times >= t0) & (times < t1) & voiced
    sv = midi[m]
    sv = sv[np.isfinite(sv)]
    total = int(((times >= t0) & (times < t1)).sum())
    if len(sv) < 3:
        return {"voiced_coverage": round(float(m.sum()) / max(1, total), 3),
                "center_midi": None, "iqr_cents": None}
    return {"voiced_coverage": round(float(m.sum()) / max(1, total), 3),
            "center_midi": round(float(np.median(sv)), 3),
            "iqr_cents": round(float((np.percentile(sv, 75)
                                      - np.percentile(sv, 25)) * 100), 1)}


def _evidence(note: dict, times: np.ndarray, midi: np.ndarray,
              voiced: np.ndarray, energy: np.ndarray | None,
              fcpe: dict | None = None) -> dict:
    t0, t1 = note["start"], note["start"] + note["dur"]
    m = (times >= t0) & (times < t1)
    total = int(m.sum())
    cov = float((m & voiced).sum() / max(1, total))
    flags: list[str] = []
    err = iqr = None
    sv = midi[m & voiced]
    sv = sv[np.isfinite(sv)]
    if len(sv) >= 3:
        iqr = float((np.percentile(sv, 75) - np.percentile(sv, 25)) * 100)
        err = float((np.median(sv) - note["tone"]) * 100)
        aerr = abs(err)
        if aerr > WRONG_PITCH_CENTS:
            flags.append("possible_octave_error"
                         if OCTAVE_BAND_CENTS[0] <= aerr <= OCTAVE_BAND_CENTS[1]
                         else "wrong_pitch")
        if iqr > DISPERSION_FLAG_CENTS:
            flags.append("high_dispersion")
    else:
        flags.append("weak_f0_evidence")
    if note["dur"] < 0.06:
        flags.append("very_short_isolated_note")
    out = {"voiced_coverage": round(cov, 3),
           "f0_iqr_cents": None if iqr is None else round(iqr, 1),
           "err_cents": None if err is None else round(err, 1),
           "flags": flags}
    if fcpe is not None:
        # dual-F0 evidence (M2.2B): independent center/IQR per extractor
        rmv = _track_stats(times, midi, voiced, t0, t1)
        out["rmvpe"] = rmv
        ft = fcpe["times"]
        fmidi = np.where(fcpe["voiced"],
                         np.log2(np.maximum(fcpe["f0_hz"], 1e-6) / 440.0)
                         * 12 + 69, np.nan)
        fcp = _track_stats(ft, fmidi, fcpe["voiced"], t0, t1)
        out["fcpe"] = fcp
        if rmv["center_midi"] is not None and fcp["center_midi"] is not None:
            d = (fcp["center_midi"] - rmv["center_midi"]) * 100
            out["dual_f0"] = {
                "rmvpe_vs_fcpe_cents": round(d, 1),
                "game_vs_rmvpe_cents": out["err_cents"],
                "game_vs_fcpe_cents": round(
                    (fcp["center_midi"] - note["tone"]) * 100, 1),
                # both extractors agree with each other within 50c
                "extractors_agree": abs(d) <= 50.0,
                # both extractors jointly disagree with GAME by >100c
                "both_oppose_game": bool(
                    out["err_cents"] is not None
                    and abs(out["err_cents"]) > WRONG_PITCH_CENTS
                    and abs((fcp["center_midi"] - note["tone"]) * 100)
                    > WRONG_PITCH_CENTS
                    and abs(d) <= 50.0),
            }
    return out


def _boundaries(notes: list[dict]) -> np.ndarray:
    """Note onset times of voiced notes."""
    return np.array([n["start"] for n in notes if n["voiced"]],
                    dtype=np.float64)


def _align_variants(a: list[dict], b: list[dict],
                    tol_s: float = 0.15) -> dict:
    """Greedy onset-time matching between two note sequences."""
    sa = [(n["start"], n) for n in a if n["voiced"]]
    sb = [(n["start"], n) for n in b if n["voiced"]]
    used_b: set[int] = set()
    matched, pitch_diffs, drifts = [], [], []
    for t, na in sa:
        j = min((k for k in range(len(sb)) if k not in used_b),
                key=lambda k: abs(sb[k][0] - t), default=None)
        if j is not None and abs(sb[j][0] - t) <= tol_s:
            used_b.add(j)
            matched.append((t, sb[j][0]))
            pitch_diffs.append(round(na["tone"] - sb[j][1]["tone"], 2))
            drifts.append(round(sb[j][0] - t, 3))
    return {"matched": len(matched),
            "a_only": len(sa) - len(matched),
            "b_only": len(sb) - len(used_b),
            "pitch_disagree_gt1st": int(sum(abs(d) > 1
                                          for d in pitch_diffs)),
            "median_onset_drift_ms": round(float(np.median(drifts)) * 1000, 1)
            if drifts else None}


def _lyric_boundary_match(boundary_secs: list[float], notes: list[dict],
                          times, struct, voiced, energy) -> list[dict]:
    gb = _boundaries(notes)
    out = []
    for bs in boundary_secs:
        if gb.size == 0:
            break
        d_ms = float(np.min(np.abs(gb - bs)) * 1000)
        rec = {"lyric_boundary_s": round(bs, 3),
               "nearest_game_boundary_ms": round(d_ms, 1)}
        if d_ms <= MATCH_MS:
            rec["class"] = "matched"
        elif d_ms <= SNAP_MS:
            rec["class"] = "possible_snap"
        else:
            # >300ms from any GAME boundary: check F0 support
            m = (times >= bs - 0.15) & (times <= bs + 0.15) & voiced
            sv = struct[m]
            sv = sv[np.isfinite(sv)]
            change = (float(np.median(sv[int(len(sv) / 2):])
                            - np.median(sv[:int(len(sv) / 2)]))
                      if len(sv) >= 6 else None)
            rec["structural_change_st"] = (None if change is None
                                           else round(change, 2))
            rec["class"] = ("possible_missing_boundary"
                            if change is not None and abs(change) >= 1.0
                            else "unsupported_lyric_boundary")
        out.append(rec)
    return out


def run_diagnostic(src: str | Path, run, cfg: dict,
                   language: str = "zh", timeout_min: int = 30,
                   repeats: int = 1,
                   progress=None) -> dict[str, Any]:
    from ..audio.decode import decode, probe_duration
    from ..audio.separate import separate
    from ..transcription.game_onnx import GameOnnx, default_model_dir
    from ..analysis.rmvpe import infer_rmvpe
    from ..analysis.lyrics import find_lyrics, force_align
    from ..analysis.onsets import frame_rms
    from ..analysis.align import load_lrc
    from ..openutau.build import build_project
    from ..openutau.bridge import run_bridge
    from ..evaluation.wavcheck import analyze_wav

    log = progress or (lambda m: None)
    diag_dir = run.dir / "diagnostic"
    diag_dir.mkdir(parents=True, exist_ok=True)
    rep: dict[str, Any] = {"schema_version": "1", "run_id": run.id,
                           "source": str(src),
                           "repair": "none (M2.1.1 diagnostic)"}

    # --- shared per-source cache -------------------------------------------
    import hashlib
    src_key = hashlib.md5(str(Path(src).resolve()).encode()).hexdigest()[:12]
    cache = Path(cfg["runs_dir"]) / "_cache" / src_key
    cache.mkdir(parents=True, exist_ok=True)
    orig = cache / "original.wav"
    if not orig.exists():
        log("decode")
        decode(src, orig, mono=False)
    rep["source_duration_s"] = probe_duration(orig)
    sep_json = cache / "separation.json"
    if sep_json.exists():
        stems = json.loads(sep_json.read_text(encoding="utf-8"))
    else:
        log("separate")
        stems = separate(wav_path=orig, out_dir=cache,
                         model="UVR-MDX-NET-Voc_FT.onnx")
        sep_json.write_text(json.dumps(stems, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    vocals = Path(stems["vocals"])

    import soundfile as sf
    wav, sr = sf.read(str(vocals), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)

    # --- GAME variants ------------------------------------------------------
    game = GameOnnx(default_model_dir())
    rep["game"] = {"models": str(default_model_dir()),
                   "languages": game.languages}

    def notes_json(notes, path):
        path.write_text(json.dumps(notes, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    log("game variant A: raw")
    va = game.infer(wav)
    notes_json(va, diag_dir / "game_raw.json")
    raw_runs = [va]
    for i in range(1, repeats):
        log(f"game raw repeat {i + 1}/{repeats}")
        n = game.infer(wav)
        notes_json(n, diag_dir / f"game_raw_r{i + 1}.json")
        raw_runs.append(n)

    log("game variant B: language=zh")
    vb = game.infer(wav, language=language)
    notes_json(vb, diag_dir / "game_zh.json")
    zh_runs = [vb]
    for i in range(1, repeats):
        log(f"game zh repeat {i + 1}/{repeats}")
        n = game.infer(wav, language=language)
        notes_json(n, diag_dir / f"game_zh_r{i + 1}.json")
        zh_runs.append(n)

    # lyric boundaries: sha256-bound lrc + whisper DTW (evidence only)
    known_bounds: list[float] = []
    lyric_info = {"status": "unavailable"}
    found = find_lyrics(src)
    if found:
        lrc_path, kind = found
        lrc_lines = load_lrc(str(lrc_path))
        lyric_info = {"status": "aligned", "source": f"{kind}:{lrc_path}",
                      "n_lines": len(lrc_lines)}
        (diag_dir / "alignment").mkdir(exist_ok=True)
        for i, line in enumerate(lrc_lines):
            if not line["text"].strip():
                continue
            t1 = min(line["end"], line["start"] + 29.0)
            try:
                chars = force_align(vocals, line["text"],
                                    line["start"], t1)
            except Exception as e:
                lyric_info.setdefault("align_errors", []).append(
                    {"line": i, "error": str(e)[:200]})
                continue
            known_bounds += [c["start"] for c in chars]
            (diag_dir / "alignment" / f"line_{i}.json").write_text(
                json.dumps({"text": line["text"], "chars": chars},
                           ensure_ascii=False, indent=1), encoding="utf-8")
    rep["lyrics"] = lyric_info

    # Variant C: forced boundaries — EXPERIMENTAL ONLY, not a candidate
    if known_bounds:
        log(f"game variant C (experimental): +{len(known_bounds)} boundaries")
        vc = game.infer(wav, language=language,
                        known_boundary_sec=np.array(known_bounds))
        notes_json(vc, diag_dir / "game_forced_boundaries.json")
    else:
        vc = None

    # --- M2.1.2 GAME stochastic consensus -----------------------------------
    from .consensus import (build_consensus, consensus_stats,
                            event_as_note)
    consensus_raw = consensus_zh = None
    if repeats > 1:
        log(f"consensus over {repeats} raw runs")
        consensus_raw = build_consensus(raw_runs)
        (diag_dir / "consensus_raw.json").write_text(
            json.dumps(consensus_raw, ensure_ascii=False, indent=1),
            encoding="utf-8")
        log(f"consensus over {repeats} zh runs")
        consensus_zh = build_consensus(zh_runs)
        (diag_dir / "consensus_zh.json").write_text(
            json.dumps(consensus_zh, ensure_ascii=False, indent=1),
            encoding="utf-8")
        rep["stochastic"] = {
            "n_runs": repeats,
            "raw_note_counts": [sum(n["voiced"] for n in r)
                                for r in raw_runs],
            "zh_note_counts": [sum(n["voiced"] for n in r)
                               for r in zh_runs],
            "consensus_raw": consensus_stats(consensus_raw),
            "consensus_zh": consensus_stats(consensus_zh),
        }

    def _attach_consensus(rec: dict) -> None:
        """Attach the consensus event with max temporal overlap with this
        note (start-distance matching fails when split members merge into
        one event whose median start shifts)."""
        if consensus_raw is None:
            return
        t0, t1 = rec["start"], rec["start"] + rec["dur"]
        best, best_ov = None, 0.02  # min 20ms overlap
        for e in consensus_raw:
            e0 = e["start_median"]
            e1 = e0 + e["duration_median"]
            ov = min(t1, e1) - max(t0, e0)
            if ov > best_ov:
                best, best_ov = e, ov
        if best is not None:
            rec["consensus"] = {k: best[k] for k in
                                ("presence_rate", "tone_agreement",
                                 "tone_median", "start_iqr_ms",
                                 "run_note_counts", "structure_varies",
                                 "stability")}

    # --- RMVPE + structural F0 (variant D evidence) --------------------------
    log("rmvpe")
    r = infer_rmvpe(vocals)
    np.savez(diag_dir / "rmvpe_f0.npz", f0_hz=r["f0_hz"], voiced=r["voiced"],
             times=r["times"], sr=r["sr"], hop=r["hop"])
    struct = _structural_f0(r)
    np.savez(diag_dir / "structural_f0.npz", structural_midi=struct,
             times=r["times"])
    log("fcpe (dual-F0 evidence)")
    from ..analysis.f0 import extract_f0
    fcpe = extract_f0(vocals)
    np.savez(diag_dir / "fcpe_f0.npz", f0_hz=fcpe["f0_hz"],
             voiced=fcpe["voiced"], times=fcpe["times"])
    vw2, vsr = sf.read(str(vocals), dtype="float32")
    if vw2.ndim > 1:
        vw2 = vw2.mean(axis=1)
    energy = frame_rms(vw2, vsr, r["times"])

    # --- validator on GAME RAW (primary), evidence only ---------------------
    times, voiced = r["times"], r["voiced"]
    packets, suspicious = [], []
    for i, n in enumerate(va):
        if not n["voiced"]:
            continue
        ev = _evidence(n, times, struct, voiced, energy, fcpe=fcpe)
        rec = {"id": f"note_{i:04d}", "start": round(n["start"], 3),
               "dur": round(n["dur"], 3), "game_tone": round(n["tone"], 2),
               **ev}
        _attach_consensus(rec)
        packets.append(rec)
        if ev["flags"]:
            suspicious.append(rec)
    (diag_dir / "raw_evidence_packets.json").write_text(
        json.dumps(packets, ensure_ascii=False, indent=1), encoding="utf-8")
    (diag_dir / "raw_suspicious_regions.json").write_text(
        json.dumps(suspicious, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # --- variant comparison: time-aligned, no index zip ----------------------
    variant_alignment = {"A_vs_B": _align_variants(va, vb)}
    if vc is not None:
        variant_alignment["A_vs_C_forced"] = _align_variants(va, vc)
    if consensus_raw is not None and consensus_zh is not None:
        variant_alignment["consensusA_vs_consensusB"] = _align_variants(
            [event_as_note(e) for e in consensus_raw],
            [event_as_note(e) for e in consensus_zh])
    (diag_dir / "variant_alignment.json").write_text(
        json.dumps(variant_alignment, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # --- variant E: lyric-boundary overlay (matching only) ------------------
    lyric_matches = []
    if known_bounds:
        lyric_matches = _lyric_boundary_match(known_bounds, va, times,
                                              struct, voiced, energy)
    (diag_dir / "lyric_boundary_matches.json").write_text(
        json.dumps(lyric_matches, ensure_ascii=False, indent=1),
        encoding="utf-8")
    lm_counts: dict[str, int] = {}
    for m in lyric_matches:
        lm_counts[m["class"]] = lm_counts.get(m["class"], 0) + 1

    # --- build + render primary variants for A/B -----------------------------
    renders = {}
    for tag, notes in (("game_raw", va),
                       ("game_forced_boundaries", vc)):
        if not notes:
            continue
        segs = _notes_to_segments(notes)
        if not segs:
            continue
        ustx = diag_dir / f"{tag}.ustx"
        build_project(f"diag-{tag}", segs, ustx, voice_color="Yousa_Normal")
        out_wav = diag_dir / f"{tag}_vocal.wav"
        br = run_bridge(cfg, ["render", "--project", str(ustx),
                              "--out", str(out_wav),
                              "--timeout", str(timeout_min)],
                        timeout=timeout_min * 60 + 120)
        renders[tag] = {"ustx": str(ustx), "ok": bool(br.get("ok"))}
        if br.get("ok"):
            files = [f["path"] for f in br.get("files", [])]
            wav_f = next((f for f in files if f.lower().endswith(".wav")),
                         None)
            renders[tag]["vocal_wav"] = wav_f
            if wav_f:
                renders[tag]["check"] = analyze_wav(wav_f)
    rep["renders"] = renders

    # --- report ---------------------------------------------------------------
    def stats(notes):
        sung = [n for n in notes if n["voiced"]]
        return {"n_notes": len(sung), "n_rests": len(notes) - len(sung),
                "dur_sung_s": round(sum(n["dur"] for n in sung), 2)}
    rep["variants"] = {"A_raw": stats(va), "B_zh": stats(vb)}
    if vc is not None:
        rep["variants"]["C_forced_boundaries"] = stats(vc)
    flag_counts: dict[str, int] = {}
    for p in suspicious:
        for f in p["flags"]:
            flag_counts[f] = flag_counts.get(f, 0) + 1
    rep["raw_suspicious"] = {"n": len(suspicious), "by_flag": flag_counts,
                             "n_packets": len(packets)}
    rep["lyric_boundary_match_counts"] = lm_counts
    rep["variant_alignment"] = variant_alignment
    rep["octave_candidates"] = [p for p in packets
                              if "possible_octave_error" in p["flags"]]
    # M2.2B benchmark packets — one file per octave candidate (plan2 §13)
    for p in rep["octave_candidates"]:
        bm = {"region": [round(p["start"] - 0.15, 3),
                         round(p["start"] + p["dur"] + 0.15, 3)],
              "game": p.get("consensus") or {"tone": p["game_tone"]},
              "rmvpe": p.get("rmvpe"), "fcpe": p.get("fcpe"),
              "dual_f0": p.get("dual_f0"),
              "aligned_structure": (p.get("consensus") or {}).get(
                  "run_note_counts"),
              "decision": "pending"}
        (diag_dir / f"benchmark_octave_{p['start']:.2f}s.json").write_text(
            json.dumps(bm, ensure_ascii=False, indent=1),
            encoding="utf-8")

    (diag_dir / "diagnostic_report.md").write_text(
        _report_md(rep), encoding="utf-8")
    rep["diagnostic_dir"] = str(diag_dir)
    rep["status"] = "completed_with_warnings"  # always: needs listening review
    run.write_json("report.json", rep)
    run.write_state({"status": rep["status"], "stage": "done",
                     "artifacts": [str(diag_dir)]})
    return rep


def _report_md(rep) -> str:
    v = rep["variants"]
    lines = ["# GAME diagnostic report — 《年轮》 (M2.1.1 corrected)",
             "",
             f"source: `{rep['source']}`  ",
             f"run: `{rep['run_id']}`  ",
             "",
             "## Variant note counts", "",
             "| variant | sung notes | rests | sung duration |", "|---|---|---|---|"]
    for k, s in v.items():
        lines.append(f"| {k} | {s['n_notes']} | {s['n_rests']} "
                     f"| {s['dur_sung_s']}s |")
    lines += ["", "## Variant alignment (onset-time matching, no index zip)",
              ""]
    for k, a in rep["variant_alignment"].items():
        lines.append(
            f"- {k}: matched={a['matched']}, a_only={a['a_only']}, "
            f"b_only={a['b_only']}, pitch_disagree>1st="
            f"{a['pitch_disagree_gt1st']}, median_onset_drift="
            f"{a['median_onset_drift_ms']}ms")
    if "stochastic" in rep:
        s = rep["stochastic"]
        lines += ["", "## M2.1.2 GAME stochastic consensus", "",
                  f"runs: {s['n_runs']} per config", "",
                  f"- raw note counts: {s['raw_note_counts']}",
                  f"- zh note counts: {s['zh_note_counts']}",
                  f"- consensus raw: {s['consensus_raw']}",
                  f"- consensus zh: {s['consensus_zh']}", ""]
    lines += ["",
              "## GAME-raw suspicious regions (RMVPE structural evidence)",
              "",
              f"flagged: **{rep['raw_suspicious']['n']}** / "
              f"{rep['raw_suspicious']['n_packets']} voiced notes", ""]
    for f, c in sorted(rep["raw_suspicious"]["by_flag"].items(),
                       key=lambda kv: -kv[1]):
        lines.append(f"- `{f}`: {c}")
    lines += ["", "## Lyric-boundary matching (overlay, never forced)", ""]
    for cls, c in sorted(rep["lyric_boundary_match_counts"].items(),
                         key=lambda kv: -kv[1]):
        lines.append(f"- `{cls}`: {c}")
    lines += ["", "## Artifacts", "",
              "- `game_raw.*` — variant A baseline (ustx + vocal render)",
              "- `game_zh.json` — variant B (language=zh)",
              "- `game_forced_boundaries.*` — EXPERIMENTAL variant C",
              "- `rmvpe_f0.npz`, `structural_f0.npz` — evidence layer",
              "- `raw_evidence_packets.json`, `raw_suspicious_regions.json`",
              "- `lyric_boundary_matches.json`, `variant_alignment.json`",
              "- `alignment/line_*.json` — whisper-DTW char boundaries", "",
              "听音顺序建议：game_raw → 与原唱对轨；forced-boundary 仅实验对照。"]
    return "\n".join(lines) + "\n"
