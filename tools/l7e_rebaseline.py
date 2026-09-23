"""L7 Round E — 1.65c / dpV2 renderer re-baseline (attribution only).

Frozen accepted candidates, expression bytes held fixed:
    P1_sustain = C3v2
    P2_slides  = C3v2
    P3_vibrato = C3 (v1 fallback)

For each phrase this tool:
  1. copies the accepted USTX, changing ONLY the track-level singer
     identity  YousaV1.65b -> YousaV1.65c  (explicit — the 1.65b
     junction may not be used for formal evidence);
  2. proves semantic identity: a recursive diff of old vs new docs must
     differ only at  tracks[*].singer ;
  3. renders through the dpV2 bridge;
  4. measures the new render with the SAME blind-spot metrics that
     exposed the L7-E failure (tools/l7e_listening_evidence.py —
     imported, not redefined);
  5. diffs new vs the committed old-render metrics;
  6. assembles a combined OpenUtau listening project from the new
     1.65c candidate parts at their original song positions.

Forbidden by round contract: PITD regeneration, closed-loop correction,
ownership/vibrato/candidate changes, metric changes, v2/v3 substitution.

Output: runs/expr-20260921/rebaseline/
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import l7_phrase_gate as drv                          # noqa: E402
import l7e_listening_evidence as lev                  # noqa: E402
from agent2utau.analysis.f0 import extract_f0         # noqa: E402
from agent2utau.openutau.ustx import load_ustx, save_ustx, sha256  # noqa: E402
from agent2utau.openutau.bridge import run_bridge     # noqa: E402
from agent2utau.review.render import render_provenance  # noqa: E402
from agent2utau.resources.config import load_config   # noqa: E402

OUT_DIR = drv.RUN_DIR / "rebaseline"
LISTEN_TEMPLATE = drv.RUN_DIR / "listening" / \
    "agent2utau_L7E_P1_P3_P2.ustx"
LISTEN_OUT = OUT_DIR / "agent2utau_L7E_v165c_P1_P3_P2.ustx"
REPORT = OUT_DIR / "l7e_rebaseline_report.json"
OLD_EVIDENCE = drv.RUN_DIR / "listening" / "l7e_listening_evidence.json"

OLD_SINGER = "YousaV1.65b"
NEW_SINGER = "YousaV1.65c"


def _diff(a, b, path=""):
    """Recursive structural diff; returns list of differing leaf paths."""
    diffs = []
    if type(a) is not type(b):
        return [path or "<root>"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            ka, kb = k in a, k in b
            if ka and kb:
                diffs += _diff(a[k], b[k], f"{path}.{k}")
            else:
                diffs.append(f"{path}.{k}({'only ' +
                            ('old' if ka else 'new')})")
    elif isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}.len({len(a)}!={len(b)})")
        for i, (x, y) in enumerate(zip(a, b)):
            diffs += _diff(x, y, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        if a != b:
            diffs.append(f"{path}({a!r}!={b!r})")
    elif a != b:
        diffs.append(f"{path}({a!r}!={b!r})")
    return diffs


def make_v165c_copy(old_path, new_path):
    """Copy accepted USTX with only tracks[*].singer migrated."""
    doc = load_ustx(old_path)
    new = copy.deepcopy(doc)
    touched = []
    for i, tr in enumerate(new.get("tracks", [])):
        if tr.get("singer") == OLD_SINGER:
            tr["singer"] = NEW_SINGER
            touched.append(f"tracks[{i}].singer")
    if not touched:
        raise RuntimeError(f"{old_path}: no '{OLD_SINGER}' singer field")
    save_ustx(new, new_path)
    diffs = _diff(doc, load_ustx(new_path))
    allowed = {f"tracks[{i}].singer" for i in
               range(len(doc.get("tracks", [])))}
    unexpected = [d for d in diffs
                  if d.split("(")[0] not in allowed]
    return {"touched": touched, "unexpected_diffs": unexpected,
            "semantic_identity": not unexpected}


def build_listening_project(new_ustx_by_part):
    """Combined project: L7E template + new 1.65c voice parts."""
    doc = copy.deepcopy(load_ustx(LISTEN_TEMPLATE))
    for tr in doc.get("tracks", []):
        if tr.get("singer") == OLD_SINGER:
            tr["singer"] = NEW_SINGER
    new_parts = []
    for name in ("P1_sustain_C3", "P3_vibrato_C3", "P2_slides_C3"):
        src = new_ustx_by_part[name]
        part = copy.deepcopy(load_ustx(src)["voice_parts"][0])
        part["track_no"] = 0
        part["name"] = name
        new_parts.append(part)
    doc["voice_parts"] = new_parts
    doc["name"] = "agent2utau L7-E2 v165c re-baseline (P1,P3,P2)"
    doc["comment"] = ("same frozen candidates rendered through "
                      "YousaV1.65c + OpenUtau dpV2")
    save_ustx(doc, LISTEN_OUT)
    return LISTEN_OUT


def eval_new_render(phrase, ustx_path, wav_path, src_f0, src_wav):
    w0, w1 = drv.PHRASES[phrase]
    src_off = drv.PAD_S - w0
    f0 = extract_f0(wav_path)
    rec = {"path": str(wav_path), "sha256": sha256(wav_path)[:16],
           "jitter": lev._jitter_stats(f0, w0, w1),
           "quality": lev._quality_stats(wav_path, f0, w0, w1),
           "defects": lev._defects(wav_path, f0, w0, w1, src_f0,
                                   src_wav, src_off),
           "note_gesture_table": lev._note_gesture_table(
               ustx_path, f0, src_f0, src_off, w0)}
    return rec


def _delta_rows(old, new):
    """Old-vs-new metric deltas for the report's comparison table."""
    rows = {}
    oj, nj = old.get("jitter", {}), new.get("jitter", {})
    for k in ("dcent_med", "dcent_p90", "dcent_gt30_frac",
              "detrended_rms_c", "voiced_frac"):
        rows[f"jitter.{k}"] = {"old": oj.get(k), "new": nj.get(k)}
    oq, nq = old.get("quality", {}), new.get("quality", {})
    for k in ("acf_peak_med", "spec_flat_2_8k_med"):
        rows[f"quality.{k}"] = {"old": oq.get(k), "new": nq.get(k)}
    od, nd = old.get("defects", {}), new.get("defects", {})
    for k in ("pitch_dips_gt300c", "unvoiced_dropouts",
              "energy_collapses"):
        rows[f"defects.{k}"] = {"old": od.get(k), "new": nd.get(k),
                                "old_count": len(od.get(k) or []),
                                "new_count": len(nd.get(k) or [])}
    og = {r["note"]: r for r in old.get("note_gesture_table") or []}
    ng = {r["note"]: r for r in new.get("note_gesture_table") or []}
    grows = []
    for i in sorted(set(og) | set(ng)):
        o, n = og.get(i, {}), ng.get(i, {})
        grows.append({"note": i, "t_s": n.get("t_s", o.get("t_s")),
                      "offset_c": {"old": o.get("offset_c"),
                                   "new": n.get("offset_c")},
                      "range_ratio": {"old": o.get("range_ratio"),
                                      "new": n.get("range_ratio")}})
    rows["note_gesture_table"] = grows
    return rows


