"""Config loading: configs/defaults.yaml + optional configs/local.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(repo: Path | None = None) -> dict[str, Any]:
    repo = repo or REPO_ROOT
    cfg: dict[str, Any] = {}
    for name in ("defaults.yaml", "local.yaml"):
        p = repo / "configs" / name
        if p.exists():
            cfg = _deep_merge(cfg, yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    cfg.setdefault("openutau_dir", r"E:\software\OpenUtau-win-x64 (6)")
    cfg.setdefault("default_singer", "YousaV1.65c")
    cfg.setdefault("reference_dir", r"E:\data\project_opentuau")
    cfg.setdefault("runs_dir", str(repo / "runs"))
    cfg["openutau_dir"] = os.path.expandvars(cfg["openutau_dir"])
    cfg["reference_dir"] = os.path.expandvars(cfg["reference_dir"])
    cfg["runs_dir"] = os.path.expandvars(cfg["runs_dir"])
    return cfg
