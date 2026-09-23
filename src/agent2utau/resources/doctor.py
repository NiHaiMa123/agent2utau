"""`doctor` command: probe local resources.

Reports are deliberately split into files_found / singer_loaded /
render_passed / automation_passed per plan section 2.3.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from ..util.jsonio import diag
from ..openutau.bridge import bridge_path, run_bridge


def _tool(cmd: str) -> dict[str, Any]:
    exe = shutil.which(cmd)
    return {"name": cmd, "path": exe, "found": exe is not None}


def _run(argv: list[str], timeout: int = 15) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def probe(cfg: dict[str, Any]) -> dict[str, Any]:
    ou_dir = Path(cfg["openutau_dir"])
    exe = ou_dir / "OpenUtau.exe"
    report: dict[str, Any] = {
        "schema_version": "1",
        "status": "ok",
        "files_found": {},
        "singer_loaded": {},
        "render_passed": None,
        "automation_passed": None,
        "tools": [],
        "warnings": [],
    }

    # --- files_found ---
    ff = report["files_found"]
    ff["openutau_exe"] = exe.exists()
    ff["openutau_core_dll"] = (ou_dir / "OpenUtau.Core.dll").exists()
    ff["prefs"] = (ou_dir / "prefs.json").exists()
    ff["portable_mode"] = not (ou_dir / "installed.txt").exists()
    ff["installed_marker"] = (ou_dir / "installed.txt").exists()

    # version from OpenUtau.deps.json (authoritative for the app entry)
    ver = None
    deps = ou_dir / "OpenUtau.deps.json"
    if deps.exists():
        try:
            d = json.loads(deps.read_text(encoding="utf-8-sig"))
            for k in d.get("libraries", {}):
                if k.startswith("OpenUtau/"):
                    ver = k.split("/", 1)[1]
        except Exception as e:
            report["warnings"].append(f"deps.json parse: {e}")
    ff["openutau_version"] = ver

    singer_id = cfg.get("default_singer", "YousaV1.65c")
    singer_dir = ou_dir / "Singers" / singer_id
    ff["singer_dir"] = singer_dir.exists()
    ff["singer_character_yaml"] = (singer_dir / "character.yaml").exists()
    ff["singer_dsconfig"] = (singer_dir / "dsconfig.yaml").exists()
    ff["onnx_acoustic"] = (singer_dir / "0818_no_shuffle.onnx").exists()
    ff["bridge_deployed"] = bridge_path(cfg) is not None

    if (singer_dir / "character.yaml").exists():
        ch = yaml.safe_load((singer_dir / "character.yaml").read_text(encoding="utf-8-sig"))
        report["singer_loaded"]["character"] = {
            "singer_type": ch.get("singer_type"),
            "default_phonemizer": ch.get("default_phonemizer"),
            "subbanks": [s.get("color") for s in ch.get("subbanks", [])],
        }
    if (singer_dir / "dsconfig.yaml").exists():
        dsc = yaml.safe_load((singer_dir / "dsconfig.yaml").read_text(encoding="utf-8-sig"))
        report["singer_loaded"]["dsconfig"] = {
            "sample_rate": dsc.get("sample_rate"),
            "hop_size": dsc.get("hop_size"),
            "speakers": dsc.get("speakers"),
            "use_key_shift": dsc.get("use_key_shift"),
            "use_speed": dsc.get("use_speed"),
            "use_breathiness": dsc.get("use_breathiness"),
            "use_voicing": dsc.get("use_voicing"),
            "use_tension": dsc.get("use_tension"),
            "use_energy": dsc.get("use_energy"),
            "max_depth": dsc.get("max_depth"),
        }

    # --- tools ---
    for t in ("python", "ffmpeg", "ffprobe", "dotnet", "uv"):
        report["tools"].append(_tool(t))
    rc, out = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    report["gpu"] = out if rc == 0 else None
    rc, out = _run(["dotnet", "--version"])
    report["dotnet_version"] = out if rc == 0 else None

    # --- bridge-level checks (singer actually loads in OpenUtau.Core) ---
    bp = bridge_path(cfg)
    if bp:
        br = run_bridge(cfg, ["doctor"], timeout=120)
        report["bridge"] = br
        if br.get("ok"):
            report["singer_loaded"]["via_core"] = singer_id in br.get("singers_found", [])
    else:
        report["warnings"].append("a2u-bridge not deployed; singer_loaded/render_passed unverified")

    report["render_passed"] = False   # only render-smoke sets this true
    report["automation_passed"] = bp is not None
    return report
