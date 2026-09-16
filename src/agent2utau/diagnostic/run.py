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


def _comb_score(spec: np.ndarray, freqs: np.ndarray, f_hz: float) -> float:
    s = 0.0
    for k in range(1, 5):
        i = int(np.argmin(np.abs(freqs - f_hz * k)))
        w = max(2, int(0.03 * f_hz * k / (freqs[1] - freqs[0])))
        s += float(spec[max(0, i - w):i + w + 1].max())
    return s


def _separation_octave_check(mix: np.ndarray, m_sr: int,
                             sep: np.ndarray, s_sr: int,
                             t0: float, t1: float,
                             midi_a: float, midi_b: float) -> dict | None:
    """§5.8/5.3: uncertainty FLAG only — does the original-mix spectrum
    prefer a different fundamental than the separated vocal? Mix contains
    accompaniment so this can never pick the true pitch; a disagreement
    only lowers confidence."""
    out = {}
    fa = 440.0 * 2 ** ((midi_a - 69) / 12)
    fb = 440.0 * 2 ** ((midi_b - 69) / 12)
    for tag, w, sr in (("mix", mix, m_sr), ("sep", sep, s_sr)):
        seg = w[int(t0 * sr):int(t1 * sr)]
        if len(seg) < 256:
            return None
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        fr = np.fft.rfftfreq(len(seg), 1 / sr)
        sa, sb = _comb_score(sp, fr, fa), _comb_score(sp, fr, fb)
        out[tag] = "a" if sa >= sb else "b"
        out[tag + "_ratio"] = round(sa / max(1e-9, sb), 3)
    out["separation_sensitive"] = out["mix"] != out["sep"]
    return out


def _boundaries(notes: list[dict]) -> np.ndarray:
    """Note onset times of voiced notes."""
    return np.array([n["start"] for n in notes if n["voiced"]],
                    dtype=np.float64)


