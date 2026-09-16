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
              progress=None) -> dict[str, Any]:
    from .audio.decode import decode, probe_duration
    from .audio.separate import separate
    from .audio.mix import mix
    from .analysis.lyrics import transcribe
    from .analysis.f0 import extract_f0
    from .analysis.notes import build_notes
    from .analysis.onsets import (frame_rms, gate_voiced, voiced_extent,
                                  voiced_blocks, detect_onsets)
    from .analysis.align import load_lrc, lyric_chars, distribute
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
    f0_full_path = cache / "f0.npz"
    if f0_full_path.exists():
        f0_np = np.load(f0_full_path)
        f0 = {"f0_hz": f0_np["f0_hz"], "voiced": f0_np["voiced"],
              "times": f0_np["times"], "sr": int(f0_np["sr"]),
              "hop": int(f0_np["hop"]), "backend": str(f0_np["backend"])}
    else:
        f0 = _stage(run, "f0", extract_f0,
                    wav_path=mono_vocals(mono, vocals))
        np.savez(f0_full_path, f0_hz=f0["f0_hz"], voiced=f0["voiced"],
                 times=f0["times"], sr=f0["sr"], hop=f0["hop"],
                 backend=f0["backend"])
    vw, vsr = sf.read(str(vocals), dtype="float32")
    if vw.ndim > 1:
        vw = vw.mean(axis=1)
    rms = frame_rms(vw, vsr, f0["times"])
    f0g = gate_voiced(f0, rms)
    all_blocks = voiced_blocks(f0g)

    # --- lyric source ----------------------------------------------------
    lrc_lines = None
    if lyrics:
        lrc_lines = load_lrc(str(lyrics))
        rep["lyrics_source"] = f"lrc:{lyrics}"
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
    used_blocks: set[int] = set()
    log("analysis")
    for i, (t0, t1) in enumerate(segments):
        if lrc_lines:
            text = lrc_lines[i]["text"]
            ext = voiced_extent(f0g, t0, t1)
            # Re-anchor: LRC time can drift from the actual audio (live
            # arrangements differ). If the window has no/poor voiced
            # coverage, snap to the nearest voiced block within 4s.
            span = t1 - t0
            poor = ext is None or (ext[1] - ext[0]) < 0.4 * span
            if poor:
                cand = [(bi, b) for bi, b in enumerate(all_blocks)
                        if bi not in used_blocks
                        and b[1] > t0 - 4.0 and b[0] < t1 + 4.0]
                if cand:
                    bi, best = max(cand, key=lambda ib: (
                        min(ib[1][1], t1) - max(ib[1][0], t0),
                        -abs(ib[1][0] - t0)))
                    used_blocks.add(bi)
                    ext = best
                    rep.setdefault("reanchored", []).append(
                        {"line": text, "lrc": [t0, t1],
                         "audio": [round(ext[0], 2), round(ext[1], 2)]})
            else:
                # good natural extent: claim overlapping blocks so a later
                # drifting line can't re-anchor onto them
                for bi, b in enumerate(all_blocks):
                    if b[1] > ext[0] and b[0] < ext[1]:
                        used_blocks.add(bi)
            if ext is None:
                seg_payloads.append({"start_sec": t0, "end_sec": t1,
                                     "notes": [], "line": text,
                                     "status": "no_voiced_region"})
                continue
            ons = detect_onsets(vocals, ext[0], ext[1])
            chars = lyric_chars(text)
            aligned = distribute(chars, ons, ext[0], ext[1])
            notes, _ = build_notes(aligned, f0g)
            seg_payloads.append({
                "start_sec": ext[0], "end_sec": ext[1], "notes": notes,
                "line": text, "lrc_start": t0, "n_onsets": len(ons),
                "n_chars": len(chars),
                "status": "ok" if len(ons) >= len(chars) * 0.7
                else "few_onsets"})
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
    score = {"tempo_source": "fixed", "bpm_fixed": 120.0,
             "segments": seg_payloads}
    run.write_json("score.json", score)

    # --- build USTX ------------------------------------------------------
    ustx = run.dir / "cover.ustx"
    log("build ustx")
    build_project(Path(src).stem, seg_payloads, ustx)
    rep["ustx"] = str(ustx)

    # --- render -----------------------------------------------------------
    vocal_out = audio / "vocal_render.wav"
    log("render")
    br = run_bridge(cfg, ["render", "--project", str(ustx),
                          "--out", str(vocal_out),
                          "--timeout", str(timeout_min)],
                    timeout=timeout_min * 60 + 120)
    rep["bridge"] = {k: v for k, v in br.items() if k != "files"}
    if not br.get("ok"):
        run.write_state({"status": "failed", "stage": "render",
                         "failure_code": "render_failed"})
        rep.update(status="failed", failure_code="render_failed")
        return rep
    files = [f["path"] for f in br.get("files", [])]
    vocal_wav = next((f for f in files if f.lower().endswith(".wav")),
                     str(vocal_out))
    rep["vocal_wav"] = vocal_wav
    rep["vocal_check"] = analyze_wav(vocal_wav)

    # --- mix ---------------------------------------------------------------
    mix_wav = audio / "mix.wav"
    log("mix")
    rep["mix"] = mix(vocal_wav, instr, mix_wav, vocal_gain_db=0.0)

    # --- evaluate -----------------------------------------------------------
    log("evaluate")
    rep["mix_check"] = analyze_wav(str(mix_wav))
    rep["pitch_eval"] = evaluate(vocal_wav, all_notes, f0)
    weak = rep["n_weak_notes"] / max(1, rep["n_notes"])
    pitch = rep["pitch_eval"].get("pitch", {})
    conf = "high"
    if weak > 0.3 or pitch.get("frac_within_100c", 0) < 0.7:
        conf = "medium"
    if weak > 0.6 or pitch.get("frac_within_100c", 0) < 0.4:
        conf = "low"
    rep["quality_confidence"] = conf
    rep["caveats"] = caveats(rep, seg_payloads)
    rep["status"] = "completed"
    run.write_json("report.json", rep)
    run.write_state({"status": "completed", "stage": "done",
                     "artifacts": [rep["ustx"], vocal_wav, str(mix_wav)]})
    return rep


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
    c.append("DiffSinger model baseline only; no manual pitch/dyn tuning")
    c.append("no AP/breath notes inserted")
    c.append("source is a duet; all lines are rendered by the single target "
             "singer")
    return c
