"""agent2utau CLI - shared contract for all agents (docs/agent-contract.md)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .resources.config import load_config
from .util.jsonio import emit, fail, exception_payload, diag


def _out(args, payload) -> int:
    emit(payload)
    return 0 if payload.get("status") not in ("failed",) else 1


def cmd_doctor(args) -> int:
    from .resources.doctor import probe
    cfg = load_config()
    return _out(args, probe(cfg))


def cmd_inspect_reference(args) -> int:
    from .openutau.reference import inspect_reference
    return _out(args, inspect_reference(Path(args.path)))


def cmd_migrate_phrase(args) -> int:
    from .openutau.ustx import load_ustx, TempoMap
    from .openutau.migrate import select_phrase, migrate_phrase
    doc = load_ustx(args.project)
    tm = TempoMap.from_doc(doc)
    parts = doc.get("voice_parts") or []
    phrase = None
    for i, p in enumerate(parts):
        if p.get("track_no") != args.track:
            continue
        phrase = select_phrase(p, tm, part_index=i,
                               min_notes=args.min_notes,
                               min_ms=args.min_ms, max_ms=args.max_ms)
        if phrase:
            break
    if not phrase:
        return fail("no_phrase", "no suitable sung phrase found",
                    next_actions=["loosen --min-ms/--min-notes", "pick another track"])
    rep = migrate_phrase(args.project, args.out, args.track, phrase,
                         new_singer=args.singer)
    rep["status"] = "ok"
    return _out(args, rep)


def cmd_render_smoke(args) -> int:
    from .openutau.bridge import bridge_path, run_bridge
    from .evaluation.wavcheck import analyze_wav
    from .state import Run, new_run_id
    cfg = load_config()
    run = Run(Path(cfg["runs_dir"]), new_run_id("smoke"))
    run.write_state({"status": "running", "stage": "render_smoke"})
    payload: dict = {"schema_version": "1", "run_id": run.id,
                     "status": "running", "stage": "render"}
    try:
        if bridge_path(cfg) is None:
            from .openutau.bridge import deploy_bridge
            deploy_bridge(cfg)
        br = run_bridge(cfg, ["render", "--project", args.project,
                              "--out", str(run.dir / "vocal.wav"),
                              "--timeout", str(args.timeout_min)],
                        timeout=args.timeout_min * 60 + 120)
        payload["bridge"] = br
        if not br.get("ok"):
            run.write_state({"status": "failed", "stage": "render",
                             "failure_code": "render_failed"})
            payload.update(status="failed", failure_code="render_failed")
            return _out(args, payload)
        files = [f["path"] for f in br.get("files", [])]
        checks = [analyze_wav(f) for f in files]
        payload["render_checks"] = checks
        ok = all(c["non_silent"] for c in checks) and checks
        payload["status"] = "completed" if ok else "failed"
        if not ok:
            payload["failure_code"] = "silent_output"
        run.write_state({"status": payload["status"], "stage": "done",
                         "artifacts": files})
        return _out(args, payload)
    except Exception as e:
        run.write_state({"status": "failed", "stage": "render",
                         "failure_code": "internal_error"})
        emit(exception_payload(e))
        return 1


def cmd_roundtrip(args) -> int:
    from .openutau.bridge import run_bridge
    cfg = load_config()
    br = run_bridge(cfg, ["roundtrip", "--project", args.project,
                          "--out", args.out], timeout=600)
    br["status"] = "ok" if br.get("ok") else "failed"
    return _out(args, br)


def cmd_deploy_bridge(args) -> int:
    from .openutau.bridge import deploy_bridge, build_bridge
    cfg = load_config()
    out = build_bridge() if not args.no_build else None
    exe = deploy_bridge(cfg, out)
    return _out(args, {"schema_version": "1", "status": "ok",
                       "bridge": str(exe)})


def cmd_cover(args) -> int:
    from .pipeline import run_cover, parse_segments
    from .state import Run, new_run_id
    cfg = load_config()
    if not args.source:
        return fail("missing_source", "cover requires a source audio path")
    src = Path(args.source)
    if not src.exists():
        return fail("missing_source", f"source not found: {src}")
    segments = parse_segments(args.segments) if args.segments else None
    run = Run(Path(cfg["runs_dir"]), new_run_id("cover"))
    run.write_state({"status": "running", "stage": "init",
                     "source": str(src)})
    run.write_json("request.json", {
        "source": str(src), "singer": args.singer,
        "segments": args.segments, "auto_segments": args.auto_segments,
        "seg_len": args.seg_len, "lyrics": args.lyrics,
        "lines": args.lines, "asr_model": args.asr_model,
        "sep_model": args.sep_model, "timeout_min": args.timeout_min,
        "iters": args.iters, "pitch_strength": args.pitch_strength,
        "voice_color": args.voice_color, "compare_colors": args.compare_colors,
        "breaths": not args.no_breaths})
    try:
        rep = run_cover(src, run, cfg, segments=segments,
                        auto_segments=args.auto_segments,
                        seg_len=args.seg_len, asr_model=args.asr_model,
                        sep_model=args.sep_model,
                        lyrics=args.lyrics, lines=args.lines,
                        timeout_min=args.timeout_min,
                        iters=args.iters,
                        pitch_strength=args.pitch_strength,
                        voice_color=(None if args.voice_color.lower()
                                     in ("", "none") else args.voice_color),
                        compare_colors=args.compare_colors,
                        breaths=not args.no_breaths,
                        progress=lambda m: diag(f"[cover] {m}"))
        return _out(args, rep)
    except Exception as e:
        run.write_state({"status": "failed", "stage": "error",
                         "failure_code": "internal_error"})
        emit(exception_payload(e))
        return 1


def cmd_diagnose(args) -> int:
    from .diagnostic.run import run_diagnostic
    from .state import Run, new_run_id
    cfg = load_config()
    src = Path(args.source)
    if not src.exists():
        return fail("missing_source", f"source not found: {src}")
    run = Run(Path(cfg["runs_dir"]), new_run_id("diag"))
    run.write_state({"status": "running", "stage": "init",
                     "source": str(src)})
    try:
        rep = run_diagnostic(src, run, cfg, language=args.language,
                             timeout_min=args.timeout_min,
                             repeats=args.repeats,
                             progress=lambda m: diag(f"[diag] {m}"))
        return _out(args, rep)
    except Exception as e:
        run.write_state({"status": "failed", "stage": "error",
                         "failure_code": "internal_error"})
        emit(exception_payload(e))
        return 1


def cmd_review_batch(args) -> int:
    """M2.3.2D: generate a phrase-review batch from a diagnostic run."""
    from .review.render import generate_batch, regenerate_batch
    cfg = load_config()
    run_dir = Path(cfg["runs_dir"]) / args.run_id
    if not (run_dir / "diagnostic" / "residual_triage.json").exists():
        return fail("no_diagnostic",
                    f"{args.run_id} has no diagnostic artifacts")
    items = args.items.split(",") if args.items else None
    try:
        if args.regenerate is not None:
            batch = regenerate_batch(
                run_dir, cfg=cfg, src_batch_id=args.regenerate or None,
                render=not args.no_render, batch_id=args.batch_id,
                progress=lambda m: diag(f"[review] {m}"))
        else:
            batch = generate_batch(
                run_dir, cfg=cfg, render=not args.no_render,
                max_items=args.max_items, only_items=items,
                batch_id=args.batch_id,
                progress=lambda m: diag(f"[review] {m}"))
    except Exception as e:
        emit(exception_payload(e))
        return 1
    if batch is None:
        return fail("no_items", "nothing to package "
                    "(no review items / regeneration queue empty)")
    out = {"schema_version": "1", "status": "ok",
           "batch_id": batch["batch_id"], "run_id": batch["run_id"],
           "n_items": len(batch["items"]),
           "rendered": not args.no_render,
           "items": [{k: it[k] for k in
                      ("item_id", "type", "reason", "phrase", "n_options")}
                     for it in batch["items"]]}
    return _out(args, out)


def _review_batch_dir(args) -> Path:
    from .review.render import find_batch
    cfg = load_config()
    run_dir = Path(cfg["runs_dir"]) / args.run_id
    return find_batch(run_dir, getattr(args, "batch", None))


def cmd_review_status(args) -> int:
    from .review.decisions import DecisionStore, DECISIONS_NAME
    from .review.render import load_batch
    try:
        bdir = _review_batch_dir(args)
        batch, mans = load_batch(bdir)
    except FileNotFoundError as e:
        return fail("no_batch", str(e))
    store = DecisionStore(bdir / DECISIONS_NAME)
    items = [{"item_id": m["review_item_id"],
              "package_hash": m["package_hash"]} for m in mans.values()]
    status = store.batch_status(items)
    return _out(args, {"schema_version": "1", "status": "ok",
                       "batch_id": batch["batch_id"],
                       "run_id": batch["run_id"], "progress": status})


def cmd_review_decide(args) -> int:
    """Record one human decision non-interactively (persisted at once)."""
    from .review.decisions import (DecisionStore, DECISIONS_NAME,
                                   SPECIAL_CHOICES)
    from .review.render import load_batch
    try:
        bdir = _review_batch_dir(args)
        batch, mans = load_batch(bdir)
    except FileNotFoundError as e:
        return fail("no_batch", str(e))
    man = mans.get(args.item_id)
    if man is None:
        return fail("no_item", f"no review item {args.item_id}")
    choice = args.choice
    valid = [o["option_id"] for o in man["options"]] + list(SPECIAL_CHOICES)
    if choice not in valid:
        return fail("bad_choice", f"choice must be one of {valid}")
    store = DecisionStore(bdir / DECISIONS_NAME)
    rev = store.record(args.item_id, choice, man["package_hash"], man,
                       generation=man["review"]["generation"])
    return _out(args, {"schema_version": "1", "status": "ok",
                       "decision": rev})


def _play(path: Path):
    """Play a wav through ffplay (blocking); fall back to os.startfile."""
    import shutil
    import subprocess
    ffplay = shutil.which("ffplay")
    if ffplay:
        subprocess.run([ffplay, "-nodisp", "-autoexit", "-loglevel",
                        "error", str(path)], check=False)
    else:  # Windows default player; returns immediately
        import os
        os.startfile(str(path))  # noqa: S606


def cmd_review(args) -> int:
    """Interactive blind review loop with resume (§6.11-§6.13)."""
    from .review.decisions import (DecisionStore, DECISIONS_NAME,
                                   SPECIAL_CHOICES)
    from .review.render import load_batch
    try:
        bdir = _review_batch_dir(args)
        batch, mans = load_batch(bdir)
    except FileNotFoundError as e:
        return fail("no_batch", str(e))
    store = DecisionStore(bdir / DECISIONS_NAME)
    items = [{"item_id": m["review_item_id"],
              "package_hash": m["package_hash"]} for m in mans.values()]
    pending = store.pending_items(items)
    order = [it["item_id"] for it in batch["items"]
             if it["item_id"] in pending]
    if not order:
        return _out(args, {"schema_version": "1", "status": "ok",
                           "message": "no pending items"})
    print(f"{len(order)} pending items in batch {batch['batch_id']}")
    for iid in order:
        man = mans[iid]
        ph = man["phrase"]
        print(f"\n=== {iid}  phrase {ph['start']:.2f}-{ph['end']:.2f}s "
              f"({man['target_group']['type']})  "
              f"gen{man['review']['generation']} ===")
        print("  play: s=source mix  v=separated vocal  "
              + "  ".join(f"{i}=OPTION_{i}"
                         for i in range(len(man["options"])))
              + "\n  decide: o0..o%d select | e=都差不多 equivalent | "
                "x=都不对 none_correct | q=quit"
              % (len(man["options"]) - 1))
        pdir = bdir / "phrases" / man["context"]["phrase_key"]
        while True:
            try:
                c = input("choice> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                c = "q"
            if c == "q":
                return _out(args, {"schema_version": "1", "status": "ok",
                                   "message": "quit; progress saved"})
            if c == "s":
                _play(pdir / "SOURCE_PHRASE_original_mix.wav")
            elif c == "v":
                _play(pdir / "SOURCE_PHRASE_separated_vocal.wav")
            elif c.isdigit() and int(c) < len(man["options"]):
                _play(bdir / "items" / iid / f"OPTION_{c}.wav")
            elif c == "r":
                continue
            elif c in ("e", "x"):
                choice = "equivalent" if c == "e" else "none_correct"
                rev = store.record(iid, choice, man["package_hash"], man,
                                   generation=man["review"]["generation"])
                print(f"  saved: {rev['semantics']}")
                break
            elif c.startswith("o") and c[1:].isdigit() and \
                    int(c[1:]) < len(man["options"]):
                rev = store.record(iid, f"OPTION_{c[1:]}",
                                   man["package_hash"], man,
                                   generation=man["review"]["generation"])
                print(f"  saved: {rev['semantics']} ({c})")
                break
            else:
                print("  (0..n plays; o0..on selects; e=equivalent; "
                      "x=none; q=quit)")
    return _out(args, {"schema_version": "1", "status": "ok",
                       "message": "batch complete"})


def cmd_status(args) -> int:
    from .state import read_state
    cfg = load_config()
    st = read_state(Path(cfg["runs_dir"]), args.run_id)
    if st is None:
        return fail("no_run", f"no run state for {args.run_id}")
    out = {"schema_version": "1", "status": st.get("status", "unknown"),
           "state": st}
    rep = Path(cfg["runs_dir"]) / args.run_id / "report.json"
    if rep.exists():
        import json
        r = json.loads(rep.read_text(encoding="utf-8"))
        out["report"] = {k: r[k] for k in
                         ("n_notes", "n_weak_notes", "quality_confidence",
                          "pitch_eval", "ustx", "vocal_wav", "mix",
                          "caveats", "lyrics_source") if k in r}
        if "pitch_eval" in out["report"]:
            out["report"]["pitch_eval"] = out["report"]["pitch_eval"].get(
                "pitch", {})
    return _out(args, out)


def cmd_resume(args) -> int:
    import json
    from .pipeline import run_cover, parse_segments
    from .state import Run
    cfg = load_config()
    run_dir = Path(cfg["runs_dir"]) / args.run_id
    req_path = run_dir / "request.json"
    if not req_path.exists():
        return fail("no_request",
                    f"{args.run_id} has no request.json; cannot resume")
    req = json.loads(req_path.read_text(encoding="utf-8"))
    run = Run(Path(cfg["runs_dir"]), args.run_id)
    run.write_state({"status": "running", "stage": "resumed",
                     "source": req["source"]})
    try:
        rep = run_cover(
            req["source"], run, cfg,
            segments=parse_segments(req["segments"]) if req.get("segments")
            else None,
            auto_segments=req.get("auto_segments", 2),
            seg_len=req.get("seg_len", 15.0),
            asr_model=req.get("asr_model", "large-v3-turbo"),
            sep_model=req.get("sep_model", "UVR-MDX-NET-Voc_FT.onnx"),
            lyrics=req.get("lyrics"), lines=req.get("lines"),
            timeout_min=req.get("timeout_min", 30),
            iters=req.get("iters", 2),
            pitch_strength=req.get("pitch_strength", 1.0),
            voice_color=req.get("voice_color", "Yousa_Normal"),
            compare_colors=req.get("compare_colors", False),
            breaths=req.get("breaths", True),
            progress=lambda m: diag(f"[resume] {m}"))
        rep["resumed_from"] = args.run_id
        return _out(args, rep)
    except Exception as e:
        run.write_state({"status": "failed", "stage": "error",
                         "failure_code": "internal_error"})
        emit(exception_payload(e))
        return 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="agent2utau")
    ap.add_argument("--json", action="store_true", default=True)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor"); p.set_defaults(fn=cmd_doctor)
    p = sub.add_parser("inspect-reference"); p.set_defaults(fn=cmd_inspect_reference)
    p.add_argument("path")

    p = sub.add_parser("migrate-phrase"); p.set_defaults(fn=cmd_migrate_phrase)
    p.add_argument("--project", required=True)
    p.add_argument("--track", type=int, default=0)
    p.add_argument("--out", required=True)
    p.add_argument("--singer", default="YousaV1.65b")
    p.add_argument("--min-notes", type=int, default=8)
    p.add_argument("--min-ms", type=float, default=4000)
    p.add_argument("--max-ms", type=float, default=12000)

    p = sub.add_parser("render-smoke"); p.set_defaults(fn=cmd_render_smoke)
    p.add_argument("--project", required=True)
    p.add_argument("--timeout-min", type=int, default=20)

    p = sub.add_parser("roundtrip"); p.set_defaults(fn=cmd_roundtrip)
    p.add_argument("--project", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("deploy-bridge"); p.set_defaults(fn=cmd_deploy_bridge)
    p.add_argument("--no-build", action="store_true")

    p = sub.add_parser("cover"); p.set_defaults(fn=cmd_cover)
    p.add_argument("source", nargs="?")
    p.add_argument("--singer", default="yousa")
    p.add_argument("--segments", default=None,
                   help="comma list of start:end seconds, e.g. '60:75,150:165'")
    p.add_argument("--auto-segments", type=int, default=2,
                   help="auto-pick N high-energy vocal windows")
    p.add_argument("--seg-len", type=float, default=15.0)
    p.add_argument("--lyrics", default=None,
                   help="Recording-matched LRC; characters are acoustically aligned")
    p.add_argument("--lines", default=None,
                   help="line range within lyrics file, e.g. '0:4'")
    p.add_argument("--asr-model", default="large-v3-turbo")
    p.add_argument("--sep-model", default="UVR-MDX-NET-Voc_FT.onnx")
    p.add_argument("--timeout-min", type=int, default=30)
    p.add_argument("--iters", type=int, default=2,
                   help="1=baseline only; 2=also try pitd-inject variant")
    p.add_argument("--pitch-strength", type=float, default=1.0,
                   help="0-1 blend of measured F0 into pitd curve")
    p.add_argument("--voice-color", default="Yousa_Normal",
                   help="Yousa_Bright|Classic|Cute|Normal|Whisper")
    p.add_argument("--compare-colors", action="store_true",
                   help="also render all 5 colors on first segment")
    p.add_argument("--no-breaths", action="store_true",
                   help="don't auto-insert AP breath notes at phrase gaps")

    p = sub.add_parser("diagnose"); p.set_defaults(fn=cmd_diagnose)
    p.add_argument("source")
    p.add_argument("--language", default="zh")
    p.add_argument("--timeout-min", type=int, default=30)
    p.add_argument("--repeats", type=int, default=1,
                   help="same-config GAME reruns per variant (>=5 builds "
                        "the M2.1.2 stochastic consensus)")

    p = sub.add_parser("review-batch"); p.set_defaults(fn=cmd_review_batch)
    p.add_argument("run_id", help="diagnostic run id")
    p.add_argument("--batch-id", default=None)
    p.add_argument("--regenerate", nargs="?", const="", default=None,
                   help="build generation-2 packages for items rejected "
                        "in the given (or latest) batch")
    p.add_argument("--no-render", action="store_true",
                   help="write manifests only, no OpenUtau render")
    p.add_argument("--max-items", type=int, default=None)
    p.add_argument("--items", default=None,
                   help="comma list of packet ids to include")

    p = sub.add_parser("review"); p.set_defaults(fn=cmd_review)
    p.add_argument("run_id", help="diagnostic run id")
    p.add_argument("--batch", default=None)

    p = sub.add_parser("review-status"); p.set_defaults(fn=cmd_review_status)
    p.add_argument("run_id", help="diagnostic run id")
    p.add_argument("--batch", default=None)

    p = sub.add_parser("review-decide"); p.set_defaults(fn=cmd_review_decide)
    p.add_argument("run_id", help="diagnostic run id")
    p.add_argument("item_id")
    p.add_argument("choice",
                   help="OPTION_i | equivalent | none_correct")
    p.add_argument("--batch", default=None)

    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)
    p.add_argument("run_id")

    p = sub.add_parser("resume"); p.set_defaults(fn=cmd_resume)
    p.add_argument("run_id")

    return ap


def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except Exception as e:
        emit(exception_payload(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