def _align_variants(a: list[dict], b: list[dict], **_kw) -> dict:
    """Variant comparison via the formal DP alignment (§5.6) — order-
    preserving, explicit split/merge ops, no onset-greedy index zip."""
    from .seqalign import align_pair
    ops, A, B = align_pair(a, b)
    matched = [op for op in ops if op[0] == "m"]
    pitch_diffs = [A[i]["tone"] - B[j]["tone"] for _, i, j in matched]
    drifts = [B[j]["start"] - A[i]["start"] for _, i, j in matched]
    return {"matched": len(matched),
            "a_only": sum(1 for op in ops if op[0] == "ga"),
            "b_only": sum(1 for op in ops if op[0] == "gb"),
            "splits_merges": sum(1 for op in ops
                                 if op[0] in ("s", "g")),
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

    # --- shared per-source cache (§5.5: content-bound provenance) --------
    import hashlib

    def _sha256(p: Path, limit: int | None = None) -> str:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            n = 0
            while True:
                b = f.read(1 << 20)
                if not b or (limit and n >= limit):
                    break
                h.update(b)
                n += len(b)
        return h.hexdigest()

    src_key = hashlib.md5(str(Path(src).resolve()).encode()).hexdigest()[:12]
    cache = Path(cfg["runs_dir"]) / "_cache" / src_key
    cache.mkdir(parents=True, exist_ok=True)
    src_sha = _sha256(Path(src))
    man_path = cache / "manifest.json"
    CACHE_SCHEMA = "m232a3-1"
    sep_model = "UVR-MDX-NET-Voc_FT.onnx"
    # §5.4 (A3): cache must bind source content, separator model BYTES, and
    # the separator config — not just the model name.
    # audio-separator's default model dir is the literal "/tmp/..." string;
    # resolve it the same way the library does so we hash the real file.
    sep_model_path = Path("/tmp/audio-separator-models") / sep_model
    if not sep_model_path.exists() and man_path.exists():
        prev = json.loads(man_path.read_text(encoding="utf-8")) \
            .get("separator_model_path")
        if prev and Path(prev).exists():
            sep_model_path = Path(prev)
    sep_model_sha = _sha256(sep_model_path) \
        if sep_model_path.exists() else None
    sep_cfg = {"model": sep_model, "output_format": "WAV",
               "backend": "onnxruntime-cpu"}
    sep_cfg_sha = hashlib.sha256(
        json.dumps(sep_cfg, sort_keys=True).encode()).hexdigest()
    man = json.loads(man_path.read_text(encoding="utf-8")) \
        if man_path.exists() else {}
    cache_fresh = (man.get("source_sha256") == src_sha
                   and man.get("separator_model") == sep_model
                   and man.get("separator_model_sha256") == sep_model_sha
                   and man.get("separator_config_sha256") == sep_cfg_sha
                   and man.get("schema") == CACHE_SCHEMA)
    orig = cache / "original.wav"
    sep_json = cache / "separation.json"
    if not orig.exists() or not cache_fresh:
        log("decode" + (" (cache invalidated)" if orig.exists() else ""))
        decode(src, orig, mono=False)
    rep["source_duration_s"] = probe_duration(orig)
    if sep_json.exists() and cache_fresh:
        stems = json.loads(sep_json.read_text(encoding="utf-8"))
    else:
        log("separate")
        stems = separate(wav_path=orig, out_dir=cache, model=sep_model)
        sep_json.write_text(json.dumps(stems, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    man_path.write_text(json.dumps({
        "schema": CACHE_SCHEMA, "source_sha256": src_sha,
        "separator_model": sep_model,
        "separator_model_path": str(sep_model_path),
        "separator_model_sha256": sep_model_sha,
        "separator_config": sep_cfg,
        "separator_config_sha256": sep_cfg_sha},
        ensure_ascii=False, indent=1), encoding="utf-8")
    rep["cache"] = {"key": src_key, "source_sha256": src_sha[:16],
                    "fresh": cache_fresh}
    vocals = Path(stems["vocals"])

    import soundfile as sf
    wav, sep_sr = sf.read(str(vocals), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)

    # --- GAME variants ------------------------------------------------------
    game = GameOnnx(default_model_dir())
    md = default_model_dir()
    rep["game"] = {"models": str(md), "languages": game.languages,
                   "model_sha256": {n: _sha256(md / f"{n}.onnx")[:16]
                                    for n in ("encoder", "segmenter",
                                              "bd2dur", "estimator")}}

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
        # M2.3 step 1: medoid baseline run = Candidate 0 (§5.7: medoid is
        # a representative run, NOT a truth vote — report structure-only
        # medoid as a sensitivity check)
        from .triage import pick_baseline
        bl = pick_baseline(raw_runs)
        bl_struct = pick_baseline(raw_runs, pitch_w=0.0)
        rep["baseline"] = {"run_index": bl["index"],
                           "total_alignment_cost": bl["total_cost"],
                           "per_run_costs": bl["costs"],
                           "structure_only_medoid": bl_struct["index"],
                           "baseline_selection_uncertain":
                           bl["index"] != bl_struct["index"],
                           "n_notes": sum(n["voiced"]
                                          for n in raw_runs[bl["index"]])}
        if bl["index"] != 0:
            va = raw_runs[bl["index"]]
            notes_json(va, diag_dir / "game_raw.json")
            (diag_dir / "baseline_game.json").write_text(
                json.dumps({"run_index": bl["index"], "notes": va},
                           ensure_ascii=False, indent=1), encoding="utf-8")
        else:
            (diag_dir / "baseline_game.json").write_text(
                json.dumps({"run_index": 0, "notes": va},
                           ensure_ascii=False, indent=1), encoding="utf-8")

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
    fcpe_struct = _structural_f0(fcpe)
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

    # --- M2.3 step 3/4: plateau evidence + triage --------------------------
    # M2.3.1: dual-extractor structure evidence + calibrated re-triage
    from .triage import (detect_plateaus, classify, interior_center,
                         dual_structure_evidence, safe_retune_gate,
                         orthogonal_states)
    mix_wav, mix_sr = sf.read(str(orig), dtype="float32")
    if mix_wav.ndim > 1:
        mix_wav = mix_wav.mean(axis=1)
    plateau_ev, dual_struct_ev = {}, {}
    for idx, rec in enumerate(packets):
        plats = detect_plateaus(times, struct, rec["start"],
                                rec["start"] + rec["dur"])
        interior = interior_center(times, struct, rec["start"],
                                   rec["start"] + rec["dur"])
        rec["plateaus"] = plats
        rec["interior_center_midi"] = (None if interior is None
                                     else round(interior, 2))
        rec["triage"] = classify(rec, plats, interior)
        fpl = detect_plateaus(fcpe["times"], fcpe_struct,
                              rec["start"], rec["start"] + rec["dur"])
        if plats:
            plateau_ev[rec["id"]] = plats
        # §5.2 (A3): dual structure evidence whenever GAME structure is
        # unstable — independent of what legacy triage returned
        if (rec.get("consensus") or {}).get("structure_varies"):
            ev2 = dual_structure_evidence(plats, fpl)
            rec["structure_evidence"] = ev2
            dual_struct_ev[rec["id"]] = ev2
        if rec["triage"] == "PITCH_HARD_SUSPICIOUS":
            nb = [p for p in (packets[idx - 1] if idx else None,
                              packets[idx + 1]
                              if idx + 1 < len(packets) else None)
                  if p]
            rec["safe_gate"] = safe_retune_gate(rec, plats, fpl, nb)
        # §5.8: separation sensitivity as an uncertainty flag only
        if rec["triage"] in ("F0_EXTRACTOR_CONFLICT",
                             "PITCH_HARD_SUSPICIOUS",
                             "NEEDS_LISTENING_REVIEW"):
            rmc = (rec.get("rmvpe") or {}).get("center_midi")
            if rmc is not None:
                ss = _separation_octave_check(
                    mix_wav, mix_sr, wav, sep_sr, rec["start"],
                    rec["start"] + rec["dur"], rec["game_tone"], rmc)
                if ss:
                    rec["separation"] = ss
        rec["state"] = orthogonal_states(rec)
    (diag_dir / "plateau_evidence.json").write_text(
        json.dumps(plateau_ev, ensure_ascii=False, indent=1),
        encoding="utf-8")
    (diag_dir / "residual_triage.json").write_text(
        json.dumps(packets, ensure_ascii=False, indent=1),
        encoding="utf-8")
    (diag_dir / "structure_dual_f0_evidence.json").write_text(
        json.dumps(dual_struct_ev, ensure_ascii=False, indent=1),
        encoding="utf-8")
    triage_counts: dict[str, int] = {}
    for rec in packets:
        triage_counts[rec["triage"]] = triage_counts.get(rec["triage"], 0) + 1
    review = [p for p in packets if p["triage"] != "GAME_LIKELY_CORRECT"]
    (diag_dir / "review_regions.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=1),
        encoding="utf-8")
    pitch_safe = [p for p in packets
                  if p.get("safe_gate", {}).get("eligible")]
    (diag_dir / "pitch_safe_candidates.json").write_text(
        json.dumps(pitch_safe, ensure_ascii=False, indent=1),
        encoding="utf-8")
    struct_cands = [p for p in packets
                    if p["triage"] == "STRUCTURE_CANDIDATE"]
    (diag_dir / "structure_candidates.json").write_text(
        json.dumps(struct_cands, ensure_ascii=False, indent=1),
        encoding="utf-8")
    decision_counts: dict[str, int] = {}
    for rec in packets:
        d = rec["state"]["decision"]
        decision_counts[d] = decision_counts.get(d, 0) + 1
    rep["residual_triage_summary"] = {"baseline_notes": len(packets),
                                      **triage_counts,
                                      "decisions": decision_counts,
                                      "safe_retune_candidates":
                                      len(pitch_safe)}
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

    # --- M2.3.1 regression cases + benchmark clips --------------------------
    rc_dir = diag_dir / "regression_cases"
    rc_dir.mkdir(exist_ok=True)
    for p in rep.get("octave_candidates", []):
        (rc_dir / f"{p['start']:.2f}_f0_conflict.json").write_text(
            json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")

    # every extractor-conflict region + every pitch-unstable consensus event
    # gets a regression case (plan §22 output contract)
    for p in packets:
        c = p.get("consensus") or {}
        if p["triage"] == "F0_EXTRACTOR_CONFLICT":
            (rc_dir / f"{p['start']:.2f}_f0_conflict.json").write_text(
                json.dumps(p, ensure_ascii=False, indent=1),
                encoding="utf-8")
        elif c.get("tone_agreement", 1.0) < 1.0:
            (rc_dir / f"{p['start']:.2f}_pitch_unstable.json").write_text(
                json.dumps(p, ensure_ascii=False, indent=1),
                encoding="utf-8")
    raw_wav = (renders.get("game_raw") or {}).get("vocal_wav")

    def _clip(src_wav, out, t0, t1):
        import soundfile as _sf
        w, sr = _sf.read(str(src_wav), dtype="float32")
        i0, i1 = int(t0 * sr), int(t1 * sr)
        _sf.write(str(out), w[max(0, i0):i1], sr)

    benchmark = []
    for p in pitch_safe:
        t0, t1 = p["start"] - 0.6, p["start"] + p["dur"] + 0.6
        tag = f"{p['start']:.2f}"
        (rc_dir / f"{tag}_pitch_candidate.json").write_text(
            json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
        entry = {"note": p["id"], "start": p["start"],
                 "game_tone": p["game_tone"],
                 "target_tone": round(
                     (p.get("rmvpe") or {}).get("center_midi")
                     or p["game_tone"], 2)}
        _clip(vocals, rc_dir / f"{tag}_source_vocal.wav", t0, t1)
        if raw_wav:
            _clip(raw_wav, rc_dir / f"{tag}_baseline_render.wav", t0, t1)
        # retune candidate: ±2 neighbour notes, target note -> extractor tone
        win = [n for n in va if n["voiced"]
               and n["start"] >= t0 - 0.4 and n["start"] <= t1 + 0.4]
        fixed = [dict(n) for n in win]
        for n in fixed:
            if abs(n["start"] - p["start"]) < 0.02:
                n["tone"] = entry["target_tone"]
        if fixed:
            ustx = rc_dir / f"{tag}_retune.ustx"
            build_project(f"bench-{tag}", _notes_to_segments(fixed), ustx,
                          voice_color="Yousa_Normal")
            br = run_bridge(cfg, ["render", "--project", str(ustx),
                                  "--out", str(rc_dir / f"{tag}_retune.wav"),
                                  "--timeout", str(timeout_min)],
                            timeout=timeout_min * 60 + 120)
            entry["retune_render_ok"] = bool(br.get("ok"))
        benchmark.append(entry)
    if benchmark:
        (diag_dir / "benchmark_AB.json").write_text(
            json.dumps(benchmark, ensure_ascii=False, indent=1),
            encoding="utf-8")

    # calibration review set: up to 15 evenly-spaced structure candidates
    if struct_cands:
        step = max(1, len(struct_cands) // 15)
        cal = struct_cands[::step][:15]
        (diag_dir / "calibration_review_set.json").write_text(
            json.dumps(cal, ensure_ascii=False, indent=1),
            encoding="utf-8")
        (diag_dir / "calibration_results.json").write_text(
            json.dumps({"status": "pending_human_review",
                        "n_samples": len(cal)}, ensure_ascii=False,
                       indent=1), encoding="utf-8")

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
    if "residual_triage_summary" in rep:
        lines += ["", "## M2.3 residual-error triage", ""]
        for cls, c in rep["residual_triage_summary"].items():
            if isinstance(c, dict):
                inner = ", ".join(f"{k}={v}" for k, v in
                                  sorted(c.items(), key=lambda kv: -kv[1]))
                lines.append(f"- `{cls}`: {inner}")
            else:
                lines.append(f"- `{cls}`: {c}")
        lines.append("")
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
