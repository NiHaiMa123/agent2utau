"""L7 Round J Phase J6 — Huahai full-corpus ingestion (ingestion only).

Commits the complete human-project / GAME / SOURCE raw-F0 corpus to
runs/huahai_corpus/ so the reviewer can analyze raw evidence directly.

Scope (plan J6.1-J6.8):
- inventory ALL discovered human-authored 花海 projects (bytes kept
  immutable; other songs' projects are listed but not committed)
- per project: metadata + written-control dump + standardized render
  (1.65c/dpV2) -> full-song FCPE + RMVPE npz
- GAME note-level pitch representation for the song (no pre-existing
  artifact was found; generated once with the pinned existing
  implementation and a fixed seed, labelled generated_for_corpus)
- Jay SOURCE full-song FCPE + RMVPE on BOTH vocal separations
- manifest.json binding every artifact by sha256 + axis metadata

No analysis/aggregation beyond index-level fields; no cherry-picking.
Requires a clean git worktree.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import l7_phrase_gate as drv                          # noqa: E402
import l7j_huahai_benchmark as hb                     # noqa: E402
from agent2utau.analysis.f0 import extract_f0         # noqa: E402
from agent2utau.analysis.rmvpe import infer_rmvpe     # noqa: E402
from agent2utau.openutau.ustx import (                # noqa: E402
    load_ustx, sha256)
from agent2utau.resources.config import load_config   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "runs" / "huahai_corpus"
PROJECT_DIRS = [Path(r"E:\data\project_opentuau")]
JAY_FLAC = hb.JAY_FLAC
KIM2_VOCALS = hb.KIM2_VOCALS
UVR_VOCALS = hb.VOCALS
RENDER_SINGER = "YousaV1.65c"


def _npz(path, **kw):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **kw)


def _f0_npz(path, f0d, *, extractor, audio, axis, wave_off,
            project_sha=None, render_env=None):
    _npz(path,
         times=np.asarray(f0d["times"], dtype=np.float64),
         f0_hz=np.asarray(f0d["f0_hz"], dtype=np.float32),
         voiced=np.asarray(f0d["voiced"], dtype=bool))
    meta = {
        "extractor": extractor,
        "hop_ms": 10.0,
        "audio_sha256": sha256(audio) if Path(audio).exists() else None,
        "audio": str(audio),
        "audio_axis": axis,
        "wave_offset_s": wave_off,
        "project_sha256": project_sha,
        "render_environment": render_env,
        "n_frames": int(len(f0d["times"])),
        "t0_s": float(f0d["times"][0]) if len(f0d["times"]) else None,
        "t1_s": float(f0d["times"][-1]) if len(f0d["times"]) else None,
        "voiced_frac": float(np.mean(f0d["voiced"]))
        if len(f0d["voiced"]) else None,
    }
    Path(str(path) + ".meta.json").write_text(
        json.dumps(meta, indent=1, ensure_ascii=False),
        encoding="utf-8")
    return meta


def _written_npz(path, part):
    """Raw written pitch controls for one voice part (lossless)."""
    notes = part.get("notes", [])
    pitd = next((c for c in part.get("curves", [])
                 if c.get("abbr") == "pitd"), None)
    kw = dict(
        note_position=np.array([n.get("position") for n in notes],
                               dtype=np.int64),
        note_duration=np.array([n.get("duration") for n in notes],
                               dtype=np.int64),
        note_tone=np.array([n.get("tone") for n in notes],
                           dtype=np.int16),
        note_lyric=np.array([str(n.get("lyric")) for n in notes]),
        pitd_xs=np.array(pitd["xs"] if pitd else [], dtype=np.int64),
        pitd_ys=np.array(pitd["ys"] if pitd else [], dtype=np.int16),
        vibrato_length=np.array(
            [(n.get("vibrato") or {}).get("length", 0) for n in notes],
            dtype=np.float32),
        vibrato_period=np.array(
            [(n.get("vibrato") or {}).get("period", 0) for n in notes],
            dtype=np.float32),
        vibrato_depth=np.array(
            [(n.get("vibrato") or {}).get("depth", 0) for n in notes],
            dtype=np.float32),
        vibrato_in=np.array(
            [(n.get("vibrato") or {}).get("in", 0) for n in notes],
            dtype=np.float32),
        vibrato_out=np.array(
            [(n.get("vibrato") or {}).get("out", 0) for n in notes],
            dtype=np.float32),
        vibrato_shift=np.array(
            [(n.get("vibrato") or {}).get("shift", 0) for n in notes],
            dtype=np.float32),
        vibrato_drift=np.array(
            [(n.get("vibrato") or {}).get("drift", 0) for n in notes],
            dtype=np.float32),
        pitch_y0=np.array(
            [((n.get("pitch") or {}).get("data") or [{}])[0].get("y", 0)
             for n in notes], dtype=np.int16),
    )
    _npz(path, **kw)


def _project_meta(doc, path):
    t2s = hb.tempo_map(doc)
    tempos = doc.get("tempos", [])
    bpm0 = (tempos[0].get("bpm") if tempos else 120) or 120
    ms_tick = 60000.0 / (bpm0 * 480.0)
    parts = []
    for i, p in enumerate(doc.get("voice_parts", [])):
        lyr = [str(n.get("lyric")) for n in p.get("notes", [])]
        parts.append({
            "index": i, "name": p.get("name"),
            "position_tick": p.get("position"),
            "track_no": p.get("track_no"),
            "n_notes": len(p.get("notes", [])),
            "lyric_sequence": lyr})
    wparts = []
    for i, p in enumerate(doc.get("wave_parts", [])):
        rel = p.get("relative_path")
        cand = Path(path).parent / rel if rel else None
        wparts.append({
            "index": i, "name": p.get("name"),
            "relative_path": rel,
            "position_tick": p.get("position"),
            "position_s": (round(t2s(p.get("position") or 0), 3)
                           if p.get("position") is not None else None),
            "track_no": p.get("track_no"),
            "file_available": bool(cand and cand.exists())})
    return {
        "tempo_bpm": (tempos[0].get("bpm") if tempos else None),
        "tempos": tempos,
        "resolution_ticks_per_quarter":
            doc.get("resolution"),
        "ms_per_tick": ms_tick,
        "tracks": [{"singer": t.get("singer"),
                    "phonemizer": t.get("phonemizer"),
                    "name": t.get("track_name")}
                   for t in doc.get("tracks", [])],
        "voice_parts": parts,
        "wave_parts": wparts}


def _render_env(cfg):
    import hashlib
    oudir = Path(cfg["openutau_dir"])
    exe = oudir / "OpenUtau.exe"
    core = oudir / "OpenUtau.Core.dll"
    return {
        "openutau_dir": str(oudir),
        "singer": RENDER_SINGER,
        "openutau_exe_sha256":
            hashlib.sha256(exe.read_bytes()).hexdigest()
            if exe.exists() else None,
        "openutau_core_sha256":
            hashlib.sha256(core.read_bytes()).hexdigest()
            if core.exists() else None,
        "note": ("standardized render substitutes project singer "
                 "with the installed voicebank; original singer "
                 "yousaV1.56 is NOT installed")}


def main():
    head = drv._require_clean_worktree("l7j6_corpus")
    cfg = load_config()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"evaluated_head": head,
                "worktree_clean_at_generation": True,
                "corpus": "huahai full reference corpus (J6)",
                "human_projects": [], "source": {}, "game": {},
                "other_discovered_projects": []}

    # ---------------- J6.1 inventory ----------------
    discovered = []
    for d in PROJECT_DIRS:
        for p in sorted(d.glob("*.ustx")):
            discovered.append(p)
    hua = [p for p in discovered if "花海" in p.name]
    manifest["other_discovered_projects"] = [
        {"path": str(p), "sha256": sha256(p), "class": "other_song"}
        for p in discovered if p not in hua]
    print(f"discovered {len(discovered)} ustx, "
          f"{len(hua)} huahai", flush=True)

    # ---------------- per-project corpus ----------------
    for p in hua:
        sha = sha256(p)
        pid = "huahai_plus4_baishuo_" + sha[:8]
        pdir = OUT / "human_projects" / pid
        pdir.mkdir(parents=True, exist_ok=True)
        dst = pdir / ("original_project" + p.suffix)
        shutil.copyfile(p, dst)
        doc = load_ustx(p)
        meta = _project_meta(doc, p)
        meta.update({"original_path": str(p),
                     "original_filename": p.name,
                     "sha256": sha,
                     "committed_copy": str(dst),
                     "committed_copy_sha256": sha256(dst),
                     "wave_offset_s": 1.29,
                     "audio_axis": "jay audio = project_s - wave_off",
                     "declared_transposition": "+4 key (project name)",
                     "measured_transposition":
                         "supported_median ~+4.2st on track0 parts "
                         "(see huahai_benchmark/j0_inputs.json)",
                     "state": "COMMITTED"})
        # written-control dump per voice part
        for i, vp in enumerate(doc["voice_parts"]):
            _written_npz(pdir / f"written_part{i}.npz", vp)
        (pdir / "metadata.json").write_text(
            json.dumps(meta, indent=1, ensure_ascii=False),
            encoding="utf-8")
        entry = {"project_id": pid, "state": "COMMITTED",
                 "path": str(pdir), "sha256": sha,
                 "original_render": "MISSING (no referenced wave "
                                    "files exist locally)"}
        # standardized full-song render on 1.65c/dpV2
        try:
            import copy as _copy
            rdoc = _copy.deepcopy(doc)
            for tr in rdoc["tracks"]:
                tr["singer"] = RENDER_SINGER
            rustx = pdir / "standardized_render_project.ustx"
            hb.save_ustx(rdoc, rustx)
            rwav = drv.render(cfg, rustx,
                              pdir / "standardized_render")
            env = _render_env(cfg)
            for name, fn in (("fcpe", extract_f0),
                             ("rmvpe", infer_rmvpe)):
                f0 = fn(rwav)
                _f0_npz(
                    pdir / f"standardized_render_f0_{name}.npz",
                    f0, extractor=name, audio=rwav,
                    axis="project", wave_off=1.29,
                    project_sha=sha256(rustx), render_env=env)
            entry["standardized_render"] = {
                "wav": str(rwav), "sha256": sha256(rwav),
                "singer_substitution": RENDER_SINGER}
        except Exception as e:  # noqa: BLE001
            entry["standardized_render"] = {"state": "FAILED",
                                            "error": str(e)[:300]}
        manifest["human_projects"].append(entry)
        print(f"  {pid}: {entry['state']} "
              f"render={'wav' in str(entry.get('standardized_render'))}",
              flush=True)

    # ---------------- J6.4 SOURCE full F0 ----------------
    sdir = OUT / "source"
    sdir.mkdir(parents=True, exist_ok=True)
    for tag, stem in (("uvr_mdx_voc_ft", UVR_VOCALS),
                      ("kim_vocal_2", KIM2_VOCALS)):
        if not Path(stem).exists():
            manifest["source"][tag] = {"state": "MISSING_STEM"}
            continue
        for name, fn in (("fcpe", extract_f0), ("rmvpe", infer_rmvpe)):
            f0 = fn(stem)
            _f0_npz(sdir / f"jay_source_f0_{tag}_{name}.npz", f0,
                    extractor=name, audio=stem, axis="jay_audio",
                    wave_off=0.0)
        manifest["source"][tag] = {
            "stem": str(stem), "stem_sha256": sha256(stem),
            "f0_extractors": ["fcpe", "rmvpe"]}
        print(f"  source {tag} f0 done", flush=True)
    manifest["source"]["original_audio"] = {
        "path": str(JAY_FLAC), "sha256": sha256(JAY_FLAC),
        "note": "bound by path+hash; bytes not duplicated"}

    # ---------------- J6.3 GAME evidence ----------------
    gdir = OUT / "game"
    gdir.mkdir(parents=True, exist_ok=True)
    game_note = ("no pre-existing Huahai GAME artifact found anywhere "
                 "in runs/ or project dirs; generated_for_corpus=true "
                 "with the pinned existing implementation")
    try:
        from agent2utau.transcription.game_onnx import (
            GameOnnx, default_model_dir)
        import librosa
        wav, _sr = librosa.load(str(KIM2_VOCALS), sr=44100, mono=True)
        g = GameOnnx(default_model_dir())
        notes = g.infer(wav, language="zh", seed=42)
        (gdir / "game_huahai_kim2_notes.json").write_text(
            json.dumps(notes, ensure_ascii=False), encoding="utf-8")
        start = np.array([n["start"] for n in notes], dtype=np.float64)
        _npz(gdir / "game_huahai_kim2_notes.npz",
             start_s=start,
             dur_s=np.array([n["dur"] for n in notes],
                            dtype=np.float32),
             tone_midi=np.array([n["tone"] for n in notes],
                                dtype=np.float32),
             voiced=np.array([n["voiced"] for n in notes],
                             dtype=bool))
        manifest["game"] = {
            "state": "GENERATED_NO_EXISTING_ARTIFACT",
            "note": game_note,
            "generator": "agent2utau.transcription.game_onnx "
                         "(pinned code head below)",
            "code_head": head,
            "seed": 42, "language": "zh",
            "input_audio": str(KIM2_VOCALS),
            "input_audio_sha256": sha256(KIM2_VOCALS),
            "n_notes": len(notes),
            "audio_axis": "jay_audio",
            "representation": "note-level {start,dur,tone,voiced} "
                              "— GAME's written-pitch form, not a "
                              "frame F0"}
    except Exception as e:  # noqa: BLE001
        manifest["game"] = {"state": "FAILED", "error": str(e)[:300],
                            "note": game_note}
    print("  game:", manifest["game"]["state"], flush=True)

    (OUT / "manifest.json").write_text(
        json.dumps(drv._jsonable(manifest), indent=1,
                   ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT / "manifest.json")


if __name__ == "__main__":
    main()