def main():
    head = drv._require_clean_worktree("l7e_rebaseline")
    cfg = load_config()
    ou = Path(cfg["openutau_dir"])
    print(f"env: {ou} / singer {cfg.get('default_singer')}", flush=True)
    assert ou.is_dir() and "dpV2" in str(ou), \
        f"openutau_dir does not resolve to dpV2 build: {ou}"
    assert cfg.get("default_singer") == NEW_SINGER
    bdoc = run_bridge(cfg, ["doctor"])
    prov = render_provenance(cfg)

    old_ev = json.loads(OLD_EVIDENCE.read_text(encoding="utf-8"))
    report = {
        "tool": "tools/l7e_rebaseline.py",
        "round": "L7 Round E — 1.65c/dpV2 renderer re-baseline",
        "purpose": "attribute L7-E P2/P3 listening failures to renderer "
                   "vs expression compiler; frozen candidates unchanged",
        "evaluated_head": head,
        "worktree_clean_at_generation": True,
        "environment": {
            "openutau_dir": str(ou),
            "singer": NEW_SINGER,
            "bridge_doctor": bdoc,
            "provenance": prov,
            "fork": "KakaruHayate/OpenUtau dpV2 actions build",
            "fork_commit": "not recoverable from install; binary "
                           "hashes above are the binding identity"},
        "phrases": {},
    }
    new_ustx_by_part = {}
    for phrase in drv.PHRASES:
        print(f"== {phrase}", flush=True)
        pdir = drv.PHRASE_DIR / phrase
        man = json.loads((pdir / "run_manifest.json")
                         .read_text(encoding="utf-8"))
        old_ustx = Path(man["ustx_path"])
        old_wav = Path(man["render_wav_path"])
        out_dir = OUT_DIR / phrase
        out_dir.mkdir(parents=True, exist_ok=True)
        new_ustx = out_dir / (old_ustx.stem + "_v165c.ustx")
        ident = make_v165c_copy(old_ustx, new_ustx)
        print(f"   copy -> {new_ustx.name} "
              f"(identity={ident['semantic_identity']})", flush=True)
        new_wav = drv.render(cfg, new_ustx,
                             out_dir / (old_ustx.stem + "_v165c_vocal"))
        print(f"   rendered {new_wav.name}", flush=True)
        src_wav = pdir / "SOURCE.wav"
        src_f0 = extract_f0(src_wav)
        new_rec = eval_new_render(phrase, new_ustx, new_wav,
                                  src_f0, src_wav)
        old_rec = (old_ev.get("phrases", {}).get(phrase, {})
                   .get("signals", {}).get("accepted", {}))
        report["phrases"][phrase] = {
            "old_ustx": {"path": str(old_ustx),
                         "sha256": sha256(old_ustx)},
            "new_ustx": {"path": str(new_ustx),
                         "sha256": sha256(new_ustx)},
            "old_wav": {"path": str(old_wav),
                        "sha256": sha256(old_wav)},
            "new_wav": {"path": str(new_wav),
                        "sha256": sha256(new_wav)},
            "semantic_identity": ident,
            "new_render": new_rec,
            "deltas_old_vs_new": _delta_rows(old_rec, new_rec),
        }
        doc = load_ustx(new_ustx)
        new_ustx_by_part[doc["voice_parts"][0]["name"]] = new_ustx
    lp = build_listening_project(new_ustx_by_part)
    report["listening_project"] = {
        "path": str(lp), "sha256": sha256(lp),
        "parts": sorted(new_ustx_by_part)}
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"wrote {REPORT}", flush=True)


if __name__ == "__main__":
    main()
