"""JSON stdout contract helpers: machine result on stdout, diagnostics on stderr."""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any


def emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def diag(msg: str) -> None:
    sys.stderr.write(f"[agent2utau] {msg}\n")
    sys.stderr.flush()


def fail(failure_code: str, message: str, *, retryable: bool = False,
         next_actions: list[str] | None = None, exit_code: int = 1) -> int:
    emit({
        "schema_version": "1",
        "status": "failed",
        "failure_code": failure_code,
        "error": message,
        "retryable": retryable,
        "next_actions": next_actions or [],
    })
    return exit_code


def exception_payload(exc: BaseException) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "status": "failed",
        "failure_code": "internal_error",
        "error": f"{type(exc).__name__}: {exc}",
        "traceback": traceback.format_exc(),
        "retryable": False,
        "next_actions": ["inspect stderr log", "report bug"],
    }
