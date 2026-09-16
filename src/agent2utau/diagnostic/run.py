"""M2.1 GAME diagnostic experiment — transcribe only, no auto-repair.

Variants (plan2 §6):
  A: GAME raw (no language conditioning)
  B: GAME + language=zh
  C: GAME + known word/char boundaries (Whisper attention/DTW -> segmenter
     `known_boundaries` input — the OpenUtau UI path never sets it)
  D: C + RMVPE overlay (evidence only, notes unchanged)

Everything is compared, nothing is corrected. Outputs live in
runs/<id>/diagnostic/ per the plan.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

NEUTRAL_LYRIC = "a"  # valid zh pinyin; diagnostics check melody, not words


def _notes_to_segments(notes: list[dict]) -> list[dict]:
    """Voiced GAME notes -> one build_project segment (absolute seconds)."""
    sung = [n for n in notes if n["voiced"] and n["dur"] > 0.01]
    out = [{"lyric": NEUTRAL_LYRIC, "start": round(n["start"], 4),
            "end": round(n["start"] + n["dur"], 4), "dur": round(n["dur"], 4),
            "tone": int(round(n["tone"])), "conf": "game",
            "game_score": round(n["tone"], 3)} for n in sung]
    return [{"notes": out, "start_sec": out[0]["start"]}] if out else []


def _structural_f0(f0: dict) -> np.ndarray:
    """Median-filtered midi contour suppressing vibrato half-cycles/spikes."""
    from scipy.ndimage import median_filter
    from ..analysis.f0 import hz_to_midi
    midi = np.where(f0["voiced"], hz_to_midi(f0["f0_hz"]), np.nan)
    # fill short unvoiced gaps so the filter doesn't erase real platforms
    filled = midi.copy()
    valid = np.isfinite(midi)
    idx = np.arange(len(midi))
    if valid.sum() > 1:
        filled = np.interp(idx, idx[valid], midi[valid])
    width = max(3, int(round(0.07 / 0.01)) | 1)  # ~70ms at 10ms hop
    sm = median_filter(filled, size=width, mode="nearest")
    sm[~valid] = np.nan
    return sm


def _evidence(note: dict, times: np.ndarray, midi: np.ndarray,
              voiced: np.ndarray) -> dict:
    t0, t1 = note["start"], note["start"] + note["dur"]
    m = (times >= t0) & (times < t1)
    total = int(m.sum())
    cov = float((m & voiced).sum() / max(1, total))
    flags = []
    err = None
    if (m & voiced).sum() >= 3:
        stable = midi[m & voiced]
        stable = stable[np.isfinite(stable)]
        if len(stable):
            err = float((np.median(stable) - note["tone"]) * 100)
            if abs(err) > 100:
                flags.append("wrong_pitch" if abs(err - np.sign(err) * 1200)
                             > 150 else "possible_octave_error")
            if len(stable) > 4 and np.percentile(stable, 75) - \
                    np.percentile(stable, 25) > 60:
                flags.append("high_dispersion")
    else:
        flags.append("weak_f0_evidence")
    if note["dur"] < 0.06:
        flags.append("very_short_isolated_note")
    return {"coverage": round(cov, 3), "err_cents": None if err is None
            else round(err, 1), "flags": flags}


def run_diagnostic(src: str | Path, run, cfg: dict,
                   language: str = "zh", timeout_min: int = 30,
                   progress=None) -> dict[str, Any]:
    from ..audio.decode import decode, probe_duration
    from ..audio.separate import separate
    from ..transcription.game_onnx import GameOnnx, default_model_dir
    from ..analysis.rmvpe import infer_rmvpe
    from ..analysis.lyrics import find_lyrics, force_align
    from ..analysis.align import load_lrc
    from ..openutau.build import build_project
    from ..openutau.bridge import run_bridge
    from ..evaluation.wavcheck import analyze_wav

    log = progress or (lambda m: None)
    diag_dir = run.dir / "diagnostic"
    diag_dir.mkdir(parents=True, exist_ok=True)
    rep: dict[str, Any] = {"schema_version": "1", "run_id": run.id,
                           "source": str(src), "repair": "none (M2.1)"}

    # --- reuse the shared per-source cache for decode/separate -------------
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

    log("game variant B: language=zh")
    vb = game.infer(wav, language=language)
    notes_json(vb, diag_dir / "game_zh.json")

    # char boundaries from bound lyrics (sha256-matched) + whisper DTW
    known_bounds: list[float] = []
    lyric_info = {"status": "unavailable"}
    found = find_lyrics(src)
    if found:
        lrc_path, kind = found
        lrc_lines = load_lrc(str(lrc_path))
        lyric_info = {"status": "aligned", "source": f"{kind}:{lrc_path}",
                      "n_lines": len(lrc_lines)}
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
            (diag_dir / "alignment").mkdir(exist_ok=True)
            (diag_dir / "alignment" / f"line_{i}.json").write_text(
                json.dumps({"text": line["text"], "chars": chars},
                           ensure_ascii=False, indent=1), encoding="utf-8")
    rep["lyrics"] = lyric_info

    if known_bounds:
        log(f"game variant C: +{len(known_bounds)} known boundaries")
        vc = game.infer(wav, language=language,
                        known_boundary_sec=np.array(known_bounds))
    else:
        vc = vb
        rep.setdefault("caveats", []).append(
            "no lyric boundaries available; variant C falls back to B")
    notes_json(vc, diag_dir / "game_word_boundaries.json")

    # --- RMVPE evidence (variant D overlay) ---------------------------------
    log("rmvpe")
    r = infer_rmvpe(vocals)
    np.savez(diag_dir / "rmvpe_f0.npz", f0_hz=r["f0_hz"], voiced=r["voiced"],
             times=r["times"], sr=r["sr"], hop=r["hop"])
    struct = _structural_f0(r)
    np.savez(diag_dir / "structural_f0.npz", structural_midi=struct,
             times=r["times"])
    (diag_dir / "overlay.json").write_text(json.dumps({
        "note": "RMVPE continuous F0 + structural contour overlaid on GAME "
                "variant C notes; evidence only, notes unchanged",
        "frames": len(r["times"])}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # --- suspicious-region pass on variant C (detection only) ---------------
    times, voiced = r["times"], r["voiced"]
    packets, suspicious = [], []
    for i, n in enumerate(vc):
        if not n["voiced"]:
            continue
        ev = _evidence(n, times, struct, voiced)
        rec = {"id": f"note_{i:04d}", "start": round(n["start"], 3),
               "dur": round(n["dur"], 3), "game_tone": round(n["tone"], 2),
               **ev}
        packets.append(rec)
        if ev["flags"]:
            suspicious.append(rec)
    (diag_dir / "suspicious_regions.json").write_text(
        json.dumps(suspicious, ensure_ascii=False, indent=1),
        encoding="utf-8")

    # --- build + render the two main variants for A/B -----------------------
    renders = {}
    for tag, notes in (("game_raw", va), ("game_word_boundaries", vc)):
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

    # --- report -------------------------------------------------------------
    def stats(notes):
        sung = [n for n in notes if n["voiced"]]
        return {"n_notes": len(sung),
                "n_rests": len(notes) - len(sung),
                "dur_sung_s": round(sum(n["dur"] for n in sung), 2)}
    rep["variants"] = {"A_raw": stats(va), "B_zh": stats(vb),
                       "C_boundaries": stats(vc)}
    n_diff = sum(1 for a, b in zip(va, vc)
                 if a["voiced"] != b["voiced"]
                 or abs(a["tone"] - b["tone"]) > 0.5
                 or abs(a["dur"] - b["dur"]) > 0.05)
    rep["A_vs_C_diff_positions"] = n_diff
    flag_counts: dict[str, int] = {}
    for p in suspicious:
        for f in p["flags"]:
            flag_counts[f] = flag_counts.get(f, 0) + 1
    rep["suspicious"] = {"n": len(suspicious), "by_flag": flag_counts,
                         "n_packets": len(packets)}

    md = diag_dir / "diagnostic_report.md"
    md.write_text(_report_md(rep, va, vb, vc, suspicious),
                  encoding="utf-8")
    rep["diagnostic_dir"] = str(diag_dir)
    rep["status"] = "completed_with_warnings"  # always: needs listening review
    run.write_json("report.json", rep)
    run.write_state({"status": rep["status"], "stage": "done",
                     "artifacts": [str(diag_dir)]})
    return rep


def _report_md(rep, va, vb, vc, suspicious) -> str:
    v = rep["variants"]
    lines = ["# GAME diagnostic report — 《年轮》 (M2.1, no auto-repair)",
             "",
             f"source: `{rep['source']}`  ",
             f"run: `{rep['run_id']}`  ",
             "",
             "## Variant note counts", "",
             "| variant | sung notes | rests | sung duration |", "|---|---|---|---|"]
    for k, s in v.items():
        lines.append(f"| {k} | {s['n_notes']} | {s['n_rests']} "
                     f"| {s['dur_sung_s']}s |")
    lines += ["",
              f"A vs C differing note positions: "
              f"**{rep['A_vs_C_diff_positions']}**",
              "",
              "## Suspicious regions (variant C, RMVPE evidence)", "",
              f"total flagged: **{rep['suspicious']['n']}** / "
              f"{rep['suspicious']['n_packets']} voiced notes", ""]
    for f, c in sorted(rep["suspicious"]["by_flag"].items(),
                       key=lambda kv: -kv[1]):
        lines.append(f"- `{f}`: {c}")
    lines += ["", "## Artifacts", "",
              "- `game_raw.json/.ustx/_vocal.wav` — variant A",
              "- `game_zh.json` — variant B (language=zh)",
              "- `game_word_boundaries.json/.ustx/_vocal.wav` — variant C",
              "- `rmvpe_f0.npz`, `structural_f0.npz`, `overlay.json` — D",
              "- `suspicious_regions.json` — evidence packets",
              "- `alignment/line_*.json` — whisper-DTW char boundaries", "",
              "听音顺序建议：game_raw → game_word_boundaries → 与原唱对轨。"]
    return "\n".join(lines) + "\n"
