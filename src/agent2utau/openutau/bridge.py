"""Locate/deploy and invoke a2u-bridge.exe inside the OpenUtau install dir.

Deployment copies a2u-bridge.{exe,dll,runtimeconfig.json} and generates
a2u-bridge.deps.json by cloning the OpenUtau target entry in
OpenUtau.deps.json (same dependency set -> identical assembly resolution).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ..util.jsonio import diag
from ..resources.config import REPO_ROOT

BRIDGE_NAME = "a2u-bridge"


def bridge_path(cfg: dict[str, Any]) -> Path | None:
    exe = Path(cfg["openutau_dir"]) / f"{BRIDGE_NAME}.exe"
    return exe if exe.exists() else None


def build_bridge(out_dir: Path | None = None) -> Path:
    """dotnet publish self-contained; returns publish dir."""
    out_dir = out_dir or (REPO_ROOT / "bridge" / "out-sc")
    proj = REPO_ROOT / "bridge" / "OuBridge" / "OuBridge.csproj"
    p = subprocess.run(
        ["dotnet", "publish", str(proj), "-c", "Release", "-r", "win-x64",
         "--self-contained", "true", "-o", str(out_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"bridge publish failed:\n{p.stdout}\n{p.stderr}")
    return out_dir


def make_deps_json(ou_dir: Path) -> dict:
    src = ou_dir / "OpenUtau.deps.json"
    d = json.loads(src.read_text(encoding="utf-8-sig"))
    rid_key = None
    for k in d["targets"]:
        if "/" in k:  # the RID-qualified target
            rid_key = k
    if rid_key is None:
        rid_key = list(d["targets"].keys())[-1]
    tgt = d["targets"][rid_key]
    ou_entry_key = next(k for k in tgt if k.startswith("OpenUtau/"))
    entry = json.loads(json.dumps(tgt[ou_entry_key]))  # deep copy
    entry["runtime"] = {f"{BRIDGE_NAME}.dll": {}}
    tgt[f"{BRIDGE_NAME}/0.1.0"] = entry
    d["libraries"][f"{BRIDGE_NAME}/0.1.0"] = {
        "type": "project", "serviceable": False, "sha512": ""}
    return d


def deploy_bridge(cfg: dict[str, Any], publish_dir: Path | None = None) -> Path:
    ou_dir = Path(cfg["openutau_dir"])
    publish_dir = publish_dir or (REPO_ROOT / "bridge" / "out-sc")
    if not publish_dir.exists():
        build_bridge(publish_dir)
    for ext in (".exe", ".dll", ".runtimeconfig.json"):
        src = publish_dir / f"{BRIDGE_NAME}{ext}"
        dst = ou_dir / src.name
        dst.write_bytes(src.read_bytes())
        diag(f"deployed {dst}")
    deps = make_deps_json(ou_dir)
    (ou_dir / f"{BRIDGE_NAME}.deps.json").write_text(
        json.dumps(deps), encoding="utf-8")
    diag(f"wrote {ou_dir / (BRIDGE_NAME + '.deps.json')}")
    return ou_dir / f"{BRIDGE_NAME}.exe"


def run_bridge(cfg: dict[str, Any], args: list[str], timeout: int = 600) -> dict[str, Any]:
    exe = bridge_path(cfg)
    if exe is None:
        raise FileNotFoundError("a2u-bridge.exe not deployed in OpenUtau dir")
    p = subprocess.run([str(exe), *args], capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace",
                       cwd=cfg["openutau_dir"])
    if p.stderr.strip():
        diag(p.stderr.strip()[:2000])
    out = p.stdout.strip()
    try:
        result = json.loads(out.splitlines()[-1]) if out else {"ok": False, "errors": ["no output"]}
    except json.JSONDecodeError:
        result = {"ok": False, "errors": [f"bad bridge output: {out[:500]}"]}
    result["exit_code"] = p.returncode
    return result
