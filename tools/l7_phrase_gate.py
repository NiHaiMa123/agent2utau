"""L7 phrase gate driver — deterministic end-to-end run for one phrase.

Per phrase window this script:
  1. slices the trusted base_score notes inside the phrase window
     (identity/lyrics/timing unchanged — expression work only),
  2. builds SOURCE / neutral contour signals on the shared absolute axis
     from the committed full-song F0 caches (no DTW, no lag search),
  3. detects events separately in SOURCE and neutral, matches them,
  4. compiles the event-aware C3 PITD candidate (compile_C3) plus native
     note-vibrato marks,
  5. renders v1 through the real OpenUtau bridge, runs ONE bounded
     closed-loop correction (closed_loop_update -> v2), and arbitrates
     via run_shape_gate: topology + event-lane + the absolute
     event-shape gate, all fail-closed, with at most one rollback (v3),
  6. rewrites the phrase artifact bundle: SOURCE.wav, dense.npz,
     events/, qa/, run_manifest.json bound to file SHA256s and code
     provenance.

Every render goes through a2u-bridge.exe — stale or synthetic wavs are
never treated as evidence.  QA mask convention (documented, uniform):
all SOURCE-voiced frames inside written notes (src.voiced & note_idx>=0).

Usage:
    .venv/Scripts/python.exe tools/l7_phrase_gate.py [P1_sustain ...]
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent2utau.analysis.f0 import extract_f0
from agent2utau.analysis.rmvpe import infer_rmvpe
from agent2utau.expression import contour_qa as cq
from agent2utau.expression.contour import build_contour_signal
from agent2utau.expression.events import (
    detect_artifact_regions, detect_onset_events, detect_ornament_events,
    detect_portamento_events, detect_stable_trend, detect_vibrato_events,
    event_to_json, match_pitch_events, match_vibrato_events)
from agent2utau.expression.pitch_residual import (
    compile_C3, compile_portamento_lane, closed_loop_update,
    compute_dense, flatten_pitd_spans, run_shape_gate)
from agent2utau.openutau.bridge import run_bridge
from agent2utau.openutau.ustx import TempoMap, is_sung, load_ustx, \
    save_ustx, semantic_notes_sha256, sha256
from agent2utau.resources.config import load_config

RUN_DIR = Path("runs/expr-20260921")
PHRASE_DIR = RUN_DIR / "phrases3"
BASE_USTX = RUN_DIR / "expression" / "base_score.ustx"
SRC_VOCAL = Path("runs/_cache/082598c2b4b5/"
                 "original_(Vocals)_UVR-MDX-NET-Voc_FT.wav")
SRC_FCPE = Path("runs/_cache/082598c2b4b5/"
                "f0-fcpe-v2-voiced-mask-native-clock.npz")
SRC_RMVPE = RUN_DIR / "expression" / "dense" / "f0_rmvpe_ref.npz"
NEU_FCPE = RUN_DIR / "expression" / "neutral" / "f0_neutral.npz"
NEU_RMVPE = RUN_DIR / "expression" / "dense" / "f0_rmvpe_neu.npz"
CHAR_NUCLEUS = Path("runs/hfa/char_nucleus.json")

# Phrase windows on the absolute source axis, seconds.  Fixed review
# targets: P1 sustained line, P2 slide-dense line, P3 vibrato tail.
PHRASES = {
    "P1_sustain": (18.8, 21.61),
    "P2_slides": (51.16, 56.71),
    "P3_vibrato": (25.23, 30.77),
}
PAD_S = 0.30            # context pad around the phrase window
NUCLEUS_TOL_S = 0.7     # |char w0 - note start| tolerance


def _npz_f0(p):
    d = np.load(p)
    return {"times": d["times"], "f0_hz": d["f0_hz"],
            "voiced": d["voiced"].astype(bool)}


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return [_jsonable(v) for v in o.tolist()]
    return o


def _dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(obj), ensure_ascii=False,
                               indent=1), encoding="utf-8")


def _git_head():
    p = subprocess.run(["git", "rev-parse", "HEAD"],
                       capture_output=True, text=True, check=True)
    return p.stdout.strip()


def _require_clean_worktree(context="L7 artifact generation"):
    """Artifacts may bind a commit SHA only when that SHA actually
    contains the code being executed.  Running with uncommitted source
    changes produces false provenance (HEAD names code that cannot
    reproduce the bytes), so fail before any render/evaluation work."""
    p = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                       capture_output=True, text=True, check=True)
    dirty = [line for line in p.stdout.splitlines() if line.strip()]
    if dirty:
        sample = "; ".join(dirty[:8])
        raise RuntimeError(
            f"{context} requires a clean git worktree before execution; "
            f"commit/stash changes first. Dirty entries: {sample}")
    return _git_head()


def phrase_notes(doc, w0, w1):
    """Notes fully inside [w0,w1]; keeps the base note dict for rebuild."""
    tm = TempoMap.from_doc(doc)
    part = next(p for p in doc["voice_parts"]
                if p["name"] == "vocal_pipeline")
    out = []
    for n in part["notes"]:
        a = int(part["position"]) + int(n["position"])
        s = tm.tick_to_ms(a) / 1000.0
        e = tm.tick_to_ms(a + int(n["duration"])) / 1000.0
        if s >= w0 - 1e-3 and e <= w1 + 1e-3:
            out.append({"abs_start_s": s, "dur_s": e - s,
                        "tone": n["tone"], "lyric": n["lyric"],
                        "_abs_tick": a, "_dur_tick": int(n["duration"]),
                        "_note": n})
    return part, out


def nucleus_times(notes):
    """{phrase note index: nucleus time} from HubertFA char_nucleus.json,
    matched in lyric order with |w0 - note start| <= NUCLEUS_TOL_S."""
    chars = json.loads(CHAR_NUCLEUS.read_text(encoding="utf-8"))
    nuc, ci = {}, 0
    for i, n in enumerate(notes):
        if not is_sung(n["_note"]):
            continue
        while ci < len(chars) and chars[ci]["char"] != n["lyric"]:
            ci += 1
        if ci < len(chars) and \
                abs(chars[ci]["w0"] - n["abs_start_s"]) <= NUCLEUS_TOL_S:
            nuc[i] = float(chars[ci]["nuc"])
            ci += 1
    return nuc


def detect_all(sig, notes, nuc):
    """Full detector battery on one signal; committed ordering
    vibrato/onset/portamento/ornament/artifact/stable."""
    vib = detect_vibrato_events(sig, notes)
    ons = detect_onset_events(sig, notes, nuc, exclude_events=vib)
    port = detect_portamento_events(sig, notes)
    orn = detect_ornament_events(sig, notes,
                                 exclude_events=vib + ons + port)
    art = detect_artifact_regions(sig, notes)
    stab = detect_stable_trend(sig, notes,
                               vib + ons + port + orn + art)
    return vib + ons + port + orn + art + stab


def _matches_to_json(m):
    return {
        "matched": [{**d, "source": str(d["source"]),
                     "neutral": str(d["neutral"])}
                    for d in m["matched"]],
        "source_only": [str(e) for e in m["source_only"]],
        "neutral_only": [str(e) for e in m["neutral_only"]],
        "ambiguous": [{**d, "source": str(d["source"])}
                      for d in m["ambiguous"]]}


def build_phrase_doc(base_doc, base_part, notes, part_pos, pitd,
                     vib_marks, name, porta_marks=None):
    """Phrase USTX: base doc minus wave parts, one voice part holding the
    window's notes.  Written note pitch-bend data is flattened — the PITD
    curve is the sole expression carrier for the candidate, except where
    the portamento lane (compile_portamento_lane) owns a verified
    cross-note slide on the target note's pitch.data."""
    part = {k: copy.deepcopy(v) for k, v in base_part.items()
            if k not in ("notes", "curves", "Duration")}
    part["name"] = name
    part["position"] = part_pos
    porta_marks = porta_marks or {}
    new_notes = []
    for i, nd in enumerate(notes):
        n = copy.deepcopy(nd["_note"])
        n["position"] = nd["_abs_tick"] - part_pos
        if i in porta_marks:
            n["pitch"] = copy.deepcopy(porta_marks[i])
        else:
            n["pitch"] = {"data": [{"x": -40, "y": 0, "shape": "io"},
                                   {"x": 0, "y": 0, "shape": "io"}],
                          "snap_first": bool(
                              n.get("pitch", {}).get("snap_first", False))}
        vib = {"length": 0, "period": 175, "depth": 25, "in": 10,
               "out": 10, "shift": 0, "drift": 0, "volLink": 0}
        vib.update(vib_marks.get(i, {}))
        n["vibrato"] = vib
        new_notes.append(n)
    part["notes"] = new_notes
    part["curves"] = [pitd]
    last = notes[-1]
    part["Duration"] = (last["_abs_tick"] + last["_dur_tick"]
                        - part_pos + 480)
    doc = copy.deepcopy(base_doc)
    doc["voice_parts"] = [part]
    doc["wave_parts"] = []
    return doc


