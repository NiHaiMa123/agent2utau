"""L7 Round J J7A — low-DOF rule-based pitch drawing trial.

Single bounded experiment (plan J7.14): one implementation, one
benchmark generation, one real render, one diagnostic eval, STOP.

Design (J7.2-J7.11):
- trusted note scaffold = human +4 project phrase notes (same 5
  benchmark phrases as J2/J5 so A/B/C/D layers already exist);
- SOURCE = committed corpus Kim_Vocal_2 stem FCPE+RMVPE, transposed
  +4st onto the written frame, shifted to the project axis; a frame
  counts only when both families agree within 50c;
- per-note low-DOF evidence only: bounded core offset (+-50c),
  constant/linear body, coherent onset/tail gestures, per-cycle
  vibrato measurement (rate+depth envelope), Baishuo-style
  pitch.data entry init for contiguous leaps;
- PITD is the sole curve carrier; knots are structural (gesture
  extrema + trend ends + vibrato extrema), never a 10ms residual.

Outputs per phrase: rule JSON, candidate USTX, real render WAV,
render F0 (fcpe+rmvpe), diagnostic JSON, A/B listening USTX
(part0 = GAME/base neutral, part1 = J7 candidate).

Requires clean git worktree.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import l7_phrase_gate as drv                          # noqa: E402
import l7j_huahai_benchmark as hb                     # noqa: E402
from agent2utau.analysis.f0 import extract_f0         # noqa: E402
from agent2utau.analysis.rmvpe import infer_rmvpe     # noqa: E402
from agent2utau.openutau.ustx import (                # noqa: E402
    load_ustx, sha256)
from agent2utau.resources.config import load_config   # noqa: E402

CORPUS = Path("runs/huahai_corpus")
OUT = Path("runs/huahai_j7")
WAVE_OFF = 1.29
CONSENSUS_ST = 0.5          # both extractor families within 50c
CORE_GUARD_C = 50.0         # J7 experimental pitch-centre guardrail
ONSET_MIN_C = 80.0          # onset/tail gesture minimum extremum
TREND_MIN_C = 60.0          # sustained slope needed for linear body
VIB_MIN_DUR_S = 0.7
VIB_MIN_CYCLES = 3
VIB_MIN_DEPTH_C = 40.0
PAD_S = 0.30


def _midi(hz):
    return 69.0 + 12.0 * np.log2(np.maximum(hz, 1e-6) / 440.0)


def _load_src():
    f0s = {}
    for name in ("fcpe", "rmvpe"):
        z = np.load(CORPUS / "source"
                    / f"jay_source_f0_kim_vocal_2_{name}.npz")
        f0s[name] = {"times": z["times"] + WAVE_OFF,
                     "midi": _midi(z["f0_hz"]) + 4.0,
                     "voiced": z["voiced"].astype(bool)}
    return f0s


def _consensus(f0s, a, b):
    """Consensus sample points in [a,b] (project s). Returns
    (times, rel_cents_per_tone_placeholder midi) — caller subtracts
    the note tone."""
    t1, m1, v1 = (f0s["fcpe"][k] for k in ("times", "midi", "voiced"))
    t2, m2, v2 = (f0s["rmvpe"][k] for k in ("times", "midi", "voiced"))
    sel1 = v1 & (t1 >= a) & (t1 <= b)
    tt = t1[sel1]
    mm1 = m1[sel1]
    mm2 = np.interp(tt, t2[v2], m2[v2]) if v2.any() \
        else np.full(tt.shape, np.nan)
    ok = np.isfinite(mm2) & (np.abs(mm1 - mm2) <= CONSENSUS_ST)
    return tt[ok], (mm1[ok] + mm2[ok]) / 2.0


def _note_evidence(tt, mm, a, b, tone):
    """Low-DOF evidence for one note. All times project s; rel cents
    vs written tone."""
    if tt.size == 0:
        return {"reliable": False}
    rel = (mm - tone) * 100.0
    dur = b - a
    m0 = max(0.12, 0.2 * dur)
    core = (tt >= a + m0) & (tt <= b - m0)
    core_rel = rel[core]
    core_t = tt[core]
    ev = {"reliable": bool(core_rel.size >= 5),
          "n_consensus": int(tt.size),
          "core_coverage": float(core.sum() / max(tt.size, 1))}
    if core_rel.size >= 5:
        core_off = float(np.median(core_rel))
        ev["core_off_c"] = round(core_off, 1)
        # linear body trend inside the core
        A = np.vstack([core_t - core_t.mean(),
                       np.ones(core_t.size)]).T
        slope, off = np.linalg.lstsq(A, core_rel, rcond=None)[0]
        ev["trend_slope_c_s"] = round(float(slope), 1)
        ev["trend_span_c"] = round(float(slope) *
                                   (core_t.max() - core_t.min()), 1)
    # onset gesture: consensus median in first 150ms
    om = tt < min(a + 0.15, a + 0.35 * dur)
    if om.sum() >= 5 and ev.get("core_off_c") is not None:
        onset = float(np.median(rel[om])) - ev["core_off_c"]
        ev["onset_extremum_c"] = round(onset, 1)
        ev["onset_n"] = int(om.sum())
    # tail gesture: consensus median in last 150ms
    sm = tt > max(b - 0.15, b - 0.35 * dur)
    if sm.sum() >= 5 and ev.get("core_off_c") is not None:
        tail = float(np.median(rel[sm])) - ev["core_off_c"]
        ev["tail_extremum_c"] = round(tail, 1)
        ev["tail_n"] = int(sm.sum())
    return ev


def _vibro_evidence(tt, mm, a, b, tone, core_off, slope):
    """Per-cycle vibrato measurement on detrended consensus signal."""
    dur = b - a
    if dur < VIB_MIN_DUR_S or tt.size < 40:
        return None
    rel = (mm - tone) * 100.0
    detr = rel - (core_off + slope * (tt - (a + b) / 2.0))
    # restrict to the middle 80% so onset/tail gestures don't pollute
    mid = (tt >= a + 0.1 * dur) & (tt <= b - 0.1 * dur)
    t_m, d_m = tt[mid], detr[mid]
    if t_m.size < 30:
        return None
    sg = np.sign(d_m)
    zx = np.where(np.diff(sg) != 0)[0]
    if zx.size < 2 * VIB_MIN_CYCLES:
        return None
    # cycles between every other zero crossing
    cycles = []
    for i in range(0, zx.size - 2, 2):
        t_a, t_b = t_m[zx[i]], t_m[zx[i + 2]]
        seg = d_m[zx[i]:zx[i + 2] + 1]
        seg_t = t_m[zx[i]:zx[i + 2] + 1]
        if seg.size < 4:
            continue
        depth = (seg.max() - seg.min()) / 2.0
        cycles.append({"t0": float(t_a), "t1": float(t_b),
                       "period_ms": float(1000 * (t_b - t_a)),
                       "depth_c": float(depth),
                       "t_max": float(seg_t[np.argmax(seg)]),
                       "y_max": float(seg.max()),
                       "t_min": float(seg_t[np.argmin(seg)]),
                       "y_min": float(seg.min())})
    if len(cycles) < VIB_MIN_CYCLES:
        return None
    periods = np.array([c["period_ms"] for c in cycles])
    depths = np.array([c["depth_c"] for c in cycles])
    rate = 1000.0 / float(np.median(periods))
    if not (3.5 <= rate <= 10.0) or np.median(depths) < VIB_MIN_DEPTH_C:
        return None
    # depth envelope: linear fit over cycle index
    xs = np.arange(len(cycles))
    A = np.vstack([xs, np.ones(len(xs))]).T
    d_slope, d_off = np.linalg.lstsq(A, depths, rcond=None)[0]
    return {"n_cycles": len(cycles),
            "rate_hz": round(rate, 2),
            "depth_med_c": round(float(np.median(depths)), 1),
            "depth_first3": round(float(depths[:3].mean()), 1),
            "depth_last3": round(float(depths[-3:].mean()), 1),
            "depth_slope_per_cycle": round(float(d_slope), 1),
            "cycles": [{k: (round(v, 3) if isinstance(v, float) else v)
                        for k, v in c.items() if k != "t0"
                        and k != "t1"}
                       | {"t0": round(c["t0"], 3),
                          "t1": round(c["t1"], 3)} for c in cycles]}


def _compile_note(i, note, prev, nxt, ev, vib, ms_tick):
    """Compile one note to (knots, pitch_data_or_None, rule_rec).
    knots = [(project_s, rel_cents)]."""
    a, b, tone = note["a"], note["b"], note["tone"]
    dur = b - a
    knots, rec = [], {"note": note["lyric"], "span_s": [round(a, 3),
                    round(b, 3)], "tone": tone, "dof": 0, "classes": []}
    core_off = 0.0
    slope = 0.0
    if ev.get("reliable"):
        core_off = float(np.clip(ev.get("core_off_c", 0.0),
                                 -CORE_GUARD_C, CORE_GUARD_C))
        rec["classes"].append("core_offset")
        rec["core_off_c"] = core_off
        span = ev.get("trend_span_c", 0.0)
        if abs(span) >= TREND_MIN_C:
            slope = ev["trend_slope_c_s"]
            rec["classes"].append("linear_body")
            rec["body_slope_c_s"] = slope
    # body knot times
    m0 = max(0.12, 0.2 * dur)
    c0, c1 = a + m0, b - m0
    mid_t = (a + b) / 2.0

    def body_at(t):
        return core_off + slope * (t - mid_t)
    # onset gesture
    if ev.get("onset_extremum_c") is not None \
            and abs(ev["onset_extremum_c"]) >= ONSET_MIN_C:
        ext = core_off + ev["onset_extremum_c"]
        knots.append((a, ext))
        knots.append((min(a + 0.14, c0), body_at(a + 0.14)))
        rec["classes"].append("onset_gesture")
        rec["onset_c"] = round(ext, 1)
    # vibrato (long notes only)
    if vib is not None and dur >= VIB_MIN_DUR_S:
        rec["classes"].append("vibrato_pitd_extrema")
        rec["vibrato"] = {k: vib[k] for k in
                          ("rate_hz", "depth_med_c", "depth_first3",
                           "depth_last3", "n_cycles")}
        for c in vib["cycles"]:
            knots.append((c["t_max"],
                          body_at(c["t_max"]) + c["y_max"]))
            knots.append((c["t_min"],
                          body_at(c["t_min"]) + c["y_min"]))
    # body knots (always needed to anchor the trend)
    knots.append((c0, body_at(c0)))
    knots.append((c1, body_at(c1)))
    # tail gesture
    if ev.get("tail_extremum_c") is not None \
            and abs(ev["tail_extremum_c"]) >= ONSET_MIN_C:
        knots.append((b - 0.02, core_off + ev["tail_extremum_c"]))
        rec["classes"].append("tail_gesture")
        rec["tail_c"] = round(core_off + ev["tail_extremum_c"], 1)
    # pitch.data init for contiguous leap (Baishuo convention)
    pitch = None
    if prev is not None:
        leap = tone - prev["tone"]
        gap = a - prev["b"]
        if leap != 0 and gap < 0.08:
            pitch = {"data": [{"x": -40, "y": int(-10 * leap),
                               "shape": "io"},
                              {"x": 0, "y": 0, "shape": "io"}],
                     "snap_first": True}
            rec["classes"].append("pitch_data_entry_init")
            rec["entry_y0"] = -10 * leap
    knots.sort(key=lambda k: k[0])
    rec["dof"] = len(knots) + (2 if pitch else 0)
    return knots, pitch, rec


def _render_diag(wav, notes, wave_off, ms_tick, evs):
    """Render F0 (audio axis) -> per-note quick stats + global flags."""
    out = {"fcpe": None, "rmvpe": None, "notes": []}
    for name, fn in (("fcpe", extract_f0), ("rmvpe", infer_rmvpe)):
        f0 = fn(wav)
        out[name] = {"times": (np.asarray(f0["times"]) - wave_off),
                     "midi": _midi(np.asarray(f0["f0_hz"])),
                     "voiced": np.asarray(f0["voiced"], dtype=bool)}
    # cross-extractor consistency on jointly-voiced frames
    a_, b_ = out["fcpe"], out["rmvpe"]
    m2 = np.interp(a_["times"], b_["times"][b_["voiced"]],
                   b_["midi"][b_["voiced"]]) if b_["voiced"].any() \
        else np.full(a_["times"].shape, np.nan)
    both = a_["voiced"] & np.isfinite(m2)
    d = np.abs(a_["midi"] - m2) * 100
    out["cross_extractor"] = {
        "med_abs_delta_c": round(float(np.median(d[both])), 1)
        if both.any() else None,
        "p95_abs_delta_c": round(float(np.percentile(d[both], 95)), 1)
        if both.any() else None}
    # global defect flags on the fcpe track
    t, mm, vv = a_["times"], a_["midi"], a_["voiced"]
    d1 = np.abs(np.diff(mm[vv])) * 100
    spikes = int(np.sum(d1 > 300)) if d1.size else 0
    out["flags"] = {"f0_spikes_gt300c": spikes,
                    "voiced_frac": round(float(vv.mean()), 3)}
    for i, n in enumerate(notes):
        sel = vv & (t >= n["a"] - wave_off + 0.02) \
            & (t <= n["b"] - wave_off - 0.02)
        rc = mm[sel] * 100 - n["tone"] * 100.0
        row = {"note": n["lyric"],
               "render_rng_c": (round(float(np.percentile(rc, 95)
                                          - np.percentile(rc, 5)), 1)
                                if rc.size > 8 else None)}
        ev = evs[i] if i < len(evs) else {}
        src_rng = ev.get("src_rng_c")
        row["src_rng_c"] = src_rng
        row["rng_ratio"] = (round(row["render_rng_c"] / src_rng, 2)
                            if row["render_rng_c"] and src_rng else None)
        out["notes"].append(row)
    return out


def main():
    head = drv._require_clean_worktree("l7j7_rules")
    cfg = load_config()
    OUT.mkdir(parents=True, exist_ok=True)
    doc = load_ustx(hb.HUMAN_USTX)
    t2s = hb.tempo_map(doc)
    tempos = doc.get("tempos") or [{"bpm": 75}]
    ms_tick = 60000.0 / (tempos[0]["bpm"] * 480.0)
    picked = json.loads((hb.OUT / "j1_phrases.json")
                        .read_text(encoding="utf-8"))["selected"]
    f0s = _load_src()
    base_doc = copy.deepcopy(doc)
    for tr in base_doc["tracks"]:
        tr["singer"] = "YousaV1.65c"

    manifest = {"evaluated_head": head,
                "worktree_clean_at_generation": True,
                "phrases": []}
    for k, ph in enumerate(picked):
        a, b = ph["a"], ph["b"]
        part = doc["voice_parts"][ph["part"]]
        notes = []
        for n in part["notes"]:
            lyr = str(n.get("lyric"))
            if lyr in hb.SPECIAL_LYRICS or lyr == "+":
                continue
            s_p = t2s(part["position"] + n["position"])
            e_p = t2s(part["position"] + n["position"]
                      + n["duration"])
            if s_p - WAVE_OFF >= a - 1e-3 \
                    and e_p - WAVE_OFF <= b + 1e-3:
                notes.append({"a": s_p, "b": e_p, "tone": n["tone"],
                              "lyric": lyr,
                              "_abs_tick": part["position"]
                              + n["position"],
                              "_dur_tick": n["duration"], "_note": n})
        part_pos = notes[0]["_abs_tick"] - 480
        tag = f"j7_{k}_{ph['class']}"
        pdir = OUT / tag
        pdir.mkdir(parents=True, exist_ok=True)
        print(f"== {ph['class']} {len(notes)} notes", flush=True)

        # per-note evidence + compile
        evs, all_knots, porta, recs = [], [], {}, []
        for i, n in enumerate(notes):
            tt, mm = _consensus(f0s, n["a"] - 0.05, n["b"] + 0.05)
            inote = (tt >= n["a"]) & (tt <= n["b"])
            ev = _note_evidence(tt[inote], mm[inote],
                                n["a"], n["b"], n["tone"])
            if tt.size:
                rel_all = (mm - n["tone"]) * 100
                ev["src_rng_c"] = round(
                    float(np.percentile(rel_all, 95)
                          - np.percentile(rel_all, 5)), 1)
            core_off = float(np.clip(ev.get("core_off_c", 0.0),
                                     -CORE_GUARD_C, CORE_GUARD_C))
            slope = ev["trend_slope_c_s"] \
                if abs(ev.get("trend_span_c", 0)) >= TREND_MIN_C else 0.0
            vib = _vibro_evidence(tt[inote], mm[inote], n["a"], n["b"],
                                  n["tone"], core_off, slope) \
                if ev.get("reliable") else None
            prev = notes[i - 1] if i else None
            knots, pitch, rec = _compile_note(i, n, prev, None, ev,
                                            vib, ms_tick)
            if pitch is not None:
                porta[i] = pitch
            all_knots += knots
            evs.append(ev)
            recs.append(rec)
        (pdir / "rules.json").write_text(json.dumps(
            {"phrase": ph["class"], "evaluated_head": head,
             "evidence": evs, "notes": recs},
            indent=1, ensure_ascii=False), encoding="utf-8")

        # knots (project s) -> pitd curve (part-relative ticks)
        xs = np.round(np.array([k0 for k0, _ in all_knots])
                      * 1000.0 / ms_tick - part_pos).astype(int)
        ys = np.clip(np.round(np.array([k1 for _, k1 in all_knots])),
                     -1150, 1150).astype(int)
        o = np.argsort(xs, kind="stable")
        xs, ys = xs[o], ys[o]
        keep = np.concatenate([[True], np.diff(xs) > 0])
        pitd = {"abbr": "pitd", "xs": xs[keep].tolist(),
                "ys": ys[keep].tolist()}
        cand = drv.build_phrase_doc(base_doc, part, notes, part_pos,
                                    pitd, {}, tag + "_cand",
                                    porta_marks=porta)
        custx = pdir / (tag + "_cand.ustx")
        hb.save_ustx(cand, custx)
        cwav = drv.render(cfg, custx, pdir / (tag + "_cand"))
        # A baseline = the J5 neutral render of the same notes
        neut_ustx = Path(f"runs/huahai_benchmark/j5_{k}_{ph['class']}"
                         f"/j5_{k}_{ph['class']}_neutral.ustx")
        neut_wav = Path(f"runs/huahai_benchmark/j5_{k}_{ph['class']}"
                        f"/j5_{k}_{ph['class']}_neutral_main.wav")
        # A/B listening ustx: part0 neutral, part1 candidate, same pos
        ndoc = load_ustx(neut_ustx)
        cdoc = load_ustx(custx)
        ab = copy.deepcopy(cdoc)
        pa = copy.deepcopy(ndoc["voice_parts"][0])
        pb = copy.deepcopy(cdoc["voice_parts"][0])
        pa["name"] = "A_neutral_base"; pb["name"] = "B_j7_rules"
        pa["track_no"] = 0; pb["track_no"] = 1
        ab["voice_parts"] = [pa, pb]
        ab_ustx = pdir / f"agent2utau_J7_{ph['class']}_AB.ustx"
        hb.save_ustx(ab, ab_ustx)

        diag = _render_diag(cwav, notes, WAVE_OFF, ms_tick, evs)
        for name in ("fcpe", "rmvpe"):
            sig = diag.pop(name)
            np.savez(pdir / f"render_f0_{name}.npz",
                     times=sig["times"], midi=sig["midi"],
                     voiced=sig["voiced"])
        (pdir / "diag.json").write_text(json.dumps(drv._jsonable(
            {"phrase": ph["class"], "candidate_wav": str(cwav),
             "candidate_wav_sha256": sha256(cwav),
             "candidate_ustx_sha256": sha256(custx),
             "baseline_wav": str(neut_wav),
             "baseline_ustx": str(neut_ustx), **diag}),
            indent=1, ensure_ascii=False), encoding="utf-8")
        dof = [r["dof"] for r in recs]
        manifest["phrases"].append({
            "class": ph["class"], "dir": str(pdir),
            "dof_per_note": dof,
            "flags": diag["flags"],
            "cross_extractor": diag["cross_extractor"],
            "ab_listening_ustx": str(ab_ustx)})
        print(f"   dof={dof} spikes="
            f"{diag['flags']['f0_spikes_gt300c']}", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(
        manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT / "manifest.json")


if __name__ == "__main__":
    main()
