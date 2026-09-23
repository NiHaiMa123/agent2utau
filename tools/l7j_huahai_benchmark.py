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


def transposition_evidence(doc, f0, t2s):
    """Delta (written_tone - measured_midi) over sustained sung notes."""
    times, hz, vv = f0["times"], f0["f0_hz"], f0["voiced"]
    rows = []
    for p in doc["voice_parts"]:
        for i, n in enumerate(p["notes"]):
            if str(n.get("lyric")) in SPECIAL_LYRICS \
                    or str(n.get("lyric")) == "+":
                continue
            a = t2s(p["position"] + n["position"])
            d = t2s(p["position"] + n["position"] + n["duration"]) - a
            if d < 0.30:
                continue
            m = (times >= a + 0.06) & (times <= a + d - 0.06) & vv
            if m.sum() < 5:
                continue
            rows.append({
                "part_track": p.get("track_no"),
                "t_s": round(a, 2), "tone": int(n["tone"]),
                "lyric": str(n.get("lyric")),
                "measured_midi": round(float(np.median(_midi(hz[m]))), 2),
                "voiced_frames": int(m.sum())})
    for r in rows:
        r["delta_st"] = round(r["tone"] - r["measured_midi"], 2)
    deltas = np.array([r["delta_st"] for r in rows])
    # modal bin at 0.5st resolution
    hist, edges = np.histogram(deltas, bins=np.arange(-12, 13, 0.5))
    peak_i = int(np.argmax(hist))
    mode = float((edges[peak_i] + edges[peak_i + 1]) / 2)
    near = np.abs(deltas - mode) <= 1.5
    return {"n_notes_measured": len(rows),
            "delta_mode_st": mode,
            "frac_within_1p5st_of_mode": round(float(near.mean()), 3),
            "delta_p25_p75": [round(float(np.percentile(deltas, 25)), 2),
                              round(float(np.percentile(deltas, 75)), 2)],
            "per_note": rows[:400]}


def main():
    head = drv._require_clean_worktree("l7j_huahai_benchmark")
    OUT.mkdir(parents=True, exist_ok=True)
    doc = load_ustx(HUMAN_USTX)
    info = sf.info(str(JAY_FLAC))

    t2s = tempo_map(doc)
    print("extracting vocal F0 ...", flush=True)
    f0 = extract_f0(VOCALS)
    tp = transposition_evidence(doc, f0, t2s)
    print(f"  delta mode={tp['delta_mode_st']}st "
          f"within={tp['frac_within_1p5st_of_mode']}", flush=True)

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
        "transposition_proven": bool(
            abs(tp["delta_mode_st"] - 4.0) <= 0.5
            and tp["frac_within_1p5st_of_mode"] >= 0.6),
    }
    out = OUT / "j0_inputs.json"
    out.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print("wrote", out)
    if not manifest["transposition_proven"]:
        print("WARNING: +4 transposition not proven — per contract "
              "classify UNKNOWN for note correspondence")


if __name__ == "__main__":
    main()
