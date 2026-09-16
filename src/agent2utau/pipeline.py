"""M2 cover pipeline: decode -> separate -> ASR/F0 -> notes -> USTX -> render
-> mix -> evaluate. Each stage writes an artifact so reruns can resume.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from .state import Run


def _stage(run: Run, name: str, fn, **kw) -> Any:
    run.write_state({"status": "running", "stage": name})
    t = time.time()
    out = fn(**kw)
    run.write_json(f"debug/{name}.json", {
        "stage": name, "elapsed_s": round(time.time() - t, 2),
        **({} if out is None else {"result_summary": _summ(out)})})
    return out


def _summ(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: v for k, v in o.items()
                if not isinstance(v, (np.ndarray, list)) or len(v) < 8}
    return str(o)[:200]


def pick_segments(vocals_wav: Path, n: int, seg_len: float,
                  min_gap: float = 8.0) -> list[tuple[float, float]]:
    """Pick the n highest-energy seg_len windows in the vocal stem."""
    wav, sr = sf.read(str(vocals_wav), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    win = int(seg_len * sr)
    hop = int(1.0 * sr)
    cands = []
    for i in range(0, max(1, len(wav) - win), hop):
        e = float(np.sqrt(np.mean(wav[i:i + win] ** 2)))
        cands.append((e, i / sr))
    cands.sort(reverse=True)
    picked: list[tuple[float, float]] = []
    for _e, t in cands:
        if all(abs(t - p[0]) >= seg_len + min_gap for p in picked):
            picked.append((round(t, 2), round(t + seg_len, 2)))
        if len(picked) >= n:
            break
    return sorted(picked)


def parse_segments(spec: str) -> list[tuple[float, float]]:
    out = []
    for tok in spec.split(","):
        a, b = tok.split(":")
        out.append((float(a), float(b)))
    return out


def run_cover(src: str | Path, run: Run, cfg: dict,
              segments: list[tuple[float, float]] | None = None,
              auto_segments: int = 2, seg_len: float = 15.0,
              lyrics: str | Path | None = None,
              lines: str | None = None,
              asr_model: str = "large-v3-turbo",
              sep_model: str = "UVR-MDX-NET-Voc_FT.onnx",
              timeout_min: int = 30,
              iters: int = 2, pitch_strength: float = 1.0,
              voice_color: str | None = "Yousa_Normal",
              compare_colors: bool = False,
              breaths: bool = True,
              progress=None) -> dict[str, Any]:
    from .audio.decode import decode, probe_duration
    from .audio.separate import separate
    from .audio.mix import mix
    from .analysis.lyrics import transcribe, find_lyrics, force_align
    from .analysis.f0 import extract_f0, F0_CACHE_VERSION
    from .analysis.notes import build_notes
    from .analysis.onsets import frame_rms, gate_voiced, voiced_extent
    from .analysis.align import load_lrc, lyric_chars, trim_aligned_chars
    from .openutau.build import build_project, sec_to_tick
    from .openutau.bridge import run_bridge
    from .evaluation.wavcheck import analyze_wav
    from .evaluation.evaluate import evaluate

    log = progress or (lambda m: None)
    audio = run.dir / "audio"
    rep: dict[str, Any] = {"schema_version": "1", "run_id": run.id,
                           "source": str(src)}

    # --- shared per-source cache: decode/separate/f0 are deterministic ---
    import hashlib
    import json
    src_key = hashlib.md5(str(Path(src).resolve()).encode()).hexdigest()[:12]
    cache = Path(cfg["runs_dir"]) / "_cache" / src_key
    cache.mkdir(parents=True, exist_ok=True)
    audio.mkdir(parents=True, exist_ok=True)
    rep["cache_dir"] = str(cache)

    # --- decode ---------------------------------------------------------
    orig = cache / "original.wav"
    if not orig.exists():
        log("decode")
        decode(src, orig, mono=False)
    rep["source_duration_s"] = probe_duration(orig)
    mono = cache / "mono.wav"
    if not mono.exists():
        decode(orig, mono, mono=True)

    # --- separate -------------------------------------------------------
    sep_json = cache / "separation.json"
    if sep_json.exists():
        stems = json.loads(sep_json.read_text(encoding="utf-8"))
    else:
        log("separate")
        stems = _stage(run, "separate", separate, wav_path=orig,
                       out_dir=cache, model=sep_model)
        sep_json.write_text(json.dumps(stems, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    rep["separation"] = {k: v for k, v in stems.items()
                         if k in ("model", "backend", "model_sha256")}
    vocals, instr = Path(stems["vocals"]), Path(stems["instrumental"])

    # --- f0 + energy gate (full song, cached) ----------------------------
    log("f0")
    # Legacy f0.npz inverted the unvoiced mask. Never reuse those arrays.
    f0_full_path = cache / f"f0-{F0_CACHE_VERSION}.npz"
    if f0_full_path.exists():
        f0_np = np.load(f0_full_path)
        f0 = {"f0_hz": f0_np["f0_hz"], "voiced": f0_np["voiced"],
              "times": f0_np["times"], "sr": int(f0_np["sr"]),
              "hop": int(f0_np["hop"]), "backend": str(f0_np["backend"])}
    else:
        f0 = _stage(run, "f0", extract_f0,
                    wav_path=mono_vocals(mono, vocals))
        np.savez(f0_full_path, cache_version=F0_CACHE_VERSION,
                 f0_hz=f0["f0_hz"], voiced=f0["voiced"],
                 times=f0["times"], sr=f0["sr"], hop=f0["hop"],
                 backend=f0["backend"])
    vw, vsr = sf.read(str(vocals), dtype="float32")
    if vw.ndim > 1:
        vw = vw.mean(axis=1)
    rms = frame_rms(vw, vsr, f0["times"])
    f0g = gate_voiced(f0, rms)
    rep["f0_version"] = F0_CACHE_VERSION

    # --- lyric source ----------------------------------------------------
    lrc_lines = None
    if not lyrics:
        found = find_lyrics(src)
        if found:
            lyrics, kind = found
            rep["lyrics_source"] = f"lrc:{kind}:{lyrics}"
            rep.setdefault("caveats", []).append(
                "lyrics auto-discovered (reference file, not ASR)")
    if lyrics:
        lrc_lines = load_lrc(str(lyrics))
        if not lrc_lines:
            raise ValueError("Lyrics need timed LRC entries; no timed lines found")
        rep.setdefault("lyrics_source", f"lrc:{lyrics}")
        if lines:
            lo, hi = (int(x) for x in lines.split(":"))
            lrc_lines = lrc_lines[lo:hi]
        rep["lines_used"] = [l["text"] for l in lrc_lines]
    else:
        rep["lyrics_source"] = f"asr:{asr_model}"

    # --- segments ----------------------------------------------------------
    if lrc_lines:
        # one part per lyric line; position = line start on absolute timeline
        segments = [(l["start"], l["end"]) for l in lrc_lines]
    elif segments is None:
        segments = pick_segments(vocals, auto_segments, seg_len)
    rep["segments"] = [{"start": a, "end": b} for a, b in segments]

    # --- per-segment analysis -------------------------------------------
    all_notes: list[dict] = []
    seg_payloads = []
    log("analysis")
    for i, (t0, t1) in enumerate(segments):
        if lrc_lines:
            text = lrc_lines[i]["text"]
            # No nearest-block relocation: it can put the wrong lyric on a
            # perfectly valid neighbouring phrase. Align text acoustically.
            ext = voiced_extent(f0g, t0, t1, pad=0.05)
            if ext is None:
                seg_payloads.append({"start_sec": t0, "end_sec": t1,
                                     "notes": [], "line": text,
                                     "status": "no_voiced_region"})
                continue
            key = hashlib.sha256(json.dumps(
                ["acoustic-v1", asr_model, text, t0, t1],
                ensure_ascii=False).encode()).hexdigest()[:20]
            aligned_path = cache / f"alignment-{key}.json"
            if aligned_path.exists():
                aligned = json.loads(aligned_path.read_text(encoding="utf-8"))
            else:
                log(f"align line {i + 1}/{len(lrc_lines)}")
                aligned = force_align(vocals, text, t0, t1, model=asr_model)
                aligned_path.write_text(json.dumps(aligned, ensure_ascii=False), encoding="utf-8")
            aligned = trim_aligned_chars(aligned, f0g)
            run.write_json(f"debug/alignment_{i}.json", {"text": text, "chars": aligned})
            bad = [c for c in aligned if c["end"] - c["start"] < 0.04]
            if bad or len(aligned) != len(lyric_chars(text)):
                raise ValueError(f"Collapsed/missing lyric alignment in line {i}: {text}")
            notes, _ = build_notes(aligned, f0g)
            seg_payloads.append({
                "start_sec": aligned[0]["start"], "end_sec": aligned[-1]["end"],
                "notes": notes, "line": text, "lrc_start": t0,
                "n_chars": len(aligned), "alignment": "whisper-attention-dtw",
                "status": "aligned"})
        else:
            asr = _stage(run, f"asr_seg{i}", transcribe, wav_path=vocals,
                         model=asr_model, t0=t0, t1=t1)
            run.write_json(f"asr_seg{i}.json", asr)
            chars = [c for s in asr["segments"] for c in s["chars"]]
            notes, _last = build_notes(chars, f0g)
            seg_payloads.append({
                "start_sec": t0, "end_sec": t1, "notes": notes,
                "asr_text": "".join(s["text"] for s in asr["segments"]),
                "asr_logprob": [s["avg_logprob"] for s in asr["segments"]],
            })
        all_notes += notes
    rep["n_notes"] = len(all_notes)
    rep["n_weak_notes"] = sum(1 for n in all_notes if n["conf"] == "weak")

    # breaths: 'AP' notes in real gaps before phrase starts (must precede
    # curve building — part anchors move earlier where a breath fits)
    if breaths:
        from .analysis.breaths import insert_breaths
        rep["n_breaths"] = insert_breaths(seg_payloads)
        if rep["n_breaths"]:
            rep.setdefault("caveats", []).append(
                "breath notes (AP) auto-inserted at phrase gaps")

    score = {"tempo_source": "fixed", "bpm_fixed": 120.0,
             "segments": seg_payloads}
    run.write_json("score.json", score)

    # --- iterations: baseline render, then measured corrections ----------
    from .analysis.pitchcurve import build_pitd
    it_dir = run.dir / "iterations"
    it_dir.mkdir(exist_ok=True)
    best: dict | None = None
    rep["iterations"] = []

    def render_variant(tag: str, curves_fn=None,
                       color: str | None = None) -> dict | None:
        for s in seg_payloads:
            s["curves"] = curves_fn(s) if curves_fn else []
        ustx_i = it_dir / tag / "cover.ustx"
        build_project(Path(src).stem, seg_payloads, ustx_i,
                      voice_color=color or voice_color)
        out_i = it_dir / tag / "vocal.wav"
        br = run_bridge(cfg, ["render", "--project", str(ustx_i),
                              "--out", str(out_i),
                              "--timeout", str(timeout_min)],
                        timeout=timeout_min * 60 + 120)
        rec = {"tag": tag, "ustx": str(ustx_i)}
        if not br.get("ok"):
            rec["error"] = "render_failed"
            rep["iterations"].append(rec)
            return None
        files = [f["path"] for f in br.get("files", [])]
        vw = next((f for f in files if f.lower().endswith(".wav")),
                  str(out_i))
        rec["vocal"] = vw
        rec["check"] = analyze_wav(vw)
        rec["pitch"] = evaluate(vw, all_notes, f0g).get("pitch", {})
        run.write_json(f"iterations/{tag}/eval.json", rec)
        rep["iterations"].append(
            {"tag": tag, "pitch": rec["pitch"],
             "voiced_fraction": rec["check"]["voiced_fraction"]})
        return rec

    # iter 0: model baseline (no pitch curves — dspitch predicts)
    log("iter0 baseline render")
    best = render_variant("iter0_baseline")
    if best is None:
        run.write_state({"status": "failed", "stage": "render",
                         "failure_code": "render_failed"})
        rep.update(status="failed", failure_code="render_failed")
        return rep

    # iter 1: inject measured source F0 as pitd (mixed-performance path)
    if iters >= 2 and best["pitch"].get("frac_within_100c", 0) < 0.95:
        log("iter1 pitd-inject render")
        def pitd_curves(s):
            if not s["notes"]:
                return []
            c = build_pitd(f0g, s["notes"],
                           s.get("part_start_sec", s["start_sec"]),
                           sec_to_tick, strength=pitch_strength)
            return [c] if c else []
        cand = render_variant("iter1_pitd", pitd_curves)
        if cand and _better(cand["pitch"], best["pitch"]):
            best = cand
    # optional: render every voice color on the first non-empty segment as
    # audition artifacts (user/agent picks by listening, we keep the default)
    if compare_colors:
        colors = ["Yousa_Bright", "Yousa_Classic", "Yousa_Cute",
                  "Yousa_Normal", "Yousa_Whisper"]
        first = next((s for s in seg_payloads if s["notes"]), None)
        rep["color_comparison"] = []
        if first:
            for c in colors:
                log(f"color render {c}")
                mini = {"notes": first["notes"],
                        "start_sec": first["start_sec"],
                        "part_start_sec": first.get(
                            "part_start_sec", first["start_sec"])}
                ustx_c = it_dir / "colors" / f"{c}.ustx"
                build_project(Path(src).stem, [mini], ustx_c,
                              voice_color=c)
                out_c = it_dir / "colors" / f"{c}.wav"
                br = run_bridge(cfg, ["render", "--project", str(ustx_c),
                                      "--out", str(out_c),
                                      "--timeout", str(timeout_min)],
                                timeout=timeout_min * 60 + 120)
                files = [f["path"] for f in br.get("files", [])]
                wav_c = next((f for f in files
                              if f.lower().endswith(".wav")), None)
                rep["color_comparison"].append(
                    {"color": c, "wav": wav_c,
                     "ok": bool(br.get("ok"))})
        rep["voice_color_used"] = voice_color
    rep["chosen"] = best["tag"]
    vocal_wav = best["vocal"]
    ustx = Path(best["ustx"])
    rep["ustx"] = str(ustx)
    rep["vocal_wav"] = vocal_wav
    rep["vocal_check"] = best["check"]
    # copy winning artifacts to canonical names for convenience
    import shutil
    final_ustx = run.dir / "cover.ustx"
    if str(ustx) != str(final_ustx):
        shutil.copy2(ustx, final_ustx)
        rep["ustx"] = str(final_ustx)

    # --- mix ---------------------------------------------------------------
    mix_wav = audio / "mix.wav"
    log("mix")
    rep["mix"] = mix(vocal_wav, instr, mix_wav, reference_vocal=vocals)

    # --- evaluate -----------------------------------------------------------
    log("evaluate")
    rep["mix_check"] = analyze_wav(str(mix_wav))
    rep["pitch_eval"] = evaluate(vocal_wav, all_notes, f0g)
    weak = rep["n_weak_notes"] / max(1, rep["n_notes"])
    pitch = rep["pitch_eval"].get("pitch", {})
    conf = "high"
    if weak > 0.3 or pitch.get("frac_within_100c", 0) < 0.7:
        conf = "medium"
    if weak > 0.6 or pitch.get("frac_within_100c", 0) < 0.4 or pitch.get("coverage", 0) < 0.7:
        conf = "low"
    rep["pitch_confidence"] = conf
    rep["quality_confidence"] = "unverified"
    rep["caveats"] = rep.get("caveats", []) + caveats(rep, seg_payloads)
    rep["alignment_verified_by_listener"] = False
    rep["status"] = "completed_with_warnings"
    run.write_json("report.json", rep)
    run.write_state({"status": rep["status"], "stage": "done",
                     "artifacts": [rep["ustx"], vocal_wav, str(mix_wav)]})
    return rep


def _better(a: dict, b: dict) -> bool:
    """Candidate pitch stats `a` beats incumbent `b` if coverage-adjusted
    accuracy is better."""
    if a.get("n_evaluated", 0) < 5:
        return False
    if a.get("coverage", 0) + 0.02 < b.get("coverage", 0):
        return False
    ka = (a.get("accuracy_all_notes_100c", 0), -a.get("median_abs_cents", 1e9))
    kb = (b.get("accuracy_all_notes_100c", 0), -b.get("median_abs_cents", 1e9))
    return ka > kb


def mono_vocals(mono: Path, vocals: Path) -> Path:
    """F0 source: vocals stem downmixed to mono (created once)."""
    out = vocals.parent / "vocals_mono.wav"
    if not out.exists():
        w, sr = sf.read(str(vocals), dtype="float32")
        if w.ndim > 1:
            w = w.mean(axis=1)
        sf.write(str(out), w, sr, subtype="PCM_16")
    return out


def caveats(rep: dict, seg_payloads: list[dict] | None = None) -> list[str]:
    c = []
    if rep.get("n_weak_notes"):
        c.append(f"{rep['n_weak_notes']}/{rep['n_notes']} notes had weak F0 "
                 "evidence; pitch fell back to context")
    p = rep.get("pitch_eval", {}).get("pitch", {})
    if p.get("frac_within_100c", 1) < 0.7:
        c.append("pitch tracking vs source is loose in places")
    if rep.get("reanchored"):
        c.append(f"{len(rep['reanchored'])} lyric lines were re-anchored to "
                 "nearby audio because the LRC time drifted")
    if seg_payloads:
        unmatched = [s.get("line", "?") for s in seg_payloads
                     if s.get("status") == "no_voiced_region"]
        if unmatched:
            c.append(f"{len(unmatched)} lines had no sung audio nearby and "
                     f"were skipped: {unmatched}")
        weak_seg = sum(1 for s in seg_payloads
                       if s.get("status") == "few_onsets")
        if weak_seg:
            c.append(f"{weak_seg} lines had sparse onsets; char timing there "
                     "is interpolated")
    c.append("tempo axis is fixed 120bpm, not the song's real BPM")
    c.append("DiffSinger model baseline + measured-pitd correction only; "
             "no manual pitch/dyn tuning")
    c.append("automatic acoustic lyric alignment requires listening verification; "
             "pitch scores alone do not certify intelligibility")
    return c