def render(cfg, ustx_path, out_stem, timeout=600):
    """Real render through the bridge; returns the produced vocal wav.
    Paths must be absolute — the bridge cwd is the OpenUtau install dir."""
    res = run_bridge(cfg, ["render", "--project",
                           str(Path(ustx_path).resolve()),
                           "--out",
                           str(Path(out_stem).resolve()) + ".wav"],
                     timeout=timeout)
    if not res.get("ok"):
        raise RuntimeError(f"bridge render failed for {ustx_path}: "
                           f"{res.get('errors')}")
    files = res.get("files") or []
    if not files:
        raise RuntimeError(f"bridge produced no wav for {ustx_path}")
    return Path(files[0]["path"])


def run_phrase(phrase, cfg, base_doc, caches, head,
               porta_ownership="full_note"):
    w0, w1 = PHRASES[phrase]
    t0, t1 = w0 - PAD_S, w1 + PAD_S
    pdir = PHRASE_DIR / phrase
    pdir.mkdir(parents=True, exist_ok=True)
    print(f"== {phrase} window [{w0},{w1}]", flush=True)

    base_part, notes = phrase_notes(base_doc, w0, w1)
    part_pos = notes[0]["_abs_tick"] - 480
    nuc = nucleus_times(notes)
    print(f"   {len(notes)} notes, part_pos {part_pos}, "
          f"nuclei {len(nuc)}", flush=True)

    # SOURCE.wav = vocal cut [t0,t1] (mono 44.1k s16, listening ref)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.3f}",
         "-to", f"{t1:.3f}", "-i", str(SRC_VOCAL),
         "-ac", "1", "-ar", "44100", str(pdir / "SOURCE.wav")],
        check=True)

    src_sig = build_contour_signal(caches["src_fcpe"], caches["src_rmvpe"],
                                   notes, t0_s=t0, t1_s=t1,
                                   extractor="fcpe", source="source")
    src_sig_b = build_contour_signal(caches["src_rmvpe"],
                                     caches["src_fcpe"], notes,
                                     t0_s=t0, t1_s=t1,
                                     extractor="rmvpe", source="source")
    neu_sig = build_contour_signal(caches["neu_fcpe"], caches["neu_rmvpe"],
                                   notes, t0_s=t0, t1_s=t1,
                                   extractor="fcpe", source="neutral")
    neu_sig_b = build_contour_signal(caches["neu_rmvpe"],
                                     caches["neu_fcpe"], notes,
                                     t0_s=t0, t1_s=t1,
                                     extractor="rmvpe", source="neutral")
    dense = compute_dense(caches["src_fcpe"], caches["neu_fcpe"],
                          caches["src_rmvpe"], caches["neu_rmvpe"],
                          notes, t0, t1)
    np.savez(pdir / "dense.npz", **dense)

    src_events = detect_all(src_sig, notes, nuc)
    neu_events = detect_all(neu_sig, notes, nuc)
    # Independent F0 family for the cross-extractor gate: the same
    # detector battery runs on the rmvpe-family signals so the absolute
    # event-shape verdict can be re-measured off the fcpe family.
    src_events_b = detect_all(src_sig_b, notes, nuc)
    neu_events_b = detect_all(neu_sig_b, notes, nuc)
    vib_match = match_vibrato_events(src_events, neu_events, notes)
    pitch_match = match_pitch_events(src_events, neu_events, notes, nuc)
    print(f"   events src {len(src_events)} neu {len(neu_events)} "
          f"matched {len(pitch_match['matched'])}", flush=True)

    pitd_v1, vib_marks, vib_prov = compile_C3(
        dense, src_sig, neu_sig, notes, part_pos, vib_match,
        max_err_c=10.0,
        base_vibrato={i: n["_note"].get("vibrato")
                      for i, n in enumerate(notes)})

    # Native portamento lane (L7-R3): extractor-stable cross-note slides
    # are carried by the TARGET note's pitch.data instead of PITD —
    # the acoustic transition smoothing breaks written-coords PITD on
    # ~40ms gestures (probe_portamento/ evidence).  The lane owns its
    # span absolutely, so PITD is flattened there to avoid a double
    # residual.
    porta_marks, porta_spans, porta_prov = compile_portamento_lane(
        src_sig, src_sig_b, notes, src_events, vib_marks=vib_marks,
        ownership=porta_ownership)
    if porta_spans:
        pitd_v1 = flatten_pitd_spans(pitd_v1, porta_spans, part_pos)
        print(f"   portamento lane: {len(porta_marks)} notes, "
              f"{len(porta_spans)} owned spans", flush=True)

    # QA mask: all SOURCE-voiced frames inside written notes (uniform
    # across stages and across both extractor families, each on its own
    # signal's voiced mask).
    qa_mask = src_sig.voiced & (src_sig.note_idx >= 0)
    qa_mask_b = src_sig_b.voiced & (src_sig_b.note_idx >= 0)

    recs = {}          # stage tag -> render record
    rec_by_sig = {}    # id(sig) -> render record

    def load_render(wav):
        f = extract_f0(wav)
        r = infer_rmvpe(wav)
        sig = build_contour_signal(f, r, notes, t0_s=t0, t1_s=t1,
                                   extractor="fcpe", source="render")
        sig_b = build_contour_signal(r, f, notes, t0_s=t0, t1_s=t1,
                                     extractor="rmvpe", source="render")
        rec = {"wav": Path(wav), "sig": sig, "sig_b": sig_b,
               "events": detect_all(sig, notes, nuc),
               "events_b": detect_all(sig_b, notes, nuc)}
        rec_by_sig[id(sig)] = rec
        return rec

    def qa_fn(sig):
        ev = rec_by_sig[id(sig)]["events"]
        return {"topology": cq.turning_point_metrics(
                    src_sig.cents, sig.cents, qa_mask),
                "portamento": cq.portamento_metrics(src_events, ev),
                "vibrato": cq.vibrato_metrics(src_events, ev)}

    def event_shape_fn(sig):
        return cq.event_shape_gate(src_events,
                                   rec_by_sig[id(sig)]["events"],
                                   neu_sig, src_sig, sig)

    def candidate_fn(curve, tag):
        # tags 'v2'/'v3' -> files {P}_C3v2.ustx / {P}_C3v3.ustx
        # Lane-owned spans stay flattened even if the closed-loop update
        # or rollback wrote into them (owned span extends to note end,
        # beyond the protected event window).
        curve = flatten_pitd_spans(curve, porta_spans, part_pos)
        ustx = pdir / f"{phrase}_C3{tag}.ustx"
        save_ustx(build_phrase_doc(base_doc, base_part, notes, part_pos,
                                   curve, vib_marks, f"{phrase}_C3",
                                   porta_marks=porta_marks),
                  ustx)
        rec = load_render(render(cfg, ustx, pdir / f"{phrase}_C3{tag}"))
        rec["ustx"] = ustx
        recs[tag] = rec
        print(f"   rendered {tag}: {rec['wav'].name}", flush=True)
        return curve, rec["sig"]

    # ---- v1: compile -> real render -> signal ------------------------
    ustx_v1 = pdir / f"{phrase}_C3.ustx"
    save_ustx(build_phrase_doc(base_doc, base_part, notes, part_pos,
                               pitd_v1, vib_marks, f"{phrase}_C3",
                               porta_marks=porta_marks),
              ustx_v1)
    rec_v1 = load_render(render(cfg, ustx_v1, pdir / f"{phrase}_C3_v1"))
    rec_v1["ustx"] = ustx_v1
    recs["v1"] = rec_v1
    print(f"   rendered v1: {rec_v1['wav'].name}", flush=True)

    pitd_v2 = flatten_pitd_spans(
        closed_loop_update(
            pitd_v1, src_sig, rec_v1["sig"], notes, part_pos,
            protected_events=src_events, clip_c=300.0, max_err_c=10.0,
            guard_s=0.15),
        porta_spans, part_pos)

    final_curve, gate = run_shape_gate(
        pitd_v1, pitd_v2, src_sig, rec_v1["sig"], notes, part_pos,
        candidate_fn=candidate_fn, qa_fn=qa_fn,
        event_shape_fn=event_shape_fn)
    print(f"   gate -> {gate['final_candidate']} "
          f"blocked={gate['blocked']}", flush=True)

    # ---- final artifacts on the ACCEPTED candidate -------------------
    final_tag = gate["final_candidate"]
    rec = recs[final_tag]
    final_sig, final_events = rec["sig"], rec["events"]

    qa = {
        "position_metrics": cq.contour_position_metrics(
            src_sig.cents, final_sig.cents, qa_mask),
        "slope_metrics": cq.contour_slope_metrics(
            src_sig.cents, final_sig.cents, qa_mask),
        "curvature_metrics": cq.contour_curvature_metrics(
            src_sig.cents, final_sig.cents, qa_mask),
        "topology_metrics": cq.turning_point_metrics(
            src_sig.cents, final_sig.cents, qa_mask),
        "modulation_metrics": cq.modulation_metrics(
            src_sig.cents, final_sig.cents, qa_mask),
        "vibrato_metrics": cq.vibrato_metrics(src_events, final_events),
        "portamento_metrics": cq.portamento_metrics(src_events,
                                                    final_events),
        "event_shape_metrics": cq.event_shape_gate(
            src_events, final_events, neu_sig, src_sig, final_sig),
        # Cross-extractor lane (plan §7.4): the absolute event-shape
        # verdict re-measured entirely on the rmvpe family. Same
        # extractor self-scoring can never authorize PASS.
        "event_shape_metrics_rmvpe": cq.event_shape_gate(
            src_events_b, rec["events_b"], neu_sig_b, src_sig_b,
            rec["sig_b"]),
        "shape_gate_report": gate,
    }
    state = dense["state"]
    st_names = ["both_voiced", "src_only", "neu_only", "unvoiced",
                "extractor_conflict", "note_transition", "gap"]
    fr = {st_names[i]: round(float((state == i).mean()), 4)
          for i in range(len(st_names)) if (state == i).any()}
    art = [e for e in src_events if e.type == "artifact"]
    amask = np.zeros(len(src_sig.times), dtype=bool)
    for e in art:
        amask |= (src_sig.times >= e.start_s) & (src_sig.times <= e.end_s)
    qa["artifact_coverage"] = {
        "frame_state_ratio": fr,
        "artifact_regions": len(art),
        "artifact_frames_ratio": round(
            float((amask & qa_mask).sum() / max(qa_mask.sum(), 1)), 4)}
    qa["cross_extractor_metrics"] = {
        "fcpe_eval": cq.contour_position_metrics(
            src_sig.cents, final_sig.cents, qa_mask),
        "rmvpe_eval": cq.contour_position_metrics(
            src_sig_b.cents, rec["sig_b"].cents, qa_mask_b)}
    for name, payload in qa.items():
        _dump(payload, pdir / "qa" / f"{name}.json")

    ev_dir = pdir / "events"
    _dump([event_to_json(e) for e in src_events],
          ev_dir / "source_events.json")
    _dump([event_to_json(e) for e in neu_events],
          ev_dir / "neutral_events.json")
    _dump([event_to_json(e) for e in final_events],
          ev_dir / "render_events.json")
    _dump({"pitch_matches": _matches_to_json(pitch_match),
           "vibrato_matches": vib_match}, ev_dir / "event_matches.json")
    _dump([event_to_json(e) for e in src_events],
          ev_dir / f"{phrase}_source.json")
    _dump([event_to_json(e) for e in neu_events],
          ev_dir / f"{phrase}_neutral.json")
    _dump(_matches_to_json(pitch_match), ev_dir / f"{phrase}_matched.json")
    _dump(vib_match, ev_dir / f"{phrase}_vibrato_match.json")
    _dump([], ev_dir / f"{phrase}.json")

    variant = "C3" if final_tag == "v1" else f"C3{final_tag}"
    manifest = {
        "variant": variant,
        "generator_code_head": head,
        "qa_code_head": _git_head(),
        "worktree_clean_at_generation": True,
        "base_file_sha256": sha256(BASE_USTX),
        "base_semantic_sha256": semantic_notes_sha256(base_doc),
        "candidate_ustx_sha256": sha256(rec["ustx"]),
        "ustx_path": str(rec["ustx"].resolve()),
        "render_wav_sha256": sha256(rec["wav"]),
        "render_wav_path": str(rec["wav"].resolve()),
        "shape_gate": {
            "final_candidate": variant,
            "blocked": gate["blocked"],
            "stages": [{"candidate": s["candidate"],
                        "gate_passed": s["gate_passed"],
                        "violations": s["violations"],
                        "event_shape": {
                            "status": s["event_shape"]["status"],
                            "n_blocking":
                                s["event_shape"].get("n_blocking")}}
                       for s in gate["stages"]]},
        "f0_extractors": {
            "fcpe": {"model": "torchfcpe", "hop_ms": 10, "sr": 16000},
            "rmvpe": {"model": "rmvpe onnx", "hop_ms": 10}},
        "compiler": {
            "module": "agent2utau.expression.pitch_residual",
            "candidate": "C3", "vibrato_depth_gain": 0.69,
            "closed_loop_clip_c": 300, "closed_loop_max_err_c": 10,
            "closed_loop_guard_s": 0.15, "closed_loop_iterations": 1,
            "portamento_lane_ownership": porta_ownership,
            "portamento_lane": porta_prov},
        "phrase_window_s": [w0, w1],
        "qa_files": sorted(f"{n}.json" for n in qa),
        "event_files": ["source_events.json", "neutral_events.json",
                        "render_events.json", "event_matches.json"]}
    _dump(manifest, pdir / "run_manifest.json")
    print(f"   manifest: variant {variant} blocked={gate['blocked']} "
          f"blocking_es={qa['event_shape_metrics']['n_blocking']}",
          flush=True)


def main():
    head = _require_clean_worktree("l7_phrase_gate")
    cfg = load_config()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {a.split("=", 1)[0]: a.split("=", 1)[1]
            for a in sys.argv[1:] if "=" in a}
    porta_ownership = opts.get("--porta-ownership", "full_note")
    which = args or list(PHRASES)
    base_doc = load_ustx(BASE_USTX)
    caches = {"src_fcpe": _npz_f0(SRC_FCPE), "src_rmvpe": _npz_f0(SRC_RMVPE),
              "neu_fcpe": _npz_f0(NEU_FCPE), "neu_rmvpe": _npz_f0(NEU_RMVPE)}
    for phrase in which:
        run_phrase(phrase, cfg, base_doc, caches, head,
                   porta_ownership=porta_ownership)


if __name__ == "__main__":
    main()
