"""Run state: runs/<run-id>/ with atomic state.json writes and a lock file."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid():x}"


class Run:
    def __init__(self, root: Path, run_id: str):
        self.id = run_id
        self.dir = root / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "debug").mkdir(exist_ok=True)
        (self.dir / "iterations").mkdir(exist_ok=True)
        (self.dir / "audio").mkdir(exist_ok=True)
        self.lock = self.dir / "run.lock"
        self.lock.write_text(str(os.getpid()), encoding="utf-8")

    @property
    def state_path(self) -> Path:
        return self.dir / "state.json"

    def write_state(self, state: dict[str, Any]) -> None:
        state = {**state, "run_id": self.id, "schema_version": "1",
                 "updated_at": time.time()}
        tmp = self.dir / "state.json.tmp"
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(tmp, self.state_path)

    def write_json(self, name: str, data: dict[str, Any]) -> Path:
        p = self.dir / name
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                     encoding="utf-8")
        return p


def read_state(runs_dir: Path, run_id: str) -> dict[str, Any] | None:
    p = runs_dir / run_id / "state.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
