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
    return fail("not_implemented",
                "cover pipeline requires M2 (separation/ASR/F0); not yet implemented",
                next_actions=["run inspect-reference + render-smoke first"])


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

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except Exception as e:
        emit(exception_payload(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
