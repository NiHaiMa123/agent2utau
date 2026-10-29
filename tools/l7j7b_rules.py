"""L7 Round J7B event-geometry and boundary-ownership trial."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import l7_phrase_gate as drv
import l7j_huahai_benchmark as hb
from agent2utau.analysis.f0 import extract_f0
from agent2utau.analysis.rmvpe import infer_rmvpe
from agent2utau.expression.contour import build_contour_signal, robust_pitch_trend
from agent2utau.expression.events import (
    detect_artifact_regions,
    detect_onset_events,
    detect_ornament_events,
    detect_portamento_events,
    detect_vibrato_events,
    event_to_json,
    match_pitch_events,
)
from agent2utau.expression.lowdof import (
    body_value,
    fit_body_model,
    note_core_window,
    pitd_curve,
    structural_transition,
)
from agent2utau.openutau.ustx import load_ustx, sha256
from agent2utau.resources.config import load_config

CORPUS = Path("runs/huahai_corpus")
OUT = Path("runs/huahai_j7b")
WAVE_OFF = 1.29
MIN_CONFIDENCE = 5.0 / 6.0


def _load_source():
    out = {}
    ratio = 2.0 ** (4.0 / 12.0)
    for name in ("fcpe", "rmvpe"):
        z = np.load(CORPUS / "source" /
                    f"jay_source_f0_kim_vocal_2_{name}.npz")
        out[name] = {
            "times": np.asarray(z["times"], dtype=float) + WAVE_OFF,
            "f0_hz": np.asarray(z["f0_hz"], dtype=float) * ratio,
            "voiced": np.asarray(z["voiced"], dtype=bool),
        }
    return out


def _nucleus_times(signal, notes):
    out = {}
    for i, note in enumerate(notes):
        a = note["abs_start_s"]
        e = min(a + 0.18, a + 0.4 * note["dur_s"])
        m = ((signal.times >= a) & (signal.times <= e) & signal.voiced
             & (signal.confidence >= MIN_CONFIDENCE))
        idx = np.flatnonzero(m)
        if len(idx):
            out[i] = float(signal.times[idx[0]])
    return out


def _overlaps_artifact(event, artifacts):
    return any(min(event.end_s, a.end_s) > max(event.start_s, a.start_s)
               for a in artifacts)


def _detect(signal, notes, nuclei):
    vib = detect_vibrato_events(signal, notes)
    onset = detect_onset_events(signal, notes, nuclei, exclude_events=vib)
    porta = detect_portamento_events(signal, notes)
    ornament = detect_ornament_events(
        signal, notes, exclude_events=vib + onset + porta)
    artifact = detect_artifact_regions(signal, notes)
    return {"vibrato": vib, "onset": onset, "portamento": porta,
            "ornament": ornament, "artifact": artifact}


def _dual_events(fcpe_signal, rmvpe_signal, notes):
    nuclei = _nucleus_times(fcpe_signal, notes)
    left = _detect(fcpe_signal, notes, nuclei)
    right = _detect(rmvpe_signal, notes, nuclei)
    matched = match_pitch_events(
        left["onset"] + left["portamento"] + left["ornament"],
        right["onset"] + right["portamento"] + right["ornament"],
        notes, nuclei)
    artifacts = left["artifact"] + right["artifact"]
    supported = []
    matches = []
    for row in matched["matched"]:
        event = row["source"]
        if _overlaps_artifact(event, artifacts):
            continue
        supported.append(event)
        matches.append({"score": row["score"],
                        "source": event_to_json(row["source"]),
                        "secondary": event_to_json(row["neutral"])})

    vibrato_matches = []
    for i in range(len(notes)):
        va = [e for e in left["vibrato"] if i in e.note_indices]
        vb = [e for e in right["vibrato"] if i in e.note_indices]
        if not va or not vb:
            continue
        a, b = va[0], vb[0]
        overlap = max(0.0, min(a.end_s, b.end_s) - max(a.start_s, b.start_s))
        union = max(a.end_s, b.end_s) - min(a.start_s, b.start_s)
        rate_delta = abs(a.params["rate_hz"] - b.params["rate_hz"])
        depth_delta = abs(a.params["depth_c"] - b.params["depth_c"])
        if overlap / max(union, 1e-6) < 0.5 or rate_delta > 0.8 \
                or depth_delta > 40.0 or _overlaps_artifact(a, artifacts):
            continue
        supported.append(a)
        vibrato_matches.append({"note_index": i,
                                "rate_delta_hz": round(rate_delta, 2),
                                "depth_delta_c": round(depth_delta, 1),
                                "source": event_to_json(a),
                                "secondary": event_to_json(b)})
    return supported, {
        "nuclei": {str(k): round(v, 3) for k, v in nuclei.items()},
        "primary": {k: [event_to_json(e) for e in v]
                    for k, v in left.items()},
        "secondary": {k: [event_to_json(e) for e in v]
                      for k, v in right.items()},
        "matched": matches,
        "vibrato_matched": vibrato_matches,
        "supported": [event_to_json(e) for e in supported],
    }


def _knot(time_s, value_c, owner, priority):
    return {"time_s": float(time_s), "value_c": float(value_c),
            "owner": owner, "priority": int(priority)}


def _event_knots(event, note, model):
    a = note["abs_start_s"]
    b = a + note["dur_s"]
    out = []
    if event.type in ("scoop", "undershoot", "overshoot"):
        peak = (event.params["anchor_nucleus_s"]
                + event.params["peak_time_ms"] / 1000.0)
        peak = min(max(peak, a), b - 0.01)
        start = min(max(event.start_s, a), peak)
        end = min(max(event.end_s, peak), b - 0.005)
        sign = 1.0 if event.type == "overshoot" else -1.0
        depth = min(float(event.params["depth_c"]), 180.0)
        out.extend([
            _knot(start, body_value(model, start),
                  f"onset:{event.type}:baseline", 70),
            _knot(peak, body_value(model, peak) + sign * depth,
                  f"onset:{event.type}:extremum", 72),
            _knot(end, body_value(model, end),
                  f"onset:{event.type}:settle", 70),
        ])
    elif event.type == "ornament":
        start = max(a, event.start_s - 0.02)
        end = min(b - 0.005, event.end_s + 0.02)
        out.append(_knot(start, body_value(model, start),
                         "ornament:baseline", 70))
        for dt, excursion in zip(event.params["extrema_rel_ms"],
                                 event.params["excursions_c"]):
            t = min(max(event.start_s + dt / 1000.0, a), b - 0.005)
            value = body_value(model, t) + float(np.clip(excursion, -180, 180))
            out.append(_knot(t, value, "ornament:extremum", 72))
        out.append(_knot(end, body_value(model, end),
                         "ornament:settle", 70))
    elif event.type == "vibrato":
        start = max(a, event.start_s)
        end = min(b - 0.005, event.end_s)
        rate = float(event.params["rate_hz"])
        phase = float(event.params["phase_rad"])
        origin = float(event.params["phase_origin_s"])
        depths = np.asarray(event.params["depth_envelope_c"], dtype=float)
        depths = np.clip(depths, 0.0, 100.0)
        out.append(_knot(start, body_value(model, start),
                         "vibrato:baseline", 65))
        k0 = int(np.floor((2 * np.pi * rate * (start - origin) + phase
                           - np.pi / 2) / np.pi)) - 1
        k1 = int(np.ceil((2 * np.pi * rate * (end - origin) + phase
                          - np.pi / 2) / np.pi)) + 1
        for k in range(k0, k1 + 1):
            t = origin + (np.pi / 2 + k * np.pi - phase) / (2 * np.pi * rate)
            if t <= start or t >= end:
                continue
            frac = (t - start) / max(end - start, 1e-6)
            depth = float(np.interp(frac, np.linspace(0, 1, len(depths)), depths))
            out.append(_knot(t, body_value(model, t) + (-1) ** k * depth,
                             "vibrato:extremum", 67))
        out.append(_knot(end, body_value(model, end),
                         "vibrato:release", 65))
    return out


def _compile(notes, signal_a, signal_b, supported_events, part_pos, tick_ms):
    trend_a, _ = robust_pitch_trend(signal_a, cutoff_hz=1.5)
    trend_b, _ = robust_pitch_trend(signal_b, cutoff_hz=1.5)
    both = (signal_a.voiced & signal_b.voiced & np.isfinite(trend_a)
            & np.isfinite(trend_b))
    trend = np.where(both, (trend_a + trend_b) / 2.0, np.nan)
    confidence = np.minimum(signal_a.confidence, signal_b.confidence)
    models = [fit_body_model(signal_a.times, trend, both, confidence, note)
              for note in notes]

    port_by_target = {}
    for event in supported_events:
        if event.type == "portamento":
            port_by_target[int(event.params["to_note"])] = event

    knots = []
    porta_marks = {}
    transitions = []
    for i, (note, model) in enumerate(zip(notes, models)):
        a = note["abs_start_s"]
        b = a + note["dur_s"]
        for t, y in model.get("knots", []):
            knots.append(_knot(t, y, f"body:{i}:{model['model']}", 20))
        inner = min(0.025, 0.15 * note["dur_s"])
        knots.append(_knot(a + inner, body_value(model, a + inner),
                           f"body:{i}:start", 25))
        knots.append(_knot(b - inner, body_value(model, b - inner),
                           f"body:{i}:end", 25))
        if i == 0:
            knots.append(_knot(a, body_value(model, a),
                               "boundary:phrase_start", 50))
            continue
        prev = notes[i - 1]
        trans = structural_transition(prev, note, port_by_target.get(i))
        if trans is not None:
            porta_marks[i] = trans["pitch"]
            dep, arr = trans["departure_s"], trans["arrival_s"]
            knots.append(_knot(dep, body_value(models[i - 1], dep),
                               f"boundary:{i}:departure", 50))
            knots.append(_knot(arr, body_value(model, arr),
                               f"boundary:{i}:arrival", 50))
            settle = min(b - 0.005, arr + 0.03)
            knots.append(_knot(settle, body_value(model, settle),
                               f"boundary:{i}:settle", 50))
            transitions.append({"target_note": i,
                                "departure_s": round(dep, 3),
                                "arrival_s": round(arr, 3),
                                "source_supported": trans["source_supported"],
                                "pitch": trans["pitch"]})
        else:
            prev_end = prev["abs_start_s"] + prev["dur_s"]
            dep = min(prev_end - 0.005, a - 0.025)
            arr = max(a + 0.005, dep + 0.01)
            knots.append(_knot(dep, body_value(models[i - 1], dep),
                               f"boundary:{i}:departure", 50))
            knots.append(_knot(arr, body_value(model, arr),
                               f"boundary:{i}:arrival", 50))
            transitions.append({"target_note": i,
                                "departure_s": round(dep, 3),
                                "arrival_s": round(arr, 3),
                                "source_supported": False,
                                "pitch": None})

    transition_spans = [(x["departure_s"], x["arrival_s"])
                        for x in transitions]
    compiled_events = []
    for event in supported_events:
        if event.type == "portamento" or not event.note_indices:
            continue
        i = int(event.note_indices[0])
        if i >= len(notes):
            continue
        if event.type in ("scoop", "undershoot", "overshoot") and any(
                min(event.end_s, e) > max(event.start_s, s)
                for s, e in transition_spans):
            continue
        event_points = _event_knots(event, notes[i], models[i])
        knots.extend(event_points)
        if event_points:
            compiled_events.append(event_to_json(event))

    pitd, knot_audit = pitd_curve(knots, part_pos, tick_ms)
    return pitd, porta_marks, {
        "body_models": models,
        "transitions": transitions,
        "compiled_events": compiled_events,
        "knot_audit": knot_audit,
        "dof": len(pitd["xs"]) + sum(len(x["pitch"]["data"])
                                      for x in transitions if x["pitch"]),
    }


def _score_signature(part):
    return [(int(n["position"]), int(n["duration"]), int(n["tone"]),
             str(n["lyric"])) for n in part["notes"]]


def _max_bad_run(mask):
    best = cur = 0
    for value in mask:
        cur = cur + 1 if value else 0
        best = max(best, cur)
    return best


def _render_diag(wav, notes, transitions, declared_events):
    raw = {}
    for name, fn in (("fcpe", extract_f0), ("rmvpe", infer_rmvpe)):
        f0 = fn(wav)
        raw[name] = {"times": np.asarray(f0["times"], dtype=float),
                     "f0_hz": np.asarray(f0["f0_hz"], dtype=float),
                     "voiced": np.asarray(f0["voiced"], dtype=bool)}
    a = raw["fcpe"]
    b = raw["rmvpe"]
    midi_a = 69.0 + 12.0 * np.log2(np.maximum(a["f0_hz"], 1e-6) / 440.0)
    midi_b = 69.0 + 12.0 * np.log2(np.maximum(b["f0_hz"], 1e-6) / 440.0)
    interp_b = np.interp(a["times"], b["times"], midi_b)
    voiced_b = np.interp(a["times"], b["times"], b["voiced"].astype(float)) > 0.5
    both = a["voiced"] & voiced_b
    delta = np.abs(midi_a - interp_b) * 100.0

    transition_spans = [(x["departure_s"], x["arrival_s"])
                        for x in transitions]
    consecutive = (np.diff(a["times"]) <= 0.025) & a["voiced"][:-1] \
        & a["voiced"][1:]
    jump_t = (a["times"][:-1] + a["times"][1:]) / 2.0
    declared = np.zeros(len(jump_t), dtype=bool)
    for s, e in transition_spans:
        declared |= (jump_t >= s - 0.02) & (jump_t <= e + 0.02)
    jumps = np.abs(np.diff(midi_a)) * 100.0
    unexplained_jumps = int(np.sum(consecutive & ~declared & (jumps > 300.0)))

    arrival_by_note = {int(x["target_note"]): float(x["arrival_s"])
                       for x in transitions}
    rows = []
    reasons = []
    for i, note in enumerate(notes):
        a0 = note["abs_start_s"]
        b0 = a0 + note["dur_s"]
        offset = midi_a * 100.0 - note["tone"] * 100.0
        c0, c1 = note_core_window(note)
        core = a["voiced"] & (a["times"] >= c0) & (a["times"] <= c1)
        for event in declared_events:
            if i in event.get("note_indices", []):
                core &= ~((a["times"] >= event["start_s"])
                          & (a["times"] <= event["end_s"]))
        core_med = float(np.median(offset[core])) if core.sum() >= 4 else None
        arr = arrival_by_note.get(i, a0 + min(0.10, 0.3 * note["dur_s"]))
        ps = min(b0 - 0.03, arr + 0.03)
        pe = min(b0 - 0.01, ps + 0.12)
        post = a["voiced"] & (a["times"] >= ps) & (a["times"] <= pe)
        post_med = float(np.median(offset[post])) if post.sum() >= 3 else None
        stable = a["voiced"] & (a["times"] >= ps) & (a["times"] <= b0 - 0.01)
        bad_run_ms = _max_bad_run(stable & (np.abs(offset) > 200.0)) * 10
        row = {"note_index": i, "note": note["lyric"],
               "core_median_c": round(core_med, 1) if core_med is not None else None,
               "post_arrival_median_c": round(post_med, 1)
               if post_med is not None else None,
               "sustained_gt200c_ms": int(bad_run_ms)}
        rows.append(row)
        if core_med is not None and abs(core_med) > 100.0:
            reasons.append(f"note_{i}_core_displacement")
        if post_med is not None and abs(post_med) > 120.0:
            reasons.append(f"note_{i}_post_arrival_displacement")
        if bad_run_ms >= 100:
            reasons.append(f"note_{i}_sustained_displacement")
    if unexplained_jumps:
        reasons.append("unexplained_extreme_jump")
    return raw, {
        "cross_extractor": {
            "median_abs_delta_c": round(float(np.median(delta[both])), 1)
            if both.any() else None,
            "p95_abs_delta_c": round(float(np.percentile(delta[both], 95)), 1)
            if both.any() else None,
        },
        "unexplained_voiced_island_jumps_gt300c": unexplained_jumps,
        "notes": rows,
        "machine_pass": not reasons,
        "failure_reasons": sorted(set(reasons)),
    }


def _listening_tracks(candidate):
    source = candidate["tracks"][candidate["voice_parts"][0]["track_no"]]
    names = ("A0_neutral", "B_j7b_event_geometry", "C_human_reference")
    tracks = []
    for name in names:
        track = copy.deepcopy(source)
        track["track_name"] = name
        track["mute"] = False
        track["solo"] = False
        tracks.append(track)
    return tracks


def _listening_doc(neutral_path, candidate_path, human_path, out_path):
    neutral = load_ustx(neutral_path)
    candidate = load_ustx(candidate_path)
    human = load_ustx(human_path)
    doc = copy.deepcopy(candidate)
    pa = copy.deepcopy(neutral["voice_parts"][0])
    pb = copy.deepcopy(candidate["voice_parts"][0])
    pc = copy.deepcopy(human["voice_parts"][0])
    pa["name"], pb["name"], pc["name"] = (
        "A0_neutral", "B_j7b_event_geometry", "C_human_reference")
    pa["track_no"], pb["track_no"], pc["track_no"] = 0, 1, 2
    doc["tracks"] = _listening_tracks(candidate)
    doc["voice_parts"] = [pa, pb, pc]
    hb.save_ustx(doc, out_path)


def main():
    head = drv._require_clean_worktree("l7j7b_rules")
    cfg = load_config()
    OUT.mkdir(parents=True, exist_ok=True)
    doc = load_ustx(hb.HUMAN_USTX)
    t2s = hb.tempo_map(doc)
    tempo = (doc.get("tempos") or [{"bpm": 75}])[0]["bpm"]
    tick_ms = 60000.0 / (tempo * 480.0)
    picked = json.loads((hb.OUT / "j1_phrases.json")
                        .read_text(encoding="utf-8"))["selected"]
    source = _load_source()
    base_doc = copy.deepcopy(doc)
    for track in base_doc["tracks"]:
        track["singer"] = "YousaV1.65c"

    manifest = {"round": "J7B", "evaluated_head": head,
                "worktree_clean_at_generation": True, "phrases": []}
    listening_parts = []
    for k, phrase in enumerate(picked):
        part = doc["voice_parts"][phrase["part"]]
        notes = []
        for note in part["notes"]:
            lyric = str(note.get("lyric"))
            if lyric in hb.SPECIAL_LYRICS or lyric == "+":
                continue
            start = t2s(part["position"] + note["position"])
            end = t2s(part["position"] + note["position"] + note["duration"])
            if end - WAVE_OFF > phrase["a"] \
                    and start - WAVE_OFF < phrase["b"] - 0.01:
                notes.append({"a": start, "b": end,
                              "abs_start_s": start, "dur_s": end - start,
                              "tone": int(note["tone"]), "lyric": lyric,
                              "_abs_tick": part["position"] + note["position"],
                              "_dur_tick": note["duration"], "_note": note})
        part_pos = notes[0]["_abs_tick"] - 480
        tag = f"j7b_{k}_{phrase['class']}"
        pdir = OUT / tag
        pdir.mkdir(parents=True, exist_ok=True)
        t0 = notes[0]["abs_start_s"] - 0.35
        t1 = notes[-1]["abs_start_s"] + notes[-1]["dur_s"] + 0.35
        sig_a = build_contour_signal(source["fcpe"], source["rmvpe"],
                                     notes, t0_s=t0, t1_s=t1,
                                     extractor="fcpe", source="source")
        sig_b = build_contour_signal(source["rmvpe"], source["fcpe"],
                                     notes, t0_s=t0, t1_s=t1,
                                     extractor="rmvpe", source="source")
        supported, event_audit = _dual_events(sig_a, sig_b, notes)
        pitd, porta, rules = _compile(notes, sig_a, sig_b, supported,
                                      part_pos, tick_ms)
        candidate = drv.build_phrase_doc(base_doc, part, notes, part_pos,
                                         pitd, {}, tag, porta_marks=porta)
        candidate_path = pdir / f"{tag}_cand.ustx"
        hb.save_ustx(candidate, candidate_path)
        expected = [(n["_abs_tick"] - part_pos, n["_dur_tick"], n["tone"],
                     n["lyric"]) for n in notes]
        score_identity = _score_signature(candidate["voice_parts"][0]) == expected
        if not score_identity:
            raise RuntimeError(f"{tag}: score identity changed")
        wav = drv.render(cfg, candidate_path, pdir / f"{tag}_cand")
        raw_f0, diag = _render_diag(
            wav, notes, rules["transitions"], rules["compiled_events"])
        for name, f0 in raw_f0.items():
            np.savez(pdir / f"render_f0_{name}.npz", **f0)

        neutral = Path(f"runs/huahai_benchmark/j5_{k}_{phrase['class']}"
                       f"/j5_{k}_{phrase['class']}_neutral.ustx")
        human = Path(f"runs/huahai_benchmark/j2_{k}_{phrase['class']}"
                     f"/j2_{k}_{phrase['class']}.ustx")
        abc = pdir / f"agent2utau_J7B_{phrase['class']}_ABC.ustx"
        _listening_doc(neutral, candidate_path, human, abc)
        drv._dump({"phrase": phrase["class"], "score_identity": score_identity,
                   "events": event_audit, "rules": rules},
                  pdir / "rules.json")
        drv._dump({"phrase": phrase["class"], "score_identity": score_identity,
                   "candidate_ustx": str(candidate_path),
                   "candidate_ustx_sha256": sha256(candidate_path),
                   "candidate_wav": str(wav),
                   "candidate_wav_sha256": sha256(wav), **diag},
                  pdir / "diag.json")
        manifest["phrases"].append({
            "class": phrase["class"], "dir": str(pdir),
            "score_identity": score_identity, "machine_pass": diag["machine_pass"],
            "failure_reasons": diag["failure_reasons"],
            "dof": rules["dof"], "supported_events": len(supported),
            "listening_ustx": str(abc)})
        listening_parts.append((neutral, candidate_path, human, phrase["class"]))
        print(tag, "pass=" + str(diag["machine_pass"]),
              "dof=" + str(rules["dof"]),
              "events=" + str(len(supported)), flush=True)

    combined = copy.deepcopy(base_doc)
    parts = []
    for neutral, candidate, human, cls in listening_parts:
        for track_no, path, prefix in ((0, neutral, "A0"),
                                       (1, candidate, "B"),
                                       (2, human, "C")):
            part = copy.deepcopy(load_ustx(path)["voice_parts"][0])
            part["name"] = f"{prefix}_{cls}"
            part["track_no"] = track_no
            parts.append(part)
    combined["tracks"] = _listening_tracks(load_ustx(listening_parts[0][1]))
    combined["voice_parts"] = parts
    combined_path = OUT / "agent2utau_J7B_all_ABC.ustx"
    hb.save_ustx(combined, combined_path)
    manifest["combined_listening_ustx"] = str(combined_path)
    manifest["overall_machine_pass"] = all(
        p["machine_pass"] for p in manifest["phrases"])
    drv._dump(manifest, OUT / "manifest.json")
    print("wrote", OUT / "manifest.json")


if __name__ == "__main__":
    main()
