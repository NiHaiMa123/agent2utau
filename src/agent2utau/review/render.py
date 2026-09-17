"""Local review-package IO + OpenUtau render (§6.7-§6.12).

Everything here touches real files/audio and is only exercised on the
local OpenUtau machine — CI unit tests cover `build.py`/`decisions.py`.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .build import (IDENTITY_SCHEMA, REVIEW_SCHEMA, apply_patch,
                    audio_package_hash, collect_review_items,
                    find_silences, plan_batch, render_profile,
                    render_profile_hash)
from .decisions import (SEMANTICS_CANDIDATE, ReviewLog,
                        current_valid_decision, expected_item_id,
                        load_packages, rebuild_state, register_package,
                        regeneration_queue)


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _jwrite(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False),
                    encoding="utf-8")


# ------------------------------------------------------------------ loading

def load_run(run_dir: Path) -> dict:
    """Load everything a review batch needs from a finished diagnostic run."""
    from ..analysis.align import load_lrc
    from ..analysis.lyrics import find_lyrics
    import numpy as np

    run_dir = Path(run_dir)
    diag = run_dir / "diagnostic"
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    packets = json.loads((diag / "residual_triage.json")
                         .read_text(encoding="utf-8"))
    baseline = json.loads((diag / "baseline_game.json")
                          .read_text(encoding="utf-8"))["notes"]
    src = Path(report["source"])
    cache_key = report["cache"]["key"]
    cache = run_dir.parent / "_cache" / cache_key
    sep = json.loads((cache / "separation.json").read_text(encoding="utf-8"))
    f0 = np.load(diag / "rmvpe_f0.npz")

    import soundfile as sf
    duration = sf.info(str(cache / "original.wav")).duration

    lrc_hit = find_lyrics(src)
    lrc_lines = load_lrc(str(lrc_hit[0])) if lrc_hit else []

    chars = []
    adir = diag / "alignment"
    if adir.is_dir():
        for f in sorted(adir.glob("line_*.json")):
            chars += json.loads(f.read_text(encoding="utf-8"))["chars"]
    chars.sort(key=lambda c: c["start"])

    return {
        "run_dir": run_dir, "run_id": run_dir.name, "report": report,
        "source": src, "song_sha256": report["cache"]["source_sha256"],
        "packets": packets,
        "packets_by_id": {p["id"]: p for p in packets},
        "baseline_notes": baseline,
        "candidate0_sha256": _sha_notes(baseline),
        "duration": duration,
        "lrc_lines": lrc_lines,
        "silences": find_silences(f0["times"], f0["voiced"]),
        "chars": chars,
        "original_wav": cache / "original.wav",
        "vocals_wav": Path(sep["vocals"]),
    }


def _sha_notes(notes) -> str:
    from .build import sha
    return sha(notes)


# ------------------------------------------------------------------- lyrics

def lyric_map(notes, chars):
    """Note → lyric char (§6.9). Context notes get their aligned char;
    split continuations '+'; merged notes take the first parent's char;
    unmatched notes fall back to the same neutral 'a' on every option."""
    def char_at(t):
        best, bd = None, 0.30
        for c in chars:
            d = 0.0 if c["start"] <= t <= c["end"] else \
                min(abs(c["start"] - t), abs(c["end"] - t))
            if d < bd:
                best, bd = c["char"], d
        return best or "a"

    out = []
    for n in notes:
        if n.get("split_child") is not None:
            out.append(n["lyric_char"] if n.get("lyric_char") else "+")
        elif n["id"].endswith("__merged__"):
            out.append(n.get("lyric_char") or char_at(n["start"]))
        else:
            out.append(char_at((n["start"] + n["end"]) / 2.0))
    return out


def option_notes(item, option, chars):
    """Final render note list for one option (context + score_patch)."""
    patched = apply_patch(item["context"], option["score_patch"])
    # first split child inherits the parent's lyric char
    parent_char = None
    for n in item["context"]:
        if n["id"] in (option["score_patch"].get("note_ids") or []):
            mid = (n["start"] + n["end"]) / 2.0
            parent_char = next(
                (c["char"] for c in chars
                 if c["start"] <= mid <= c["end"]), None)
    first = True
    for n in patched:
        if n.get("split_child") is not None:
            n["lyric_char"] = parent_char if first else "+"
            first = False
    lyrics = lyric_map(patched, chars)
    s = item["phrase"]["start"]
    return [{"lyric": lyr, "start": n["start"] - s, "end": n["end"] - s,
             "dur": n["end"] - n["start"], "tone": int(round(n["tone"]))}
            for n, lyr in zip(patched, lyrics)]


def region_signature(notes):
    """Rounded identity+pitch+timing signature for render dedupe (§6.6)."""
    return sorted((round(n["start"], 3), round(n["end"], 3),
                   int(round(n["tone"]))) for n in notes)


# ------------------------------------------------------------------- render

def _clip(src: Path, dst: Path, t0, t1):
    import soundfile as sf
    dst.parent.mkdir(parents=True, exist_ok=True)
    info = sf.info(str(src))
    a, b = int(t0 * info.samplerate), int(t1 * info.samplerate)
    data, sr = sf.read(str(src), start=a, stop=b,
                       dtype="float32", always_2d=True)
    peak = float(abs(data).max()) if data.size else 0.0
    gain = min(1.0, 0.95 / peak) if peak > 0 else 1.0
    sf.write(str(dst), data * gain, sr, subtype="PCM_16")
    return {"path": dst.name, "sha256": _file_sha(dst),
            "gain_db": round(20 * __import__("math").log10(max(gain, 1e-9)), 2),
            "sample_rate": sr}


def render_item(cfg, item_dir, item, chars, timeout_min=10):
    """Render all options of one item fairly (§6.10). Returns manifest
    render results {option_id: {wav_sha256,...}}."""
    import numpy as np
    import soundfile as sf
    from ..openutau.build import build_project
    from ..openutau.bridge import run_bridge

    item_dir.mkdir(parents=True, exist_ok=True)
    phrase_len = item["phrase"]["end"] - item["phrase"]["start"]
    raw = {}
    for opt in item["options"]:
        oid = opt["option_id"]
        notes = option_notes(item, opt, chars)
        ustx = item_dir / f"{oid}.ustx"
        build_project(f"review_{item['item_id']}_{oid}",
                      [{"notes": notes, "start_sec": 0.0,
                        "part_start_sec": 0.0}], ustx)
        wav_tmp = item_dir / f"{oid}.raw.wav"
        try:
            br = run_bridge(cfg, ["render", "--project", str(ustx),
                                  "--out", str(wav_tmp),
                                  "--timeout", str(timeout_min)],
                            timeout=timeout_min * 60 + 120)
            produced = [f["path"] for f in br.get("files", [])
                        if f["path"].lower().endswith(".wav")]
            wav = Path(produced[0]) if produced else None
            if not br.get("ok") or wav is None or not wav.exists():
                raise RuntimeError(
                    f"bridge render failed: {str(br)[:200]}")
            data, sr = sf.read(str(wav), dtype="float32", always_2d=True)
        except Exception as e:  # render failure must not kill the batch
            raw[oid] = {"error": str(e)[:300]}
            continue
        need = int(round(phrase_len * sr))
        if data.shape[0] < need:                      # pad tail silence
            data = np.vstack(
                [data, np.zeros((need - data.shape[0], data.shape[1]),
                                dtype=np.float32)])
        else:                                          # exact same end
            data = data[:need]
        raw[oid] = {"data": data, "sr": sr}
        wav.unlink(missing_ok=True)

    # ONE shared gain across every option of the item (§6.10)
    peak = max((float(abs(r["data"]).max()) for r in raw.values()
                if "data" in r), default=0.0)
    gain = min(1.0, 0.95 / peak) if peak > 0 else 1.0
    results = {}
    for oid, r in raw.items():
        if "data" not in r:
            results[oid] = r
            continue
        out = item_dir / f"{oid}.wav"
        sf.write(str(out), r["data"] * gain, r["sr"], subtype="PCM_16")
        results[oid] = {"wav": out.name, "wav_sha256": _file_sha(out),
                        "sample_rate": r["sr"], "frames": int(r["data"].shape[0])}
    return {"shared_gain_db": round(20 * __import__("math").log10(max(gain, 1e-9)), 2),
            "options": results}


# ------------------------------------------------------------------ package

def render_provenance(cfg):
    """Real render provenance for audio_package_hash (§6.1): the actual
    OpenUtau/bridge executables and the voicebank's material files
    (acoustic/duration/pitch/variance/vocoder models, dsconfig, phonemes,
    speaker embeddings) — bytes, not logical names."""
    ou = Path(cfg["openutau_dir"])
    singer = ou / "Singers" / cfg.get("default_singer", "YousaV1.65b")
    bins = {}
    for f in (ou / "OpenUtau.exe", ou / "OpenUtau.Core.dll",
              ou / "a2u-bridge.exe"):
        if f.exists():
            bins[f.name] = {"sha256": _file_sha(f),
                            "size": f.stat().st_size}
    materials = {}
    if singer.is_dir():
        for f in sorted(singer.rglob("*")):
            rel = str(f.relative_to(singer))
            if not f.is_file() or "image" in f.parts or \
                    "LISENCES" in f.parts:
                continue
            if f.suffix.lower() in (".onnx", ".yaml", ".json", ".emb",
                                    ".txt"):
                materials[rel] = _file_sha(f)
    return {"openutau_dir": str(ou), "binaries": bins,
            "voicebank": {"singer": singer.name, "materials": materials},
            "phonemizer": "OpenUtau.Core.DiffSinger."
                          "DiffSingerChinesePhonemizer",
            "impl": REVIEW_SCHEMA}


def assess_package(man) -> str:
    """Reviewability gate (§6.1): a package is only reviewable when every
    source clip and every option rendered successfully with recorded
    hashes and a uniform sample rate / phrase length."""
    if not man.get("audio_package_hash"):
        return "unrendered"
    srcs = man.get("source_reference") or {}
    if any(not (srcs.get(k) or {}).get("sha256")
           for k in ("original_mix", "separated_vocal")):
        return "invalid"
    rates, frames = set(), set()
    for o in man["options"]:
        if o.get("render_error") or not o.get("wav") or \
                not o.get("wav_sha256"):
            return "invalid"
        rates.add(o.get("sample_rate"))
        frames.add(o.get("frames"))
    if len(rates) > 1 or len(frames) > 1:
        return "invalid"
    return "valid"


def verify_package(man, item_dir: Path) -> tuple[bool, str]:
    """Decide-time re-verification: files must still exist, match the
    recorded sha256, AND the recorded audio_package_hash must recompute
    identically from the revalidated bytes + plan_hash + provenance —
    a package whose audio or provenance changed or vanished is not
    reviewable even if its manifest claims otherwise (§6.7)."""
    if assess_package(man) != "valid":
        return False, f"package_state={assess_package(man)}"
    item_dir = Path(item_dir)
    wavs = {}
    for o in man["options"]:
        w = item_dir / o["wav"]
        if not w.exists():
            return False, f"missing {o['wav']}"
        h = _file_sha(w)
        if h != o["wav_sha256"]:
            return False, f"hash mismatch {o['wav']}"
        wavs[o["option_id"]] = {"wav_sha256": h}
    srcs = {}
    for k, ref in (man.get("source_reference") or {}).items():
        w = (item_dir / ref["path"]).resolve()
        if not w.exists():
            return False, f"missing source {k}"
        h = _file_sha(w)
        if h != ref["sha256"]:
            return False, f"hash mismatch source {k}"
        srcs[k] = {"sha256": h}
    aph = audio_package_hash(man.get("plan_hash"), srcs, wavs,
                             man.get("render_provenance"))
    if aph != man.get("audio_package_hash"):
        return False, "audio_package_hash recompute mismatch"
    return True, "ok"


def item_manifest(run, item, batch_id, rph, source_refs,
                  render_results=None, provenance=None):
    """Schema-bound per-item manifest (§6.12)."""
    p0 = run["packets_by_id"][item["packets"][0]]
    b = p0.get("pitch_adjudication") or {}
    c = p0.get("structure_adjudication") or {}
    opts = []
    for o in item["options"]:
        r = (render_results or {}).get("options", {}).get(o["option_id"], {})
        opts.append({"option_id": o["option_id"],
                     "candidate_id": o["candidate_id"],
                     "score_patch": o["score_patch"],
                     "provenance": o["provenance"],
                     "wav": r.get("wav"), "wav_sha256": r.get("wav_sha256"),
                     "sample_rate": r.get("sample_rate"),
                     "frames": r.get("frames"),
                     "render_error": r.get("error")})
    aph = audio_package_hash(item["plan_hash"], source_refs,
                             {o["option_id"]: {
                                 "wav_sha256": o["wav_sha256"]}
                              for o in opts},
                             provenance) if render_results is not None \
        else None
    man = {
        "schema": REVIEW_SCHEMA,
        "identity_schema": IDENTITY_SCHEMA,
        "review_item_id": item["item_id"],
        "target_key": item["target_key"],
        "song_sha256": run["song_sha256"],
        "diagnostic_run_id": run["run_id"],
        "review_batch_id": batch_id,
        "candidate0_sha256": run["candidate0_sha256"],
        "target_group": {k: item[k] for k in
                         ("type", "parent_ids", "note_ids", "region",
                          "packets", "reason")},
        "context": {"phrase": item["phrase"],
                    "phrase_key": item["phrase_key"],
                    "candidate0_note_ids": item["context_note_ids"]},
        "phrase": item["phrase"],
        "options": opts,
        "baseline_option": item["baseline_option"],
        "source_reference": source_refs,
        "render_profile": rph["profile"],
        "render_profile_hash": rph["hash"],
        "shared_gain_db": (render_results or {}).get("shared_gain_db"),
        "machine_evidence": {
            "pitch": {"status": b.get("status"),
                      "winning_hypothesis": b.get("winning_hypothesis"),
                      "reason": b.get("reason"),
                      "top_hypotheses": (b.get("hypotheses") or [])[:3]},
            "structure": {"status": c.get("status"),
                          "winning_hypothesis": c.get("winning_hypothesis"),
                          "boundary": c.get("boundary"),
                          "all_scores": c.get("all_scores")},
            "virtual_b": [{"id": v.get("id"), "status": v.get("status"),
                           "winning_hypothesis": v.get("winning_hypothesis")}
                          for v in p0.get("virtual_note_adjudication") or []],
            "flags": p0.get("flags") or {},
        },
        "review": {"generation": item.get("generation", 1),
                   "blinded": True,
                   "choices": ["OPTION_%d" % i for i in range(len(opts))]
                   + ["equivalent", "none_correct"]},
        "plan_hash": item["plan_hash"],
        "audio_package_hash": aph,
        "render_provenance": provenance,
    }
    man["package_state"] = assess_package(man)
    return man


def _shown_tones(manifest):
    """Tones already presented in a prior package (§6.14 dedupe)."""
    out = set()
    for o in manifest.get("options", []):
        sp = o.get("score_patch") or {}
        if sp.get("to") is not None:
            out.add(round(float(sp["to"]), 2))
        for ch in sp.get("children") or []:
            out.add(round(float(ch["tone"]), 2))
        if (sp.get("merged") or {}).get("tone") is not None:
            out.add(round(float(sp["merged"]["tone"]), 2))
    return out


def generate_batch(run_dir, cfg=None, render=True, max_items=None,
                   only_items=None, batch_id=None, progress=print,
                   gen2=None):
    run = load_run(run_dir)
    profile = render_profile(
        template_sha=_file_sha(
            Path(__file__).resolve().parents[3]
            / "configs" / "ustx_template.yaml"))
    rph = {"profile": profile, "hash": render_profile_hash(profile)}
    items = collect_review_items(run["packets"])
    if not items:
        progress("no finalized needs_phrase_review packets")
        return None
    if batch_id is None:
        batch_id = "rb-" + time.strftime("%Y%m%d-%H%M%S")
    bdir = run["run_dir"] / "review_batches" / batch_id

    planned = plan_batch(items, run["duration"], run["baseline_notes"],
                         run["lrc_lines"], run["silences"],
                         run["packets_by_id"], run["run_id"],
                         run["song_sha256"], run["candidate0_sha256"],
                         rph["hash"], max_items=max_items,
                         only_items=only_items, gen2=gen2)

    # shared phrase sources: identical windows reuse the same assets (§6.4)
    phrase_refs = {}
    for it in planned:
        phrase_refs.setdefault(it["phrase_key"], it["phrase"])

    prov = render_provenance(cfg) if render else None
    batch = {"schema": REVIEW_SCHEMA, "batch_id": batch_id,
             "run_id": run["run_id"], "created_at": time.time(),
             "song_sha256": run["song_sha256"],
             "candidate0_sha256": run["candidate0_sha256"],
             "render_profile_hash": rph["hash"],
             "items": []}

    src_rendered = {}
    for it in planned:
        pkey = it["phrase_key"]
        pdir = bdir / "phrases" / pkey
        refs = None
        if render:
            if pkey not in src_rendered:
                ph = it["phrase"]
                refs = {
                    "original_mix": _clip(
                        run["original_wav"],
                        pdir / "SOURCE_PHRASE_original_mix.wav",
                        ph["start"], ph["end"]),
                    "separated_vocal": _clip(
                        run["vocals_wav"],
                        pdir / "SOURCE_PHRASE_separated_vocal.wav",
                        ph["start"], ph["end"]),
                }
                for r in refs.values():  # self-auditing relative path
                    r["path"] = f"../../phrases/{pkey}/{r['path']}"
                src_rendered[pkey] = refs
                progress(f"  source phrase {pkey} "
                         f"({ph['end'] - ph['start']:.2f}s, "
                         f"{ph['boundary_source']})")
            else:
                refs = src_rendered[pkey]  # same assets, same hashes
        item_dir = bdir / "items" / it["item_id"]
        rres = None
        if render:
            progress(f"  rendering {it['item_id']} "
                     f"({it['type']}, {len(it['options'])} options)")
            rres = render_item(cfg, item_dir, it, run["chars"])
        man = item_manifest(run, it, batch_id, rph, refs, rres,
                            provenance=prov)
        mpath = item_dir / "manifest.json"
        _jwrite(mpath, man)
        register_package(run["run_dir"], it["item_id"], batch_id, man,
                         manifest_path=mpath)
        batch["items"].append({
            "item_id": it["item_id"], "target_key": it["target_key"],
            "type": it["type"],
            "reason": it["reason"], "phrase": it["phrase"],
            "phrase_key": pkey, "region": it["region"],
            "packets": it["packets"],
            "n_options": len(it["options"]),
            "plan_hash": it["plan_hash"],
            "audio_package_hash": man["audio_package_hash"],
            "package_state": man["package_state"]})
    _jwrite(bdir / "batch.json", batch)
    rebuild_state(run["run_dir"])
    _jwrite(run["run_dir"] / "latest_batch.json",
            {"batch_id": batch_id, "created_at": time.time(),
             "note": "convenience pointer only — runs/<diag>/review/ "
                     "is the authoritative state"})
    progress(f"batch {batch_id}: {len(planned)} items → {bdir}")
    return batch


def regenerate_batch(run_dir, cfg=None, src_batch_id=None, render=True,
                     batch_id=None, progress=print):
    """§6.14: build generation-2 packages for `none_correct` items.

    The queue comes from the run-level authoritative state
    (pending_regeneration), not from any single batch's file. Shown tones
    are excluded from new pitch candidates and phrase context widens.
    A second rejection yields manual_followup_required (ReviewLog).
    """
    run_dir = Path(run_dir)
    queue = regeneration_queue(run_dir)
    if src_batch_id:  # restrict regeneration to one batch's items
        src = json.loads((find_batch(run_dir, src_batch_id)
                          / "batch.json").read_text(encoding="utf-8"))
        allowed = {i["item_id"] for i in src["items"]}
        queue = [i for i in queue if i in allowed]
    if not queue:
        progress("no pending_regeneration items")
        return None
    from .decisions import load_packages
    pkgs = load_packages(run_dir)
    gen2, keep_packets = {}, set()
    for iid in queue:
        rec = pkgs.get(iid)
        if not rec or not rec.get("manifest"):
            continue
        man = json.loads(Path(rec["manifest"]).read_text(encoding="utf-8"))
        pid = man["target_group"]["packets"][0]
        # stable identity: the gen-2 package derives the SAME
        # review_item_id from the target — no id override needed (§6.3)
        gen2[pid] = {"generation": 2,
                     "shown_tones": _shown_tones(man)}
        keep_packets.add(pid)
    if not gen2:
        progress("queued items have no resolvable package")
        return None
    return generate_batch(run_dir, cfg=cfg, render=render,
                          only_items=list(keep_packets),
                          batch_id=batch_id,
                          progress=progress, gen2=gen2)


def find_batch(run_dir: Path, batch_id: str | None = None) -> Path:
    run_dir = Path(run_dir)
    if batch_id is None:
        ptr = run_dir / "latest_batch.json"
        batch_id = json.loads(ptr.read_text(encoding="utf-8"))["batch_id"]
    bdir = run_dir / "review_batches" / batch_id
    if not (bdir / "batch.json").exists():
        raise FileNotFoundError(f"no review batch at {bdir}")
    return bdir


def load_batch(bdir: Path):
    batch = json.loads((Path(bdir) / "batch.json").read_text(encoding="utf-8"))
    mans = {}
    for it in batch["items"]:
        mpath = Path(bdir) / "items" / it["item_id"] / "manifest.json"
        mans[it["item_id"]] = json.loads(
            mpath.read_text(encoding="utf-8"))
    return batch, mans


# ---------------------------------------------------------- M2.4 authority

def repair_authorized_decision(run_dir: Path, item_id: str):
    """§6.7 — the ONLY gate M2.4 may consume for human-selected repair.

    Returns the authoritative revision, or None unless EVERY check holds:
    d3 authority + review-target-v1 identity, semantics ==
    human_selected_candidate, current package valid, actual audio bytes
    verify, review_item_id == ri-<target_key[:16]> across decision /
    package record / manifest, identical target_key and
    audio_package_hash across all three, and complete selection
    snapshots. Anything legacy, malformed, stale or mismatched → None.
    """
    rev = current_valid_decision(run_dir, item_id)
    if not rev or rev["semantics"] != SEMANTICS_CANDIDATE:
        return None
    rec = load_packages(run_dir).get(item_id)
    if not rec or not rec.get("manifest"):
        return None
    mpath = Path(rec["manifest"])
    if not mpath.exists():
        return None
    man = json.loads(mpath.read_text(encoding="utf-8"))
    tk = rev.get("target_key")
    if not tk or rec.get("target_key") != tk or \
            man.get("target_key") != tk:
        return None
    if item_id != expected_item_id(tk) or \
            rec.get("review_item_id") != item_id or \
            man.get("review_item_id") != item_id:
        return None
    if rev["audio_package_hash"] != rec.get("audio_package_hash") or \
            rec["audio_package_hash"] != man.get("audio_package_hash"):
        return None
    ok, _ = verify_package(man, mpath.parent)
    if not ok:
        return None
    if not all(rev.get(k) for k in
               ("selected_option_id", "selected_score_patch",
                "selected_provenance", "selected_wav_sha256")):
        return None
    return rev
